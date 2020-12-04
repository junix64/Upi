from PyQt4.QtCore import *
from PyQt4.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import *
import pyqtgraph as pg
#import glob
import time, threading, sys
import serial
import numpy as np
import codec as UpiCodec

class MainWindow(QtGui.QMainWindow):
	pmax = 1
	dH = 250		#dockHight
	dW = 1200		#dockWidht
	dockCount = 0
	threads = []
	
	def __init__(self, parent = None):
		super(MainWindow, self).__init__()
		self.setAttribute(Qt.WA_DeleteOnClose, True)
		self.a = DockArea()
		self.setCentralWidget(self.a)
		self.port = QStringList()
		self.resize(self.dW, self.dH)
		self.show()

	'''def newIn (self, title, In):		
		t = ThreadPlotter(self, title, In)
		self.threads.append(t)'''
		
			
	def addDock(self, p, d1 = None, title = ''):
		d = self.a.addDock(Dock(title, size=(800,200), closable=True),'bottom', d1)
		d.label.sigCloseClicked.connect(lambda d=d, p=p: self.rmDock(d,p))
		self.dockCount += 1
		#self.resize(self.frameGeometry().width(), self.dH*self.dockCount)#(self.dW, self.dH*self.dockCount)
		return d
	
	def rmDock(self,d,p):
		self.dockCount -= 1
		#self.resize(self.frameGeometry().width(), self.dH*self.dockCount)
		p.exit()
			
		
	def closeEvent(self, b):
		print 'Upiscope closeEvent()'
		#exit all threads
		for t in self.threads:
			t.exit()

class SignalGenerator(MainWindow):
	color = ['r','y','g','b','c','k','w','m']#['#f6989d', '#fff79a', '#c4df9b']
	sigUpiGet = pyqtSignal([])
	def __init__(self, title):
		super(SignalGenerator, self).__init__()
		#MainWindow.__init__(self)
		self.setWindowTitle(title) 
		l = QFormLayout()
		self.w = QtGui.QDialog()
		self.w.setLayout(l)
		dock = self.addDock(None, None, 'Signal Format')
		self.inPut = UpiLogicalLayer(LayOut = l)
		self.inPut.sigUpiGet.connect(self.handle)
		dock.addWidget(self.w)
		self.pl = pg.PlotWidget()
		self.legend = self.pl.addLegend()
		dock.addWidget(self.pl, col=1, row = 0)
		self.inPut.inPut.setFocus()
		self.sender = UpiSignalSender(LayOut = l)
		
	def handle(self, a):
		data = a
		self.pl.clear()
		self.legend.scene().removeItem(self.legend)
		self.legend = self.pl.addLegend()
		for i in range(len(data)):
			d = data[i]['data']
			t = data[i]['codec']
			curve = pg.PlotCurveItem(range(len(d)+1), d, clear=True, stepMode=True, pen=(self.color[i]), name = t)
			if len(d) > 0:
				self.pl.addItem(curve)
			if data[i]['title'] is 'Output':
				self.data = d

class UpiLineEdit(QLineEdit):
	color = ['#f6989d', '#fff79a', '#c4df9b']
	sigUpiGet = pyqtSignal(str)
	def __init__(self, val = UpiCodec.asciiRegExp):
		QLineEdit.__init__(self)
		self.returnPressed.connect(self.handle)
		self.textChanged.connect(self.check)
		self.setValidator(QRegExpValidator(QRegExp(val)))
		
	def setmode(self,c):
		self.setFocus()
		if c == 0:
			self.textChanged.disconnect(self.handle)
			self.returnPressed.connect(self.handle)
		elif c == 2:
			self.textChanged.connect(self.handle)
			self.returnPressed.disconnect(self.handle)
		else:
			pass
		
	def check(self):
		self.setStyleSheet('QLineEdit { background-color: %s }' % self.color[self.validator().validate(self.text(), 0)[0]])
			
	def handle(self):
		self.sigUpiGet.emit(self.text())
		
'''	def get(self):
		return self.text()'''
		
