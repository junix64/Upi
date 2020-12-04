from PyQt4.QtCore import *
from PyQt4.QtGui import *
from pyqtgraph.Qt import QtCore, QtGui
#from pyqtgraph.dockarea import *
import pyqtgraph as pg
#import glob
import time, threading, sys
import serial
import numpy as np
import Upi as Upi

app = QtGui.QApplication([])
cod =  [Upi.UpiCodec.Codec('Hexa', Upi.UpiCodec.hexa, val = Upi.UpiCodec.hexRegExp) ,
		Upi.UpiCodec.desimalCodec,
		Upi.UpiCodec.Codec('binary', Upi.UpiCodec.bin, val = Upi.UpiCodec.binRegExp)
		]
		
mw = Upi.SignalGenerator('Upi Signal Generator')#, [Upi.Codec.Codec('ASCII', Upi.Codec.ascii, val = Upi.Codec.binRegExp)])
#mw.inPut.addCodec(cod)

#-------------------------------------------------------------------------

## Start Qt event loop unless running in interactive mode using pyside.
if __name__ == '__main__':
	import sys
	if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
		QtGui.QApplication.instance().exec_()

