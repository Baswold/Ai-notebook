import json
import asyncio
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

    async def step_gen(self, user_input):
        self.history.append({"role": "user", "content": user_input})
        backend = get_backend()
        
        MAX_STEPS = 1000000
        step_count = 0
        
        while step_count < MAX_STEPS:
            step_count += 1
            try:
                if step_count == 1:
                    yield {"type": "status", "content": "Thinking..."}
                else:
                    yield {"type": "status", "content": f"Thinking (Step {step_count})..."}

                # Call LLM
                response = await backend.chat_completion(self.history, tools=TOOLS_DEF)
                
                if "error" in response:
                    yield {"type": "error", "content": f"LLM Error: {response['error']}"}
                    return

                choice = response["choices"][0]
                message = choice["message"]
                
                # Check for tool calls
                if message.get("tool_calls"):
                    self.history.append(message)
                    
                    # Yield thought if present
                    if message.get("content"):
                         yield {"type": "thought", "content": message["content"]}
                    
                    tool_calls = message["tool_calls"]
                    
                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        arguments = json.loads(tool_call["function"]["arguments"])
                        
                        yield {"type": "tool_call", "name": function_name, "arguments": arguments}
                        
                        if function_name in TOOL_FUNCTIONS:
                            yield {"type": "status", "content": f"Executing {function_name}..."}
                            try:
                                # Run blocking tool in separate thread with timeout to prevent hangs
                                result = await asyncio.wait_for(
                                    asyncio.to_thread(TOOL_FUNCTIONS[function_name], **arguments),
                                    timeout=30.0
                                )
                            except asyncio.TimeoutError:
                                result = f"Error: Tool {function_name} timed out after 30 seconds."
                                
                                # Verification Check: Did it actually succeed despite timeout?
                                if function_name in ["add_multiple_cells", "add_cell"] and "filename" in arguments:
                                     try:
                                         # Check if file exists and has content
                                         # We use a separate thread for this too just in case, but usually verification is fast read
                                         verify_res = await asyncio.to_thread(TOOL_FUNCTIONS["read_notebook"], arguments["filename"])
                                         if not verify_res.startswith("Error"):
                                             # It returned valid JSON content, so the write likely worked.
                                             result += " BUT verification check shows the notebook was updated successfully. Do not retry."
                                     except Exception:
                                         pass
                            except Exception as tool_e:
                                result = f"Error executing tool {function_name}: {str(tool_e)}"
                        else:
                            result = f"Error: Tool {function_name} not found."
                            
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
                        self.history.append(message)
                        yield {"type": "message", "content": message["content"]}
                    
                    # We are done
                    break
                    
            except Exception as e:
                yield {"type": "error", "content": f"Agent Error: {str(e)}"}
                return
        
        if step_count >= MAX_STEPS:
             yield {"type": "error", "content": "Agent reached maximum step limit."}

    def clear_history(self):
        self.history = [self.history[0]]
