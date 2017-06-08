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
 *   This program is copyright protected                                   *
 *                                                                         *
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   Help file for this app is in the plugin directory                     *
 *   and called "marine values help.txt"                                   *                                  
 *                                                                         *
 *   Environment Versions                                                  *
 *   ------------------------------------                                  *
 *   QGIS 2.18.2 Las Palmas                                                *
 *   Qt Creator 4.2.0                                                      *
 *                                                                         *
 *                                                                         *
 *   Plugins required:                                                     *
 *   ------------------------------------                                  *
 *                                                                         *
 *   Set up:                                                               *
 *   ------------------------------------                                  *
 *   In Options / Map Tools:                                               *
 *   Preferred distance units: Kilometers                                  *
 *   Preferred area units: Square kilometers                               *
 *   Preferred angle units: Degrees                                        *
 *                                                                         *
 *   In Options / CRS:                                                     *
 *   CRS for new layers: Use a default CRS: Selected CRS (EPSG:4326, WGS 84) *
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   Configuration of the shapefiles and project                           *
 *   Shapefiles and project must be in CRS "WGS84 (EPSG:4326)"             *                                  
 *                                                                         *
 *                                                                         *
 ***************************************************************************/

"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo, QAbstractItemModel, Qt, QVariant
from PyQt4.QtGui import QAction, QIcon, QStandardItemModel, QStandardItem, QHeaderView, QColor
from qgis.gui import QgsRubberBand, QgsMapToolEmitPoint, QgsMapCanvas
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
import processing

project = QgsProject.instance()

