#!./venv/bin/python
from __future__ import annotations
from PySide6.QtCore import *
from PySide6.QtCore import Qt
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtWidgets import QWidget
import networkx as nx
from enum import Enum
import random
import resources_rc
import itertools
import sys
import file_export
import copy
from webbrowser import open as webopen
from socket import inet_ntoa
import regexdef
import os

rad = 5
NODE_RAD = 50
userSettings: QSettings = None

class ToolMode(Enum):
	SELECT=1
	MOVE=2
	CONNECT=3
	NEW=4
	DELETE=5

def createNodeNameGenerator(basename: str):
	for i in itertools.count(1, 1):
		yield f"{basename}{i}"

def createIPv4Generator():
	# 0xc0a80001 = 192.168.0.1
	for i in itertools.count(0xc0a80001, 1):
		ip = inet_ntoa(i.to_bytes(4, byteorder="big"))
		ip += "/24"
		yield ip

def createMACAddrGenerator():
	for i in itertools.count(0x000000000000, 1):
		bs = i.to_bytes(6, "big")
		mac = ""
		for b in bs:
			mac += f"{b:02x}:"
		yield mac[0:-1]

def clearLayout(layout: QLayout):
	while (item := layout.itemAt(0)) != None:
		item.widget().deleteLater()
		layout.removeWidget(item.widget())

def initializeUserSettings():
	showKeys = ["OVSSingleControllerWarn"]
	for k in showKeys:
		if userSettings.value(f"Show/{k}") == None:
			userSettings.setValue(f"Show/{k}", True)

