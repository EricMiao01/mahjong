import sys
import os
import curses
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from mahjong.game import Game


def main(stdscr):
    game = Game(stdscr)
    game.run()


if __name__ == "__main__":
    curses.wrapper(main)
