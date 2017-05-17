# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CSIROMarineValuesDialog
                                 A QGIS plugin
 MARVIN - CSIRO Marine values tool. Management of marine value layers
                             -------------------
        begin                : 2016-12-25
        git sha              : $Format:%H$
        copyright            : (C) 2016 by CSIRO Oceans and Atmosphere Chris Moeseneder
        email                : chris.moeseneder@csiro.au
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic, QtCore

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'marine_values_dialog_base.ui'))


class CSIROMarineValuesDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(CSIROMarineValuesDialog, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)
        # Set up the user interface fr om Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        pal=QtGui.QPalette()
        role = QtGui.QPalette.Background
        pal.setColor(role, QtGui.QColor(214, 211, 171))
        self.setPalette(pal)        

        #Doesn't work. Need to make resources
        self.setWindowIcon(QtGui.QIcon(':/plugins/CSIROMarineValues/mv_icon32x32.png'))

        #Disable action of the close button 'x'. 
        #self._want_to_close = False

        #print self.defaultPath.toPlainText()

    #def closeEvent(self, evnt):
    #    if self._want_to_close:
    #        super(MyDialog, self).closeEvent(evnt)
    #    else:
    #        evnt.ignore()
