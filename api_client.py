import requests
import zipfile
import os
import tempfile
import urllib.parse

class ApiClient:
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

    def get_maps(self):
        """
        Fetches the user's existing maps from the portal.
        """
        if not self.api_key:
            raise Exception("API Key is not set.")
            
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            response = requests.get(f"{self.base_url}/maps", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            err_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                err_msg = e.response.text
            raise Exception(err_msg)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch maps: {str(e)}")

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
            
            # Perform POST request
            headers = {"Authorization": f"Bearer {self.api_key}"}
            if map_id:
                headers["x-map-id"] = map_id
                headers["x-map-title"] = urllib.parse.quote(map_title, safe='')
            
            with open(zip_path, 'rb') as f:
                filename = f"{map_title}.zip"
                files = {'file': (filename, f, 'application/zip')}
                response = requests.post(f"{self.base_url}/upload", headers=headers, files=files)
                response.raise_for_status()
                return response.json()
            
        except requests.exceptions.HTTPError as e:
            err_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                err_msg = e.response.text
            raise Exception(err_msg)
        except Exception as e:
            raise e
        finally:
            if os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except:
                    pass

    def upload_zip(self, zip_path, map_title="QGIS Upload", map_id=None):
        """
        Uploads an existing zip file.
        """
        if not self.api_key:
            raise Exception("API Key is not set.")
            
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            if map_id:
                headers["x-map-id"] = map_id
                headers["x-map-title"] = urllib.parse.quote(map_title, safe='')
            
            with open(zip_path, 'rb') as f:
                filename = f"{map_title}.zip"
                files = {'file': (filename, f, 'application/zip')}
                response = requests.post(f"{self.base_url}/upload", headers=headers, files=files)
                response.raise_for_status()
                return response.json()
        except requests.exceptions.HTTPError as e:
            err_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                err_msg = e.response.text
            raise Exception(err_msg)
        except Exception as e:
            raise e
