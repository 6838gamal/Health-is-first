import asyncio
import logging
import os
import uuid
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

ARABIC_VOICES = {
    "male": "ar-EG-ShakirNeural",
    "female": "ar-EG-SalmaNeural",
    "male_sa": "ar-SA-HamedNeural",
    "female_sa": "ar-SA-ZariyahNeural",
}


class TTSService:
    def __init__(self):
        self.output_dir = Path(settings.AUDIO_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_audio_edge(
        self, text: str, voice: str = None, output_filename: str = None
    ) -> str:
        import edge_tts
        voice = voice or settings.TTS_VOICE
        filename = output_filename or f"{uuid.uuid4()}.mp3"
        output_path = self.output_dir / filename

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))
        logger.info(f"Audio generated: {output_path}")
        return str(output_path)

    def generate_audio_gtts(self, text: str, lang: str = "ar", output_filename: str = None) -> str:
        from gtts import gTTS
        filename = output_filename or f"{uuid.uuid4()}.mp3"
        output_path = self.output_dir / filename
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(str(output_path))
        logger.info(f"Audio generated (gTTS): {output_path}")
        return str(output_path)

    def generate_audio(self, text: str, voice: str = None, output_filename: str = None) -> str:
        if settings.TTS_PROVIDER == "edge_tts":
            return asyncio.run(self.generate_audio_edge(text, voice, output_filename))
        else:
            return self.generate_audio_gtts(text, output_filename=output_filename)

    def get_audio_duration(self, audio_path: str) -> float:
        try:
            from moviepy.editor import AudioFileClip
            with AudioFileClip(audio_path) as clip:
                return clip.duration
        except Exception as e:
            logger.error(f"Error getting audio duration: {e}")
            return 0.0
