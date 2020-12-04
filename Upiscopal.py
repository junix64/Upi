#from PyQt4 import QtGui
#from PyQt4 import QtCore
#import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.dockarea import *
import pyqtgraph as pg
import glob
import time, threading, sys
import serial
import numpy as np



class SerialReader(threading.Thread):
    """ Defines a thread for reading and buffering serial data.
    By default, about 5MSamples are stored in the buffer.
    Data can be retrieved from the buffer by calling get(N)"""
    def __init__(self, In, chunkSize=1024, chunks=5000):
        threading.Thread.__init__(self)
        #print 'SerialReader.init: ',self
        # circular buffer for storing serial data until it is 
        # fetched by the GUI
        self.buffer = np.zeros(chunks*chunkSize, dtype=np.uint16)
        self.chunks = chunks        # number of chunks to store in the buffer
        self.chunkSize = chunkSize  # size of a single chunk (items, not bytes)
        self.ptr = 0                # pointer to most (recently collected buffer index) + 1
        self.dataIn = In            # serial port handle
        self.sps = 0.0              # holds the average sample acquisition rate
        self.exitFlag = False
        self.exitMutex = threading.Lock()
        self.dataMutex = threading.Lock()
        
    def run(self):
        exitMutex = self.exitMutex
        dataMutex = self.dataMutex
        buffer = self.buffer
        port = self.In
        count = 0
        sps = None
        lastUpdate = pg.ptime.time()
        
        while True:
            # see whether an exit was requested
            with exitMutex:
                if self.exitFlag:
                    break
            
            # read one full chunk from the serial port
            data = dataIn.read(self.chunkSize*2)
            # convert data to 16bit int numpy array
            data = np.fromstring(data, dtype=np.uint16)
            
            # keep track of the acquisition rate in samples-per-second
            count += self.chunkSize
            now = pg.ptime.time()
            dt = now-lastUpdate
            if dt > 1.0:
                # sps is an exponential average of the running sample rate measurement
                if sps is None:
                    sps = count / dt
                else:
                    sps = sps * 0.9 + (count / dt) * 0.1
                count = 0
                lastUpdate = now
                
            # write the new chunk into the circular buffer
            # and update the buffer pointer
            with dataMutex:
                buffer[self.ptr:self.ptr+self.chunkSize] = data
                self.ptr = (self.ptr + self.chunkSize) % buffer.shape[0]
                if sps is not None:
                    self.sps = sps
                
                
    def get(self, num, downsample=1):
        """ Return a tuple (time_values, voltage_values, rate)
          - voltage_values will contain the *num* most recently-collected samples 
            as a 32bit float array. 
          - time_values assumes samples are collected at 1MS/s
          - rate is the running average sample rate.
        If *downsample* is > 1, then the number of values returned will be
        reduced by averaging that number of consecutive samples together. In 
        this case, the voltage array will be returned as 32bit float.
        """
        with self.dataMutex:  # lock the buffer and copy the requested data out
            ptr = self.ptr
            if ptr-num < 0:
                data = np.empty(num, dtype=np.uint16)
                data[:num-ptr] = self.buffer[ptr-num:]
                data[num-ptr:] = self.buffer[:ptr]
            else:
                data = self.buffer[self.ptr-num:self.ptr].copy()
            rate = self.sps
        
        # Convert array to float and rescale to voltage.
        # Assume 3.3V / 12bits
        # (we need calibration data to do a better job on this)
        data = data.astype(np.float32) * (3.3 / 2**12)
        if downsample > 1:  # if downsampling is requested, average N samples together
            data = data.reshape(num/downsample,downsample).mean(axis=1)
            num = data.shape[0]
            return np.linspace(0, (num-1)*1e-6*downsample, num), data, rate
        else:
            return np.linspace(0, (num-1)*1e-6, num), data, rate
    
    def exit(self):
        """ Instruct the serial thread to exit."""
        print 'Serial Reader exit()'
        with self.exitMutex:
            self.exitFlag = True

