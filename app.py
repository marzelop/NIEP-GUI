#!./venv/bin/python
from __future__ import annotations
from PySide6.QtCore import Qt, QLine, QPointF, QLineF
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QPainterPath, QAction, QIcon, QTransform, QPalette
from PySide6.QtWidgets import (
	QGraphicsSceneMouseEvent, QLabel, QMainWindow, QApplication, QWidget,
	QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout,
	QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
	QGraphicsItem, QGraphicsPathItem, QListWidget,
	QListWidgetItem, QMenuBar, QMenu, QToolBar,
	QGraphicsItemGroup, QGraphicsTextItem,
	QGraphicsLineItem, QStyle, QLayout, QSpacerItem,
	QSizePolicy, QLineEdit, QScrollArea
)
import networkx as nx
from enum import Enum
import random
import resources_rc
import itertools
import sys
from socket import inet_ntoa
import json_export

rad = 5
NODE_RAD = 50

class ToolMode(Enum):
	SELECT=1
	MOVE=2
	CONNECT=3
	NEW=4
	DELETE=5

def createNodeNameGenerator(basename: str):
	for i in itertools.count(1, 1):
		yield f"{basename} {i}"

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

		self.setMenuBar(self.menu)
		self.setCentralWidget(self.mainWidget)
	
	def createMenuBar(self) -> QMenuBar:
		menuBar = QMenuBar()
		menus = {
			"&File": {
				"New": None,
				"Load": None,
				"Save": None,
				"Save as ...": None,
				"Export as ...": lambda: json_export.netgraph_to_json(self.mainWidget.view.scene.netgraph, "out.json") 
			},
			"&Help": {
				"Documentation": None,
				"Report a bug": None,
				"Troubleshooting": None
			}
		}
		self.actions = []
		for menu in menus.keys():
			newmenu = QMenu(menu)
			for action in menus[menu].keys():
				a = QAction(action)
				self.actions.append(a)
				# Conditional for development: Should be removed after complete menu functionality
				if menus[menu][action] != None:
					a.triggered.connect(menus[menu][action])
				newmenu.addAction(self.actions[-1])
				#newmenu.addAction(action)

			menuBar.addMenu(newmenu)

		return menuBar
	
	def createEditToolBar(self):
		self.editActions: list[QAction] = []
		toolbar = QToolBar("Edit")
		FUNCTION = 0
		ICON_PATH = 1
		actions = {
			"&Select": (lambda: self.setToolMode(ToolMode.SELECT), ":cursor.png"),
			"&Move": (lambda: self.setToolMode(ToolMode.MOVE), ":palm-of-hand.png"),
			"&Connect": (lambda: self.setToolMode(ToolMode.CONNECT), ":line.png"),
			"&New": (lambda: self.setToolMode(ToolMode.NEW), ":add.png"),
			"&Delete": (lambda: self.setToolMode(ToolMode.DELETE), ":trash.png")
		}
		for action in actions.keys():
			self.editActions.append(QAction(QIcon(actions[action][ICON_PATH]), action))
			self.editActions[-1].triggered.connect(actions[action][FUNCTION]) 

		toolbar.addActions(self.editActions)
		return toolbar
	
	def setToolMode(self, toolMode: ToolMode) -> None:
		self.view.scene.setToolMode(toolMode)


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
		QListWidgetItem("test1", self.options)
		QListWidgetItem("test2", self.options)
		QListWidgetItem("test3", self.options)
		layout.addWidget(self.options)
		layout.addWidget(self.elementViewer)
		self.setMinimumWidth(200)
		self.setLayout(layout)


class ElementViewer(QWidget):
	def __init__(self):
		super(ElementViewer, self).__init__()
		self.element: Node | Edge | None = None
		self.attributes: dict | None = None
		self.scene: SceneClass = None
		self.setAutoFillBackground(True)
		self.setPalette(QColor(255, 255, 255))
		self.setLayout(QVBoxLayout())
		self.setElement(None)
		self.setMaximumHeight(300)
		
	
	def setElement(self, element: Node | Edge | None):
		clearLayout(self.layout())
		self.element = element
		self.show()
		if type(element) == Node:
			self.setNode(element)
		elif type(element) == Edge:
			self.setEdge(element)
		else:
			self.hide()

	def setNode(self, node: Node):
		nodeName = node.getName()
		nodeInfo = self.getNodeFromScene(nodeName)["info"]
		layout = self.layout()
		layout.setSpacing(0)
		nameLabel = QLabel("Node")
		nameLabel.setAlignment(Qt.AlignmentFlag.AlignHCenter)
		nameEdit = NodeNameEditor(nodeName, self.scene)
		layout.addWidget(nameLabel)
		layout.addWidget(nameEdit)
		for i, interface in enumerate(nodeInfo["INTERFACES"]):
			ilabel = QLabel(f"Interface {i+1}:")
			layout.addWidget(ilabel)
			for k in interface.keys():
				layout.addWidget(ElementLineEditor(interface, k))
		newInterfaceButton = QPushButton(QIcon(":add.png"), "")
		newInterfaceButton.setToolTip("Add new interface")
		newInterfaceButton.clicked.connect(self.addInterface)
		layout.addWidget(newInterfaceButton)
	
	def addInterface(self):
		node: Node = self.element
		iface = {"IP": None, "MAC": "00:00:00:00:00:00"}
		node.nodeInfo["INTERFACES"].append(iface)
		inum = len(node.nodeInfo["INTERFACES"])
		layout = self.layout()
		ilabel = QLabel(f"Interface {inum}:")
		button = layout.itemAt(layout.count()-1).widget()
		layout.removeWidget(button)
		layout.addWidget(ilabel)
		for k in iface.keys():
			layout.addWidget(ElementLineEditor(iface, k))
		layout.addWidget(button)
		

	def setEdge(self, edge: Edge):
		pass

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

		layout = QHBoxLayout()
		nameEdit = QLineEdit(nodeName)
		nameEdit.editingFinished.connect(self.updateNodeName)
		layout.addWidget(QLabel(f"Name:"))
		layout.addWidget(nameEdit)
		self.setLayout(layout)
		self.nameEdit = nameEdit
	
	def updateNodeName(self):
		newName = self.nameEdit.text()
		if not self.scene.renameNode(self.nodeName, newName):
			self.nameEdit.setText(self.nodeName)
			return
		self.nodeName = newName

