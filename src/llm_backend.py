import httpx
import os
import json
import subprocess
import asyncio
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

class ClaudeCodeCLIBackend(LLMBackend):
    """
    Backend that uses Claude Code CLI in headless mode.

    WARNING: This backend uses your Claude Pro/Team subscription through the Claude Code CLI.
    It will consume usage from your subscription VERY QUICKLY during automated operations.
    Make sure you understand the implications before using this in CI/CD or automated workflows.
    """
    def __init__(self, config_dict):
        self.allowed_tools = config_dict.get("allowed_tools", "Read,Write,Edit,Bash,Glob,Grep")
        self.skip_permissions = config_dict.get("skip_permissions", True)

    async def chat_completion(self, messages, tools=None):
        """
        Execute Claude Code CLI with the conversation history.
        Returns response in OpenAI-compatible format.
        """
        try:
            # Build the prompt from messages
            prompt = self._build_prompt(messages, tools)

            # Build Claude Code CLI command
            cmd = ["claude", "-p", prompt, "--allowedTools", self.allowed_tools]

            if self.skip_permissions:
                cmd.append("--dangerously-skip-permissions")

            # Execute Claude Code CLI
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return {
                    "error": f"Claude Code CLI failed with exit code {result.returncode}",
                    "details": result.stderr
                }

            # Parse output and convert to OpenAI format
            return self._parse_claude_output(result.stdout, tools)

        except subprocess.TimeoutExpired:
            return {"error": "Claude Code CLI timed out after 120 seconds"}
        except FileNotFoundError:
            return {
                "error": "Claude Code CLI not found",
                "details": "Please install Claude Code CLI: npm install -g @anthropic/claude-code"
            }
        except Exception as e:
            return {"error": f"Claude Code CLI error: {str(e)}"}

    def _build_prompt(self, messages, tools=None):
        """Build a comprehensive prompt from the message history."""
        parts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"SYSTEM INSTRUCTIONS:\n{content}\n")
            elif role == "user":
                parts.append(f"USER REQUEST:\n{content}\n")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    # Format tool calls
                    tool_calls_str = "\n".join([
                        f"- {tc['function']['name']}({tc['function']['arguments']})"
                        for tc in msg["tool_calls"]
                    ])
                    parts.append(f"PREVIOUS ACTIONS:\n{tool_calls_str}\n")
                if content:
                    parts.append(f"ASSISTANT:\n{content}\n")
            elif role == "tool":
                parts.append(f"TOOL RESULT:\n{content}\n")

        # Add tool definitions if provided
        if tools:
            tool_descriptions = "\n".join([
                f"- {tool['function']['name']}: {tool['function']['description']}"
                for tool in tools
            ])
            parts.append(f"\nAVAILABLE TOOLS:\n{tool_descriptions}\n")
            parts.append("\nIMPORTANT: You must respond with tool calls in this JSON format:")
            parts.append('{"tool_calls": [{"function": {"name": "tool_name", "arguments": "{...}"}}]}')

        return "\n".join(parts)

    def _parse_claude_output(self, output, tools=None):
        """Parse Claude Code CLI output into OpenAI format."""
        # Try to detect if Claude returned tool calls
        tool_calls = None
        content = output.strip()

        # Look for JSON tool call format in the output
        if tools and '{"tool_calls":' in content:
            try:
                # Extract JSON from output
                import re
                json_match = re.search(r'\{.*"tool_calls".*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if "tool_calls" in parsed:
                        # Convert to OpenAI format
                        tool_calls = []
                        for idx, tc in enumerate(parsed["tool_calls"]):
                            tool_calls.append({
                                "id": f"call_{idx}",
                                "type": "function",
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": tc["function"]["arguments"]
                                }
                            })
                        # Remove the JSON from content
                        content = content.replace(json_match.group(0), "").strip()
            except json.JSONDecodeError:
                pass

        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": content if content else None,
                    "tool_calls": tool_calls
                },
                "finish_reason": "stop"
            }]
        }

