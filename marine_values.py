# -*- coding: utf-8 -*-
"""
/***************************************************************************
*    CSIRO Marine Values                                                   *
*    marine_values.py                                                      *
*    A QGIS plugin                                                         *
*    MARVIN - CSIRO Marine values tool. Management of marine value         *
*             information.                                                 *
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
 *   called "marine values help.txt"                                       * 
 *                                                                         *
 *   Environment Versions                                                  *
 *   ------------------------------------                                  *
 *   Python 2.7.5                                                          *
 *   QGIS 2.18.2 Las Palmas                                                *
 *   Qt Creator 4.2.0                                                      *
 *                                                                         *
 *                                                                         *
 *   Plugins required:                                                     *
 *   ------------------------------------                                  *
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
 *   Default project shapefile is '/gis/Marine Values New Britain LLG.shp' *
 *   which should be write-protected so user can not make changes.         *
 *   -------------------------------------------------------------------   *
 *   Shapefile naming convention:                                          *
 *      'Marine Values...'      - A layer for which values and value       *
 *                                metric scores are processed.             *
 *      'MarineValues...'       - A WFS layer for which values and value   *
 *                                 metric scores are processed. Entire     *
 *                                 name may not contain any spaces         *
 *      ending in ... .LLG       - Processing as per LLGs                  *
 *      ending in ... .Districts - Processing as per Disctrics             *
 *      ending in ... .Features  - Processing as per countable features    *
 *                               without scale                             *
 *                                                                         *
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

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo, QAbstractItemModel, Qt, QVariant, QPyNullVariant
from PyQt4.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QHeaderView, QColor, QBrush
from qgis.gui import QgsRubberBand, QgsMapToolEmitPoint, QgsMapCanvas, QgsMapToolZoom
from marine_values_dialog import CSIROMarineValuesDialog
from PyQt4.QtSql import QSqlDatabase #For SQLite DB access
from PyQt4 import QtGui
from PyQt4 import QtCore
from os import listdir
from os.path import isfile, join
from qgis.core import *
from qgis.core import QgsMapLayer
from qgis.utils import QGis
from collections import defaultdict
from pprint import pprint
from os.path import expanduser

from win32api import GetSystemMetrics


class CSIROMarineValues:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        #Constructor.


#CHECKTIME
#        self.dlg.checktime = []
#        chktime_time = datetime.datetime.now()
#        chktime_step = 1
#        chk = [chktime_time, chktime_step]
#        self.checktime.dlg.append(chk)
        self.project = QgsProject.instance()

        # Have we filled the list widget with the shps yet?
        self.filled = False
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        #Counter for sort order of layers
        self.treeLayerIdx = 0
        #Operation mode of this plugin: 
        #  'dev' - development. Ending does not close QGIS.
        #  'prod'- production. End command ends QGIS.
        self.opmode = 'dev'
        self.geometryTypes = defaultdict(lambda: 'unknown', {QGis.Polygon: 'polygon', QGis.Point: 'point'})

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

#        chktime_time = datetime.datetime.now()
#        chktime_step = 20
#        chk = [chktime_time, chktime_step]
#        self.checktime.dlg.append(chk)

       

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
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):

        # Create the dialog (after translation) and keep reference
        self.dlg = CSIROMarineValuesDialog()


        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/CSIROMarineValues/mv_icon32x32.png'
        self.add_action(
            icon_path,
            text=self.tr(u'CSIRO Marine Values System'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # Define Set signal only in iniGui
        # connect to signal renderComplete which is emitted when canvas
        # rendering is done
        QtCore.QObject.connect(self.iface.mapCanvas(), QtCore.SIGNAL("renderComplete(QPainter *)"), self.renderTest)

        #self.dlg.loadProject.clicked.connect(self.loadProjectClicked)
        self.dlg.saveProject.clicked.connect(self.saveProjectClicked)
        rMyIcon = QtGui.QPixmap(self.plugin_dir + "\\resources\\save.png");
        self.dlg.saveProject.setIcon(QtGui.QIcon(rMyIcon))

        self.dlg.endButton.clicked.connect(self.endButtonClicked)
        rMyIcon = QtGui.QPixmap(self.plugin_dir + "\\resources\\end.png");
        self.dlg.endButton.setIcon(QtGui.QIcon(rMyIcon))

        self.dlg.rubberband.clicked.connect(self.rubberbandClicked)
        rMyIcon = QtGui.QPixmap(self.plugin_dir + "\\resources\\sel_area2.png");
        self.dlg.rubberband.setIcon(QtGui.QIcon(rMyIcon))

        self.dlg.pushButtonPan.clicked.connect(self.pushButtonPanClicked)
        rMyIcon = QtGui.QPixmap(self.plugin_dir + "\\resources\\hand.png");
        self.dlg.pushButtonPan.setIcon(QtGui.QIcon(rMyIcon))

        self.dlg.pushButtonZoomPlus.clicked.connect(self.pushButtonZoomPlusClicked)
        rMyIcon = QtGui.QPixmap(self.plugin_dir + "\\resources\\zoomin.png");
        self.dlg.pushButtonZoomPlus.setIcon(QtGui.QIcon(rMyIcon))

        self.dlg.pushButtonZoomMinus.clicked.connect(self.pushButtonZoomMinusClicked)
        rMyIcon = QtGui.QPixmap(self.plugin_dir + "\\resources\\zoomout.png");
        self.dlg.pushButtonZoomMinus.setIcon(QtGui.QIcon(rMyIcon))

        self.dlg.pushButtonExport.clicked.connect(self.pushButtonExportClicked)
        rMyIcon = QtGui.QPixmap(self.plugin_dir + "\\resources\\export.png");
        self.dlg.pushButtonExport.setIcon(QtGui.QIcon(rMyIcon))

        self.dlg.pushButtonOrigExtent.clicked.connect(self.pushButtonOrigExtentClicked)
        #rMyIcon = QtGui.QPixmap(self.plugin_dir + "\\resources\\export.png");
        #self.dlg.pushButtonOrigExtent.setIcon(QtGui.QIcon(rMyIcon))

        # Set up tableView table ****************************
        #self.dlg.tableView.setModel(model)
        self.dlg.tableView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.dlg.tableView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        xmod = Model()
        self.dlg.tableView.setModel(xmod)

        header = self.dlg.tableView.horizontalHeader()
        #header.setDefaultAlignment(QtCore.Qt.AlignHCenter)
        header.setResizeMode(QtGui.QHeaderView.Fixed)
        self.dlg.tableView.setColumnWidth(0,230)
        self.dlg.tableView.setColumnWidth(1,80)
        self.dlg.tableView.setColumnWidth(2,0)
        self.dlg.tableView.setColumnWidth(3,0)

        #self.dlg.tableView.model().clicked.connect(self.tableViewselectionChanged)

        self.dlg.tableView.verticalHeader().setMovable(True)
        self.dlg.tableView.verticalHeader().setDragEnabled(True)
        self.dlg.tableView.verticalHeader().setDragDropMode(QtGui.QAbstractItemView.InternalMove)

        QtCore.QObject.connect(self.dlg.tableView.verticalHeader(), QtCore.SIGNAL("sectionMoved(int, int, int)"), self.tableViewRowMoved)        

        #self.dlg.tableView.setDropIndicatorShown(True)
        #self.dlg.tableView.setAcceptDrops(True)
        #self.dlg.tableView.setDragEnabled(True)
        #self.dlg.tableView.dropOn = lambda event: pprint(event)
        #self.dlg.tableView.droppingOnItself = lambda event: pprint(event)

        #self.dlg.tableView.model().selectionChanged = lambda x, y: pprint([self, x, y])
        #self.dlg.tableView.stateChanged = lambda x, y: pprint([self, x, y])
        #self.dlg.tableView.itemChanged.connect(self.s_changed)
        self.dlg.tableView.clicked.connect(self.tableViewClicked)

        #self.dlg.tableView.mousePressEvent = lambda event: pprint(event)
        #self.dlg.tableView.dropEvent = lambda event: pprint(event)
        #self.dlg.tableView.model().columnsMoved.connect(lambda event: pprint(event))


        QtCore.QObject.connect(self.dlg.tableView, QtCore.SIGNAL("clicked(const QModelIndex & index)"), self.tableViewClicked)
        #QtCore.QObject.connect(self.dlg.objectInfo, QtCore.SIGNAL("clicked(const QModelIndex & index)"), self.tableViewClicked)

        self.dlg.endButton.setDefault(True)
        self.dlg.endButton.setAutoDefault(True)

        self.dlg.checktime = []
        chktime_time = "***"
        chktime_step = "***"
        chk = [chktime_time, chktime_step]
        self.dlg.checktime.append(chk)


        chktime_time = datetime.datetime.now()
        chktime_step = 30
        chk = [chktime_time, chktime_step]
        self.dlg.checktime.append(chk)

        #self.iface.mapCanvas().xyCoordinates.connect(showCoordinates)
        #myMapTool.canvasClicked.connect(manageClick)
        #self.iface.mapCanvas().setMapTool(myMapTool)

    def run(self):

        # Should not connect signals in the run function

        chktime_time = datetime.datetime.now()
        chktime_step = 50
        chk = [chktime_time, chktime_step]
        self.dlg.checktime.append(chk)
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
        '''if not self.filled:
            self.filled = True
            model = QStandardItemModel()
            #model = QAbstractItemModel()
            model.setColumnCount(3)
            model.setHorizontalHeaderLabels(['Layer', 'Type', 'Sort Key'])
            for fil in onlyfiles:
                item = QStandardItem(fil)
                item.setCheckable(True)
                model.appendRow([item, QStandardItem('unknown'), QStandardItem('99999')])'''
            

        # Set up objectInfo table ***************************
        #self.dlg.objectInfo.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        #self.dlg.objectInfo.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        #xmodobjinf = ModelObjInfo()
        #self.dlg.objectInfo.setModel(xmodobjinf)
        #header = self.dlg.objectInfo.horizontalHeader()
        #self.dlg.objectInfo.setColumnWidth(0,100)
        #self.dlg.objectInfo.setColumnWidth(1,100)
        #self.dlg.objectInfo.setColumnWidth(2,100)
        #header.setDefaultAlignment(QtCore.Qt.AlignHCenter)
        #header.setResizeMode(QtGui.QHeaderView.Fixed)
        #self.dlg.objectInfo.verticalHeader().setMovable(True)
        #self.dlg.objectInfo.clicked.connect(self.objectInfoClicked)

        self.dlg.tableWidgetDetail.setColumnWidth(0,120)
        self.dlg.tableWidgetDetail.setColumnWidth(1,120)
        self.dlg.tableWidgetDetail.setColumnWidth(2,120)
        self.dlg.tableWidgetDetail.setColumnWidth(3,120)
        self.dlg.tableWidgetDetail.setColumnWidth(4,120)

        self.dlg.tableWidgetDetailCounts.setColumnWidth(0,230)
        self.dlg.tableWidgetDetailCounts.setColumnWidth(1,80)


#Load main project
        self.project_load()

        #Stores name of currently active layer. Need this since rubber band sets itself current
        #so must set back
        self.cur_lay = ""

        #List of points in last created Rubberband
        self.rubberbandPoints = []

        #self.dlg.tableView.selectRow(0)

        #self.dlg.objectInfo.selectRow(0)

        self.dlg.radioButtonWellbeing.setChecked(True)

        #Read database with marine value details and keep in memory for quick access.
        #Read only required fields
        self.dlg.list_of_values = []
        self.readSQLiteDB()

        chktime_time = datetime.datetime.now()
        chktime_step = 70
        chk = [chktime_time, chktime_step]
        self.dlg.checktime.append(chk)

        #Set MARVIN's position and size
        px = self.dlg.geometry().x = 10
        py = self.dlg.geometry().y = 30
        dw = self.dlg.width = 350
        #dh = self.dlg.height = 960
        sh = GetSystemMetrics(1) #Determine screen height

        chktime_time = datetime.datetime.now()
        chktime_step = 75
        chk = [chktime_time, chktime_step]
        self.dlg.checktime.append(chk)

        if sh > 780:
            twh = sh - self.dlg.tableWidgetDetailCounts.y() - 80
            self.dlg.tableWidgetDetailCounts.setMinimumHeight(twh)
            self.dlg.tableWidgetDetailCounts.setMaximumHeight(twh) 
            dh = sh - 70
        else:
            self.dlg.tableWidgetDetailCounts.height = 200
            dh = 810
        self.dlg.setGeometry( px, py, dw, dh )

        chktime_time = datetime.datetime.now()
        chktime_step = 80
        chk = [chktime_time, chktime_step]
        self.dlg.checktime.append(chk)

        #Set mouse pointer in case we crashed and pointer was still in rubberband mode
        #Does not work
        self.iface.actionPan().trigger()
        #self.iface.mapCanvas.actionZoomIn()

        chktime_time = datetime.datetime.now()
        chktime_step = 90
        chk = [chktime_time, chktime_step]
        self.dlg.checktime.append(chk)

        ## show the dialog
        self.dlg.show()

        chktime_time = datetime.datetime.now()
        chktime_step = 100
        chk = [chktime_time, chktime_step]
        self.dlg.checktime.append(chk)

        for tt in self.dlg.checktime:
            print tt

        self.OrigExtent()

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed

        #if result:
        if result == 1:
            pass




    def unload(self):
        pass
        """Removes the plugin menu item and icon from QGIS GUI."""
#        for action in self.actions:
#            self.iface.removePluginMenu(
#                self.tr(u'&CSIRO Marine Values'), action)
#            self.iface.removeToolBarIcon(action)
        # remove the toolbar
#        del self.toolbar

    def endButtonClicked(self):
        self.xclosing()

    def closeEvent(self, event):
        self.xclosing()

    def xclosing(self):
        print "MARVIN unloading..."
        self.treeLayerIdx = 0
        """Removes the Marine Values plugin icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removeToolBarIcon(action)
        del self.toolbar
        QtCore.QObject.disconnect(self.iface.mapCanvas(), QtCore.SIGNAL("renderComplete(QPainter *)"), self.renderTest)
        QtCore.QObject.disconnect(self.dlg.tableView.verticalHeader(), QtCore.SIGNAL("sectionMoved(int, int, int)"), self.tableViewRowMoved)        
        QtCore.QObject.disconnect(self.dlg.tableView, QtCore.SIGNAL("clicked(const QModelIndex & index)"), self.tableViewClicked)
        self._want_to_close = True
        self.dlg.close()
