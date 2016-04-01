import qt, vtk, ctk
import os, logging
import slicer


class ModuleWidgetMixin(object):

  @property
  def layoutManager(self):
    return slicer.app.layoutManager()

  @property
  def dicomDatabase(self):
    return slicer.dicomDatabase

  @staticmethod
  def truncatePath(path):
    try:
      split = path.split('/')
      path = '.../' + split[-2] + '/' + split[-1]
    except IndexError:
      pass
    return path

  @staticmethod
  def setFOV(sliceLogic, FOV):
    sliceNode = sliceLogic.GetSliceNode()
    sliceNode.SetFieldOfView(FOV[0], FOV[1], FOV[2])
    sliceNode.UpdateMatrices()

  @staticmethod
  def removeNodeFromMRMLScene(node):
    if node:
      slicer.mrmlScene.RemoveNode(node)
      node = None

  @staticmethod
  def refreshViewNodeIDs(node, sliceNodes):
    displayNode = node.GetDisplayNode()
    if displayNode:
      displayNode.RemoveAllViewNodeIDs()
      for sliceNode in sliceNodes:
        displayNode.AddViewNodeID(sliceNode.GetID())

  @staticmethod
  def jumpSliceNodeToTarget(sliceNode, targetNode, index):
    point = [0,0,0,0]
    targetNode.GetMarkupPointWorld(index, 0, point)
    sliceNode.JumpSlice(point[0], point[1], point[2])

  @staticmethod
  def resetToRegularViewMode():
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    interactionNode.SwitchToViewTransformMode()
    interactionNode.SetPlaceModePersistence(0)

  def getSetting(self, setting, moduleName=None):
    moduleName = moduleName if moduleName else self.moduleName
    settings = qt.QSettings()
    return str(settings.value(moduleName + '/' + setting))

  def setSetting(self, setting, value, moduleName=None):
    moduleName = moduleName if moduleName else self.moduleName
    settings = qt.QSettings()
    settings.setValue(moduleName + '/' + setting, value)

  def createHLayout(self, elements, **kwargs):
    return self._createLayout(qt.QHBoxLayout, elements, **kwargs)

  def createVLayout(self, elements, **kwargs):
    return self._createLayout(qt.QVBoxLayout, elements, **kwargs)

  def _createLayout(self, layoutClass, elements, **kwargs):
    widget = qt.QWidget()
    rowLayout = layoutClass()
    widget.setLayout(rowLayout)
    for element in elements:
      rowLayout.addWidget(element)
    for key, value in kwargs.iteritems():
      if hasattr(rowLayout, key):
        setattr(rowLayout, key, value)
    return widget

  def createIcon(self, filename, iconPath=None):
    if not iconPath:
      iconPath = os.path.join(self.modulePath, 'Resources/Icons')
    path = os.path.join(iconPath, filename)
    pixmap = qt.QPixmap(path)
    return qt.QIcon(pixmap)

  def createLabel(self, title, **kwargs):
    label = qt.QLabel(title)
    return self.extendQtGuiElementProperties(label, **kwargs)

  def createButton(self, title, **kwargs):
    button = qt.QPushButton(title)
    button.setCursor(qt.Qt.PointingHandCursor)
    return self.extendQtGuiElementProperties(button, **kwargs)

  def createDirectoryButton(self, **kwargs):
    button = ctk.ctkDirectoryButton()
    for key, value in kwargs.iteritems():
      if hasattr(button, key):
        setattr(button, key, value)
    return button

  def extendQtGuiElementProperties(self, element, **kwargs):
    for key, value in kwargs.iteritems():
      if hasattr(element, key):
        setattr(element, key, value)
      else:
        if key == "fixedHeight":
          element.minimumHeight = value
          element.maximumHeight = value
        elif key == 'hidden':
          if value:
            element.hide()
          else:
            element.show()
        else:
          logging.error("%s does not have attribute %s" % (element.className(), key))
    return element

  def createComboBox(self, **kwargs):
    combobox = slicer.qMRMLNodeComboBox()
    combobox.addEnabled = False
    combobox.removeEnabled = False
    combobox.noneEnabled = True
    combobox.showHidden = False
    for key, value in kwargs.iteritems():
      if hasattr(combobox, key):
        setattr(combobox, key, value)
      else:
        logging.error("qMRMLNodeComboBox does not have attribute %s" % key)
    combobox.setMRMLScene(slicer.mrmlScene)
    return combobox


