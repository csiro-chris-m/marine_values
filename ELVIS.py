# -*- coding: utf-8 -*-
"""
/***************************************************************************
*    CSIRO - Commonwealth Scientific and Industrial Research Organisation  *
*    ELVIS - Environmental and Livelihood Values Interrogation System      *
*    A QGIS plugin                                                         *
* ------------------------------------------------------------------------ *
*        begin                : 2016-12-25                                 *
*        git sha              : $Format:%H$                                *
*        copyright            : (C) 2017 by CSIRO Oceans and Atmosphere    *
*        author               : Chris Moeseneder                           *
*        email                : chris.moeseneder@csiro.au                  *
***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   Help file for this app is in the plugin directory                     *
 *   named "elvis help.txt"                                                * 
 *                                                                         *
 *   Environment Versions                                                  *
 *   ------------------------------------                                  *
 *   Python 2.7.5                                                          *
 *   QGIS 2.18.2 Las Palmas                                                *
 *   Qt Creator 4.2.0                                                      *
 *                                                                         *
 *   Modules required:                                                     *
 *   ------------------------------------                                  *
 *   pyqtgraph - problems with installation via pip and ez_setup           *
 *               hence copy manually to the                                *
 *               QGIS/Apps/Python27/Lib/site-packages dir                  *
 *                                                                         *
 *   QGIS:                                                                 *
 *   ------------------------------------                                  *
 *   In Options / Map Tools:                                               *
 *   Preferred distance units: Kilometers                                  *
 *   Preferred area units: Square kilometers                               *
 *   Preferred angle units: Degrees                                        *
 *   Settings / Options / CRS / CRS for new layers: Use a default CRS:     *
 *                              Selected CRS (EPSG:4326, WGS 84)           *
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   Configuration of the shapefiles and project                           *
 *   Shapefiles and project must be in CRS "WGS84 (EPSG:4326)"             *                                  
 *   -------------------------------------------------------------------   *
 *   Project files should be write-protected so user can not make changes  *
 *   -------------------------------------------------------------------   *
 *                                                                         *
 ***************************************************************************/

/***************************************************************************
 *   Known issues:                                                         *
 *   Inexplicable slow behaviour in previously fast functions, like        *
 *   project load, area selection and info function, could be caused by    *
 *   the plugin reloader. Ensure that the newest version is in use.        *
 ***************************************************************************/

"""

import resources
import os.path
import json
import os
import processing
import ntpath
import csv
import datetime
import sys
import unicodedata
import numpy
import operator
import qgis.utils
import pyqtgraph as pg
import time

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo, QAbstractItemModel, Qt, QVariant, QPyNullVariant, QDir
from PyQt4.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QHeaderView, QColor, QBrush,QDialogButtonBox, QFileDialog, QToolBar, QApplication, QListWidgetItem, QTreeWidgetItem, QPixmap, QTableWidgetItem, QFont, QAbstractItemView, QMessageBox, QPen
from qgis.gui import QgsRubberBand, QgsMapToolEmitPoint, QgsMapCanvas, QgsMapToolZoom, QgsLayerTreeMapCanvasBridge, QgsMapTool
from PyQt4 import uic
from ELVIS_dialog import ELVISDialog
from PyQt4.QtSql import QSqlDatabase, QSqlQuery
from PyQt4 import QtGui
from PyQt4 import QtCore
from os import listdir
from os.path import isfile, join, basename
from qgis.core import *
from qgis.core import QgsWKBTypes
from qgis.core import QgsMapLayer
from qgis.core import QgsProviderRegistry
from qgis.utils import QGis
from qgis import utils
from collections import defaultdict
from pprint import pprint
from os.path import expanduser

try:
    from win32api import GetSystemMetrics
except ImportError:
    pass


