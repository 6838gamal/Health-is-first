"""
Unit tests for Gemini Service
Run: pytest tests/unit/test_gemini_service.py -v
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestGeminiService:
    def test_extract_json_from_markdown(self):
        from app.services.ai.gemini_service import GeminiService
        service = GeminiService.__new__(GeminiService)

        text = '```json\n{"key": "value"}\n```'
        result = service._extract_json(text)
        assert result == '{"key": "value"}'

    def test_extract_json_plain(self):
        from app.services.ai.gemini_service import GeminiService
        service = GeminiService.__new__(GeminiService)

        text = '{"key": "value"}'
        result = service._extract_json(text)
        assert result == '{"key": "value"}'

    @patch("google.generativeai.GenerativeModel")
    def test_analyze_trend(self, mock_model):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "virality_score": 8.0,
            "quality_score": 7.5,
            "category": "nutrition",
            "is_safe": True,
            "safety_notes": "Safe",
            "target_audience": "Adults",
            "content_angle": "Educational",
            "estimated_engagement": "high",
            "keywords": ["health", "nutrition"],
        })
        mock_model.return_value.generate_content.return_value = mock_response

        from app.services.ai.gemini_service import GeminiService
        with patch("google.generativeai.configure"):
            service = GeminiService()
            service.model = mock_model.return_value

            result = service.analyze_trend("Benefits of Vitamin D", "Studies show...")
            assert result["virality_score"] == 8.0
            assert result["is_safe"] is True
            assert result["category"] == "nutrition"


class TestThumbnailGenerator:
    def test_hex_to_rgb(self):
        from app.services.thumbnail.thumbnail_generator import ThumbnailGenerator
        gen = ThumbnailGenerator.__new__(ThumbnailGenerator)
        assert gen._hex_to_rgb("#e94560") == (233, 69, 96)
        assert gen._hex_to_rgb("#1a1a2e") == (26, 26, 46)
        assert gen._hex_to_rgb("ffffff") == (255, 255, 255)