class GeminiCLIBackend(LLMBackend):
    """
    Backend that uses Google Gemini CLI in headless mode.

    WARNING: This backend uses your Google AI Studio / Gemini API quota.
    It will consume usage from your quota VERY QUICKLY during automated operations.
    Make sure you understand the implications before using this in CI/CD or automated workflows.
    """
    def __init__(self, config_dict):
        self.yolo_mode = config_dict.get("yolo_mode", True)
        self.model = config_dict.get("default_model", "gemini-pro-2.5")

    async def chat_completion(self, messages, tools=None):
        """
        Execute Google Gemini CLI with the conversation history.
        Returns response in OpenAI-compatible format.
        """
        try:
            # Build the prompt from messages
            prompt = self._build_prompt(messages, tools)

            # Build Gemini CLI command
            cmd = ["gemini", "-p", prompt, "--model", self.model, "--output-format", "json"]

            if self.yolo_mode:
                cmd.append("--yolo")

            # Execute Gemini CLI
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return {
                    "error": f"Gemini CLI failed with exit code {result.returncode}",
                    "details": result.stderr
                }

            # Parse output and convert to OpenAI format
            return self._parse_gemini_output(result.stdout, tools)

        except subprocess.TimeoutExpired:
            return {"error": "Gemini CLI timed out after 120 seconds"}
        except FileNotFoundError:
            return {
                "error": "Gemini CLI not found",
                "details": "Please install Gemini CLI: npm install -g @google/gemini-cli"
            }
        except Exception as e:
            return {"error": f"Gemini CLI error: {str(e)}"}

    def _build_prompt(self, messages, tools=None):
        """Build a comprehensive prompt from the message history."""
        parts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"SYSTEM INSTRUCTIONS:\n{content}\n")
            elif role == "user":
                parts.append(f"USER REQUEST:\n{content}\n")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    # Format tool calls
                    tool_calls_str = "\n".join([
                        f"- {tc['function']['name']}({tc['function']['arguments']})"
                        for tc in msg["tool_calls"]
                    ])
                    parts.append(f"PREVIOUS ACTIONS:\n{tool_calls_str}\n")
                if content:
                    parts.append(f"ASSISTANT:\n{content}\n")
            elif role == "tool":
                parts.append(f"TOOL RESULT:\n{content}\n")

        # Add tool definitions if provided
        if tools:
            tool_descriptions = "\n".join([
                f"- {tool['function']['name']}: {tool['function']['description']}"
                for tool in tools
            ])
            parts.append(f"\nAVAILABLE TOOLS:\n{tool_descriptions}\n")
            parts.append("\nIMPORTANT: You must respond with tool calls in this JSON format:")
            parts.append('{"tool_calls": [{"function": {"name": "tool_name", "arguments": "{...}"}}]}')

        return "\n".join(parts)

    def _parse_gemini_output(self, output, tools=None):
        """Parse Gemini CLI JSON output into OpenAI format."""
        try:
            # Gemini CLI with --output-format json returns JSON
            data = json.loads(output)

            # Extract content from Gemini response
            content = ""
            if isinstance(data, dict):
                # Try different possible keys
                content = data.get("text") or data.get("content") or data.get("response") or str(data)
            else:
                content = str(data)

            # Try to detect tool calls in the response
            tool_calls = None
            if tools and '{"tool_calls":' in content:
                try:
                    import re
                    json_match = re.search(r'\{.*"tool_calls".*\}', content, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        if "tool_calls" in parsed:
                            # Convert to OpenAI format
                            tool_calls = []
                            for idx, tc in enumerate(parsed["tool_calls"]):
                                tool_calls.append({
                                    "id": f"call_{idx}",
                                    "type": "function",
                                    "function": {
                                        "name": tc["function"]["name"],
                                        "arguments": tc["function"]["arguments"]
                                    }
                                })
                            # Remove the JSON from content
                            content = content.replace(json_match.group(0), "").strip()
                except json.JSONDecodeError:
                    pass

            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": content if content else None,
                        "tool_calls": tool_calls
                    },
                    "finish_reason": "stop"
                }]
            }
        except json.JSONDecodeError:
            # Fallback: return raw output
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": output.strip(),
                        "tool_calls": None
                    },
                    "finish_reason": "stop"
                }]
            }
        except Exception as e:
            # Fallback: return raw output
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": output.strip(),
                        "tool_calls": None
                    },
                    "finish_reason": "stop"
                }]
            }