#        self = None


    def pushButtonClicked(self):
        items = self.dlg.listWidget.selectedItems()
        x=[]
        for i in list(items):
            stp = str(i.text())
            x.append(stp)
            qset = QSettings()
            defpath = qset.value("marine_values/default_path", "")
            layer = self.iface.addVectorLayer(defpath, "layer name you like", "ogr")

    def manageLayer(self, x, index):
        #Write code here to load and unload layers and save project
        try:
            x
        except IOError:
            pass

    def project_load(self):
#        project = QgsProject.instance()
        qset = QSettings()
        defpath = qset.value("marine_values/default_path", "")
        
#        project = QgsProject.instance()
        self.project.fileName()
        filen = os.path.splitext(ntpath.basename(self.project.fileName()))[0]

        if filen != "marine_values":

            if not self.project.read(QFileInfo(defpath + '\marine_values.qgs')):
                self.dlg.error.setText("Could not load marine_values.qgs")
            elif len(self.project.layerTreeRoot().findLayers()) < 1:
                self.dlg.error.setText("No layers found")
            else:
                pass

#TESTTEST WFS
        #Note that the name of a WFS layer may not contain any spaces or it will fail to load
#        uri = "http://cmar-geo.bne.marine.csiro.au:8080/geoserver/mqcfr/wfs?service=WFS&typename=mqcfr:MarineValuesNewBritainTestLLG"
#        vlayer = QgsVectorLayer(uri, "MarineValuesNewBritainTestLLG", "WFS")
#        QgsMapLayerRegistry.instance().addMapLayer(vlayer)
#TESTTEST


        #self.dlg.tableView.model().itemChanged.connect(lambda x: self.manageLayer(self, x))
        self.treeLayerIdx = 0
        position = {}
        self.layerInfo = {}
        for treeLayer in self.project.layerTreeRoot().findLayers():
            layer = treeLayer.layer()
            for i in range(self.dlg.tableView.model().rowCount()):

                item = self.dlg.tableView.model().item(i, 0)

                #Skip the row which is the divider between loaded and unloaded items
                it4 = self.dlg.tableView.model().item(i, 2)
                it5 = it4.text()
                if it5 == '90000':
                    pass

                else:

                    if item.text() in layer.source().split("|")[0]:
                        #self.layerInfo[item.text()] = self.getLayerInfo(layer)
                        self.dlg.tableView.model().item(i, 0).setCheckState(QtCore.Qt.Checked)
                        #Set column 4 to same as checkbox. Click on checkox is hard to 
                        #catch so using thisas indicator
                        self.dlg.tableView.model().item(i, 3).setText(self.tr('checked'))


                        geometryType = self.dlg.tableView.model().item(i, 1)
                        geometryType.setText(self.geometryTypes[layer.geometryType()])
                        sortOrder = self.dlg.tableView.model().item(i, 2)
                        sortOrder.setText('{:05d}'.format(self.treeLayerIdx))
            self.treeLayerIdx += 1
        #print self.layerInfo
        self.dlg.tableView.model().sort(2)







