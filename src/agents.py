import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from .llm import LLMBackend, LLMResponse, TokenUsage
from .memory import get_memory_path
from .tools import ToolRegistry, ToolResult


@dataclass
class AgentResponse:
    content: str
    tool_calls_made: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=TokenUsage)
    iterations: int = 0


class Agent1:
    def __init__(
        self,
        llm: LLMBackend,
        tools: ToolRegistry,
        system_prompt: str,
        max_iterations: int = 20
    ):
        self.llm = llm
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
    
    def run(
        self,
        instructions: str,
        codebase_context: str,
        last_commit: Optional[str] = None,
        task_summary: Optional[str] = None
    ) -> AgentResponse:
        messages = [{"role": "system", "content": self.system_prompt}]
        
        user_content = f"""## CODEBASE SNAPSHOT
{codebase_context}

"""
        if last_commit:
            user_content += f"""## LAST COMMIT
{last_commit}

"""
        if task_summary:
            user_content += f"""## TASK CONTEXT
{task_summary}

"""
        user_content += f"""## PERSISTENT MEMORY
Use `memory_read` with `agent="implementer"` to recall notes that persist across fresh contexts. 
After you finish a cycle, append any lessons you wish you had at the start using `memory_append` to `memories/implementer_memories.md`.

## INSTRUCTIONS
{instructions}

Execute these instructions now. Use the available tools to implement the required changes.
"""
        messages.append({"role": "user", "content": user_content})
        
        total_usage = TokenUsage()
        all_tool_calls = []
        all_tool_results = []
        final_content = ""
        iteration = 0
        
        tool_schemas = self.tools.get_schemas() if self.llm.supports_tools() else None
        
        for iteration in range(self.max_iterations):
            response = self.llm.generate(
                messages=messages,
                tools=tool_schemas,
                max_tokens=4096
            )
            
            total_usage = total_usage + response.usage
            
            if not response.tool_calls:
                final_content = response.content
                break
            
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": response.tool_calls
            })
            
            for tool_call in response.tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                try:
                    arguments = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}
                
                result = self.tools.execute(tool_name, arguments)
                all_tool_calls.append({"name": tool_name, "arguments": arguments})
                all_tool_results.append(result)
                
                tool_id = tool_call.get("id", f"call_{iteration}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result.output if result.success else f"Error: {result.error}"
                })
            
            if response.finish_reason == "stop":
                final_content = response.content
                break
        
        return AgentResponse(
            content=final_content,
            tool_calls_made=all_tool_calls,
            tool_results=all_tool_results,
            usage=total_usage,
            iterations=iteration + 1
        )


class Agent2:
    def __init__(
        self,
        llm: LLMBackend,
        system_prompt: str,
        tools: Optional[ToolRegistry] = None,
        max_iterations: int = 10
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.tools = tools
        self.max_iterations = max_iterations
    
    def review(
        self,
        original_spec: str,
        codebase_context: str,
        git_log: str,
        memory_agent: str = "reviewer"
    ) -> "ReviewResult":
        messages = [{"role": "system", "content": self.system_prompt}]

        memory_path_str = None
        if self.tools:
            try:
                memory_path_str = str(
                    get_memory_path(self.tools.workspace, memory_agent, ensure_dir=True).relative_to(self.tools.workspace)
                )
            except Exception:
                memory_path_str = None
        
        user_content = f"""## ORIGINAL SPECIFICATION
{original_spec}

## CURRENT CODEBASE
{codebase_context}

## GIT LOG (Recent Commits)
{git_log}

Review the codebase against the specification. Rate completeness and provide specific next instructions.
Do NOT trust claims in commit messages - verify everything in the actual code.
"""

        if memory_path_str:
            user_content += f"""

Persistent memory for this reviewer: {memory_path_str}
- Read notes with `memory_read` using `agent=\"{memory_agent}\"`
- Append lessons you wish you knew at the start with `memory_append`
"""

        messages.append({"role": "user", "content": user_content})
        
        tool_schemas = None
        if self.tools and self.llm.supports_tools():
            tool_schemas = self.tools.get_schemas()

        total_usage = TokenUsage()
        final_content = ""

        for iteration in range(self.max_iterations):
            response = self.llm.generate(
                messages=messages,
                tools=tool_schemas,
                max_tokens=4096
            )

            total_usage = total_usage + response.usage

            if not response.tool_calls:
                final_content = response.content
                break

            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": response.tool_calls
            })

            for tool_call in response.tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                try:
                    arguments = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}

                result = self.tools.execute(tool_name, arguments) if self.tools else ToolResult(False, "", "No tools available")
                tool_id = tool_call.get("id", f"call_{iteration}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result.output if result.success else f"Error: {result.error}"
                })

            if response.finish_reason == "stop":
                final_content = response.content
                break

        if not final_content:
            final_content = response.content if 'response' in locals() else ""

        return ReviewResult.parse(final_content, total_usage)


@dataclass
class ReviewResult:
    raw_content: str
    completeness_score: int
    completed_items: List[str]
    remaining_work: List[str]
    issues_found: List[str]
    commit_instructions: str
    next_instructions: str
    usage: TokenUsage
    is_complete: bool = False
    
    @classmethod
    def parse(cls, content: str, usage: TokenUsage) -> "ReviewResult":
        score = 0
        completed = []
        remaining = []
        issues = []
        commit_instr = ""
        next_instr = ""
        
        lines = content.split("\n")
        current_section = None
        section_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if "completeness score" in line_lower:
                import re
                match = re.search(r"(\d+)", line)
                if match:
                    score = int(match.group(1))
                current_section = "score"
                continue
            elif "what was just completed" in line_lower or "completed:" in line_lower:
                current_section = "completed"
                continue
            elif "remaining work" in line_lower:
                current_section = "remaining"
                continue
            elif "issues found" in line_lower or "specific issues" in line_lower:
                current_section = "issues"
                continue
            elif "commit instructions" in line_lower:
                current_section = "commit"
                section_content = []
                continue
            elif "next instructions" in line_lower or "instructions for agent" in line_lower:
                if current_section == "commit":
                    commit_instr = "\n".join(section_content)
                current_section = "next"
                section_content = []
                continue
            
            if current_section == "completed" and line.strip().startswith("-"):
                completed.append(line.strip()[1:].strip())
            elif current_section == "remaining" and (line.strip().startswith("-") or line.strip()[:2].replace(".", "").isdigit()):
                remaining.append(line.strip().lstrip("-0123456789. "))
            elif current_section == "issues" and line.strip().startswith("-"):
                issues.append(line.strip()[1:].strip())
            elif current_section in ("commit", "next"):
                section_content.append(line)
        
        if current_section == "commit":
            commit_instr = "\n".join(section_content)
        elif current_section == "next":
            next_instr = "\n".join(section_content)
        
        if not next_instr and section_content:
            next_instr = "\n".join(section_content)
        
        is_complete = score >= 95 and not remaining
        
        return cls(
            raw_content=content,
            completeness_score=score,
            completed_items=completed,
            remaining_work=remaining,
            issues_found=issues,
            commit_instructions=commit_instr,
            next_instructions=next_instr or content,
            usage=usage,
            is_complete=is_complete
        )
