import logging
import os
import uuid
import subprocess
from pathlib import Path
from typing import List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class VideoRenderer:
    def __init__(self):
        self.output_dir = Path(settings.VIDEOS_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = settings.VIDEO_WIDTH
        self.height = settings.VIDEO_HEIGHT
        self.fps = settings.VIDEO_FPS

    def create_text_clip_ffmpeg(
        self,
        text: str,
        duration: float,
        font_size: int = 60,
        font_color: str = "white",
        bg_color: str = "#1a1a2e",
    ) -> str:
        output = str(self.output_dir / f"text_{uuid.uuid4()}.mp4")
        text_escaped = text.replace("'", "\\'").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={bg_color}:size={self.width}x{self.height}:duration={duration}:rate={self.fps}",
            "-vf", (
                f"drawtext=text='{text_escaped}'"
                f":fontsize={font_size}"
                f":fontcolor={font_color}"
                f":x=(w-text_w)/2:y=(h-text_h)/2"
                f":line_spacing=10"
                f":borderw=3:bordercolor=black"
                f":expansion=none"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            output,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")
        return output

    def add_audio_to_video(self, video_path: str, audio_path: str) -> str:
        output = str(self.output_dir / f"with_audio_{uuid.uuid4()}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            output,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg audio merge failed: {result.stderr}")
        return output

    def add_subtitles(self, video_path: str, subtitle_path: str) -> str:
        output = str(self.output_dir / f"subtitled_{uuid.uuid4()}.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles={subtitle_path}:force_style='FontSize=24,PrimaryColour=&Hffffff,Alignment=2'",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "copy",
            output,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"Subtitle error: {result.stderr}")
            return video_path
        return output

    def render_shorts_video(
        self,
        script_title: str,
        full_script: str,
        audio_path: str,
        subtitle_path: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> str:
        try:
            from moviepy.editor import (
                AudioFileClip, ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips
            )
            audio = AudioFileClip(audio_path)
            duration = audio.duration

            bg = ColorClip(size=(self.width, self.height), color=(26, 26, 46), duration=duration)

            title_clip = (
                TextClip(
                    script_title[:50],
                    fontsize=55,
                    color="white",
                    font="DejaVu-Sans-Bold",
                    size=(self.width - 100, None),
                    method="caption",
                )
                .set_position(("center", 200))
                .set_duration(duration)
            )

            channel_clip = (
                TextClip(
                    "Health is First | الصحة أولاً",
                    fontsize=30,
                    color="#e94560",
                    font="DejaVu-Sans",
                )
                .set_position(("center", self.height - 120))
                .set_duration(duration)
            )

            final = CompositeVideoClip([bg, title_clip, channel_clip])
            final = final.set_audio(audio)

            filename = output_filename or f"{uuid.uuid4()}.mp4"
            output_path = str(self.output_dir / filename)

            final.write_videofile(
                output_path,
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile="temp_audio.m4a",
                remove_temp=True,
                verbose=False,
                logger=None,
            )
            logger.info(f"Video rendered: {output_path}")
            return output_path

        except ImportError:
            logger.warning("MoviePy not available, using FFmpeg fallback")
            video_path = self.create_text_clip_ffmpeg(
                script_title, duration=30, font_size=55
            )
            return self.add_audio_to_video(video_path, audio_path)

    def get_video_info(self, video_path: str) -> dict:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,nb_frames",
            "-of", "json", video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            streams = data.get("streams", [{}])
            if streams:
                s = streams[0]
                return {
                    "width": s.get("width"),
                    "height": s.get("height"),
                    "duration": float(s.get("duration", 0)),
                    "frames": int(s.get("nb_frames", 0)),
                }
        return {}