#    def getLayerInfo(self, layer):
        #layerInfo = []
        #request = QgsFeatureRequest()
        #request.setSubsetOfAttributes(['name','id'],layer.pendingFields())
        #request.setFlags(QgsFeatureRequest.NoGeometry)
        #for feature in layer.getFeatures(request):
        #    geom = feature.geometry()
        #    if len(feature.attributes()) > 3:
        #        layerInfo.append(feature.attributes()[3])
        #        model = QStandardItemModel()
        #        model.setColumnCount(3)
        #        model.setHorizontalHeaderLabels(['Layer', 'Type', 'Sort Key', 'Chk ind'])
        #        item = QStandardItem("\n".join(layerInfo[0]))
        #        model.appendRow([item, QStandardItem('unknown'), QStandardItem('99999')])
        #        self.dlg.objectInfo.setModel(model)



    def tableViewselectionChanged(self):
        getLayerInfo()        

    def tableViewClicked(self, index):
        if QgsMapLayerRegistry.instance().mapLayers():
            row = index.row()
            model = self.dlg.tableView.model()

            valx = model.item(row, 0)
            val = valx.text()
            if val != "Unloaded layers:":
                val_wo_ext = os.path.splitext(val)[0]

                qset = QSettings()
                defpath = qset.value("marine_values/default_path", "")
                sfile = os.path.join(defpath, val)

                ##############################################################
                #This is how to read cell content of tableView
                #it = model.item(row, 3)
                #print it.text()
                ##############################################################

                #Since mouse click on tableView row cannot determine if the checkbox
                #was clicked (which controls loading/unloading of layers) or if the 
                #row was clicked elsewhere (which makes a layer active) we store the click
                #status in column 3 and check the checkbox state against it to see if
                #the checkbox was clicked.
                v2 = model.item(row, 3)
                v2a = v2.text()

                #Was unchecked and has now been checked
                if v2a == "not checked" and model.item(row,0).checkState() == QtCore.Qt.Checked: 
                #if model.item(row,0).checkState() == QtCore.Qt.Checked:
                    layer = self.iface.addVectorLayer(sfile, val_wo_ext, "ogr")
                    lid = layer.id()

                    #Add map to layer registry
                    QgsMapLayerRegistry.instance().addMapLayer(layer)

                    #Previously loaded items are reordered starting with value 2
                    neworder = 2
                    for i in range(self.dlg.tableView.model().rowCount()):
                        it4 = self.dlg.tableView.model().item(i, 2)
                        it5 = it4.text()
                        if it5 == '90000': #Arrived at divider between loaded and unloaded layers
                            break
                        model.item(i, 2).setText('{:05d}'.format(neworder))
                        neworder += 1


                    model.item(row, 3).setText(self.tr('checked'))
                    #Newly loaded layer gets order 1, which is default QGIS behavious, set it on top
                    model.item(row, 2).setText('{:05d}'.format(1)) 
                    #self.treeLayerIdx += 1

                    #Look up layer geometry type
                    root = QgsProject.instance().layerTreeRoot()
                    lyr3 = root.findLayer(lid).layer()
                    geot = self.geometryTypes[lyr3.geometryType()]
                    model.item(row, 1).setText(self.tr(geot))


                    self.dlg.tableView.model().sort(2)
                    return

                #Was checked and has now been unchecked
                if v2a == "checked" and model.item(row,0).checkState() == QtCore.Qt.Unchecked:
                    model.item(row, 3).setText(self.tr('not checked'))
                    for layer in QgsMapLayerRegistry.instance().mapLayers().values():
                        if val_wo_ext == layer.name():
                            QgsMapLayerRegistry.instance().removeMapLayer(layer)
                            self.treeLayerIdx -= 1
                            model.item(row, 2).setText(self.tr('99999'))
                            self.dlg.tableView.model().sort(2)
                            return
                
                #Checkbox has not been clicked. Process as set layer active   
                for treeLayer in self.project.layerTreeRoot().findLayers():
                    pass
                    #layer = treeLayer.layer()
                    #lnam = layer.name()

                    #if val_wo_ext == lnam:
                    #    self.iface.setActiveLayer(layer)
                    #    self.cur_lay = layer.name()

                    #    if self.cur_lay.endswith('LLG'):
                    #        self.cur_scale_id = "LLG"
                    #    if self.cur_lay.endswith('Districts'):
                    #        self.cur_scale_id = "Districts"
                    #    if self.cur_lay.endswith('Features'):
                    #        self.cur_scale_id = "Features"

                layer = self.iface.activeLayer()
                lna = layer.name()
                if lna.endswith('LLG'):
                    self.cur_scale_id = "LLG"
                if lna.endswith('Districts'):
                    self.cur_scale_id = "Districts"
                if lna.endswith('Features'):
                    self.cur_scale_id = "Features"

                if self.cur_scale_id == "LLG" or self.cur_scale_id == "Districts":
                    if layer:
                        iter = layer.getFeatures()

                        #Using column names (to find index of column) rather than column ids.
                        #so can change column order but not names
                        idx_spatfeat = layer.fieldNameIndex('spat_feat')
                        if self.cur_scale_id == "LLG":
                            idx_llg_dist = layer.fieldNameIndex('llg')
                        if self.cur_scale_id == "Districts":
                            idx_llg_dist = layer.fieldNameIndex('district')
                        idx_foodsec = layer.fieldNameIndex('food_secur')
                        idx_wellbeing = layer.fieldNameIndex('well_being')
                        idx_income = layer.fieldNameIndex('income')

                        feat_count = 0
                        attx3 = []
                        attb = []

                        imporval = None #Do not declare a type
                        col_choice = None
                        headi = ""
                        if self.dlg.radioButtonWellbeing.isChecked():
                            headi = "Human wellbeing"
                            col_choice = idx_wellbeing
                            col_choicex = "well_being"
                        if self.dlg.radioButtonSecurity.isChecked():
                            headi = "Food security"
                            col_choice = idx_foodsec
                            col_choicex = "food_secur"
                        if self.dlg.radioButtonIncome.isChecked():
                            headi = "Income"
                            col_choice = idx_income
                            col_choicex = "income"

                        for feature in iter:

                            feat_count += 1;
                            geom = feature.geometry()

                            # show some information about the feature
                #            if geom.type() == QGis.Point:
                #                x = geom.asPoint()
                #                #print "Point: " + str(x)
                #            elif geom.type() == QGis.Line:
                #                x = geom.asPolyline()
                #                print "Line: %d points" % len(x)
                #            elif geom.type() == QGis.Polygon:
                #                x = geom.asPolygon()
                #                numPts = 0
                #                for ring in x:
                #                    numPts += len(ring)
                #                #print "Polygon: %d rings with %d points" % (len(x), numPts)
                #            else:
                #                pass #Dummy statement so next one can be rem'ed w/o failing
                                #print "Unknown"

    #                        if feature.attributes:
    #                            attrs = feature.attributes()
    #                            if len(attrs) > 2:

    #                                arear = str(attrs[col_choice])
    #                               gg = [attrs[idx_spatfeat],arear,attrs[idx_llg_dist]]
    #                                attb.append(gg)

    #                    model = QStandardItemModel()
    #                    model.setColumnCount(3)
    #                    model.setHorizontalHeaderLabels(['Scale name', 'Spatial feature', headi])

    #                    for itc in attb:
    #                        item = QStandardItem("1")
    #                        vals = itc[1]

    #                        if vals == "NULL":
    #                            model.appendRow([QStandardItem(itc[2]), QStandardItem(itc[0]),QStandardItem("")])
    #                        else:
    #                            valf = float(vals)
    #                            valr = round(valf,4)
    #                            valo = "{0:.4f}".format(valr)
    #                            model.appendRow([QStandardItem(itc[2]), QStandardItem(itc[0]),QStandardItem(valo)])

    #                    self.dlg.objectInfo.setModel(model)

                    else:
                        self.dlg.error.setText("Layer not loaded.")
    #            else:
    #                model = QStandardItemModel()
    #                self.dlg.objectInfo.setModel(model)
    #                model.clear()
            else:
                self.dlg.error.setText("No map layers.")

    def saveProjectClicked(self):
        #project = QgsProject.instance()
        if self.project.write():
            self.dlg.error.setText("Project saved")
        else:
            self.dlg.error.setText("Project not saved. File may be writeprotected.")

    def renderTest(self, painter):
        # use painter for drawing to map canvas
        print ""

    def tableViewRowMoved(self, row, old_index, new_index):
        str1 = "row:" + str(row) + ", old_index:" + str(old_index) + ", new_index:" + str(new_index)
        print str1

        #Previously loaded items are reordered
        neworder = 1
        model = self.dlg.tableView.model()

        for i in range(self.dlg.tableView.model().rowCount()):
            it4 = self.dlg.tableView.model().item(i, 2)
            it5 = it4.text()
            if it5 == '90000': #Arrived at divider between loaded and unloaded layers
                break
            model.item(i, 2).setText('{:05d}'.format(neworder))
            neworder += 1





        #for layer in QgsMapLayerRegistry.instance().mapLayers().values():
        #        if val_wo_ext == layer.name():
        #            QgsMapLayerRegistry.instance().removeMapLayer(layer)

        #Move layer from old to new position in layertree

        for treeLayer in self.project.layerTreeRoot().findLayers():
            layer = treeLayer.layer()
            idd = layer.Id()
            print idd
            lnam = layer.name()
            print lnam


        #root = QgsProject.instance().layerTreeRoot()
        #layid = project.layerTreeRoot().findLayer(new_index).Id()
        #lyr3 = root.findLayer(layid).layer()
        #lyr3.id = new_index

    def pushButtonExportClicked(self):
        path = QtGui.QFileDialog.getSaveFileName(None,"Export data",self.plugin_dir,"Comma Separated Values Spreadsheet (*.csv);;""All Files (*)")
        if not path:
            return
        else:

            with open(unicode(path), 'wb') as stream:
                writer = csv.writer(stream, delimiter=',')
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
                h = ["Area values:"]
                writer.writerow(h)
                h = ["Scale name","Spatial feature/Value","Value metric score","Selected km2/Calc","Area km2"]
                writer.writerow(h)
                for row in range(self.dlg.tableWidgetDetail.rowCount()):
                    rowdata = []
                    for column in range(self.dlg.tableWidgetDetail.columnCount()):
                        item = self.dlg.tableWidgetDetail.item(row, column)
                        if item is not None:
                            rowdata.append(
                                unicode(item.text()).encode('utf8'))
                        else:
                            rowdata.append('')
                    writer.writerow(rowdata)

                writer.writerow("")
                g = ["Countable values:"]
                writer.writerow(g)
                g = ["Value type","Count"]
                writer.writerow(g)
                for row in range(self.dlg.tableWidgetDetailCounts.rowCount()):
                    rowdata = []
                    for column in range(self.dlg.tableWidgetDetailCounts.columnCount()):
                        item = self.dlg.tableWidgetDetailCounts.item(row, column)
                        if item is not None:
                            rowdata.append(
                                unicode(item.text()).encode('utf8'))
                        else:
                            rowdata.append('')
                    writer.writerow(rowdata)


    def pushButtonPanClicked(self):
        self.iface.actionPan().trigger()

    def pushButtonZoomPlusClicked(self):
        self.iface.actionZoomIn().trigger()

    def pushButtonZoomMinusClicked(self):
        self.iface.actionZoomOut().trigger()

    def rubberbandClicked(self):
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


    def showRBCoordinates(self, currentPos):
        if self.myRubberBand and self.myRubberBand.numberOfVertices():
            self.myRubberBand.removeLastPoint()
            self.myRubberBand.addPoint(currentPos)



    def manageClick(self, currentPos, clickedButton):
        
        if clickedButton == Qt.LeftButton:
            self.myRubberBand.addPoint(currentPos)


        if clickedButton == Qt.RightButton:
            self.dlg.tableWidgetDetail.setRowCount(0)
            self.dlg.tableWidgetDetailCounts.setRowCount(0)

            self.iface.mapCanvas().xyCoordinates.disconnect(self.showRBCoordinates)
            self.iface.mapCanvas().setMapTool(self.previousMapTool)

            geom_rb = self.myRubberBand.asGeometry()

            #Create in-memory layer from Rubberband geometry for later processing
            vlx = QgsVectorLayer("Polygon?crs=epsg:4326", "rubber_band", "memory")
            prx = vlx.dataProvider()
            # Enter editing mode
            vlx.startEditing()
            # add fields
            prx.addAttributes( [ QgsField("id", QVariant.Int) ] )
            # add a feature
            fetx = QgsFeature()
            fetx.setGeometry(geom_rb)
            fetx.setAttributes([0, "Feature"])
            prx.addFeatures( [ fetx ] )
            vlx.updateExtents()
            # Commit changes
            vlx.commitChanges()
            QgsMapLayerRegistry.instance().addMapLayers([vlx])


            #Getting coordinates to save rubber band to tableViewRB
            clay = QgsMapLayerRegistry.instance().mapLayersByName("rubber_band")[0]




            #symbol = QgsMarkerSymbolV2.createSimple({'name': 'square', 'color': 'red'})
            
            symbol = QgsSymbolV2.defaultSymbol(clay.geometryType())
            symbol.setColor(QColor("transparent"))
            clay.rendererV2().setSymbol(symbol)


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
            for layerIterator in ql:
                layname = layerIterator.name()
                #Only processing vector layers
                if layerIterator.type() == QgsMapLayer.VectorLayer:
                    if layerIterator.geometryType() == 2:
                        #Only processing where name of layer = 'Marine Values' or 'MarineValues' for a wfs layer
                        if layname[:13] == ("Marine Values") or layname[:12] == "MarineValues":

