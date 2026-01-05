import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    ASSETS_DIR = BASE_DIR / "assets"
    OUTPUT_DIR = BASE_DIR / "output"
    TEMP_DIR = BASE_DIR / "temp"
    BGM_DIR = ASSETS_DIR / "bgm"
    FONTS_DIR = ASSETS_DIR / "fonts"
    
    # AI Providers
    # "g4f" or "openai" or "gemini"
    SCRIPT_PROVIDER = os.getenv("SCRIPT_PROVIDER", "g4f") 
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Image Generation
    # "pollinations"
    IMAGE_PROVIDER = os.getenv("IMAGE_PROVIDER", "pollinations")
    
    # Text to Speech
    # "edge-tts"
    TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge-tts")
    TTS_VOICE = os.getenv("TTS_VOICE", "en-US-ChristopherNeural") # Deep male voice, good for horror

    # Video Settings
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920
    FPS = 24
    
    ENABLE_BGM = True
    BGM_VOLUME = 0.3
    
    @classmethod
    def ensure_dirs(cls):
        cls.ASSETS_DIR.mkdir(exist_ok=True)
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        cls.TEMP_DIR.mkdir(exist_ok=True)
        cls.BGM_DIR.mkdir(exist_ok=True)
        cls.FONTS_DIR.mkdir(exist_ok=True)

Config.ensure_dirs()
