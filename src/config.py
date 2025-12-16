import os

class Config:
    # Default constants
    DEFAULT_MODEL = "labs-devstral-small-2512" 
    
    # Backend configurations
    BACKENDS = {
        "mistral_api": {
            "type": "openai_compatible",
            "base_url": "https://api.mistral.ai/v1",
            "api_key_env": "MISTRAL_API_KEY",
            "default_model": "mistral-small-latest" # Fallback or specific
        },
        "ollama": {
            "type": "openai_compatible",
            "base_url": "http://localhost:11434/v1",
            "api_key": "ollama", # Ollama doesn't care, but header is often required by libs
            "default_model": DEFAULT_MODEL
        },
        "lm_studio": {
            "type": "openai_compatible",
            "base_url": "http://localhost:1234/v1",
            "api_key": "lm-studio",
            "default_model": "local-model" # LM Studio often ignores model name or uses loaded one
        }
    }

    def __init__(self):
        self.active_backend = "mistral_api" # Default backend
        self.active_model = self.BACKENDS["ollama"]["default_model"]
        self.mode = "build" # 'build' or 'run'

    def get_active_backend_config(self):
        return self.BACKENDS[self.active_backend]

    def set_backend(self, backend_name):
        if backend_name in self.BACKENDS:
            self.active_backend = backend_name
            # Update generic model if specific one exists, else keep current or use default
            # For now, just reset to backend default
            self.active_model = self.BACKENDS[backend_name]["default_model"]
            return True
        return False
        
    def set_model(self, model_name):
        self.active_model = model_name

    def set_mistral_key(self, key):
        self.BACKENDS["mistral_api"]["api_key"] = key
        # Also set env var for current session if needed by backend init
        os.environ["MISTRAL_API_KEY"] = key

GLOBAL_CONFIG = Config()
