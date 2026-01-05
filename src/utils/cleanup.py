import shutil
from .config import Config
from .logger import logger

def cleanup_temp():
    """
    Deletes all files in the temp directory.
    """
    temp_dir = Config.TEMP_DIR
    if not temp_dir.exists():
        return

    logger.info(f"Cleaning up temp files in {temp_dir}...")
    try:
        # Delete only files inside, keep the dir or recreate it
        for item in temp_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        logger.info("Cleanup complete.")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
