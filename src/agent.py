import json
import asyncio
from .llm_backend import get_backend
from .tools import TOOLS_DEF, TOOL_FUNCTIONS
from .config import GLOBAL_CONFIG

class Agent:
    def __init__(self):
        self.history = [
            {"role": "system", "content": f"You are Almanac, an advanced AI assistant specialized in creating and managing Jupyter Notebooks. Your default model is {GLOBAL_CONFIG.DEFAULT_MODEL}. You can manipulate notebooks using the provided tools. Always assume the user wants to work in the current directory. When in 'Build' mode, you cannot execute notebooks, only create/edit them. Always assume that the user wants the notebook made to the FULL extent of your capabilities. Do not shy away from work. you should always try to make the notebook, as if you REALLY REALLY want it to run, which you should. Don't say you have implamented something, unless you are 100% sure that you have."}
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
