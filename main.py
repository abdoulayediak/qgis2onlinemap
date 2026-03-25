import os

# Compatibility layer for PyQt5/PyQt6
try:
    from PyQt6 import QtWidgets, QtCore, QtGui
    QAction = QtGui.QAction
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui
    QAction = QtWidgets.QAction

from .interface import PluginDialog

class Qgis2OnlineMapPlugin:
    def __init__(self, iface):
        """
        Constructor.
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dialog = None

        import qgis.utils
        qgis.utils.plugins['Qgis2OnlineMap'] = self

    def open_with_path(self, target_folder):
        """
        Public method to be called by other QGIS plugins (like Qgis2threejs).
        """
        if not self.dialog:
            self.dialog = PluginDialog(self.iface, self.iface.mainWindow())
            
        # Check if logged in
        if not self.dialog.api_client.api_key:
            self.dialog.tabs.setCurrentWidget(self.dialog.settings_tab)
            QtWidgets.QMessageBox.warning(self.dialog, "Login Required", "Please login to Qgis2OnlineMap to upload this map.")
        else:
            self.dialog.tabs.setCurrentWidget(self.dialog.upload_tab)
            self.dialog.file_widget.setFilePath(target_folder)
            
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def initGui(self):
        """
        Create the menu entries and toolbar icons inside the QGIS GUI.
        """
        try:
            icon_path = os.path.join(self.plugin_dir, 'icon.png')
            if os.path.exists(icon_path):
                icon = QtGui.QIcon(icon_path)
                self.action = QAction(icon, "Qgis2OnlineMap", self.iface.mainWindow())
            else:
                self.action = QAction("Qgis2OnlineMap", self.iface.mainWindow())
        except Exception:
            self.action = QAction("Qgis2OnlineMap", self.iface.mainWindow())
            
        self.action.setObjectName("Qgis2OnlineMapAction")
        self.action.setToolTip("Qgis2OnlineMap - Publish Maps Online")
        self.action.triggered.connect(self.run)
        
        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Qgis2OnlineMap", self.action)

    def unload(self):
        """
        Removes the plugin menu item and icon from QGIS GUI.
        """
        if self.action:
            self.iface.removePluginMenu("&Qgis2OnlineMap", self.action)
            self.iface.removeToolBarIcon(self.action)

    def run(self):
        """
        Run method that performs all the real work.
        """
        # Create the dialog (after translation) and keep reference
        if not self.dialog:
            self.dialog = PluginDialog(self.iface, self.iface.mainWindow())
        
        # show the dialog
        self.dialog.show()
        # Bring it to front
        self.dialog.raise_()
        self.dialog.activateWindow()
