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
        },
        "claude_code": {
            "type": "claude_code_cli",
            "default_model": "claude-sonnet-4-5",
            "allowed_tools": "Read,Write,Edit,Bash,Glob,Grep",
            "skip_permissions": True,
            "usage_warning": """
⚠️  WARNING: CLAUDE CODE CLI BACKEND ⚠️
This backend uses your Claude Pro/Team subscription through the Claude Code CLI.
It will consume usage from your subscription VERY QUICKLY during automated operations.
Make sure you understand the implications before using this in CI/CD or automated workflows.

Requirements:
- Claude Code CLI must be installed: npm install -g @anthropic/claude-code
- You must be logged in with a Claude Pro/Team account: claude login
- This backend is recommended ONLY for CLI usage, not API calls
"""
        },
        "codex": {
            "type": "codex_cli",
            "default_model": "gpt-5-codex",
            "full_auto": True,
            "sandbox": "danger-full-access",
            "usage_warning": """
⚠️  WARNING: OPENAI CODEX CLI BACKEND ⚠️
This backend uses your ChatGPT Plus/Pro subscription through the Codex CLI.
It will consume usage from your subscription VERY QUICKLY during automated operations.
Make sure you understand the implications before using this in CI/CD or automated workflows.

Requirements:
- Codex CLI must be installed: npm install -g @openai/codex
- You must be logged in with ChatGPT Plus/Pro/Business account
- This backend is recommended ONLY for CLI usage, not API calls
"""
        }
    }

    def __init__(self):
        self.active_backend = "ollama" # Default backend (changed from mistral_api)
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
