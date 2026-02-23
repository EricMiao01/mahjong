from __future__ import annotations
from .tile import Tile


class Player:
    """玩家"""

    name: str
    hand_tiles: list[Tile]
    melded_tiles: list[Tile]
    discarded_tiles: list[Tile]
    flower_tiles: list[Tile]
    is_winner: bool

    def __init__(self):
        self.hand_tiles = []
        self.melded_tiles = []   # 已亮出的面子（碰/槓/吃）
        self.discarded_tiles = []
        self.flower_tiles = []   # 補進來的花牌
        self.is_winner = False

    def __str__(self) -> str:
        return " ".join([str(tile) for tile in self.hand_tiles])

    def add_tile_to_hand(self, tile: Tile):
        self.hand_tiles.append(tile)

    def discard_tile(self, tile: Tile):
        self.hand_tiles.remove(tile)
        self.discarded_tiles.append(tile)

    def order_hand(self):
        self.hand_tiles.sort(key=lambda tile: tile.code)

    def declare_pong(self, tile: Tile):
        """碰牌：從手牌移除 2 張，將 3 張（含棄牌）加入 melded_tiles"""
        for _ in range(2):
            self.hand_tiles.remove(tile)
        self.melded_tiles.extend([tile, tile, tile])

    def declare_kong(self, tile: Tile):
        """槓牌：從手牌移除 3 張，將 4 張（含棄牌）加入 melded_tiles"""
        for _ in range(3):
            self.hand_tiles.remove(tile)
        self.melded_tiles.extend([tile, tile, tile, tile])

    def declare_concealed_kong(self, tile: Tile):
        """暗槓：從手牌移除 4 張，將 4 張加入 melded_tiles"""
        for _ in range(4):
            self.hand_tiles.remove(tile)
        self.melded_tiles.extend([tile, tile, tile, tile])


    def declare_chow(self, tile: Tile, option: tuple[int, int]):
        """吃牌：option 為手牌中兩張的 code；從手牌移除這兩張，將 3 張加入 melded_tiles"""
        code_a, code_b = option
        tile_a = next(t for t in self.hand_tiles if t.code == code_a)
        tile_b = next(t for t in self.hand_tiles if t.code == code_b)
        self.hand_tiles.remove(tile_a)
        self.hand_tiles.remove(tile_b)
        self.melded_tiles.extend([tile_a, tile, tile_b])
        self.melded_tiles.sort(key=lambda t: t.code)

    def declare_replace_flower(self, tile: Tile):
        """補花：將花牌從手牌移至 flower_tiles（補牌由 Game 層負責）"""
        self.hand_tiles.remove(tile)
        self.flower_tiles.append(tile)

    def declare_hu(self, tile: Tile | None):
        """胡牌：若 tile 不為 None（別人打的牌），加入手牌，標記勝利"""
        if tile:
            self.hand_tiles.append(tile)
        self.is_winner = True