class ELVIS:
    def __init__(self, iface):
        #Constructor.

        #Following code is unused but can be used to check if previous instance of plugin
        #is running
        #ELVIS loaded and available
        #for plug in qgis.utils.available_plugins:
        #    if plug == "ELVIS":

        self.project = QgsProject.instance()

        # Have we filled the list widget with the shps yet?
        self.filled = False
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        #Directory where project file and all shps reside
        self.last_opened_project_dir = ""

        #Counter for sort order of layers
        self.treeLayerIdx = 0
        #Operation mode of this plugin: 
        #  'dev' - development. Ending does not close QGIS.
        #  'prod'- production. End command ends QGIS.
        self.opmode = 'dev'
        self.geometryTypes = defaultdict(lambda: 'unknown', {QGis.Polygon: 'polygon', QGis.Point: 'point'})

        self.myRubberBand = QgsRubberBand(self.iface.mapCanvas(),QGis.Polygon)
        self.RBMode = "" #Rubberband created by user (user) or saved area (saved)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'ELVIS_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&CSIRO ELVIS')
        self.toolbar = self.iface.addToolBar(u'CSIRO ELVIS')
        self.toolbar.setObjectName(u'CSIRO ELVIS')

        # In memory list of layers and associated info (ie which are loaded, sorting) that are available in the project dir
        # 0 - sort key, 1 - loaded, 2 - type, 3 - layername
        self.projectlayers = []


    def tr(self, message):
        #Get the translation for a string using Qt translation API.
        #We implement this ourselves since we do not inherit QObject.
        #   :param message: String for translation. Type message: str, QString. Returns: Translated version of message. rtype: QString
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('ELVIS', message)


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

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.triggered.connect(self.closeEvent)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            for x in self.iface.mainWindow().findChildren(QToolBar): 
                if x.objectName() == "CSIRO ELVIS":
                    pass
                else:
                    self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        try:
            # Create the dialog (after translation) and keep reference
            self.dlg = ELVISDialog()

            #Create the menu entries and toolbar icons inside the QGIS GUI
            icon_path = ':/plugins/ELVIS/resources/ELVIS32.png'
            self.add_action(
                icon_path,
                text=self.tr(u'CSIRO ELVIS'),
                callback=self.run,
                parent=self.iface.mainWindow())

            # Define Set signal only in iniGui. Connect to signal renderComplete which is emitted when canvas rendering is done
            QtCore.QObject.connect(self.iface.mapCanvas(), QtCore.SIGNAL("renderComplete(QPainter *)"), self.renderTest)

            self.dlg.ELVISInfo.clicked.connect(self.DoELVISProgramInfo)
            self.dlg.ELVISInfo.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/ELVIS16.png'))

            self.dlg.saveProject.clicked.connect(self.saveProjectClicked)
            self.dlg.saveProject.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/save.png'))

            self.dlg.endButton.clicked.connect(self.endButtonClicked)
            self.dlg.endButton.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/end.png'))

            self.dlg.rubberband.clicked.connect(self.rubberbandClicked)
            self.dlg.rubberband.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/sel_area2.png'))

            self.dlg.pushButtonPan.clicked.connect(self.pushButtonPanClicked)
            self.dlg.pushButtonPan.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/hand.png'))

            self.dlg.pushButtonZoomPlus.clicked.connect(self.pushButtonZoomPlusClicked)
            self.dlg.pushButtonZoomPlus.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/zoomin.png'))

            self.dlg.pushButtonZoomMinus.clicked.connect(self.pushButtonZoomMinusClicked)
            self.dlg.pushButtonZoomMinus.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/zoomout.png'))

            self.dlg.pushButtonExport.clicked.connect(self.pushButtonExportClicked)
            self.dlg.pushButtonExport.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/export.png'))

            self.dlg.butClearError.clicked.connect(self.butClearErrorClicked)

            self.dlg.pushButtonOrigExtent.clicked.connect(self.pushButtonOrigExtentClicked)
            
            self.dlg.openProj.clicked.connect(self.openProjClicked)
            self.dlg.openProj.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/open.png'))

            self.dlg.delRubber.clicked.connect(self.delRubberClicked)

            self.dlg.btnInfo2.setIcon(QtGui.QIcon(':/plugins/ELVIS/resources/info.png'))
            self.dlg.btnInfo2.clicked.connect(self.btnInfo2Clicked)

            self.dlg.buttonOpenSaved.clicked.connect(self.buttonOpenSavedClicked)

            #self.dlg.tableWidgetSF.setColumnWidth(20,120)

            self.dlg.tableWidgetLayers.clicked.connect(self.tableWidgetLayersClicked)

            QtCore.QObject.connect(self.dlg.tableWidgetLayers, QtCore.SIGNAL("clicked(const QModelIndex & index)"), self.tableWidgetLayersClicked)

            QtCore.QObject.connect(self.dlg.listWidgetScaleNames, QtCore.SIGNAL("itemClicked(QListWidgetItem *)"), self.listWidgetScaleNamesItemClicked)

            self.dlg.tableWidgetSF.cellClicked.connect(self.tableWidgetSFClicked)
            
            #Prevent tables from being user edited
            self.dlg.tableWidgetLayers.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.dlg.tableWidgetDetail.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.dlg.tableWidgetSF.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.dlg.tableWidgetDetailCounts.setEditTriggers(QAbstractItemView.NoEditTriggers)

            self.dlg.endButton.setDefault(True)
            self.dlg.endButton.setAutoDefault(True)

            #Set background to white on graph control
            pg.setConfigOption('background', 'w')
            pg.setConfigOption('foreground', 'k')

            self.sfr = ""

            self.dlg.error.setPlainText("")
        except:
            self.dlg.error.setPlainText("Error initialising GUI. [3]")


    def run(self):
        # Should not connect signals in the run function

        self.dlg.tableWidgetLayers.setColumnWidth(0,20)
        self.dlg.tableWidgetLayers.setColumnWidth(1,0)
        self.dlg.tableWidgetLayers.setColumnWidth(2,0)
        self.dlg.tableWidgetLayers.setColumnWidth(3,30)
        self.dlg.tableWidgetLayers.setColumnWidth(4,0)
        self.dlg.tableWidgetLayers.setColumnWidth(5,200) #Will be stretched with HorizontalHeaderStretchLastSection

        self.dlg.tableWidgetDetail.setColumnWidth(0,120)
        self.dlg.tableWidgetDetail.setColumnWidth(1,120)
        self.dlg.tableWidgetDetail.setColumnWidth(2,80)
        self.dlg.tableWidgetDetail.setColumnWidth(3,80)
        self.dlg.tableWidgetDetail.setColumnWidth(4,80)
        self.dlg.tableWidgetDetail.setColumnWidth(5,80)
        self.dlg.tableWidgetDetail.setColumnWidth(6,80)
        self.dlg.tableWidgetDetail.setColumnWidth(7,80)
        self.dlg.tableWidgetDetail.setColumnWidth(8,80)
        self.dlg.tableWidgetDetail.setColumnWidth(9,80)
        self.dlg.tableWidgetDetail.setColumnWidth(10,80)

        self.dlg.tableWidgetDetailCounts.setColumnWidth(0,150)
        self.dlg.tableWidgetDetailCounts.setColumnWidth(1,100)
        self.dlg.tableWidgetDetailCounts.setColumnWidth(2,40)

        #Load main project
        self.project_load()

        #Stores name of currently active layer. Need this since rubber band sets itself current so must set back
        self.cur_lay = ""

        #List of points in last created Rubberband
        self.rubberbandPoints = []

        #Read database with ELVIS value details and keep in memory for quick access.
        self.dlg.list_of_values = []

        self.dlg.list_of_values_fields = []
        self.dlg.list_of_values_fields.append(['Spatial feature name', 'spatial_feature_name', 17])
        self.dlg.list_of_values_fields.append(['Scale name', 'scale_name', 8])
        self.dlg.list_of_values_fields.append(['Scale id', 'scale_id', 7])
        self.dlg.list_of_values_fields.append(['Value name', 'value_name', 1])
        self.dlg.list_of_values_fields.append(['Value metric score', 'value_metric_score', 12])
        self.dlg.list_of_values_fields.append(['Value type', 'value_type', 4])
        self.dlg.list_of_values_fields.append(['Value metric description', 'value_metric_description', 10])
        self.dlg.list_of_values_fields.append(['Spatial feature id', 'spatial_feature_id', 18])
        self.dlg.list_of_values_fields.append(['Value category', 'value_category', 2])
        self.dlg.list_of_values_fields.append(['Scale type', 'scale_type', 6])
        self.dlg.list_of_values_fields.append(['Value metric units', 'value_metric_units', 11])
        self.dlg.list_of_values_fields.append(['Spatial feature description', 'spatial_feature_description', 19])
        self.dlg.list_of_values_fields.append(['Date collected', 'date_collected', 21])
        self.dlg.list_of_values_fields.append(['Metric score source', 'metric_score_source', 22])
        self.dlg.list_of_values_fields.append(['Metric score contact', 'metric_score_contact', 23])

        self.dlg.area_value_matrix = []
        self.readSQLiteDB()

        #List for items to graph
        self.graphItemsList = []

        #Main window sizing and position
        if sys.platform == "win32": # Windows
            self.dlg.setGeometry(10, 30, self.dlg.width(), self.dlg.height())

        if sys.platform == "darwin": # OS X, MacOS
            pass

        #Set mouse pointer in case we crashed and pointer was still in rubberband mode
        self.iface.actionPan().trigger()

        #Show the dialog
        self.dlg.show()

        self.OrigExtent()

        #Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed. If yes, the main function is terminated.
        if result == 1:
            pass


    def unload(self):
        pass


    def endButtonClicked(self):
        self.xclosing()


    def closeEvent(self, event):
        self.xclosing()


    def xclosing(self):
        self.treeLayerIdx = 0
        """Removes the ELVIS plugin icon from QGIS GUI."""
        #for action in self.actions:
        #    self.iface.removeToolBarIcon(action)
        #del self.toolbar
        QtCore.QObject.disconnect(self.iface.mapCanvas(), QtCore.SIGNAL("renderComplete(QPainter *)"), self.renderTest)
        QtCore.QObject.disconnect(self.dlg.tableWidgetLayers, QtCore.SIGNAL("clicked(const QModelIndex & index)"), self.tableWidgetLayersClicked)
        self._want_to_close = True
        self.dlg.close()
        #Must close current project and begin new empty project, otherwise QGIS stays open
        #with current project and running ELVIS again causes unexpected behaviour, i.e. clear the main map window
        self.iface.newProject()


    def manageLayer(self, x, index):
        try:
            x
        except IOError:
            pass

    def project_load(self):
        try:
            qset = QSettings()
            ret = qset.value("ELVIS/last_opened_project")
            if ret:
                self.last_opened_project = qset.value("ELVIS/last_opened_project")
            else:
                self.last_opened_project = qset.setValue("ELVIS/last_opened_project", "")

            if self.last_opened_project and not self.last_opened_project.isspace():
                self.last_opened_project_dir = ntpath.dirname(self.last_opened_project)

                #Must instantiate bridge to sync stand-alone project with map tree        
                bridge = QgsLayerTreeMapCanvasBridge(self.project.layerTreeRoot(), self.iface.mapCanvas())
                self.project.read(QFileInfo(self.last_opened_project))
            else:
                fileo = QtGui.QFileDialog.getOpenFileName(None, 'Project file to open:', '', '*.qgs')
                filep = QDir.toNativeSeparators(fileo)
                self.last_opened_project = qset.setValue("ELVIS/last_opened_project", filep)
                self.last_opened_project_dir = ntpath.dirname(filep)
                #Must instantiate bridge to sync stand-alone project with map tree        
                bridge = QgsLayerTreeMapCanvasBridge(self.project.layerTreeRoot(), self.iface.mapCanvas())
                self.project.read(QFileInfo(fileo))

            self.dlg.tableWidgetDetail.setRowCount(0)
            self.dlg.tableWidgetDetailCounts.setRowCount(0)
            self.InitLayerList()
            #self.GUILoadProjectLayers()
            self.GUILayersResync()

    #TESTTEST WFS
            #Note that the name of a WFS layer may not contain any spaces or it will fail to load
    #        uri = "http://cmar-geo.bne.marine.csiro.au:8080/geoserver/mqcfr/wfs?service=WFS&typename=mqcfr:MarineValuesNewBritainTestLLG"
    #        vlayer = QgsVectorLayer(uri, "MarineValuesNewBritainTestLLG", "WFS")
    #        QgsMapLayerRegistry.instance().addMapLayer(vlayer)
    #TESTTEST

        except:
            self.dlg.error.setPlainText("Error loading project. [5]")


    def openProjClicked(self):
        try:
            fileo = QtGui.QFileDialog.getOpenFileName(None, 'Project file to open:', '', '*.qgs')
            if fileo:
                filep = QDir.toNativeSeparators(fileo)
                qset = QSettings()
                self.last_opened_project = qset.setValue("ELVIS/last_opened_project", filep)
                self.last_opened_project_dir = ntpath.dirname(filep)

                #Must instantiate bridge to sync stand-alone project with map tree        
                bridge = QgsLayerTreeMapCanvasBridge(self.project.layerTreeRoot(), self.iface.mapCanvas())
                self.project.read(QFileInfo(fileo))
                self.dlg.tableWidgetDetail.setRowCount(0)
                self.dlg.tableWidgetDetailCounts.setRowCount(0)
                self.dlg.listWidgetScaleNames.clear()
                self.dlg.tableWidgetSF.setRowCount(0)
                self.dlg.graphicsView.clear()
                self.dlg.lblWell.setText("")
                self.dlg.lblInc.setText("")
                self.dlg.lblFoosec.setText("")
                self.InitLayerList()
                self.GUILayersResync()
        except:
            self.dlg.error.setPlainText("Error opening project. [55]")

    def doGraph(self):
        try:
            self.dlg.graphicsView.clear()
            self.dlg.lblWell.setText("")
            self.dlg.lblInc.setText("")
            self.dlg.lblFoosec.setText("")
            #Read output table to get values for graph
            firstmatrix = True
            quitproc = False
            totalmatrix = []
            for row in range(self.dlg.tableWidgetDetail.rowCount()):
                rowdata = []
                isfirstcol = True
                for column in range(self.dlg.tableWidgetDetail.columnCount()):
                    item = self.dlg.tableWidgetDetail.item(row, column)
                    if item is not None:
                        if '---------------------------------' in item.text() and not firstmatrix:
                            quitproc = True
                            break
                        firstmatrix = False
                        rowdata.append(unicode(item.text()).encode('utf8'))
                        if isfirstcol:
                            totalmatrix.append(rowdata)
                            isfirstcol = False
                    else:
                        rowdata.append('')
                    if quitproc:
                        break
                    isfirstcol = False
                if quitproc:
                    break

            tt = []
            rd = []
            for i in range(len(totalmatrix)):
                if '---------------------------------' in totalmatrix[i][0]:
                    pass
                else:
                    for j in range(len(totalmatrix[i])):
                        if totalmatrix[i][j]:
                            rd.append(unicode(totalmatrix[i][j]).encode('utf8'))
                        else:
                            rd.append("")
                    tt.append(rd)
                    rd = []

            vv = []
            #Sort matrix on columns 1 and 2
            self.graphItemsList = sorted(tt, key = operator.itemgetter(0, 1))

            ctr = 1
            for telem in self.graphItemsList:
                telem.append(ctr)
                ctr = ctr + 1

            #Get only first field, scale name
            lst2 = [item[0] for item in self.graphItemsList]
            #Create unique list
            lst3 = set(lst2)
            lst4 = sorted(lst3, key = operator.itemgetter(0))

            self.dlg.listWidgetScaleNames.clear()
            for telem in lst4:
                item = QListWidgetItem(telem)
                self.dlg.listWidgetScaleNames.addItem(item)

            self.dlg.tableWidgetSF.setRowCount(0)

            if len(lst4) > 0:
                self.dlg.listWidgetScaleNames.setCurrentRow(0);
                self.redrawGraph(self.dlg.listWidgetScaleNames.item(0).text())
        except:
            self.dlg.error.setPlainText("General error drawing graph. [17]")

        #Styling graph labels and axis ***************************************
        #*********************************************************************
        #Refer to these pages for reference on axis and label item parameters
        #http://www.pyqtgraph.org/documentation/graphicsItems/axisitem.html
        #http://www.pyqtgraph.org/documentation/_modules/pyqtgraph/graphicsItems/AxisItem.html
        labelStyle = {'color': '#333', 'font-size': '7pt', 'margin': '0', 'padding': '0', 'border-style': 'none'}

        self.dlg.graphicsView.setLabel('left', text='Contribution in sel. area', units='%', unitPrefix=None, **labelStyle)
        #This sets the space between the legend and the ticks. It is huge by default and needs to be reduced.
        self.dlg.graphicsView.getAxis('left').setWidth(w=34)
        
        self.dlg.graphicsView.setLabel('bottom', text='Spatial feature (legend see below)', units=None, unitPrefix=None, **labelStyle)
        #This sets the space between the legend and the ticks. It is huge by default and needs to be reduced.
        self.dlg.graphicsView.getAxis('bottom').setHeight(h=24)
        
        #These were tested and they work. They are not used but should be retained for possible future use 
        #since they are difficult to find on the web
        #self.dlg.graphicsView.setFixedWidth(200)
        #self.dlg.graphicsView.getAxis('left').setStyle(tickTextOffset = -10)

        #Trying to color one tick item. Does not work.
        #self.dlg.graphicsView.tickSliderItem(orientation='bottom', allowAdd=False)
        #w3 = pg.GradientWidget(orientation='bottom')
        #w3.setTickColor(2, QColor(255,0,0))
        #self.dlg.graphicsView.addWidget(w3,0,1)
        

    def doGraphPointer(self, xseries):

        #So it will run. Remove when ready to develop more.
        pass

        plt = self.dlg.graphicsView
        # Anchor doesn't draw anything, it just tracks a position in the viewbox
        anchor = Anchor(plt.plotItem.vb, [xseries, 1], x=True, y=True)
        anchor.setParentItem(plt.plotItem)
        # Attach any shape to the anchor
        marker = pg.QtGui.QGraphicsEllipseItem(-10, -10, 20, 20)
        marker.setPos(20, 0)
        marker.setPen(pg.mkPen('y', width=3))
        marker.setParentItem(anchor)
        

    def redrawGraph(self, scalename):
        try:
            self.sfr = scalename

            self.dlg.lblWell.setText("")
            self.dlg.lblInc.setText("")
            self.dlg.lblFoosec.setText("")

            self.dlg.tableWidgetSF.setRowCount(0)
            self.dlg.graphicsView.clear()

            #Get unique spatial features for this scale name and sort
            fl = []
            for it in self.graphItemsList:
                if it[0] == scalename:
                    fl.append(str(it[1]))
            lst3 = set(fl)
            lst4 = sorted(lst3, key = operator.itemgetter(0))

            for it in lst4:
                    rowPosition = self.dlg.tableWidgetSF.rowCount()
                    self.dlg.tableWidgetSF.insertRow(rowPosition)
                    self.dlg.tableWidgetSF.setItem(rowPosition, 0, QtGui.QTableWidgetItem(it))
                    self.dlg.tableWidgetSF.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetSF.verticalHeader().minimumSectionSize())
                    self.dlg.tableWidgetSF.setRowHeight(rowPosition,17)

            well = []
            wellt = 0
            for it in self.graphItemsList:
                if it[0] == scalename:
                    well.append(float(it[3])) #Wellb for scale in sel area
                    wellt = wellt + float(it[3])
            self.dlg.lblWell.setText('Wellbeing:' + '{:6.2f}'.format(wellt))
            self.dlg.lblWell.setStyleSheet("QLabel {color: #1e6aaf;}")

            inc = []
            inct = 0
            for it in self.graphItemsList:
                if it[0] == scalename:
                    inc.append(float(it[5])) #Income for scale in sel area
                    inct = inct + float(it[5])
            self.dlg.lblInc.setText('Income:' + '{:6.2f}'.format(inct))
            self.dlg.lblInc.setStyleSheet("QLabel {color: #e58e4c;}")

            fsec = []
            fsect = 0
            for it in self.graphItemsList:
                if it[0] == scalename:
                    fsec.append(float(it[7])) #Income for scale in sel area
                    fsect = fsect + float(it[7])
            self.dlg.lblFoosec.setText('Food sec.:' + '{:6.2f}'.format(fsect))
            self.dlg.lblFoosec.setStyleSheet("QLabel {color: #a5a5a5;}")

            #Wellbeing
            x1 = numpy.array(range(1,len(well)))
            y1 = numpy.array(well)

            wellb = pg.BarGraphItem(x=x1, height=y1, width=0.2, brush=QBrush(QColor.fromRgb(30,106,175)))
            #wellb = pg.BarGraphItem(x=x1, height=y1, width=0.2, brush=QBrush(QColor.fromRgb(30,106,175)), pens=par)
            self.dlg.graphicsView.addItem(wellb)

            #Income
            x2 = numpy.array(range(1,len(inc)))
            y2 = numpy.array(inc)
            income = pg.BarGraphItem(x=x2-0.2, height=y2, width=0.2, brush=QBrush(QColor.fromRgb(229,142,76)))
            self.dlg.graphicsView.addItem(income)

            #Food security
            x3 = numpy.array(range(1,len(fsec)))
            y3 = numpy.array(fsec)
            foodsec = pg.BarGraphItem(x=x3+0.2, height=y3, width=0.2, brush=QBrush(QColor.fromRgb(165,165,165)))
            self.dlg.graphicsView.addItem(foodsec)
        except:
            self.dlg.error.setPlainText("Error redrawing graph. [96]")

    def tableWidgetSFClicked(self, row, column):
        pass
        #Deactivate for now since this requires more development such as deleting the previous shapes when running again
        #self.redrawGraph(self.sfr)
        #self.doGraphPointer(row+1)


    def tableWidgetLayersClicked(self, index):
        try:
            row = index.row()
            cs = self.dlg.tableWidgetLayers.item(row, 0)
            if self.dlg.tableWidgetLayers.item(row, 0).text() != 'Unloaded but available layers:':
                chk = self.dlg.tableWidgetLayers.item(row, 2).text()
                nam = self.dlg.tableWidgetLayers.item(row, 5).text() #with extension .shp
                namwo = os.path.splitext(self.dlg.tableWidgetLayers.item(row, 5).text())[0] # w/o shp

                #Was unchecked and has now been checked
                if chk == 'not loaded' and cs.checkState() == QtCore.Qt.Checked:
                    sfile = os.path.join(self.last_opened_project_dir, nam) + ".shp"

                    #Reference about nodes: https://www.lutraconsulting.co.uk/blog/2014/07/25/qgis-layer-tree-api-part-2/
                    layer = QgsVectorLayer(sfile, namwo, "ogr")

                    root = QgsProject.instance().layerTreeRoot()
                    mygroup = root.findGroup("ELVIS")
                    if mygroup == None:
                        #In following line, the second parameter set to False means that the layer is not shown in the tree root. 
                        #Hence we add manually to control where it goes
                        ly = QgsMapLayerRegistry.instance().addMapLayer(layer, False) 
                        root.addLayer(layer)
                    else:
                        ly = QgsMapLayerRegistry.instance().addMapLayer(layer, False) 
                        mygroup.insertChildNode(-1, QgsLayerTreeLayer(layer.id()))

                    for agl in range(len(self.projectlayers)):
                        if nam == self.projectlayers[agl][3]:
                            self.projectlayers[agl][1] = 'loaded'
                    self.GUILayersResync()
                    return

                #Was checked and has now been unchecked
                if chk == 'loaded' and cs.checkState() == QtCore.Qt.Unchecked:
                    for layer in QgsMapLayerRegistry.instance().mapLayers().values():
                        if nam == layer.name():
                            QgsMapLayerRegistry.instance().removeMapLayer(layer)
                    for agl in range(len(self.projectlayers)):
                        if nam == self.projectlayers[agl][3]:
                            self.projectlayers[agl][1] = 'not loaded'
                    self.GUILayersResync()
                    return
        except:
            self.dlg.error.setPlainText("Unable to load or unload a layer. [66]")


    def listWidgetScaleNamesItemClicked(self, item):
        self.redrawGraph(item.text())


    def delRubberClicked(self):
        self.delRubberband()


    def delRubberband(self):
        self.iface.mapCanvas().scene().removeItem(self.myRubberBand)
        for treeLayer in self.project.layerTreeRoot().findLayers():                
            layer_f2 = treeLayer.layer()
            if layer_f2.name() == "rubber_band":
                QgsMapLayerRegistry.instance().removeMapLayer(layer_f2.id())


    def butClearErrorClicked(self):
        self.dlg.error.setPlainText("")


    def DoELVISProgramInfo(self):
        try:
            self.elvinf = ELVISProgramInfo()
            self.elvinf.setModal(True)
            self.elvinf.setWindowIcon(QtGui.QIcon(':/plugins/ELVIS/resources/ELVIS16.png'))
            pixmap = QPixmap(':/plugins/ELVIS/resources/CSIROs.png')
            self.elvinf.lblCSIRO.setPixmap(pixmap)
            pixmap = QPixmap(':/plugins/ELVIS/resources/ausaid.png')
            self.elvinf.lblAusaid.setPixmap(pixmap)
            pixmap = QPixmap(':/plugins/ELVIS/resources/cepa2.png')
            self.elvinf.lblCEPA.setPixmap(pixmap)
            pixmap = QPixmap(':/plugins/ELVIS/resources/tnc2.png')
            self.elvinf.lblTNC.setPixmap(pixmap)
            pixmap = QPixmap(':/plugins/ELVIS/resources/enb2.png')
            self.elvinf.lblENB.setPixmap(pixmap)
            pixmap = QPixmap(':/plugins/ELVIS/resources/wnb2.png')
            self.elvinf.lblWNB.setPixmap(pixmap)
            pixmap = QPixmap(':/plugins/ELVIS/resources/cti2.png')
            self.elvinf.lblCTI.setPixmap(pixmap)
            self.elvinf.show()
        except:
            self.dlg.error.setPlainText("Could not open info window. [59]")


    def btnInfo2Clicked(self):
        try:
            if self.dlginfo2:
                self.dlginfo2.activateWindow()
        except: #If try fails then the window is not open. So we open a new instance.
            self.dlginfo2 = MVinfo2()
            self.dlginfo2.butCloseInfo2.clicked.connect(self.butCloseInfo2Clicked)
            self.dlginfo2.setModal(False)
            self.dlginfo2.setWindowIcon(QtGui.QIcon(':/plugins/ELVIS/resources/ELVIS16.png'))

            QApplication.setOverrideCursor(Qt.WhatsThisCursor);
            self.tool2 = PointTool2(self.iface.mapCanvas(), self.dlg.list_of_values, self.dlg.list_of_values_fields, self.dlginfo2)
            self.iface.mapCanvas().setMapTool(self.tool2)
            self.dlginfo2.tableWidget.setColumnWidth(0,200)
            self.dlginfo2.tableWidget.setColumnWidth(1,70)
            self.dlginfo2.tableWidget.setColumnWidth(2,150)
            self.dlginfo2.tableWidget.setColumnWidth(3,150)
            self.dlginfo2.show()
            self.dlginfo2.setWindowTitle("ELVIS feature info")


    def butCloseInfo2Clicked(self):
        self.iface.mapCanvas().unsetMapTool(self.tool2)
        self.dlginfo2.close()

    def InitLayerList(self):
        try:
            #In memory list of project layers and types
            self.projectlayers = []
            for f in listdir(self.last_opened_project_dir):
                if isfile(join(self.last_opened_project_dir, f)):
                    shapef = join(self.last_opened_project_dir, f)
                    if f.endswith('.shp'):
                        fo = os.path.splitext(f)[0] # w/o shp                    
                        if basename(f).endswith('_DIS.shp') or basename(f).endswith('_ECO.shp') or basename(f).endswith('_LLG.shp'):
                            cons = []
                            cons.append('99999')       # 0 - sortkey
                            cons.append('not loaded')  # 1 - loaded/ticked status
                            tlayer = QgsVectorLayer(shapef, "testing_geometry", "ogr")
                            if tlayer.wkbType() == 1:
                                cons.append('point')       # 2 - type
                            elif tlayer.wkbType() == 3:
                                cons.append('polygon')     # 2 - type
                            else:
                                cons.append('unsupported') # 2 - type
                            cons.append(fo)                 # 3 - layername with path
                            self.projectlayers.append(cons)
                            tlayer = None

            #If layer is loaded in project, set it to loaded in projectlayer list 
            for agl in self.projectlayers:
                shp = os.path.splitext(agl[3])[0] #Get just filename
                if QgsMapLayerRegistry.instance().mapLayersByName(shp):
                    agl[1] = 'loaded'
            #Sort loaded layers first, then layer name
            self.projectlayers = sorted(self.projectlayers, key = operator.itemgetter(1, 3))
        except:
            self.dlg.error.setPlainText("Error while initial load of layers. [65]")


    def GUILayersResync(self):
        try:
            self.projectlayers = sorted(self.projectlayers, key = operator.itemgetter(0, 1))

            grecol = QColor.fromRgb(152,152,152)
            whtcol = QColor.fromRgb(255,255,255)
            xFont=QtGui.QFont()
            xFont.setBold(True)
            self.dlg.tableWidgetLayers.setRowCount(0)
            divider_inserted = False
            if self.projectlayers:
                for ll in self.projectlayers:
                    #Insert divider before first unloaded layer
                    if ll[1] == 'not loaded' and not divider_inserted:
                        rowPosition = self.dlg.tableWidgetLayers.rowCount()
                        self.dlg.tableWidgetLayers.insertRow(rowPosition)
                        self.dlg.tableWidgetLayers.setItem(rowPosition, 0, QtGui.QTableWidgetItem('Unloaded but available layers:'))
                        self.dlg.tableWidgetLayers.setRowHeight(rowPosition,17) 
                        self.dlg.tableWidgetLayers.item(rowPosition, 0).setBackground(QBrush(grecol))
                        self.dlg.tableWidgetLayers.item(rowPosition, 0).setForeground(QBrush(whtcol))
                        self.dlg.tableWidgetLayers.item(rowPosition, 0).setFont(xFont)
                        self.dlg.tableWidgetLayers.setSpan(rowPosition, 0, 1, 6)
                        divider_inserted = True
                    chkBoxItem = QTableWidgetItem()
                    chkBoxItem.setFlags(Qt.ItemIsUserCheckable|Qt.ItemIsEnabled)
                    if ll[1] == 'not loaded':
                        chkBoxItem.setCheckState(Qt.Unchecked)
                    if ll[1] == 'loaded':
                        chkBoxItem.setCheckState(Qt.Checked)
                    icon_item = QTableWidgetItem()
                    if ll[2] == 'polygon':
                        icon = QIcon(':/plugins/ELVIS/resources/polys.png')
                    elif ll[2] == 'point':
                        icon = QIcon(':/plugins/ELVIS/resources/points.png')
                    icon_item.setIcon(icon)
                    rowPosition = self.dlg.tableWidgetLayers.rowCount()
                    self.dlg.tableWidgetLayers.insertRow(rowPosition)
                    self.dlg.tableWidgetLayers.setItem(rowPosition, 0, chkBoxItem)
                    self.dlg.tableWidgetLayers.setItem(rowPosition, 1, QtGui.QTableWidgetItem(ll[0]))
                    self.dlg.tableWidgetLayers.setItem(rowPosition, 2, QtGui.QTableWidgetItem(ll[1]))
                    self.dlg.tableWidgetLayers.setItem(rowPosition, 3, QtGui.QTableWidgetItem(icon_item))
                    self.dlg.tableWidgetLayers.setItem(rowPosition, 4, QtGui.QTableWidgetItem(ll[2]))
                    self.dlg.tableWidgetLayers.setItem(rowPosition, 5, QtGui.QTableWidgetItem(ll[3]))
                    self.dlg.tableWidgetLayers.setRowHeight(rowPosition,17) 

            if not divider_inserted:
                rowPosition = self.dlg.tableWidgetLayers.rowCount()
                self.dlg.tableWidgetLayers.insertRow(rowPosition)
                self.dlg.tableWidgetLayers.setItem(rowPosition, 0, QtGui.QTableWidgetItem('Unloaded but available layers:'))
                self.dlg.tableWidgetLayers.setRowHeight(rowPosition,17) 
                self.dlg.tableWidgetLayers.item(rowPosition, 0).setBackground(QBrush(grecol))
                self.dlg.tableWidgetLayers.item(rowPosition, 0).setForeground(QBrush(whtcol))
                self.dlg.tableWidgetLayers.item(rowPosition, 0).setFont(xFont)
                self.dlg.tableWidgetLayers.setSpan(rowPosition, 0, 1, 6)
        except:
            self.dlg.error.setPlainText("Error in resync of layers. [20]")


    def saveProjectClicked(self):
        try:
            if self.project.write():
                self.dlg.error.setPlainText("Project saved")
            else:
                self.dlg.error.setPlainText("Project not saved. File may be write-protected. [09]")
        except:
            self.dlg.error.setPlainText("General error while saving project. [10]")


    def renderTest(self, painter):
        #Use painter for drawing to map canvas
        pass

    def pushButtonExportClicked(self):
        path = QtGui.QFileDialog.getSaveFileName(None,"Export data",self.plugin_dir,"Comma Separated Values Spreadsheet (*.csv);;""All Files (*)")
        if not path:
            return
        else:
            try:
                with open(unicode(path), 'wb') as stream:
                    writer = csv.writer(stream, delimiter=',')

                    f = ["ECOLOGICAL VALUES DATABASE - ELVIS"]
                    writer.writerow(f)

                    ndate = datetime.date.today()
                    n_day = "%02d" % (ndate.day,) 
                    n_mon = "%02d" % (ndate.month,) 
                    n_yea = "%04d" % (ndate.year,) 
                    ntime = datetime.datetime.now()
                    n_hou = "%02d" % (ntime.hour,) 
                    n_min = "%02d" % (ntime.minute,) 
                    n_sec = "%02d" % (ntime.second,) 
                    dt = n_day + "/" + n_mon + "/" + n_yea +  " " + n_hou + ":" + n_min + ":" + n_sec
                    f = ["Output created:", dt]
                    writer.writerow(f)
                    scalet = "Scale type: " + self.cur_scale_id
                    f = [scalet]
                    writer.writerow(f)

                    writer.writerow("")
                    f = ["AREA SELECTED COORDINATES"]
                    writer.writerow(f)

                    f = ["Selection coordinates:"]
                    writer.writerow(f)
                    f = ["Longitude", "Latitude"]
                    writer.writerow(f)

                    for pt in self.rubberbandPoints:
                        rowdata = []
                        px = "{0:.5f}".format(round(float(str(pt[0])),5))
                        rowdata.append(px)
                        py = "{0:.5f}".format(round(float(str(pt[1])),5))
                        rowdata.append(py)  
                        writer.writerow(rowdata)

                    writer.writerow("")
                    h = ["AREA VALUES"]
                    writer.writerow("")
                    h = ["Natural resource values"]
                    writer.writerow(h)
                    writer.writerow("")

                    h = ["Contribution of EGS"]
                    writer.writerow(h)

                    wellb_whole_scale = 0
                    wellb_sel_area = 0
                    wellb_sel_are_perc = 0

                    income_whole_scale = 0
                    income_sel_area = 0
                    income_sel_are_perc = 0

                    foodsec_whole_scale = 0
                    foodsec_sel_area = 0
                    foodsec_sel_are_perc = 0

                    h = ["Scale name","Spatial feature/Value","Wellbeing value for Scale-name","Well-being value for scale name in area selected","Income value for Scale-name","Income value for scale name in area selected","Food security value for Scale-name","Food security value for scale name in area selected","Area of spatial feature selected km2","Area of spatial feature total km2"]
                    writer.writerow(h)

                    #For summarizing later
                    totalmatrix = []
                    firstmatrix = True
                    quitproc =  False

                    for row in range(self.dlg.tableWidgetDetail.rowCount()):
                        rowdata = []
                        isfirstcol = True
                        for column in range(self.dlg.tableWidgetDetail.columnCount()):
                            item = self.dlg.tableWidgetDetail.item(row, column)
                            if item is not None:
                                if '---------------------------------' in item.text() and not firstmatrix:
                                    quitproc = True
                                    break
                                firstmatrix = False
                                rowdata.append(unicode(item.text()).encode('utf8'))
                                if isfirstcol:
                                    totalmatrix.append(rowdata)
                                    isfirstcol = False
                            else:
                                rowdata.append('')
                            if quitproc:
                                break
                            isfirstcol = False
                        if quitproc:
                            break
                        writer.writerow(rowdata)
                    writer.writerow("")

                    #Sums per contribution
                    sum_col2 = 0.0
                    sum_col3 = 0.0
                    sum_col4 = 0.0
                    sum_col5 = 0.0
                    sum_col6 = 0.0
                    sum_col7 = 0.0
                    sum_col8 = 0.0
                    sum_col9 = 0.0
                    for i in range(len(totalmatrix)):
                        for j in range(len(totalmatrix[i])):
                            if totalmatrix[i][j]:
                                if j == 2:
                                    sum_col2 = sum_col2 + float(totalmatrix[i][j])
                                if j == 3:
                                    sum_col3 = sum_col3 + float(totalmatrix[i][j])
                                if j == 4:
                                    sum_col4 = sum_col4 + float(totalmatrix[i][j])
                                if j == 5:
                                    sum_col5 = sum_col5 + float(totalmatrix[i][j])
                                if j == 6:
                                    sum_col6 = sum_col6 + float(totalmatrix[i][j])
                                if j == 7:
                                    sum_col7 = sum_col7 + float(totalmatrix[i][j])
                                if j == 8:
                                    sum_col8 = sum_col8 + float(totalmatrix[i][j])
                                if j == 9:
                                    sum_col9 = sum_col9 + float(totalmatrix[i][j])

                    #Sums per contribution and scale
                    sum_contsca_col2 = []
                    for i in range(len(totalmatrix)):
                        if '---------------------------------' in totalmatrix[i][0]:
                            pass
                        else:
                            upd4 = False
                            for srw in sum_contsca_col2:
                                if totalmatrix[i][0] == srw[0]:
                                    srw[2] = srw[2] + float(totalmatrix[i][2])
                                    srw[3] = srw[3] + float(totalmatrix[i][3])
                                    srw[4] = srw[4] + float(totalmatrix[i][4])
                                    srw[5] = srw[5] + float(totalmatrix[i][5])
                                    srw[6] = srw[6] + float(totalmatrix[i][6])
                                    srw[7] = srw[7] + float(totalmatrix[i][7])
                                    srw[8] = srw[8] + float(totalmatrix[i][8])
                                    srw[9] = srw[9] + float(totalmatrix[i][9])
                                    upd4 = True
                            if not upd4:
                                rowda = []
                                pval = totalmatrix[i][0]
                                rowda.append(pval)
                                rowda.append("") #Placeholder for unused column 1. So indices match up with totalmatrix eventhough we don't have spatial feature/value

                                for g in (2,3,4,5,6,7,8,9):
                                    pval = totalmatrix[i][g]
                                    if pval:
                                        rowda.append(float(pval))
                                    else:
                                        rowda.append(0)
                                sum_contsca_col2.append(rowda)

                    f = ["Contribution of N.R. to Overall Wellbeing (%)"]
                    writer.writerow(f)
                    writer.writerow("")
                    f = ["Scale name", "", "For whole scale name (%)", "In selected area (%)", "% in selected area"]
                    writer.writerow(f)
                    rwd3 = []
                    if sum_contsca_col2:
                        for srw in sum_contsca_col2:
                            rwd3.append(unicode(srw[0]).encode('utf8'))
                            rwd3.append("")
                            rwd3.append(unicode(srw[2]).encode('utf8'))
                            rwd3.append(unicode(srw[3]).encode('utf8'))
                            if srw[2] != 0:
                                perse = srw[3] / srw[2] * 100
                            else:
                                perse = 0
                            rwd3.append(unicode(perse).encode('utf8'))
                            writer.writerow(rwd3)
                            rwd3 = []
                    writer.writerow("")

                    f = ["Contribution of N.R. to Overall Income (%)"]
                    writer.writerow(f)
                    writer.writerow("")
                    f = ["Scale name", "", "For whole scale name (%)", "In selected area (%)", "% in selected area"]
                    writer.writerow(f)
                    rwd3 = []
                    if sum_contsca_col2:
                        for srw in sum_contsca_col2:
                            rwd3.append(unicode(srw[0]).encode('utf8'))
                            rwd3.append("")
                            rwd3.append(unicode(srw[4]).encode('utf8'))
                            rwd3.append(unicode(srw[5]).encode('utf8'))
                            if srw[4] != 0:
                                perse = srw[5] / srw[4] * 100
                            else:
                                perse - 0
                            rwd3.append(unicode(perse).encode('utf8'))
                            writer.writerow(rwd3)
                            rwd3 = []
                        writer.writerow("")

                    f = ["Contribution of N.R. to Overall Food security (%)"]
                    writer.writerow(f)
                    writer.writerow("")
                    f = ["Scale name", "", "For whole scale name (%)", "In selected area (%)", "% in selected area"]
                    writer.writerow(f)
                    rwd3 = []
                    if sum_contsca_col2:
                        for srw in sum_contsca_col2:
                            rwd3.append(unicode(srw[0]).encode('utf8'))
                            rwd3.append("")
                            rwd3.append(unicode(srw[6]).encode('utf8'))
                            rwd3.append(unicode(srw[7]).encode('utf8'))
                            if srw[6] != 0:
                                perse = srw[7] / srw[6] * 100
                            else:
                                perse = 0
                            rwd3.append(unicode(perse).encode('utf8'))
                            writer.writerow(rwd3)
                            rwd3 = []
                        writer.writerow("")

                    h = ["Contribution of Features (%)"]
                    writer.writerow(h)
                    writer.writerow("")
                    h = ["Scale name","Spatial feature","Wellbeing value for Scale-name","Well-being value for scale name in area selected","Income value for Scale-name","Income value for scale name in area selected","Food security value for Scale-name","Food security value for scale name in area selected","Area of spatial feature selected km2","Area of spatial feature total km2"]
                    writer.writerow(h)
                    tt = []
                    rd = []
                    for i in range(len(totalmatrix)):
                        if '---------------------------------' in totalmatrix[i][0]:
                            pass
                        else:
                            for j in range(len(totalmatrix[i])):
                                if totalmatrix[i][j]:
                                    rd.append(unicode(totalmatrix[i][j]).encode('utf8'))
                                else:
                                    rd.append("")
                            tt.append(rd)
                            rd = []
                    vv = []
                    #Sort matrix on columns 1 and 2
                    vv = sorted(tt, key = operator.itemgetter(0, 1))
                    for e4 in vv:
                        writer.writerow(e4)
                    writer.writerow("")

                    h = ["Contribution of EGS"]
                    writer.writerow(h)

                    tmatrix = []
                    firstmat = True
                    endproc = False
                    for row in range(self.dlg.tableWidgetDetail.rowCount()):
                        esc = False
                        rowdata = []
                        for column in range(self.dlg.tableWidgetDetail.columnCount()):
                            item = self.dlg.tableWidgetDetail.item(row, column)
                            if item is not None:
                                if '---------------------------------' in item.text():
                                    if firstmat:
                                        firstmat = False
                                    else:
                                        endproc = True
                                        break
                                    esc = True
                                    break
                                rowdata.append(unicode(item.text()).encode('utf8'))
                            else:
                                rowdata.append("")
                        if endproc:
                            break
                        if not esc:
                            tmatrix.append(rowdata)

                    #Add first column text to sub-items
                    titl = ""
                    for i in range(len(tmatrix)):
                        if tmatrix[i][0]:
                            titl = tmatrix[i][0]
                            tmatrix[i][0] = "" #Clear text in first cell just so we can delete this sum row later by searching for empty cell
                        else:
                            tmatrix[i][0] = titl
                    #Now remove higher level items (features)
                    newm = []
                    for i in range(len(tmatrix)):
                        if tmatrix[i][0] is not "":
                            newm.append(tmatrix[i])
                    #Sort matrix on columns 1 and 2
                    gg = []
                    gg = sorted(newm, key = operator.itemgetter(0, 1))


                    writer.writerow("")
                    h = ["Scale name","EGS","Wellbeing value for Scale-name","Well-being value for scale name in area selected","Income value for Scale-name","Income value for scale name in area selected","Food security value for Scale-name","Food security value for scale name in area selected"]
                    writer.writerow(h)
                    roawda4 = []
                    for i in range(len(gg)):
                        lin = []
                        for de in range(len(gg[i])):
                            lin.append(unicode(gg[i][de]).encode('utf8'))
                        writer.writerow(lin)
                    writer.writerow("")

                    isheader = False
                    for row in range(self.dlg.tableWidgetDetailCounts.rowCount()):
                        rowdata2 = []
                        it = self.dlg.tableWidgetDetailCounts.item(row, 1).text()
                        if it == "": #This is a header row
                            isheader = True
                            writer.writerow("") #Leading blank line
                        else:
                            isheader = False
                        for column in range(self.dlg.tableWidgetDetailCounts.columnCount()):
                            item = self.dlg.tableWidgetDetailCounts.item(row, column)
                            if item is not None:
                                rowdata2.append(unicode(item.text()).encode('utf8'))
                            else:
                                rowdata2.append("")
                        writer.writerow(rowdata2)
                        if isheader:
                            writer.writerow("") #Leading blank line
                            h = ["Scale name","Value locations","Count"]
                            writer.writerow(h)
            except:
                self.dlg.error.setPlainText("Error while exporting. Ensure that an area is selected. [33]")


    def pushButtonPanClicked(self):
        self.iface.actionPan().trigger()


    def pushButtonZoomPlusClicked(self):
        self.iface.actionZoomIn().trigger()


    def pushButtonZoomMinusClicked(self):
        self.iface.actionZoomOut().trigger()


    def rubberbandClicked(self):
        try:
            #Delete any pre-existing rubberband layer
            self.delRubberband()

            self.rubberbandPoints = []
            self.previousMapTool = self.iface.mapCanvas().mapTool()
            self.myMapTool = QgsMapToolEmitPoint(self.iface.mapCanvas())
            self.myMapTool.canvasClicked.connect(self.manageClick)
            self.myRubberBand = QgsRubberBand(self.iface.mapCanvas(), QGis.Polygon)
            color = QColor("green")
            color.setAlpha(50)
            self.myRubberBand.setColor(color)
            self.iface.mapCanvas().xyCoordinates.connect(self.showRBCoordinates)
            self.iface.mapCanvas().setMapTool(self.myMapTool)
        except:
            self.dlg.error.setPlainText("Error while initializing rubberband. [12]")


    def showRBCoordinates(self, currentPos):
        if self.myRubberBand and self.myRubberBand.numberOfVertices():
            self.myRubberBand.removeLastPoint()
            self.myRubberBand.addPoint(currentPos)


    def manageClick(self, currentPos, clickedButton):
        if clickedButton == Qt.LeftButton:
            self.myRubberBand.addPoint(currentPos)

        if clickedButton == Qt.RightButton:
            self.iface.mapCanvas().xyCoordinates.disconnect(self.showRBCoordinates)
            self.iface.mapCanvas().setMapTool(self.previousMapTool)
            self.RBMode = "user"
            self.procAreaSelection('points')


    def procAreaSelection(self, proc_type):
        try:
            self.dlg.tableWidgetDetail.setRowCount(0)
            self.dlg.tableWidgetDetailCounts.setRowCount(0)
            geom_rb = self.myRubberBand.asGeometry()

            #Delete any pre-existing rubberband layer
            self.delRubberband()

            #Create in-memory layer from Rubberband geometry for later processing
            vlx = QgsVectorLayer("Polygon?crs=epsg:4326", "rubber_band", "memory")
            prx = vlx.dataProvider()
            # Enter editing mode
            vlx.startEditing()
            # Add fields
            prx.addAttributes( [ QgsField("id", QVariant.Int) ] )
            # Add a feature
            fetx = QgsFeature()

            #Get geometry from rubberband list
            if proc_type == 'points':
                fetx.setGeometry(geom_rb)
                fetx.setAttributes([0, "Feature"])
                prx.addFeatures( [ fetx ] )
            #Get geometry from  polygon in shapefile (passed into this function via proc_type parameter)
            else:
                layer = QgsVectorLayer(proc_type, 'import_rubberband', "ogr")
                cfeature = QgsFeature()
                cfeatures = []
                cfeat = layer.getFeatures()
                for xfeature in cfeat:
                    xgeometry = xfeature.geometry()
                    cfeature.setGeometry(xgeometry)
                    cfeatures.append(cfeature)
                prx.addFeatures(cfeatures)

            #Change rubberband appearance
            symbol = QgsSymbolV2.defaultSymbol(vlx.geometryType())
            symbol.setColor(QColor.fromRgb(222,109,170))
            symbol.setAlpha(0.6)
            registry = QgsSymbolLayerV2Registry.instance()
            lineMeta = registry.symbolLayerMetadata("SimpleLine")
            lineLayer = lineMeta.createSymbolLayer({'width': '1', 'color': '142,28,107'})
            symbol.appendSymbolLayer(lineLayer)

            vlx.rendererV2().setSymbol(symbol)
            vlx.commitChanges()
            QgsMapLayerRegistry.instance().addMapLayers([vlx])
            #Getting coordinates to save rubber band to tableViewRB
            clay = QgsMapLayerRegistry.instance().mapLayersByName("rubber_band")[0]

            cfeat = clay.getFeatures()
            temp_geom = []
            for fea in cfeat:
                cgeo = fea.geometry()
                multi_geom = cgeo.asPolygon()
                for pp in multi_geom:
                    for pt in pp:
                    #temp_geom.extend(i)
                        px = "{0:.5f}".format(round(float(str(pt.x())),5))
                        py = "{0:.5f}".format(round(float(str(pt.y())),5))
                        new_pt = (px,py)
                        self.rubberbandPoints.append(new_pt)

            ql = QgsMapLayerRegistry.instance().mapLayers().values()

            #List of all countable values before sumarising
            countable_nat_res = []
            countable_eco_reg = []
            countable_eco_stru_proc = []
            countable_soc_cul = []

            for layerIterator in ql:
                layname = layerIterator.name()
                #Only processing vector layers
                if layerIterator.type() == QgsMapLayer.VectorLayer:
    #POINT PROCESSING
                    if layerIterator.geometryType() == 2 or layerIterator.geometryType() == QGis.Point:
                        if layname.endswith('_LLG') or layname.endswith('_DIS') or layname.endswith('_ECO'):
                            layer = layerIterator
                            if layer:
                                if layname.endswith('_LLG'):
                                    self.cur_scale_id = "LLG"
                                if layname.endswith('_DIS'):
                                    self.cur_scale_id = "DIS"
                                if layname.endswith('_ECO'):
                                    self.cur_scale_id = "ECO"

                                clp_lay = layer.name()
                                iter = layer.getFeatures()
                                for feature in iter:
                                    geom_feat = feature.geometry()
                                
                                overlay_layer = QgsVectorLayer()

                                for treeLayer in self.project.layerTreeRoot().findLayers():                
                                    layer_t6 = treeLayer.layer()

                                    if layer_t6.name() == layname:
                                        overlay_layer = layer_t6
                                        break

                                    if layer_t6.name() == "rubber_band":
                                        layer_to_clip = layer_t6

                                #Clipping intersected area and saving it in-memory. It is layer named "Clipped"
                                processing.runandload("qgis:clip", overlay_layer, layer_to_clip, None)
                                                            
                                xres_lay = QgsMapLayerRegistry.instance().mapLayersByName("Clipped")

                                res_lay = QgsVectorLayer()
                                #Get first layer that is returned (because maplayersbyname returns a list). Syntaxt ("Clipped")[0] does not work in somce QGIS versions
                                for itl in xres_lay:
                                    res_lay = itl
                                    break
                                res_lay.updateExtents()
                                res_feat = res_lay.getFeatures()

                                #Clear selected objects list view
                                model = QStandardItemModel(0,0)
                                model = QStandardItemModel(1,1)

        #***** AREA PERCENTAGES *************************************************************************************************
                                #For layers which are processed area dependent
                                if self.cur_scale_id == "LLG" or self.cur_scale_id == "DIS":
        # H E A D E R
                                    #Red header for each layer
                                    rowPosition = self.dlg.tableWidgetDetail.rowCount()
                                    self.dlg.tableWidgetDetail.insertRow(rowPosition)
                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 0, QtGui.QTableWidgetItem(layname + " ---------------------------------"))
                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 1, QtGui.QTableWidgetItem(""))
                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 2, QtGui.QTableWidgetItem(""))
                                    self.dlg.tableWidgetDetail.setSpan(rowPosition, 0, 1, 10)
                                    self.dlg.tableWidgetDetail.item(rowPosition,0).setForeground(QBrush(QColor.fromRgb(255,255,255)))
                                    self.dlg.tableWidgetDetail.item(rowPosition,0).setBackground(QBrush(QColor.fromRgb(30,106,175)))
                                    self.dlg.tableWidgetDetail.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetail.verticalHeader().minimumSectionSize())
                                    self.dlg.tableWidgetDetail.setRowHeight(rowPosition,17)

                                    idx_llg_dist = ""
                                    idx_spatfeat = res_lay.fieldNameIndex('spat_feat')
                                    if self.cur_scale_id == "LLG":
                                        idx_llg_dist = res_lay.fieldNameIndex('llg')
                                    if self.cur_scale_id == "DIS":
                                        idx_llg_dist = res_lay.fieldNameIndex('district')
                                    idx_shapar = res_lay.fieldNameIndex('shape_area')
                                    idx_foodsec = res_lay.fieldNameIndex('food_secur')
                                    idx_wellbeing = res_lay.fieldNameIndex('well_being')
                                    idx_income = res_lay.fieldNameIndex('income')

                                    for f in res_feat:
                                        rub = None
                                        shapar = 0.0
                                        csomt = 0.0
                                        csomtot = 0.0
                                        cs_wellb = 0.0
                                        cs_wellbs  = 0.0
                                        cs_inco = 0.0
                                        cs_incos = 0.0
                                        cs_foosec = 0.0
                                        cs_foosecs = 0.0
                                        spat_feat_qry = ""
                                        llg_qry = ''
                                        res_geom = f.geometry()

                                        if f.attributes:
                                            attry = f.attributes()

                                            #Calc totals
                                            if len(attry) > 2:
                                                if res_geom != None:
                                                    d = QgsDistanceArea()
                                                    d.setEllipsoidalMode(True)
                                                    art = res_geom.area()
                                                    ar = d.convertMeasurement(art, QGis.Degrees, QGis.Kilometers, True)     
                                                    arx = str(ar[0])
                                                    rub = ar[0] #rub is used further down where each sub area is retrieved from list
                                                    shapar = attry[idx_shapar] #shapar (feature area) is used further down where each sub area is retrieved from list

                                                    #self.dlg.area_value_matrix:
                                                    # 0 - value_name
                                                    # 1 - spatial_feature_name
                                                    # 2 - scale_name
                                                    # 3 - scale_id
                                                    # 4 - wellbeing (= value_metric_score of records where value_metric_description = "Importance for human wellbeing")
                                                    # 5 - income (= value_metric_score of records where value_metric_description = "Importance for income")
                                                    # 6 - food_security (= value_metric_score of records where value_metric_description = "Importance for food security")

                                                    for cgs in self.dlg.area_value_matrix:
                                                        if (cgs[3] == "llg" and self.cur_scale_id == "LLG") or (cgs[3] == "dist" and self.cur_scale_id == "DIS"):
                                                            #Looking for all that are in the same spatial_feature category
                                                            if cgs[1] == attry[idx_spatfeat]:
                                                                #Looking for all that are in the same LLG/District
                                                                if cgs[2] == attry[idx_llg_dist]:
                                                                    cs_wellb = float(cgs[4])
                                                                    cs_wellbs = cs_wellbs + cs_wellb
                                                                    cs_inco = float(cgs[5])
                                                                    cs_incos = cs_incos + cs_inco
                                                                    cs_foosec = float(cgs[6])
                                                                    cs_foosecs = cs_foosecs + cs_foosec

                                                    #Calculating wellb, income and food sec values per selected areas 
                                                    selare_wellb = cs_wellbs * (float(arx) / float(shapar))
                                                    selare_inco = cs_incos * (float(arx) / float(shapar))
                                                    selare_foosec = cs_foosecs * (float(arx) / float(shapar))

                                                rowPosition = self.dlg.tableWidgetDetail.rowCount()
                                                self.dlg.tableWidgetDetail.insertRow(rowPosition)
                                                self.dlg.tableWidgetDetail.setItem(rowPosition, 0, QtGui.QTableWidgetItem(attry[idx_llg_dist]))
                                                self.dlg.tableWidgetDetail.setItem(rowPosition, 1, QtGui.QTableWidgetItem(attry[idx_spatfeat]))

                                                try:
                                                    rwell = float(cs_wellbs)
                                                    rwell = "{0:.4f}".format(round(rwell,4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 2, QtGui.QTableWidgetItem(rwell))
                                                except (TypeError, UnboundLocalError):
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 2, QtGui.QTableWidgetItem("Error"))

                                                try:
                                                    xselare_wellb = float(selare_wellb)
                                                    xselare_wellb = "{0:.4f}".format(round(xselare_wellb,4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 3, QtGui.QTableWidgetItem(xselare_wellb))
                                                except (TypeError, UnboundLocalError):
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 3, QtGui.QTableWidgetItem("Error"))

                                                try:
                                                    rinco = float(cs_incos)
                                                    rinco = "{0:.4f}".format(round(rinco,4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 4, QtGui.QTableWidgetItem(rinco))
                                                except (TypeError, UnboundLocalError):
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 4, QtGui.QTableWidgetItem("Error"))

                                                try:
                                                    xselare_inco = float(selare_inco)
                                                    xselare_inco = "{0:.4f}".format(round(xselare_inco,4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 5, QtGui.QTableWidgetItem(xselare_inco))
                                                except (TypeError, UnboundLocalError):
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 5, QtGui.QTableWidgetItem("Error"))

                                                try:
                                                    rfoos = float(cs_foosecs)
                                                    rfoos = "{0:.4f}".format(round(rfoos,4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 6, QtGui.QTableWidgetItem(rfoos))
                                                except (TypeError, UnboundLocalError):
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 6, QtGui.QTableWidgetItem("Error"))

                                                try:
                                                    xselare_foosec = float(selare_foosec)
                                                    xselare_foosec = "{0:.4f}".format(round(xselare_foosec,4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 7, QtGui.QTableWidgetItem(xselare_foosec))
                                                except (TypeError, UnboundLocalError):
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 7, QtGui.QTableWidgetItem("Error"))

                                                try:
                                                    arx = "{0:.4f}".format(round(float(arx),4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 8, QtGui.QTableWidgetItem(arx))
                                                except (TypeError, UnboundLocalError):
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 8, QtGui.QTableWidgetItem("Error"))
                                                    self.dlg.error.setPlainText("Error calculating area. Invalid rubberband geometry. Select an area that has at least three points and is not self-intersecting")

                                                #shape area
                                                if shapar:
                                                    # Round to four digits and display with four digits
                                                    shapar = "{0:.4f}".format(round(float(shapar),4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 9, QtGui.QTableWidgetItem(shapar))
                                                else:
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 9, QtGui.QTableWidgetItem(""))

                                                for col in range(0,10):
                                                    self.dlg.tableWidgetDetail.item(rowPosition,col).setBackground(QBrush(QColor.fromRgb(198,187,107)))

                                            #self.dlg.area_value_matrix:
                                            # 0 - value_name
                                            # 1 - spatial_feature_name
                                            # 2 - scale_name
                                            # 3 - scale_id
                                            # 4 - wellbeing (= value_metric_score of records where value_metric_description = "Importance for human wellbeing")
                                            # 5 - income (= value_metric_score of records where value_metric_description = "Importance for income")
                                            # 6 - food_security (= value_metric_score of records where value_metric_description = "Importance for food security")

                                            #Process details
                                            for cg in self.dlg.area_value_matrix:
                                                if (cg[3] == "llg" and self.cur_scale_id == "LLG") or (cg[3] == "dist" and self.cur_scale_id == "DIS"):
                                                    #Looking for all that are in the same spatial_feature category
                                                    if cg[1] == attry[idx_spatfeat]:
                                                        #Looking for all that are in the same LLG/District
                                                        if cg[2] == attry[idx_llg_dist]:

                                                            try:
                                                                cwellb = float(cg[4]) * rub / float(shapar)
                                                                cwellb = "{0:.4f}".format(round(cwellb,4))
                                                            except TypeError:
                                                                cwellb = "Error"
                                                                self.dlg.error.setPlainText("Some errors occurred while calculating wellbeing values. Values from this run are valid, except for those marked with 'Error'. [42-1]")

                                                            try:
                                                                cinc = float(cg[5]) * rub / float(shapar)
                                                                cinc = "{0:.4f}".format(round(cinc,4))
                                                            except TypeError:
                                                                cinc = "Error"
                                                                self.dlg.error.setPlainText("Some errors occurred while calculating income values. Values from this run are valid, except for those marked with 'Error'. [42-2]")

                                                            try:
                                                                cfsec = float(cg[6]) * rub / float(shapar)
                                                                cfsec = "{0:.4f}".format(round(cfsec,4))
                                                            except TypeError:
                                                                cfsec = "Error"
                                                                self.dlg.error.setPlainText("Some errors occurred while calculating food security values. Values from this run are valid, except for those marked with 'Error'. [42-3]")

                                                            rowPosition = self.dlg.tableWidgetDetail.rowCount()
                                                            self.dlg.tableWidgetDetail.insertRow(rowPosition)
                                                            self.dlg.tableWidgetDetail.setItem(rowPosition, 1, QtGui.QTableWidgetItem(cg[0]))
                                                            self.dlg.tableWidgetDetail.setItem(rowPosition, 2, QtGui.QTableWidgetItem(cg[4]))
                                                            self.dlg.tableWidgetDetail.setItem(rowPosition, 3, QtGui.QTableWidgetItem(cwellb))
                                                            self.dlg.tableWidgetDetail.setItem(rowPosition, 4, QtGui.QTableWidgetItem(cg[5]))
                                                            self.dlg.tableWidgetDetail.setItem(rowPosition, 5, QtGui.QTableWidgetItem(cinc))
                                                            self.dlg.tableWidgetDetail.setItem(rowPosition, 6, QtGui.QTableWidgetItem(cg[6]))
                                                            self.dlg.tableWidgetDetail.setItem(rowPosition, 7, QtGui.QTableWidgetItem(cfsec))
                                                            self.dlg.tableWidgetDetail.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetail.verticalHeader().minimumSectionSize())
                                                            self.dlg.tableWidgetDetail.setRowHeight(rowPosition,17)

        #****COUNTS************************************************************************

        #For layers which are processed in counts:

                                if self.cur_scale_id == "ECO":
        # H E A D E R
                                    #Read header for each layer

                                    '''
                                    #********************************************************************************************
                                    #The following deactivated code fills the countable values table
                                    #by marking entries per layer. Each layer has a header and data after it.
                                    #The code was changed since the team required the data to be summarized
                                    #across layers. Rest of code has been left intact so will create results
                                    #by layer but then added code for summarizing and printing across layers.
                                    #Further down there are other deactivated code lines for the same reason.
                                    #********************************************************************************************

                                    rowPositionC = self.dlg.tableWidgetDetailCounts.rowCount()
                                    self.dlg.tableWidgetDetailCounts.insertRow(rowPositionC)
                                    self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 0, QtGui.QTableWidgetItem(layname + " ----------------------------------"))
                                    self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 1, QtGui.QTableWidgetItem(""))
                                    self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 2, QtGui.QTableWidgetItem(""))
                                    self.dlg.tableWidgetDetailCounts.setSpan(rowPositionC, 0, 1, 10)
                                    self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setForeground(QBrush(QColor.fromRgb(255,255,255)))
                                    self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setBackground(QBrush(QColor.fromRgb(30,106,175)))
                                    self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())
                                    self.dlg.tableWidgetDetailCounts.setRowHeight(rowPositionC,17)
                                    '''

                                    lstValueTypes = []
                                    restab = []
                                    for f in res_feat:
                                        res_geom = f.geometry()
                                        idx_poly_id = res_lay.fieldNameIndex('poly_id')
                                        idx_point_id = res_lay.fieldNameIndex('point_1')
                                        proc_type = ""
                                        if f.attributes:
                                            poly_id = ""
                                            point_id = ""
                                            attct = 0
                                            attry = f.attributes()
                                            if attry[idx_poly_id] == None or idx_poly_id == -1: #Poly ID field empty or not found 
                                                if idx_point_id > -1: #Point ID field found
                                                    proc_type = "POINT"
                                                    point_id = "PNT_" + str(attry[idx_point_id])
                                                else:
                                                    proc_type = "NONE" #Could not find any point or poly fields
                                            else:
                                                if idx_poly_id > -1: #Poly ID field found
                                                        proc_type = "POLY"
                                                        poly_id = "POLY_" + str(attry[idx_poly_id])
                                                else:
                                                    proc_type = "NONE" #Could not find any point or poly fields
                                            count_detail = 0
                                            if proc_type != "NONE":
                                                for cfs in self.dlg.list_of_values:
                                                    #Check it is in value type
                                                    if cfs[5] in ["Carbon sequestration"
                                                       ,"Hazard reduction"
                                                       ,"Water regulation"
                                                       ,"Biological diversity"
                                                       ,"Importance for ETP species or habitats"
                                                       ,"Naturalness"
                                                       ,"Productivity or nutrient cycling"
                                                       ,"Rarity/uniqueness"
                                                       ,"Vulnerability, sensitivity or slow recovery"
                                                       ,"Natural resources"
                                                       ,"Cultural heritage importance"
                                                       ,"Recreational, tourism or aesthetic importance"
                                                       ,"Spiritual importance"]:
                                                        cc = str(cfs[7])
                                                        if (proc_type == "POLY" and poly_id == cc) or (proc_type == "POINT" and point_id == cc):
                                                            ladd2 = [cfs[1],cfs[5],cfs[8], 1]
                                                            lstValueTypes.append(ladd2)
                                    #Summarize per scale name and value type
                                    firstr = True
                                    xfou = False
                                    for elem in lstValueTypes:
                                        if firstr:
                                            ladd3 = [elem[0],elem[1],elem[2], 1]
                                            restab.append(ladd3)
                                            firstr = False
                                        else:
                                            for elo in restab:
                                                if elo[0] == elem[0] and elo[1] == elem[1]:
                                                    elo[3] = elo[3] + 1
                                                    xfou = True
                                                    break
                                            if not xfou:
                                                ladd3 = [elem[0],elem[1],elem[2], 1]
                                                restab.append(ladd3)
                                            xfou = False
                                    nt = []                                                
                                    nt = sorted(restab, key = operator.itemgetter(0, 1)) #Scale name and value type which will be retained when grouped later

                                    if res_feat:
                                        #Reorganise list to group by value categories
                                        newtab = []
                                        fg = []
                                        fg.append("Natural resource values")
                                        fg.append("")
                                        fg.append("")
                                        newtab.append(fg)
                                        for e1 in restab:
                                            if e1[2] == "Natural resource values":
                                                fg = []
                                                fg.append(e1[0])
                                                fg.append(e1[1])
                                                fg.append(e1[3])
                                                newtab.append(fg)

                                                #Append to list of all countable values
                                                countable_nat_res.append(fg)

                                        fg = []
                                        fg.append("Ecological regulatory values")
                                        fg.append("")
                                        fg.append("")
                                        newtab.append(fg)
                                        for e1 in restab:
                                            if e1[2] == "Ecological regulatory values":
                                                fg = []
                                                fg.append(e1[0])
                                                fg.append(e1[1])
                                                fg.append(e1[3])
                                                newtab.append(fg)

                                                #Append to list of all countable values
                                                countable_eco_reg.append(fg)

                                        fg = []
                                        fg.append("Ecosystem structure and process values")
                                        fg.append("")
                                        fg.append("")
                                        newtab.append(fg)
                                        for e1 in restab:
                                            if e1[2] == "Ecosystem structure and process values":
                                                fg = []
                                                fg.append(e1[0])
                                                fg.append(e1[1])
                                                fg.append(e1[3])
                                                newtab.append(fg)

                                                #Append to list of all countable values
                                                countable_eco_stru_proc.append(fg)

                                        fg = []
                                        fg.append("Socio-cultural values")
                                        fg.append("")
                                        fg.append("")
                                        newtab.append(fg)
                                        for e1 in restab:
                                            if e1[2] == "Socio-cultural values":
                                                fg = []
                                                fg.append(e1[0])
                                                fg.append(e1[1])
                                                fg.append(e1[3])
                                                newtab.append(fg)

                                                #Append to list of all countable values
                                                countable_soc_cul.append(fg)

                                        #Deactivated code. Reactivate is display by layer is required
                                        '''
                                        for elem70 in newtab:
                                            rowPosition = self.dlg.tableWidgetDetailCounts.rowCount()
                                            self.dlg.tableWidgetDetailCounts.insertRow(rowPosition)
                                            self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 0, QtGui.QTableWidgetItem(str(elem70[0])))
                                            self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 1, QtGui.QTableWidgetItem(str(elem70[1])))
                                            self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 2, QtGui.QTableWidgetItem(str(elem70[2])))
                                            if not elem70[1]: #If second column is empty we assume it is a header and colour it
                                                for col in range(0,3):
                                                    self.dlg.tableWidgetDetailCounts.item(rowPosition,col).setBackground(QBrush(QColor.fromRgb(198,187,107)))
                                            self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())
                                        '''

            #**********************************************************************************

                                else:
                                    pass
                                #Since each layer has been clipped must remove each clip layer
                                for treeLayer in self.project.layerTreeRoot().findLayers():                
                                    layer_f2 = treeLayer.layer()
                                    if layer_f2.name() == "Clipped":
                                        QgsMapLayerRegistry.instance().removeMapLayer(layer_f2.id())

            #Summarise countable values. Deactivate this block to return to values by layer.
            #Also requires deactivation of some code above.
            rowPositionC = self.dlg.tableWidgetDetailCounts.rowCount()
            self.dlg.tableWidgetDetailCounts.insertRow(rowPositionC)
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 0, QtGui.QTableWidgetItem('Natural resource values' + " ----------------------------------"))
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 1, QtGui.QTableWidgetItem(""))
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 2, QtGui.QTableWidgetItem(""))
            self.dlg.tableWidgetDetailCounts.setSpan(rowPositionC, 0, 1, 10)
            self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setForeground(QBrush(QColor.fromRgb(255,255,255)))
            self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setBackground(QBrush(QColor.fromRgb(30,106,175)))
            self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())
            self.dlg.tableWidgetDetailCounts.setRowHeight(rowPositionC,17)

            cou_nat_res = []
            countable_nat_res = sorted(countable_nat_res, key = operator.itemgetter(0, 1))
            if len(countable_nat_res) > 0:
                for fl in countable_nat_res:
                    if len(cou_nat_res) > 0:
                        notfound = True
                        for x in cou_nat_res:
                            if fl[0].strip() == x[0].strip() and fl[1].strip() == x[1].strip():
                                x[2] = x[2] + fl[2]
                                notfound = False
                                break
                        if notfound:
                            cou_nat_res.append(fl)
                    else: #First one
                        cou_nat_res.append(fl)

                for elem80 in cou_nat_res:
                    rowPosition = self.dlg.tableWidgetDetailCounts.rowCount()
                    self.dlg.tableWidgetDetailCounts.insertRow(rowPosition)
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 0, QtGui.QTableWidgetItem(str(elem80[0])))
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 1, QtGui.QTableWidgetItem(str(elem80[1])))
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 2, QtGui.QTableWidgetItem(str(elem80[2])))
                    if not elem80[1]: #If second column is empty we assume it is a header and colour it
                        for col in range(0,3):
                            self.dlg.tableWidgetDetailCounts.item(rowPosition,col).setBackground(QBrush(QColor.fromRgb(198,187,107)))
                    self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())


            rowPositionC = self.dlg.tableWidgetDetailCounts.rowCount()
            self.dlg.tableWidgetDetailCounts.insertRow(rowPositionC)
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 0, QtGui.QTableWidgetItem('Ecological regulatory values' + " ----------------------------------"))
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 1, QtGui.QTableWidgetItem(""))
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 2, QtGui.QTableWidgetItem(""))
            self.dlg.tableWidgetDetailCounts.setSpan(rowPositionC, 0, 1, 10)
            self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setForeground(QBrush(QColor.fromRgb(255,255,255)))
            self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setBackground(QBrush(QColor.fromRgb(30,106,175)))
            self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())
            self.dlg.tableWidgetDetailCounts.setRowHeight(rowPositionC,17)

            cou_eco_reg = []
            countable_eco_reg = sorted(countable_eco_reg, key = operator.itemgetter(0, 1))
            if len(countable_eco_reg) > 0:
                for fl in countable_eco_reg:
                    if len(cou_eco_reg) > 0:
                        notfound = True
                        for x in cou_eco_reg:
                            if fl[0].strip() == x[0].strip() and fl[1].strip() == x[1].strip():
                                x[2] = x[2] + fl[2]
                                notfound = False
                                break
                        if notfound:
                            cou_eco_reg.append(fl)
                    else: #First one
                        cou_eco_reg.append(fl)

                for elem80 in cou_eco_reg:
                    rowPosition = self.dlg.tableWidgetDetailCounts.rowCount()
                    self.dlg.tableWidgetDetailCounts.insertRow(rowPosition)
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 0, QtGui.QTableWidgetItem(str(elem80[0])))
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 1, QtGui.QTableWidgetItem(str(elem80[1])))
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 2, QtGui.QTableWidgetItem(str(elem80[2])))
                    if not elem80[1]: #If second column is empty we assume it is a header and colour it
                        for col in range(0,3):
                            self.dlg.tableWidgetDetailCounts.item(rowPosition,col).setBackground(QBrush(QColor.fromRgb(198,187,107)))
                    self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())


            rowPositionC = self.dlg.tableWidgetDetailCounts.rowCount()
            self.dlg.tableWidgetDetailCounts.insertRow(rowPositionC)
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 0, QtGui.QTableWidgetItem('Ecosystem structure and process values' + " ----------------------------------"))
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 1, QtGui.QTableWidgetItem(""))
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 2, QtGui.QTableWidgetItem(""))
            self.dlg.tableWidgetDetailCounts.setSpan(rowPositionC, 0, 1, 10)
            self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setForeground(QBrush(QColor.fromRgb(255,255,255)))
            self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setBackground(QBrush(QColor.fromRgb(30,106,175)))
            self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())
            self.dlg.tableWidgetDetailCounts.setRowHeight(rowPositionC,17)

            cou_eco_stru_proc = []
            countable_eco_stru_proc = sorted(countable_eco_stru_proc, key = operator.itemgetter(0, 1))
            if len(countable_eco_stru_proc) > 0:
                for fl in countable_eco_stru_proc:
                    if len(cou_eco_stru_proc) > 0:
                        notfound = True
                        for x in cou_eco_stru_proc:
                            if fl[0].strip() == x[0].strip() and fl[1].strip() == x[1].strip():
                                x[2] = x[2] + fl[2]
                                notfound = False
                                break
                        if notfound:
                            cou_eco_stru_proc.append(fl)
                    else: #First one
                        cou_eco_stru_proc.append(fl)

                for elem80 in cou_eco_stru_proc:
                    rowPosition = self.dlg.tableWidgetDetailCounts.rowCount()
                    self.dlg.tableWidgetDetailCounts.insertRow(rowPosition)
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 0, QtGui.QTableWidgetItem(str(elem80[0])))
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 1, QtGui.QTableWidgetItem(str(elem80[1])))
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 2, QtGui.QTableWidgetItem(str(elem80[2])))
                    if not elem80[1]: #If second column is empty we assume it is a header and colour it
                        for col in range(0,3):
                            self.dlg.tableWidgetDetailCounts.item(rowPosition,col).setBackground(QBrush(QColor.fromRgb(198,187,107)))
                    self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())


            rowPositionC = self.dlg.tableWidgetDetailCounts.rowCount()
            self.dlg.tableWidgetDetailCounts.insertRow(rowPositionC)
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 0, QtGui.QTableWidgetItem('Socio-cultural values' + " ----------------------------------"))
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 1, QtGui.QTableWidgetItem(""))
            self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 2, QtGui.QTableWidgetItem(""))
            self.dlg.tableWidgetDetailCounts.setSpan(rowPositionC, 0, 1, 10)
            self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setForeground(QBrush(QColor.fromRgb(255,255,255)))
            self.dlg.tableWidgetDetailCounts.item(rowPositionC,0).setBackground(QBrush(QColor.fromRgb(30,106,175)))
            self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())
            self.dlg.tableWidgetDetailCounts.setRowHeight(rowPositionC,17)

            cou_soc_cul = []
            countable_soc_cul = sorted(countable_soc_cul, key = operator.itemgetter(0, 1))
            if len(countable_soc_cul) > 0:
                for fl in countable_soc_cul:
                    if len(cou_soc_cul) > 0:
                        notfound = True
                        for x in cou_soc_cul:
                            if fl[0].strip() == x[0].strip() and fl[1].strip() == x[1].strip():
                                x[2] = x[2] + fl[2]
                                notfound = False
                                break
                        if notfound:
                            cou_soc_cul.append(fl)
                    else: #First one
                        cou_soc_cul.append(fl)

                for elem80 in cou_soc_cul:
                    rowPosition = self.dlg.tableWidgetDetailCounts.rowCount()
                    self.dlg.tableWidgetDetailCounts.insertRow(rowPosition)
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 0, QtGui.QTableWidgetItem(str(elem80[0])))
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 1, QtGui.QTableWidgetItem(str(elem80[1])))
                    self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 2, QtGui.QTableWidgetItem(str(elem80[2])))
                    if not elem80[1]: #If second column is empty we assume it is a header and colour it
                        for col in range(0,3):
                            self.dlg.tableWidgetDetailCounts.item(rowPosition,col).setBackground(QBrush(QColor.fromRgb(198,187,107)))
                    self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())

            #Create graph
            if self.dlg.tableWidgetDetail.columnCount() > 1:
                self.doGraph()

            if self.RBMode == "user":
                self.myMapTool.deleteLater()

            self.dlg.activateWindow()
        except:
            self.dlg.error.setPlainText("Error retrieving data from spatial operation. [46]")


    def testReadELVISdb(self):
        try:
            #Test access to ELVIS.db and test read to the three main tables/views
            db = QSqlDatabase.addDatabase("QSQLITE");
            # Reuse the path to DB to set database name
            db.setDatabaseName(self.last_opened_project_dir + "\\ELVIS.db")
            # Open the connection
            db.open()
            # query the table
            query = db.exec_("select * from marine_values_all")
            while query.next():
                record = query.record()
            tq = query.lastError().text()
            query = db.exec_("select * from area_selections")
            while query.next():
                record = query.record()
            tq = tq + query.lastError().text()
            query = db.exec_("select * from marine_values_value_matrix")
            while query.next():
                record = query.record()
            tq = tq + query.lastError().text()
            if len(tq) > 0:
                return True
            else:
                self.dlg.error.setPlainText("ELVIS database is missing or incrorrectly structured. [78]")
                return False
        except:
            self.dlg.error.setPlainText("Error during read test of ELVIS database. [19]")


    def readSQLiteDB(self):
        try:
            if self.testReadELVISdb():
                db = QSqlDatabase.addDatabase("QSQLITE");
                # Reuse the path to DB to set database name
                db.setDatabaseName(self.last_opened_project_dir + "\\ELVIS.db")
                # Open the connection
                db.open()
                query = QSqlQuery(db)
                query.exec_("select * from marine_values_all")

                while query.next():

                    record = query.record()
                    # **************************************************************************
                    # self.dlg.list_of_values - copy of SQLite table marine_values_all (has values for polygons and points in the shapefiles)
                    listv = [str(record.value(17)),      # 0 - Spatial feature name
                       str(record.value(8)),               # 1 - Scale name
                       str(record.value(7)),                # 2 - Scale id
                       str(record.value(1)),                 # 3 - Value name
                       str(record.value(12)),            # 4 - Value metric score
                       str(record.value(4)),                # 5 - Value type
                       str(record.value(10)),             # 6 - Value metric description
                       str(record.value(18)),     # 7 - Spatial feature id
                       str(record.value(2)),          # 8 - Value category
                       str(record.value(6)),              # 9 - Scale type
                       str(record.value(11)),       #10 - Value metric units
                       str(record.value(19)),           #11 - Spatial feature description
                       str(record.value(21)),          #12 - Date collected
                       str(record.value(22)),      #13 - Metric score source
                       str(record.value(23))]     #14 - Metric score contact
                    # **************************************************************************
                    self.dlg.list_of_values.append(listv)

                query2 = db.exec_("select * from marine_values_value_matrix")
                while query2.next():
                    recorda = query2.record()
                    # 1 - value_name
                    # 2 - spatial_feature_name
                    # 3 - scale_name
                    # 4 - scale_id
                    # 5 - wellbeing (= value_metric_score of records where value_metric_description = "Importance for human wellbeing")
                    # 6 - income (= value_metric_score of records where value_metric_description = "Importance for income")
                    # 7 - food_security (= value_metric_score of records where value_metric_description = "Importance for food security")
                    listw = [str(recorda.value(0)), str(recorda.value(1)), str(recorda.value(2)), str(recorda.value(3)), str(recorda.value(4)), str(recorda.value(5)), str(recorda.value(6))]
                    self.dlg.area_value_matrix.append(listw)
        except:
            self.dlg.error.setPlainText("Error during read test of ELVIS database. [35]")

    def pushButtonOrigExtentClicked(self):
        self.OrigExtent()


    def OrigExtent(self):
        mapExtentRect = QgsRectangle(147.9,-3.4,152.8,-6.6)
        mc = self.iface.mapCanvas() 
        mc.setExtent(mapExtentRect)
        self.iface.mapCanvas().zoomScale(1600000)