class CSIROMarineValues:
    """QGIS Plugin Implementation."""


    def __init__(self, iface):
        #Constructor.

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

        icon_path = ':/plugins/CSIROMarineValues/mv_icon32x32.png'
        self.add_action(
            icon_path,
            text=self.tr(u'CSIRO Marine Values System'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # connect to signal renderComplete which is emitted when canvas
        # rendering is done
        QtCore.QObject.connect(self.iface.mapCanvas(), QtCore.SIGNAL("renderComplete(QPainter *)"), self.renderTest)

        #self.dlg.loadProject.clicked.connect(self.loadProjectClicked)
        self.dlg.saveProject.clicked.connect(self.saveProjectClicked)
        self.dlg.endButton.clicked.connect(self.endButtonClicked)
        self.dlg.rubberband.clicked.connect(self.rubberbandClicked)
        QtCore.QObject.connect(self.dlg.tableView, QtCore.SIGNAL("clicked(const QModelIndex & index)"), self.tableViewClicked)
        QtCore.QObject.connect(self.dlg.objectInfo, QtCore.SIGNAL("clicked(const QModelIndex & index)"), self.tableViewClicked)

        self.dlg.endButton.setDefault(True)
        self.dlg.endButton.setAutoDefault(True)


        #self.iface.mapCanvas().xyCoordinates.connect(showCoordinates)
        #myMapTool.canvasClicked.connect(manageClick)
        #self.iface.mapCanvas().setMapTool(myMapTool)

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
        self.dlg.objectInfo.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.dlg.objectInfo.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        xmodobjinf = ModelObjInfo()
        self.dlg.objectInfo.setModel(xmodobjinf)
        header = self.dlg.objectInfo.horizontalHeader()
        self.dlg.objectInfo.setColumnWidth(0,50)
        self.dlg.objectInfo.setColumnWidth(1,100)
        self.dlg.objectInfo.setColumnWidth(2,100)
        #header.setDefaultAlignment(QtCore.Qt.AlignHCenter)
        header.setResizeMode(QtGui.QHeaderView.Fixed)
        self.dlg.objectInfo.verticalHeader().setMovable(True)
        self.dlg.objectInfo.clicked.connect(self.objectInfoClicked)




        # Set up tableView table ****************************

        #self.dlg.tableView.setModel(model)
        self.dlg.tableView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.dlg.tableView.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        xmod = Model()
        self.dlg.tableView.setModel(xmod)

        header = self.dlg.tableView.horizontalHeader()
        #header.setDefaultAlignment(QtCore.Qt.AlignHCenter)
        header.setResizeMode(QtGui.QHeaderView.Fixed)
        self.dlg.tableView.setColumnWidth(0,200)
        self.dlg.tableView.setColumnWidth(1,100)
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

        #Load main project
        self.project_load()



        self.dlg.tableView.selectRow(0)

        self.dlg.objectInfo.selectRow(0)



        ## show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed

        #if result:
        if result == 1:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass




    def unload(self):
        self.treeLayerIdx = 0
        QtCore.QObject.disconnect(self.iface.mapCanvas(), QtCore.SIGNAL("renderComplete(QPainter *)"), self.renderTest)
        print "MARVIN unloading..."
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&CSIRO Marine Values'), action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

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

    #def loadProjectClicked(self):
    #    return

    def project_load(self):
        project = QgsProject.instance()
        #if project.fileName():
            #self.dlg.error.setText("Please close any currently open projects")
            #return
        qset = QSettings()
        defpath = qset.value("marine_values/default_path", "")
        

        #tryCount is an attempt at solving loading problems. Probalby not needed anymore since
        #end of plugin will terminate QGIS. This is in keeping with QGIS functionality
        #that an application instance cannot exist without an open project file.
        #tryCount = 0
        #while tryCount < 2:

        #print project.fileName()

        if not project.read(QFileInfo(defpath + '\marine_values.qgs')):
            self.dlg.error.setText("Could not load marine_values.qgs")
        elif len(project.layerTreeRoot().findLayers()) < 1:
            self.dlg.error.setText("No layers found")
        else:
            pass
            #tryCount = 9999
            #tryCount += 1





        #self.dlg.tableView.model().itemChanged.connect(lambda x: self.manageLayer(self, x))
        self.treeLayerIdx = 0
        position = {}
        self.layerInfo = {}
        for treeLayer in project.layerTreeRoot().findLayers():
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
        





    def getLayerInfo(self, layer):
        layerInfo = []
        request = QgsFeatureRequest()
        request.setSubsetOfAttributes(['name','id'],layer.pendingFields())
        # Don't return geometry objects
        request.setFlags(QgsFeatureRequest.NoGeometry)
        for feature in layer.getFeatures(request):
            geom = feature.geometry()
            #layerInfo.append("Feature ID %d: " % feature.id())
            if len(feature.attributes()) > 3:
                layerInfo.append(feature.attributes()[3])
        #return "\n".join(layerInfo)
                #print "**** LayerInfo in getLayerInfo"
                #print layerInfo

                model = QStandardItemModel()
                model.setColumnCount(3)
                model.setHorizontalHeaderLabels(['Layer', 'Type', 'Sort Key', 'Chk ind'])
                item = QStandardItem("\n".join(layerInfo[0]))
                model.appendRow([item, QStandardItem('unknown'), QStandardItem('99999')])
                self.dlg.objectInfo.setModel(model)



    def tableViewselectionChanged(self):
        getLayerInfo()        

    def endButtonClicked(self):
        self.dlg.close()
        pass
        #self.unload()
        #Should close project if we close the dialog but QGIS does not have close project method
        #self.unload()


    def objectInfoClicked(self, index):
        row = index.row()
        model = self.dlg.objectInfo.model()


    def tableViewClicked(self, index):
        row = index.row()
        model = self.dlg.tableView.model()
        valx = model.item(row, 0)
        val = valx.text()
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
        for treeLayer in project.layerTreeRoot().findLayers():
            layer = treeLayer.layer()
            lnam = layer.name()
            if val_wo_ext == lnam:
                self.iface.setActiveLayer(layer)




        layer = self.iface.activeLayer()
        if layer:
            iter = layer.getFeatures()
            feat_count = 0
            attx3 = []

            attb = []

            for feature in iter:

                feat_count += 1;
                # retrieve every feature with its geometry and attributes
                # fetch geometry
                geom = feature.geometry()
                #print "Feature ID %d: " % feature.id()



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

                if feature.attributes:
                    attrs = feature.attributes()
                    if len(attrs) > 2:
                        arear = str(attrs[9]) #9 - column food security
                        gg = [attrs[3],arear]
                        attb.append(gg)

            model = QStandardItemModel()
            model.setColumnCount(3)
            model.setHorizontalHeaderLabels(['Obj', 'Feature', 'Food secure'])


            for itc in attb:
                item = QStandardItem("1")
                model.appendRow([item, QStandardItem(itc[0]),QStandardItem(itc[1])])

            self.dlg.objectInfo.setModel(model)


        else:
            self.dlg.error.setText("Layer not loaded.")

    def saveProjectClicked(self):
        project = QgsProject.instance()
        project.write()
        self.dlg.error.setText("Project saved")

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

        for treeLayer in project.layerTreeRoot().findLayers():
            layer = treeLayer.layer()
            idd = layer.Id()
            print idd
            lnam = layer.name()
            print lnam


        #root = QgsProject.instance().layerTreeRoot()
        #layid = project.layerTreeRoot().findLayer(new_index).Id()
        #lyr3 = root.findLayer(layid).layer()
        #lyr3.id = new_index


    def rubberbandClicked(self):
        layer = self.iface.activeLayer()
        if layer:        
            self.previousMapTool = self.iface.mapCanvas().mapTool()
            self.myMapTool = QgsMapToolEmitPoint(self.iface.mapCanvas())
            self.myMapTool.canvasClicked.connect(self.manageClick)
            self.myRubberBand = QgsRubberBand(self.iface.mapCanvas(), QGis.Polygon)
            color = QColor("green")
            color.setAlpha(50)
            self.myRubberBand.setColor(color)

            self.iface.mapCanvas().xyCoordinates.connect(self.showRBCoordinates)
            self.iface.mapCanvas().setMapTool(self.myMapTool)
    #        r = QgsRubberBand(self.iface.mapCanvas(), True)  # True = a polygon
    #        r.setColor(QColor(0, 0, 255))
    #        r.setWidth(30)
    #        points = [[QgsPoint(0, 0), QgsPoint(200, 200), QgsPoint(450, 76)]]
    #        r.setToGeometry(QgsGeometry.fromPolygon(points), None)
            #pass
        else:
            self.dlg.error.setText("No active layer. Click a layer.")

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
            self.myMapTool.deleteLater()

            #print self.myRubberBand.numberOfVertices()
            geom_rb = self.myRubberBand.asGeometry()
            #print geom_rb.asPolygon()

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
            



            layer = self.iface.activeLayer()
            if layer:
                clp_lay = layer.name()
                iter = layer.getFeatures()
                itrctr = 0
                for feature in iter:
                    geom_feat = feature.geometry()

                    # create layer
                    vl = QgsVectorLayer("Polygon?crs=epsg:4326", "temporary_points", "memory")
                    pr = vl.dataProvider()
                    # Enter editing mode
                    vl.startEditing()
                    # add fields
                    pr.addAttributes( [ QgsField("id", QVariant.Int), QgsField("Description", QVariant.String) ] )
                    # add a feature
                    fet = QgsFeature()
                    fet.setGeometry(geom_feat)
                    fet.setAttributes([itrctr, "Feature"])
                    pr.addFeatures( [ fet ] )
                    # Commit changes
                    vl.commitChanges()
                    itrctr =+ 1

                #print geom_rb.area()
                #print geom_feat.area()


                if geom_rb.intersects(geom_feat):
                    #print "Intersecting"

                    for treeLayer in project.layerTreeRoot().findLayers():                
                        layer_t6 = treeLayer.layer()
                        #if layer_t6.name() == clp_lay:
                        if layer_t6.name() == "feature_valuetype_llg":
                            overlay_layer = layer_t6
                        #if layer.name() == "cut2":
                        if layer_t6.name() == "rubber_band":
                            layer_to_clip = layer_t6
                    #processing.runalg
                    
                    #Clipping intersected area and saving it in-memory. It is layer named "Clipped"
                    #processing.runandload("qgis:clip", overlay_layer, layer_to_clip, "tmp_output.shp")
                    #processing.runandload("qgis:clip", overlay_layer, layer_to_clip, None)
                    processing.runandload("qgis:clip", overlay_layer, layer_to_clip, None)
                    res_lay = QgsMapLayerRegistry.instance().mapLayersByName("Clipped")[0]
                    res_lay.updateExtents()
                    res_feat = res_lay.getFeatures()


                    str2 = ""
                    str3 = ""

                    for f in res_feat:
                        res_geom = f.geometry()
                        #d = QgsDistanceArea()
                        #d.setEllipsoidalMode(True)
                        #m = d.measurePolygon(res_geom.asPolygon()[0])
                        #ar = d.convertMeasurement(m, QGis.Degrees, QGis.Kilometers, True)     
                        #print "New area: ", ar

                        if f.attributes:
                            attry = f.attributes()
                            if len(attry) > 2:
                                str2 = "Spat feat: " + attry[3]
                                str2 = str2.strip()
                                str3 = "Food security: " + str(attry[9]) #9 - column food security
                                str3 = str3.strip()
                        d = QgsDistanceArea()
                        d.setEllipsoidalMode(True)
                        art = res_geom.area()
                        ar = d.convertMeasurement(art, QGis.Degrees, QGis.Kilometers, True)     
                        arx = str(ar[0])
                        ary = "Area: " + arx
                        ary = ary.strip()

                        print ary + " / " + str2 + " / " + str3



                    #print res_lay

                else:
                    pass
                    #print "Not intersecting"

                self.iface.mapCanvas().scene().removeItem(self.myRubberBand)

                for treeLayer in project.layerTreeRoot().findLayers():                
                    layer_f2 = treeLayer.layer()
                    if layer_f2.name() == "rubber_band":
                        QgsMapLayerRegistry.instance().removeMapLayer(layer_f2.id())
                    elif layer_f2.name() == "Clipped":
                        QgsMapLayerRegistry.instance().removeMapLayer(layer_f2.id())


class ModelObjInfo(QStandardItemModel):
    def __init__(self, parent=None):
        QtGui.QStandardItemModel.__init__(self)
        self.setColumnCount(3)

        #self.setHorizontalHeaderLabels(['Object'])
        #self.appendRow([QStandardItem('Looking good')])

    def data(self, index, role):
        if index.isValid():
            return super(ModelObjInfo, self).data(index, QtCore.Qt.DisplayRole)

    #def xappendRow(self):
     #   self.d = QStandardItem('X')
    #    self.d.setTextAlignment(QtCore.Qt.AlignLeft)
    #    self.d.setText = "testing"
    #    self.d.setCheckable(False) 
    #    #self.d.setFlags(QtCore.Qt.ItemIsUserCheckable| QtCore.Qt.ItemIsEnabled)
    #    self.appendRow([self.d, QStandardItem('unknown')])


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
                    self.appendRow([self.d, QStandardItem('unknown'), QStandardItem('99999'), QStandardItem('not checked')])
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
            #print "Index valid"
            if role == QtCore.Qt.CheckStateRole:
            #    print "******* CheckStateRole"
            #    #if role == Qt.DisplayRole:
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


