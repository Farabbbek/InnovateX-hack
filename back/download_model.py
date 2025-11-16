import os
import requests

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "yolov8m_best.pt")
MODEL_URL = os.environ.get("MODEL_URL")

def download_model(url, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        print("Model already exists")
        return
    print("Downloading model:", url)
    r = requests.get(url, stream=True)
    r.raise_for_status()
    with open(dst, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print("Model downloaded:", dst)

if MODEL_URL:
    download_model(MODEL_URL, MODEL_PATH)
else:
    print("MODEL_URL not set, skipping model download")
