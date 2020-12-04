
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

	def __init__(self, parent, times, data, **kwargs):
		super(UpiDigitizer, self).__init__(parent)
		self.setAttribute(Qt.WA_DeleteOnClose)
		#self.destroyed.connect(self.exit)
		self.l = pg.GraphicsLayout(border=(0,100,100))
		self.setCentralItem(self.l)
		self.data = data
		self.times = times
		self.bins = 20
		self.info = {'Bin count':self.bins}
		self.p1 = self.l.addPlot(col=2)
		self.p1.scene().sigMouseClicked.connect(self.st)
		self.controls = [{'class':'zoom','obj':None}]
		self.digits = self.digitize(show = True)
		self.p1.plot(self.times, self.filter(self.digits, self.data))

	def st(self):
		print 'st:'
		
	def digitize(self, show = False):
		info = {}
		dig = []
		l = []
		show = show
		a = False
		y,x = np.histogram(self.data, bins=np.linspace(np.min(self.data),np.max(self.data),self.bins))
		#---- Minus least square sum methode - Bipolar and Multilevel -----------------------------
		f = 1.0 #factor for sifting trendline right
		t = np.polyfit(x[:-1], y*f, 2)#compute factors for trendline
		p = np.poly1d(t)#trendline formula
		z = y-p(x[:-1])
		if show:
			self.h1 = self.l.addPlot(col=1)
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
			self.h1.setTitle('Trendline formula:'+str(p))#' Frequency Rate: %0.2f'%r+'Hz'
		for i in range(len(z)-1):
			if z[i] > 0 and z[i+1] <= 0 and not a:
				l.append(x[i+2])
				a = True
				#print i,'a:',z[i],z[i+1], l
			if (z[i+1] > 0) and (z[i] <= 0) and a:
				l.append(x[i])
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
		'''for i in self.info['Unipolar']:
			print i, self.info['Unipolar'][i]'''

		return dig

		
	def getControls(self):
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
		'''for ctr in self.controls:
			print ctr['class']'''
		return self.controls
		
	def zoom(self,b):
		self.a1X = b.getRegion()
		self.p1.setXRange(self.a1X[0], self.a1X[1], padding=0) 
		
	def setRegion(self, b, i):
		self.digits[i] = b.getRegion()
		self.p1.plot(self.times, self.filter(self.digits, self.data), clear=True)
		
	def filter(self, dig, data):
		#print 'filter'
		d = data.copy()
		for i, v in enumerate(d):
			c = 0
			for j in range(len(dig)):
				b = dig[j]
				if v > b[1]:
					c += 1
					continue
				elif v >= b[0]:
					if i > 0:
						c = int(d[i-1])
					break
					
						
			d[i] = c
		return d
		
	def exit(self):
		print 'UpiDigitizer exit()'
		

#--------------------------------------------------------------
# class for plotting data from thread
class ThreadPlotter(QtGui.QWidget):
	def __init__(self, parent, name, In, chunkSize=20000):
		super(ThreadPlotter, self).__init__(parent)
		self.setAttribute(Qt.WA_DeleteOnClose, True)
		self.parent = parent
		self.timer = pg.QtCore.QTimer()
		self.chunkSize = chunkSize
		self.bins = 20
		self.filt = None

		#-----  THREAD  --------------------
		self.name = name
		self.thread = In
		self.thread.start()
		self.timer.timeout.connect(self.update)
		#-----------------------------------
		
		self.d1 = parent.addDock(self, None, 'Thread Plotter')
		self.h = pg.PlotWidget()
		#self.h.resize(10,10)
		self.p = pg.PlotWidget()
		self.d1.addWidget(self.h)
		self.d1.addWidget(self.p, col=1, row = 0)
		self.p.scene().sigMouseClicked.connect(self.st)
		self.timer.start(0)

	def st(self, b):
		e = b.button()
		self.filt = UpiDigitizer(self, self.time, self.data)
		c = self.filt.getControls()
		#c = {'controls':self.filt.getControls()}
		#c.append('controls':self.filt.getControls())
		if e == 1:
			if self.timer.isActive():
				self.timer.stop()
				self.d = self.parent.addDock(self.filt,self.d1, 'Digitizer')
				self.d.addWidget(self.filt)
				for i in c:
					if i['class'] == 'zoom':
						i['obj'].setRegion([0,self.chunkSize/1000])
						self.p.addItem(i['obj'], ignoreBounds=True)
					if i['class'] == 'digits':
						self.h.addItem(i['obj'], ignoreBounds=True)
			else:
				self.timer.start(0)
				if self.d.isVisible():
					self.d.label.sigCloseClicked.emit()
		if e == 2 and self.filt is not None:
			print '2'
			#c = self.filt.getControls()
			self.w = pg.DataTreeWidget(data=c)
			#self.w.setColumnCount(2)
			self.w.show()
			self.w.setWindowTitle('pyqtgraph example: DataTreeWidget')
			for i in c:
				print i['class']
				item = QtGui.QTreeWidgetItem([i['class']])#QtGui.QTreeWidgetItem(["Item 1"])
				item.addChild(i['obj'].getRegion()[1])
				self.w.addTopLevelItem(item)


	def update(self):
		self.time, self.data, r = self.thread.get(self.chunkSize, downsample=1)		
		self.p.plot(self.time, self.data, clear=True)
		self.p.setTitle('Input '+self.name+' Frequency Rate: %0.2f'%r+'Hz')
		self.h.clear()
		self.h.addItem(self.hist())

	def hist(self):
		y,x = np.histogram(self.data, bins=np.linspace(np.min(self.data),np.max(self.data),self.bins))
		h = pg.PlotCurveItem(-x, map(float, y)/sum(y), stepMode=True, fillLevel=0, brush=(255, 0, 0, 80))
		h.rotate(-90)
		return h

	def exit(self):
		print 'Thread Plotter exit()'
		self.thread.exit()
		if self.filt is not None:
			self.filt.exit()
		self.timer.stop()

