
import os
from src.tools import create_notebook, add_multiple_cells

filename = "debug_nb.ipynb"
if os.path.exists(filename):
    os.remove(filename)

print("Creating notebook...")
print(create_notebook(filename))

cells_data = [
    {'content': "# Welcome", 'type': 'markdown'},
    {'content': 'print("Hello")', 'type': 'code'}
]

print("Adding multiple cells...")
try:
    res = add_multiple_cells(filename, cells_data)
    print(f"Result: {res}")
except Exception as e:
    print(f"CRASH: {e}")
