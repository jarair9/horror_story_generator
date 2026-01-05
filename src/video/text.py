from moviepy.editor import ImageClip, CompositeVideoClip
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import textwrap
from ..utils.logger import logger
from ..utils.config import Config

class TextEngine:
    def __init__(self, font_name=None, fontsize=70, color="white", stroke_color="black", stroke_width=4):
        self.fontsize = fontsize
        self.color = color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        
        # Load custom font if available
        self.font_path = self._find_font(font_name)
        
    def _find_font(self, font_name):
        """Finds any .ttf file in assets/fonts or uses default"""
        if font_name:
             specific_path = Config.FONTS_DIR / font_name
             if specific_path.exists():
                 return str(specific_path)

        # Search for any .ttf
        fonts = list(Config.FONTS_DIR.glob("*.ttf"))
        if fonts:
            logger.info(f"Using custom font: {fonts[0].name}")
            return str(fonts[0])
            
        return "arialbd.ttf" # Fallback
        
    def _create_pil_text_image(self, text, max_width=900):
        """
        Creates a PIL Image with the text drawn on transparency.
        """
        try:
            # Try to load font, fallback to default if not found
            try:
                font = ImageFont.truetype(self.font_path, self.fontsize)
            except IOError:
                logger.warning(f"Font {self.font_path} not found, using default.")
                font = ImageFont.load_default()
            
            # Wrap text
            avg_char_width = self.fontsize * 0.5 # Adjusted for horror fonts which might be narrow
            wrap_width = int(max_width / avg_char_width)
            if wrap_width < 10: wrap_width = 10
            
            lines = textwrap.wrap(text, width=wrap_width)
            
            # Calculate total size
            line_heights = []
            line_widths = []
            
            for line in lines:
                bbox = font.getbbox(line)
                line_widths.append(bbox[2] - bbox[0])
                line_heights.append(bbox[3] - bbox[1])
                
            line_spacing = int(self.fontsize * 0.2)
            total_height = sum(line_heights) + (len(lines) - 1) * line_spacing + 40 # extra padding
            max_line_width = max(line_widths) if line_widths else 0
            img_width = max(max_width, max_line_width + 40)
            
            # Create transparent image with a semi-transparent background box for readability
            img = Image.new('RGBA', (img_width, total_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # No background rectangle: keep caption background transparent for clear overlay

            # Draw text
            y_offset = 20
            shadow_offset = 6
            
            for line in lines:
                bbox = font.getbbox(line)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                
                # Center align
                x_offset = (img_width - w) // 2
                
                # 1. Drop Shadow (Hard shadow for now)
                draw.text((x_offset + shadow_offset, y_offset + shadow_offset), line, font=font, fill="black")

                # 2. Outline/Stroke
                if self.stroke_width > 0:
                    for adj in range(-self.stroke_width, self.stroke_width+1):
                        for adj2 in range(-self.stroke_width, self.stroke_width+1):
                             draw.text((x_offset+adj, y_offset+adj2), line, font=font, fill=self.stroke_color)

                # 3. Main Text
                draw.text((x_offset, y_offset), line, font=font, fill=self.color)
                
                y_offset += h + line_spacing
                
            return img
            
        except Exception as e:
            logger.error(f"Error creating PIL text image: {e}")
            return None

    def create_caption_clip(self, text: str, duration: float) -> ImageClip:
        """
        Creates a single text clip for a specific duration using PIL.
        """
        pil_img = self._create_pil_text_image(text, max_width=Config.VIDEO_WIDTH - 150)
        
        if pil_img:
            # Position captions near the center for better focus on-screen
            return ImageClip(np.array(pil_img)).set_duration(duration).set_position(('center', 'center'), relative=True).crossfadein(0.1)
        
        return None

    def split_text_into_chunks(self, text: str, max_words=5) -> list[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_words):
            chunks.append(" ".join(words[i:i+max_words]))
        return chunks

    def generate_subtitles(self, scenes: list) -> list:
        """
        Generates a list of TextClips synced to the scenes.
        Splits long sentences into smaller chunks (Karaoke style).
        """
        clips = []
        for scene in scenes:
            full_text = scene.get("text", "")
            total_duration = scene.get("duration", 2)
            
            # Split into chunks
            chunks = self.split_text_into_chunks(full_text, max_words=5)
            if not chunks:
                continue
                
            # Calculate duration per chunk based on character count
            total_chars = len(full_text.replace(" ", ""))
            if total_chars == 0: total_chars = 1
            
            start_time = 0 # Relative to scene start
            
            for chunk in chunks:
                chunk_chars = len(chunk.replace(" ", ""))
                # Proportional duration
                chunk_duration = (chunk_chars / total_chars) * total_duration
                
                # Create clip
                clip = self.create_caption_clip(chunk, chunk_duration)
                if clip:
                    # We need to set the start time relative to the sequence if we were using CompositeVideo as a whole
                    # But here we are returning a list of clips to be concatenated?
                    # No, TextEngine.generate_subtitles returns a list of clips. 
                    # The caller (composer.py) iterates zip(video_clips, scenes).
                    # Composer expects ONE clip that lasts the whole scene OR needs to composite multiple.
                    
                    # Wait! Composer.py logic:
                    # txt_clip = text_engine.create_caption_clip(text, clip.duration)
                    # composite = CompositeVideoClip([clip, txt_clip])
                    
                    # We need to change Composer to handle a LIST of text clips for one scene.
                    # Or we return a single CompositeVideoClip containing all the text chunks properly timed.
                    
                    clip = clip.set_start(start_time)
                    clips.append(clip)
                
                start_time += chunk_duration

        # This return logic is now broken for the current Composer implementation.
        # The current Composer expects `create_caption_clip` to return one clip.
        # We need to update `generate_scenes_with_text` logic in Composer or return a Composite here.
        return clips
        
    def create_karaoke_clip(self, text: str, total_duration: float) -> CompositeVideoClip:
        """
        Creates a CompositeVideoClip containing the sequence of chunked text clips.
        """
        chunks = self.split_text_into_chunks(text, max_words=5)
        if not chunks:
            return None
            
        total_chars = len(text.replace(" ", ""))
        if total_chars == 0: total_chars = 1
        
        text_clips = []
        current_time = 0
        
        for chunk in chunks:
            chunk_chars = len(chunk.replace(" ", ""))
            chunk_duration = (chunk_chars / total_chars) * total_duration
            
            # Create the image clip
            img_clip = self.create_caption_clip(chunk, chunk_duration)
            if img_clip:
                img_clip = img_clip.set_start(current_time)
                text_clips.append(img_clip)
            
            current_time += chunk_duration
            
        if not text_clips:
            return None
            
        # Create a transparent base clip to hold them all
        # return CompositeVideoClip(text_clips, size=(Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT)).set_duration(total_duration)
        # Actually returning a list or just the composite of text is fine if the background is transparent.
        # But CompositeVideoClip needs a size if it's just text clips.
        
        # Simpler: Just return the list of timed clips to be composited over the video in Composer.
        return text_clips
