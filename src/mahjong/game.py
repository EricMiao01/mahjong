from __future__ import annotations
from .tile import Tile
from .deck import Deck
from .player import Player
from .rule_engine import RuleEngine
from .ai import SimpleAI


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
        """補花。回傳 True 表示玩家集齊八花，遊戲結束。"""
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
            options: list[tuple[str, str, object]] = []
            for action, extra in actions:
                if action == "吃":
                    label = f"吃 {Tile(extra[0])}{Tile(extra[1])}"
                else:
                    label = action
                options.append((label, action, extra))
            options.append(("略過", "略過", None))

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
        if self.deck.get_remaining_tiles_count() <= 16:
            print("\n牌已剩 8 墩，流局！")
            return True

        tile = self.deck.draw_from_front()
        player.add_tile_to_hand(tile)
        player.order_hand()
        print(f"\n{'─'*40}")
        print(f"玩家 {idx} 摸牌：{tile}（牌庫剩 {self.deck.get_remaining_tiles_count()} 張）")

        # 2. 補花
        if self._handle_flowers(idx):
            return True

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
            if self._handle_flowers(i):
                print("\n遊戲結束！")
                return
            self.players[i].order_hand()

        while True:
            if self.play_turn():
                break

        print("\n遊戲結束！")
        for i, p in enumerate(self.players):
            status = "[勝利者]" if p.is_winner else ""
            print(f"玩家 {i}: {p} {status}")