#DO NOT remove but rather append to output written to tableWidgetDetail and tableWidgetDetailCounts

                            layer = layerIterator
                            if layer:
                                if layname.endswith('LLG'):
                                    self.cur_scale_id = "LLG"
                                if layname.endswith('Districts'):
                                    self.cur_scale_id = "Districts"
                                if layname.endswith('Features'):
                                    self.cur_scale_id = "Features"

                                clp_lay = layer.name()

                                iter = layer.getFeatures()

                                for feature in iter:
                                    geom_feat = feature.geometry()
                                
                                #No sure why this test was here. There are problems using it (no feature selected with smaller rubberband area)
                                #if geom_rb.intersects(geom_feat):
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
                                res_lay = QgsMapLayerRegistry.instance().mapLayersByName("Clipped")[0]
                                res_lay.updateExtents()
                                res_feat = res_lay.getFeatures()

                                #Clear selected objects list view
                                model = QStandardItemModel(0,0)
                                model = QStandardItemModel(1,1)

        #***** AREA PERCENTAGES *************************************************************************************************
                                #For layers which are processed spatially, ie area proportions are calculated for features: LLG and Districts
                                if self.cur_scale_id == "LLG" or self.cur_scale_id == "Districts":

# H E A D E R
                                    #Red header for each layer
                                    rowPosition = self.dlg.tableWidgetDetail.rowCount()
                                    self.dlg.tableWidgetDetail.insertRow(rowPosition)
                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 0, QtGui.QTableWidgetItem(layname + " ---------------------------------"))
                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 1, QtGui.QTableWidgetItem(""))
                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 2, QtGui.QTableWidgetItem(""))
                                    self.dlg.tableWidgetDetail.setSpan(rowPosition, 0, 1, 3)
                                    for col in range(0,3):
                                        self.dlg.tableWidgetDetail.item(rowPosition,col).setBackground(QBrush(QColor(188,69,57)))
                                    self.dlg.tableWidgetDetail.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetail.verticalHeader().minimumSectionSize())
                                    self.dlg.tableWidgetDetail.setRowHeight(rowPosition,17)



                                    idx_llg_dist = ""
                                    idx_spatfeat = res_lay.fieldNameIndex('spat_feat')
                                    if self.cur_scale_id == "LLG":
                                        idx_llg_dist = res_lay.fieldNameIndex('llg')
                                    if self.cur_scale_id == "Districts":
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
                                        spat_feat_qry = ""
                                        llg_qry = ''
                                        res_geom = f.geometry()

                                        if f.attributes:
                                            attry = f.attributes()
                                            if len(attry) > 2:

                                                if res_geom != None:
                                                    d = QgsDistanceArea()
                                                    d.setEllipsoidalMode(True)
                                                    art = res_geom.area()
                                                    ar = d.convertMeasurement(art, QGis.Degrees, QGis.Kilometers, True)     
                                                    arx = str(ar[0])
                                                    rub = ar[0] #rub is used further down where each sub area is retrieved from list
                                                    shapar = attry[idx_shapar] #shapar (feature area) is used further down where each sub area is retrieved from list
                                                    
                                                    for cfs in self.dlg.list_of_values:
                                                        if (cfs[2] == "llg" and self.cur_scale_id == "LLG") or (cfs[2] == "dist" and self.cur_scale_id == "Districts"):
                                                            if cfs[0] == attry[idx_spatfeat]:
                                                                if cfs[1] == attry[idx_llg_dist]:
                                                                    doInsert = False
                                                                    if self.dlg.radioButtonWellbeing.isChecked():
                                                                        if cfs[6] == "Importance for human wellbeing":
                                                                            doInsert = True
                                                                    if self.dlg.radioButtonSecurity.isChecked():
                                                                        if cfs[6] == "Importance for food security":
                                                                            doInsert = True
                                                                    if self.dlg.radioButtonIncome.isChecked():
                                                                        if cfs[6] == "Importance for income":
                                                                            doInsert = True
                                                                    if doInsert:
                                                                        csomt = float(cfs[4])
                                                                        csomtot = csomtot + csomt



            #                                    dis_val = ""
            #                                    if self.dlg.radioButtonWellbeing.isChecked():
            #                                        if attry[idx_wellbeing]:
            #                                            dis_val = attry[idx_wellbeing]

            #                                    if self.dlg.radioButtonSecurity.isChecked():
            #                                        if attry[idx_foodsec]:
            #                                            dis_val = attry[idx_foodsec]

            #                                    if self.dlg.radioButtonIncome.isChecked():
            #                                        if attry[idx_income]:
            #                                            dis_val = attry[idx_income]

                                                rowPosition = self.dlg.tableWidgetDetail.rowCount()
                                                self.dlg.tableWidgetDetail.insertRow(rowPosition)
                                                self.dlg.tableWidgetDetail.setItem(rowPosition, 0, QtGui.QTableWidgetItem(attry[idx_llg_dist]))
                                                self.dlg.tableWidgetDetail.setItem(rowPosition, 1, QtGui.QTableWidgetItem(attry[idx_spatfeat]))

                                                if csomtot:
                                                    # Round to four digits and display with four digits
                                                    csomtot = "{0:.4f}".format(round(float(csomtot),4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 2, QtGui.QTableWidgetItem(csomtot))
                                                else:
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 2, QtGui.QTableWidgetItem(""))

