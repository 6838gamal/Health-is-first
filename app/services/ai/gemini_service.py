import google.generativeai as genai
import json
import time
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.8,
            top_p=0.95,
            max_output_tokens=4096,
        )

    def _generate(self, prompt: str, expect_json: bool = False) -> str:
        start = time.time()
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
            )
            text = response.text.strip()
            if expect_json:
                text = self._extract_json(text)
            logger.info(f"Gemini call completed in {(time.time()-start)*1000:.0f}ms")
            return text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def _extract_json(self, text: str) -> str:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        return text

    def analyze_trend(self, trend_title: str, trend_summary: str) -> dict:
        prompt = f"""
أنت محلل محتوى صحي خبير. حلّل هذا الترند الصحي وقدّم تقييماً دقيقاً.

الترند: {trend_title}
الملخص: {trend_summary}

أعد JSON بالتنسيق التالي فقط:
{{
  "virality_score": <0-10>,
  "quality_score": <0-10>,
  "category": "<nutrition|fitness|mental_health|disease_prevention|lifestyle|medical>",
  "is_safe": <true|false>,
  "safety_notes": "<ملاحظات السلامة>",
  "target_audience": "<الجمهور المستهدف>",
  "content_angle": "<زاوية المحتوى المقترحة>",
  "estimated_engagement": "<low|medium|high|viral>",
  "keywords": ["<كلمة1>", "<كلمة2>", "<كلمة3>"]
}}
"""
        result = self._generate(prompt, expect_json=True)
        return json.loads(result)

    def generate_content_idea(self, trend_title: str, analysis: dict) -> dict:
        prompt = f"""
أنت منشئ محتوى YouTube Shorts متخصص في الصحة. 
اصنع فكرة فيديو جذابة بناءً على هذا الترند.

الترند: {trend_title}
التحليل: {json.dumps(analysis, ensure_ascii=False)}

القواعد:
- لا تدعي علاجات أو معلومات طبية خطيرة
- الهدف 30-60 ثانية
- محتوى عربي جذاب
- يعتمد على الحقائق العلمية

أعد JSON فقط:
{{
  "title": "<عنوان جذاب>",
  "hook": "<جملة افتتاحية صادمة - 5 ثوان>",
  "angle": "<الزاوية الرئيسية للفيديو>",
  "key_points": ["<نقطة1>", "<نقطة2>", "<نقطة3>"],
  "target_keywords": ["<كلمة1>", "<كلمة2>"],
  "estimated_virality": <0-10>
}}
"""
        result = self._generate(prompt, expect_json=True)
        return json.loads(result)

    def generate_script(self, idea: dict) -> dict:
        prompt = f"""
أنت كاتب سكريبت محترف لـ YouTube Shorts صحي. 
اكتب سكريبت كامل ومتكامل.

الفكرة: {json.dumps(idea, ensure_ascii=False)}

قواعد السكريبت:
- Hook: جملة صادمة تُوقف التمرير (5 ثوان)
- Body: معلومات قيمة سريعة (20-40 ثانية)
- CTA: دعوة للتفاعل واضحة (5 ثوان)
- إجمالي: 30-60 ثانية
- لغة: عربية بسيطة ومفهومة
- لا ادعاءات طبية خطيرة
- معلومات علمية موثوقة

أعد JSON فقط:
{{
  "title": "<عنوان YouTube جذاب>",
  "hook": "<نص الـ Hook>",
  "body": "<نص الجزء الرئيسي>",
  "cta": "<نص الـ CTA>",
  "full_script": "<السكريبت كاملاً متدفقاً>",
  "description": "<وصف YouTube مناسب>",
  "hashtags": "#صحة #health #shorts #<هاشتاق1> #<هاشتاق2>",
  "estimated_duration": <عدد الثوان>,
  "word_count": <عدد الكلمات>
}}
"""
        result = self._generate(prompt, expect_json=True)
        return json.loads(result)

    def safety_check(self, script: str) -> dict:
        prompt = f"""
أنت مدقق طبي ومحقق في صحة المعلومات الصحية.
راجع هذا السكريبت وتحقق من سلامته.

السكريبت:
{script}

تحقق من:
1. لا ادعاءات علاجية خطيرة
2. لا تشجيع على إيقاف الأدوية
3. لا معلومات طبية مضللة
4. المعلومات علمية ومعقولة
5. لا يضر بالصحة العامة

أعد JSON فقط:
{{
  "is_safe": <true|false>,
  "risk_level": "<low|medium|high>",
  "issues": ["<مشكلة1 إن وجدت>"],
  "suggestions": ["<اقتراح تحسين1>"],
  "approved": <true|false>,
  "notes": "<ملاحظات عامة>"
}}
"""
        result = self._generate(prompt, expect_json=True)
        return json.loads(result)

    def generate_thumbnail_prompt(self, title: str, hook: str) -> dict:
        prompt = f"""
أنت مصمم جرافيك متخصص في Thumbnails يوتيوب.
اقترح تصميم Thumbnail جذاب لهذا الفيديو.

العنوان: {title}
الهوك: {hook}

أعد JSON فقط:
{{
  "main_text": "<النص الرئيسي 2-4 كلمات>",
  "sub_text": "<نص ثانوي>",
  "background_theme": "<dark|light|gradient|health_green>",
  "primary_color": "<hex color>",
  "accent_color": "<hex color>",
  "emoji": "<إيموجي مناسب>",
  "style": "<bold|clean|dramatic|medical>"
}}
"""
        result = self._generate(prompt, expect_json=True)
        return json.loads(result)
