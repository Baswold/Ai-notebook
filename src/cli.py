import time
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import signal

from .config import LoopConfig
from .orchestrator import Orchestrator, CycleResult
from .llm import list_backends


BANNER = """
================================================================================
                         COMPLETENESS LOOP
                   Autonomous Multi-Agent Coding System
================================================================================
"""

HELP_TEXT = """
Commands:
  start <idea.md> <workspace>  Start a new loop
  resume <workspace>           Resume a paused loop
  status [workspace]           Show current status
  score [workspace]            Show completeness history
  backends                     List available LLM backends
  config                       Generate example config
  help                         Show this help
  quit                         Exit the REPL
"""


class CompletenessREPL:
    def __init__(self):
        self.config = LoopConfig()
        self.current_workspace = None
        self.orchestrator = None
        self.running = False
    
    def print_banner(self):
        print(BANNER)
        print(f"  Backend: {self.config.model.backend}")
        print(f"  Model:   {self.config.model.name}")
        print()
        print("  Type 'help' for commands, 'quit' to exit")
        print("=" * 80)
        print()
    
    def format_time(self, seconds):
        return str(timedelta(seconds=int(seconds)))
    
    def progress_bar(self, score, width=40):
        filled = int(score / 100 * width)
        bar = "#" * filled + "-" * (width - filled)
        return f"[{bar}] {score}%"
    
    def print_cycle(self, result, elapsed):
        print()
        print(f"--- Cycle {result.cycle_number} Complete ---")
        print(f"Score: {self.progress_bar(result.completeness_score)}")
        print(f"Time:  {result.duration_seconds:.1f}s (total: {self.format_time(elapsed)})")
        
        if result.agent1_response:
            print(f"Agent 1: {result.agent1_response.usage.total_tokens:,} tokens, {result.agent1_response.iterations} iterations")
        
        if result.agent2_review:
            print(f"Agent 2: {result.agent2_review.usage.total_tokens:,} tokens")
            
            if result.agent2_review.completed_items:
                print("  Completed:")
                for item in result.agent2_review.completed_items[:3]:
                    print(f"    + {item[:70]}")
            
            if result.agent2_review.remaining_work:
                print("  Remaining:")
                for item in result.agent2_review.remaining_work[:3]:
                    print(f"    - {item[:70]}")
        
        if result.error:
            print(f"  ERROR: {result.error}")
        print()
    
    def print_status(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")
    
    def cmd_start(self, args):
        if len(args) < 2:
            print("Usage: start <idea.md> <workspace>")
            return
        
        idea_path = Path(args[0]).resolve()
        workspace_path = Path(args[1]).resolve()
        
        if not idea_path.exists():
            print(f"Error: Idea file not found: {idea_path}")
            return
        
        workspace_path.mkdir(parents=True, exist_ok=True)
        self.current_workspace = workspace_path
        
        print()
        print(f"Idea:      {idea_path}")
        print(f"Workspace: {workspace_path}")
        print()
        
        self._run_loop(idea_path, workspace_path, resume=False)
    
    def cmd_resume(self, args):
        if len(args) < 1:
            if self.current_workspace:
                workspace_path = self.current_workspace
            else:
                print("Usage: resume <workspace>")
                return
        else:
            workspace_path = Path(args[0]).resolve()
        
        state_file = workspace_path / ".completeness_state.json"
        if not state_file.exists():
            print(f"Error: No saved state in {workspace_path}")
            return
        
        idea_file = None
        for f in workspace_path.parent.glob("*.md"):
            idea_file = f
            break
        
        if not idea_file:
            print("Error: Cannot find idea file. Use 'start' instead.")
            return
        
        self._run_loop(idea_file, workspace_path, resume=True)
    
    def _run_loop(self, idea_path, workspace_path, resume=False):
        start_time = time.time()
        
        def on_cycle(result):
            self.print_cycle(result, time.time() - start_time)
        
        def on_status(status):
            self.print_status(status)
        
        self.orchestrator = Orchestrator(
            workspace=workspace_path,
            idea_file=idea_path,
            config=self.config,
            on_cycle_complete=on_cycle,
            on_status_change=on_status
        )
        
        self.running = True
        action = "Resuming" if resume else "Starting"
        self.print_status(f"{action} loop... (Ctrl+C to pause)")
        print()
        
        try:
            self.orchestrator.run(resume=resume)
        except KeyboardInterrupt:
            print()
            self.print_status("Pausing...")
            self.orchestrator.pause()
        except Exception as e:
            print(f"Error: {e}")
        
        self.running = False
        status = self.orchestrator.get_status()
        
        print()
        print("=" * 60)
        print(f"Cycles:      {status['cycle_count']}")
        print(f"Final Score: {self.progress_bar(status['current_score'])}")
        print(f"Phase:       {status.get('phase', 'implementation')}")
        print(f"Runtime:     {self.format_time(time.time() - start_time)}")
        print(f"Tokens:      {status['total_tokens']:,}")
        
        if status['is_complete']:
            print("Status:      COMPLETE")
        elif status.get('is_paused'):
            print("Status:      PAUSED (use 'resume' to continue)")
        else:
            print("Status:      STOPPED")
        print("=" * 60)
        print()
    
    def cmd_status(self, args):
        workspace = Path(args[0]).resolve() if args else self.current_workspace
        if not workspace:
            print("Usage: status <workspace>")
            return
        
        state_file = workspace / ".completeness_state.json"
        if not state_file.exists():
            print("No session found.")
            return
        
        with open(state_file) as f:
            state = json.load(f)
        
        history = state.get("completeness_history", [])
        latest_score = history[-1]["score"] if history else 0
        
        print()
        print(f"Workspace: {workspace}")
        print(f"Cycles:    {state.get('cycle_count', 0)}")
        print(f"Score:     {self.progress_bar(latest_score)}")
        print(f"Phase:     {state.get('phase', 'implementation')}")
        print(f"Complete:  {'Yes' if state.get('is_complete') else 'No'}")
        print(f"Paused:    {'Yes' if state.get('is_paused') else 'No'}")
        print()
    
    def cmd_score(self, args):
        workspace = Path(args[0]).resolve() if args else self.current_workspace
        if not workspace:
            print("Usage: score <workspace>")
            return
        
        state_file = workspace / ".completeness_state.json"
        if not state_file.exists():
            print("No session found.")
            return
        
        with open(state_file) as f:
            state = json.load(f)
        
        history = state.get("completeness_history", [])
        if not history:
            print("No history yet.")
            return
        
        print()
        print("Cycle | Score")
        print("------+--------------------------------------------------")
        for entry in history[-15:]:
            cycle = entry.get("cycle", "?")
            score = entry.get("score", 0)
            phase = entry.get("phase", "impl")[:4]
            bar = self.progress_bar(score, 35)
            print(f"{cycle:>5} | {bar} [{phase}]")
        print()
    
    def cmd_backends(self, args):
        print(list_backends())
    
    def cmd_config(self, args):
        output = Path(args[0]) if args else Path("config.yaml")
        self.config.save(output)
        print(f"Config saved to {output}")
    
    def cmd_help(self, args):
        print(HELP_TEXT)
    
    def run(self):
        self.print_banner()
        
        while True:
            try:
                line = input("loop> ").strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                if self.running:
                    continue
                print()
                break
            
            if not line:
                continue
            
            parts = line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            
            if cmd in ("quit", "exit", "q"):
                break
            elif cmd == "start":
                self.cmd_start(args)
            elif cmd == "resume":
                self.cmd_resume(args)
            elif cmd == "status":
                self.cmd_status(args)
            elif cmd == "score":
                self.cmd_score(args)
            elif cmd == "backends":
                self.cmd_backends(args)
            elif cmd == "config":
                self.cmd_config(args)
            elif cmd == "help":
                self.cmd_help(args)
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")
        
        print("Goodbye!")


def main():
    repl = CompletenessREPL()
    repl.run()


if __name__ == "__main__":
    main()