#--------------------------------------------------------------
# class for plotting data from thread
class UpiDigitizer(pg.GraphicsView):

	def __init__(self, time, data, parent, **kwargs):
		super(UpiDigitizer, self).__init__(parent)
		print 'UpiDigitizer init():'
		self.setAttribute(Qt.WA_DeleteOnClose)
		#self.timer = pg.QtCore.QTimer()
		self.l = pg.GraphicsLayout(border=(0,100,100))
		self.setCentralItem(self.l)
		self.data = data
		self.time = time
		self.bins = 20
		self.info = {'Bin count':self.bins}
		#self.console = self.addWidget(pg.console.ConsoleWidget())
		self.h1 = self.l.addPlot()#(col=1)
		self.p1 = self.l.addPlot()#(col=2)
		self.p1.scene().sigMouseClicked.connect(self.st)
		#self.timer.start(0)
		self.controls = [{'class':'zoom','obj':None}]
		self.digits = self.digitize()
		self.filter(self.digits)

	def st(self):
		print 'st:'
		
	def digitize(self):
		print 'digitize():'
		info = {}
		dig = []
		l = []
		show = True
		a = False
		y,x = np.histogram(self.data, bins=np.linspace(np.min(self.data),np.max(self.data),self.bins))
		#---- Minus least square sum methode - Bipolar and Multilevel -----------------------------
		f = 1.3 #factor for sifting trendline right
		t = np.polyfit(x[:-1], y*f, 2)#compute factors for trendline
		p = np.poly1d(t)#trendline formula
		z = y-p(x[:-1])
		if show:
			delta = pg.PlotCurveItem(-x, z, stepMode=True, fillLevel=0, brush= (255, 0, 0, 100))
			delta.rotate (-90)
			trend = pg.PlotCurveItem(-x, p(x), stepMode=False, fillLevel=0)#, brush= (255, 0, 0, 10))
			trend.rotate(-90)
			hist = pg.PlotCurveItem(-x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 10))
			hist.rotate(-90)
			self.h1.clear()
			self.h1.addItem(trend)			
			self.h1.addItem(hist)
			self.h1.addItem(delta)
			print 'Trendline formula:',p
		for i in range(len(z)-1):
			if z[i] > 0 and z[i+1] <= 0 and not a:
				l.append(x[i+1])
				a = True
				#print i,'a:',z[i],z[i+1], l
			if (z[i+1] > 0) and (z[i] <= 0) and a:
				l.append(x[i-1])
				a = False
				#print i,'b:',z[i+1],z[i], l
				self.controls.append({'class':'digits', 'obj':None, 'index':len(dig)})
				dig.append(l)
				l = []
			#print l
				
		#---- Bigest square sum methode - Unpolar--------------------------
		'''z = np.argsort(-y)
		s = -np.sort(-y)
		A = len(y)*s[0]
		l = [z[0],0]	#indices for chosen unipolar levels
		area = float(0)
		amax = float(0)
		print 'i:\t','y:\t','z:\t','c:\t','d:\t','area:\t','A=',A

		for i in range(1,len(s)-1):
			l1=l[0]
			c = abs(l1-z[i])
			d = float(s[0])*c
			e = float(s[i])*c
			if e > area:
			#if d > area:
				amax = d
				area = e
				l[1] = z[i]
			#print i,'\t',y[z[i]],'\t',z[i],'\t',c,'\t',d,'\t',area,'\t',l#(float(a)/A)*100,'%

		l.sort()
		l[0]+=1
		info['Noise'] = [l[0],len(y)-l[1]]
		self.controls.append({'class':'digits', 'obj':None, 'index':len(dig)})
		dig.append([x[l[0]],x[l[1]]])
		
		info['Area %'] = [(area/A)*100,(amax/A)*100]
		info['Digits'] = dig
		self.info['Unipolar'] = info
		self.controls.append({'class':'digits', 'obj':None, 'index':len(dig)})
		dig.append([x[l[0]+2],x[l[0]-2]])
		info['Area %'] = [(area/A)*100,(amax/A)*100]'''
		
		info['Digits'] = dig
		self.info['Unipolar'] = info
		for i in self.info['Unipolar']:
			print i, self.info['Unipolar'][i]

		return dig

		
	def getControls(self):
		print 'getControls:'
		for ctr in self.controls:
			if ctr['obj'] == None: #don't make dublicates
				if ctr['class'] == ('zoom'):
					r = pg.LinearRegionItem()
					r.setZValue(10)
					r.sigRegionChanged.connect(self.zoom)
					ctr['obj'] = r
					continue
				if ctr['class'] == ('digits'):
					r = pg.LinearRegionItem(orientation=pg.LinearRegionItem.Horizontal)
					r.setZValue(10)
					i = ctr['index']
					r.sigRegionChanged.connect(lambda b, i=i: self.setRegion(b,i))
					r.setRegion(self.digits[i])
					ctr['obj'] = r
					continue
        		print 'UpiDigitizer has no control Class: ',ctr['class'],'!'
		for ctr in self.controls:
			print ctr['class']
		return self.controls
		
	def zoom(self,b):
		self.a1X = b.getRegion()
		self.p1.setXRange(self.a1X[0], self.a1X[1], padding=0) 
		
	def setRegion(self, b, i):
		#print 'setRegion i :',i
		#print self.digits
		self.digits[i] = b.getRegion()
		self.filter(self.digits)

	'''def seta3(self, b):
		self.digits[1] = b.getRegion()
		self.filter(self.digits)'''
		
	def filter(self, a):
		#print 'filter'
		d = self.data.copy()
		t = self.time
		bins = [val for sublist in a for val in sublist]
		bins.sort()
		for i, v in enumerate(d):
			c = 0
			for j in range(len(a)):
				b = a[j]
				#print v,'\t',j,'\t',b[0],'\t',b[1]	
				if v > b[1]:
					c += 1
					continue
				elif v >= b[0]:
					if i > 0:
						c = int(d[i-1])
					break
					
						
			d[i] = c
			#print '-->',c
		self.p1.plot(t, d, clear=True)



