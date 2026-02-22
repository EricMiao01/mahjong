from __future__ import annotations
import random

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


class RuleEngine:
    def can_pong(hand: list[Tile], tile: Tile) -> bool:
        return hand.count(tile) >= 2

    def can_kong(hand: list[Tile], tile: Tile) -> bool:
        return hand.count(tile) >= 3

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
                    if c_dict[i] >=3:
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

        _valid_codes = list(range(11, 20)) + list(range(21, 30)) + list(range(31, 40)) + list(range(41, 48))
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
        advice: dict[int, list[Tile]] = {}  # code -> ting_tiles
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
        from collections import Counter
        code_count = Counter(t.code for t in hand)

        def keep_value(tile: Tile) -> int:
            suit = tile.get_suit()
            value = tile.get_value()
            c = tile.code
            score = 0

            # 對子/刻子：高度保留
            cnt = code_count[c]
            if cnt >= 3: score += 8
            elif cnt == 2: score += 5

            # 順子潛力
            if suit <= 3:
                neighbors = [c-2, c-1, c+1, c+2]
                for nb in neighbors:
                    if nb in code_count:
                        dist = abs(nb - c)
                        score += (3 - dist)  # 越近分越高

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

        # 模擬從手牌移除 2 張該牌
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

        # 1. 一定胡
        if "胡" in action_map:
            return ("胡", None)

        # 2. 槓
        if "槓" in action_map:
            if SimpleAI.choose_pong(hand, tile):
                return ("槓", None)

        # 3. 碰（考慮順子影響）
        if "碰" in action_map:
            if SimpleAI.choose_pong(hand, tile):
                return ("碰", None)

        # 4. 吃（選第一個選項）
        chow_opts = [(a, e) for a, e in actions if a == "吃"]
        if chow_opts:
            return chow_opts[0]

        return None  # 略過