class UpiLogicalLayer(QtGui.QDialog):
	""" Takes input as ascii, interpretes it from selected code format to binary format, and drows a pyqtgrafh PlotCurveItem"""
	sigUpiGet = pyqtSignal(list)
	srcCodec = None
	enCodec = None
	text = ''
	level = 1
	bipolar = False
	def __init__(self, LayOut = QFormLayout(), **kwargs):
		super(UpiLogicalLayer, self).__init__()
		QDialog.__init__(self)
		self.setAttribute(Qt.WA_DeleteOnClose, True)
		l = LayOut#kwargs['LayOut']
		self.inPut = UpiLineEdit()
		self.inPut.sigUpiGet.connect(self.handle)
		self.srcSel = UpiCodec.TextCodecSelector(CTitle = 'Update')
		self.srcSel.codecChanged.connect(self.setSrcCodec)
		self.enCodSel = UpiCodec.EnCoderCodecSelector(CTitle = 'Bipolar')
		self.enCodSel.codecChanged.connect(self.setEnCodec)
		self.srcSel.checked.connect(self.inPut.setmode)
		self.enCodSel.checked.connect(self.setPolarity)
		self.srcCodec = self.srcSel.get()
		self.enCodec = self.enCodSel.get()
		self.srcSel.check.setChecked(True)
		l.addRow('Select Codec', self.srcSel)
		l.addRow('Select Encoder', self.enCodSel)
		l.addRow('Input Data', self.inPut)
		
	def setPolarity(self, c):
		if c == 0:
			self.bipolar = False
		elif c == 2:
			self.bipolar = True
		else:
			pass
		self.signalize()
		self.inPut.setFocus()
		
	def setLevel(self, a):
		self.level = a
		self.signalize()


	def setSrcCodec(self, a):
		'''select Upi.Codec used for interpret string to binary'''
		self.srcCodec = a
		self.inPut.setValidator(self.srcCodec.validator)
		self.inPut.setFocus()

	def setEnCodec(self, a):
		'''select Upi.Codec used for encode data'''
		self.enCodec = a
		self.signalize()
		self.inPut.setFocus()
		
	def handle(self, t):
		'''Gets data from input runs the selected Codec.handle each time text is changed'''
		self.text = t
		self.signalize()
		
	def signalize(self):
		t = self.text
		l = self.level
		bi = self.bipolar
		t = self.srcCodec.handle(t)
		t = ''.join(["{0:08b}".format(c) for c in t])
		t = np.array(map(float, t))
		inp = {'title':'Input', 'codec':self.srcCodec.title,'data':t}
		out = {'title':'Output', 'codec':self.enCodec.title, 'data':np.array(self.enCodec.handle(t, level = l, bipolar = bi))}
		data = [inp,out]
		self.sigUpiGet.emit(data)
		
'''	def get (self):
			return self.data'''
			
class UpiSignalSender(QHBoxLayout):
	def __init__(self, LayOut = QFormLayout(), **kwargs):
		super(UpiSignalSender, self).__init__()
		l = LayOut#kwargs['LayOut']
		g = QGroupBox()
		sl = QSlider(Qt.Horizontal, minimum = 0, maximum = 1000)
		sl.valueChanged.connect(self.Setlevel)
		self.sll = QLabel("Signal Level:")
		vbox = QVBoxLayout()
		vbox.addWidget(sl)
		vbox.addWidget(self.sll)
		g.setLayout(vbox)
		self.addWidget(g)
		f = QGroupBox()
		br=QSlider(Qt.Horizontal, minimum = 0, maximum = 1000)
		br.valueChanged.connect(self.Setbr)
		self.brl = QLabel("Baud Rate:")
		vvbox = QVBoxLayout()
		vvbox.addWidget(br)
		vvbox.addWidget(self.brl)
		f.setLayout(vvbox)
		self.addWidget(f)
		l.addRow(self)
		
	def Setlevel(self, a):
		self.sll.setText("Signal Level: "+str(float(a)/10)+"V")
		
	def Setbr(self, a):
		self.brl.setText("Baude Rate: "+str(a)+" kbaud")


class Connection(object):
	sigUpiGet = pyqtSignal()	
	def __init__(self, inp):
		super(Connection, self).__init__()
		self.inp = inp
		self.inp.sigUpiGet.connect(self.handle())
	
	def handle(self):
		self.data = self.inp.get()
		sigUpiGet.emit()
		

		
		