#--------------------------------------------------------------
# class for plotting data from thread
class ThreadPlotter(QtGui.QMainWindow):
	def __init__(self,name, In, parent):
		super(ThreadPlotter, self).__init__(parent)
		self.setAttribute(Qt.WA_DeleteOnClose, True)
		def exit(self):
			print 'Thread Plotter exit():'
			self.thread.exit()
		self.destroyed.connect(self.exit)
		self.timer = pg.QtCore.QTimer()
		self.bins = 20

		#-----  THREAD  --------------------
		'''if port is None:
			self.port = None
			self.data = np.random.normal(size=1000)
			self.timer.timeout.connect(self.demo)'''

		#else:
		self.name = name
		print 'ThreadPlotter.init on port:', In
		#self.s = serial.Serial(self.port)
		#self.thread = SerialReader(self.s)
		self.thread = In
		self.thread.start()
		print self.thread
		self.timer.timeout.connect(self.update)
		#-----------------------------------
		
		self.a = DockArea()
		self.setCentralWidget(self.a)
		self.h = pg.PlotWidget()#(col=1)
		self.p = pg.PlotWidget()#title="Dock 6 plot")#(col=1)
		self.d1 = self.a.addDock(Dock('NoPort', closable=True))
		self.d1.addWidget(self.h)
		self.d1.addWidget(self.p, col=1, row = 0)
		self.p.scene().sigMouseClicked.connect(self.st)
		self.timer.start(0)

	def st(self):
		if self.timer.isActive():
			print 'stop:'
			self.timer.stop()
			self.d = self.a.addDock(Dock('Filter', closable=True),'bottom', self.d1)
			self.filt = UpiDigitizer(self.time, self.data, self)
			self.d.addWidget(self.filt)
			c = self.filt.getControls()
			for i in c:
				#print i['class']
				if i['class'] == 'zoom':
					self.p.addItem(i['obj'], ignoreBounds=True)
				if i['class'] == 'digits':
					self.h.addItem(i['obj'], ignoreBounds=True)
		else:
			print 'start:'
			self.d.close()
			self.timer.start(0)

	# Calling update() will request a copy of the most recently-acquired 
	# samples and plot them.

	def update(self):
		'''self.time, self.data, r = self.thread.get(5100, downsample=1)		
		self.p.plot(self.time, self.data, clear=True)
		self.p.setTitle('Input '+self.name+' Frequency Rate: %0.2f'%r+'Hz')
		self.h.clear()
		self.h.addItem(self.hist())'''

		if not self.p.isVisible():
			self.exit()
			self.timer.stop()

	'''def demo(self):
		self.data[:-1] = self.data[1:]
		self.data[-1] = np.random.normal()
		self.data += np.sin(np.linspace(0, 90, 1000))
		
		self.p.plot(self.data, clear=True)
		self.p.setTitle(self.thread)
		self.h.clear()
		self.h.addItem(self.hist())'''
		
	def hist(self):
		y,x = np.histogram(self.data, bins=np.linspace(np.min(self.data),np.max(self.data),self.bins))
		h = pg.PlotCurveItem(-x, map(float, y)/sum(y), stepMode=True, fillLevel=0, brush=(255, 0, 0, 80))
		h.rotate(-90)
		return h


	def exit(self):
		print 'Thread Plotter exit()'
		self.thread.exit()

#---------------------------------------------------------------

