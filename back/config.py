
import os
from pathlib import Path

class Config:
   
    BASE_DIR = Path(__file__).parent.parent
    MODEL_PATH = BASE_DIR / 'models' / 'yolov8m_best.pt'
    OUTPUT_DIR = BASE_DIR / 'outputs'
    
   
    CONFIDENCE_THRESHOLD = 0.25  
    IOU_THRESHOLD = 0.5
    IMAGE_SIZE = 640
    

    HOST = '0.0.0.0'
    PORT = 5000
    DEBUG = False
    
    
    PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY', '').strip()
    PERPLEXITY_MODEL = os.getenv('PERPLEXITY_MODEL', 'llama-3.1-70b-instruct')

   
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '').strip()
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    

    CLASS_NAMES = ['signature', 'stamp', 'qr_code']
    CLASS_COLORS = {
        0: (0, 0, 255),    # Red
        1: (255, 0, 0),    # Blue
        2: (0, 255, 0)     # Green
    }
    

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {
        'jpg', 'jpeg', 'png', 'bmp', 'webp', 'tif', 'tiff', 'heic', 'heif', 'pdf'
    }
    
    @staticmethod
    def init_app():
        """Инициализация папок"""
        os.makedirs(Config.OUTPUT_DIR / 'images', exist_ok=True)
        os.makedirs(Config.OUTPUT_DIR / 'json', exist_ok=True)

    # Режим саммари: 'counts' (по числу детекций), 'random' (демо), 'llm' (внешние модели)
    SUMMARIZE_MODE = os.getenv('SUMMARIZE_MODE', 'counts').strip().lower() or 'counts'
