  │                                                                                           
  │                                                                                           
Traceback (most recent call last):
  File "/home/runner/workspace/main.py", line 5, in <module>
    main()
  File "/home/runner/workspace/src/cli.py", line 649, in main
    repl.run()
  File "/home/runner/workspace/src/cli.py", line 619, in run
    self.cmd_go()
  File "/home/runner/workspace/src/cli.py", line 377, in cmd_go
    if not self.prompt_for_idea():
           ^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/workspace/src/cli.py", line 307, in prompt_for_idea
    idea_path.write_text(idea_content)
  File "/nix/store/7d088dip86hlzri9sk0h78b63yfmx0a0-python3-3.11.13/lib/python3.11/pathlib.py", line 1078, in write_text
    with self.open(mode='w', encoding=encoding, errors=errors, newline=newline) as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/nix/store/7d088dip86hlzri9sk0h78b63yfmx0a0-python3-3.11.13/lib/python3.11/pathlib.py", line 1044, in open
    return io.open(self, mode, buffering, encoding, errors, newline)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: '/home/runner/workspace/start/idea.md'
~/workspace$ 