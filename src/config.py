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
        },
        "gemini": {
            "type": "gemini_cli",
            "default_model": "gemini-pro-2.5",
            "yolo_mode": True,
            "usage_warning": """
⚠️  WARNING: GOOGLE GEMINI CLI BACKEND ⚠️
This backend uses your Google AI Studio / Gemini API quota.
It will consume usage from your quota VERY QUICKLY during automated operations.
Make sure you understand the implications before using this in CI/CD or automated workflows.

Requirements:
- Gemini CLI must be installed: npm install -g @google/gemini-cli
- You must be authenticated with Google AI Studio
- YOLO mode (--yolo) is enabled by default for autonomous operation
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

    def get_model_options_for_backend(self):
        """Get model options based on the active backend"""
        backend_models = {
            "ollama": [
                ("labs-devstral-small-2512", "Devstral Small 2"),
                ("mistral-small-latest", "Mistral Small"),
                ("llama3", "Llama 3"),
                ("qwen2.5-coder", "Qwen 2.5 Coder"),
            ],
            "lm_studio": [
                ("local-model", "Local Model"),
                ("labs-devstral-small-2512", "Devstral Small 2"),
            ],
            "mistral_api": [
                ("mistral-small-latest", "Mistral Small"),
                ("mistral-medium-latest", "Mistral Medium"),
                ("mistral-large-latest", "Mistral Large"),
            ],
            "claude_code": [
                ("claude-sonnet-4-5", "Claude Sonnet 4.5"),
                ("claude-opus-4-5", "Claude Opus 4.5"),
                ("claude-sonnet-3-7", "Claude Sonnet 3.7"),
            ],
            "codex": [
                ("gpt-5-codex", "GPT-5 Codex"),
                ("gpt-5-codex-mini", "GPT-5 Codex Mini"),
                ("gpt-5", "GPT-5"),
            ],
            "gemini": [
                ("gemini-pro-2.5", "Gemini Pro 2.5"),
                ("gemini-flash-2.5", "Gemini Flash 2.5"),
                ("gemini-pro-1.5", "Gemini Pro 1.5"),
            ],
        }

        # Get models for current backend, or default to Ollama models
        models = backend_models.get(self.active_backend, backend_models["ollama"])

        # Ensure current model is in list if not already
        current = self.active_model
        if not any(m[0] == current for m in models):
            models.insert(0, (current, current + " (Current)"))

        return models

GLOBAL_CONFIG = Config()
