# CLI Backends Guide

This guide provides detailed information about using Claude Code CLI and OpenAI Codex CLI as backends for ALMANAC.

## Overview

ALMANAC now supports using Claude Code and Codex CLIs as backends, allowing you to leverage your Claude Pro/Team or ChatGPT Plus/Pro subscriptions instead of running local models or using APIs directly.

## ⚠️ Important Warnings

### Usage Consumption

**These backends will consume your subscription usage VERY QUICKLY.** Here's why:

- Each agent reasoning step makes a full CLI invocation
- Complex tasks can take 10-50 steps
- Each step processes the entire conversation history
- This can consume significant subscription credits in minutes

**Example**: Creating a complex notebook with data analysis, visualizations, and error handling could consume as much usage as 30-50 normal chat interactions.

### When to Use CLI Backends

✅ **Good Use Cases:**
- One-off complex notebook creation tasks
- CI/CD pipelines where local GPU isn't available
- Quick prototypes that need frontier models
- When you have subscription credits to spare

❌ **Bad Use Cases:**
- Regular daily development work (use Ollama instead)
- Long-running iterative development
- Production automation at scale
- When you're on a limited subscription plan

### API vs CLI Backends

**These backends are designed ONLY for CLI-based workflows.** Here's why:

- Using Claude Code or Codex CLI in ALMANAC means you're using their CLI infrastructure
- This is separate from direct API usage
- You won't hit API rate limits since you're not making API calls
- However, you will consume CLI usage credits instead

## Installation & Setup

### Claude Code CLI Backend

#### 1. Install Claude Code CLI

```bash
npm install -g @anthropic/claude-code
```

Verify installation:
```bash
claude --version
```

#### 2. Authenticate

```bash
claude login
```

This will open your browser and prompt you to log in with your Claude Pro/Team account.

#### 3. Verify Authentication

```bash
claude -p "Hello, are you working?"
```

You should get a response from Claude.

#### 4. Use in ALMANAC

Start ALMANAC:
```bash
python main.py
```

Switch to Claude Code backend:
```
/backend claude_code
```

You'll see a warning about usage consumption. Type your request normally and ALMANAC will use Claude Code CLI for reasoning.

### OpenAI Codex CLI Backend

#### 1. Install Codex CLI

```bash
npm install -g @openai/codex
```

Verify installation:
```bash
codex --version
```

#### 2. Authenticate

The Codex CLI should prompt you to authenticate when you first run it, or you can run:

```bash
codex exec "Hello"
```

Follow the authentication prompts to log in with your ChatGPT Plus/Pro/Business account.

#### 3. Use in ALMANAC

Start ALMANAC:
```bash
python main.py
```

Switch to Codex backend:
```
/backend codex
```

You'll see a warning about usage consumption. Type your request normally and ALMANAC will use Codex CLI for reasoning.

## Configuration

### Default Settings

Both CLI backends come pre-configured with sensible defaults in `src/config.py`:

#### Claude Code
```python
"claude_code": {
    "type": "claude_code_cli",
    "default_model": "claude-sonnet-4-5",
    "allowed_tools": "Read,Write,Edit,Bash,Glob,Grep",
    "skip_permissions": True,
}
```

#### Codex
```python
"codex": {
    "type": "codex_cli",
    "default_model": "gpt-5-codex",
    "full_auto": True,
    "sandbox": "danger-full-access",
}
```

### Customization

You can customize these settings by editing `src/config.py`. For example:

**To change allowed tools for Claude Code:**
```python
"allowed_tools": "Read,Write,Edit,Bash"  # Remove Glob,Grep if not needed
```

**To enable permission prompts (not recommended for automation):**
```python
"skip_permissions": False  # Claude will ask before using tools
```

**To change Codex sandbox mode:**
```python
"sandbox": "read-only"  # More restrictive mode
```

## How It Works

### Architecture

1. **Normal Flow (API Backends)**:
   ```
   User Input → Agent → HTTP API Call → LLM Response → Tool Execution → Repeat
   ```

2. **CLI Backend Flow**:
   ```
   User Input → Agent → CLI Subprocess Call → LLM Response → Tool Execution → Repeat
   ```

### Key Differences

- **CLI backends invoke a subprocess** for each reasoning step
- The conversation history is converted to a comprehensive prompt
- Tool definitions are included in the prompt
- The CLI output is parsed and converted back to OpenAI-compatible format
- Tool execution still happens locally in ALMANAC (not in the CLI)

### Why Keep Tools Local?

ALMANAC has custom tools for Jupyter notebook manipulation (`create_notebook`, `add_cell`, etc.) that are specific to this application. While Claude Code and Codex have their own file editing tools, we want to use ALMANAC's specialized notebook tools instead.

This hybrid approach gives us:
- Powerful reasoning from frontier models (Claude Sonnet 4.5, GPT-5 Codex)
- Specialized notebook tools from ALMANAC
- Seamless integration without code duplication

