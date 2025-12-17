# ALMANAC 📘
**A**utomated **L**earning **M**anagement **A**nd **N**otebook **A**gent **C**reator

> *An almanac is traditionally a book containing datasets, forecasts, and tables used to predict the future. Since this agent uses AI to manage Notebooks—our modern datasets and experiments—it is the modern evolution of the classic Almanac.*

Almanac is a premium terminal-based agent designed to autonomously create, edit, run, and manage Jupyter Notebooks. It features a robust TUI (Terminal User Interface) inspired by high-end CLI tools, powered by **Devstral Small 2** (via Ollama) by default.

## Features

-   **Autonomous Notebook Management**: Create, edit, and read Jupyter notebooks through natural language.
-   **Dual Modes**:
    -   **Build Mode**: Safe. Can only write code and create files. Execution is blocked.
    -   **Run Mode**: Powerful. Can execute notebook cells and read the outputs back into the agent's context.
-   **Beautiful TUI**:
    -   Full-screen flicker-free interface.
    -   Boxed input area with "Gemini CLI" styling.
    -   Persistent status footer (Mode, Backend, Model, Memory Usage).
    -   Rich markdown and syntax highlighting.
-   **Backend Agnostic**: Supports **Ollama**, **LM Studio**, **Mistral API**, **Claude Code CLI**, **OpenAI Codex CLI**, and **Google Gemini CLI**.

## Quick Start

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Almanac**:
    ```bash
    python main.py
    ```

## Slash Commands

-   `/mode [build|run]`: Switch between Build (default) and Run modes.
-   `/model [name]`: Change the underlying LLM (default: `labs-devstral-small-2512`).
-   `/backend [ollama|lm_studio|mistral_api|claude_code|codex|gemini]`: Switch the LLM provider.
-   `/clear`: Clear the screen and history.
-   `/quit`: Exit the agent (or double-press `Ctrl+C`).

## Requirements

-   Python 3.10+
-   Ollama (recommended) or LM Studio running locally.
-   Models: Devstral Small 2 (recommended) or Mistral/Llama variants.

## CLI Backends (Claude Code & Codex)

⚠️ **IMPORTANT USAGE WARNING** ⚠️

Almanac now supports **Claude Code CLI** and **OpenAI Codex CLI** as backends. These backends allow you to use your Claude Pro/Team or ChatGPT Plus/Pro subscriptions instead of running local models.

### Why Use CLI Backends?

-   **No Local GPU Required**: Use powerful cloud models without local hardware.
-   **Access to Latest Models**: Get access to Claude Sonnet 4.5, GPT-5 Codex, and other frontier models.
-   **Perfect for CI/CD**: Use your subscription credits in automated workflows.

### ⚠️ Critical Warning

**These backends will consume your subscription usage VERY QUICKLY** during automated operations. Each agent step makes a CLI call, and complex tasks can consume significant usage in minutes.

**These backends are recommended ONLY for CLI-based workflows**, not for API usage. This ensures you don't hit rate limits on both your CLI subscription AND your API keys.

### Setup

#### Claude Code CLI Backend

1.  **Install Claude Code CLI**:
    ```bash
    npm install -g @anthropic/claude-code
    ```

2.  **Login with your Claude Pro/Team account**:
    ```bash
    claude login
    ```

3.  **Switch to Claude Code backend in Almanac**:
    ```bash
    /backend claude_code
    ```

#### OpenAI Codex CLI Backend

1.  **Install Codex CLI**:
    ```bash
    npm install -g @openai/codex
    ```

2.  **Login with your ChatGPT Plus/Pro/Business account**:
    Follow the authentication prompts from Codex CLI.

3.  **Switch to Codex backend in Almanac**:
    ```bash
    /backend codex
    ```

#### Google Gemini CLI Backend

1.  **Install Gemini CLI**:
    ```bash
    npm install -g @google/gemini-cli
    ```

2.  **Authenticate with Google AI Studio**:
    Follow the Gemini CLI authentication flow (typically opens browser).

3.  **Switch to Gemini backend in Almanac**:
    ```bash
    /backend gemini
    ```

### Configuration

All CLI backends come with sensible defaults:

-   **Claude Code**: Uses `claude-sonnet-4-5` model with tools: `Read,Write,Edit,Bash,Glob,Grep`
-   **Codex**: Uses `gpt-5-codex` model with `--full-auto` and `--sandbox danger-full-access` for full automation.
-   **Gemini**: Uses `gemini-pro-2.5` model with `--yolo` mode enabled for autonomous operation.

You can customize these in `src/config.py` if needed.
