import os
import shutil
from src.tools import create_notebook, add_cell, read_notebook, run_notebook, edit_notebook
from src.config import GLOBAL_CONFIG

def test_tools():
    test_file = "test_nb.ipynb"
    if os.path.exists(test_file):
        os.remove(test_file)
        
    print("1. Testing create_notebook...")
    res = create_notebook(test_file)
    print(res)
    assert os.path.exists(test_file)
    
    print("2. Testing add_cell...")
    res = add_cell(test_file, "print('Hello World')", "code")
    print(res)
    
    print("3. Testing read_notebook...")
    content = read_notebook(test_file)
    print(content)
    assert "Hello World" in content
    
    print("4. Testing run_notebook (Build Mode - Should Fail)...")
    GLOBAL_CONFIG.mode = "build"
    res = run_notebook(test_file)
    print(res)
    assert "Action Prevented" in res
    
    print("5. Testing run_notebook (Run Mode)...")
    GLOBAL_CONFIG.mode = "run"
    res = run_notebook(test_file)
    print(res)
    
    content_after_run = read_notebook(test_file)
    print("Content after run:", content_after_run)
    # Check if we can find output (depends on if nbclient executes and saves back)
    # nbclient executes in-memory usually unless we write it back. My run_notebook writes it back.
    
    print("6. Testing edit_notebook...")
    res = edit_notebook(test_file, 0, "print('Edited')")
    print(res)
    content_edited = read_notebook(test_file)
    assert "Edited" in content_edited
    
    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)
        
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_tools()
