import os
import threading
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from qgis.core import QgsSettings
from qgis.gui import QgsFileWidget

from .api_client import ApiClient


class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        if 'token' in params:
            token = params['token'][0]
            self.server.token = token
            html = "<html><body><h1>Login successful!</h1><p>You can now close this window and return to QGIS.</p><script>window.close();</script></body></html>"
            self.wfile.write(html.encode('utf-8'))
        else:
            html = "<html><body><h1>Login failed or no token provided.</h1><p>Please try again.</p></body></html>"
            self.wfile.write(html.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # Suppress console logging

# Compatibility layer for PyQt5/PyQt6
try:
    from qgis.PyQt import QtWidgets, QtCore, QtGui
    if QtCore.QT_VERSION >= 0x060000:
        # Qt 6 scoped enums
        USER_ROLE = QtCore.Qt.ItemDataRole.UserRole
        ECHO_PASSWORD = QtWidgets.QLineEdit.EchoMode.Password
        WAIT_CURSOR = QtCore.Qt.CursorShape.WaitCursor
        HEADER_STRETCH = QtWidgets.QHeaderView.ResizeMode.Stretch
        HEADER_RESIZE_TO_CONTENTS = QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        HEADER_INTERACTIVE = QtWidgets.QHeaderView.ResizeMode.Interactive
        ALIGN_CENTER = QtCore.Qt.AlignmentFlag.AlignCenter
        POINTING_HAND_CURSOR = QtCore.Qt.CursorShape.PointingHandCursor
        WINDOW_MODAL = QtCore.Qt.WindowModality.WindowModal
        SIZE_PREFERRED = QtWidgets.QSizePolicy.Policy.Preferred
        SIZE_FIXED = QtWidgets.QSizePolicy.Policy.Fixed
        SELECT_ROWS = QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        NO_EDIT_TRIGGERS = QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        MSG_YES = QtWidgets.QMessageBox.StandardButton.Yes
        MSG_NO = QtWidgets.QMessageBox.StandardButton.No
    else:
        # Qt 5 legacy enums
        USER_ROLE = QtCore.Qt.UserRole
        ECHO_PASSWORD = QtWidgets.QLineEdit.Password
        WAIT_CURSOR = QtCore.Qt.WaitCursor
        HEADER_STRETCH = QtWidgets.QHeaderView.Stretch
        HEADER_RESIZE_TO_CONTENTS = QtWidgets.QHeaderView.ResizeToContents
        HEADER_INTERACTIVE = QtWidgets.QHeaderView.Interactive
        ALIGN_CENTER = QtCore.Qt.AlignCenter
        POINTING_HAND_CURSOR = QtCore.Qt.PointingHandCursor
        WINDOW_MODAL = QtCore.Qt.WindowModal
        SIZE_PREFERRED = QtWidgets.QSizePolicy.Preferred
        SIZE_FIXED = QtWidgets.QSizePolicy.Fixed
        SELECT_ROWS = QtWidgets.QAbstractItemView.SelectRows
        NO_EDIT_TRIGGERS = QtWidgets.QAbstractItemView.NoEditTriggers
        MSG_YES = QtWidgets.QMessageBox.Yes
        MSG_NO = QtWidgets.QMessageBox.No
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui
    # Fallback to standard names if needed
    pass


class DragDropUploadWidget(QtWidgets.QWidget):
    fileDropped = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(DragDropUploadWidget, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                # Get local absolute path
                file_path = urls[0].toLocalFile()
                self.fileDropped.emit(file_path)
            event.acceptProposedAction()
        else:
            event.ignore()


class NotLoggedInWidget(QtWidgets.QWidget):
    def __init__(self, callback, parent=None):
        super(NotLoggedInWidget, self).__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(30)
        
        self.img_label = QtWidgets.QLabel()
        
        icon_dir = os.path.dirname(__file__)
        gif_path = os.path.join(icon_dir, 'icon.gif')
        png_path = os.path.join(icon_dir, 'icon.png')
        
        if os.path.exists(gif_path):
            # Scale down slightly to fit well in the 819x513 dialog viewport
            self.img_label.setFixedSize(500, 265) 
            movie = QtGui.QMovie(gif_path)
            movie.setScaledSize(QtCore.QSize(500, 265))
            self.img_label.setMovie(movie)
            movie.start()
            # Store a reference so the movie is not garbage collected
            self.img_label._movie = movie
        elif os.path.exists(png_path):
            self.img_label.setFixedSize(120, 120)
            pixmap = QtGui.QPixmap(png_path)
            self.img_label.setPixmap(pixmap)
            self.img_label.setScaledContents(True)
            
        self.img_label.setAlignment(ALIGN_CENTER)
        
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(10)
        
        self.msg_title = QtWidgets.QLabel("Start Publishing in seconds")
        self.msg_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0f172a;")
        
        self.msg_text = QtWidgets.QLabel("Create a free account to unlock instant cloud hosting for your QGIS exports.")
        self.msg_text.setWordWrap(True)
        self.msg_text.setStyleSheet("font-size: 14px; color: #475569;")
        
        self.btn_dashboard = QtWidgets.QPushButton("Get Started")
        self.btn_dashboard.setStyleSheet("background-color: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: bold;")
        self.btn_dashboard.setCursor(POINTING_HAND_CURSOR)
        self.btn_dashboard.clicked.connect(callback)
        
        text_layout.addStretch()
        text_layout.addWidget(self.msg_title)
        text_layout.addWidget(self.msg_text)
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addWidget(self.btn_dashboard)
        btn_layout.addStretch()
        
        text_layout.addLayout(btn_layout)
        text_layout.addStretch()
        
        layout.addStretch()
        layout.addWidget(self.img_label)
        layout.addLayout(text_layout)
        layout.addStretch()


class PluginDialog(QtWidgets.QDialog):
    LOGIN_TIMEOUT_SECONDS = 60  # 1-minute timeout for browser login

    def __init__(self, iface, parent=None):
        super(PluginDialog, self).__init__(parent)
        self.iface = iface
        self.api_client = ApiClient()
        self.httpd = None
        self.server_thread = None
        self._login_elapsed = 0
        self._last_maps = []
        self.login_timer = QtCore.QTimer(self)
        self.login_timer.timeout.connect(self.check_login_status)
        
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """
        Create the UI programmatically.
        """
        self.setWindowTitle("Qgis2OnlineMap - Publish Maps Online")
        self.resize(819, 513)
        
        # --- Modern Styling (Now optional) ---
        # self.apply_custom_styling()
        
        self.layout = QtWidgets.QVBoxLayout(self)
        
        self.tabs = QtWidgets.QTabWidget()
        self.layout.addWidget(self.tabs)
        
        # --- Tab 1: My Maps ---
        self.maps_tab = QtWidgets.QWidget()
        self.maps_layout = QtWidgets.QVBoxLayout(self.maps_tab)
        
        self.maps_stack = QtWidgets.QStackedWidget()
        self.maps_layout.addWidget(self.maps_stack)
        
        self.maps_content = QtWidgets.QWidget()
        self.maps_content_layout = QtWidgets.QVBoxLayout(self.maps_content)
        self.maps_content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table_widget = QtWidgets.QTableWidget(0, 4)
        self.table_widget.setHorizontalHeaderLabels(["Map Name", "Updated", "Online", "Actions"])
        self.table_widget.horizontalHeader().setStretchLastSection(False)
        self.table_widget.horizontalHeader().setSectionResizeMode(0, HEADER_STRETCH)
        self.table_widget.horizontalHeader().setSectionResizeMode(1, HEADER_RESIZE_TO_CONTENTS)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, HEADER_RESIZE_TO_CONTENTS)
        self.table_widget.verticalHeader().setDefaultSectionSize(40)
        self.table_widget.setSelectionBehavior(SELECT_ROWS)
        self.table_widget.setEditTriggers(NO_EDIT_TRIGGERS)
        self.table_widget.setSortingEnabled(True)
        self.maps_content_layout.addWidget(self.table_widget)
        
        self.btn_layout = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Refresh List")
        
        self.btn_manage = QtWidgets.QPushButton("Manage on Web")
        self.btn_manage.setObjectName("ViewBtn")
        
        self.btn_layout.addWidget(self.btn_refresh)
        self.btn_layout.addWidget(self.btn_manage)
        
        self.maps_content_layout.addLayout(self.btn_layout)
        
        self.maps_not_logged_in = NotLoggedInWidget(self.start_login)
        self.maps_stack.addWidget(self.maps_not_logged_in)
        self.maps_stack.addWidget(self.maps_content)
        
        self.tabs.addTab(self.maps_tab, "Projects")
        
        # --- Tab: Publish ---
        self.upload_tab = DragDropUploadWidget()
        self.upload_tab.fileDropped.connect(self._handle_file_drop)
        self.upload_layout = QtWidgets.QVBoxLayout(self.upload_tab)
        
        self.upload_stack = QtWidgets.QStackedWidget()
        self.upload_layout.addWidget(self.upload_stack)
        
        self.upload_content = QtWidgets.QWidget()
        self.upload_content_layout = QtWidgets.QVBoxLayout(self.upload_content)
        self.upload_content_layout.setContentsMargins(0, 0, 0, 0)
        
        self.upload_form = QtWidgets.QFormLayout()
        
        self.upload_type = QtWidgets.QComboBox()
        self.upload_type.addItems(["Folder", "Zip Archive"])
        self.upload_form.addRow("Source Type:", self.upload_type)
        
        self.file_widget = QgsFileWidget()
        self.file_widget.setStorageMode(QgsFileWidget.GetDirectory)
        self.upload_form.addRow("Map files:", self.file_widget)
        
        self.map_name_edit = QtWidgets.QLineEdit()
        self.map_name_edit.setPlaceholderText("Enter Map Title")
        self.upload_form.addRow("Map Title:", self.map_name_edit)
        
        self.upload_content_layout.addLayout(self.upload_form)
        self.upload_content_layout.addSpacing(16)
        
        # --- Drop Area ---
        self.drop_area_frame = QtWidgets.QFrame()
        self.drop_area_frame.setObjectName("DropArea")
        self.drop_area_frame.setMinimumHeight(120)
        self.drop_area_layout = QtWidgets.QVBoxLayout(self.drop_area_frame)
        self.drop_area_layout.setContentsMargins(20, 20, 20, 20)
        
        self.upload_msg = QtWidgets.QLabel("📂 Drag & Drop a folder or .zip file here\nor use the controls above to select your map.")
        self.upload_msg.setAlignment(ALIGN_CENTER)
        self.upload_msg.setWordWrap(True)
        self.upload_msg.setStyleSheet("font-size: 14px; color: #64748b; font-weight: 500;")
        
        self.drop_area_layout.addWidget(self.upload_msg)
        self.upload_content_layout.addWidget(self.drop_area_frame)
        
        self.upload_content_layout.addStretch()
        
        # --- Action Buttons (Right aligned) ---
        self.action_btn_layout = QtWidgets.QHBoxLayout()
        self.action_btn_layout.addStretch()
        
        self.btn_do_upload = QtWidgets.QPushButton("Publish")
        self.btn_do_upload.setObjectName("UploadBtn")
        self.btn_do_upload.setFixedSize(110, 36)
        self.action_btn_layout.addWidget(self.btn_do_upload)
        
        self.upload_content_layout.addLayout(self.action_btn_layout)
        
        self.upload_not_logged_in = NotLoggedInWidget(self.start_login)
        self.upload_stack.addWidget(self.upload_not_logged_in)
        self.upload_stack.addWidget(self.upload_content)

        
        self.tabs.addTab(self.upload_tab, "Publish Map")
        
        # --- Tab: Settings ---
        self.settings_tab = QtWidgets.QWidget()
        self.settings_layout = QtWidgets.QVBoxLayout(self.settings_tab)
        self.settings_layout.setSpacing(12)

        # ── Account group ──────────────────────────────────────────
        account_group = QtWidgets.QGroupBox("Account")
        account_layout = QtWidgets.QVBoxLayout(account_group)
        account_layout.setSpacing(8)

        self.lbl_status = QtWidgets.QLabel("🔴 Status: Not Logged In")

        auth_btn_layout = QtWidgets.QHBoxLayout()
        self.btn_login = QtWidgets.QPushButton("Login via Web Browser")
        self.btn_login.setObjectName("LoginBtn")
        self.btn_login.setSizePolicy(SIZE_PREFERRED, SIZE_FIXED)

        self.btn_logout = QtWidgets.QPushButton("Logout")
        self.btn_logout.setObjectName("LogoutBtn")
        self.btn_logout.setStyleSheet("color: #ef4444; font-weight: bold;")
        self.btn_logout.setSizePolicy(SIZE_PREFERRED, SIZE_FIXED)

        auth_btn_layout.addWidget(self.btn_login)
        auth_btn_layout.addWidget(self.btn_logout)
        auth_btn_layout.addStretch()

        account_layout.addWidget(self.lbl_status)
        account_layout.addLayout(auth_btn_layout)
        self.settings_layout.addWidget(account_group)

        # ── Appearance group ───────────────────────────────────────
        appearance_group = QtWidgets.QGroupBox("Appearance")
        appearance_layout = QtWidgets.QVBoxLayout(appearance_group)
        self.chk_theme = QtWidgets.QCheckBox("Use custom theme")
        self.chk_theme.setChecked(False)
        appearance_layout.addWidget(self.chk_theme)
        self.settings_layout.addWidget(appearance_group)

        # ── Developer group (hidden unless env var set) ────────────
        self.dev_group = QtWidgets.QGroupBox("Developer")
        dev_layout = QtWidgets.QFormLayout(self.dev_group)
        self.lbl_env = QtWidgets.QLabel("Environment:")
        self.cmb_env = QtWidgets.QComboBox()
        self.cmb_env.addItems(["Production", "Local (Emulator)"])
        self.cmb_env.currentTextChanged.connect(self.env_changed)
        dev_layout.addRow(self.lbl_env, self.cmb_env)
        
        if os.environ.get('QGIS2ONLINEMAP_DEV') == '1':
            self.settings_layout.addWidget(self.dev_group)
        else:
            self.dev_group.hide()
            self.dev_group.setParent(None)

        self.settings_layout.addStretch()
        self.tabs.addTab(self.settings_tab, "Settings")
        
        # --- Connections ---
        self.btn_refresh.clicked.connect(self.refresh_maps)
        self.btn_manage.clicked.connect(self.manage_on_web)
        self.btn_do_upload.clicked.connect(self.prepare_upload)
        self.upload_type.currentTextChanged.connect(self._toggle_upload_type)
        self.file_widget.fileChanged.connect(self._auto_populate_title)
        self.btn_login.clicked.connect(self.start_login)
        self.btn_logout.clicked.connect(self.logout)
        self.chk_theme.toggled.connect(self.toggle_theme)

    def apply_custom_styling(self):
        """
        Applies a modern, custom CSS stylesheet to the dialog.
        """
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
            }
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                background: white;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                color: #64748b;
                font-weight: 500;
                font-size: 13px;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #3b82f6;
                color: #0f172a;
                font-weight: bold;
            }
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                background: white;
                font-size: 14px;
                color: #1e293b;
                gridline-color: #f1f5f9;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f8fafc;
            }
            QTableWidget::item:selected {
                background-color: #eff6ff;
                color: #1d4ed8;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 4px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
                font-weight: bold;
                color: #475569;
            }
            QPushButton {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                color: #334155;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
            }
            #DropArea {
                border: 2px dashed #cbd5e1;
                border-radius: 12px;
                background-color: #f1f5f9;
            }
            #DropArea:hover {
                background-color: #f8fafc;
                border-color: #3b82f6;
            }
            #UploadBtn {
                background-color: #10b981;
                color: white;
                border: none;
                font-weight: bold;
            }
            #UploadBtn:hover {
                background-color: #059669;
            }
            #LoginBtn {
                background-color: #3b82f6;
                color: white;
                border: none;
                font-weight: bold;
                padding: 10px;
                margin-top: 10px;
            }
            #LoginBtn:hover {
                background-color: #2563eb;
            }
            #ViewBtn {
                background-color: #f59e0b;
                color: white;
                border: none;
                font-weight: bold;
            }
            #ViewBtn:hover {
                background-color: #d97706;
            }
            QLabel {
                color: #475569;
                font-size: 13px;
            }
        """)

    def reset_to_native_styling(self):
        """
        Clears the stylesheet to return to native QGIS/OS look.
        """
        self.setStyleSheet("")

    def toggle_theme(self, checked):
        if checked:
            self.apply_custom_styling()
        else:
            self.reset_to_native_styling()
        self.save_settings()
        if hasattr(self, '_last_maps') and self._last_maps:
            self._populate_table(self._last_maps)

    def load_settings(self):
        """
        Load API Key from QGIS persistent settings.
        """
        settings = QgsSettings()
        settings.beginGroup("Qgis2OnlineMapPlugin")
        api_key = settings.value("api_key", "")
        env = settings.value("env", "Production")
        use_theme = settings.value("use_custom_theme", False, type=bool)
        settings.endGroup()
        
        self.cmb_env.setCurrentText(env)
        self.api_client.set_env(env)
        
        # We need to ensure theme logic checks and unchecks safely
        if hasattr(self, 'chk_theme'):
            self.chk_theme.setChecked(use_theme)
        if use_theme:
            self.apply_custom_styling()
        else:
            self.reset_to_native_styling()
        
        if api_key:
            self.api_client.api_key = api_key
            
        self.update_login_ui()

    def update_login_ui(self, revoked=False):
        if self.api_client.api_key and not revoked:
            if hasattr(self, 'maps_stack'):
                self.maps_stack.setCurrentWidget(self.maps_content)
            if hasattr(self, 'upload_stack'):
                self.upload_stack.setCurrentWidget(self.upload_content)
                
            self.lbl_status.setText("🟢 Status: Logged In")
            self.lbl_status.setStyleSheet("color: #16a34a; font-weight: bold;")
            self.btn_login.setText("Reconnect / Refresh Login")
            self.btn_logout.setVisible(True)
            self.refresh_maps()
        else:
            if hasattr(self, 'maps_stack'):
                self.maps_stack.setCurrentWidget(self.maps_not_logged_in)
            if hasattr(self, 'upload_stack'):
                self.upload_stack.setCurrentWidget(self.upload_not_logged_in)

            if revoked and self.api_client.api_key:
                self.lbl_status.setText("⚪ Status: Revoked (Check Web Dashboard)")
                self.lbl_status.setStyleSheet("color: #64748b; font-weight: bold;")
                self.btn_login.setText("Re-authenticate")
                self.btn_logout.setVisible(True)
            else:
                self.lbl_status.setText("🔴 Status: Not Logged In")
                self.lbl_status.setStyleSheet("color: #dc2626; font-weight: bold;")
                self.btn_login.setText("Login via Web Dashboard")
                self.btn_logout.setVisible(False)
                self.table_widget.setRowCount(0)

    def logout(self):
        self.api_client.api_key = ""
        self.save_settings()
        self.update_login_ui()
        QtWidgets.QMessageBox.information(self, "Logout", "You have successfully logged out from the plugin.")

    def env_changed(self, env):
        self.api_client.set_env(env)
        self.save_settings()

    def save_settings(self):
        """
        Store API Key securely in QgsSettings.
        """
        api_key = self.api_client.api_key
        env = self.cmb_env.currentText()
        settings = QgsSettings()
        settings.beginGroup("Qgis2OnlineMapPlugin")
        settings.setValue("api_key", api_key)
        settings.setValue("env", env)
        settings.setValue("use_custom_theme", self.chk_theme.isChecked())
        settings.endGroup()
        
        self.api_client.api_key = api_key
        self.api_client.set_env(env)

    def start_login(self):
        """
        Starts a local auth server and opens the browser.
        """
        try:
            if self.httpd:
                self.httpd.shutdown()
                self.httpd.server_close()
                self.httpd = None

            self.httpd = HTTPServer(('localhost', 0), OAuthHandler)
            self.httpd.token = None
            port = self.httpd.server_port

            self.server_thread = threading.Thread(target=self.httpd.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()

            login_url = f"{self.api_client.app_url}?redirect=http://localhost:{port}/"
            webbrowser.open(login_url)

            self._login_elapsed = 0
            self.btn_login.setText("Waiting for authentication… (0s)")
            self.btn_login.setEnabled(False)
            self.login_timer.start(1000)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to start local server:\n{e}")

    def _cancel_login(self):
        """Stops the login timer and re-enables the button."""
        self.login_timer.stop()
        self.btn_login.setEnabled(True)
        self.btn_login.setText("Login via Web Browser")
        if self.httpd:
            # Shutdown and close server safely
            def cleanup(server):
                server.shutdown()
                server.server_close()
            threading.Thread(target=cleanup, args=(self.httpd,)).start()
            self.httpd = None

    def check_login_status(self):
        """
        Periodically checks if the server received a token, with a 2-minute timeout.
        """
        self._login_elapsed += 1

        # Update button label with elapsed time
        remaining = self.LOGIN_TIMEOUT_SECONDS - self._login_elapsed
        self.btn_login.setText(f"Waiting for authentication… ({self._login_elapsed}s)")

        # Timeout reached
        if self._login_elapsed >= self.LOGIN_TIMEOUT_SECONDS:
            self._cancel_login()
            QtWidgets.QMessageBox.warning(
                self, "Login Timeout",
                f"No response was received from the browser after {self.LOGIN_TIMEOUT_SECONDS} seconds.\n"
                "Please try again."
            )
            return

        if self.httpd and getattr(self.httpd, 'token', None):
            self.login_timer.stop()
            self.api_client.api_key = self.httpd.token
            self.save_settings()

            self.update_login_ui()
            self.btn_login.setEnabled(True)
            QtWidgets.QMessageBox.information(self, "Login Success", "Successfully logged in via web!")

            # Shutdown server in a thread to not block UI
            threading.Thread(target=self.httpd.shutdown).start()

    def refresh_maps(self):
        """
        Fetch user's maps with a background thread.
        """
        if not self.api_client.api_key:
            return

        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("⌛ Refreshing...")
        
        # Clear table and show a loading message in the first row
        self.table_widget.setSortingEnabled(False)
        self.table_widget.setRowCount(1)
        loading_item = QtWidgets.QTableWidgetItem("Loading maps...")
        loading_item.setForeground(QtGui.QColor("#64748b"))
        self.table_widget.setItem(0, 0, loading_item)
        for col in range(1, 4):
            self.table_widget.setItem(0, col, QtWidgets.QTableWidgetItem(""))

        self.fetch_thread = FetchMapsThread(self.api_client)
        self.fetch_thread.finished.connect(self._on_fetch_finished)
        self.fetch_thread.error.connect(self._on_fetch_error)
        self.fetch_thread.start()

    def _on_fetch_finished(self, maps):
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("Refresh List")
        self._last_maps = maps
        self._populate_table(maps)

    def _populate_table(self, maps):
        is_themed = self.chk_theme.isChecked()
        self.table_widget.verticalHeader().setDefaultSectionSize(48 if is_themed else 40)
        self.table_widget.setRowCount(0)
        
        if not maps:
            return
                
        try:
            self.table_widget.setRowCount(len(maps))
            for row, map_data in enumerate(maps):
                title = map_data.get('title', 'Untitled Map')
                is_online = map_data.get('isActive', True)

                # Format date as dd/mm/yyyy hh:mm
                updated_at_raw = map_data.get('updatedAt', '')
                updated_at = ''
                if updated_at_raw:
                    try:
                        # Parse ISO 8601 (e.g. 2024-03-19T17:31:00.123Z)
                        dt_str = updated_at_raw.replace('Z', '+00:00')
                        # Python 3.7+ fromisoformat doesn't handle the trailing +00:00 on all builds
                        # strip timezone for simple display
                        dt_str_clean = updated_at_raw[:19]  # "2024-03-19T17:31:00"
                        from datetime import datetime
                        dt = datetime.strptime(dt_str_clean, '%Y-%m-%dT%H:%M:%S')
                        updated_at = dt.strftime('%d/%m/%Y %H:%M')
                    except Exception:
                        updated_at = updated_at_raw[:10]  # fallback to date only

                item_title = QtWidgets.QTableWidgetItem(title)
                item_title.setData(USER_ROLE, map_data)

                item_date = QtWidgets.QTableWidgetItem(updated_at)

                # Online status cell — centred circle emoji
                status_label = QtWidgets.QLabel('🟢' if is_online else '🔴')
                status_label.setAlignment(ALIGN_CENTER)
                status_widget = QtWidgets.QWidget()
                status_layout = QtWidgets.QHBoxLayout(status_widget)
                status_layout.setContentsMargins(0, 0, 0, 0)
                status_layout.addWidget(status_label)

                action_widget = QtWidgets.QWidget()
                action_layout = QtWidgets.QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                action_layout.setSpacing(4)
                
                is_themed = self.chk_theme.isChecked()
                
                btn_view = QtWidgets.QPushButton("👁️" if is_themed else "View")
                btn_view.setToolTip("View on Web")
                if is_themed:
                    btn_view.setFixedSize(56, 30)
                else:
                    btn_view.setMinimumHeight(27)
                btn_view.setStyleSheet("background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 12px;")
                btn_view.setCursor(POINTING_HAND_CURSOR)
                btn_view.clicked.connect(lambda checked, m=map_data: self.view_on_web(m))
                
                btn_copy = QtWidgets.QPushButton("🔗" if is_themed else "Copy")
                btn_copy.setToolTip("Copy Viewer Link")
                if is_themed:
                    btn_copy.setFixedSize(56, 30)
                else:
                    btn_copy.setMinimumHeight(27)
                btn_copy.setStyleSheet("background-color: #f1f5f9; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 12px;")
                btn_copy.setCursor(POINTING_HAND_CURSOR)
                btn_copy.clicked.connect(lambda checked, m=map_data: self.copy_link(m))
                
                btn_update = QtWidgets.QPushButton("🔄" if is_themed else "Update")
                btn_update.setToolTip("Update Map")
                if is_themed:
                    btn_update.setFixedSize(56, 30)
                else:
                    btn_update.setMinimumHeight(27)
                btn_update.setStyleSheet("background-color: #8b5cf6; color: white; border: 1px solid #7c3aed; border-radius: 4px; font-size: 12px;")
                btn_update.setCursor(POINTING_HAND_CURSOR)
                
                update_menu = QtWidgets.QMenu()
                action_update_folder = update_menu.addAction("📂 Local Folder...")
                action_update_zip = update_menu.addAction("📦 Zip Archive...")
                btn_update.setMenu(update_menu)
                
                action_update_folder.triggered.connect(lambda checked, m=map_data: self.update_folder(m))
                action_update_zip.triggered.connect(lambda checked, m=map_data: self.update_zip(m))
                
                action_layout.addWidget(btn_view)
                action_layout.addWidget(btn_copy)
                action_layout.addWidget(btn_update)

                self.table_widget.setItem(row, 0, item_title)
                self.table_widget.setItem(row, 1, item_date)
                self.table_widget.setCellWidget(row, 2, status_widget)
                self.table_widget.setCellWidget(row, 3, action_widget)
            self.table_widget.setSortingEnabled(True)
            self.table_widget.horizontalHeader().setSectionResizeMode(1, HEADER_RESIZE_TO_CONTENTS)
            self.table_widget.horizontalHeader().setSectionResizeMode(2, HEADER_RESIZE_TO_CONTENTS)
            
            if is_themed:
                self.table_widget.horizontalHeader().setSectionResizeMode(3, HEADER_RESIZE_TO_CONTENTS)
            else:
                self.table_widget.horizontalHeader().setSectionResizeMode(3, HEADER_INTERACTIVE)
                self.table_widget.setColumnWidth(3, 220)
        except Exception as e:
            print(f"Error populating table: {e}")

    def _on_fetch_error(self, err_msg):
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("Refresh List")
        self.table_widget.setRowCount(0)
        
        # If the error looks like an auth failure, force logout
        if "401" in err_msg or "403" in err_msg or "Unauthorized" in err_msg:
            if "Revoked" in err_msg:
                self.update_login_ui(revoked=True)
                QtWidgets.QMessageBox.warning(self, "Access Revoked", "Your QGIS access has been revoked.\n\nPlease go to the 'Account' tab in your Web Dashboard to re-enable your key, then log in again.")
            else:
                self.api_client.api_key = ""
                self.save_settings()
                self.update_login_ui()
                QtWidgets.QMessageBox.warning(self, "Session Expired", "Your session has expired or is invalid. Please log in again.")
        else:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to fetch maps:\n{err_msg}")

    def copy_link(self, map_data=None):
        if not map_data:
            map_data = self._get_selected_map()
        if not map_data: return
        baseUrl = self.api_client.app_url.replace('/app', '') 
        viewer_url = f"{baseUrl}/v/{map_data['id']}"
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(viewer_url)
        QtWidgets.QMessageBox.information(self, "Link Copied", "Viewer map link copied to clipboard!")

    def view_on_web(self, map_data=None):
        """
        Opens the selected map URL in the system's default browser.
        """
        if not map_data:
            map_data = self._get_selected_map()

        if not map_data: return

        if map_data and isinstance(map_data, dict) and 'id' in map_data:
            baseUrl = self.api_client.app_url.replace('/app', '')
            viewer_url = f"{baseUrl}/v/{map_data['id']}"
            import webbrowser
            webbrowser.open(viewer_url)
        else:
            QtWidgets.QMessageBox.warning(self, "Warning", "No URL found for the selected map.")

    def manage_on_web(self):
        """ Opens the dashboard in the browser """
        import webbrowser
        webbrowser.open(self.api_client.app_url)

    def _get_selected_map(self):
        current_row = self.table_widget.currentRow()
        if current_row < 0:
            QtWidgets.QMessageBox.warning(self, "Warning", "Please select a map from the list first.")
            return None
        return self.table_widget.item(current_row, 0).data(USER_ROLE)

    def _perform_upload(self, path, is_zip, default_name, map_id=None):
        # For updates (map_id provided): just reuse the existing title without prompting.
        # For new uploads via the Upload tab: title already validated by prepare_upload().
        # For new uploads triggered from other code paths: fall back to a dialog.
        title = default_name
        if not map_id and not title:
            title, ok = QtWidgets.QInputDialog.getText(
                self, "Map Title", "Enter a name for this map:", text=""
            )
            if not ok or not title.strip():
                return

        self.progress_dialog = QtWidgets.QProgressDialog("Communicating with server, please wait...", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("Please Wait")
        self.progress_dialog.setWindowModality(WINDOW_MODAL)
        self.progress_dialog.setCancelButton(None) # Remove cancel button to make it a true modal loader
        self.progress_dialog.show()

        self.upload_thread = UploadThread(self.api_client, path, is_zip, title.strip(), map_id)
        self.upload_thread.finished.connect(self._on_upload_finished)
        self.upload_thread.error.connect(self._on_upload_error)
        self.upload_thread.start()

    def _on_upload_finished(self, result):
        self.progress_dialog.close()
        
        # Reset upload fields
        self.map_name_edit.clear()
        self.file_widget.setFilePath("")
        
        map_id = result.get('mapId') if isinstance(result, dict) else None
        reply = QtWidgets.QMessageBox.question(
            self, "Upload Success",
            "Map uploaded/updated successfully.\n\nOpen in browser now?",
            MSG_YES | MSG_NO
        )
        self.refresh_maps()
        if reply == MSG_YES and map_id:
            self.view_on_web({'id': map_id})
        
    def _on_upload_error(self, err_msg):
        self.progress_dialog.close()
        QtWidgets.QMessageBox.critical(self, "Upload Failed", f"Upload failed:\n{err_msg}")

    def _handle_file_drop(self, file_path):
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                self.upload_type.setCurrentText("Folder")
                self.file_widget.setFilePath(file_path)
                # fileChanged signal may not fire when set programmatically, so call directly
                self._auto_populate_title(file_path)
            elif file_path.lower().endswith(".zip"):
                self.upload_type.setCurrentText("Zip Archive")
                self.file_widget.setFilePath(file_path)
                self._auto_populate_title(file_path)
            else:
                QtWidgets.QMessageBox.warning(self, "Invalid Format", "Please drop a folder or a .zip file directly into the plugin window.")

    def _toggle_upload_type(self, text):
        if text == "Folder":
            self.file_widget.setStorageMode(QgsFileWidget.GetDirectory)
            self.file_widget.setFilter("")
        else:
            self.file_widget.setStorageMode(QgsFileWidget.GetFile)
            self.file_widget.setFilter("Zip files (*.zip)")
            
    def _auto_populate_title(self, path):
        if not path: return
        
        if self.upload_type.currentText() == "Folder":
            name = os.path.basename(os.path.normpath(path))
        else:
            name = os.path.splitext(os.path.basename(path))[0]
            
        self.map_name_edit.setText(name)

    def prepare_upload(self):
        path = self.file_widget.filePath()
        if not path or not os.path.exists(path):
            QtWidgets.QMessageBox.warning(self, "Invalid Path", "Please select a valid folder or file to upload.")
            return
            
        title = self.map_name_edit.text().strip()
        if not title:
            QtWidgets.QMessageBox.warning(self, "Missing Title", "Please provide a name for this map.")
            return
            
        is_zip = (self.upload_type.currentText() == "Zip Archive")
        self._perform_upload(path, is_zip, title)

    def update_folder(self, map_data=None):
        if not map_data:
            map_data = self._get_selected_map()
        if not map_data: return
        
        folder_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Folder to Replace Map")
        if not folder_path: return
        
        # Automatically use the folder name as the new title
        title = os.path.basename(os.path.normpath(folder_path))
        self._perform_upload(folder_path, False, title, map_data.get('id'))

    def update_zip(self, map_data=None):
        if not map_data:
            map_data = self._get_selected_map()
        if not map_data: return
        
        zip_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Zip File to Replace Map", "", "Zip Files (*.zip)")
        if not zip_path: return
        
        # Automatically use the ZIP filename as the new title
        title = os.path.splitext(os.path.basename(zip_path))[0]
        self._perform_upload(zip_path, True, title, map_data.get('id'))

class FetchMapsThread(QtCore.QThread):
    finished = QtCore.pyqtSignal(list)
    error = QtCore.pyqtSignal(str)

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    def run(self):
        try:
            maps = self.api_client.get_maps()
            # api_client.get_maps() returns a list of dicts
            self.finished.emit(maps)
        except Exception as e:
            self.error.emit(str(e))

class UploadThread(QtCore.QThread):
    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)

    def __init__(self, api_client, path, is_zip, title, map_id=None):
        super().__init__()
        self.api_client = api_client
        self.path = path
        self.is_zip = is_zip
        self.title = title
        self.map_id = map_id

    def run(self):
        try:
            if self.is_zip:
                result = self.api_client.upload_zip(self.path, self.title, self.map_id)
            else:
                result = self.api_client.upload_folder(self.path, self.title, self.map_id)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