#                                                try:
#                                                 arx
#                                                except (TypeError, UnboundLocalError) as e:
#                                                else:
                                                    # Round to four digits and display with four digits
                                                try:
                                                    arx = "{0:.4f}".format(round(float(arx),4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 3, QtGui.QTableWidgetItem(arx))
                                                except (TypeError, UnboundLocalError):
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 3, QtGui.QTableWidgetItem("Error"))
                                                    self.dlg.error.setText("Error calculating area. Invalid rubberband geometry. Select an area that has at least three points and is not self-intersecting")

                                                #shape area
                                                if shapar:
                                                    # Round to four digits and display with four digits
                                                    shapar = "{0:.4f}".format(round(float(shapar),4))
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 4, QtGui.QTableWidgetItem(shapar))
                                                else:
                                                    self.dlg.tableWidgetDetail.setItem(rowPosition, 4, QtGui.QTableWidgetItem(""))



                                                for col in range(0,5):
                                                    self.dlg.tableWidgetDetail.item(rowPosition,col).setBackground(QBrush(QColor.fromRgb(198,187,107)))

                                        #self.dlg.list_of_values
                                        #[0]: 17 - spatial_feature_name
                                        #[1]:  8 - scale_name
                                        #[2]:  7 - scale_id
                                        #[3]:  1 - value_name
                                        #[4]: 12 - value_metric_score
                                        #[5]:  4 - value_type
                                        #[6]: 10 - value_metric_description
                                        #[7]:      spatial_feature_id


                                            for cf in self.dlg.list_of_values:

                                                if (cf[2] == "llg" and self.cur_scale_id == "LLG") or (cf[2] == "dist" and self.cur_scale_id == "Districts"):
                                                    #Looking for all that are in the same spatial_feature category
                                                    if cf[0] == attry[idx_spatfeat]:
                                                        #Looking for all that are in the same LLG/District
                                                        if cf[1] == attry[idx_llg_dist]:

                                                            doInsert = False
                                                            if self.dlg.radioButtonWellbeing.isChecked():
                                                                if cf[6] == "Importance for human wellbeing":
                                                                    doInsert = True
                                                            if self.dlg.radioButtonSecurity.isChecked():
                                                                if cf[6] == "Importance for food security":
                                                                    doInsert = True
                                                            if self.dlg.radioButtonIncome.isChecked():
                                                                if cf[6] == "Importance for income":
                                                                    doInsert = True
                                                            if doInsert:
                                                                try:
                                                                    csom = float(cf[4]) * rub / float(shapar)
                                                                    csom = "{0:.4f}".format(round(csom,4))
                                                                except TypeError:
                                                                    csom = "Error"
                                                                    self.dlg.error.setText("Error calculating area. Invalid rubberband geometry. Select an area that has at least three points and is not self-intersecting")

                                                                rowPosition = self.dlg.tableWidgetDetail.rowCount()
                                                                self.dlg.tableWidgetDetail.insertRow(rowPosition)
                                                                self.dlg.tableWidgetDetail.setItem(rowPosition, 1, QtGui.QTableWidgetItem(cf[3]))
                                                                self.dlg.tableWidgetDetail.setItem(rowPosition, 2, QtGui.QTableWidgetItem(cf[4]))
                                                                self.dlg.tableWidgetDetail.setItem(rowPosition, 3, QtGui.QTableWidgetItem(csom))
                                                                #self.dlg.tableWidgetDetail.setItem(rowPosition, 4, QtGui.QTableWidgetItem(cf[2]))
                                                                #self.dlg.tableWidgetDetail.setItem(rowPosition, 5, QtGui.QTableWidgetItem(cf[1]))
                                                                #self.dlg.tableWidgetDetail.setItem(rowPosition, 6, QtGui.QTableWidgetItem(cf[0]))
                                                                self.dlg.tableWidgetDetail.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetail.verticalHeader().minimumSectionSize())
                                                                self.dlg.tableWidgetDetail.setRowHeight(rowPosition,17)

        #****COUNTS************************************************************************

                                #For layers which are processed in counts: Features

                                if self.cur_scale_id == "Features":