class Game:
    def __init__(self, ai_players: set[int] | None = None):
        self.deck = Deck()
        self.players = [Player() for _ in range(4)]
        self.current_player = 0
        self.current_wind = 1
        # ai_players: 哪幾位玩家由 AI 操作，預設 1/2/3
        self.ai_players: set[int] = ai_players if ai_players is not None else {1, 2, 3}

    def start_game(self):
        self.deck.shuffle()
        for _ in range(16):
            for player in self.players:
                player.add_tile_to_hand(self.deck.draw_from_front())
        for player in self.players:
            player.order_hand()

    # ── 顯示 ──────────────────────────────────────────

    def _show_table(self, highlight_player: int = -1):
        """顯示所有玩家的亮牌與棄牌"""
        print(f"\n{'='*50}")
        for i, p in enumerate(self.players):
            mark = " <- 出牌" if i == highlight_player else ""
            melded = " ".join(str(t) for t in p.melded_tiles) or "-"
            flowers = " ".join(str(t) for t in p.flower_tiles) or "-"
            discarded = " ".join(str(t) for t in p.discarded_tiles) or "-"
            print(f" 玩家 {i}{mark}")
            print(f"   亮牌: {melded}   花: {flowers}")
            print(f"   棄牌: {discarded}")
        print(f"{'='*50}")

    def _show_hand(self, player_idx: int):
        player = self.players[player_idx]
        print(f"\n-- 玩家 {player_idx} 的手牌 --")
        for i, tile in enumerate(player.hand_tiles):
            print(f"  [{i:2d}] {tile}", end="")
        print()

    # ── 補花 ──────────────────────────────────────────

    def _handle_flowers(self, player_idx: int) -> bool:
        """補花。回傳 True 表示玩家集齊八花，游戲結束。"""
        player = self.players[player_idx]
        while True:
            flowers = [t for t in player.hand_tiles if t.get_suit() == 5]
            if not flowers:
                break
            for f in flowers:
                print(f"  玩家 {player_idx} 補花：{f}")
                player.declare_replace_flower(f)
                player.add_tile_to_hand(self.deck.draw_from_back())
            player.order_hand()

            # 八花胡判斷
            if len(player.flower_tiles) >= 8:
                player.is_winner = True
                print(f"\n*** 玩家 {player_idx} 集齊八花，花胡！ ***")
                return True
        return False

    # ── 玩家選擇打哪張牌 ───────────────────────────────

    def _prompt_discard(self, player_idx: int) -> Tile:
        player = self.players[player_idx]

        if player_idx in self.ai_players:
            tile = SimpleAI.choose_discard(player.hand_tiles)
            print(f"  [AI] 玩家 {player_idx} 打出：{tile}")
            return tile

        self._show_table()
        self._show_hand(player_idx)

        # 聽牌建議：對每張可打的牌模擬移除，看看是否聽牌
        advice = RuleEngine.get_tenpai_advice(player.hand_tiles)
        if advice:
            print("  [*] 聽牌建議：")
            for code, ting_tiles in advice.items():
                discard_tile = Tile(code)
                ting_str = " ".join(str(t) for t in ting_tiles)
                print(f"      打 {discard_tile} 可聽: {ting_str}")

        while True:
            try:
                idx = int(input(f"玩家 {player_idx}，請選擇要打出的牌（輸入編號）: "))
                if 0 <= idx < len(player.hand_tiles):
                    return player.hand_tiles[idx]
            except ValueError:
                pass
            print("  無效輸入，請重試")

    # ── 其他玩家對棄牌的反應 ───────────────────────────

    def _prompt_reactions(self, discarder: int, tile: Tile) -> tuple[int, str, object] | None:
        """
        詢問其他玩家是否要碰/槓/吃/胡。
        回傳 (player_idx, action, extra) 或 None（所有人都略過）。
        優先順序：胡 > 碰/槓 > 吃（只有下家可吃）。
        """
        self._show_table(highlight_player=discarder)

        # 收集每位玩家的可行動列表 {player_idx: [(action, extra), ...]}
        player_actions: dict[int, list[tuple[str, object]]] = {}

        for offset in range(1, 4):
            idx = (discarder + offset) % 4
            player = self.players[idx]
            actions: list[tuple[str, object]] = []

            if RuleEngine.is_hu(player.hand_tiles, tile):
                actions.append(("胡", None))
            if RuleEngine.can_pong(player.hand_tiles, tile):
                actions.append(("碰", None))
            if RuleEngine.can_kong(player.hand_tiles, tile):
                actions.append(("槓", None))
            if offset == 1:
                for opt in RuleEngine.can_chow(player.hand_tiles, tile):
                    actions.append(("吃", opt))

            if actions:
                player_actions[idx] = actions

        if not player_actions:
            return None

        # 依照出牌順序詢問每位玩家（胡優先：先收集胡，再詢問）
        # 優先順序：胡 > 碰/槓 > 吃
        priority = {"胡": 0, "碰": 1, "槓": 1, "吃": 2}

        for offset in range(1, 4):
            idx = (discarder + offset) % 4
            if idx not in player_actions:
                continue

            actions = player_actions[idx]
            actions.sort(key=lambda a: priority[a[0]])

            # === AI 玩家：自動决策 ===
            if idx in self.ai_players:
                decision = SimpleAI.choose_reaction(self.players[idx].hand_tiles, tile, actions)
                if decision is None:
                    print(f"  [AI] 玩家 {idx} 略過")
                    continue
                action_str, extra = decision
                if action_str == "吃":
                    label = f"吃 {Tile(extra[0])}{Tile(extra[1])}"
                else:
                    label = action_str
                print(f"  [AI] 玩家 {idx} 選擇：{label}")
                return (idx, action_str, extra)

            # === 人工玩家：顯示選項 ===
            # 建立選項列表
            options: list[tuple[str, str, object]] = []   # (顯示文字, action, extra)
            for action, extra in actions:
                if action == "吃":
                    label = f"吃 {Tile(extra[0])}{Tile(extra[1])}"
                else:
                    label = action
                options.append((label, action, extra))
            options.append(("略過", "略過", None))

            # 顯示該玩家的手牌，讓他能做決定
            self._show_hand(idx)
            print(f"\n玩家 {idx} 可以：")
            for i, opt in enumerate(options):
                print(f"  [{i}] {opt[0]}")

            while True:
                try:
                    sel = int(input("請選擇（輸入編號）: ").strip())
                    if 0 <= sel < len(options):
                        break
                except ValueError:
                    pass
                print("  無效輸入，請重試")

            chosen_label, chosen_action, chosen_extra = options[sel]

            if chosen_action == "略過":
                continue
            return (idx, chosen_action, chosen_extra)

        return None

    # ── 打牌後反應（遞迴處理碰/吃/槓/胡）──────────────

    def _after_discard(self, player_idx: int, discard: Tile) -> bool:
        """玩家打出一張牌後，處理所有其他玩家的反應。回傳 True 表示遊戲結束。"""
        result = self._prompt_reactions(player_idx, discard)

        if result is None:
            self.current_player = (player_idx + 1) % 4
            return False

        winner_idx, action, extra = result

        if action == "胡":
            self.players[winner_idx].declare_hu(discard)
            print(f"\n*** 玩家 {winner_idx} 胡牌！（{discard}） ***")
            return True

        if action == "碰":
            self.players[winner_idx].declare_pong(discard)
            print(f"玩家 {winner_idx} 碰！")

        elif action == "槓":
            self.players[winner_idx].declare_kong(discard)
            print(f"玩家 {winner_idx} 槓！")
            # 槓後補牌（從塔後抽）
            extra_tile = self.deck.draw_from_back()
            self.players[winner_idx].add_tile_to_hand(extra_tile)
            self.players[winner_idx].order_hand()
            self._handle_flowers(winner_idx)

        elif action == "吃":
            self.players[winner_idx].declare_chow(discard, extra)
            print(f"玩家 {winner_idx} 吃！")

        # 碰/槓/吃 後：winner_idx 打一張牌，再遞迴處理反應
        self.current_player = winner_idx
        discard2 = self._prompt_discard(winner_idx)
        self.players[winner_idx].discard_tile(discard2)
        print(f"玩家 {winner_idx} 打出：{discard2}")
        return self._after_discard(winner_idx, discard2)

    # ── 單回合 ────────────────────────────────────────

    def play_turn(self) -> bool:
        """執行目前玩家的回合。回傳 True 表示遊戲結束。"""
        idx = self.current_player
        player = self.players[idx]

        # 1. 摸牌
        if self.deck.get_remaining_tiles_count() <= 16:  # 剩 8 墩（16 張）和局
            print("\n牌已剩 8 墩，流局！")
            return True

        tile = self.deck.draw_from_front()
        player.add_tile_to_hand(tile)
        player.order_hand()
        print(f"\n{'─'*40}")
        print(f"玩家 {idx} 摸牌：{tile}（牌庫剩 {self.deck.get_remaining_tiles_count()} 張）")

        # 2. 補花
        if self._handle_flowers(idx):
            return True  # 八花胡

        # 3. 自摸判斷
        if RuleEngine.is_hu(player.hand_tiles, None):
            if idx in self.ai_players:
                player.declare_hu(None)
                print(f"\n*** 玩家 {idx} 自摸胡牌！ ***")
                return True
            self._show_hand(idx)
            ans = input(f"玩家 {idx} 可以自摸！要胡嗎？(y/n): ").strip().lower()
            if ans == "y":
                player.declare_hu(None)
                print(f"\n*** 玩家 {idx} 自摸胡牌！ ***")
                return True

        # 4. 打牌 → 處理反應
        discard = self._prompt_discard(idx)
        player.discard_tile(discard)
        print(f"玩家 {idx} 打出：{discard}")
        return self._after_discard(idx, discard)


    # ── 主迴圈 ────────────────────────────────────────

    def run(self):
        print("=" * 40)
        print("      歡迎來到終端機麻將！")
        print("=" * 40)
        print("玩家 0~3，哪幾位由 AI 操作？")
        print("  Enter    : 預設 [1 2 3]（只有你是玩家 0）")
        print("  0 1 2 3  : 指定哪幾位是 AI")
        print("  a        : 全部 AI（觀戰模式）")
        raw = input("請選擇: ").strip().lower()
        if raw == "a":
            self.ai_players = {0, 1, 2, 3}
        elif raw:
            try:
                self.ai_players = {int(x) for x in raw.split() if x in "0123"}
            except ValueError:
                print("輸入無效，使用預設 [1 2 3]")
        human = sorted(set(range(4)) - self.ai_players)
        print(f"AI 玩家: {sorted(self.ai_players) or '無'}，人工玩家: {human or '無（觀戰模式）'}")
        print()
        self.start_game()

        # 發牌後補花
        for i in range(4):
            if self._handle_flowers(i):  # 八花胡
                print("\n游戲結束！")
                return
            self.players[i].order_hand()

        while True:
            if self.play_turn():
                break

        print("\n遊戲結束！")
        for i, p in enumerate(self.players):
            status = "[勝利者]" if p.is_winner else ""
            print(f"玩家 {i}: {p} {status}")


if __name__ == "__main__":
    game = Game()
    game.run()
