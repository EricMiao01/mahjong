from __future__ import annotations
from .tile import Tile


class RuleEngine:
    def can_pong(hand: list[Tile], tile: Tile) -> bool:
        return hand.count(tile) >= 2

    def can_kong(hand: list[Tile], tile: Tile) -> bool:
        return hand.count(tile) >= 3

    def can_concealed_kong(hand: list[Tile]) -> list[Tile]:
        """回傳手牌中可以暗槓的牌（出現 4 次的牌），每種只回傳一個代表。"""
        seen: set[int] = set()
        result: list[Tile] = []
        for tile in hand:
            if tile.code not in seen and hand.count(tile) >= 4:
                seen.add(tile.code)
                result.append(tile)
        return result

    def can_chow(hand: list[Tile], tile: Tile) -> list[tuple[Tile, Tile]]:
        if tile.get_suit() >= 4:
            return []

        hand_codes = {t.code for t in hand}

        options = []
        if tile.code - 2 in hand_codes and tile.code - 1 in hand_codes:
            options.append((tile.code - 2, tile.code - 1))

        if tile.code - 1 in hand_codes and tile.code + 1 in hand_codes:
            options.append((tile.code - 1, tile.code + 1))

        if tile.code + 1 in hand_codes and tile.code + 2 in hand_codes:
            options.append((tile.code + 1, tile.code + 2))

        return options

    def can_replace_flower(hand: list[Tile], tile: Tile) -> bool:
        return tile.get_suit() == 5

    def is_hu(hand: list[Tile], tile: Tile) -> bool:
        tiles_to_check = hand.copy()
        if tile:
            tiles_to_check.append(tile)

        # 台灣 16 張胡牌必為 3n+2 張
        if len(tiles_to_check) % 3 != 2:
            return False

        counts = {code: 0 for code in range(11, 50)}
        for tile in tiles_to_check:
            counts[tile.code] += 1

        def check_melds(c_dict):
            for i in range(11, 50):
                if c_dict[i] > 0:

                    # 檢查刻子
                    if c_dict[i] >= 3:
                        c_dict[i] -= 3
                        if check_melds(c_dict):
                            return True
                        c_dict[i] += 3

                    # 檢查順子
                    if i % 10 <= 7 and c_dict[i+1] > 0 and c_dict[i+2] > 0:
                        c_dict[i] -= 1
                        c_dict[i+1] -= 1
                        c_dict[i+2] -= 1
                        if check_melds(c_dict):
                            return True
                        c_dict[i] += 1
                        c_dict[i+1] += 1
                        c_dict[i+2] += 1

                    return False
            return True

        for i in range(11, 50):
            if counts[i] >= 2:
                counts[i] -= 2
                if check_melds(counts):
                    return True
                counts[i] += 2
        return False

    def get_ting_tiles(hand: list[Tile]) -> list[Tile]:
        if len(hand) % 3 != 1:
            return []

        ting_tiles = []

        _valid_codes = (
            list(range(11, 20)) + list(range(21, 30)) +
            list(range(31, 40)) + list(range(41, 48))
        )
        all_tiles = [Tile(code) for code in _valid_codes]
        for tile in all_tiles:
            if hand.count(tile) == 4:
                continue
            if RuleEngine.is_hu(hand, tile):
                ting_tiles.append(tile)

        return ting_tiles

    @staticmethod
    def get_tenpai_advice(hand: list[Tile]) -> dict[int, list[Tile]]:
        """
        計算手牌中打掉哪張牌可以聽牌。
        回傳 {code: ting_tiles} 字典，code 為可以打出的牌種。
        """
        advice: dict[int, list[Tile]] = {}
        seen_codes: set[int] = set()
        for i, tile in enumerate(hand):
            if tile.code in seen_codes:
                continue
            seen_codes.add(tile.code)
            trial = hand[:i] + hand[i+1:]
            ting = RuleEngine.get_ting_tiles(trial)
            if ting:
                advice[tile.code] = ting
        return advice
