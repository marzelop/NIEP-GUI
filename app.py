#!./venv/bin/python
from __future__ import annotations
from PySide6.QtCore import Qt, QLine, QPointF, QLineF
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QPainterPath, QAction, QIcon
from PySide6.QtWidgets import (
	QGraphicsSceneMouseEvent, QLabel, QMainWindow, QApplication, QWidget,
	QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout,
	QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
	QGraphicsItem, QGraphicsPathItem, QListWidget,
	QListWidgetItem, QMenuBar, QMenu, QToolBar,
	QGraphicsItemGroup, QGraphicsTextItem,
	QGraphicsLineItem
)
import networkx as nx
import network as net
from enum import Enum
import random
import resources_rc

rad = 5
NODE_RAD = 45

class ToolMode(Enum):
	SELECT=1
	MOVE=2
	CONNECT=3
	NEW=4

class WindowClass(QMainWindow):
	def __init__(self):
		super(WindowClass, self).__init__()
		self.setWindowTitle("NIEP GUI")
		self.mainWidget = MainWidget()
		self.editMenu = self.mainWidget.editMenu
		self.view = self.mainWidget.view
		self.menuBar = self.createMenuBar()
		self.editToolbar = self.createEditToolBar()
		self.addToolBar(self.editToolbar)

		self.setMenuBar(self.menuBar)
		self.setCentralWidget(self.mainWidget)
	
	def createMenuBar(self) -> QMenuBar:
		menuBar = QMenuBar()
		menus = {
			"&File": {
				"New": None,
				"Load": None,
				"Save": None,
				"Save as ...": None,
				"Export as ...": None
			},
			"&Help": {
				"Documentation": None,
				"Report a bug": None,
				"Troubleshooting": None
			}
		}

		for menu in menus.keys():
			newmenu = QMenu(menu)
			for action in menus[menu].keys():
				newmenu.addAction(action)
			menuBar.addMenu(newmenu)

		return menuBar
	
	def createEditToolBar(self):
		self.editActions = []
		toolbar = QToolBar("Edit")
		ICON_PATH = 1
		actions = {
			"&Select": (self.testf, ":cursor.png"),
			"&Move": (self.testf, ":palm-of-hand.png"),
			"&Connect": (self.testf, ":line.png"),
			"&New": (self.testf, ":add.png")
		}
		for action in actions.keys():
			self.editActions.append(QAction(QIcon(actions[action][ICON_PATH]), action))

		toolbar.addActions(self.editActions)
		return toolbar

	def testf(self):
		print(self.sender().text())


class MainWidget(QWidget):
	def __init__(self):
		super(MainWidget, self).__init__()
		self.editMenu = EditMenu()
		self.view = ViewClass()
		layout = QHBoxLayout()
		layout.addWidget(self.editMenu)
		layout.addWidget(self.view)
		self.setLayout(layout)


class EditMenu(QWidget):
	def __init__(self):
		super(EditMenu, self).__init__()
		layout = QVBoxLayout()
		self.options = QListWidget()
		QListWidgetItem("test1", self.options)
		QListWidgetItem("test2", self.options)
		QListWidgetItem("test3", self.options)
		layout.addWidget(self.options)
		self.setLayout(layout)


class ViewClass(QGraphicsView):
	def __init__(self):
		super(ViewClass, self).__init__()

		self.setDragMode(QGraphicsView.RubberBandDrag)

		self.s = SceneClass()
		self.setScene(self.s)
		self.setRenderHint(QPainter.Antialiasing)
	
	def zoom(self, angleDelta: int, center: QPointF):
		if (angleDelta < 0):
			factor = 1/(1.0 + abs(angleDelta)*0.008)
		else: factor = (1.0 + angleDelta*0.008)
		self.centerOn(center)
		self.scale(factor, factor)


class SceneClass(QGraphicsScene):
	def __init__(self, id=None):
		super(SceneClass, self).__init__()
		self.setSceneRect(-500, -500, 1000, 1000)
		self.grid = 40
		self.netgraph = nx.Graph()

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
		if event.button() == Qt.RightButton:
			node = self.addNode("Cliente", event.scenePos())
			node2 = self.addNode("Servidor", event.scenePos() + QPointF(100, 100))
			edge = self.connectNodes(node, node2)
		super(SceneClass, self).mousePressEvent(event)
	
	def addNode(self, id: str, position: QPointF, nodeInfo: dict = {}) -> Node:
		node = Node(id, nodeInfo)
		self.netgraph.add_node(id, obj=node, info=nodeInfo)
		node.setPos(position)
		self.addItem(node)

		return node
	
	def connectNodes(self, u: Node, v: Node, edgeInfo={}) -> Edge:
		edge = Edge(u, v)
		self.netgraph.add_edge(u, v, obj=self, info=edgeInfo)
		u.addEdge(edge)
		v.addEdge(edge)
		self.addItem(edge)

		return edge


class Node(QGraphicsEllipseItem):
	def __init__(self, id: str, nodeInfo: dict = {}):
		# Using -NODE_RAD for the x and y of the bounding rectangle aligns the rectangle at the center of the node
		self.i = 0
		super(Node, self).__init__(-NODE_RAD, -NODE_RAD, 2*NODE_RAD, 2*NODE_RAD)

		# Instantiate the text object
		self.text = QGraphicsTextItem(id, parent=self)
		# Set max text width to 90% of node diameter
		self.text.setTextWidth(min(0.9*2*NODE_RAD, self.text.boundingRect().width())) 
		# Centers it within the ellipse
		self.text.setX(-self.text.boundingRect().width()/2)
		self.text.setY(-self.text.boundingRect().height()/2)
		
		self.edges: list[Edge] = []
		
		self.setFlag(QGraphicsItem.ItemIsMovable)
		self.setFlag(QGraphicsItem.ItemIsSelectable)
		self.setZValue(-1)
		self.setBrush(QColor(35, 158, 207))
	
	def getName(self) -> str:
		return self.text.toPlainText()
	
	def addEdge(self, edge: Edge) -> None:
		self.edges.append(edge)
	
	def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
		for edge in self.edges:
			edge.updateLine()
		return super().mouseMoveEvent(event)

	

class Edge(QGraphicsLineItem):
	def __init__(self, u: Node, v: Node, edgeInfo: dict = {}):
		super(Edge, self).__init__(QLineF(u.pos(), v.pos()))
		self.nodes = (u, v)
		pen = QPen()
		pen.setWidth(3)
		self.setPen(pen)

		self.setZValue(0.5)
	
	def updateLine(self):
		self.setLine(QLineF(self.nodes[0].pos(), self.nodes[1].pos()))


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
