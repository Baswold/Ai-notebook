import json
import asyncio
import os
from datetime import datetime
from .llm_backend import get_backend
from .tools import TOOLS_DEF, TOOL_FUNCTIONS
from .config import GLOBAL_CONFIG

class Agent:
    def __init__(self):
        self.history = [
            {"role": "system", "content": f"""
You are Almanac, an expert AI software engineer specialized in creating and managing Jupyter Notebooks. Your default model is {GLOBAL_CONFIG.DEFAULT_MODEL}. You can manipulate notebooks using the provided tools. Always assume the user works in the current directory. In 'Build' mode you cannot execute notebooks, only create/edit them.

Mindset: relentless, thorough, and persistent. Always build notebooks to the fullest extent of your capabilities. Do not claim you implemented something unless you are certain. Never skip edge cases or hard parts.

Workflow (follow every time):
1) Analyze the request and restate goals briefly.
2) Think step by step with numbered reasoning before acting.
3) Produce a detailed plan/pseudocode (modules/functions/steps and edge cases). Do not generate final code until after the plan.
4) Execute the plan using the provided tools; keep responses structured.
5) Self-check: verify code against all requirements, check for syntax/logic issues, and ensure edge cases are covered. Fix before finalizing.
6) Present output in sections: Reasoning/Plan, Code (in a single block), Verification notes, and any Next steps.

Output expectations: be explicit about assumptions and paths, prefer numbered lists for reasoning, and aim for complete, ready-to-run notebooks. Good luck.
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

        backend = get_backend()

        while self.current_step_count < self.max_steps:
            self.current_step_count += 1
            self._log(f"Step {self.current_step_count}/{self.max_steps}")
            try:
                if self.current_step_count == 1 and not continue_from_previous:
                    yield {"type": "status", "content": "Thinking..."}
                else:
                    yield {"type": "status", "content": f"Thinking (Step {self.current_step_count}/{self.max_steps})..."}

                # Call LLM
                response = await backend.chat_completion(self.history, tools=TOOLS_DEF)

                if "error" in response:
                    self._log(f"LLM Error: {response['error']}")
                    yield {"type": "error", "content": f"LLM Error: {response['error']}"}
                    return

                choice = response["choices"][0]
                message = choice["message"]

                # Check for tool calls
                if message.get("tool_calls"):
                    self.history.append(message)

                    # Yield thought if present
                    if message.get("content"):
                         self._log(f"Thought: {message['content'][:100]}...")
                         yield {"type": "thought", "content": message["content"]}

                    tool_calls = message["tool_calls"]

                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        arguments = json.loads(tool_call["function"]["arguments"])

                        self._log(f"Tool call: {function_name} with args: {str(arguments)[:100]}...")
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
                            self._log(f"Tool not found: {function_name}")

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
                        yield {"type": "message", "content": message["content"]}

                    # We are done
                    self._log("Agent completed successfully")
                    break

            except Exception as e:
                self._log(f"Agent error: {str(e)}")
                yield {"type": "error", "content": f"Agent Error: {str(e)}"}
                return

        if self.current_step_count >= self.max_steps:
             self._log(f"Reached max iterations: {self.max_steps}")
             yield {"type": "max_iterations", "content": f"Reached maximum of {self.max_steps} iterations. Would you like to add another 50 iterations?", "current_steps": self.current_step_count}

    def _log(self, message):
        """Log messages to completeness_log.txt with timestamps"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"

        # Append to log file
        with open(self.log_file, "a") as f:
            f.write(log_message)

    def extend_max_steps(self, additional_steps=50):
        """Extend the maximum number of steps"""
        self.max_steps += additional_steps
        self._log(f"Extended max steps by {additional_steps} to {self.max_steps}")

    def clear_history(self):
        self._log("History cleared")
        self.history = [self.history[0]]
