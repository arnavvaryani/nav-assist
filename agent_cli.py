import sys
from app import run_agent

if __name__ == "__main__":
    task_input = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_agent(task_input)
    print(result)
