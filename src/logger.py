"""
Logging utility for the notebook AI agent.
Logs all user inputs and agent outputs to auto-incrementing log files.
"""

import os
from datetime import datetime

class AgentLogger:
    def __init__(self, base_name="log", extension=".txt", log_dir="."):
        """Initialize logger with auto-incrementing filename."""
        self.log_dir = log_dir
        self.log_file = None
        self.log_filename = self._get_log_filename(base_name, extension)
        self._open_log_file()

    def _get_log_filename(self, base_name, extension):
        """Get next available log filename with auto-increment."""
        base_path = os.path.join(self.log_dir, f"{base_name}{extension}")

        if not os.path.exists(base_path):
            return base_path

        counter = 1
        while True:
            path = os.path.join(self.log_dir, f"{base_name}{counter}{extension}")
            if not os.path.exists(path):
                return path
            counter += 1

    def _open_log_file(self):
        """Open the log file for writing."""
        try:
            self.log_file = open(self.log_filename, 'w', encoding='utf-8')
            self._write_header()
        except Exception as e:
            print(f"Warning: Could not open log file {self.log_filename}: {e}")
            self.log_file = None

    def _write_header(self):
        """Write header to log file."""
        if self.log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"{'='*80}\n")
            self.log_file.write(f"Agent Log Started: {timestamp}\n")
            self.log_file.write(f"Log File: {self.log_filename}\n")
            self.log_file.write(f"{'='*80}\n\n")
            self.log_file.flush()

    def log_user_input(self, user_input):
        """Log user input."""
        if not self.log_file:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"\n{'='*80}\n")
        self.log_file.write(f"[{timestamp}] USER INPUT:\n")
        self.log_file.write(f"{'-'*80}\n")
        self.log_file.write(f"{user_input}\n")
        self.log_file.write(f"{'='*80}\n\n")
        self.log_file.flush()

    def log_agent_output(self, output_type, content, **kwargs):
        """Log agent output (thoughts, tool calls, results, messages)."""
        if not self.log_file:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.write(f"[{timestamp}] AGENT {output_type.upper()}:\n")

        # Format based on output type
        if output_type == "tool_call":
            self.log_file.write(f"  Tool: {kwargs.get('name', 'unknown')}\n")
            self.log_file.write(f"  Arguments: {kwargs.get('arguments', {})}\n")
        elif output_type == "tool_result":
            self.log_file.write(f"  Tool: {kwargs.get('name', 'unknown')}\n")
            self.log_file.write(f"  Result: {content}\n")
        elif output_type in ["thought", "message", "status", "error"]:
            self.log_file.write(f"  {content}\n")
        else:
            self.log_file.write(f"  {content}\n")

        self.log_file.write("\n")
        self.log_file.flush()

    def close(self):
        """Close the log file."""
        if self.log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"\n{'='*80}\n")
            self.log_file.write(f"Agent Log Ended: {timestamp}\n")
            self.log_file.write(f"{'='*80}\n")
            self.log_file.close()
            self.log_file = None

    def __del__(self):
        """Ensure log file is closed on deletion."""
        self.close()

# Global logger instance
_global_logger = None

def get_logger():
    """Get or create the global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = AgentLogger()
    return _global_logger

def close_logger():
    """Close the global logger."""
    global _global_logger
    if _global_logger:
        _global_logger.close()
        _global_logger = None