class WindowClass(QMainWindow):
	def __init__(self):
		super(WindowClass, self).__init__()
		self.setWindowTitle("NIEP GUI")
		self.mainWidget = MainWidget()
		self.editMenu = self.mainWidget.editMenu
		self.view = self.mainWidget.view
		self.menu = self.createMenuBar()
		self.editToolbar = self.createEditToolBar()
		self.addToolBar(self.editToolbar)
		self.filepath = ""
		self.setToolMode(ToolMode.SELECT)

		self.setMenuBar(self.menu)
		self.setCentralWidget(self.mainWidget)
	
	def createMenuBar(self) -> QMenuBar:
		menuBar = QMenuBar()
		menus = {
			"&File": {
				"New": (None, None),
				"Load": (self.loadTopology, "Ctrl+L"),
				"Save": (self.saveTopology, "Ctrl+S"),
				"Save as ...": (self.saveTopologyAs, "Ctrl+Shift+S"),
				"Export as ...": (lambda: self.exportDir(), "Ctrl+E")
			},
			"&Help": {
				"Documentation": (lambda: webopen("https://github.com/marzelop/NIEP-GUI/tree/main/docs"), None),
				"Report a bug": (None, None),
				"Troubleshooting": (None, None)
			},
			"&Run": {
				"Run topology": (self.runTopology, "Ctrl+R"),
				"Kill topology": (self.killTopology, "Ctrl+K")
			}
		}
		self.actions = []
		for menu in menus.keys():
			newmenu = QMenu(menu)
			for action in menus[menu].keys():
				a = QAction(action)
				self.actions.append(a) # Save actions so that they won't be destroyed when this function ends for some reason
				# Conditional for development: Should be removed after complete menu functionality
				if menus[menu][action][0] != None:
					a.triggered.connect(menus[menu][action][0])
				shortcut = menus[menu][action][1]
				if shortcut != None:
					shortcut = QKeySequence(shortcut)
					a.setShortcut(shortcut)
				newmenu.addAction(self.actions[-1])
				#newmenu.addAction(action)

			menuBar.addMenu(newmenu)

		return menuBar
	
	def createEditToolBar(self):
		self.editActions: list[QAction] = []
		toolbar = QToolBar("Edit")
		FUNCTION = 0
		ICON_PATH = 1
		SHORTCUT = 2
		actions = {
			"&Select": (lambda: self.setToolMode(ToolMode.SELECT), ":cursor.png", "S"),
			# "&Move": (lambda: self.setToolMode(ToolMode.MOVE), ":palm-of-hand.png"),
			"&Connect": (lambda: self.setToolMode(ToolMode.CONNECT), ":line.png", "C"),
			"&New": (lambda: self.setToolMode(ToolMode.NEW), ":add.png", "A"),
			"&Delete": (lambda: self.setToolMode(ToolMode.DELETE), ":trash.png", "D")
		}
		for action in actions.keys():
			self.editActions.append(QAction(QIcon(actions[action][ICON_PATH]), action))
			self.editActions[-1].triggered.connect(actions[action][FUNCTION])
			actionShortcut = QKeySequence(actions[action][SHORTCUT])
			self.editActions[-1].setShortcut(actionShortcut)
			self.editActions[-1].setCheckable(True)

		toolbar.addActions(self.editActions)
		return toolbar
	
	def getCurrentToolMode(self):
		return self.view.scene.toolMode
	
	def getToolModeButton(self, toolMode: ToolMode):
		if toolMode.value > ToolMode.MOVE.value: # Removed MOVE button
			return self.editActions[toolMode.value - 2]
		return self.editActions[toolMode.value - 1]
	
	def getCurrentToolModeButton(self):
		return self.getToolModeButton(self.getCurrentToolMode())

	def setToolMode(self, toolMode: ToolMode) -> None:
		self.getCurrentToolModeButton().setChecked(False)
		self.view.scene.setToolMode(toolMode)
		self.getCurrentToolModeButton().setChecked(True)

	def export(self, format: str):
		exportFunctions = {
			"JSON": file_export.generate_topo_file
		}
		f = exportFunctions[format]
		fname = QFileDialog.getSaveFileName()[0]
		if fname == '': # Prevents error when user cancel file selection or doesn't select any files
			return
		f(self.mainWidget.view.scene.netgraph, fname)
	
	def saveTopology(self):
		if self.filepath == "":
			self.saveTopologyAs()
		else:
			file_export.generate_NPGI_file(self.mainWidget.view.scene.netgraph, self.filepath)
	
	def saveTopologyAs(self):
		self.filepath = QFileDialog.getSaveFileName(filter="NPGI file (*.npgi)")[0]
		if self.filepath == "":
			return
		self.saveTopology()
	
	def loadTopology(self):
		filepath = QFileDialog.getOpenFileName(filter="Topology file (*.npgi)")[0]
		if filepath == "":
			return
		topo = file_export.load_NPGI_file(filepath)
		hosts: list[dict] = topo["TOPO"]["MININET"]["HOSTS"]
		positions: dict = topo["POSITIONS"]
		scene: SceneClass = self.mainWidget.view.scene
		scene.clear()
		nodes_without_pos = []
		# Load Hosts
		for h in hosts:
			name, hostInterfaces = h["ID"], h["INTERFACES"]
			pos = positions.get(name, None)
			if pos is None:
				pos = QPointF(0.0, 0.0)
				nodes_without_pos.append(name)
			else:
				pos = QPointF(pos[0], pos[1])
			scene.addNode(name, pos, "Host", {"INTERFACES": hostInterfaces})
		
		# Load Switches
		for s in topo["TOPO"]["MININET"]["SWITCHES"]:
			name = s
			pos = positions.get(name, None)
			if pos is None:
				pos = QPointF(0.0, 0.0)
				nodes_without_pos.append(name)
			else:
				pos = QPointF(pos[0], pos[1])
			scene.addNode(name, pos, "Switch", {})
		
		# Load VMS
		for vm in topo["VMS"]:
			name = vm["ID"]
			vminfo = copy.deepcopy(vm)
			vminfo.pop("ID")
			if name[-4:] == "@VNF":
				name = name[0:-4]
				vminfo["VNF"] = True
			else: vminfo["VNF"] = False

			for iface in vminfo["INTERFACES"]:
				if "LINK_MAC" not in iface.keys():
					iface["LINK_MAC"] = ""
			pos = positions.get(name, None)
			if pos is None:
				pos = QPointF(0.0, 0.0)
				nodes_without_pos.append(name)
			else:
				pos = QPointF(pos[0], pos[1])
			scene.addNode(name, pos, "VM", vminfo)	
		
		# Load Controllers
		for c in topo["TOPO"]["MININET"]["CONTROLLERS"]:
			name, ip, port = c["ID"], c["IP"], c["PORT"]
			pos = positions.get(name, None)
			if pos is None:
				pos = QPointF(0.0, 0.0)
				nodes_without_pos.append(name)
			else:
				pos = QPointF(pos[0], pos[1])
			scene.addNode(name, pos, "Controller", {"IP": ip, "PORT": port})
		
		for ovs in topo["TOPO"]["MININET"]["OVSWITCHES"]:
			name, ctrl = ovs["ID"], ovs["CONTROLLER"]
			ctrlobj = None if ctrl is None else scene.getNode(ctrl)['obj']
			pos = positions.get(name, None)
			if pos is None:
				pos = QPointF(0.0, 0.0)
				nodes_without_pos.append(name)
			else:
				pos = QPointF(pos[0], pos[1])
			ovsnode = scene.addNode(name, pos, "OVSwitch", {"CONTROLLER": ctrlobj})
			scene.connectNodes(ovsnode, ctrlobj)
		
		# Load connections
		connections = topo["TOPO"]["CONNECTIONS"]
		for c in connections:
			u, ui, v, vi = c["IN/OUT"], c.get("IN/OUTIFACE", None), c["OUT/IN"], c.get("OUT/INIFACE", None)
			uobj, vobj = scene.getNode(u)["obj"], scene.getNode(v)["obj"]
			uinfo, vinfo = uobj.nodeInfo, vobj.nodeInfo
			uiindex, viindex = None, None
			if uobj.hasInterface():
				uiindex = next((index for (index, iface) in enumerate(uinfo["INTERFACES"]) if iface["MAC"] == ui), None)
			if vobj.hasInterface():
				viindex = next((index for (index, iface) in enumerate(vinfo["INTERFACES"]) if iface["MAC"] == vi), None)		
			edgeInfo = {"INTERFACES": [uiindex, viindex]}
			scene.connectNodes(uobj, vobj, edgeInfo)
		self.filepath = filepath

	def runTopology(self):
		import requests
		filepath = QFileDialog.getOpenFileName(filter="JSON file (*.json)")[0]
		if filepath == "":
			return
		try:
			responseData = requests.post("http://127.0.0.1:5000/setup", params={"path":filepath})
			print(responseData)
		except requests.ConnectionError as e:
			msg = QMessageBox(QMessageBox.Icon.Critical, "Failed to run topology", f"Failed to run topology, verify if NIEP (not GUI) is running.")
			msg.exec()

	def killTopology(self):
		import requests
		try:
			responseData = requests.post("http://127.0.0.1:5000/kill", params={})
			print(responseData)
		except requests.ConnectionError:
			msg = QMessageBox(QMessageBox.Icon.Critical, "Failed to kill topology", f"Failed to kill topology, verify if NIEP (not GUI) is running.")
			msg.exec()

	def exportDir(self):
		import json
		import shutil
		responseDict = {}
		dialog = ExportDialog(responseDict)
		dialog.exec()
		if dialog.result() == 0:
			return
		filepath = responseDict["FILEPATH"]
		topoid = responseDict["ID"]
		mode = responseDict["MODE"]
		zipname = ""
		if mode == "ZIP":
			if filepath[-4:] == ".zip":
				filepath = filepath[:-4]
			zipname = f"{filepath}.zip"
		os.mkdir(filepath)
		os.mkdir(f"{filepath}/VMS")
		os.mkdir(f"{filepath}/VNFS")
		scene: SceneClass = self.mainWidget.view.scene
		topo = file_export.generate_topo_dict(scene.netgraph, "Topology")
		topo["ID"] = topoid
		vms = file_export.generate_VM_definitions(scene.netgraph)
		vnfs = file_export.generate_VNF_definitions(topo)
		with open(f"{filepath}/{topo['ID']}.json", "w") as fp:
			json.dump(topo, fp, indent=4)
		for vm in vms:
			with open(f"{filepath}/VMS/{vm['ID']}.json", "w") as fp:
				json.dump(vm, fp, indent=4)
		for vnf in vnfs:
			with open(f"{filepath}/VNFS/{vnf['ID']}.json", "w") as fp:
				json.dump(vnf, fp, indent=4)
		if mode == "ZIP":
			shutil.make_archive(filepath, "zip", f"{filepath}/../", filepath)


