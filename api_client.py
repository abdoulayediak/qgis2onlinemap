import zipfile
import os
import tempfile
import json
import urllib.parse
from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QUrl, QEventLoop, QIODevice, QT_VERSION
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply, QHttpMultiPart, QHttpPart

# Qt5/Qt6 Compatibility
if QT_VERSION >= 0x060000:
    FORM_DATA_TYPE = QHttpMultiPart.ContentType.FormDataType
    HDR_CONTENT_DISPOSITION = QNetworkRequest.KnownHeaders.ContentDispositionHeader
    HDR_CONTENT_TYPE = QNetworkRequest.KnownHeaders.ContentTypeHeader
else:
    FORM_DATA_TYPE = QHttpMultiPart.FormDataType
    HDR_CONTENT_DISPOSITION = QNetworkRequest.ContentDispositionHeader
    HDR_CONTENT_TYPE = QNetworkRequest.ContentTypeHeader


class ApiClient:
    """
    Client to interact with the Qgis2OnlineMap API using QgsNetworkAccessManager.
    """

    def __init__(self, api_key="", env="Production"):
        self.api_key = api_key
        self.set_env(env)

    def set_env(self, env):
        self.env = env
        if self.env == "Local (Emulator)":
            self.base_url = "http://localhost:5001/qgis2onlinemap/europe-west1/api"
            self.app_url = "http://localhost:5000/app"
        else:
            self.base_url = "https://qgis2onlinemap.com/api"
            self.app_url = "https://qgis2onlinemap.com/app"

    def _execute_request(self, request, data=None, multipart=None):
        """
        Synchronously executes a QNetworkRequest using a local QEventLoop.
        """
        nam = QgsNetworkAccessManager.instance()
        loop = QEventLoop()

        if multipart:
            reply = nam.post(request, multipart)
        elif data:
            reply = nam.post(request, data)
        else:
            reply = nam.get(request)

        reply.finished.connect(loop.quit)
        if hasattr(loop, 'exec'):
            loop.exec()
        else:
            loop.exec_()

        error_code = reply.error()
        if error_code != QNetworkReply.NetworkError.NoError:
            error_msg = reply.errorString()
            try:
                raw_data = reply.readAll().data()
                if raw_data:
                    decoded = raw_data.decode('utf-8')
                    try:
                        server_data = json.loads(decoded)
                        if isinstance(server_data, dict) and 'message' in server_data:
                            error_msg = server_data['message']
                        elif isinstance(server_data, str):
                            error_msg = server_data
                    except json.JSONDecodeError:
                        # Plain text error message from server
                        if len(decoded) < 200:  # Avoid showing massive HTML payloads
                            error_msg = decoded
            except Exception:
                pass
            raise Exception(f"Network error: {error_msg} (QtError: {error_code})")

        return reply.readAll().data().decode('utf-8')

    def get_maps(self):
        """
        Fetches the user's existing maps from the portal.
        """
        if not self.api_key:
            raise Exception("API Key is not set.")

        url = f"{self.base_url}/maps"
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Authorization", f"Bearer {self.api_key}".encode('utf-8'))

        response_text = self._execute_request(request)
        return json.loads(response_text)

    def upload_folder(self, folder_path, map_title="QGIS Upload", map_id=None):
        """
        Zips a selected local folder and performs a POST upload.
        """
        if not self.api_key:
            raise Exception("API Key is not set.")

        zip_path = os.path.join(tempfile.gettempdir(), f"qgis2onlinemap_{map_title.replace(' ', '_')}.zip")

        try:
            # Zip the folder
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, folder_path)
                        zipf.write(abs_path, rel_path)

            return self.upload_zip(zip_path, map_title, map_id)

        finally:
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except Exception:
                    pass

    def upload_zip(self, zip_path, map_title="QGIS Upload", map_id=None):
        """
        Uploads an existing zip file using QHttpMultiPart.
        """
        if not self.api_key:
            raise Exception("API Key is not set.")

        url = f"{self.base_url}/upload"
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Authorization", f"Bearer {self.api_key}".encode('utf-8'))

        if map_id:
            request.setRawHeader(b"x-map-id", map_id.encode('utf-8'))
            encoded_title = urllib.parse.quote(map_title, safe='').encode('utf-8')
            request.setRawHeader(b"x-map-title", encoded_title)

        multi_part = QHttpMultiPart(FORM_DATA_TYPE)

        file_part = QHttpPart()
        safe_title = map_title.replace('"', '_')
        file_part.setHeader(
            HDR_CONTENT_DISPOSITION,
            f'form-data; name="file"; filename="{safe_title}.zip"'
        )
        file_part.setHeader(HDR_CONTENT_TYPE, "application/zip")

        file_device = os.open(zip_path, os.O_RDONLY | os.O_BINARY) if os.name == 'nt' else os.open(zip_path, os.O_RDONLY)
        # Using a file object that QHttpMultiPart can manage
        f = open(zip_path, 'rb')
        file_part.setBody(f.read())
        f.close()

        multi_part.append(file_part)

        response_text = self._execute_request(request, multipart=multi_part)
        # multi_part stay alive until request finished (handled by _execute_request)

        return json.loads(response_text)
