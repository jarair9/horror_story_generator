import streamlit as st
import asyncio
import os
import sys
from pathlib import Path
import PIL.Image
import random

# Monkey patch for moviepy compatibility
try:
    from PIL import Image, ImageFilter
    # Assign unconditionally to silence read-access DeprecationWarning in older Pillow
    # and to ensure it exists in newer Pillow
    Image.ANTIALIAS = Image.LANCZOS
except ImportError:
    pass

# Add src to pythonpath if needed
sys.path.append(str(Path(__file__).parent))

from src.generators.script import ScriptGenerator
from src.generators.audio import AudioGenerator
from src.generators.image import ImageGenerator
from src.video.composer import VideoCompositor
from src.utils.config import Config
from src.utils.cleanup import cleanup_temp
from src.utils.logger import logger

# Configure Streamlit page
st.set_page_config(
    page_title="Horror Video Generator",
    page_icon="👻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stButton>button {
        background-color: #ff4b4b;
        color: white;
        border-radius: 5px;
        height: 3em;
        width: 100%;
        font-weight: bold;
    }
    /* Add spacing between elements */
    .stButton {
        margin-bottom: 15px;
    }
    div.stButton > button:first-child {
        background-color: #ff4b4b;
        color: white;
    }
    .stProgress > div > div > div > div {
        background-color: #ff4b4b;
    }
    div[data-testid="stExpander"] {
        border-color: #333;
        background-color: #1a1a1a;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("👻 AI Horror Video Generator")
st.markdown("Create viral, cinematic horror videos with AI-powered storytelling.")
st.divider()

# Function to get random topics (Fallback)
def get_random_topic():
    topics = [
        "The Capgras Delusion: Imposters in your family",
        "Why you should never whistle at night",
        "The Dead Internet Theory explained",
        "The Roko's Basilisk Paradox",
        "Liminal Spaces: Why empty places scare you",
        "The Call of the Void (L'appel du vide)",
        "Cotard's Syndrome: The walking dead",
        "The Black Eyed Children phenomenon",
        "Why looking in a mirror in logic dreams is dangerous",
        "The dark truth behind the 'Backrooms'"
    ]
    return random.choice(topics)

# Initialize session state for topic
if 'topic_input' not in st.session_state:
    st.session_state.topic_input = ""

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    st.divider()
    
    st.subheader("📝 Story")
    
    # Use columns with gap for buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎲 Random Hook", help="Get a random psychological horror hook"):
             st.session_state.topic_input = get_random_topic()
             
    with col2:
        if st.button("🤖 AI Idea", help="Generate a unique viral hook with AI"):
             with st.spinner("Thinking..."):
                 try:
                     # Run async in sync context
                     loop = asyncio.new_event_loop()
                     asyncio.set_event_loop(loop)
                     gen = ScriptGenerator()
                     topic = loop.run_until_complete(gen.generate_viral_topic())
                     loop.close()
                     st.session_state.topic_input = topic
                 except Exception as e:
                     st.error("AI Failed")
                     st.session_state.topic_input = get_random_topic()
        
    topic = st.text_area("Horror Topic", value=st.session_state.topic_input, placeholder="e.g. A cursed phone number...", height=120)
    # Update session state if user types manually
    st.session_state.topic_input = topic
    
    st.divider()
    
    st.subheader("🔊 Audio")
    enable_bgm = st.checkbox("Enable Background Music", value=Config.ENABLE_BGM)
    
    # BGM Uploader
    with st.expander("📤 Upload Custom BGM"):
        uploaded_bgm = st.file_uploader("Upload MP3", type=["mp3"])
        if uploaded_bgm:
            # Save to assets/bgm
            bgm_save_path = Config.BGM_DIR / uploaded_bgm.name
            with open(bgm_save_path, "wb") as f:
                f.write(uploaded_bgm.getbuffer())
            st.success(f"Saved: {uploaded_bgm.name}")
    
    # List available BGM files (refresh list)
    bgm_files = list(Config.BGM_DIR.glob("*.mp3"))
    bgm_options = ["Random"] + [f.name for f in bgm_files]
    
    selected_bgm = st.selectbox("Select BGM Track", bgm_options, disabled=not enable_bgm)
    bgm_volume = st.slider("BGM Volume", 0.0, 1.0, Config.BGM_VOLUME, 0.05, disabled=not enable_bgm)
    
    # Update Config based on UI
    Config.ENABLE_BGM = enable_bgm
    Config.BGM_VOLUME = bgm_volume

async def generate_video_flow(topic_input, bgm_file_path=None):
    # Use a clean container for status
    status_container = st.container()
    
    with status_container:
        status_text = st.empty()
        progress_bar = st.progress(0)
    
    def update_status(text, prog):
        status_text.markdown(f"### {text}")
        progress_bar.progress(prog)
    
    try:
        cleanup_temp()
        
        # 1. Script
        update_status("✍️ Writing the Horror Story...", 10)
        
        if not topic_input:
            topic_input = None
            
        script_gen = ScriptGenerator()
        scenes = await script_gen.generate_script(topic_input)
        
        # Display Script Preview
        with st.expander("📜 View Generated Script", expanded=True):
            for i, scene in enumerate(scenes):
                st.markdown(f"**Scene {i+1}**: {scene['text']}")
                st.caption(f"Visual: *{scene['image_prompt']}*")

        # Save script to output
        import json
        script_path = Config.OUTPUT_DIR / "script.json"
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(scenes, f, indent=4)
        
        # 2. Assets
        audio_gen = AudioGenerator()
        image_gen = ImageGenerator()
        
        # Generate per-scene audio for perfect synchronization
        update_status("🎙️ Generating Scene Narration...", 30)
        
        from moviepy.editor import AudioFileClip
        
        for i, scene in enumerate(scenes):
            prog = 30 + int(5 * (i / len(scenes)))
            update_status(f"🎙️ Generating Audio ({i+1}/{len(scenes)})...", prog)
            
            # Generate audio for this specific scene
            audio_path = await audio_gen.generate_voiceover(scene['text'], i)
            
            # Get exact duration from the audio file
            audio_clip = AudioFileClip(audio_path)
            scene['audio'] = audio_path
            scene['duration'] = audio_clip.duration
            audio_clip.close()
        
        # Generate Images
        update_status("🎨 Generating Visuals...", 35)
        
        processed_scenes = []
        total_scenes = len(scenes)
        
        # Create a grid for images
        image_cols = st.columns(4)
        
        for i, scene in enumerate(scenes):
            prog = 35 + int(55 * (i / total_scenes))
            update_status(f"🎨 Generating Visuals ({i+1}/{total_scenes})...", prog)
            
            image_path = await image_gen.generate_image(scene['image_prompt'], i)
            
            processed_scenes.append({
                "text": scene['text'],
                "image": image_path,
                "audio": scene['audio'],
                "duration": scene['duration']
            })
            
            # Show image in grid
            col_idx = i % 4
            with image_cols[col_idx]:
                st.image(image_path, caption=f"Scene {i+1}", width="stretch")

        # 3. Assembly
        update_status("🎬 Assembling Final Video (Applying Vignette & Captions)...", 90)
        compositor = VideoCompositor()
        
        output_file = compositor.assemble_video(
            processed_scenes,
            specific_bgm_path=str(bgm_file_path) if bgm_file_path else None
        )
        
        update_status("✅ Generation Complete!", 100)
        return output_file
        
    except Exception as e:
        status_text.error(f"❌ Error: {str(e)}")
        logger.exception("Streamlit generation error")
        return None
    finally:
        cleanup_temp()

if st.button("🎥 Generate Horror Video"):
    # Check keys if needed (disabled for g4f mode)
    if not Config.OPENAI_API_KEY and not Config.GEMINI_API_KEY and Config.SCRIPT_PROVIDER != "g4f":
         st.error("Please configure API Keys in .env or switch execution provider.")
    else:
        # Resolve BGM Path
        selected_bgm_path = None
        if Config.ENABLE_BGM and selected_bgm != "Random":
            selected_bgm_path = Config.BGM_DIR / selected_bgm
            
        with st.spinner("Summoning the spirits..."):
            output_video_path = asyncio.run(generate_video_flow(st.session_state.topic_input, selected_bgm_path))
            
            if output_video_path:
                st.success("Your nightmare is ready.")
                st.video(output_video_path)
                
                with open(output_video_path, "rb") as file:
                    st.download_button(
                        label="⬇️ Download Video",
                        data=file,
                        file_name="horror_story.mp4",
                        mime="video/mp4"
                    )
