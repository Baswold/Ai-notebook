import httpx
import os
import json
from .config import GLOBAL_CONFIG

class LLMBackend:
    async def chat_completion(self, messages, system_prompt=None):
        raise NotImplementedError

class OpenAICompatibleBackend(LLMBackend):
    def __init__(self, config_dict):
        self.base_url = config_dict["base_url"]
        self.api_key = config_dict.get("api_key")
        
        # If api_key is not set in config, check if it expects an env var
        if not self.api_key and "api_key_env" in config_dict:
            self.api_key = os.environ.get(config_dict["api_key_env"])
            
        if not self.api_key:
            self.api_key = "dummy" # Some local servers need a non-empty string

    async def chat_completion(self, messages, tools=None):
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": GLOBAL_CONFIG.active_model,
            "messages": messages,
            "stream": False # For now, no streaming to keep tool logic simple
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.ConnectError:
                return {
                    "error": f"Connection failed to {self.base_url}", 
                    "details": "Is the backend service (Ollama/LM Studio) running? Please check your connection."
                }
            except httpx.HTTPError as e:
                return {"error": str(e), "details": response.text if 'response' in locals() else "No response"}

def get_backend():
    config = GLOBAL_CONFIG.get_active_backend_config()
    if config["type"] == "openai_compatible":
        return OpenAICompatibleBackend(config)
    raise ValueError(f"Unknown backend type: {config['type']}")