# H E A D E R
                                    #Red header for each layer
                                    rowPositionC = self.dlg.tableWidgetDetailCounts.rowCount()
                                    self.dlg.tableWidgetDetailCounts.insertRow(rowPositionC)
                                    self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 0, QtGui.QTableWidgetItem(layname + " ----------------------------------"))
                                    self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 1, QtGui.QTableWidgetItem(""))
                                    self.dlg.tableWidgetDetailCounts.setItem(rowPositionC, 2, QtGui.QTableWidgetItem(""))
                                    self.dlg.tableWidgetDetailCounts.setSpan(rowPositionC, 0, 1, 2)
                                    for colc in range(0,2):
                                        self.dlg.tableWidgetDetailCounts.item(rowPositionC,colc).setBackground(QBrush(QColor.fromRgb(188,69,57)))
                                    self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())
                                    self.dlg.tableWidgetDetailCounts.setRowHeight(rowPositionC,17)

                                    lstValueTypes = []
                                    for f in res_feat:
                                        res_geom = f.geometry()
                                        idx_poly_id = res_lay.fieldNameIndex('poly_id')
                                        idx_point_id = res_lay.fieldNameIndex('point_1')                                
                                        proc_type = ""
                                        if f.attributes:
                                            poly_id = ""
                                            point_id = ""
                                            attry = f.attributes()

                                            if attry[idx_poly_id] == None:
                                                proc_type = "POINT"
                                                point_id = "PNT_" + str(attry[idx_point_id])
                                            else:
                                                proc_type = "POLY"
                                                poly_id = "POLY_" + str(attry[idx_poly_id])
                                            count_detail = 0
                                            for cfs in self.dlg.list_of_values:
                                                if cfs[5] in ["Carbon sequestration","Hazard reduction","Water regulation","Biological diversity","Importance for ETP species or habitats","Naturalness","Productivity or nutrient cycling","Rarity/uniqueness","Vulnerability, sensitivity or slow recovery","Natural resources","Cultural heritage importance","Recreational, tourism or aesthetic importance","Spiritual importance"]:
                                                    
                                                    cc = str(cfs[7])
                                                    if (proc_type == "POLY" and poly_id == cc) or (proc_type == "POINT" and point_id == cc):
                                                        count_detail = count_detail + 1

                                                        if len(lstValueTypes) > 0:
                                                            founda = False
                                                            for elem in lstValueTypes:
                                                                if elem[0] == cfs[5]:
                                                                    elem[1] = elem[1] + 1
                                                                    founda = True
                                                            if not founda:
                                                                ladd1 = [cfs[5],1]
                                                                lstValueTypes.append(ladd1)
                                                        else:
                                                            ladd2 = [cfs[5],1]
                                                            lstValueTypes.append(ladd2)

                                    for elem70 in lstValueTypes:
                                        rowPosition = self.dlg.tableWidgetDetailCounts.rowCount()
                                        self.dlg.tableWidgetDetailCounts.insertRow(rowPosition)
                                        self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 0, QtGui.QTableWidgetItem(elem70[0]))
                                        self.dlg.tableWidgetDetailCounts.setItem(rowPosition, 1, QtGui.QTableWidgetItem(str(elem70[1])))
                                        self.dlg.tableWidgetDetailCounts.verticalHeader().setDefaultSectionSize(self.dlg.tableWidgetDetailCounts.verticalHeader().minimumSectionSize())

            #**********************************************************************************

                                else:
                                    pass

                                for treeLayer in self.project.layerTreeRoot().findLayers():                
                                    layer_f2 = treeLayer.layer()
                                    if layer_f2.name() == "Clipped":
                                        QgsMapLayerRegistry.instance().removeMapLayer(layer_f2.id())


            self.myMapTool.deleteLater()
            self.iface.mapCanvas().scene().removeItem(self.myRubberBand)

            for treeLayer in self.project.layerTreeRoot().findLayers():                
                layer_f2 = treeLayer.layer()
                if layer_f2.name() == "rubber_band":
                    QgsMapLayerRegistry.instance().removeMapLayer(layer_f2.id())



    def readSQLiteDB(self):
        db = QSqlDatabase.addDatabase("QSQLITE");
        # Reuse the path to DB to set database name
        #db.setDatabaseName("C:\\Users\\Default.Default-THINK\\.qgis2\\python\\plugins\\marine_values\\chinook.db")
        db.setDatabaseName(self.plugin_dir + "\\marine_values.db")
        # Open the connection
        db.open()
        # query the table
        query = db.exec_("select * from marine_values_all")

        # Play with results (not efficient, just for demo)
        while query.next():
            record = query.record()
            #Getting these fields:
            # 17 - spatial_feature_name  * used to query
            #  8 - scale_name            * used to query
            #  7 - scale_id              * used to query
            #  1 - value_name
            # 12 - value_metric_score
            #  4 - value_type
            # 10 - value_metric_description

            idx_spatfeatnam = query.record().indexOf('spatial_feature_name')
            idx_scalenam = query.record().indexOf('scale_name')
            idx_scaleid = query.record().indexOf('scale_id')
            idx_valnam = query.record().indexOf('value_name')
            idx_valmetscore = query.record().indexOf('value_metric_score')
            idx_valtype = query.record().indexOf('value_type')
            idx_valmetdesc = query.record().indexOf('value_metric_description')
            idx_spatial_feature_id = query.record().indexOf('spatial_feature_id')

            #listv = [str(record.value(17)), str(record.value(8)), str(record.value(7)), str(record.value(1)), str(record.value(12)), str(record.value(4)), str(record.value(10))]
            listv = [str(record.value(idx_spatfeatnam)), str(record.value(idx_scalenam)), str(record.value(idx_scaleid)), str(record.value(idx_valnam)), str(record.value(idx_valmetscore)), str(record.value(idx_valtype)), str(record.value(idx_valmetdesc)), str(record.value(idx_spatial_feature_id))]
            self.dlg.list_of_values.append(listv)


