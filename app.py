#!./venv/bin/python
from PySide6.QtCore import Qt, QLine, QPointF
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QPainterPath, QAction, QIcon
from PySide6.QtWidgets import (
	QLabel, QMainWindow, QApplication, QWidget,
	QVBoxLayout, QHBoxLayout, QPushButton, QGridLayout,
	QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
	QGraphicsItem, QGraphicsPathItem, QListWidget,
	QListWidgetItem, QMenuBar, QMenu, QToolBar
)
import networkx as nx
import network as net
import random
import resources_rc

rad = 5

class WindowClass(QMainWindow):
	def __init__(self):
		super(WindowClass, self).__init__()
		self.setWindowTitle("NIEP GUI")
		self.mainWidget = MainWidget()
		self.menuBar = self.createMenuBar()
		#self.addToolBar(TopMenu())
		self.edittoolbar = self.createToolBar()
		self.addToolBar(self.edittoolbar)
		print(self.edittoolbar.actions())


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
	
	def createToolBar(self):
		self.editActions = []
		toolbar = QToolBar("Edit")
		ICON_PATH = 1
		actions = {
			"&Select": (self.testf, ":cursor.png"),
			"&Move": (self.testf, ":palm-of-hand.png"),
			"&Connect": (self.testf, ":line.png")
		}
		for action in actions.keys():
			print("Atumalaca")
			self.editActions.append(QAction(QIcon(actions[action][ICON_PATH]), action))
			print(self.editActions)
			#newAction = QAction(action)

		toolbar.addActions(self.editActions)
		return toolbar

	def testf(self):
		print(self.sender().text())


class MainWidget(QWidget):
	def __init__(self):
		super(MainWidget, self).__init__()
		layout = QVBoxLayout()
		layout.addWidget(EVWrapper())
		self.setLayout(layout)


class TopMenu(QToolBar):
	def __init__(self):
		super(TopMenu, self).__init__("Edit")
		ICON_PATH = 1
		actions = {
			"&Select": (self.testf, ":cursor.png"),
			"&Move": (self.testf, ":palm-of-hand.png"),
			"&Connect": (self.testf, ":line.png")
		}
		for action in actions.keys():
			newAction = QAction(QIcon(actions[action][ICON_PATH]), action)
			#newAction = QAction(action)

			self.addAction(newAction)

	def testf(self):
		print(self.sender().text())
		

class EVWrapper(QWidget):
	'''
	Class to encapsulate the EditMenu and ViewClass into one widget.
	'''
	def __init__(self):
		super(EVWrapper, self).__init__()
		layout = QHBoxLayout()
		layout.addWidget(EditMenu())
		layout.addWidget(ViewClass())
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
		# self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		# self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

		self.s = SceneClass()
		self.setScene(self.s)
		self.setRenderHint(QPainter.Antialiasing)


class SceneClass(QGraphicsScene):
	def __init__(self, id=None):
		super(SceneClass, self).__init__()
		self.setSceneRect(-500, -500, 1000, 1000)
		self.grid = 25
		self.it = None
		self.node = None

	def drawBackground(self, painter, rect):
		if False:
			painter = QPainter()
			rect = QRect()

		painter.fillRect(rect, QColor(30, 30, 30))
		left = int(rect.left()) - int((rect.left()) % self.grid)
		top = int(rect.top()) - int((rect.top()) % self.grid)
		right = int(rect.right())
		bottom = int(rect.bottom())
		lines = []
		for x in range(left, right, self.grid):
			lines.append(QLine(x, top, x, bottom))
		for y in range(top, bottom, self.grid):
			lines.append(QLine(left, y, right, y))
		painter.setPen(QPen(QColor(50, 50, 50)))
		painter.drawLines(lines)

	def mousePressEvent(self, event):
		if event.button() == Qt.RightButton:
			path = QPainterPath()
			path.moveTo(event.scenePos() + QPointF(random.randint(-100, 100), random.randint(-100, 100)))
			path.lineTo(event.scenePos())
			self.addItem(Path(path, self))
		super(SceneClass, self).mousePressEvent(event)

class Node(QGraphicsEllipseItem):
	def __init__(self, path, index):
		super(Node, self).__init__(-rad, -rad, 2*rad, 2*rad)

		self.rad = rad
		self.path = path
		self.index = index

		self.setZValue(1)
		self.setFlag(QGraphicsItem.ItemIsMovable)
		self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
		self.setBrush(Qt.green)

	def itemChange(self, change, value):
		if change == QGraphicsItem.ItemPositionChange:
			self.path.updateElement(self.index, value)
		return QGraphicsEllipseItem.itemChange(self, change, value)


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
