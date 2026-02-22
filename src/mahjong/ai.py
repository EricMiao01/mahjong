from __future__ import annotations
from collections import Counter
from .tile import Tile


class SimpleAI:
    """簡易 AI 玩家決策邏輯"""

    @staticmethod
    def _sequence_potential(hand: list[Tile]) -> int:
        """計算手牌中的順子潛力分數（相鄰/接近張的對數）"""
        codes = {t.code for t in hand}
        score = 0
        for t in hand:
            if t.get_suit() >= 4:
                continue
            c = t.code
            if c + 1 in codes: score += 2
            if c + 2 in codes: score += 1
        return score

    @staticmethod
    def choose_discard(hand: list[Tile]) -> Tile:
        """選出最適合打出的牌（保留價值最低）"""
        code_count = Counter(t.code for t in hand)

        def keep_value(tile: Tile) -> int:
            suit = tile.get_suit()
            c = tile.code
            score = 0

            # 對子/刻子：高度保留
            cnt = code_count[c]
            if cnt >= 3: score += 8
            elif cnt == 2: score += 5

            # 順子潛力
            if suit <= 3:
                for nb in [c-2, c-1, c+1, c+2]:
                    if nb in code_count:
                        score += 3 - abs(nb - c)

            # 字牌（無法成順子）：偏向打出
            if suit == 4:
                score -= 2

            return score

        return min(hand, key=keep_value)

    @staticmethod
    def choose_pong(hand: list[Tile], tile: Tile) -> bool:
        """判斷是否應該碰牌"""
        suit = tile.get_suit()

        # 字牌：直接碰（無法成順子，不影響）
        if suit >= 4:
            return True

        # 數牌：模擬移除 2 張後，順子潛力下降多少
        pot_before = SimpleAI._sequence_potential(hand)

        hand_after = list(hand)
        removed = 0
        for i in range(len(hand_after) - 1, -1, -1):
            if hand_after[i].code == tile.code and removed < 2:
                hand_after.pop(i)
                removed += 1

        pot_after = SimpleAI._sequence_potential(hand_after)

        # 只有潛力下降不超過 25% 才碰
        if pot_before == 0:
            return True
        return (pot_before - pot_after) / pot_before <= 0.25

    @staticmethod
    def choose_reaction(
        hand: list[Tile],
        tile: Tile,
        actions: list[tuple[str, object]]
    ) -> tuple[str, object] | None:
        """
        從可行動列表中選擇行動。
        actions: [(action, extra), ...] 已依優先順序排好。
        回傳 (action, extra) 或 None（略過）。
        """
        action_map = {a: e for a, e in actions}

        if "胡" in action_map:
            return ("胡", None)

        if "槓" in action_map:
            if SimpleAI.choose_pong(hand, tile):
                return ("槓", None)

        if "碰" in action_map:
            if SimpleAI.choose_pong(hand, tile):
                return ("碰", None)

        chow_opts = [(a, e) for a, e in actions if a == "吃"]
        if chow_opts:
            return chow_opts[0]

        return None
