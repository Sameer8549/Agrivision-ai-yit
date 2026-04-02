"""
CropSentinel AI  -  utils/llm_router.py
3-tier LLM routing: Mixtral (Tier 2) -> Groq (Tier 1) -> Ollama (Tier 3) -> Hardcoded fallback.
"""

import json
import logging
import os
import re

import requests
from dotenv import load_dotenv
from groq import Groq

from utils.prompt_builder import PromptBuilder

load_dotenv()

logger = logging.getLogger("LLMRouter")


class MultiLLMRouter:
    """
    Routes inference requests to the most capable available LLM tier.

    Tier 2 (Mixtral)   -  HIGH severity / confidence > 85%
    Tier 1 (Groq)      -  Standard; also fallback for Tier 2 failures
    Tier 3 (Ollama)    -  Offline fallback
    Hardcoded           -  Last resort when all LLMs unavailable
    """

    def __init__(self):
        self.groq_key    = os.getenv("GROQ_API_KEY", "")
        self.mistral_key = os.getenv("MISTRAL_API_KEY", "")

        self.prompt_builder  = PromptBuilder()
        self.groq_model      = "llama-3.1-8b-instant"
        self.mistral_model   = "mistral-large-latest"
        self.ollama_model    = "llama3"
        self.ollama_url      = "http://localhost:11434/api/generate"

        logger.info(
            f"LLMRouter initialised  -  "
            f"Groq: {'✓' if self.groq_key else '✗'} | "
            f"Mistral: {'✓' if self.mistral_key else '✗'}"
        )

    def route(
        self,
        crop: str,
        disease: str,
        confidence: float,
        severity: str,
        geo: dict,
        top3: list,
    ) -> tuple[dict, str]:
        """
        Select the best LLM, build the right prompt, parse the response.

        Returns
        -------
        (recommendation_dict, tier_label_str)
        """
        prompt = self.prompt_builder.build_tier1(
            crop, disease, confidence, severity, geo
        )
        result = self._try_groq(prompt)
        if result:
            return result, "Groq Tier 1  -  llama-3.1-8b-instant"

        prompt = self.prompt_builder.build_tier3(crop, disease, severity)
        result = self._try_ollama(prompt)
        if result:
            return result, "Ollama Tier 2  -  llama3 (offline)"
            
        return self._fallback(), "Error: LLMs unavailable"

    def _try_groq(self, prompt: str) -> dict | None:
        try:
            if not self.groq_key or self.groq_key == "your_groq_api_key_here":
                logger.debug("Groq API key not configured  -  skipping.")
                return None
            client = Groq(api_key=self.groq_key)
            response = client.chat.completions.create(
                model=self.groq_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3,
                timeout=10,
            )
            return self._parse(response.choices[0].message.content)
        except Exception as e:
            logger.warning(f"Groq failed: {e}")
            return None

    def _try_mixtral(self, prompt: str) -> dict | None:
        try:
            if not self.mistral_key or self.mistral_key == "your_mistral_api_key_here":
                logger.debug("Mistral API key not configured  -  skipping.")
                return None
            headers = {
                "Authorization": f"Bearer {self.mistral_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": self.mistral_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1500,
                "temperature": 0.2
            }
            resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=data, timeout=30)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return self._parse(content)
        except Exception as e:
            logger.warning(f"Mixtral failed: {e}")
            return None

    def _try_ollama(self, prompt: str) -> dict | None:
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model":  self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=30,
            )
            response.raise_for_status()
            text = response.json().get("response", "")
            return self._parse(text)
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")
            return None

    def _parse(self, text: str) -> dict | None:
        """
        Extract and parse the first valid JSON object from LLM output.
        """
        try:
            if not text:
                return None

            text = text.strip()
            text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"```\s*", "", text)

            start = text.find("{")
            end   = text.rfind("}") + 1
            if start == -1 or end == 0:
                return None

            json_str = text[start:end]
            parsed = json.loads(json_str)

            return {
                "action_plan": parsed.get("action_plan", ["Error generating structured steps."]),
                "est_recovery": parsed.get("est_recovery", "Unknown recovery timeline."),
                "preventive_note": parsed.get("preventive_note", "No preventive measures generated."),
            }

        except Exception as e:
            return None

    def _fallback(self) -> dict:
        return {
            "action_plan": ["System Offline: LLM Generation Failed."],
            "est_recovery": "System Offline: LLM Generation Failed.",
            "preventive_note": "System Offline: LLM Generation Failed.",
        }

    @property
    def groq_available(self) -> bool:
        return bool(self.groq_key and self.groq_key != "your_groq_api_key_here")

    @property
    def mistral_available(self) -> bool:
        return bool(self.mistral_key and self.mistral_key != "your_mistral_api_key_here")

    def ollama_available(self) -> bool:
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False