class ExportDialog(QDialog):
	class FilePathSelector(QWidget):
		def __init__(self, filepath: str):
			super().__init__()
			layout = QHBoxLayout()
			self.filepath = filepath
			self.filepathLabel = QLabel()
			self.setFilepath(filepath)
			self.filepathLabel.setFixedWidth(250)
			browseButton = QPushButton("Browse")
			browseButton.clicked.connect(self.getFilepathDialog)
			layout.addWidget(self.filepathLabel)
			layout.addWidget(browseButton)	
			self.setLayout(layout)
		
		def getFilepathDialog(self):
			filename = QFileDialog.getSaveFileName(filter="")[0]
			if filename != "":
				self.setFilepath(filename)
			return filename
		
		def getFilepath(self):
			return self.filepath
		
		def setFilepath(self, filepath):
			self.filepath = filepath
			metrics = QFontMetrics(self.filepathLabel.font())
			text = metrics.elidedText(filepath, Qt.TextElideMode.ElideLeft, self.filepathLabel.width())
			self.filepathLabel.setText(text)
			
		
	class TopoNameEditor(QWidget):
		def __init__(self):
			super().__init__()
			layout = QHBoxLayout()
			label = QLabel("Topology ID:")
			self.toponameedit = QLineEdit("Topology")
			layout.addWidget(label)
			layout.addWidget(self.toponameedit)
			self.setLayout(layout)
		
		def getTopoName(self):
			return self.toponameedit.text()

	def __init__(self, response: dict):
		super().__init__()
		layout = QVBoxLayout()
		self.response = response
		self.setModal(True)
		self.filepathSelector = self.FilePathSelector("")
		self.toponame = self.TopoNameEditor()
		self.exportMode = QComboBox()
		self.exportMode.addItems(["Directory", "ZIP file"])
		exportButton = QPushButton("Export")
		exportButton.clicked.connect(self.export)
		layout.addWidget(self.filepathSelector)
		layout.addWidget(self.toponame)
		layout.addWidget(self.exportMode)
		layout.addWidget(exportButton)
		self.setLayout(layout)
	
	def export(self):
		response = self.response
		topoName = self.toponame.getTopoName()
		filepath = self.filepathSelector.getFilepath()
		errorMessages = []
		if topoName == "":
			errorMessages.append("Invalid topology ID.")
		if filepath == "":
			errorMessages.append("Invalid file destination.")
		if len(errorMessages) > 0:
			return errorMessages
		if self.exportMode.currentText() == "ZIP file":
			filepath = file_export.add_default_extension(filepath, "zip")
		mode = {
			"Directory": "DIR",
			"ZIP file": "ZIP"
		}
		mode = mode[self.exportMode.currentText()]
		response.update({
			"ID": topoName,
			"FILEPATH": filepath,
			"MODE": mode
		})
		self.accept()


class MainWidget(QWidget):
	def __init__(self):
		super(MainWidget, self).__init__()
		self.editMenu = EditMenu()
		self.view = ViewClass(self.editMenu)
		layout = QHBoxLayout()
		layout.addWidget(self.editMenu)
		layout.addWidget(self.view)
		self.setLayout(layout)


class EditMenu(QWidget):
	def __init__(self):
		super(EditMenu, self).__init__()
		layout = QVBoxLayout()
		self.options = QListWidget()
		self.elementViewer = ElementViewer()
		self.creationOptions = CreationOptions()
		self.scene: SceneClass | None = None
		QListWidgetItem("test1", self.options)
		QListWidgetItem("test2", self.options)
		QListWidgetItem("test3", self.options)
		layout.addWidget(self.options)
		layout.addWidget(self.creationOptions)
		layout.addWidget(self.elementViewer.scroll)
		self.setMinimumWidth(200)
		self.setLayout(layout)
	
	def setScene(self, scene: SceneClass):
		self.elementViewer.setScene(scene)
		self.creationOptions.setScene(scene)
		self.scene = scene


