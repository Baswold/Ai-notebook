# Completeness Loop - Autonomous Coding Agent

A production-grade autonomous coding agent system that uses multi-agent verification to build complete, production-ready software from specifications.

## Features

✨ **Multi-Agent Architecture**
- **Agent 1**: Implementation agent that writes code using available tools
- **Agent 2**: Review agent that verifies completeness against the specification  
- **Agent 3**: Alignment checker that prevents drift from the original idea
- **AI-Driven Completion**: Smart completion detection with harsh criteria to prevent early stopping

🔒 **Security & Control**
- Complete workspace sandboxing - agents cannot access files outside their workspace
- Tool execution restricted to workspace directory only
- Block access attempts to system directories

🚀 **Multiple LLM Backends**
- **Anthropic Claude** (recommended for complex tasks)
- **OpenAI** (gpt-4o, gpt-4o-mini, etc.)
- **Mistral** (fast, affordable Devstral models)
- **Local options**: Ollama, LM Studio, MLX (native Apple Silicon)
- **Custom APIs**: OpenAI-compatible endpoint support

📦 **Production Features**
- Persistent progress tracking with `.completeness_state.json`
- Per-agent memories stored in `workspace/memories/` so lessons survive context refreshes
- Git-based version control with automatic commits
- Token usage tracking and reporting
- Flexible workspace configuration
- Support for existing codebases

## Installation

### Via pip (Recommended)

```bash
pip install completeness-loop
completeness-loop
```

### From Source

```bash
git clone https://github.com/Baswold/Completeness-agent-loop-harness.git
cd Completeness-agent-loop-harness
pip install -e .
completeness-loop
```

## Quick Start

### 1. Set Up Your LLM Backend

**For Anthropic:**
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

**For OpenAI:**
```bash
export OPENAI_API_KEY="your-api-key"
```

### 2. Create Your Project Idea

```bash
# Create idea.md with your project specification
echo "Build a REST API with FastAPI..." > idea.md
```

### 3. Start the Agent

```bash
completeness-loop
```

## Supported Backends

- **Anthropic Claude** (claude-3-5-sonnet-20241022 recommended)
- **OpenAI** (gpt-4o, gpt-4o-mini)
- **Mistral** (devstral-small-2505)
- **Ollama** (local)
- **LM Studio** (local with GUI)
- **MLX** (Apple Silicon native)

## Key Improvements (v1.0.0)

- ✨ Anthropic Claude backend with full tool support
- 🔒 Enhanced sandbox: prevents execution outside workspace
- 📦 Pip-installable package: `pip install completeness-loop`
- 🤖 Agent 3 alignment checker: detects and corrects drift from spec
- ✅ Smarter completion logic: AI-driven with harsh criteria
- 🎯 Flexible workspace folders: use any directory name
- 📝 Persistent TODOs: survives context refreshes
- 📊 Better CLI summaries: see what agents accomplished

## Commands

```
go          Start a new session
resume      Continue from last pause
status      Show progress
history     View completeness scores
settings    Change configuration  
backends    List available backends
help        Show commands
```

## Architecture

- **Workspace Sandboxing**: Agents cannot access files outside their workspace
- **Multi-Agent Verification**: Prevents premature completion and scope creep
- **Persistent State**: Resume sessions anytime
- **Git Tracking**: Full version history

For more details, see the full documentation or run `completeness-loop` to get started.
