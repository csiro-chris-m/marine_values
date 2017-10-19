# -*- coding: utf-8 -*-
"""
/***************************************************************************
*    CSIRO Commonwealth Scientific and Industrial Research Organisation    *
*    ELVIS - EnvironmentaL Values Interrogation System                     *
*        begin                : 2016-12-25                                 *
*        git sha              : $Format:%H$                                *
*        copyright            : (C) 2016 by CSIRO Oceans and Atmosphere    *
*        email                : chris.moeseneder@csiro.au                  *  
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
    os.path.dirname(__file__), 'ELVIS_dialog_base.ui'))


class ELVISDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ELVISDialog, self).__init__(parent, QtCore.Qt.WindowMinimizeButtonHint)
        #Use this code to make it stay on top of all other UI windows:
        #super(ELVISDialog, self).__init__(parent, QtCore.Qt.WindowStaysOnTopHint)

        # Set up the user interface fr om Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self._want_to_close = False
        pal=QtGui.QPalette()
        role = QtGui.QPalette.Background
        pal.setColor(role, QtGui.QColor(214, 211, 171))
        self.setPalette(pal)        

        self.setWindowIcon(QtGui.QIcon(':/plugins/ELVIS/ELVISicon32x32.png'))

        #Disable action of the close button 'x'. 
        #self._want_to_close = False

        #print self.defaultPath.toPlainText()

    def closeEvent(self, evnt):
        print "*"
        super(ELVISDialog, self).closeEvent(evnt)

