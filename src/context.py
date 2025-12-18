import subprocess
from pathlib import Path
from typing import List, Optional, Set

from .memory import read_memory, get_memory_path


class ContextBuilder:
    # Extensions for code files that Agent 2 should review
    CODE_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
        ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
        ".scala", ".sh", ".bash", ".zsh", ".sql", ".graphql", ".proto"
    }
    
    # Config/data files that are also relevant
    CONFIG_EXTENSIONS = {
        ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
        ".html", ".css", ".scss", ".less", ".xml"
    }
    
    # Extensions to BLOCK from Agent 2 (Agent 1 prose/summaries)
    BLOCKED_EXTENSIONS = {
        ".md", ".txt", ".doc", ".docx", ".rtf"
    }
    
    def __init__(self, workspace: Path, original_spec_name: str = "idea.md"):
        self.workspace = workspace
        self.original_spec_name = original_spec_name
        self.ignore_patterns = {
            ".git", "__pycache__", "node_modules", ".venv", "venv",
            ".env", ".idea", ".vscode", "*.pyc", "*.pyo", ".DS_Store",
            "*.egg-info", "dist", "build", ".pytest_cache", ".mypy_cache"
        }
    
    def build_file_tree(self, max_depth: int = 10) -> str:
        lines = []
        self._walk_tree(self.workspace, lines, "", max_depth)
        return "\n".join(lines)
    
    def _walk_tree(self, path: Path, lines: List[str], prefix: str, depth: int):
        if depth <= 0:
            return
        
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return
        
        filtered = [e for e in entries if not self._should_ignore(e)]
        
        for i, entry in enumerate(filtered):
            is_last = i == len(filtered) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            
            if entry.is_dir():
                extension = "    " if is_last else "│   "
                self._walk_tree(entry, lines, prefix + extension, depth - 1)
    
    def _should_ignore(self, path: Path) -> bool:
        name = path.name
        for pattern in self.ignore_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False
    
    def read_all_source_files(self, extensions: Optional[Set[str]] = None) -> str:
        """Read all source files (used by Agent 1)."""
        if extensions is None:
            extensions = {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
                ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
                ".scala", ".sh", ".bash", ".zsh", ".yaml", ".yml", ".json",
                ".toml", ".ini", ".cfg", ".md", ".txt", ".html", ".css",
                ".scss", ".less", ".sql", ".graphql", ".proto"
            }
        
        contents = []
        for file_path in self.workspace.rglob("*"):
            if file_path.is_file() and file_path.suffix in extensions:
                if self._should_ignore(file_path):
                    continue
                if any(self._should_ignore(p) for p in file_path.parents):
                    continue
                
                try:
                    rel_path = file_path.relative_to(self.workspace)
                    content = file_path.read_text(errors="replace")
                    contents.append(f"### {rel_path}\n```\n{content}\n```\n")
                except Exception:
                    continue
        
        return "\n".join(contents)

    def _build_memory_section(self, agent: Optional[str]) -> str:
        if not agent:
            return ""

        content = read_memory(self.workspace, agent)
        if not content.strip():
            return ""

        path = get_memory_path(self.workspace, agent, ensure_dir=True).relative_to(self.workspace)
        label = agent.replace("_", " ").title()
        return f"""### Persistent Memory ({label})
Path: {path}
```
{content}
```
"""
    
    def read_code_only_files(self) -> str:
        """
        Read ONLY code files for Agent 2 review.
        
        CRITICAL: This method implements the air gap principle.
        Agent 2 should NEVER see:
        - .md files created by Agent 1 (except original spec)
        - .txt files that might contain summaries
        - Any documentation created during development
        
        Agent 2 ONLY sees:
        - Original specification (idea.md)
        - Source code files
        - Config files (yaml, json, etc.)
        - Test files
        """
        allowed_extensions = self.CODE_EXTENSIONS | self.CONFIG_EXTENSIONS
        contents = []
        
        for file_path in self.workspace.rglob("*"):
            if not file_path.is_file():
                continue
            if self._should_ignore(file_path):
                continue
            if any(self._should_ignore(p) for p in file_path.parents):
                continue
            
            rel_path = file_path.relative_to(self.workspace)
            rel_path_str = str(rel_path)
            
            # ALWAYS include original spec (match by filename or full path)
            spec_name_lower = self.original_spec_name.lower()
            if (rel_path_str.lower() == spec_name_lower or 
                file_path.name.lower() == spec_name_lower or
                rel_path_str.lower().endswith("/" + spec_name_lower)):
                try:
                    content = file_path.read_text(errors="replace")
                    contents.append(f"### {rel_path} [ORIGINAL SPEC]\n```\n{content}\n```\n")
                except Exception:
                    pass
                continue
            
            # BLOCK markdown and text files created during development
            if file_path.suffix in self.BLOCKED_EXTENSIONS:
                continue
            
            # Include code and config files
            if file_path.suffix in allowed_extensions:
                try:
                    content = file_path.read_text(errors="replace")
                    contents.append(f"### {rel_path}\n```\n{content}\n```\n")
                except Exception:
                    continue
        
        return "\n".join(contents)
    
    def run_tests(self, timeout: int = 60) -> str:
        """
        Run tests and capture output for Agent 2 review.
        
        Returns actual test execution output - this is FACTUAL evidence
        that Agent 2 can use to verify implementation completeness.
        """
        test_commands = [
            # Python
            (["python", "-m", "pytest", "-v", "--tb=short"], "pytest"),
            (["python", "-m", "unittest", "discover", "-v"], "unittest"),
            # Node.js
            (["npm", "test"], "npm test"),
            # Go
            (["go", "test", "./..."], "go test"),
            # Rust
            (["cargo", "test"], "cargo test"),
        ]
        
        results = []
        
        for cmd, name in test_commands:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=self.workspace,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                output = result.stdout + result.stderr
                
                # Skip if tool is unavailable (ModuleNotFoundError, command not found, etc.)
                if "No module named" in output or "command not found" in output:
                    continue
                
                if output.strip():
                    exit_status = "PASSED" if result.returncode == 0 else "FAILED"
                    results.append(f"### Test Results ({name}) - {exit_status}\n```\n{output}\n```\n")
                    # Found working test framework - use it
                    if result.returncode == 0 or "test" in output.lower():
                        break
                    
            except FileNotFoundError:
                continue
            except subprocess.TimeoutExpired:
                results.append(f"### Test Results ({name}) - TIMEOUT\nTests exceeded {timeout}s timeout\n")
                break
            except Exception as e:
                continue
        
        if not results:
            # Try to find and run test files directly
            test_files = list(self.workspace.rglob("test_*.py"))
            test_files.extend(self.workspace.rglob("*_test.py"))
            
            if test_files:
                for test_file in test_files[:3]:  # Limit to 3 test files
                    try:
                        result = subprocess.run(
                            ["python", str(test_file)],
                            cwd=self.workspace,
                            capture_output=True,
                            text=True,
                            timeout=timeout
                        )
                        output = result.stdout + result.stderr
                        if output.strip():
                            rel_path = test_file.relative_to(self.workspace)
                            exit_status = "PASSED" if result.returncode == 0 else "FAILED"
                            results.append(f"### Test Results ({rel_path}) - {exit_status}\n```\n{output}\n```\n")
                    except Exception:
                        continue
        
        return "\n".join(results) if results else "No tests found or executed."
    
    def get_git_log(self, count: int = 10) -> str:
        try:
            result = subprocess.run(
                ["git", "log", f"-n{count}", "--pretty=format:%h %s (%cr)"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout if result.returncode == 0 else "No git history"
        except Exception:
            return "Git not available"
    
    def get_last_commit(self) -> str:
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%h %s\n\n%b"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""
    
    def build_agent1_context(self, focus_files: Optional[List[str]] = None) -> str:
        tree = self.build_file_tree()
        
        if focus_files:
            file_contents = []
            for file_path in focus_files:
                full_path = self.workspace / file_path
                if full_path.exists() and full_path.is_file():
                    try:
                        content = full_path.read_text(errors="replace")
                        file_contents.append(f"### {file_path}\n```\n{content}\n```\n")
                    except Exception:
                        pass
            files_str = "\n".join(file_contents)
        else:
            files_str = self.read_all_source_files()
        
        memories = self._build_memory_section("implementer")
        
        return f"""### File Tree
```
{tree}
```

### Source Files
{files_str}
{memories}
"""
    
    def build_agent2_context(self, run_tests: bool = True, memory_agent: Optional[str] = None) -> str:
        """
        Build context for Agent 2 review.
        
        CRITICAL AIR GAP IMPLEMENTATION:
        - Uses read_code_only_files() to exclude .md/.txt files
        - Includes test execution results (factual evidence)
        - Git log included but Agent 2 trained to ignore completion claims
        - Reviewer/testing memory is appended explicitly as the only allowed markdown context
        """
        tree = self.build_file_tree()
        
        # CODE ONLY - no markdown or text files from Agent 1
        files_str = self.read_code_only_files()
        
        git_log = self.get_git_log()
        memories = self._build_memory_section(memory_agent)
        
        context = f"""### File Tree
```
{tree}
```

### Source Files (CODE ONLY - No Agent 1 Documentation)
{files_str}

### Git Log (Verify claims in actual code, not commit messages)
```
{git_log}
```
{memories}
"""
        
        # Add test results if requested (factual verification)
        if run_tests:
            test_results = self.run_tests()
            context += f"""
### Test Execution Results (FACTUAL - Use to verify completeness)
{test_results}
"""
        
        return context
    
    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4
