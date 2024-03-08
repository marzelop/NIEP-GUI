#!./venv/bin/python
from PySide6.QtCore import Qt, QLine, QPointF
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QPainterPath
from PySide6.QtWidgets import (
	QLabel, QMainWindow, QApplication, QWidget,
	QVBoxLayout, QPushButton, QGridLayout,
	QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsItem, QGraphicsPathItem
)
import networkx as nx
import network as net
import random

rad = 5
'''
class Node(QLabel):
	def __init__(self, text: str):
		super().__init__()
		self.setText(text)
		#self.setStyleSheet("border: 2px solid black; border-radius: 50%;")
		

class AppMainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		self.netG = net.loadTopologyGraph("ServerClient.json")
		font = QFont()
		font.setPixelSize(30)
		self.view = self.createView()
		layout = QGridLayout()
		positions = [(0, 0), (1, 1), (0, 2)]
		for i, node in enumerate(list(self.netG.nodes)):
			layout.addWidget(Node(node), positions[i][0], positions[i][1])
			print(node)
		self.view.setLayout(layout)
		self.setCentralWidget(self.view)

	def createScene(self):
		scene = QGraphicsScene()
		scene.setSceneRect(-1000, -1000, 1000, 1000)
		scene.grid = 40
		scene.it = None
		scene.node = None

		return scene

	def createView(self):
		view = QGraphicsView()
		view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
		view.scene = self.createScene()

		return view
	
'''

class WindowClass(QMainWindow):
    def __init__(self):
        super(WindowClass, self).__init__()
        self.view = ViewClass()
        self.setCentralWidget(self.view)


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
        self.setSceneRect(-2000, -2000, 2000, 2000)
        self.grid = 40
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
