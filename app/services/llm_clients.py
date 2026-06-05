import os
import json
import httpx
import asyncio
import logging
from app.config import settings

logger = logging.getLogger("app")

class GrokClient:
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.x.ai/v1/chat/completions"

    async def generate(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant that summarizes legal and formal documents for narration."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()


class MedhaClient:
    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name

    async def generate(self, transcript: str, system_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            "max_tokens": 256,
            "temperature": 0.2,
            "stream": True
        }

        full_content = []
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", self.base_url, headers=headers, json=data) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                content = chunk["choices"][0]["delta"].get("content", "")
                                if content:
                                    full_content.append(content)
                            except Exception:
                                pass
            return "".join(full_content).strip()
        except Exception as e:
            logger.error(f"MedhaClient Error: {e}")
            raise RuntimeError(f"Failed to generate summary from Medha: {e}")