class ElementViewer(QWidget):
	def __init__(self):
		super(ElementViewer, self).__init__()
		self.element: Node | Edge | None = None
		self.attributes: dict | None = None
		self.scene: SceneClass = None
		self.setAutoFillBackground(True)
		self.setPalette(QColor(255, 255, 255))
		self.setLayout(QVBoxLayout())
		self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

		self.scroll = QScrollArea()
		self.scroll.setWidgetResizable(True)
		self.scroll.setWidget(self)
		
		self.setElement(None)
		
	
	def setElement(self, element: Node | Edge | None):
		clearLayout(self.layout())
		self.element = element
		self.scroll.setWidget(self)
		if type(element) == Node:
			self.setNode(element)
		elif type(element) == Edge:
			self.setEdge(element)
		else:
			self.scroll.setWidget(None)

	def setNode(self, node: Node):
		setFunctions = {
			"Host": self.setHost,
			"Switch": self.setSwitch,
			"Controller": self.setController,
			"OVSwitch": self.setOVSwitch,
			"VM": self.setVM
		}
		f = setFunctions[node.type]
		nodeName = node.getName()
		layout = self.layout()
		layout.setSpacing(0)

		nameLabel = QLabel(node.type)
		nameLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
		nameEdit = NodeNameEditor(nodeName, self.scene)
		layout.addWidget(nameLabel)
		layout.addWidget(nameEdit)

		f(node)

	def setHost(self, node: Node):
		nodeInfo = node.nodeInfo

		layout = self.layout()

		iviewer = InterfaceViewer(node)
		layout.addWidget(iviewer)
	
	def setSwitch(self, node: Node):
		pass

	def setController(self, node: Node):
		nodeInfo = node.nodeInfo

		layout = self.layout()
		IPEditor = ElementLineEditor(nodeInfo, "IP")
		portEditor = ElementLineEditor(nodeInfo, "PORT")
		layout.addWidget(IPEditor)
		layout.addWidget(portEditor)
	
	def setOVSwitch(self, node: Node):
		pass

	def setVM(self, node: Node):
		nodeInfo = node.nodeInfo

		layout = self.layout()
		vnfCheckBox = CheckBoxKeyEditor(nodeInfo, "VNF")
		memoryEditor = ElementSpinEditor(nodeInfo, "MEMORY", 1, 4096)
		vcpuEditor = ElementSpinEditor(nodeInfo, "VCPU", 1, 16)
		diskEditor = VMDiskEditor(node)
		managementMACEditor = ElementLineEditor(nodeInfo, "MANAGEMENT_MAC")

		layout.addWidget(vnfCheckBox)
		layout.addWidget(memoryEditor)
		layout.addWidget(vcpuEditor)
		layout.addWidget(diskEditor)
		layout.addWidget(managementMACEditor)

		ifaceviewer = InterfaceViewer(node)
		layout.addWidget(ifaceviewer)
			
	def addInterface(self):
		node: Node = self.element
		iface = {"IP": None, "MAC": "00:00:00:00:00:00"}
		node.nodeInfo["INTERFACES"].append(iface)
		inum = len(node.nodeInfo["INTERFACES"])
		layout = self.layout()
		ilabel = InterfaceLabel(node, inum-1)
		button = layout.itemAt(layout.count()-1).widget()
		layout.removeWidget(button)
		layout.addWidget(ilabel)
		for k in iface.keys():
			layout.addWidget(ElementLineEditor(iface, k))
		layout.addWidget(button)		

	def setEdge(self, edge: Edge):
		layout = self.layout()
		layout.setSpacing(0)

		nameLabel = QLabel("Edge")
		nameLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)

		nodes = edge.nodes
		u, v = nodes

		nodesLabel = QLabel(f"Endpoints: {u.getName()} - {v.getName()}")
		layout.addWidget(nameLabel)
		layout.addWidget(nodesLabel)

		for i, n in enumerate(nodes):
			if n.hasInterface():
				layout.addWidget(QLabel(f"{n.getName()} interface:"))
				layout.addWidget(InterfaceComboSelector(n, edge))

	def setScene(self, scene: SceneClass):
		self.scene = scene
		scene.selectionChanged.connect(self.updateElement)

	def getNodeFromScene(self, nodeName: str) -> dict:
		return self.scene.getNode(nodeName)

	# Slot
	def updateElement(self):
		elements = self.scene.selectedItems()
		if len(elements) == 0:
			self.setElement(None)
			return
		self.setElement(elements[0])


class NodeNameEditor(QWidget):
	def __init__(self, nodeName: str, scene: SceneClass):
		super(NodeNameEditor, self).__init__()
		self.nodeName = nodeName
		self.scene = scene
		validator = QRegularExpressionValidator(regexdef.defaultNaming)
		layout = QHBoxLayout()
		nameEdit = QLineEdit(nodeName)
		nameEdit.setValidator(validator)
		nameEdit.editingFinished.connect(self.updateNodeName)
		layout.addWidget(QLabel(f"Name:"))
		layout.addWidget(nameEdit)
		self.setLayout(layout)
		self.nameEdit = nameEdit
	
	def updateNodeName(self):
		newName = self.nameEdit.text()
		if newName == "":
			self.nameEdit.setText(self.nodeName)
			return
		if newName == self.nodeName: return # Prevents duplicate error message box because QLineEdit.setText triggers QLineEdit.editingFinished
		if not self.scene.renameNode(self.nodeName, newName):
			self.nameEdit.setText(self.nodeName)
			msg = QMessageBox(QMessageBox.Icon.Warning, "Duplicate node name", f"Renaming {self.nodeName} to {newName} failed beacause a node's name should be unique and a node named {newName} already exists.")
			msg.exec()
			return
		self.nodeName = newName


