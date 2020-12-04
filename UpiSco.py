from PyQt4.QtCore import *
from PyQt4.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import *
import pyqtgraph as pg
#import glob
import time, threading, sys
import serial
import numpy as np

class UpiCodec(object):
	def __init__(self, title , conv, val = "(.*)*" ):
		super(UpiCodec, self).__init__()
		self.title = title
		self.handle = conv
		self.validator = QRegExpValidator(QRegExp(val))
		
class DataInput(QtGui.QDialog):
	""" Takes input as ascii, interpretes it from selected code format to binary format, and drows a pyqtgrafh PlotCurveItem"""
	lenght = 1204
	inPut = np.zeros(lenght)
	outPut = np.zeros(lenght*4)
	c = None
	def __init__(self):#, parent, lenght=1024, chunks=5000):
		super(DataInput, self).__init__()
		QDialog.__init__(self)
		self.codec_list = [UpiCodec('Hexa', self.hexa,val = "(?:[0-9a-fA-F][0-9a-fA-F]:)*") ,UpiCodec('ASCII', self.ascii)]    
		self.setAttribute(Qt.WA_DeleteOnClose, True)
		l = QFormLayout()
		self.setLayout(l)
		sel = QComboBox()
		self.inPut = QLineEdit()
		self.inPut.textChanged.connect(self.convert)
		self.inPut.returnPressed.connect(self.send)
		sel.currentIndexChanged.connect(self.setCodec)
		sel.addItems(['Hexa', 'ASCII', 'binary'])
		l.addRow('Input Codec', sel)
		l.addRow('Input Data', self.inPut)
		self.inPut.setFocus()
		self.show()

	def setCodec(self, a):
		'''select converter used for interpret text to binary'''
		convs = [self.hexa, self.ascii, self.binary]
		v = ["(?:[0-9a-fA-F][0-9a-fA-F]:)*", "(.*)*", "([0-1]{8}:)*"]
		#self.val = QRegExpValidator(QRegExp(self.codec[a].validator))
		self.codec = self.codec_list[a]
		#self.val = self.codec_list[a].validator
		self.inPut.setValidator(self.codec.validator)
		#self.converter = convs[a]
		self.inPut.setFocus()
		
	def convert(self, text):
		'''runs the selected converter each time text has changed'''
		c = ['#f6989d', '#fff79a', '#c4df9b']
		self.inPut.setStyleSheet('QLineEdit { background-color: %s }' % c[self.codec.validator.validate(text, 0)[0]])
		#array = self.converter(text)
		array = self.codec.handle(text)
		print 'array', array
		array = ["{0:08b}".format(c) for c in array]
		#array = bin(array)
		print 'binrep', array

	def hexa(self, text):
		print 'hexa: ', text
		string = str(text)
		array = []
		for i in np.arange(len(string)):
			if string[i] is ':':
				array.append(int(string[i-2:i],16))
		return array
		
	def ascii(self, text):
		string = unicode(text, 'ascii', errors = 'ignore')
		print 'ASCII', string
		array = []
		for i in np.arange(len(string)):
			array.append(ord(string[i]))
		return array

	def binary(self, text):
		print 'binary: ', text
		string = str(text)
		array = []
		for i in np.arange(len(string)):
			if string[i] is ':':
				array.append(int(string[i-8:i],2))
		return array

		
	def binarify(self, arr):
		print 'Binarifying', arr
		
	def send(self):
		print 'send'
		