#***********************************************
# Code for 'Manage saved areas' dialog
#***********************************************

    def pushButtonReadShpClicked(self):
        try:
            qfd = QFileDialog()
            title = 'Select shapefile'
            path = ""
            fn = QFileDialog.getOpenFileName(qfd, title, path)
            layer = QgsVectorLayer(fn, 'polygon', 'ogr')
            if not layer.isValid():
                pass
            else:
                iter = layer.getFeatures()
                for feature in iter:
                    geom = feature.geometry()
                    x = geom.asPolygon()
                    pts = str(x)
                    pts = pts.replace("[[","[")
                    pts = pts.replace("]]","]")
                    pts = pts.replace(" ","")
                    self.dlgsavesel.textAOIPtLst.clear()
                    self.dlgsavesel.textAOIPtLst.appendPlainText(pts)
                    #Only read first polygon
                    return
        except:
            self.dlg.error.setPlainText("Unable to open shapefile or read point of the first polygon. [22]")


    def butDeleteClicked(self):
        try:
            if self.dlgsavesel.tableWidgetAOI.rowCount() > 0:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Question)
                msg.setText("Click Yes to delete this area permanently.")
                msg.setInformativeText("")
                msg.setWindowTitle("Confirm delete")
                msg.setDetailedText("")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.buttonClicked.connect(self.msgbtn)
                retval = msg.exec_()
                if retval == QMessageBox.Yes:
                    self.dlgsavesel.textAOIShortT.clear()
                    self.dlgsavesel.textAOIDesc.clear()
                    self.dlgsavesel.textAOIPtLst.clear()
                    if self.testReadELVISdb():
                        try: 
                            delid = str(int(self.dlgsavesel.fldID.text()))
                            db = QSqlDatabase.addDatabase("QSQLITE");
                            db.setDatabaseName(self.last_opened_project_dir + "\\ELVIS.db")
                            db.open()
                            sqls = "delete from area_selections where id = " + delid
                            query = db.exec_(sqls)
                            db.commit()
                            self.reqaoirecs()
                            self.dlgsavesel.tableWidgetAOI.selectRow(0)
                            self.tableWidgetAOIClicked(0, 0)
                        except ValueError:
                            self.dlg.error.setPlainText("Select the area to be deleted in the list at the top. [58]")
                else:
                    pass
        except:
            self.dlg.error.setPlainText("Unable to delete area. [29]")


    def msgbtn(i):
        pass


    def buttonSaveClicked(self):
        if self.testReadELVISdb():
            try: 
                delid = str(int(self.dlgsavesel.fldID.text()))
                db = QSqlDatabase.addDatabase("QSQLITE");
                db.setDatabaseName(self.last_opened_project_dir + "\\ELVIS.db")
                db.open()
                sqls = "update area_selections set short_name = '" + self.dlgsavesel.textAOIShortT.toPlainText() + "' , description = '" + self.dlgsavesel.textAOIDesc.toPlainText() + "', point_list = '" + self.dlgsavesel.textAOIPtLst.toPlainText() + "' where id = " + delid
                query = db.exec_(sqls)
                db.commit()
                self.reqaoirecs()
                self.dlgsavesel.tableWidgetAOI.selectRow(0)
                self.tableWidgetAOIClicked(0, 0)
            #Save as new record if getting the ID in the form fails or for any other reason
            except ValueError:
                AOIs = []
                db = QSqlDatabase.addDatabase("QSQLITE");
                db.setDatabaseName(self.last_opened_project_dir + "\\ELVIS.db")
                db.open()

                if self.dlgsavesel.textAOIShortT.toPlainText() and self.dlgsavesel.textAOIDesc.toPlainText() and self.dlgsavesel.textAOIPtLst.toPlainText():
                    ndate = datetime.date.today()
                    n_day = "%02d" % (ndate.day,) 
                    n_mon = "%02d" % (ndate.month,) 
                    n_yea = "%04d" % (ndate.year,) 
                    fdat1 = n_day + "/" + n_mon + "/" + n_yea
                    sqls = "insert into area_selections (crea_date, short_name, description, point_list) values ('" + fdat1 + "','" + self.dlgsavesel.textAOIShortT.toPlainText() + "','" + self.dlgsavesel.textAOIDesc.toPlainText() + "','" + self.dlgsavesel.textAOIPtLst.toPlainText() + "')"
                    query = db.exec_(sqls)
                    db.commit()
                    self.reqaoirecs()
                    self.dlgsavesel.tableWidgetAOI.selectRow(0)
                    self.tableWidgetAOIClicked(0, 0)
                    #self.dlgsavesel.close()
                else:
                    self.dlg.error.setPlainText("To save area ensure all required text is filled. [92]")
        else:
            self.dlg.error.setPlainText("ELIVS database is missing or incrorrectly structured. [93]")


    def butNewAreaClicked(self):
        self.dlgsavesel.textAOIShortT.clear()
        self.dlgsavesel.textAOIDesc.clear()
        self.dlgsavesel.textAOIPtLst.clear()
        self.dlgsavesel.fldID.clear()
        self.dlgsavesel.labelDate.clear()


    def pushButtonOKClicked(self):
