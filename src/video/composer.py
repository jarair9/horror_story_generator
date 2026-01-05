from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, CompositeAudioClip, vfx
import moviepy.audio.fx.all as afx
import os
import numpy as np
from ..utils.config import Config
from ..utils.logger import logger

class VideoCompositor:
    def __init__(self):
        self.width = Config.VIDEO_WIDTH
        self.height = Config.VIDEO_HEIGHT
        self.fps = Config.FPS

    def resize_to_fill(self, clip: ImageClip) -> ImageClip:
        """
        Resizes and crops the image to fill the target resolution (cover).
        """
        w, h = clip.size
        target_w, target_h = self.width, self.height
        
        # Calculate aspect ratios
        target_aspect = target_w / target_h
        img_aspect = w / h
        
        if img_aspect > target_aspect:
            # Image is wider than target: resize by height, then center crop width
            new_h = target_h
            new_w = int(target_h * img_aspect)
            clip_resized = clip.resize(height=new_h)
            # Center crop
            x_center = new_w / 2
            return clip_resized.crop(
                x1=x_center - target_w / 2, 
                y1=0, 
                width=target_w, 
                height=target_h
            )
        else:
            # Image is taller/narrower than target: resize by width, then center crop height
            new_w = target_w
            new_h = int(target_w / img_aspect)
            clip_resized = clip.resize(width=new_w)
            # Center crop
            y_center = new_h / 2
            return clip_resized.crop(
                x1=0, 
                y1=y_center - target_h / 2, 
                width=target_w, 
                height=target_h
            )

    def apply_ken_burns(self, clip: ImageClip, zoom_ratio=1.3) -> ImageClip:
        """
        Applies a slow zoom effect (Ken Burns).
        """
        w, h = clip.size
        # Clip is already resized to fill, so w, h should match self.width, self.height
        duration = clip.duration
        
        def resize_func(t):
            # Slow linear zoom
            scale = 1 + (zoom_ratio - 1) * (t / duration)
            return scale

        # Resize and center crop
        # MoviePy's resize is computationally expensive if done per frame using a function.
        # An alternative is to just crop a moving window, or simple resize.
        # Let's try simple resize then center crop.
        
        clip_zoomed = clip.resize(resize_func)
        return clip_zoomed.set_position(('center', 'center'))

    def add_vignette(self, clip, opacity=0.6):
        """
        Adds a dark vignette overlay to the clip.
        """
        w, h = clip.size
        
        # Create a radial gradient mask using numpy
        x = np.linspace(-1, 1, w)
        y = np.linspace(-1, 1, h)
        X, Y = np.meshgrid(x, y)
        
        # Calculate radius from center
        radius = np.sqrt(X**2 + Y**2)
        
        # Create mask: 0 at center, 1 at corners
        # Adjust curve for vignette falloff
        mask = radius ** 2.5
        mask = np.clip(mask, 0, 1) * opacity
        
        # Create a black image
        vignette_layer = np.zeros((h, w, 3), dtype=np.uint8) # Black
        
        # BUT moviepy needs an ImageClip to overlay.
        # Simpler: Create a ColorClip('black') and set its mask/alpha.
        
        from moviepy.editor import ColorClip, ImageClip
        
        # Create an alpha mask array (0=transparent center, 255=opaque corners)
        alpha_mask = (mask * 255).astype(np.uint8)
        
        # We need to make this a proper ImageClip to overlay
        # Since generating this numpy array for every frame is expensive if done dynamically,
        # we generate a static image for the vignette and overlay it.
        
        # Make an RGBA image
        vignette_img = np.dstack((vignette_layer, alpha_mask))
        
        from PIL import Image
        pil_vignette = Image.fromarray(vignette_img, 'RGBA')
        
        vignette_clip = ImageClip(np.array(pil_vignette)).set_duration(clip.duration)
        
        # Composite
        return CompositeVideoClip([clip, vignette_clip])

    def assemble_video(self, scenes: list, output_filename: str = "final_video.mp4", specific_bgm_path: str = None):
        """
        Assembles individual scenes into the final video.
        scenes: list of dicts { 'image': path, 'audio': path, 'text': str, 'duration': float }
        """
        video_clips = []
        
        logger.info("Assembling video clips...")
        
        for i, scene in enumerate(scenes):
            image_path = scene['image']
            audio_path = scene['audio']
            
            # Use provided duration (from actual audio file)
            duration = scene.get('duration', 3.0)
            
            # Load Image
            img_clip = ImageClip(image_path).set_duration(duration)
            
            # 1. Resize to Fill Screen (Cover Mode)
            img_clip = self.resize_to_fill(img_clip)
            
            # Apply Ken Burns Effect (Zoom In)
            img_clip = self.apply_ken_burns(img_clip, zoom_ratio=1.15)
            
            # Apply Vignette (Dark corners)
            img_clip = self.add_vignette(img_clip, opacity=0.7)
            
            # Set audio for this clip
            if audio_path and os.path.exists(audio_path):
                scene_audio = AudioFileClip(audio_path)
                img_clip = img_clip.set_audio(scene_audio)
            
            video_clips.append(img_clip)

        # Combine video clips
        # method="compose" is safer but slower.
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # Note: Audio is already embedded in each clip, so final_video will have the concatenated audio
        
        # Add Captions (Overlay)
        from .text import TextEngine
        text_engine = TextEngine()
        
        # Add text to each clip before they were concatenated
        clips_with_text = []
        for clip, scene in zip(video_clips, scenes):
             text = scene['text']
             text_clips = text_engine.create_karaoke_clip(text, clip.duration)
             
             if text_clips:
                 layers = [clip] + text_clips
                 composite = CompositeVideoClip(layers).set_duration(clip.duration)
                 clips_with_text.append(composite)
             else:
                 clips_with_text.append(clip)
                 
        final_video = concatenate_videoclips(clips_with_text, method="compose")
        
        # Add BGM if available
        import random
        # Search in BGM_DIR
        bgm_files = list(Config.BGM_DIR.glob("*.mp3"))
        
        bgm_path = None
        if Config.ENABLE_BGM:
            if specific_bgm_path and os.path.exists(specific_bgm_path):
                bgm_path = Path(specific_bgm_path)
            elif bgm_files:
                bgm_path = random.choice(bgm_files)
        
        if bgm_path:
            logger.info(f"Adding background music: {bgm_path}")
            bgm_clip = AudioFileClip(str(bgm_path))
            
            # Loop bgm to match video duration
            if bgm_clip.duration < final_video.duration:
                bgm_clip = afx.audio_loop(bgm_clip, duration=final_video.duration)
            else:
                bgm_clip = bgm_clip.subclip(0, final_video.duration)
                
            # Lower volume
            bgm_clip = bgm_clip.volumex(Config.BGM_VOLUME)
            
            # Combine audio (Voiceover + BGM)
            final_audio = CompositeAudioClip([final_video.audio, bgm_clip])
            final_video = final_video.set_audio(final_audio)
        else:
            logger.info("No BGM found in assets/bgm.")

        output_path = Config.OUTPUT_DIR / output_filename
        logger.info(f"Rendering final video to {output_path}...")
        
        final_video.write_videofile(
            str(output_path),
            fps=self.fps,
            codec='libx264',
            audio_codec='aac',
            threads=8,
            preset='ultrafast'
        )
        logger.info("Video rendering complete!")
        return str(output_path)
