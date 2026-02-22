import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mahjong.game import Game

if __name__ == "__main__":
    game = Game()
    game.run()
