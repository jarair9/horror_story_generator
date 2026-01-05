import asyncio
import sys
import PIL.Image

# Monkey patch for moviepy compatibility with newer Pillow versions
# Monkey patch for moviepy compatibility with newer Pillow versions
try:
    if not hasattr(PIL.Image, 'ANTIALIAS'):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
except AttributeError:
    pass

from src.generators.script import ScriptGenerator
from src.generators.audio import AudioGenerator
from src.generators.image import ImageGenerator
from src.video.composer import VideoCompositor
from src.utils.logger import logger
from src.utils.cleanup import cleanup_temp

async def main():
    try:
        cleanup_temp()
        
        print("\n\033[91m=== AI HORROR VIDEO GENERATOR ===\033[0m")
        topic = input("\nEnter Topic (or Press Enter for Random): ").strip()

        # 1. Generate Script
        print("\n\033[93m[1/3] Generating Story...\033[0m")
        script_gen = ScriptGenerator()
        scenes = await script_gen.generate_script(topic)
        print(f"      > Created {len(scenes)} scenes.")

        # Save script to file
        import json
        from src.utils.config import Config
        script_path = Config.OUTPUT_DIR / "script.json"
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, indent=4)
        
        # 2. Generate Assets (Audio & Images)
        print("\n\033[93m[2/3] Generating Assets...\033[0m")
        audio_gen = AudioGenerator()
        image_gen = ImageGenerator()
        
        # A. Continuous Audio Generation
        print("      > Generating Narration & VTT...")
        full_script_text = " ".join([s['text'] for s in scenes])
        audio_path, vtt_path = await audio_gen.generate_full_narration(full_script_text, filename="story_narration")
        
        # B. Parse VTT to get EXACT timings for each scene
        import webvtt
        
        print("      > Syncing Audio...")
        vtt = webvtt.read(vtt_path)
        all_cues = list(vtt)
        
        current_cue_idx = 0
        total_cues = len(all_cues)
        
        def normalize(s):
            return "".join(c.lower() for c in s if c.isalnum())
            
        def vtt_to_sec(t_str):
            h, m, s = t_str.split(':')
            return float(h) * 3600 + float(m) * 60 + float(s)

        for i, scene in enumerate(scenes):
            scene_text = scene['text']
            
            # Simple greedy matcher
            start_time_sec = 0
            end_time_sec = 3.0
            
            if current_cue_idx < total_cues:
                accumulated_text = ""
                scene_text_norm = normalize(scene_text)

                # Use the start time of the first cue we consume, and keep accumulating
                # cues until the normalized scene text is found within the accumulated text.
                while current_cue_idx < total_cues:
                    cue = all_cues[current_cue_idx]
                    cue_text = cue.text

                    # set start at the first consumed cue
                    if accumulated_text == "":
                        start_time_sec = vtt_to_sec(cue.start)

                    # add a space to keep words separated when concatenating cues
                    accumulated_text = (accumulated_text + " " + cue_text).strip()
                    accum_norm = normalize(accumulated_text)

                    # If the scene text appears anywhere in the accumulated cues, we consider it matched.
                    if scene_text_norm in accum_norm or len(accum_norm) >= len(scene_text_norm):
                        end_time_sec = vtt_to_sec(cue.end)
                        current_cue_idx += 1
                        break

                    current_cue_idx += 1
                
                # Check bounds
                if i == len(scenes) - 1: end_time_sec = vtt_to_sec(all_cues[-1].end)
                duration = max(1.0, end_time_sec - start_time_sec)
                scene['duration'] = duration
            else:
                scene['duration'] = 3.0

        processed_scenes = []
        
        # C. Generate Images (Sequential)
        print(f"      > Generating {len(scenes)} Cinematic Images...")
        for i, scene in enumerate(scenes):
            # Print minimal progress on same line if possible, or simple dots
            # print(f"\r      > Image {i+1}/{len(scenes)}", end="")
            processed_scenes.append({
                "text": scene['text'],
                "image": await image_gen.generate_image(scene['image_prompt'], i),
                "duration": scene['duration']
            })
        print("") # Newline

        # 3. Assemble Video
        print("\n\033[93m[3/3] Assembling Video...\033[0m")
        compositor = VideoCompositor()
        output_file = compositor.assemble_video(processed_scenes, master_audio_path=audio_path)
        
        print(f"\n\033[92m[DONE] Video saved:\033[0m {output_file}\n")
        
    except KeyboardInterrupt:
        print("\n[!] Cancelled.")
    except Exception as e:
        logger.exception("Error:")
        print(f"\n[!] Error: {e}")
    finally:
        cleanup_temp()

if __name__ == "__main__":
    if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
