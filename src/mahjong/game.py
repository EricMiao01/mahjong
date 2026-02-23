from __future__ import annotations
import curses

from .tile import Tile
from .deck import Deck
from .player import Player
from .rule_engine import RuleEngine
from .ai import SimpleAI
from . import ui


class Game:
    def __init__(self, stdscr, ai_players: set[int] | None = None):
        self.stdscr = stdscr
        self.deck = Deck()
        self.players = [Player() for _ in range(4)]
        self.current_player = 0
        self.current_wind = 1
        # ai_players: 哪幾位玩家由 AI 操作，預設 1/2/3
        self.ai_players: set[int] = ai_players if ai_players is not None else {1, 2, 3}
        self._show_advice = True   # 是否顯示聽牌建議
        self._winner: int | None = None      # 胡牌者
        self._discarder: int | None = None   # 放槍者（自摸為 None）
        self._winning_tile: Tile | None = None  # 胡的那張牌
        self._last_discard_info: str = ""   # 常駐顯示在分隔線下方

    def start_game(self):
        self.deck.shuffle()
        for _ in range(16):
            for player in self.players:
                player.add_tile_to_hand(self.deck.draw_from_front())
        for player in self.players:
            player.order_hand()

    def _end_game(self):
        self._show_msg("遊戲結束！", pause=True)

    # ── 補花 ──────────────────────────────────────────

    def _handle_flowers(self, player_idx: int) -> tuple[bool, Tile | None]:
        """補花。回傳 (是否結束遊戲, 最後摸進的牌)。"""
        player = self.players[player_idx]
        last_drawn = None
        while True:
            flowers = [t for t in player.hand_tiles if t.get_suit() == 5]
            if not flowers:
                break
            for f in flowers:
                player.declare_replace_flower(f)
                last_drawn = self.deck.draw_from_back()
                player.add_tile_to_hand(last_drawn)
            player.order_hand()

            if len(player.flower_tiles) >= 8:
                player.is_winner = True
                self._show_msg(f"玩家 {player_idx} 集齊八花，花胡！", pause=True)
                return True, last_drawn
        return False, last_drawn

    def _apply_flowers(self, player_idx: int, current_tile: Tile | None) -> tuple[bool, Tile | None]:
        """執行補花並更新 current_tile（若有補進新牌就用最後補進的牌覆蓋）。"""
        is_over, drawn = self._handle_flowers(player_idx)
        if drawn is not None:
            current_tile = drawn
        return is_over, current_tile

    # ── 暗槓 ──────────────────────────────────────────

    def _apply_concealed_kong(self, player_idx: int, current_tile: Tile | None) -> tuple[bool, Tile | None]:
        """執行暗槓（可能連續多次）並更新 current_tile（若有摸進新牌就覆蓋）。"""
        is_over, drawn = self._handle_concealed_kong(player_idx, newly_drawn=current_tile)
        if drawn is not None:
            current_tile = drawn
        return is_over, current_tile

    def _do_concealed_kong(self, player_idx: int, tile: Tile, actor_tag: str) -> tuple[bool, Tile | None]:
        """執行一次暗槓流程（宣告→補槓牌→補花），回傳 (是否結束遊戲, 最後摸進的牌)。"""
        player = self.players[player_idx]
        player.declare_concealed_kong(tile)
        last_drawn = self.deck.draw_from_back()
        player.add_tile_to_hand(last_drawn)
        player.order_hand()
        self._show_msg(f"{actor_tag}玩家 {player_idx} 暗槓：{tile}", pause=False)
        return self._apply_flowers(player_idx, last_drawn)

    def _handle_concealed_kong(self, player_idx: int, newly_drawn: Tile | None = None) -> tuple[bool, Tile | None]:
        """
        處理暗槓。會一直詢問直到玩家不再暗槓為止。
        - AI：有暗槓就做。
        - 人工：顯示選項讓玩家選哪張要暗槓，或略過。
        回傳 (是否結束遊戲, 最後摸進的牌)。
        """
        player = self.players[player_idx]

        last_drawn = None
        while True:
            kong_tiles = RuleEngine.can_concealed_kong(player.hand_tiles)
            if not kong_tiles:
                return False, last_drawn

            # AI：直接做第一個可暗槓的牌
            if player_idx in self.ai_players:
                tile = kong_tiles[0]
                is_over, last_drawn = self._do_concealed_kong(player_idx, tile, actor_tag="[AI] ")
                if is_over:
                    return True, last_drawn
                continue  # 摸到新牌後再判斷一次

            # 人工：提供選項
            option_labels = [f"暗槓 {t}" for t in kong_tiles] + ["略過"]
            sel = ui.select_from_options(
                self.stdscr,
                self.players,
                player_idx,
                self.ai_players,
                self.deck.get_remaining_tiles_count(),
                option_labels,
                msg=f"玩家 {player_idx} 可以暗槓",
            )

            if sel == len(option_labels) - 1:  # 略過
                return False, last_drawn

            chosen_tile = kong_tiles[sel]
            is_over, last_drawn = self._do_concealed_kong(player_idx, chosen_tile, actor_tag="")
            if is_over:
                return True, last_drawn
            # 繼續迴圈，看摸到的新牌是否又能暗槓

    # ── 訊息顯示 ──────────────────────────────────────

    def _show_msg(self, msg: str, pause: bool = False):
        """在目前畫面底部狀態列顯示訊息，pause=True 時等待按鍵。"""
        ui.draw_table(
            self.stdscr,
            self.players,
            self.current_player,
            self.ai_players,
            self.deck.get_remaining_tiles_count(),
            msg=msg,
            sub_msg=self._last_discard_info,
        )
        ui.draw_hint_bar(
            self.stdscr,
            "按任意鍵繼續..." if pause else ""
        )
        self.stdscr.refresh()
        if pause:
            self.stdscr.getch()

    # ── 玩家選擇打哪張牌 ───────────────────────────────

    def _prompt_discard(self, player_idx: int, newly_drawn: Tile | None = None) -> Tile:
        player = self.players[player_idx]

        if player_idx in self.ai_players:
            tile = SimpleAI.choose_discard(player.hand_tiles)
            self._show_msg(f"[AI] 玩家 {player_idx} 打出：{tile}", pause=False)
            self.stdscr.refresh()
            return tile

        # 聽牌建議
        advice = RuleEngine.get_tenpai_advice(player.hand_tiles) if self._show_advice else None

        while True:
            idx = ui.select_from_hand(
                self.stdscr,
                self.players,
                player_idx,
                self.ai_players,
                self.deck.get_remaining_tiles_count(),
                advice=advice,
                newly_drawn=newly_drawn,
                msg=f"玩家 {player_idx}，請選擇要打出的牌",
                sub_msg=self._last_discard_info,
            )
            if idx == -1:
                # 玩家按了 ? — 切換聽牌建議
                self._show_advice = not self._show_advice
                advice = RuleEngine.get_tenpai_advice(player.hand_tiles) if self._show_advice else None
            else:
                return player.hand_tiles[idx]

    # ── 其他玩家對棄牌的反應 ───────────────────────────

    def _prompt_reactions(self, discarder: int, tile: Tile) -> tuple[int, str, object] | None:
        """
        詢問其他玩家是否要碰/槓/吃/胡。
        回傳 (player_idx, action, extra) 或 None（所有人都略過）。
        優先順序：胡 > 碰/槓 > 吃（只有下家可吃）。
        """
        # 收集每位玩家的可行動列表
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

            # === AI 玩家：自動決策 ===
            if idx in self.ai_players:
                decision = SimpleAI.choose_reaction(self.players[idx].hand_tiles, tile, actions)
                if decision is None:
                    continue
                action_str, extra = decision
                if action_str == "吃":
                    label = f"吃 {Tile(extra[0])}{Tile(extra[1])}"
                else:
                    label = action_str
                self._show_msg(f"[AI] 玩家 {idx}：{label}", pause=False)
                return (idx, action_str, extra)

            # === 人工玩家：顯示選項 ===
            options_data: list[tuple[str, str, object]] = []
            for action, extra in actions:
                if action == "吃":
                    label = f"吃 {Tile(extra[0])}{Tile(extra[1])}"
                else:
                    label = action
                options_data.append((label, action, extra))
            options_data.append(("略過", "略過", None))

            option_labels = [o[0] for o in options_data]

            sel = ui.select_from_options(
                self.stdscr,
                self.players,
                idx,
                self.ai_players,
                self.deck.get_remaining_tiles_count(),
                option_labels,
                msg=f"玩家 {idx} 可以 —（玩家 {discarder} 打出 {tile}）",
                sub_msg=self._last_discard_info,
            )

            chosen_label, chosen_action, chosen_extra = options_data[sel]

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
        new_drawn_from_reaction = None

        if action == "胡":
            self.players[winner_idx].declare_hu(discard)
            self._winner = winner_idx
            self._discarder = player_idx
            self._winning_tile = discard
            self._show_msg(f"*** 玩家 {winner_idx} 胡牌！玩家 {player_idx} 放槍（{discard}） ***", pause=True)
            return True

        if action == "碰":
            self.players[winner_idx].declare_pong(discard)
            self._show_msg(f"玩家 {winner_idx} 碰！", pause=False)

        elif action == "槓":
            self.players[winner_idx].declare_kong(discard)
            extra_tile = self.deck.draw_from_back()
            self.players[winner_idx].add_tile_to_hand(extra_tile)
            self.players[winner_idx].order_hand()
            self._show_msg(f"玩家 {winner_idx} 槓！", pause=False)
            is_over, new_drawn_from_reaction = self._apply_flowers(winner_idx, extra_tile)
            if is_over:
                return True

        elif action == "吃":
            self.players[winner_idx].declare_chow(discard, extra)
            self._show_msg(f"玩家 {winner_idx} 吃！", pause=False)

        # 碰/槓/吃 後：winner_idx 打一張牌，再遞迴處理反應
        self.current_player = winner_idx
        discard2 = self._prompt_discard(winner_idx, newly_drawn=new_drawn_from_reaction)
        self.players[winner_idx].discard_tile(discard2)
        self._last_discard_info = f"上一手：玩家 {winner_idx} 打出 {discard2}"
        self._show_msg(f"玩家 {winner_idx} 打出：{discard2}", pause=False)
        return self._after_discard(winner_idx, discard2)

    # ── 單回合 ────────────────────────────────────────

    def play_turn(self) -> bool:
        """執行目前玩家的回合。回傳 True 表示遊戲結束。"""
        idx = self.current_player
        player = self.players[idx]

        # 1. 摸牌
        if self.deck.get_remaining_tiles_count() <= 16:
            self._show_msg("牌已剩 8 墩，流局！", pause=True)
            return True

        tile = self.deck.draw_from_front()
        player.add_tile_to_hand(tile)
        player.order_hand()

        self._show_msg(
            f"玩家 {idx} 摸牌：{tile}（牌庫剩 {self.deck.get_remaining_tiles_count()} 張）",
            pause=False,
        )

        # 2. 補花
        is_over, tile = self._apply_flowers(idx, tile)
        if is_over:
            return True

        # 3. 暗槓（摸進來的暗槓）
        is_over, tile = self._apply_concealed_kong(idx, tile)
        if is_over:
            return True

        # 4. 自摸判斷
        if RuleEngine.is_hu(player.hand_tiles, None):
            if idx in self.ai_players:
                player.declare_hu(None)
                self._show_msg(f"*** 玩家 {idx} 自摸胡牌！ ***", pause=True)
                return True
            confirmed = ui.prompt_yn(
                self.stdscr,
                self.players,
                idx,
                self.ai_players,
                self.deck.get_remaining_tiles_count(),
                question=f"玩家 {idx} 可以自摸！要胡嗎？(y/n)",
                newly_drawn=tile,
                sub_msg=self._last_discard_info,
            )
            if confirmed:
                player.declare_hu(None)
                self._winner = idx
                self._discarder = None
                self._winning_tile = None
                self._show_msg(f"*** 玩家 {idx} 自摸胡牌！ ***", pause=True)
                return True

        # 5. 打牌 → 處理反應
        discard = self._prompt_discard(idx, newly_drawn=tile)
        player.discard_tile(discard)
        self._last_discard_info = f"上一手：玩家 {idx} 打出 {discard}"
        self._show_msg(f"玩家 {idx} 打出：{discard}", pause=False)
        return self._after_discard(idx, discard)

    # ── 主迴圈 ────────────────────────────────────────

    def run(self):
        ui.init_colors()
        curses.curs_set(0)   # 隱藏系統游標

        # 開局設定
        self.ai_players = ui.setup_screen(self.stdscr)

        self.start_game()

        # 發牌後補花 + 暗槓（初始手牌）
        for i in range(4):
            if self._handle_flowers(i)[0]:
                self._end_game()
                return
            self.players[i].order_hand()
            if self._handle_concealed_kong(i)[0]:
                self._end_game()
                return
            self.players[i].order_hand()

        while True:
            if self.play_turn():
                break

        # 結果畫面
        self.stdscr.clear()
        ui._safe_addstr(self.stdscr, 0, 0, "遊戲結束！",
                        curses.color_pair(ui.COLOR_TITLE) | curses.A_BOLD)
        row = 1

        # 勝負摘要
        if self._winner is not None:
            winner_ai = "[AI]" if self._winner in self.ai_players else ""
            if self._discarder is not None:
                discarder_ai = "[AI]" if self._discarder in self.ai_players else ""
                tile_str = f"（{self._winning_tile}）" if self._winning_tile else ""
                summary = (f"玩家 {self._winner}{winner_ai} 胡牌{tile_str}  "
                           f"玩家 {self._discarder}{discarder_ai} 放槍")
            else:
                summary = f"玩家 {self._winner}{winner_ai} 自摸胡牌"
            ui._safe_addstr(self.stdscr, row, 0, summary,
                            curses.color_pair(ui.COLOR_WIN) | curses.A_BOLD)
        row += 2

        for i, p in enumerate(self.players):
            is_winner   = p.is_winner
            is_discard  = (i == self._discarder)
            if is_winner:
                tag  = "  ★ 胡牌"
                attr = curses.color_pair(ui.COLOR_WIN) | curses.A_BOLD
            elif is_discard:
                tag  = "  ✗ 放槍"
                attr = curses.color_pair(ui.COLOR_ADVICE) | curses.A_BOLD
            else:
                tag  = ""
                attr = 0
            ui._safe_addstr(self.stdscr, row, 0, f"玩家 {i}{tag}", attr)
            row += 1

            # 亮牌（碰/吃/槓/暗槓）
            if p.melded_tiles:
                row = ui.draw_tiles_vertical(
                    self.stdscr, p.melded_tiles, "亮: ", row, col=2, attr=attr)

            # 手牌
            row = ui.draw_tiles_vertical(
                self.stdscr, p.hand_tiles, "手: ", row, col=2, attr=attr)
            row += 1   # 空一行分隔

        ui.draw_hint_bar(self.stdscr, "按任意鍵退出")
        self.stdscr.refresh()
        self.stdscr.getch()
