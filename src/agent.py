import json
import asyncio
import os
from datetime import datetime
from .llm_backend import get_backend
from .tools import TOOLS_DEF, TOOL_FUNCTIONS
from .config import GLOBAL_CONFIG
from .logger import get_logger

class Agent:
    def __init__(self):
        self.history = [
            {"role": "system", "content": """
# Notebook Building Agent

You are a notebook building agent that creates COMPLETE, PRODUCTION-READY Jupyter notebooks with REAL implementations.

## CRITICAL RULES - NEVER VIOLATE THESE:

### 1. CREATE EXECUTABLE CODE CELLS, NOT DOCUMENTATION
- **CRITICAL**: Code must go in EXECUTABLE CODE CELLS, not markdown cells with code blocks
- **NEVER** put code inside markdown cells wrapped in ```python blocks
- **NEVER** create a documentation notebook - create a RUNNABLE notebook
- Each code snippet must be its own separate CODE CELL that can be executed
- Markdown cells are ONLY for explanations, headings, and documentation
- The notebook must be runnable from top to bottom by clicking "Run All"

### 2. NO MOCK IMPLEMENTATIONS - ABSOLUTELY FORBIDDEN
**CRITICAL: You must use REAL models and libraries, not mock/simulation code.**

Forbidden patterns - if your code contains ANY of these, you have FAILED:
- `class MockModel` or `class Mock*` (any class starting with Mock)
- `np.random.rand()` for embeddings
- Comments: "for demo purposes", "placeholder", "simulation", "mock", "dummy", "fake", "simulated"

✅ **CORRECT - Use real models:**
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("gpt2")
tokenizer = AutoTokenizer.from_pretrained("gpt2")

from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = embedding_model.encode(texts)
```

**ZERO TOLERANCE: If you use mocks, placeholders, or simulations, the notebook is WORTHLESS.**

### 3. NO COMPUTE EXCUSES
- **DO NOT** worry about compute resources, memory, or processing time
- **DO NOT** mention limitations or concerns about running the code
- The user has adequate resources - trust this and build the full implementation
- **ASSUME** the user can run transformers models, train models, and execute all code

### 4. COMPLETE IMPLEMENTATIONS ONLY
- Build the ENTIRE notebook from start to finish in ONE response
- Include ALL cells: imports, setup, implementation, training, evaluation, testing
- Every function must be fully implemented with real code
- If the spec mentions training, YOU MUST INCLUDE ACTUAL TRAINING CODE

### 5. CRITICAL: CELL TYPE REQUIREMENTS

**NEVER put ```python or ``` backticks inside ANY cell. Not in markdown cells, not in code cells. NEVER.**

**If you put ```python blocks inside code cells, you have COMPLETELY FAILED.**

✅ **CORRECT CODE CELL:**
```
import numpy as np
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

❌ **WRONG CODE CELL (has triple backticks inside):**
```
```python
import numpy as np
from sentence_transformers import SentenceTransformer
```
```

The notebook must have TWO types of cells:
1. **MARKDOWN cells** - for titles, explanations, documentation (NO CODE, NO ```python blocks)
2. **CODE cells** - for all executable Python code (NO markdown formatting, NO ```python blocks)

## WORKFLOW:

1) Analyze the request and plan the complete notebook
2) Build it in ONE response - don't stop halfway
3) Use REAL implementations - actual models, actual training, actual code
4) Include pip install commands for dependencies
5) Test and verify the implementation

## FORBIDDEN PHRASES:

Never say:
- "This is a mockup/simulation"
- "In a real implementation, you would..."
- "This is a placeholder"
- "Due to compute limitations..."
- "For demonstration purposes, we'll use a mock..."

## REQUIRED MINDSET:

- The user WANTS the full implementation
- The user HAS the resources to run it
- Incomplete notebooks are FAILURES
- Mock implementations are UNACCEPTABLE
- Your job is to BUILD, not to SIMULATE

Remember: The user explicitly does NOT want simulations or documentation. They want runnable, complete, production-ready notebooks with real implementations where every piece of code is in an EXECUTABLE CODE CELL. Anything less is a failure.
"""}
        ]
        self.log_file = "completeness_log.txt"
        self._log("Agent initialized")
        self.max_steps = 50  # Default max steps
        self.current_step_count = 0

    async def step_gen(self, user_input, continue_from_previous=False):
        if not continue_from_previous:
            self._log(f"User input: {user_input[:100]}...")
            self.history.append({"role": "user", "content": user_input})
            self.current_step_count = 0
        else:
            self._log(f"Continuing from step {self.current_step_count}")

    async def step_gen(self, user_input):
        # Log user input
        logger = get_logger()
        logger.log_user_input(user_input)

        self.history.append({"role": "user", "content": user_input})
        backend = get_backend()

        MAX_STEPS = 1000000
        step_count = 0
        
        while step_count < MAX_STEPS:
            step_count += 1
            try:
                if self.current_step_count == 1 and not continue_from_previous:
                    yield {"type": "status", "content": "Thinking..."}
                else:
                    yield {"type": "status", "content": f"Thinking (Step {self.current_step_count}/{self.max_steps})..."}

                # Call LLM
                response = await backend.chat_completion(self.history, tools=TOOLS_DEF)

                if "error" in response:
                    error_msg = f"LLM Error: {response['error']}"
                    logger.log_agent_output("error", error_msg)
                    yield {"type": "error", "content": error_msg}
                    return

                choice = response["choices"][0]
                message = choice["message"]

                # Check for tool calls
                if message.get("tool_calls"):
                    self.history.append(message)

                    # Yield thought if present
                    if message.get("content"):
                         logger.log_agent_output("thought", message["content"])
                         yield {"type": "thought", "content": message["content"]}

                    tool_calls = message["tool_calls"]

                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        arguments = json.loads(tool_call["function"]["arguments"])

                        logger.log_agent_output("tool_call", "", name=function_name, arguments=arguments)
                        yield {"type": "tool_call", "name": function_name, "arguments": arguments}

                        if function_name in TOOL_FUNCTIONS:
                            yield {"type": "status", "content": f"Executing {function_name}..."}
                            try:
                                # Run blocking tool in separate thread with timeout to prevent hangs
                                result = await asyncio.wait_for(
                                    asyncio.to_thread(TOOL_FUNCTIONS[function_name], **arguments),
                                    timeout=30.0
                                )
                                self._log(f"Tool result: {str(result)[:100]}...")
                            except asyncio.TimeoutError:
                                result = f"Error: Tool {function_name} timed out after 30 seconds."
                                self._log(f"Tool timeout: {function_name}")

                                # Verification Check: Did it actually succeed despite timeout?
                                if function_name in ["add_multiple_cells", "add_cell"] and "filename" in arguments:
                                     try:
                                         # Check if file exists and has content
                                         # We use a separate thread for this too just in case, but usually verification is fast read
                                         verify_res = await asyncio.to_thread(TOOL_FUNCTIONS["read_notebook"], arguments["filename"])
                                         if not verify_res.startswith("Error"):
                                             # It returned valid JSON content, so the write likely worked.
                                             result += " BUT verification check shows the notebook was updated successfully. Do not retry."
                                             self._log("Verification check passed despite timeout")
                                     except Exception:
                                         pass
                            except Exception as tool_e:
                                result = f"Error executing tool {function_name}: {str(tool_e)}"
                                self._log(f"Tool error: {str(tool_e)}")
                        else:
                            result = f"Error: Tool {function_name} not found."

                        logger.log_agent_output("tool_result", result, name=function_name)
                        yield {"type": "tool_result", "name": function_name, "result": result}

                        # Append result to history
                        self.history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": str(result)
                        })

                    # Loop continues to next step to let LLM process results
                    continue

                else:
                    # No tool calls, just a message (Final Answer)
                    # Only append if valid content
                    if message.get("content"):
                        self._log(f"Final message: {message['content'][:100]}...")
                        self.history.append(message)
                        logger.log_agent_output("message", message["content"])
                        yield {"type": "message", "content": message["content"]}

                    # We are done
                    self._log("Agent completed successfully")
                    break

            except Exception as e:
                error_msg = f"Agent Error: {str(e)}"
                logger.log_agent_output("error", error_msg)
                yield {"type": "error", "content": error_msg}
                return

        if step_count >= MAX_STEPS:
             error_msg = "Agent reached maximum step limit."
             logger.log_agent_output("error", error_msg)
             yield {"type": "error", "content": error_msg}

    def clear_history(self):
        self._log("History cleared")
        self.history = [self.history[0]]
