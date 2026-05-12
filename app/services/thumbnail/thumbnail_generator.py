import logging
import uuid
from pathlib import Path
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class ThumbnailGenerator:
    def __init__(self):
        self.output_dir = Path(settings.THUMBNAILS_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.width = 1280
        self.height = 720

    def generate_thumbnail(
        self,
        title_text: str,
        sub_text: str = "",
        bg_color: str = "#1a1a2e",
        accent_color: str = "#e94560",
        text_color: str = "#ffffff",
        emoji: str = "💚",
        output_filename: Optional[str] = None,
    ) -> str:
        try:
            from PIL import Image, ImageDraw, ImageFont
            import textwrap

            img = Image.new("RGB", (self.width, self.height), self._hex_to_rgb(bg_color))
            draw = ImageDraw.Draw(img)

            # Gradient overlay
            for y in range(self.height):
                alpha = int(50 * (1 - y / self.height))
                draw.line([(0, y), (self.width, y)], fill=(255, 255, 255, alpha))

            # Accent bar
            draw.rectangle([(0, 0), (10, self.height)], fill=self._hex_to_rgb(accent_color))
            draw.rectangle([(0, self.height - 10), (self.width, self.height)], fill=self._hex_to_rgb(accent_color))

            # Channel name
            draw.text((60, 40), "Health is First | الصحة أولاً", fill=self._hex_to_rgb(accent_color))

            # Emoji
            draw.text((self.width // 2 - 30, 120), emoji, fill=self._hex_to_rgb(text_color))

            # Main title
            wrapped = textwrap.wrap(title_text, width=25)
            y_pos = 220
            for line in wrapped[:3]:
                text_width = len(line) * 32
                x_pos = (self.width - text_width) // 2
                draw.text((x_pos, y_pos), line, fill=self._hex_to_rgb(text_color))
                y_pos += 70

            # Sub text
            if sub_text:
                draw.text((60, self.height - 100), sub_text[:50], fill=self._hex_to_rgb(accent_color))

            filename = output_filename or f"thumbnail_{uuid.uuid4()}.jpg"
            output_path = self.output_dir / filename
            img.save(str(output_path), "JPEG", quality=95)
            logger.info(f"Thumbnail generated: {output_path}")
            return str(output_path)

        except ImportError:
            logger.error("Pillow not installed. Cannot generate thumbnail.")
            raise RuntimeError("Pillow required for thumbnail generation")

    def generate_from_prompt_data(self, prompt_data: dict, script_title: str) -> str:
        theme_colors = {
            "dark": {"bg": "#1a1a2e", "accent": "#e94560"},
            "light": {"bg": "#f0f4f8", "accent": "#2d6a4f"},
            "gradient": {"bg": "#0d1b2a", "accent": "#f4a261"},
            "health_green": {"bg": "#1b4332", "accent": "#52b788"},
        }
        theme = prompt_data.get("background_theme", "dark")
        colors = theme_colors.get(theme, theme_colors["dark"])

        return self.generate_thumbnail(
            title_text=prompt_data.get("main_text", script_title),
            sub_text=prompt_data.get("sub_text", ""),
            bg_color=prompt_data.get("primary_color", colors["bg"]),
            accent_color=prompt_data.get("accent_color", colors["accent"]),
            emoji=prompt_data.get("emoji", "💚"),
        )

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
