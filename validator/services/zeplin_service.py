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
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        screen_data = response.json()
        
        # Try to get layer data for CSS extraction
        layers = []
        try:
            versions_url = urljoin(self.BASE_URL, f"projects/{project_id}/screens/{screen_id}/versions")
            versions_resp = requests.get(versions_url, headers=self.headers, timeout=10)
            if versions_resp.status_code == 200:
                versions_data = versions_resp.json()
                if isinstance(versions_data, list):
                    # Loop over all versions (newest usually last or first)
                    # We will try them in reverse (newest first)
                    for version in reversed(versions_data):
                        version_id = version.get('id')
                        if not version_id: continue
                        
                        layers_url = urljoin(self.BASE_URL, f"projects/{project_id}/screens/{screen_id}/versions/{version_id}/layers")
                        try:
                            layers_resp = requests.get(layers_url, headers=self.headers, timeout=10)
                            if layers_resp.status_code == 200:
                                layers = layers_resp.json()
                                if layers:
                                    break  # Successfully fetched layers!
                        except requests.exceptions.RequestException:
                            pass
        except Exception as e:
            # Silently fail layer fetching if not authorized or API changes
            pass
            
        # Fallback dummy layer if Zeplin API refuses to provide layer geometry
        if not layers:
            image_url = screen_data.get('image', {}).get('original_url')
            if image_url:
                layers = self._run_ocr_fallback(image_url)
                
            if not layers:
                layers = [{
                    "type": "text",
                    "name": "Dummy Fallback Layer",
                    "content": "Zeplin API refused to return layer data for this screen.\\nDummy block inserted for code generation testing.",
                    "rect": {"x": 50, "y": 100, "width": 600, "height": 200},
                    "fills": [{"color": {"r": 255, "g": 200, "b": 200, "a": 1}}],
                    "borders": [{"color": {"r": 255, "g": 0, "b": 0, "a": 1}, "thickness": 2}],
                    "border_radius": 10,
                    "texts": [{"style": {"font_size": 24, "color": {"r": 50, "g": 0, "b": 0, "a": 1}}}]
                }]
            
        return {
            "screen": screen_data,
            "layers": layers,
        }

    def _run_ocr_fallback(self, image_url):
        """
        Downloads the screen image into memory and uses EasyOCR to extract visual text blocks,
        generating synthetic layer JSON payloads that the HTML converter can render.
        """
        layers = []
        try:
            import urllib.request
            import numpy as np
            import cv2
            import easyocr
            import ssl
            
            # Download image bypassing SSL in case of local cert issues
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.urlopen(image_url, context=ctx)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, -1)
            
            if img is None:
                return []
                
            # Initialize reader (Downloads PyTorch models on first run if missing)
            reader = easyocr.Reader(['en'])
            results = reader.readtext(img)
            
            for (bbox, text, prob) in results:
                if prob < 0.2:
                    continue
                x1, y1 = int(bbox[0][0]), int(bbox[0][1])
                x2, y2 = int(bbox[2][0]), int(bbox[2][1])
                w = max(1, x2 - x1)
                h = max(1, y2 - y1)
                
                # Create a synthetic Zeplin text layer based on the OCR bounding box
                layers.append({
                    "type": "text",
                    "name": f"OCR Text: {text[:10]}",
                    "content": text,
                    "rect": {"x": x1, "y": y1, "width": w, "height": h},
                    "texts": [{"style": {"font_size": max(12, int(h * 0.7)), "color": {"r": 50, "g": 50, "b": 50, "a": 1}}}]
                })
        except Exception as e:
            print(f"OCR Fallback Error: {e}")
            
        return layers

    def download_design_image(self, url, output_path):
        """
        Downloads the design image to a local path.
        """
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
