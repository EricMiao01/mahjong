from __future__ import annotations
import random
from .tile import Tile


class Deck:
    """還沒被抽走的牌庫"""

    tiles: list[Tile]
    front_index: int
    back_index: int

    def __init__(self):
        self.tiles = []

        suit_config = {
            1: (range(1, 10), 4),  # 萬
            2: (range(1, 10), 4),  # 筒
            3: (range(1, 10), 4),  # 條
            4: (range(1,  8), 4),  # 字（東南西北中發白）
            5: (range(1,  9), 1),  # 花（梅蘭竹菊春夏秋冬，各一張）
        }
        for suit, (values, copies) in suit_config.items():
            for value in values:
                for i in range(copies):
                    code = suit * 10 + value
                    self.tiles.append(Tile(code))

        self.front_index = 0
        self.back_index = len(self.tiles) - 1

    def __str__(self) -> str:
        return " ".join([str(tile) for tile in self.tiles])

    def shuffle(self):
        for i in range(len(self.tiles) - 1, 0, -1):
            j = random.randint(0, i)
            self.tiles[i], self.tiles[j] = self.tiles[j], self.tiles[i]

    def draw_from_front(self) -> Tile:
        tile = self.tiles[self.front_index]
        self.front_index += 1
        return tile

    def draw_from_back(self) -> Tile:
        tile = self.tiles[self.back_index]
        self.back_index -= 1
        return tile

    def get_remaining_tiles_count(self) -> int:
        return self.back_index - self.front_index + 1
