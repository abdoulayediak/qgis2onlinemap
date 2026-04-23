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
    HDR_STATUS_CODE = QNetworkRequest.Attribute.HttpStatusCodeAttribute
    NET_NO_ERROR = QNetworkReply.NetworkError.NoError
else:
    FORM_DATA_TYPE = QHttpMultiPart.FormDataType
    HDR_CONTENT_DISPOSITION = QNetworkRequest.ContentDispositionHeader
    HDR_CONTENT_TYPE = QNetworkRequest.ContentTypeHeader
    HDR_STATUS_CODE = QNetworkRequest.HttpStatusCodeAttribute
    NET_NO_ERROR = QNetworkReply.NoError


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

        # Ensure we follow redirects (crucial for Firebase Hosting rewrites)
        if hasattr(QNetworkRequest, 'FollowRedirectsAttribute'):
            request.setAttribute(QNetworkRequest.FollowRedirectsAttribute, True)
        else:
            try:
                if hasattr(QNetworkRequest, 'Attribute'):
                    # Qt 6 scoped enums
                    request.setAttribute(
                        QNetworkRequest.Attribute.RedirectPolicyAttribute,
                        QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy
                    )
                else:
                    # Qt 5 scoped enums (Qt 5.6+)
                    request.setAttribute(
                        QNetworkRequest.RedirectPolicyAttribute,
                        QNetworkRequest.NoLessSafeRedirectPolicy
                    )
            except AttributeError:
                pass

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
        if error_code != NET_NO_ERROR:
            status_code = reply.attribute(HDR_STATUS_CODE)
            error_msg = reply.errorString()
            
            try:
                raw_data = reply.readAll().data()
                if raw_data:
                    decoded = raw_data.decode('utf-8')
                    try:
                        server_data = json.loads(decoded)
                        if isinstance(server_data, dict):
                            if 'error' in server_data:
                                error_msg = server_data['error']
                            elif 'message' in server_data:
                                error_msg = server_data['message']
                        elif isinstance(server_data, str):
                            error_msg = server_data
                    except json.JSONDecodeError:
                        # Plain text error message from server
                        if 0 < len(decoded) < 500:
                            error_msg = decoded
            except Exception:
                pass
            
            # If the error is still generic (like "Forbidden"), provide more context
            if status_code == 403 and (error_msg.strip().lower() == "forbidden" or error_msg.strip().lower() == "unauthorized"):
                error_msg = "Access Denied (403). Please verify your QGIS Plugin Key or check your map storage limits in the dashboard."
            elif status_code == 404 and (error_msg.strip().lower() == "not found"):
                error_msg = "Server endpoint not found (404). Please ensure you are using the latest version of the plugin."
            elif status_code == 413:
                error_msg = "Payload Too Large (413). The file you are trying to upload exceeds server capacity."
            
            raise Exception(error_msg)

        return reply.readAll().data().decode('utf-8')

    def get_maps(self):
        """
        Fetches the user's existing maps from the portal.
        """
        if not self.api_key:
            raise Exception("API Key is not set.")

        url = f"{self.base_url}/maps/"
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"Authorization", f"Bearer {self.api_key}".encode('utf-8'))

        response_text = self._execute_request(request)
        return json.loads(response_text)

    def upload_folder(self, folder_path, map_title="QGIS Upload", map_id=None):
        """
        Calculates size, zips a selected local folder, and uploads it via the signed URL pipeline.
        """
        if not self.api_key:
            raise Exception("API Key is not set.")

        # --- STEP 0: Calculate uncompressed size BEFORE zipping ---
        uncompressed_bytes = 0
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                abs_p = os.path.join(root, file)
                uncompressed_bytes += os.path.getsize(abs_p)
        uncompressed_mb = uncompressed_bytes / (1024 * 1024)

        zip_path = os.path.join(tempfile.gettempdir(), f"qgis2onlinemap_{map_title.replace(' ', '_')}.zip")

        try:
            # Step 1 (Get URL) now happens with the uncompressed size check
            return self.upload_zip(zip_path, map_title, map_id, uncompressed_mb=uncompressed_mb, source_folder=folder_path)

        finally:
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except Exception:
                    pass

    def upload_zip(self, zip_path, map_title="QGIS Upload", map_id=None, uncompressed_mb=None, source_folder=None):
        """
        Uploads a zip file using the three-step signed URL pipeline.
        """
        if not self.api_key:
            raise Exception("API Key is not set.")

        # --- STEP 1: Get signed upload URL (includes limit checks) ---
        query_params = []
        if map_id:
            query_params.append(f"mapId={urllib.parse.quote(map_id, safe='')}")
        
        # Pass uncompressed size if known
        if uncompressed_mb:
            query_params.append(f"uncompressedSizeMB={uncompressed_mb:.2f}")
        elif os.path.exists(zip_path):
            # Calculate uncompressed size of the ZIP archive
            try:
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    u_bytes = sum([zinfo.file_size for zinfo in zf.infolist()])
                    u_mb = u_bytes / (1024 * 1024)
                    query_params.append(f"uncompressedSizeMB={u_mb:.2f}")
            except Exception:
                zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                query_params.append(f"uncompressedSizeMB={zip_size_mb:.2f}")

        url_params = "?" + "&".join(query_params) if query_params else ""
        get_url_endpoint = f"{self.base_url}/get-upload-url{url_params}"
        
        request = QNetworkRequest(QUrl(get_url_endpoint))
        request.setRawHeader(b"Authorization", f"Bearer {self.api_key}".encode('utf-8'))
        response_text = self._execute_request(request)
        url_data = json.loads(response_text)

        signed_url_info = url_data.get('signedUrl', {})
        blob_path = url_data['blobPath']
        server_map_id = url_data['mapId']
        max_size_mb = url_data.get('maxSizeMB', 51)

        # Build the full signed URL (it's either the object or the url property)
        gcs_url = signed_url_info.get('url', signed_url_info) if isinstance(signed_url_info, dict) else signed_url_info
        if not gcs_url:
            raise Exception("Failed to get signed upload URL from server.")

        # --- STEP 1.5: Perform zipping ONLY NOW if it was a folder drop ---
        if source_folder:
            print(f">>> [Plugin] Authorized. Creating ZIP for {source_folder}...")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(source_folder):
                    for file in files:
                        abs_p = os.path.join(root, file)
                        rel_p = os.path.relpath(abs_p, source_folder)
                        zipf.write(abs_p, rel_p)

        # Client-side size pre-check (rough guard on compressed size)
        zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        if zip_size_mb > max_size_mb * 1.5:
            print(f">>> [Plugin] Warning: ZIP size ({zip_size_mb:.1f}MB) is significantly larger than limit.")

        # --- STEP 2: PUT the ZIP directly to GCS ---
        print(f">>> [Plugin] Uploading binary to GCS...")
        put_request = QNetworkRequest(QUrl(gcs_url))
        put_request.setHeader(HDR_CONTENT_TYPE, "application/zip")

        with open(zip_path, 'rb') as f:
            zip_data = f.read()

        from qgis.PyQt.QtCore import QByteArray
        self._execute_request(put_request, data=QByteArray(zip_data))

        # --- STEP 3: Finalize upload ---
        print(f">>> [Plugin] Finalizing map {server_map_id}...")
        finalize_url = f"{self.base_url}/finalize-upload"
        finalize_request = QNetworkRequest(QUrl(finalize_url))
        finalize_request.setRawHeader(b"Authorization", f"Bearer {self.api_key}".encode('utf-8'))
        finalize_request.setHeader(HDR_CONTENT_TYPE, "application/json")

        payload = json.dumps({
            "blobPath": blob_path,
            "mapId": server_map_id,
            "mapName": map_title,
            "isUpdate": bool(map_id),
        })

        from qgis.PyQt.QtCore import QByteArray
        finalize_response = self._execute_request(
            finalize_request,
            data=QByteArray(payload.encode('utf-8'))
        )
        return json.loads(finalize_response)
