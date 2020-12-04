from PyQt4.QtCore import QRegExp, pyqtSignal
from PyQt4.QtGui import QRegExpValidator, QComboBox, QWidget, QCheckBox, QHBoxLayout
import numpy as np

binRegExp = "([0-1]{8}:)*"
asciiRegExp = "(.*)*"
hexRegExp = "(?:[0-9a-fA-F][0-9a-fA-F]:)*"
desimalRegExp = "(-?(0|([1-9]\d*))(\.\d+)?:)*" # To Do

def hexa(text):
	string = str(text)
	array = []
	for i in np.arange(len(string)):
		if string[i] is ':':
			array.append(int(string[i-2:i],16))
	return array
	
def ascii(text):
	string = unicode(text, 'ascii', errors = 'ignore')
	array = []
	for i in np.arange(len(string)):
		array.append(ord(string[i]))
	return array

def bin(text):
	string = str(text)
	array = []
	for i in np.arange(len(string)):
		if string[i] is ':':
			array.append(int(string[i-8:i],2))
	return array

class EnCoder(object):
	def __init__(self, title, handle):
		super(EnCoder, self).__init__()
		self.title = title
		self.handle = handle

class Codec(EnCoder):
	def __init__(self, title , handle, val = asciiRegExp ):
		EnCoder.__init__(self, title, handle)
		#self.title = title
		#self.handle = handle
		self.validator = QRegExpValidator(QRegExp(val))
		
def binEC(a, **kwargs):
	arr = a.copy()
	level = kwargs['level']
	bi = kwargs['bipolar']
	for i in range(len(arr)):
		if arr[i] == 1:
			arr[i] = level
		elif bi == True:
			arr[i] = -level
	return arr

def amiEC(a, **kwargs):
	arr = a.copy()
	level = kwargs['level']
	for i in range(len(arr)):
		if arr[i] == 1:
			arr[i] = arr[i]*level
			level = -level
	return arr

#Text Codecs
hexaCodec = Codec('Hexa', hexa, val = hexRegExp)
binCodec = Codec('binary', bin, val = binRegExp)
asciiCodec = Codec('ASCII', ascii, val = asciiRegExp)
desimalCodec = Codec('Desimal', ascii, val = desimalRegExp)# To Do !!!-----------!!!!
textCodecs = [asciiCodec, hexaCodec, binCodec, desimalCodec]# Collection of text Codecs

#Encoder Codecs
binaryEnCodec = EnCoder('Binary', binEC)
amiEnCodec = EnCoder('Ami', amiEC)

class CodecSelector(QHBoxLayout):
	codecChanged = pyqtSignal(EnCoder)
	checked = pyqtSignal(int)
	List = []
	def __init__(self, cod = [], **kwargs):
		super(CodecSelector, self).__init__()
		ctitle = kwargs['CTitle']
		self.combo = QComboBox()
		self.check = QCheckBox(ctitle)
		self.combo.currentIndexChanged.connect(self.choiceCodec)
		self.check.stateChanged.connect(self.checked.emit)
		self.addWidget(self.combo)
		self.addWidget(self.check)
		self.setCodec(cod)
		
	def choiceCodec(self, a):
		self.codecChanged.emit(self.List[a])
		
	def addCodec(self,lst ):
		for c in lst:
			self.List.append(c)
			self.combo.addItems([c.title])
			
	def setCodec(self,lst ):
		self.List = lst
		for c in lst:
			self.combo.addItems([c.title])

	def get(self):
		return self.List[self.combo.currentIndex()]

class TextCodecSelector(CodecSelector):
	def __init__(self, cod = textCodecs, **kwargs):
		CodecSelector.__init__(self, cod = cod, **kwargs)
			
class EnCoderCodecSelector(CodecSelector):
	def __init__(self, cod = [amiEnCodec, binaryEnCodec], **kwargs):
		CodecSelector.__init__(self, cod = cod, **kwargs)