class UpiScope(QtGui.QMainWindow):
	pmax = 1
	
	def __init__(self, parent = None, **kargs):
		super(UpiScope,self).__init__(parent)
		self.setAttribute(Qt.WA_DeleteOnClose, True)
		self.initUi()

	def initUi(self):
		self.a = DockArea()
		self.setCentralWidget(self.a)
		self.port = QStringList()
		self.show()
		self.setWindowTitle('UpiScopal Arduino Signal Anlyzer')
		self.timer = pg.QtCore.QTimer()
		self.timer.start(1000)
		self.timer.timeout.connect(self.ports)
		self.ports()

	def ports(self):
		ports = glob.glob('/dev/ttyACM*')
		for p in ports:
			if p in self.port:
				pass
			else:
				print '\x1b[6;30;42m'+'\n'+'NEW PORT:''\x1b[0m'+p
				self.port << p
				print 'Port Count',len(self.port)
				#s = serial.Serial(self.port)
				In = SerialReader(serial.Serial(p))
				ThreadPlotter(p,In, self)
				self.resize(1200,len(self.port)*200)
				self.nextRow()

		if ports == [] and len(self.port) < self.pmax:
			print '\x1b[6;30;42m'+'\n'+'NO PORT FOUND:''\x1b[0m'
			self.port << "NoPort"
			print 'Port Count',len(self.port)
			d = self.a.addDock(Dock('UpiSignal', size=(800,200), closable=True))
			#UpiSignal('UpiSignal')
			d.addWidget(ThreadPlotter('UpiSignal', UpiSignal(), self))
			self.resize(1200,len(self.port)*250)
			
#-------------------------------------------------------------------------
class UpiSignal(threading.Thread):
	def __init__(self, chunkSize=1000, chunks=5000):
		threading.Thread.__init__(self)
		print 'UpiSignal.init:'
		# circular buffer for storing serial data until it is 
		# fetched by the GUI
		self.buffer = np.zeros(chunks*chunkSize, dtype=np.float)
		self.chunks = chunks        # number of chunks to store in the buffer
		self.chunkSize = chunkSize  # size of a single chunk (items, not bytes)
		self.ptr = 0                # pointer to most (recently collected buffer index) + 1
		self.sps = 0.0              # holds the average sample acquisition rate
		self.exitFlag = False
		self.exitMutex = threading.Lock()
		self.dataMutex = threading.Lock()
		
	def run(self):
		exitMutex = self.exitMutex
		dataMutex = self.dataMutex
		buffer = self.buffer
		count = 0
		sps = None
		lastUpdate = pg.ptime.time()
		func = np.sin(np.linspace(-np.pi, np.pi, 1000))
		us = 1000 #wave lenght in microseconds
		ms = us/1000 #in milliseconds
		amplitude = 255
		ptrr = 0
		
		while True:
			# see whether an exit was requested
			with exitMutex:
				if self.exitFlag:
					break
			# keep track of the acquisition rate in samples-per-second
			now = pg.ptime.time()
			dt = now-lastUpdate
			lastUpdate = now
			sSlice = int(dt*1000000)
			self.chunkSize = sSlice
			count += self.chunkSize
			#func = np.sin(np.linspace(-np.pi, np.pi, self.chunkSize))
			#data = np.random.normal(2, size=self.chunkSize)#, dtype=np.float)
			data = amplitude*func[ptrr:ptrr+sSlice]
			print 'ptrr',ptrr
			print '%:',(ptrr + sSlice) % func.shape[0]
			ptrr = (ptrr + sSlice) % func.shape[0]
			print 'dt:',dt,sSlice

			if dt > 1.0:
				# sps is an exponential average of the running sample rate measurement
				if sps is None:
					sps = count / dt
				else:
					sps = sps * 0.9 + (count / dt) * 0.1
				count = 0
				#lastUpdate = now
			# write the new chunk into the circular buffer
			# and update the buffer pointer
			with dataMutex:
				#buffer[self.ptr:self.ptr+self.chunkSize] = data
				self.ptr = (self.ptr + self.chunkSize) % buffer.shape[0]
				print 'ptr',self.ptr
				if sps is not None:
					self.sps = sps
                	
	def get(self, num, downsample=1):
		with self.dataMutex:  # lock the buffer and copy the requested data out
			ptr = self.ptr
			if ptr-num < 0:
				data = np.empty(num, dtype=np.float)
				data[:num-ptr] = self.buffer[ptr-num:]
				data[num-ptr:] = self.buffer[:ptr]
			else:
				data = self.buffer[self.ptr-num:self.ptr].copy()
			rate = self.sps
		# Convert array to float and rescale to voltage.
		# Assume 3.3V / 12bits
		# (we need calibration data to do a better job on this)
		#data = data.astype(np.float32) * (3.3 / 2**12)
		if downsample > 1:  # if downsampling is requested, average N samples together
			data = data.reshape(num/downsample,downsample).mean(axis=1)
			num = data.shape[0]
			return np.linspace(0, (num-1)*1e-6*downsample, num), data, rate
		else:
			return np.linspace(0, (num-1)*1e-6, num), data, rate
        	
	def exit(self):
		print 'UpiSignal exit()'
		with self.exitMutex:
			self.exitFlag = True

#-------------------------------------------------------------------------

app = QtGui.QApplication([])

#-------------------------------------------------------------------------

## Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
	import sys
	if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
		w = UpiScope()
		QtGui.QApplication.instance().exec_()