class ElementLineEditor(QWidget):
	def __init__(self, modDict: dict, modKey: str, validRegex: str = None):
		super(ElementLineEditor, self).__init__()
		self.modDict = modDict
		self.modKey = modKey

		layout = QHBoxLayout()
		keyEdit = QLineEdit(modDict[modKey])
		if validRegex is not None:
			regex = QRegularExpression(validRegex)
			validator = QRegularExpressionValidator(regex)
			keyEdit.setValidator(validator)
		keyEdit.setFixedWidth(110)
		keyEdit.editingFinished.connect(lambda: self.modDict.update({self.modKey: keyEdit.text()}))
		layout.addWidget(QLabel(f"{modKey.replace('_', ' ')}:"))
		layout.addWidget(keyEdit)
		self.setLayout(layout)


class ElementSpinEditor(QWidget):
	def __init__(self, modDict: dict, modKey: str, min: int, max: int):
		super(ElementSpinEditor, self).__init__()
		self.modDict = modDict
		self.modKey = modKey

		layout = QHBoxLayout()
		keyEdit = QSpinBox()
		keyEdit.setRange(min, max)
		keyEdit.setValue(modDict[modKey])
		keyEdit.setFixedWidth(110)
		keyEdit.valueChanged.connect(lambda: self.modDict.update({self.modKey: keyEdit.value()}))
		layout.addWidget(QLabel(f"{modKey}:"))
		layout.addWidget(keyEdit)
		self.setLayout(layout)


class CheckBoxKeyEditor(QCheckBox):
	def __init__(self, modDict: dict, modKey: str, negateBool: bool = False):
		super(CheckBoxKeyEditor, self).__init__(modKey)

		self.modDict = modDict
		self.modKey = modKey
		self.negate = negateBool # Negates the output

		self.setChecked(self.modDict[self.modKey] != negateBool)

		self.stateChanged.connect(self.updateKey)
	
	def updateKey(self):
		self.modDict[self.modKey] = self.isChecked() != self.negate


class InterfaceLabel(QWidget):
	def __init__(self, node: Node, ifaceidx: int):
		super(InterfaceLabel, self).__init__()
		layout = QHBoxLayout()
		self.node = node
		self.ifidx = ifaceidx
		self.deleteBtn : QPushButton | None = None
		label = QLabel(f"Interface {ifaceidx+1}")
		layout.addWidget(label)
		if ifaceidx > 0:
			deleteBtn = QPushButton("Delete IFACE")
			deleteBtn.clicked.connect(lambda: (self.node.removeInterface(self.ifidx)))
			layout.addWidget(deleteBtn)
			self.deleteBtn = deleteBtn
		self.setLayout(layout)


class InterfaceComboSelector(QComboBox):
	def __init__(self, node: Node, edge: Edge):
		super(InterfaceComboSelector, self).__init__()
		self.node = node
		self.edge = edge
		ni = node.nodeInfo["INTERFACES"]
		for j in range(1, len(ni)+1):
			self.addItem(f"{j} - {ni[j-1]['MAC']}")
		self.setCurrentIndex(edge.getNodeInterfaceIndex(node))
		self.currentIndexChanged.connect(lambda: self.edge.updateNodeInterface(self.node, self.currentIndex()))


class InterfaceViewer(QWidget):
	def __init__(self, node : Node):
		super(InterfaceViewer, self).__init__()
		self.node = node

		layout = QVBoxLayout()
		self.setLayout(layout)
		self.updateInterfaces()
	
	def updateInterfaces(self):
		node = self.node
		nodeInfo = node.nodeInfo
		layout = self.layout()
		clearLayout(layout)
		ifaceKeyValidatorRegexTable = {
			"IP": regexdef.ipv4, # Host
			"MAC": regexdef.mac, # VM, Host
			"ID": regexdef.defaultNaming, #VM
			"LINK_MAC": regexdef.mac # VM
		}
		for i, interface in enumerate(nodeInfo["INTERFACES"]):
			ilabel = self.createIfaceLabel(node, i)
			layout.addWidget(ilabel)
			for k in interface.keys():
				layout.addWidget(ElementLineEditor(interface, k, ifaceKeyValidatorRegexTable[k]))

		newInterfaceButton = QPushButton(QIcon(":add.png"), "")
		newInterfaceButton.setToolTip("Add new interface")
		newInterfaceButton.clicked.connect(self.addInterface)
		layout.addWidget(newInterfaceButton)
	
	def addInterface(self):
		node: Node = self.node
		iface = {"IP": None, "MAC": "00:00:00:00:00:00"} if node.type == "Host" else {"ID": "", "MAC": "00:00:00:00:00:00", "LINK_MAC": ""}
		node.nodeInfo["INTERFACES"].append(iface)
		inum = len(node.nodeInfo["INTERFACES"])
		layout : QVBoxLayout = self.layout()
		ilabel = self.createIfaceLabel(node, inum-1)
		button = layout.itemAt(layout.count()-1).widget()
		layout.removeWidget(button)
		layout.addWidget(ilabel)
		for k in iface.keys():
			layout.addWidget(ElementLineEditor(iface, k))
		layout.addWidget(button)

	def createIfaceLabel(self, node: Node, idx: int):
		ilabel = InterfaceLabel(node, idx)
		ideletebtn = ilabel.deleteBtn
		if (ideletebtn is not None):
			ideletebtn.clicked.connect(self.updateInterfaces)
		return ilabel


