import os
import sys

# Allow direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dotcraft

if __name__ == '__main__':
    dotcraft.main()