#        try:
        fr = self.dlgsavesel.textAOIPtLst.toPlainText()
        if fr:
            if fr.endswith(".shp"):
                if isfile(fr):
                    self.procAreaSelection(fr)
                    self.dlgsavesel.close()
                else:
                    self.dlg.error.setPlainText("Shapefile for input cannot be found. [82]")                
            else:
                self.myRubberBand = QgsRubberBand(self.iface.mapCanvas(),QGis.Polygon) #Init rubberband
                fx = unicodedata.normalize('NFKD', fr).encode('ascii','ignore')
                fx = fx.replace("[", "")
                fx = fx.replace("]", "")
                fx = fx.replace("),(", ");(")
                fx = fx.replace(" ", "")  # Remove all blanks
                fx = ' '.join(fx.split()) # Remove all white spaces
                fx = ''.join(fx.split())  # Remove all white spaces
                rub = []
                rub = fx.split(";")
                NewRubberBand = []

                for el in rub:
                    lat, lng = map(float, el.strip('()').split(','))
                    rbPt = QgsPoint(lat, lng)
                    NewRubberBand.append(rbPt)
                gPoly = QgsGeometry.fromPolygon(( [[ QgsPoint( pair[0], pair[1] ) for pair in NewRubberBand ]] ))
                self.myRubberBand.addGeometry(gPoly, None)
                self.RBMode = "saved"
                self.procAreaSelection('points')
                self.dlgsavesel.close()