class VMDiskEditor(QWidget):
	def __init__(self, node: Node):
		super(VMDiskEditor, self).__init__()
		layout = QHBoxLayout()
		label = QLabel("DISK:")
		combo = VMDiskComboSelector(node)
		layout.addWidget(label)
		layout.addWidget(combo)
		self.setLayout(layout)


class VMDiskComboSelector(QComboBox):
	options = [
		"click-on-osv",
		"tinycore12",
	]
	def __init__(self, node: Node):
		super(VMDiskComboSelector, self).__init__()
		self.node = node
		for option in self.options:
			self.addItem(option)
		self.setCurrentIndex(self.options.index(node.nodeInfo["DISK"]))
		self.currentIndexChanged.connect(self.setVMDisk)
	
	def setVMDisk(self):
		self.node.nodeInfo["DISK"] = self.options[self.currentIndex()]


class CreationOptions(QWidget):
	class NodeTypeOptionButton(QPushButton):
		def __init__(self, text: str, parent: CreationOptions):
			super().__init__(text)
			self.p = parent
			self.clicked.connect(lambda: self.p.scene.setNewNodeType(self.text()))

	def __init__(self):
		super(CreationOptions, self).__init__()
		self.scene: SceneClass = None
		options = {
			"Host": (None),
			"Switch": (None),
			"Controller": (None),
			"OVSwitch": (None),
			"VM": (None),
		}
		layout = QHBoxLayout()
		for k, v in options.items():
			button = self.NodeTypeOptionButton(k, self)
			layout.addWidget(button)
		self.setLayout(layout)

	def setScene(self, scene: SceneClass):
		self.scene = scene


class ViewClass(QGraphicsView):
	def __init__(self, editMenu: EditMenu):
		super(ViewClass, self).__init__()

		self.setDragMode(QGraphicsView.RubberBandDrag)

		self.scene : SceneClass = SceneClass(editMenu)
		self.setScene(self.scene)
		self.setRenderHint(QPainter.Antialiasing)
	
	def zoom(self, angleDelta: int, center: QPointF):
		if (angleDelta < 0):
			factor = 1/(1.0 + abs(angleDelta)*0.008)
		else: factor = (1.0 + angleDelta*0.008)
		self.centerOn(center)
		self.scale(factor, factor)


