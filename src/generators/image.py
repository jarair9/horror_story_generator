import aiohttp
import asyncio
from pathlib import Path
from ..utils.config import Config
from ..utils.logger import logger

class ImageGenerator:
    def __init__(self):
        self.output_dir = Config.TEMP_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = Config.VIDEO_WIDTH
        self.height = Config.VIDEO_HEIGHT

    async def generate_image(self, prompt: str, index: int) -> str:
        """
        Generates an image from a prompt using Pollinations AI.
        Returns the absolute path to the image file.
        """
        output_file = self.output_dir / f"scene_{index}.jpg"
        
        # Pollinations AI URL format
        # https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model=flux&nologo=true
        
        safe_prompt = prompt.replace(" ", "%20")
        
        # Base URL without model parameter
        base_url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={self.width}&height={self.height}&nologo=true&seed={index}"
        
        logger.info(f"Generating image for scene {index}...")
        
        # Models to try in order of preference
        models = ["flux", "turbo", None] # None means default model
        
        retry_count = 5 # Increased from 3
        current_model_idx = 0
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        for attempt in range(retry_count):
            try:
                # Select model for this attempt
                # If we have failures, we might want to rotate efficiency vs quality? 
                # For now let's try Flux first few times, then simple.
                
                model = models[min(current_model_idx, len(models)-1)]
                current_url = base_url
                if model:
                    current_url += f"&model={model}"
                
                # Add default timeout of 60 seconds
                timeout = aiohttp.ClientTimeout(total=60)
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.get(current_url) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            with open(output_file, "wb") as f:
                                f.write(image_data)
                            logger.info(f"Image saved: {output_file} (Model: {model})")
                            return str(output_file)
                        else:
                            logger.warning(f"Attempt {attempt+1}/{retry_count} failed. Status: {response.status} (Model: {model})")
                            # If 502/server error, maybe switch model faster?
                            if response.status in [500, 502, 503, 504]:
                                current_model_idx += 1
                                
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{retry_count} failed with error: {e}")
                
            if attempt < retry_count - 1:
                wait_time = 3 * (attempt + 1) # Increased backoff
                await asyncio.sleep(wait_time) 
                
                # Rotate model on repeated failures
                if attempt >= 1: # After second fail, switch model
                    current_model_idx += 1
                
        logger.error(f"All attempts failed for scene {index}. Generating fallback black image.")
        
        # Fallback: Create a black placeholder
        from PIL import Image
        img = Image.new('RGB', (self.width, self.height), color='black')
        img.save(output_file)
        return str(output_file)
