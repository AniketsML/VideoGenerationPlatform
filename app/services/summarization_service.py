import os
import logging
from pathlib import Path
from app.config import settings
from app.services.llm_clients import MedhaClient

logger = logging.getLogger("app")

class SummarizationService:
    def __init__(self):
        # Initialize Clients
        self.medha = self._init_medha()
        
        # Load external prompt
        self.prompt_template = self._load_prompt_template()

    def _init_medha(self) -> MedhaClient:
        api_url = os.getenv('MEDHA_API_URL') or getattr(settings, 'medha_api_url', None)
        api_key = os.getenv('MEDHA_API_KEY') or getattr(settings, 'medha_api_key', None)
        model = os.getenv('MEDHA_MODEL_NAME') or getattr(settings, 'medha_model_name', None)
        if api_url and api_key:
            return MedhaClient(api_url, api_key, model or "Medha")
        return None

    def _load_prompt_template(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / "summarization_prompt.txt"
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"SummarizationService: Failed to load prompt from {prompt_path}: {e}")
            return ""

    async def summarize_text(self, text: str, target_language: str = "Hindi", gender: str = "Female") -> str:
        """
        Coordinating service that uses the in-house Medha engine.
        """
        if not self.medha:
            raise RuntimeError("MedhaClient not configured (MEDHA_API_KEY / MEDHA_API_URL missing).")

        if not self.prompt_template:
            raise RuntimeError("Summarization prompt template missing.")

        # Separate the instruction guidelines for the system role from the transcript
        raw_system = self.prompt_template.format(
            target_language=target_language,
            text=""
        )
        # Strip off the source text and output directives at the bottom of the prompt template
        for suffix in ["SOURCE TEXT:\n", f"OUTPUT ONLY THE {target_language} SUMMARY:", "OUTPUT ONLY THE "]:
            if suffix in raw_system:
                raw_system = raw_system.split(suffix)[0]
        system_prompt = raw_system.strip()

        # Call Medha specifically for PDF tasks
        return await self.medha.generate(transcript=text, system_prompt=system_prompt)

