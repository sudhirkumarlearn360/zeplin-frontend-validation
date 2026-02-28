import requests
from django.conf import settings
from urllib.parse import urljoin

class ZeplinService:
    BASE_URL = "https://api.zeplin.dev/v1/"
    
    def __init__(self, token=None):
        self.token = token or getattr(settings, 'ZEP_DEFAULT_TOKEN', '')
        self.headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
    def fetch_screen_data(self, project_id, screen_id):
        """
        Fetches the screen top-level data and its layers from Zeplin.
        """
        url = urljoin(self.BASE_URL, f"projects/{project_id}/screens/{screen_id}")
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        screen_data = response.json()
        
        # Try to get layer data for CSS extraction
        layers = []
        version_id = screen_data.get('latest_version', {}).get('id')
        if version_id:
            try:
                layers_url = urljoin(self.BASE_URL, f"projects/{project_id}/screens/{screen_id}/versions/{version_id}/layers")
                layers_resp = requests.get(layers_url, headers=self.headers)
                if layers_resp.status_code == 200:
                    layers = layers_resp.json()
            except Exception as e:
                # Silently fail layer fetching if not authorized or API changes
                pass
                
        return {
            "screen": screen_data,
            "layers": layers,
        }

    def download_design_image(self, url, output_path):
        """
        Downloads the design image to a local path.
        """
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