#---------------------------------------------------------------

class UpiSignal(threading.Thread):
	def __init__(self, sampleSize=1000, bufferSize=5000000):
		threading.Thread.__init__(self)
		self.buffer = np.zeros(bufferSize, dtype=np.float)
		self.sampleSize = sampleSize
		self.ptr = 0 
		self.sps = 0.0 
		self.exitFlag = False
		self.exitMutex = threading.Lock()
		self.dataMutex = threading.Lock()

	def run(self):
		exitMutex = self.exitMutex
		dataMutex = self.dataMutex
		buffer = self.buffer
		sampleSize = self.sampleSize
		sps = None
		lastUpdate = pg.ptime.time()
		func = np.sin(np.linspace(-np.pi, np.pi, sampleSize))
		amplitude = 255
		noise_level = amplitude*0,2
		toGo = 0
		idx = 0
		count = 0
		time = 0
		
		while True:
			with exitMutex:
				if self.exitFlag:
					break
			now = pg.ptime.time()
			dt = now-lastUpdate
			lastUpdate = now
			toGo += int(dt*sampleSize*1000)
			data = np.array([])
 			data = amplitude*func[idx:idx+toGo]
 			s = data.shape[0]
			data += np.random.normal(20, size=s)
 			toGo -= s
 			#print toGo
 			count += s
			time += dt
			idx = (idx + s) % func.shape[0]
			
			if time > 1.0:
				if sps is None:
					sps = (count/sampleSize) / time
				else:
					sps = sps * 0.9 + ((count/sampleSize) / time) * 0.1
				count = 0
				time = 0.0
			with dataMutex:
				buffer[self.ptr:self.ptr+data.shape[0]] = data
				self.ptr = (self.ptr + data.shape[0]) % buffer.shape[0]
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
		if downsample > 1:  # if downsampling is requested, average N samples together
			data = data.reshape(num/downsample,downsample).mean(axis=1)
			num = data.shape[0]
			return np.linspace(0, (num-1)*1e-3*downsample, num), data, rate
		else:
			return np.linspace(0, (num-1)*1e-3, num), data, rate
        	
	def exit(self):
		print 'UpiSignal exit()'
		with self.exitMutex:
			self.exitFlag = True

#-------------------------------------------------------------------------

class UpiScope(QtGui.QMainWindow):
	pmax = 1
	dH = 250		#dockHight
	dW = 1200		#dockWidht
	dockCount = 0
	threads = []
	
	def __init__(self, parent = None):
		super(UpiScope, self).__init__()
		self.setAttribute(Qt.WA_DeleteOnClose, True)
		self.a = DockArea()
		self.setCentralWidget(self.a)
		self.port = QStringList()
		self.resize(self.dW, self.dH)
		self.show()
		self.setWindowTitle('UpiScopal Arduino Signal Anlyzer')
		self.timer = pg.QtCore.QTimer()
		self.timer.timeout.connect(self.ports)
		self.ports()
		self.timer.start(1000)

	def ports(self):
		ports = glob.glob('/dev/ttyACM*')
		In = None
		for p in ports:
			if p in self.port:
				pass
			else:
				print '\x1b[6;30;42m'+'\n'+'Serial Reader:''\x1b[0m'+p
				self.port << p
				self.newIn(p,serial.Serial(p))
		if ports == []  and len(self.port) < self.pmax:
			print '\x1b[6;30;42m'+'\n'+'Upi Signal:''\x1b[0m'
			self.port << "UpiSignal"
			self.newIn('UpiSignal',UpiSignal())
	
	def newIn (self, title, In):		
		t = ThreadPlotter(self, title, In)
		self.threads.append(t)
		
			
	def addDock(self, p, d1, title):
		d = self.a.addDock(Dock(title, size=(800,200), closable=True),'bottom', d1)
		d.label.sigCloseClicked.connect(lambda d=d, p=p: self.rmDock(d,p))
		self.dockCount += 1
		self.resize(self.frameGeometry().width(), self.dH*self.dockCount)
		return d
	
	def rmDock(self,d,p):
		self.dockCount -= 1
		self.resize(self.frameGeometry().width(), self.dH*self.dockCount)
		p.exit()
			
		
	def closeEvent(self, b):
		print 'Upiscope closeEvent()'
		#exit all threads
		for t in self.threads:
			t.exit()

#-------------------------------------------------------------------------

app = QtGui.QApplication([])
mw = UpiScope()

#-------------------------------------------------------------------------

## Start Qt event loop unless running in interactive modeusing pyside.
if __name__ == '__main__':
	import sys
	if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
		QtGui.QApplication.instance().exec_()