#        except:
#            self.dlg.error.setPlainText("Point list could not be read. Please verify format. [80]")                

        
    def pushButtonCancelClicked(self):
        self.dlgsavesel.close()


    def buttonOpenSavedClicked(self):
        self.setupDia()


    def setupDia(self):
        self.dlgsavesel = ELVISSaveSel()
        pal=QtGui.QPalette()
        role = QtGui.QPalette.Background
        pal.setColor(role, QtGui.QColor(214, 211, 171))
        self.dlgsavesel.setPalette(pal)        

        self.dlgsavesel.setModal(True)
        self.dlgsavesel.show()
        self.dlgsavesel.setWindowTitle("Manage saved areas")
        self.dlgsavesel.setWindowIcon(QtGui.QIcon(':/plugins/ELVIS/resources/ELVIS16.png'))
        
        self.dlgsavesel.tableWidgetAOI.cellClicked.connect(self.tableWidgetAOIClicked)
        self.dlgsavesel.buttonSave.clicked.connect(self.buttonSaveClicked)

        self.dlgsavesel.pushButtonOK.clicked.connect(self.pushButtonOKClicked)
        self.dlgsavesel.pushButtonCancel.clicked.connect(self.pushButtonCancelClicked)
        self.dlgsavesel.pushButtonReadShp.clicked.connect(self.pushButtonReadShpClicked)
        self.dlgsavesel.butDelete.clicked.connect(self.butDeleteClicked)
        self.dlgsavesel.butNewArea.clicked.connect(self.butNewAreaClicked)
        self.dlgsavesel.butInsLastSelArea.clicked.connect(self.butInsLastSelAreaClicked)
        self.dlgsavesel.butShapefile.clicked.connect(self.butShapefileClicked)

        self.dlgsavesel.tableWidgetAOI.setColumnWidth(0,30)
        self.dlgsavesel.tableWidgetAOI.setColumnWidth(1,70)
        self.dlgsavesel.tableWidgetAOI.setColumnWidth(2,200)
        self.dlgsavesel.tableWidgetAOI.setColumnWidth(3,0)
        self.dlgsavesel.tableWidgetAOI.setColumnWidth(4,0)

        #Prevent table from being edited
        self.dlgsavesel.tableWidgetAOI.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.reqaoirecs()        


    def butShapefileClicked(self):
        fileo = QtGui.QFileDialog.getOpenFileName(None, 'Select shapefile with area of interest.', '', '*.shp')
        filep = QDir.toNativeSeparators(fileo)
        self.dlgsavesel.textAOIPtLst.clear()
        self.dlgsavesel.textAOIPtLst.appendPlainText(filep)


    def butInsLastSelAreaClicked(self):
        if str(self.rubberbandPoints) != '[]':
            rbp = str(self.rubberbandPoints)
            rbp = rbp.translate(None, '\'')
            rbp = rbp.replace(" ","")
            self.dlgsavesel.textAOIPtLst.clear()
            self.dlgsavesel.textAOIPtLst.appendPlainText(rbp)
        else:
            self.dlg.error.setPlainText("No area selected recently. [23]")


    def reqaoirecs(self):
        try:
            if self.testReadELVISdb():
                AOIs = []
                db = QSqlDatabase.addDatabase("QSQLITE");
                db.setDatabaseName(self.last_opened_project_dir + "\\ELVIS.db")
                db.open()
                query = db.exec_("select * from area_selections")
                while query.next():
                    record = query.record()
                    listv = [str(record.value(0)), str(record.value(1)), str(record.value(2)), str(record.value(3)), str(record.value(4))]
                    AOIs.append(listv)

                self.dlgsavesel.tableWidgetAOI.setRowCount(0)
                if len(AOIs) > 0:
                    for ele in AOIs:
                        rowPosition = self.dlgsavesel.tableWidgetAOI.rowCount()
                        self.dlgsavesel.tableWidgetAOI.insertRow(rowPosition)
                        self.dlgsavesel.tableWidgetAOI.setItem(rowPosition, 0, QtGui.QTableWidgetItem(ele[0]))
                        self.dlgsavesel.tableWidgetAOI.setItem(rowPosition, 1, QtGui.QTableWidgetItem(str(ele[3])))
                        self.dlgsavesel.tableWidgetAOI.setItem(rowPosition, 2, QtGui.QTableWidgetItem(str(ele[1])))
                        self.dlgsavesel.tableWidgetAOI.setItem(rowPosition, 3, QtGui.QTableWidgetItem(str(ele[2])))
                        self.dlgsavesel.tableWidgetAOI.setItem(rowPosition, 4, QtGui.QTableWidgetItem(str(ele[4])))
                        self.dlgsavesel.tableWidgetAOI.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())
        except:
            self.dlg.error.setPlainText("No saved areas or error retrieving records. [97]")


    def tableWidgetAOIClicked(self, row, column):
        try:
            #self.dlgsavesel.butNewArea.setEnabled(False)

            item = self.dlgsavesel.tableWidgetAOI.item(row, 2)
            itm = item.text()
            self.dlgsavesel.textAOIShortT.clear()
            self.dlgsavesel.textAOIShortT.appendPlainText(itm)

            item = self.dlgsavesel.tableWidgetAOI.item(row, 3)
            itm = item.text()
            self.dlgsavesel.textAOIDesc.clear()
            self.dlgsavesel.textAOIDesc.appendPlainText(itm)

            item = self.dlgsavesel.tableWidgetAOI.item(row, 1)
            itm = item.text()
            self.dlgsavesel.labelDate.setText(itm)

            item = self.dlgsavesel.tableWidgetAOI.item(row, 4)
            itm = item.text()
            self.dlgsavesel.textAOIPtLst.clear()
            self.dlgsavesel.textAOIPtLst.appendPlainText(itm)

            #Hidden field ID. So we can write changes to that record
            item = self.dlgsavesel.tableWidgetAOI.item(row, 0)
            itm = item.text()
            self.dlgsavesel.fldID.setText(itm)
        except:
            self.dlg.error.setPlainText("No saved areas. [13]")

