from __future__ import annotations


class Tile:
    """麻將牌"""

    code: int   # 萬: 1X, 筒: 2X, 條: 3X, 字: 4X, 花: 5X

    def __init__(self, code: int):
        self.code = code

    def get_suit(self) -> int:
        """回傳花色
        1: 萬
        2: 筒
        3: 條
        4: 字
        5: 花
        """
        return self.code // 10

    def get_value(self) -> int:
        """回傳數值
        1-9: 一般數牌（萬筒條）
        1-7: 東南西北中發白
        1-8: 梅蘭竹菊春夏秋冬
        """
        return self.code % 10

    def to_string(self) -> str:
        """回傳麻將牌的中文字串"""
        suit = self.get_suit()
        value = self.get_value()

        suit_decode_map = {
            1: "萬", 2: "筒", 3: "條", 4: "字", 5: "花",
        }

        value_decode_map = {
            1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
            6: "六", 7: "七", 8: "八", 9: "九",
        }

        honor_decode_map = {
            1: "東", 2: "南", 3: "西", 4: "北",
            5: "中", 6: "發", 7: "白",
        }

        flower_decode_map = {
            1: "梅", 2: "蘭", 3: "竹", 4: "菊",
            5: "春", 6: "夏", 7: "秋", 8: "冬",
        }

        if suit == 4:
            return honor_decode_map[value]
        elif suit == 5:
            return flower_decode_map[value]
        else:
            return value_decode_map[value] + suit_decode_map[suit]

    def __str__(self) -> str:
        return self.to_string()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tile):
            return False
        return self.code == other.code

    def __hash__(self) -> int:
        return hash(self.code)

    def __repr__(self) -> str:
        return f"Tile(code={self.code}, str={self.to_string()})"