## Troubleshooting

### Claude Code CLI Not Found

**Error**: `Claude Code CLI not found`

**Solution**: Install the CLI:
```bash
npm install -g @anthropic/claude-code
```

If still failing, check your `$PATH`:
```bash
which claude
```

### Codex CLI Not Found

**Error**: `Codex CLI not found`

**Solution**: Install the CLI:
```bash
npm install -g @openai/codex
```

### Authentication Errors

**Error**: `Authentication failed` or `Not logged in`

**Solution for Claude Code**:
```bash
claude logout
claude login
```

**Solution for Codex**:
Re-run authentication:
```bash
codex exec "test"
```

### Timeout Errors

**Error**: `CLI timed out after 120 seconds`

**Solution**: The default timeout is 120 seconds. For very complex tasks, you might hit this limit. You can modify the timeout in `src/llm_backend.py`:

```python
# In ClaudeCodeCLIBackend or CodexCLIBackend
timeout=240  # Increase to 240 seconds (4 minutes)
```

### High Usage Consumption

**Issue**: Your subscription usage is being consumed very quickly.

**Solutions**:
1. Switch back to local backends (Ollama):
   ```
   /backend ollama
   ```

2. Use CLI backends only for specific complex tasks, not general development

3. Monitor your usage in Claude/ChatGPT dashboard

4. Consider using local models (Ollama) for iterative development and CLI backends only for final production runs

## Best Practices

1. **Start with Ollama for development**: Use local models for iterative development and testing. Switch to CLI backends only when you need frontier model capabilities.

2. **Monitor your usage**: Check your Claude/ChatGPT dashboard regularly when using CLI backends.

3. **Use Build mode initially**: Test in Build mode before switching to Run mode to avoid executing code prematurely.

4. **Clear context frequently**: Use `/new` to clear conversation history and start fresh, reducing the amount of context sent to the CLI.

5. **Provide clear, complete prompts**: Since CLI backends consume more resources, make your prompts as clear and complete as possible to minimize back-and-forth.

## Examples

### Example 1: Creating a Data Analysis Notebook with Claude Code

```bash
# Start ALMANAC
python main.py

# Switch to Claude Code backend
/backend claude_code

# Request a complex notebook
"Create a comprehensive data analysis notebook that:
1. Loads a CSV file with pandas
2. Performs exploratory data analysis
3. Creates 5 different visualizations
4. Includes statistical analysis
5. Has markdown cells explaining each step"
```

### Example 2: Machine Learning Pipeline with Codex

```bash
# Start ALMANAC
python main.py

# Switch to Codex backend
/backend codex

# Switch to Run mode to test execution
/mode run

# Request ML pipeline
"Build a complete machine learning pipeline notebook:
1. Data loading and preprocessing
2. Feature engineering
3. Model training (try 3 different algorithms)
4. Model evaluation with metrics
5. Visualization of results"
```

## Comparison: When to Use Each Backend

| Backend | Best For | Pros | Cons |
|---------|----------|------|------|
| **Ollama** (Default) | Daily development, iteration | Free, fast, private, unlimited | Requires local GPU, limited reasoning |
| **LM Studio** | Offline work, privacy | Free, private, offline capable | Requires local GPU, manual model management |
| **Mistral API** | Production API integration | Fast API, good pricing | Costs money, requires API key |
| **Claude Code CLI** | Complex one-off tasks | Frontier reasoning, no GPU needed | Consumes subscription quickly |
| **Codex CLI** | Complex coding tasks | Latest GPT models, strong at code | Consumes subscription quickly |

## FAQ

**Q: Can I use both API and CLI backends together?**
A: You can switch between them, but not use them simultaneously. Use `/backend` to switch.

**Q: Will using CLI backends affect my API rate limits?**
A: No, CLI backends use a separate infrastructure from APIs. You won't hit API rate limits, but you will consume CLI subscription usage.

**Q: Can I reduce the usage consumption?**
A: Yes, a few strategies:
- Clear context frequently with `/new`
- Provide complete prompts to minimize iterations
- Use for specific tasks only, not general chat
- Switch to Ollama for routine work

**Q: Do I need an API key for CLI backends?**
A: No, CLI backends authenticate via `claude login` or `codex` authentication. No API keys needed.

**Q: Can I use CLI backends in CI/CD?**
A: Yes, but be aware of usage consumption. You may need to set up authentication in CI/CD environments using environment variables or service accounts. Refer to Claude Code and Codex CLI documentation for CI/CD setup.

## Resources

- [Claude Code CLI Documentation](https://code.claude.com/docs)
- [OpenAI Codex CLI Documentation](https://developers.openai.com/codex/cli)
- [ALMANAC GitHub Repository](https://github.com/Baswold/Ai-notebook)

---

**Remember**: CLI backends are powerful but consume resources quickly. Use them wisely! 🚀