class CodexCLIBackend(LLMBackend):
    """
    Backend that uses OpenAI Codex CLI in headless mode.

    WARNING: This backend uses your ChatGPT Plus/Pro subscription through the Codex CLI.
    It will consume usage from your subscription VERY QUICKLY during automated operations.
    Make sure you understand the implications before using this in CI/CD or automated workflows.
    """
    def __init__(self, config_dict):
        self.full_auto = config_dict.get("full_auto", True)
        self.sandbox = config_dict.get("sandbox", "danger-full-access")

    async def chat_completion(self, messages, tools=None):
        """
        Execute OpenAI Codex CLI with the conversation history.
        Returns response in OpenAI-compatible format.
        """
        try:
            # Build the prompt from messages
            prompt = self._build_prompt(messages, tools)

            # Build Codex CLI command
            cmd = ["codex", "exec", "-", "--json"]

            if self.full_auto:
                cmd.append("--full-auto")

            if self.sandbox:
                cmd.extend(["--sandbox", self.sandbox])

            # Execute Codex CLI with prompt via stdin
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return {
                    "error": f"Codex CLI failed with exit code {result.returncode}",
                    "details": result.stderr
                }

            # Parse output and convert to OpenAI format
            return self._parse_codex_output(result.stdout, tools)

        except subprocess.TimeoutExpired:
            return {"error": "Codex CLI timed out after 120 seconds"}
        except FileNotFoundError:
            return {
                "error": "Codex CLI not found",
                "details": "Please install Codex CLI: npm install -g @openai/codex"
            }
        except Exception as e:
            return {"error": f"Codex CLI error: {str(e)}"}

    def _build_prompt(self, messages, tools=None):
        """Build a comprehensive prompt from the message history."""
        parts = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                parts.append(f"SYSTEM INSTRUCTIONS:\n{content}\n")
            elif role == "user":
                parts.append(f"USER REQUEST:\n{content}\n")
            elif role == "assistant":
                if msg.get("tool_calls"):
                    # Format tool calls
                    tool_calls_str = "\n".join([
                        f"- {tc['function']['name']}({tc['function']['arguments']})"
                        for tc in msg["tool_calls"]
                    ])
                    parts.append(f"PREVIOUS ACTIONS:\n{tool_calls_str}\n")
                if content:
                    parts.append(f"ASSISTANT:\n{content}\n")
            elif role == "tool":
                parts.append(f"TOOL RESULT:\n{content}\n")

        # Add tool definitions if provided
        if tools:
            tool_descriptions = "\n".join([
                f"- {tool['function']['name']}: {tool['function']['description']}"
                for tool in tools
            ])
            parts.append(f"\nAVAILABLE TOOLS:\n{tool_descriptions}\n")
            parts.append("\nIMPORTANT: You must respond with tool calls in this JSON format:")
            parts.append('{"tool_calls": [{"function": {"name": "tool_name", "arguments": "{...}"}}]}')

        return "\n".join(parts)

    def _parse_codex_output(self, output, tools=None):
        """Parse Codex CLI JSON output into OpenAI format."""
        try:
            # Codex exec --json returns JSONL, we want the last complete message
            lines = output.strip().split("\n")

            # Find the last line that looks like a final message
            content = ""
            for line in reversed(lines):
                if line.strip():
                    try:
                        data = json.loads(line)
                        if data.get("type") == "message" or "content" in data:
                            content = data.get("content", line)
                            break
                    except json.JSONDecodeError:
                        content = line
                        break

            if not content:
                content = output.strip()

            # Try to detect tool calls in the response
            tool_calls = None
            if tools and '{"tool_calls":' in content:
                try:
                    import re
                    json_match = re.search(r'\{.*"tool_calls".*\}', content, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        if "tool_calls" in parsed:
                            # Convert to OpenAI format
                            tool_calls = []
                            for idx, tc in enumerate(parsed["tool_calls"]):
                                tool_calls.append({
                                    "id": f"call_{idx}",
                                    "type": "function",
                                    "function": {
                                        "name": tc["function"]["name"],
                                        "arguments": tc["function"]["arguments"]
                                    }
                                })
                            # Remove the JSON from content
                            content = content.replace(json_match.group(0), "").strip()
                except json.JSONDecodeError:
                    pass

            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": content if content else None,
                        "tool_calls": tool_calls
                    },
                    "finish_reason": "stop"
                }]
            }
        except Exception as e:
            # Fallback: return raw output
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": output.strip(),
                        "tool_calls": None
                    },
                    "finish_reason": "stop"
                }]
            }

def get_backend():
    config = GLOBAL_CONFIG.get_active_backend_config()
    backend_type = config["type"]

    if backend_type == "openai_compatible":
        return OpenAICompatibleBackend(config)
    elif backend_type == "claude_code_cli":
        return ClaudeCodeCLIBackend(config)
    elif backend_type == "codex_cli":
        return CodexCLIBackend(config)
    elif backend_type == "gemini_cli":
        return GeminiCLIBackend(config)
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")