class ModuleLogicMixin(object):

  @staticmethod
  def getMostRecentFile(path, fileType, filter=None):
    assert type(fileType) is str
    files = [f for f in os.listdir(path) if f.endswith(fileType)]
    if len(files) == 0:
      return None
    mostRecent = None
    storedTimeStamp = 0
    for filename in files:
      if filter and not filter in filename:
        continue
      actualFileName = filename.split(".")[0]
      timeStamp = int(actualFileName.split("-")[-1])
      if timeStamp > storedTimeStamp:
        mostRecent = filename
        storedTimeStamp = timeStamp
    return mostRecent

  @staticmethod
  def get2DDistance(pos1, pos2):
    x = abs(pos1[0] - pos2[0])
    y = abs(pos1[1] - pos2[1])
    return [x, y]

  @staticmethod
  def get3DDistance(pos1, pos2):
    rulerNode = slicer.vtkMRMLAnnotationRulerNode()
    rulerNode.SetPosition1(pos1)
    rulerNode.SetPosition2(pos2)
    distance_3D = rulerNode.GetDistanceMeasurement()
    return distance_3D

  @staticmethod
  def dilateMask(label):
    imagedata = label.GetImageData()
    dilateErode = vtk.vtkImageDilateErode3D()
    dilateErode.SetInputData(imagedata)
    dilateErode.SetDilateValue(1.0)
    dilateErode.SetErodeValue(0.0)
    dilateErode.SetKernelSize(12, 12, 1)
    dilateErode.Update()
    label.SetAndObserveImageData(dilateErode.GetOutput())

  @staticmethod
  def getDirectorySize(directory):
    size = 0
    for path, dirs, files in os.walk(directory):
      for currentFile in files:
        size += os.path.getsize(os.path.join(path, currentFile))
    return size

  @staticmethod
  def createDirectory(directory, message=None):
    if message:
      logging.debug(message)
    try:
      os.makedirs(directory)
    except OSError:
      logging.debug('Failed to create the following directory: ' + directory)

  @staticmethod
  def getDICOMValue(currentFile, tag, fallback=None):
    db = slicer.dicomDatabase
    try:
      value = db.fileValue(currentFile, tag)
    except RuntimeError:
      logging.info("There are problems with accessing DICOM value %s from file %s" % (tag, currentFile))
      value = fallback
    return value

  @staticmethod
  def getFileList(directory):
    return [f for f in os.listdir(directory) if ".DS_Store" not in f]

  @staticmethod
  def importStudy(dicomDataDir):
    indexer = ctk.ctkDICOMIndexer()
    indexer.addDirectory(slicer.dicomDatabase, dicomDataDir)
    indexer.waitForImportFinished()

  @staticmethod
  def createScalarVolumeNode(name=None):
    return ModuleLogicMixin.createNode(slicer.vtkMRMLScalarVolumeNode, name=name)

  @staticmethod
  def createBSplineTransformNode(name=None):
    return ModuleLogicMixin.createNode(slicer.vtkMRMLBSplineTransformNode, name=name)

  @staticmethod
  def createLinearTransformNode(name=None):
    return ModuleLogicMixin.createNode(slicer.vtkMRMLLinearTransformNode, name=name)

  @staticmethod
  def createModelNode(name=None):
    return ModuleLogicMixin.createNode(slicer.vtkMRMLModelNode, name=name)

  @staticmethod
  def createNode(nodeType, name=None):
    node = nodeType()
    if name:
      node.SetName(name)
    slicer.mrmlScene.AddNode(node)
    return node

  @staticmethod
  def saveNodeData(node, outputDir, extension, replaceUnwantedCharacters=True, name=None):
    name = name if name else node.GetName()
    if replaceUnwantedCharacters:
      name = ModuleLogicMixin.replaceUnwantedCharacters(name)
    filename = os.path.join(outputDir, name + extension)
    return slicer.util.saveNode(node, filename), name

  @staticmethod
  def replaceUnwantedCharacters(string, characters=None, replaceWith="-"):
    if not characters:
      characters = [": ", " ", ":", "/"]
    for character in characters:
      string = string.replace(character, replaceWith)
    return string

  @staticmethod
  def handleSaveNodeDataReturn(success, name, successfulList, failedList):
    listToAdd = successfulList if success else failedList
    listToAdd.append(name)

  @staticmethod
  def applyTransform(transform, node):
    tfmLogic = slicer.modules.transforms.logic()
    node.SetAndObserveTransformNodeID(transform.GetID())
    tfmLogic.hardenTransform(node)

  @staticmethod
  def setAndObserveDisplayNode(node):
    displayNode = slicer.vtkMRMLModelDisplayNode()
    slicer.mrmlScene.AddNode(displayNode)
    node.SetAndObserveDisplayNodeID(displayNode.GetID())
    return displayNode

  @staticmethod
  def isVolumeExtentValid(volume):
    imageData = volume.GetImageData()
    try:
      extent = imageData.GetExtent()
      return extent[1] > 0 and extent[3] > 0 and extent[5] > 0
    except AttributeError:
      return False