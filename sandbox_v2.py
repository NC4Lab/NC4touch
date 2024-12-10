import os
import sys
import time

def test_script():
    print("Python is running on this system!")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    # Simple time delay test
    print("Starting a 3-second timer...")
    time.sleep(3)
    print("Timer complete!")
    
if __name__ == "__main__":
    test_script()
