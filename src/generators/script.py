import json
import asyncio
import g4f
from ..utils.logger import logger
from ..utils.config import Config

class ScriptGenerator:
    def __init__(self):
        self.provider = Config.SCRIPT_PROVIDER

    async def generate_viral_topic(self) -> str:
        """
        Generates a catchy, viral, psychological horror topic.
        """
        prompt = """
        Generate 1 short, viral, attention-grabbing horror video topic.
        Focus on: Psychological facts, disturbing theories, scary paradoxes, or urban legends.
        Style: Clickbait, intriguing, short (under 10 words).
        Examples:
        - "The Russian Sleep Experiment details"
        - "Why you wake up at 3AM"
        - "The Uncanny Valley explanation"
        
        Return ONLY the topic text. No quotes.
        """
        topic = await self._call_llm(prompt)
        return topic if topic else "The room that shouldn't exist"

    async def generate_script(self, topic: str = None) -> list[dict]:
        """
        Generates a horror script using a 2-step process:
        1. Write the Story (Text Only)
        2. Generate Image Prompts for each sentence
        """
        if not topic:
            topic = "A random terrifying horror concept about the unknown"

        # Step 1: Generate Story Text
        logger.info(f"Step 1: Writing story for topic: {topic}...")
        story_text = await self._generate_story_text(topic)
        if not story_text:
             logger.error("Failed to generate story text. Using fallback.")
             return [{
                 "text": "I hear them scratching behind the walls at night (Fallback).",
                 "image_prompt": "Hyper-realistic horror cinematic shot, 8k, dark moody lighting, shot on 35mm film, close up of a dirty wall with scratch marks"
             }]
             
        logger.info("Story generated. Extracting sentences...")
        # Step 2: Split into sentences
        sentences = self._split_into_sentences(story_text)
        logger.info(f"Extracted {len(sentences)} sentences.")
        
        # Step 3: Generate Prompts for sentences
        logger.info("Step 2: Generating visual prompts...")
        scenes = await self._generate_prompts_for_sentences(sentences)
        
        return scenes

    async def _generate_story_text(self, topic: str) -> str:
        prompt = f"""
        You are a professional horror writer.
        Task: Write a short, terrifying horror story about: "{topic}".
        
        Requirements:
        1. Length: Approximately 100-150 words (12-15 sentences).
        2. Tone: Dark, suspenseful, and gripping.
        3. Story: The story should be feel like real not fake. the story include story telling ,question and engaging story.
        4. Format: Return ONLY the raw story text. Do not include titles, formatting, or JSON.
        """
        return await self._call_llm(prompt)

    def _split_into_sentences(self, text: str) -> list[str]:
        import re
        # Split by . ! ? followed by whitespace or newline
        sentences = re.split(r'(?<=[.!?])[\s\n]+', text.strip())
        return [s.strip() for s in sentences if s.strip()]

    async def _generate_prompts_for_sentences(self, sentences: list[str]) -> list[dict]:
        import json
        
        # Prepare a prompt that asks for visual descriptions for the provided text
        sentences_block = "\n".join([f"{i+1}. {s}" for i, s in enumerate(sentences)])
        
        prompt = f"""
        You are a Horror Movie Director.
        Here is a script broken into sentences:
        
        {sentences_block}
        
        Task: For EACH sentence, write a "Hyper-realistic horror cinematic shot, 8k, dark moody lighting, shot on 35mm film" image prompt that visualizes that specific moment.
        
        Output strictly valid JSON list of objects:
        [
            {{ "text": "Sentence 1...", "image_prompt": "Visual description..." }},
            ...
        ]
        
        Ensure the "text" field matches the input sentences exactly.
        """
        
        response = await self._call_llm(prompt)
        
        if response:
            try:
                # Clean and parse
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0].strip()
                    
                data = json.loads(response)
                # Verify length or map back if needed, but usually it matches enough.
                return data
            except Exception as e:
                logger.warning(f"Failed to parse scenes JSON: {e}")

        # Fallback: Just return text with generic prompts
        logger.warning("Using algorithmic fallback for prompts.")
        return [{"text": s, "image_prompt": f"Hyper-realistic horror cinematic shot, 8k, dark moody lighting, shot on 35mm film. {s}"} for s in sentences]

    async def _call_llm(self, prompt: str) -> str:
        models_to_try = [
            "gpt-4",
            "gpt-3.5-turbo",
            "command-r+"
        ]
        
        for model in models_to_try:
            try:
                # logger.info(f"Calling {model}...")
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        g4f.ChatCompletion.create,
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                    ),
                    timeout=40.0
                )
                if response:
                    return response.strip()
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
        
        return None