#***********************************************
#***********************************************


#  Other Classes *********************************************************************
# ************************************************************************************

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ELVIS_save_sel.ui'))
class ELVISSaveSel(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ELVISSaveSel, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)


FORM4_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ELVIS_info2.ui'))
class MVinfo2(QtGui.QDialog, FORM4_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(MVinfo2, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)

    def closeEvent(self, event):
        QApplication.restoreOverrideCursor()


FORM5_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ELVIS_prog_info.ui'))
class ELVISProgramInfo(QtGui.QDialog, FORM5_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ELVISProgramInfo, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setupUi(self)

    def closeEvent(self, event):
        QApplication.restoreOverrideCursor()


class ModelObjInfo(QStandardItemModel):
    def __init__(self, parent=None):
        QtGui.QStandardItemModel.__init__(self)
        self.setColumnCount(3)
        #self.setHorizontalHeaderLabels(['Object'])

    def data(self, index, role):
        if index.isValid():
            return super(ModelObjInfo, self).data(index, QtCore.Qt.DisplayRole)


class Model(QStandardItemModel):
    def __init__(self, parent=None):
        self.filled = False
        QtGui.QStandardItemModel.__init__(self)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['', 'Sort Key', 'Clicked', 'Type', 'Layer'])


#TESTTEST WFS
#        tt = "MarineValuesNewBritainTestLLG"
#        onlyfiles.append(tt)
#TESTTEST


    def data(self, index, role):
        if index.isValid():
            if role == QtCore.Qt.CheckStateRole:
                return super(Model, self).data(index, QtCore.Qt.CheckStateRole)

            # Don't delete this line. Fixes  display going funny
            return super(Model, self).data(index, QtCore.Qt.DisplayRole)


    def checkState(self, index):
        if index in self.checks:
            return self.checks[index]
        else:
            return QtCore.Qt.Unchecked


class PointTool2(QgsMapTool):   
    def __init__(self, canvas, dlist_of_values, dlist_of_values_fields, info_window):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas  
        self.dlist_of_values = dlist_of_values
        self.dlist_of_values_fields = dlist_of_values_fields
        self.info_window = info_window

    def canvasReleaseEvent(self, event):
        try:
            x = event.pos().x()
            y = event.pos().y()
            point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
            self.info_window.tableWidget.setRowCount(0)

            regmap = QgsMapLayerRegistry.instance().mapLayers().values()
            curcol = QColor.fromRgb(198,187,107)
            col_alt = True
            for lay in regmap:
                layname = lay.name()

                #Only processing vector layers
                if lay.type() == QgsMapLayer.VectorLayer:
                    #Only processing where name of layer = 'Marine Values' or 'MarineValues' for a wfs layer
                    #if layname[:13] == ("Marine Values") or layname[:12] == "MarineValues":
                    if layname.endswith('_LLG') or layname.endswith('_DIS') or layname.endswith('_ECO'):
                        if lay.geometryType() == 2  or lay.geometryType() == QGis.Point:
                            fiter = lay.getFeatures()
                            for feature in fiter:
                                fgem = feature.geometry()
                                #Does this polygon contain the mouse click ?

                                isIn = False
                                if lay.geometryType() == QGis.Point:
                                    buf = fgem.buffer(0.005,100) #Within 500m radius of the pointfeature. Circle aprroximated with 100 segnments
                                    if buf.contains(point):
                                        isIn = True
                                
                                if lay.geometryType() == 2 or lay.geometryType() == 0:
                                    if fgem.contains(point): #Point is in polygon feature
                                        isIn = True

                                if isIn:
                                    if feature.attributes:
                                        poly_id = ""
                                        point_id = ""
                                        idx_poly_id = lay.fieldNameIndex('poly_id')
                                        idx_point_id = lay.fieldNameIndex('point_1')
                                        idx_value_type = lay.fieldNameIndex('value_type')
                                        proc_type = ""
                                        attry = feature.attributes()
                                        value_type = str(attry[idx_value_type])
                                        poly_or_point_id = ""

                                        if attry[idx_poly_id] == None or idx_poly_id == -1:
                                            if idx_point_id > -1: #Point ID field found
                                                proc_type = "POINT"
                                                point_id = "PNT_" + str(attry[idx_point_id])
                                                poly_or_point_id = "PNT_" + str(attry[idx_point_id])
                                            else:
                                                proc_type = "NONE" #Could not find any point or poly fields
                                        else:
                                            if idx_poly_id > -1: #Poly ID field found
                                                proc_type = "POLY"
                                                poly_id = "POLY_" + str(attry[idx_poly_id])
                                                poly_or_point_id = "POLY_" + str(attry[idx_poly_id])
                                            else:
                                                proc_type = "NONE" #Could not find any point or poly fields
                                        print poly_id
                                        print point_id
                                        if proc_type != "NONE":
                                            for cfs in self.dlist_of_values:
                                                cc = str(cfs[7])
                                                if (value_type == str(cfs[5])):
                                                    if (proc_type == "POLY" and poly_id == cc) or (proc_type == "POINT" and point_id == cc):
                                                        if col_alt:
                                                            curcol = QColor.fromRgb(198,187,107)
                                                        else:
                                                            curcol = QColor.fromRgb(255,255,255)

                                                        idx = 0
                                                        for val in self.dlist_of_values_fields:
                                                            if (val[0] == 'Value name' 
                                                            or val[0] == 'Value category' 
                                                            or val[0] == 'Value type' 
                                                            or val[0] == 'Scale type'
                                                            or val[0] == 'Scale name'
                                                            or val[0] == 'Value metric description'
                                                            or val[0] == 'Value metric units'
                                                            or val[0] == 'Value metric score'
                                                            or val[0] == 'Spatial feature name'
                                                            or val[0] == 'Spatial feature description'
                                                            or val[0] == 'Date collected'
                                                            or val[0] == 'Metric score source'
                                                            or val[0] == 'Metric score contact'):

                                                                rowPosition = self.info_window.tableWidget.rowCount()
                                                                self.info_window.tableWidget.insertRow(rowPosition)
                                                                self.info_window.tableWidget.setItem(rowPosition, 0, QtGui.QTableWidgetItem(layname))
                                                                self.info_window.tableWidget.setItem(rowPosition, 1, QtGui.QTableWidgetItem(poly_or_point_id))
                                                                self.info_window.tableWidget.setItem(rowPosition, 2, QtGui.QTableWidgetItem(val[0]))
                                                                self.info_window.tableWidget.setItem(rowPosition, 3, QtGui.QTableWidgetItem(cfs[idx]))
                                                                self.info_window.tableWidget.setRowHeight(rowPosition,17) 
                                                                for col in range(0,4):
                                                                    self.info_window.tableWidget.item(rowPosition,col).setBackground(QBrush(curcol))
                                                            idx = idx + 1
                                                        col_alt = not col_alt

            #Bring info window back to the front. It is not modal so clicking a point makes it move behind the QGIS window.
            pttxt = "Point at " + "{0:.4f}".format(round(point.x(),4)) + ", " + "{0:.4f}".format(round(point.y(),4))
            self.info_window.labelCoord.setText(pttxt)
            self.info_window.show()
            self.info_window.activateWindow()
        except:
            self.dlg.error.setPlainText("Error releasing canvas. [91]")
class Anchor(pg.ItemGroup):
    #Graphics item that anchors its position to the coordinate system inside a view box.
    def __init__(self, view, pos, x=True, y=True):
        pg.ItemGroup.__init__(self)
        self.view = view
        self.anchorPos = pg.Point(pos)
        self.anchorAxes = (x, y)
        view.sigRangeChanged.connect(self.updatePosition)

    def updatePosition(self):
        pos = self.pos()
        anchorPos = self.parentItem().mapFromScene(self.view.mapViewToScene(self.anchorPos))
        x, y = self.anchorAxes
        if x:
            pos.setX(anchorPos.x())
        if y:
            pos.setY(anchorPos.y())
        self.setPos(pos)