class SceneClass(QGraphicsScene):
	def __init__(self, editMenu: EditMenu):
		super(SceneClass, self).__init__()
		self.setSceneRect(-500, -500, 1000, 1000)
		self.grid = 40
		self.toolMode = ToolMode.SELECT
		self.netgraph = nx.Graph()
		editMenu.setScene(self)
		self.ipv4gen = createIPv4Generator()
		self.macaddrgen = createMACAddrGenerator()
		self.newNodeType = "Host"

		self.onclick = None
		self.nodeNameGenerators = self.createNodeNameGenerators(["Host", "Switch", "Controller", "OVSwitch", "VM"])
		self.tools = {
			ToolMode.SELECT.value: (None, None),
			ToolMode.NEW.value: (self.setToolNew, self.unsetToolNew),
			ToolMode.CONNECT.value: (self.setToolConnect, None),
			ToolMode.MOVE.value: (None, None),
			ToolMode.DELETE.value: (self.setToolDelete, None)
		}
		
	def drawBackground(self, painter, rect):
		painter.fillRect(rect, QColor(210, 210, 210))
		left = int(rect.left()) - int((rect.left()) % self.grid)
		top = int(rect.top()) - int((rect.top()) % self.grid)
		right = int(rect.right())
		bottom = int(rect.bottom())
		lines = []
		for x in range(left, right, self.grid):
			lines.append(QLine(x, top, x, bottom))
		for y in range(top, bottom, self.grid):
			lines.append(QLine(left, y, right, y))
		painter.setPen(QPen(QColor(150, 150, 150)))
		painter.drawLines(lines)

	def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
		if event.button() == Qt.LeftButton:
			if self.onclick != None:
				self.onclick(event)
		prevSel = self.selectedItems()
		prevSelNodes = list(filter(lambda i: type(i) == Node, prevSel))
		super(SceneClass, self).mousePressEvent(event) # This updates the selected elements

		currSel = self.selectedItems()
		currSelNodes = list(filter(lambda i: type(i) == Node, currSel))
		if self.toolMode == ToolMode.DELETE and len(currSel) > 0:
			self.remove(currSel[0])
		if len(currSelNodes) > 0:
			u = currSelNodes[0]
			if len(prevSelNodes) > 0:
				v = prevSelNodes[0]
				if self.toolMode == ToolMode.CONNECT:
					self.connectNodes(v, u, {"INTERFACES": [0, 0]})
	
	def validateConnection(self, u: Node, v: Node) -> bool:
		if u is v or self.netgraph.has_edge(u.getName(), v.getName()):
			return False
		validConnectionsTable = {
			"Host": {"Host", "Switch", "OVSwitch", "VM"},
			"Switch": {"Host", "VM"},
			"OVSwitch": {"Host", "VM", "Controller"},
			"Controller": {"OVSwitch"},
			"VM": {"Host", "Switch", "OVSwitch", "VM"}
		}
		if not v.type in validConnectionsTable[u.type]:
			return False
		return True
		
	def getToolFunction(self):
		return self.toolFunctions[self.toolMode.value]
	
	def getNewIPv4addr(self):
		return next(self.ipv4gen)
	
	def getNewMACaddr(self):
		return next(self.macaddrgen)
	
	def addNode(self, id: str, position: QPointF, type: str, nodeInfo: dict = {}) -> Node:
		node = Node(id, type, nodeInfo)
		self.netgraph.add_node(id, obj=node, info=nodeInfo)
		node.setPos(position)
		self.addItem(node)

		return node
	
	def getNode(self, nodeName: str):
		return self.netgraph.nodes[nodeName]
	
	def renameNode(self, nodeName: str, newName: str) -> bool:
		if self.netgraph.has_node(newName):
			return False
		self.netgraph = nx.relabel_nodes(self.netgraph, {nodeName: newName})
		self.getNode(newName)["obj"].setName(newName)

		return True
	
	def addDefaultHostNode(self, position: QPointF) -> Node:
		return self.addNode(self.getNodeName("Host"), position, "Host", {
			"INTERFACES": [
				{"IP": self.getNewIPv4addr(), "MAC": self.getNewMACaddr()},
			]})
	
	def addDefaultSwitchNode(self, position: QPointF) -> Node:
		return self.addNode(self.getNodeName("Switch"), position, "Switch", {})
	
	def addDefaultControllerNode(self, position: QPointF) -> Node:
		return self.addNode(self.getNodeName("Controller"), position, "Controller", {
				"IP": self.getNewIPv4addr(),
				"PORT": "3000"
			})
	
	def addDefaultOVSwitchNode(self, position: QPointF) -> Node:
		return self.addNode(self.getNodeName("OVSwitch"), position, "OVSwitch", {"CONTROLLER": None})
	
	def addDefaultVMNode(self, position: QPointF) -> Node:
		return self.addNode(self.getNodeName("VM"), position, "VM", {
			"VNF": False,
			"MEMORY": 300,
			"VCPU": 1,
			"DISK": "click-on-osv",
			"MANAGEMENT_MAC": self.getNewMACaddr(),
			"INTERFACES": [
				{
					"ID": "br0",
					"MAC": self.getNewMACaddr(),
					"LINK_MAC": ""
				}
			]
		})
	
	def setToolMode(self, toolMode):
		unsetf = self.tools[self.toolMode.value][1]
		setf = self.tools[toolMode.value][0]
		if not unsetf is None: unsetf()
		if not setf is None: setf()
		self.toolMode = toolMode
	
	def setToolNew(self):
		self.onclick = self.createNodeAtCursor
	
	def unsetToolNew(self):
		self.onclick = None
	
	def setToolConnect(self):
		self.clearSelection()
	
	def setToolDelete(self):
		self.clearSelection()

	def createNodeAtCursor(self, event: QGraphicsSceneMouseEvent):
		nodeFactories = {
			"Host": self.addDefaultHostNode,
			"Switch": self.addDefaultSwitchNode,
			"Controller": self.addDefaultControllerNode,
			"OVSwitch": self.addDefaultOVSwitchNode,
			"VM": self.addDefaultVMNode
		}
		f = nodeFactories[self.newNodeType]
		f(event.scenePos())

	def setNewNodeType(self, type: str):
		self.newNodeType = type

	def connectNodes(self, u: Node, v: Node, edgeInfo={}) -> Edge:
		if not self.validateConnection(u, v):
			return None
		if u.type == "Controller":
			u, v = v, u
		if u.type == "OVSwitch" and v.type == "Controller":
			oldControllerConnection = u.getControllerConnection()
			if oldControllerConnection != None:
				if userSettings.value("Show/OVSSingleControllerWarn") == True:
					msg = QMessageBox(QMessageBox.Icon.Information, "OVSwitch with multiple controllers", f"An OVSwitch should connect to one, and only one controller. The previous controller ({oldControllerConnection.getOtherNode(u).getName()}) will be disconnected from the OVSwitch ({u.getName()}) for this reason.")
					dontShowAgain = QCheckBox("Don't show this again")
					msg.setCheckBox(dontShowAgain)
					msg.exec()
					userSettings.setValue("Show/OVSSingleControllerWarn", not dontShowAgain.isChecked())
				self.remove(u.getControllerConnection())
			u.nodeInfo["CONTROLLER"] = v
		edge = Edge(u, v, edgeInfo)
		self.netgraph.add_edge(u.getName(), v.getName(), obj=edge, info=edgeInfo)
		u.addEdge(edge)
		v.addEdge(edge)
		self.addItem(edge)

		return edge
	
	def createNodeNameGenerators(self, nodeTypes: list[str]) -> dict:
		generators: dict = {}
		for nodeT in nodeTypes:
			generators[nodeT] = createNodeNameGenerator(nodeT)
		return generators
	
	def getNodeName(self, nodeType: str) -> str:
		name = next(self.nodeNameGenerators[nodeType])
		while (name in self.netgraph.nodes): # Prevents duplicates
			name = next(self.nodeNameGenerators[nodeType])
		return name
	
	def remove(self, obj: Node | Edge | None):
		if obj is None:
			return
		if type(obj) == Node:
			self.removeNode(obj)
		else:
			self.removeEdge(obj)
	
	def removeEdge(self, edge: Edge):
		self.netgraph.remove_edge(edge.nodes[0].getName(), edge.nodes[1].getName())
		edge.nodes[0].removeEdge(edge)
		edge.nodes[1].removeEdge(edge)
		self.removeItem(edge)

	def removeNode(self, node: Node):
		for edge in list(node.edges):
			self.removeEdge(edge)
		self.netgraph.remove_node(node.getName())
		self.removeItem(node)

	def clear(self):
		super(SceneClass, self).clear()
		self.netgraph = nx.Graph()

	def hasNode(self, nodeName: str):
		return self.netgraph.has_node(nodeName)


