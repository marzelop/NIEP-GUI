#!./venv/bin/python
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
	QLabel, QMainWindow, QApplication, QWidget,
	QVBoxLayout, QPushButton, QGridLayout
)
import networkx as nx
import network as net

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
		base = QWidget()
		base.setFont(font)
		layout = QGridLayout()
		positions = [(0, 0), (1, 1), (0, 2)]
		for i, node in enumerate(list(self.netG.nodes)):
			layout.addWidget(Node(node), positions[i][0], positions[i][1])
			print(node)
		base.setLayout(layout)
		self.setCentralWidget(base)


app = QApplication()

window = AppMainWindow()
window.show()

app.exec()