class ElementLineEditor(QWidget):
	def __init__(self, modDict: dict, modKey: str):
		super(ElementLineEditor, self).__init__()
		self.modDict = modDict
		self.modKey = modKey

		layout = QHBoxLayout()
		keyEdit = QLineEdit(modDict[modKey])
		keyEdit.setFixedWidth(110)
		keyEdit.editingFinished.connect(lambda: self.modDict.update({self.modKey: keyEdit.text()}))
		layout.addWidget(QLabel(f"{modKey}:"))
		layout.addWidget(keyEdit)
		self.setLayout(layout)


class ViewClass(QGraphicsView):
	def __init__(self, editMenu: EditMenu):
		super(ViewClass, self).__init__()

		self.setDragMode(QGraphicsView.RubberBandDrag)

		self.scene = SceneClass(editMenu)
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
		editMenu.elementViewer.setScene(self)
		self.ipv4gen = createIPv4Generator()
		self.macaddrgen = createMACAddrGenerator()

		self.onclick = None
		self.nodeNameGenerators = self.createNodeNameGenerators(["Host", "VNF"])
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
					if u != v:
						self.connectNodes(v, u)
		
	def getToolFunction(self):
		return self.toolFunctions[self.toolMode.value]
	
	def getNewIPv4addr(self):
		return next(self.ipv4gen)
	
	def getNewMACaddr(self):
		return next(self.macaddrgen)
	
	def addNode(self, id: str, position: QPointF, nodeInfo: dict = {}) -> Node:
		node = Node(id, nodeInfo)
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
		return self.addNode(self.getNodeName("Host"), position, {
			"INTERFACES": [
				{"IP": self.getNewIPv4addr(), "MAC": self.getNewMACaddr()},
			]})
	
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
		self.addDefaultHostNode(event.scenePos())

	def connectNodes(self, u: Node, v: Node, edgeInfo={}) -> Edge:
		if self.netgraph.has_edge(u.getName(), v.getName()):
			return None
		edge = Edge(u, v)
		self.netgraph.add_edge(u.getName(), v.getName(), obj=self, info=edgeInfo)
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
		return next(self.nodeNameGenerators[nodeType])
	
	def remove(self, obj: Node | Edge):
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


class Node(QGraphicsEllipseItem):
	def __init__(self, id: str, nodeInfo: dict = {}):
		# Using -NODE_RAD for the x and y of the bounding rectangle aligns the rectangle at the center of the node
		super(Node, self).__init__(-NODE_RAD, -NODE_RAD, 2*NODE_RAD, 2*NODE_RAD)

		# Instantiate the text object
		self.text = QGraphicsTextItem(id, parent=self)
		self.setName(id)
		self.nodeInfo = nodeInfo
		
		self.edges: list[Edge] = []
		
		self.setFlag(QGraphicsItem.ItemIsMovable)
		self.setFlag(QGraphicsItem.ItemIsSelectable)
		self.setZValue(1)
		self.setBrush(QColor(35, 158, 207))
	
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
		self.edges.remove(edge)

	
class Edge(QGraphicsLineItem):
	def __init__(self, u: Node, v: Node, edgeInfo: dict = {}):
		super(Edge, self).__init__(QLineF(u.pos(), v.pos()))
		self.nodes = (u, v)
		pen = QPen()
		pen.setWidth(3)
		self.setPen(pen)
		self.setFlag(QGraphicsItem.ItemIsSelectable)

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


class Path(QGraphicsPathItem):
	def __init__(self, path, scene):
		super(Path, self).__init__(path)
		for i in range(path.elementCount()):
			node = Node(self, i)
			node.setPos(QPointF(path.elementAt(i)))
			scene.addItem(node)
		self.setPen(QPen(Qt.red, 1.75))        

	def updateElement(self, index, pos):
		path = self.path()
		path.setElementPositionAt(index, pos.x(), pos.y())
		self.setPath(path)


app = QApplication()

window = WindowClass()
window.show()

app.exec()
