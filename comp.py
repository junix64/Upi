import sys
import glob
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class combobox(QWidget):
   def __init__(self, parent = None):
      super(combobox, self).__init__(parent)
      #ports = glob.glob('/dev/tty[A-Za-z]*')
      
      layout = QHBoxLayout()
      self.cb = QComboBox()
      #self.cb.addItems(ports)
      self.cb.currentIndexChanged.connect(self.selectionchange)
		
      layout.addWidget(self.cb)
      self.setLayout(layout)
      self.setWindowTitle("Ports Available")

   def selectionchange(self,i):
      print "Items in the list are :"
		
      for count in range(self.cb.count()):
         print self.cb.itemText(count)
      print "Current index",i,"selection changed ",self.cb.currentText()

   def items(self, items):
      self.cb.addItems(items)
		
def main():
   app = QApplication(sys.argv)
   ex = combobox()
   ex.items(glob.glob('/dev/tty[A-Za-z]*'))
   ex.show()
   sys.exit(app.exec_())

if __name__ == '__main__':
   main()
