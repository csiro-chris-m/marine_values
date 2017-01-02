# -*- coding: utf-8 -*-
"""
/***************************************************************************
 CSIROMarineValues
                                 A QGIS plugin
 MARVIN - CSIRO Marine values tool. Management of marine value layers
                              -------------------
        begin                : 2016-12-25
        git sha              : $Format:%H$
        copyright            : (C) 2016 by CSIRO Oceans and Atmosphere
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

/***************************************************************************
 *                                                                         *
 *   Help file for this app is in the plugin dir and called "marine values help.txt"                                                                      
 *                                                                         *
 *                                                                         *
 *                                                                         *
 *                                                                         *
 ***************************************************************************/



"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo
from PyQt4.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from marine_values_dialog import CSIROMarineValuesDialog
import os.path
import json
from os.path import expanduser
import os
from PyQt4 import QtGui
from PyQt4 import QtCore
from os import listdir
from os.path import isfile, join
from qgis.core import *
from qgis.utils import QGis
from collections import defaultdict
from pprint import pprint

class CSIROMarineValues:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Have we filled the list widget with the shps yet?
        self.filled = False
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CSIROMarineValues_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&CSIRO Marine Values')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'CSIROMarineValues')
        self.toolbar.setObjectName(u'CSIROMarineValues')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CSIROMarineValues', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        self.dlg = CSIROMarineValuesDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/CSIROMarineValues/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'CSIRO Marine Values System'),
            callback=self.run,
            parent=self.iface.mainWindow())

        self.dlg.loadProject.clicked.connect(self.loadProjectClicked)
        self.dlg.saveProject.clicked.connect(self.saveProjectClicked)
        self.dlg.getNameValue.clicked.connect(self.getNameValueClicked)
        

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&CSIRO Marine Values'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):

        #Check if there is a default path in QGIS settings 
        # (are stored persistently). If not ask
        # user to choose a directory and write that to settings.
        # Default path is used for shapefiles
        qset = QSettings()
        defpath = qset.value("marine_values/default_path", "")
        if defpath and not defpath.isspace():
            pass
        else:
            dirp = QtGui.QFileDialog.getExistingDirectory(None, 'Select a default folder (for shapefiles):', 'C:\\', QtGui.QFileDialog.ShowDirsOnly)
            #prttxt = self.dlg.defaultPath.toPlainText()
            qset.setValue("marine_values/default_path", dirp)
            defpath = qset.value("marine_values/default_path", "")

        onlyfiles = []
        for f in listdir(defpath):
            if isfile(join(defpath, f)):
                if f.endswith('.shp'):
                    onlyfiles.append(f)

        if not len(onlyfiles):
            self.dlg.error.setText("Default directory does not contain any spatial files.")

        onlyfiles.sort()
        if not self.filled:
            self.filled = True
            model = QStandardItemModel()
            model.setColumnCount(3)
            model.setHorizontalHeaderLabels(['Layer', 'Type', 'Sort Key'])
            for fil in onlyfiles:
                item = QStandardItem(fil)
                item.setCheckable(True)
                model.appendRow([item, QStandardItem('unknown'), QStandardItem('99999')])
            self.dlg.tableView.setModel(model)

        #self.dlg.tableView.verticalHeader().setMovable(True)
        #self.dlg.tableView.verticalHeader().setDragEnabled(True)
        #self.dlg.tableView.verticalHeader().setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        #self.dlg.tableView.setDropIndicatorShown(True)
        self.dlg.tableView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.dlg.tableView.setSelectionMode(QtGui.QTableView.SingleSelection)
        self.dlg.tableView.selectionChanged = lambda x, y: pprint([self, x, y])
        #self.dlg.tableView.setAcceptDrops(True)
        #self.dlg.tableView.mousePressEvent = lambda event: pprint(event)
        #self.dlg.tableView.dropEvent = lambda event: pprint(event)
        #self.dlg.tableView.dropOn = lambda event: pprint(event)
        #self.dlg.tableView.droppingOnItself = lambda event: pprint(event)
        #self.dlg.tableView.setAcceptDrops(True)
        #self.dlg.tableView.model().columnsMoved.connect(lambda event: pprint(event))

        ## show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass


    def pushButtonClicked(self):
        items = self.dlg.listWidget.selectedItems()
        x=[]
        for i in list(items):
            stp = str(i.text())
            x.append(stp)
            qset = QSettings()
            defpath = qset.value("marine_values/default_path", "")
            print defpath
            layer = self.iface.addVectorLayer(defpath, "layer name you like", "ogr")

    def manageLayer(self, x, index):
        #Write code here to load and unload layers and save project
        try:
            x
        except IOError:
            pass

    def loadProjectClicked(self):
        project = QgsProject.instance()
        #if project.fileName():
            #self.dlg.error.setText("Please close any currently open projects")
            #return
        qset = QSettings()
        defpath = qset.value("marine_values/default_path", "")
        geometryTypes = defaultdict(lambda: 'unknown', {QGis.Polygon: 'polygon', QGis.Point: 'point'})
        tryCount = 0
        while tryCount < 2:
            if not project.read(QFileInfo(defpath + '\marine_values.qgs')):
                self.dlg.error.setText("Could not load marine_values.qgs")
            elif len(project.layerTreeRoot().findLayers()) < 1:
                self.dlg.error.setText("No layers found")
            else:
                tryCount = 9999
            tryCount += 1
        self.dlg.tableView.model().itemChanged.connect(lambda x: self.manageLayer(self, x))
        treeLayerIdx = 0
        position = {}
        self.layerInfo = {}
        for treeLayer in project.layerTreeRoot().findLayers():
            layer = treeLayer.layer()
            for i in range(self.dlg.tableView.model().rowCount()):
                item = self.dlg.tableView.model().item(i, 0)
                if item.text() in layer.source().split("|")[0]:
                    self.layerInfo[item.text()] = self.getLayerInfo(layer)
                    item.setCheckState(QtCore.Qt.Checked)
                    geometryType = self.dlg.tableView.model().item(i, 1)
                    geometryType.setText(geometryTypes[layer.geometryType()])
                    sortOrder = self.dlg.tableView.model().item(i, 2)
                    sortOrder.setText('{:05d}'.format(treeLayerIdx))
            treeLayerIdx += 1
        self.dlg.tableView.model().sort(2)
                    

    def saveProjectClicked(self):
        project = QgsProject.instance()
        project.write()

    def getLayerInfo(self, layer):
        layerInfo = []
        for feature in layer.getFeatures():
            geom = feature.geometry()
            layerInfo.append("Feature ID %d: " % feature.id())
        return "\n".join(layerInfo)


    def getNameValueClicked(self):
        layer = self.iface.activeLayer()
        iter = layer.getFeatures()
        for feature in iter:
            # retrieve every feature with its geometry and attributes
            # fetch geometry
            geom = feature.geometry()
            print "Feature ID %d: " % feature.id()

            # show some information about the feature
            if geom.type() == QGis.Point:
                x = geom.asPoint()
                print "Point: " + str(x)
            elif geom.type() == QGis.Line:
                x = geom.asPolyline()
                print "Line: %d points" % len(x)
            elif geom.type() == QGis.Polygon:
                x = geom.asPolygon()
                numPts = 0
                for ring in x:
                    numPts += len(ring)
                print "Polygon: %d rings with %d points" % (len(x), numPts)
            else:
                print "Unknown"

            # fetch attributes
            attrs = feature.attributes()

            # attrs is a list. It contains all the attribute values of this feature
            print attrs