#            for index in range(record.count()):
#                lst = [1,2,3,4,5,6]
#                if index in lst: #To read only second field. Change to read other fields
#                    values.append(str(record.value(index)))
#            print ';'.join(values)        


    def pushButtonOrigExtentClicked(self):
        self.OrigExtent()

    def OrigExtent(self):
        mapExtentRect = QgsRectangle(147.9,-3.4,152.8,-6.6)
        mc = self.iface.mapCanvas() 
        mc.setExtent(mapExtentRect)
        self.iface.mapCanvas().zoomScale(1600000)
#        self.dlg.list_of_values = []
#        line = np.genfromtxt('temp.txt', usecols=3, dtype=[('floatname','float')], skip_header=1)
#        list_of_values.append(line)




# *********************** Other Classes **********************************************
# ************************************************************************************


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
        self.setHorizontalHeaderLabels(['Layer', 'Type', 'Sort Key'])

        qset = QSettings()
        defpath = qset.value("marine_values/default_path", "")
        if defpath and not defpath.isspace():
            pass
        else:
            dirp = QtGui.QFileDialog.getExistingDirectory(None, 'Select a default folder (for shapefiles):', 'C:\\', QtGui.QFileDialog.ShowDirsOnly)
            qset.setValue("marine_values/default_path", dirp)
            defpath = qset.value("marine_values/default_path", "")

        onlyfiles = []
        for f in listdir(defpath):
            if isfile(join(defpath, f)):
                if f.endswith('.shp'):
                    onlyfiles.append(f)


