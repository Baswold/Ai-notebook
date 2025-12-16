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
-   **Backend Agnostic**: Supports **Ollama**, **LM Studio**, and **Mistral API**.

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
-   `/backend [ollama|lm_studio|mistral_api]`: Switch the LLM provider.
-   `/clear`: Clear the screen and history.
-   `/quit`: Exit the agent (or double-press `Ctrl+C`).

## Requirements

-   Python 3.10+
-   Ollama (recommended) or LM Studio running locally.
-   Models: Devstral Small 2 (recommended) or Mistral/Llama variants.