class Node(QGraphicsEllipseItem):
	nodeColorTable = {
		"Host": QColor(35, 158, 207),
		"Switch": QColor(228, 240, 122),
		"Controller": QColor(56, 207, 96),
		"OVSwitch": QColor(172, 184, 68),
		"VM": QColor(40, 55, 168)
	}
	def __init__(self, id: str, type: str, nodeInfo: dict = {}):
		# Using -NODE_RAD for the x and y of the bounding rectangle aligns the rectangle at the center of the node
		super(Node, self).__init__(-NODE_RAD, -NODE_RAD, 2*NODE_RAD, 2*NODE_RAD)

		# Instantiate the text object
		self.text = QGraphicsTextItem(id, parent=self)
		self.setName(id)
		self.nodeInfo = nodeInfo
		self.type = type
		
		self.edges: list[Edge] = []
		
		self.setFlag(QGraphicsItem.ItemIsMovable)
		self.setFlag(QGraphicsItem.ItemIsSelectable)
		self.setZValue(1)
		self.setBrush(self.nodeColorTable[type])
	
	def getName(self) -> str:
		return self.text.toPlainText()
	
	def setName(self, newName: str):
		self.text.setPlainText(newName)
		self.text.adjustSize()
		# Centers it within the ellipse
		self.text.setX(-self.text.boundingRect().width()/2)
		self.text.setY(-self.text.boundingRect().height()/2)

		# Set max text width to 95% of node diameter
		self.text.setTextWidth(min(0.95*2*NODE_RAD, self.text.boundingRect().width())) 
	
	def addEdge(self, edge: Edge) -> None:
		self.edges.append(edge)

	def paint(self, painter, option, widget):
		option.state &= ~QStyle.State_Selected
		super(Node, self).paint(painter, option, widget)
	
	def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
		for edge in self.edges:
			edge.updateLine()
		return super().mouseMoveEvent(event)

	def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
		if change == QGraphicsItem.ItemSelectedChange:
			# Selection is false when the item change to select the item is ocurring.
			# Therefore, it is needed to invert the following condition to highlight 
			# the selected items.
			if not self.isSelected():
				p = QPen(QColor(255,255,255), 3)
			else: p = QPen(QColor(0, 0, 0), 1)
			self.setPen(p)
		return super().itemChange(change, value)

	def removeEdge(self, edge: Edge):
		if edge is self.getControllerConnection():
			self.nodeInfo["CONTROLLER"] = None
		self.edges.remove(edge)
	
	def hasInterface(self):
		return self.type in ["Host", "VM"]
	
	def getControllerConnection(self) -> Edge | None:
		if self.type != "OVSwitch":
			return None
		for e in self.edges:
			other = e.getOtherNode(self)
			if other.type == "Controller":
				return e
		return None
	
	def removeInterface(self, ifaceidx):
		# Update the interfaces used by the connections of the node
		for e in self.edges:
			eifaceidx = e.getNodeInterfaceIndex(self)
			if e.edgeInfo["INTERFACES"][eifaceidx] >= ifaceidx:
				e.edgeInfo["INTERFACES"][eifaceidx] -= 1
		self.nodeInfo["INTERFACES"].pop(ifaceidx) # Remove the interface from the nodeinfo dict


	
class Edge(QGraphicsLineItem):
	def __init__(self, u: Node, v: Node, edgeInfo: dict = {}):
		super(Edge, self).__init__(QLineF(u.pos(), v.pos()))
		self.nodes = (u, v)
		pen = QPen()
		pen.setWidth(3)
		self.setPen(pen)
		self.setFlag(QGraphicsItem.ItemIsSelectable)
		self.edgeInfo = edgeInfo

		self.setZValue(0.5)
	
	def updateLine(self):
		self.setLine(QLineF(self.nodes[0].pos(), self.nodes[1].pos()))

	def paint(self, painter, option, widget):
		option.state &= ~QStyle.State_Selected
		super(Edge, self).paint(painter, option, widget)
	
	def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
		if change == QGraphicsItem.ItemSelectedChange:
			# Selection is false when the item change to select the item is ocurring.
			# Therefore, it is needed to invert the following condition to highlight 
			# the selected items.
			if not self.isSelected():
				p = QPen(QColor(255,255,255), 6)
			else: p = QPen(QColor(0, 0, 0), 3)
			self.setPen(p)
		return super().itemChange(change, value)

	def getNodeInterface(self, i: int):
		return self.nodes[i].nodeInfo["INTERFACES"]

	def getNodeIndex(self, node: Node):
		if node is self.nodes[0]:
			return 0
		elif node is self.nodes[1]:
			return 1
		else:
			return -1
	
	def getOtherNode(self, node: Node):
		if node is self.nodes[0]:
			return self.nodes[1]
		if node is self.nodes[1]:
			return self.nodes[0]
		return None

	def updateNodeInterface(self, node: Node, value: int):
		ni = self.getNodeIndex(node)
		self.edgeInfo["INTERFACES"][ni] = value
	
	def getNodeInterfaceIndex(self, node: Node):
		return self.edgeInfo["INTERFACES"][self.getNodeIndex(node)]

if __name__ == "__main__":
	app = QApplication()
	app.setOrganizationName("NIEP")
	app.setApplicationName("GUI")
	app.setApplicationDisplayName("NIEP-GUI")

	userSettings = QSettings("NIEP", "GUI")
	initializeUserSettings()
	window = WindowClass()
	window.show()

	app.exec()
	userSettings.sync()
