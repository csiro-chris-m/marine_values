# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ELVIS
                                 A QGIS plugin
 CSIRO Environmental Values Interrogation System plugin
                             -------------------
        begin                : 2016-12-25
        copyright            : (C) 2016 by CSIRO Oceans and Atmosphere Chris Moeseneder
        email                : chris.moeseneder@csiro.au
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load CSIROMarineValues class from file CSIROMarineValues.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .ELVIS import ELVIS
    return ELVIS(iface)
