import sys
from .orchestrator import main as orchestrator_main
from .deployer import main as deployer_main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "deploy":
        deployer_main()
    else:
        orchestrator_main()