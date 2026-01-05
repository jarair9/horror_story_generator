# Horror Video Generator

A Python tool that automatically generates short horror videos with AI-generated scripts, voiceovers, images, and video composition.

## Features
- **Script Generation**: Uses `g4f` (Free) or other providers (Gemini/OpenAI) to write scary stories.
- **Voiceover**: Uses `edge-tts` for high-quality, free neural speech.
- **Visuals**: Generates atmospheric images using `Pollinations AI`.
- **Video Assembly**: Combines everything with `MoviePy`, adding pan/zoom effects and subtitles.

## Setup

1. **Install Python**: Ensure you have Python 3.8+ installed.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration (Optional)

The tool works out-of-the-box with free providers. To customize it, you can create a `.env` file in this directory:

```env
# Optional: Switch Script Provider to 'gemini' or 'openai'
SCRIPT_PROVIDER=g4f

# If using Gemini
GEMINI_API_KEY=your_gemini_key_here

# If using OpenAI
OPENAI_API_KEY=your_openai_key_here

# Voice Settings (default: en-US-ChristopherNeural)
TTS_VOICE=en-US-ChristopherNeural
```

## Usage

**Run with a random topic:**
```bash
python main.py
```

**Run with a specific topic:**
```bash
python main.py --topic "The Haunted Doll"
```

## Output
The final video will be saved in the `output/` folder.
