import edge_tts
import asyncio
from pathlib import Path
from ..utils.config import Config
from ..utils.logger import logger

class AudioGenerator:
    def __init__(self):
        self.voice = Config.TTS_VOICE
        self.output_dir = Config.TEMP_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_voiceover(self, text: str, index: int) -> str:
        """
        Generates audio for a single line of text.
        Returns the absolute path to the audio file.
        """
        output_file = self.output_dir / f"scene_{index}.mp3"
        
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(output_file))
            logger.info(f"Generated audio for scene {index}: {output_file}")
            return str(output_file)
        except Exception as e:
            logger.error(f"Audio generation failed for scene {index}: {e}")
            raise e

    async def generate_full_narration(self, text: str, filename="full_audio") -> tuple[str, str]:
        """
        Generates audio for the entire script text.
        Returns (audio_path, vtt_path).
        """
        audio_path = self.output_dir / f"{filename}.mp3"
        vtt_path = self.output_dir / f"{filename}.vtt"
        
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            submaker = edge_tts.SubMaker()
            
            with open(audio_path, "wb") as file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        submaker.feed(chunk)
                        
            with open(vtt_path, "w", encoding="utf-8") as file:
                # SubMaker only supports get_srt() in 7.x
                srt_content = submaker.get_srt()
                
                # Convert SRT to VTT
                # 1. Add Header
                vtt_content = "WEBVTT\n\n" + srt_content
                # 2. Convert timestamps (00:00:00,000 -> 00:00:00.000)
                vtt_content = vtt_content.replace(",", ".")
                
                file.write(vtt_content)
                
            logger.info(f"Generated full narration: {audio_path}")
            return str(audio_path), str(vtt_path)
            
        except Exception as e:
            logger.error(f"Full narration generation failed: {e}")
            raise e
