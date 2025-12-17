import asyncio
import os
import psutil
import time
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.application import Application
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea, Frame, Dialog, RadioList, Button, Label
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from .agent import Agent
from .config import GLOBAL_CONFIG

rich_console = Console(force_terminal=True, color_system="truecolor", width=100)

class AlmanacUI:
    def __init__(self):
        self.agent = Agent()
        self.log_content = "" 
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0 
        
        # Output TextArea - handles scrolling automatically
        self.output_textarea = TextArea(
            text="",
            read_only=True,
            wrap_lines=True,
            style="class:output"
        )
        self.output_window = self.output_textarea

        self.app = None
        self.is_processing = False
        self.input_queue = []

        # Scroll State
        self.autoscroll = True

        # Exit Logic State
        self.last_exit_attempt = 0
        self.notification_text = ""

        # Max iterations state
        self.waiting_for_continuation = False
        self.current_max_steps = 50

        # Key bindings
        self.kb = KeyBindings()
        
        # Mouse scroll handlers - track user scrolling to manage autoscroll
        @self.kb.add('<scroll-up>')
        def _(event):
            # User scrolled up - disable autoscroll
            self.autoscroll = False

        @self.kb.add('<scroll-down>')
        def _(event):
            # Check if we're at bottom to re-enable autoscroll
            ta = self.output_textarea
            w = ta.window if hasattr(ta, 'window') else None
            if w:
                info = w.render_info
                if info:
                    max_scroll = max(0, info.content_height - info.window_height)
                    if info.vertical_scroll >= max_scroll - 2:
                        self.autoscroll = True

        @self.kb.add('enter')
        def _(event):
            if self.app.layout.has_focus(self.input_window):
                text = self.input_buffer.text.strip()
                if not text:
                    return

                self.input_buffer.reset()
                
                # If user sends a message, snap to bottom to see response
                self.autoscroll = True
                # Move cursor to end - TextArea will auto-scroll
                self.output_textarea.buffer.cursor_position = len(self.log_content)
                if self.app:
                    self.app.invalidate()
                
                if self.is_processing:
                    self.input_queue.append(text)
                    self.print_rich(f"Queued: {text}\n")
                    self.notification_text = "Message queued."
                    asyncio.create_task(self.clear_notification())
                else:
                    asyncio.create_task(self.handle_input(text))
        
        @self.kb.add('c-c')
        def _(event):
            # If dialog is open, close it
            if self.root_container.floats:
                self.root_container.floats = []
                self.app.layout.focus(self.input_window)
                return

            now = time.time()
            if now - self.last_exit_attempt < 2.0:
                event.app.exit()
            else:
                self.last_exit_attempt = now
                self.notification_text = "Press Ctrl+C again to quit"
                asyncio.create_task(self.clear_notification())
            event.app.invalidate() 
        # Slash Command Completer
        slash_commands = ["/mode", "/backend", "/provider", "/model", "/setkey", "/clear", "/new", "/quit", "/test", "/help"]
        self.completer = WordCompleter(slash_commands, ignore_case=True)
        self.input_buffer = Buffer(multiline=False, completer=self.completer)

        self.input_window = Window(
             content=BufferControl(buffer=self.input_buffer),
             height=1, 
             wrap_lines=False
        )
        
        self.input_box = Frame(
            self.input_window,
            title=" > ",
            style="class:input-box" 
        )
        
        self.notification_window = Window(
            content=FormattedTextControl(lambda: HTML(f"<style fg='red'>{self.notification_text}</style>") if self.notification_text else ""),
            height=1,
            style="class:notification"
        )

        self.status_bar = Window(
            content=FormattedTextControl(self.get_status_bar_text),
            height=1,
            style="class:status-bar"
        )
        
        main_body = HSplit([
            self.output_window,
            Window(height=1, char=' '), 
            self.input_box,
            self.notification_window,
            self.status_bar
        ])
        
        self.root_container = FloatContainer(
            content=main_body,
            floats=[
                Float(xcursor=True, ycursor=True, content=CompletionsMenu(max_height=16, scroll_offset=1))
            ]
        )
        
        self.style = Style.from_dict({
            'input-box': '#ffffff',
            'status-bar': 'bg:#333333 #ffffff',
            'banner': 'bold cyan',
            'notification': 'bold red',
            'output': '#cccccc',
            'dialog': 'bg:#444444',
            'dialog frame.label': 'bg:#ffffff #000000',
            'dialog.body': 'bg:#000000 #ffffff',
            'dialog shadow': 'bg:#000000',
        })
        
        self.layout = Layout(self.root_container, focused_element=self.input_window)

    def show_menu(self, title, options, callback):
        def ok_handler():
            val = radio_list.current_value
            self.root_container.floats = [] # Close dialog
            self.app.layout.focus(self.input_window)
            if val:
                callback(val)
        
        def cancel_handler():
            self.root_container.floats = []
            self.app.layout.focus(self.input_window)

        radio_list = RadioList(options)
        
        # Key bindings for the dialog to allow Enter to submit
        dialog_kb = KeyBindings()
        @dialog_kb.add('enter')
        def _(event):
            ok_handler()

        dialog = Dialog(
            title=title,
            body=HSplit([
                Label(text="Select an option:", style="bold"),
                Window(height=1, char=' '),
                radio_list,
            ], key_bindings=dialog_kb),
            buttons=[
                Button(text="OK", handler=ok_handler),
                Button(text="Cancel", handler=cancel_handler),
            ],
            with_background=True
        )
        
        self.root_container.floats = [Float(content=dialog)]
        self.app.layout.focus(radio_list) # Focus the list

    async def clear_notification(self):
        await asyncio.sleep(2.0)
        self.notification_text = ""
        if self.app:
            self.app.invalidate()

        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0

    async def spinner_task(self):
        while self.is_processing:
            self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_frames)
            if self.app:
                self.app.invalidate()
            await asyncio.sleep(0.1)

    def show_input_dialog(self, title, label_text, callback, password=False):
        def ok_handler():
            val = text_area.text
            self.root_container.floats = [] 
            self.app.layout.focus(self.input_window)
            if val:
                callback(val)
        
        def cancel_handler():
            self.root_container.floats = []
            self.app.layout.focus(self.input_window)

        text_area = TextArea(multiline=False, password=password)
        
        # Key bindings for the dialog to allow Enter to submit
        dialog_kb = KeyBindings()
        @dialog_kb.add('enter')
        def _(event):
            ok_handler()

        dialog = Dialog(
            title=title,
            body=HSplit([
                Label(text=label_text, style="bold"),
                Window(height=1, char=' '),
                text_area,
            ], key_bindings=dialog_kb),
            buttons=[
                Button(text="OK", handler=ok_handler),
                Button(text="Cancel", handler=cancel_handler),
            ],
            with_background=True
        )
        
        self.root_container.floats = [Float(content=dialog)]
        self.app.layout.focus(text_area)

    async def _set_key_cb(self, val):
        GLOBAL_CONFIG.set_mistral_key(val)
        self.print_rich("Mistral API Key set successfully.\n")

    def get_status_bar_text(self):
        mem = psutil.virtual_memory()
        used_gb = round((mem.total - mem.available) / (1024**3), 1)
        cwd = os.getcwd().replace(os.path.expanduser("~"), "~")
        mode = GLOBAL_CONFIG.mode.upper()
        
        status_prefix = ""
        if self.is_processing:
            frame = self.spinner_frames[self.spinner_idx]
            status_prefix = f" <style fg='cyan'>{frame}</style> Processing... |"
        
        return HTML(
            f"{status_prefix}"
            f" <b>Dir:</b> {cwd} | "
            f"<b>Backend:</b> {GLOBAL_CONFIG.active_backend} | "
            f"<b>Model:</b> {GLOBAL_CONFIG.active_model.split('/')[-1]} | "
            f"<b>Mode:</b> {mode} | "
            f"<b>Mem:</b> {used_gb} GB"
        )
    
    def print_rich(self, renderable):
        """Print text to output, stripping all ANSI codes for plain text display"""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        if hasattr(renderable, '__rich__'):
            # Rich object - convert to plain text
            with rich_console.capture() as capture:
                rich_console.print(renderable, markup=False, highlight=False)
            text = capture.get()
            plain_text = ansi_escape.sub('', text)
        elif isinstance(renderable, str):
            # String - strip any ANSI codes
            plain_text = ansi_escape.sub('', renderable)
        else:
            # Fallback: convert to string and strip ANSI
            plain_text = ansi_escape.sub('', str(renderable))
        
        self.log_content += plain_text
        
        # Update TextArea buffer
        self.output_textarea.buffer.set_document(
            Document(text=self.log_content),
            bypass_readonly=True
        )
        
        # Auto-scroll to bottom if enabled
        if self.autoscroll:
            self.output_textarea.buffer.cursor_position = len(self.log_content)
            if self.app:
                self.app.invalidate()
            
    async def handle_input(self, text):
        self.is_processing = True
        spinner = asyncio.create_task(self.spinner_task())

        # Handle commands
        if text.startswith("/"):
            await self.handle_slash_command(text)
            self.is_processing = False
            await spinner
            return

        # Check if waiting for continuation response
        if self.waiting_for_continuation:
            self.waiting_for_continuation = False
            if text.lower().strip() in ["yes", "y"]:
                self.print_rich(f"\n> {text}\n\n")
                self.print_rich("Extending iterations by 50 and continuing...\n\n")
                self.agent.extend_max_steps(50)
                # Continue from where we left off
                try:
                    async for event in self.agent.step_gen("", continue_from_previous=True):
                        event_type = event["type"]
                        content = event.get("content", "")

                        if event_type == "status":
                            pass
                        elif event_type == "thought":
                            self.print_rich(f"\nThinking:\n{content}\n")
                        elif event_type == "tool_call":
                            self.print_rich(f"\nCalling Tool: {event['name']}\n")
                            args_str = str(event['arguments'])
                            if len(args_str) > 500:
                                args_str = args_str[:500] + "... (truncated)"
                            self.print_rich(f"{args_str}\n")
                        elif event_type == "tool_result":
                            short_res = str(event["result"])[:200] + "..." if len(str(event['result'])) > 200 else str(event['result'])
                            self.print_rich(f"Result: {short_res}\n")
                        elif event_type == "message":
                            self.print_rich(f"\nAlmanac:\n{content}\n")
                        elif event_type == "error":
                            self.print_rich(f"Error: {content}\n")
                        elif event_type == "max_iterations":
                            self.print_rich(f"\n{content}\n")
                            self.print_rich("Type 'yes' and press Enter to add 50 more iterations, or anything else to stop.\n")
                            self.waiting_for_continuation = True
                            self.current_max_steps = event.get("current_steps", 50)

                        self.app.invalidate()
                finally:
                    self.is_processing = False
                    await spinner
                    # Process next message in queue if any
                    if self.input_queue:
                        next_text = self.input_queue.pop(0)
                        asyncio.create_task(self.handle_input(next_text))
                return
            else:
                self.print_rich(f"\n> {text}\n\n")
                self.print_rich("Stopping. You can start a new task now.\n")
                self.is_processing = False
                await spinner
                return

        # Echo user input
        self.print_rich(f"\n> {text}\n\n")

        self.notification_text = ""

        try:
            async for event in self.agent.step_gen(text):
                event_type = event["type"]
                content = event.get("content", "")

                if event_type == "status":
                    pass
                elif event_type == "thought":
                    self.print_rich(f"\nThinking:\n{content}\n")
                elif event_type == "tool_call":
                    self.print_rich(f"\nCalling Tool: {event['name']}\n")
                    args_str = str(event['arguments'])
                    if len(args_str) > 500:
                        args_str = args_str[:500] + "... (truncated)"
                    self.print_rich(f"{args_str}\n")
                elif event_type == "tool_result":
                    short_res = str(event["result"])[:200] + "..." if len(str(event['result'])) > 200 else str(event['result'])
                    self.print_rich(f"Result: {short_res}\n")
                elif event_type == "message":
                    self.print_rich(f"\nAlmanac:\n{content}\n")
                elif event_type == "error":
                    self.print_rich(f"Error: {content}\n")
                elif event_type == "max_iterations":
                    self.print_rich(f"\n{content}\n")
                    self.print_rich("Type 'yes' and press Enter to add 50 more iterations, or anything else to stop.\n")
                    self.waiting_for_continuation = True
                    self.current_max_steps = event.get("current_steps", 50)

                self.app.invalidate()
        finally:
            self.is_processing = False
            await spinner

            # Process next message in queue if any
            if self.input_queue:
                next_text = self.input_queue.pop(0)
                asyncio.create_task(self.handle_input(next_text))

    async def handle_slash_command(self, text):
        parts = text.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "/clear":
            self.log_content = ""
            # Clear TextArea buffer
            self.output_textarea.buffer.set_document(Document(text=""), bypass_readonly=True)
            self.print_banner()
            
        elif cmd == "/new":
            # Clear output text
            self.log_content = ""
            self.output_textarea.buffer.set_document(Document(text=""), bypass_readonly=True)
            # Clear agent context
            self.agent.clear_history()
            # Print banner
            self.print_banner()
            self.print_rich("Context cleared. Starting fresh.\n")
            
        elif cmd == "/mode":
            if args:
                 # Direct setting
                 if args[0] in ["build", "run"]:
                    GLOBAL_CONFIG.mode = args[0]
                    self.print_rich(f"Mode switched to {args[0]}\n")
            else:
                # Interactive Menu
                self.show_menu(
                    title="Select Mode",
                    options=[("build", "Build Mode (Safe)"), ("run", "Run Mode (Execute)")],
                    callback=lambda val: asyncio.create_task(self._set_mode_cb(val))
                )

        elif cmd in ["/backend", "/provider"]:
            if args:
                 if GLOBAL_CONFIG.set_backend(args[0]):
                    self.print_rich(f"Backend switched to: {args[0]}\n")
                    # Display usage warning if present
                    backend_config = GLOBAL_CONFIG.get_active_backend_config()
                    if "usage_warning" in backend_config:
                        self.print_rich(backend_config["usage_warning"] + "\n")
            else:
                # Interactive Menu
                opts = [(k, k) for k in GLOBAL_CONFIG.BACKENDS.keys()]
                self.show_menu(
                    title="Select Backend",
                    options=opts,
                    callback=lambda val: asyncio.create_task(self._set_backend_cb(val))
                )

        elif cmd == "/model":
             if args:
                 GLOBAL_CONFIG.set_model(args[0])
                 self.print_rich(f"Model set to: {args[0]}\n")
             else:
                 # Get backend-specific model options
                 model_options = GLOBAL_CONFIG.get_model_options_for_backend()
                 self.show_menu(
                    title=f"Select Model ({GLOBAL_CONFIG.active_backend})",
                    options=model_options,
                    callback=lambda val: asyncio.create_task(self._set_model_cb(val))
                 )

        elif cmd == "/setkey":
            if args:
                GLOBAL_CONFIG.set_mistral_key(args[0])
                self.print_rich("Mistral API Key set successfully.\n")
            else:
                 self.show_input_dialog(
                     title="Set Mistral API Key",
                     label_text="Enter API Key:",
                     callback=lambda val: asyncio.create_task(self._set_key_cb(val)),
                     password=True
                 )
                 
        elif cmd == "/quit":
            self.app.exit()
        elif cmd == "/test":
            self.print_rich("Test output\n")
        else:
            self.print_rich(f"Unknown command: {cmd}\n")

    async def _set_mode_cb(self, val):
        GLOBAL_CONFIG.mode = val
        self.print_rich(f"Mode switched to {val}\n")
        
    async def _set_backend_cb(self, val):
        if GLOBAL_CONFIG.set_backend(val):
            self.print_rich(f"Backend switched to: {val}\n")
            # Display usage warning if present
            backend_config = GLOBAL_CONFIG.get_active_backend_config()
            if "usage_warning" in backend_config:
                self.print_rich(backend_config["usage_warning"] + "\n")
            
    async def _set_model_cb(self, val):
        GLOBAL_CONFIG.set_model(val)
        self.print_rich(f"Model set to: {val}\n")
            
    def print_banner(self):
        banner = """
 █████╗ ██╗     ███╗   ███╗ █████╗ ███╗   ██╗ █████╗  ██████╗
██╔══██╗██║     ████╗ ████║██╔══██╗████╗  ██║██╔══██╗██╔════╝
███████║██║     ██╔████╔██║███████║██╔██╗ ██║███████║██║     
██╔══██║██║     ██║╚██╔╝██║██╔══██║██║╚██╗██║██╔══██║██║     
██║  ██║███████╗██║ ╚═╝ ██║██║  ██║██║ ╚████║██║  ██║╚██████╗
╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝
"""
        tips = """
Tips for getting started:
1. Ask questions, edit files, or run commands.
2. Be specific for the best results.
3. Type /help for more information.
"""
        self.print_rich(banner)
        self.print_rich(tips)

    async def run(self):
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
            mouse_support=True
        )
        
        self.print_banner()
        await self.app.run_async()

async def start_ui():
    ui = AlmanacUI()
    await ui.run()