#TESTTEST WFS
#        tt = "MarineValuesNewBritainTestLLG"
#        onlyfiles.append(tt)
#TESTTEST


        if not len(onlyfiles):
            self.dlg.error.setText("Default directory does not contain any spatial files.")
        else:
            if not self.filled:
                self.filled = True
                onlyfiles.sort()
                for fil in onlyfiles:
                    self.d = QStandardItem(fil)
                    self.d.setTextAlignment(QtCore.Qt.AlignLeft)
                    self.d.setText = "testing"
                    self.d.setCheckable(True) 
                    #self.d.setFlags(QtCore.Qt.ItemIsUserCheckable| QtCore.Qt.ItemIsEnabled)
                    qsi = QStandardItem('unknown')
                    qsi.setBackground(QBrush(QColor.fromRgb(198,187,107)))
                    self.appendRow([self.d, qsi, QStandardItem('99999'), QStandardItem('not checked')])
                #Add row which is the divider between loaded and unloaded layers
                self.appendRow([QStandardItem('Unloaded layers:'), QStandardItem(''), QStandardItem('90000'), QStandardItem('not checked')])


        #self.d = QStandardItem("asd")
        #self.d.setCheckable(True)
        #self.d.setFlags(Qt.ItemIsUserCheckable| Qt.ItemIsEnabled)
        #self.appendRow(self.d)

                #item = QStandardItem(fil)
                #item.setCheckable(True)
                #self.appendRow([item, QStandardItem('unknown'), QStandardItem('99999')])


    def data(self, index, role):
        if index.isValid():
            if role == QtCore.Qt.CheckStateRole:
                return super(Model, self).data(index, QtCore.Qt.CheckStateRole)


            '''if role == QtCore.Qt.ToolTipRole:
                print "******* TooTipRole"
                return self.items[row][column]

            if role == QtCore.Qt.EditRole:
                print "******* Edit or display"
                return self.items[row][column]
                #return self.d.text()
                pass

            if role == QtCore.Qt.DisplayRole:
                print "******* Display"
                return self.items[row][column]
                #return self.d.text()
                pass'''

            # Don't delete this line. Makes display go funny
            return super(Model, self).data(index, QtCore.Qt.DisplayRole)

            #print "******* Default"
            #return QStandardItemModel.data(self, index, role)                #return self.checkState(index)
                #if value != 0:
                #    return QtCore.Qt.Checked
                #else:
                #    return QtCore.Qt.Unchecked

            #if role == QtCore.Qt.ItemDataRole:
                #print "role itemdatarole -----------------------"
            #    return self.data(index)
            #elif role==QtCore.Qt.DisplayRole:                
                #print "role displayrole -----------------------"
            #    return QtCore.QVariant(self.items[index.row()])
        #else:
            #print "Index not valid"

    def checkState(self, index):
        if index in self.checks:
            return self.checks[index]
        else:
            return QtCore.Qt.Unchecked


