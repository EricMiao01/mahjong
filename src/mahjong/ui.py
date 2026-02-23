"""
ui.py — curses 全屏 TUI 工具模組

畫面分區（由上到下）：
  0        : 標題列
  1..N_OPP : 對手資訊（其他三位玩家）
  N_OPP+1  : 分隔線
  N_OPP+2  : 玩家 0 資訊列（摸牌/動作訊息）
  N_OPP+3  : 手牌列（游標高亮）
  N_OPP+5  : 聽牌建議（可選顯示）
  底列     : 操作提示
"""
from __future__ import annotations
import curses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tile import Tile
    from .player import Player

# ── 顏色常數 ────────────────────────────────────────────────
COLOR_NORMAL  = 0   # 預設
COLOR_CURSOR  = 1   # 游標選中（反白）
COLOR_ADVICE  = 2   # 聽牌建議（黃）
COLOR_WIN     = 3   # 胡牌（綠）
COLOR_TITLE   = 4   # 標題（青）
COLOR_AI      = 5   # AI 玩家（暗灰）
COLOR_SECTION = 6   # 分隔 / 區塊標籤（藍）

def init_colors():
    """初始化 curses 顏色對。需在 curses.initscr() 之後呼叫。"""
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(COLOR_CURSOR,  curses.COLOR_BLACK,  curses.COLOR_CYAN)
    curses.init_pair(COLOR_ADVICE,  curses.COLOR_YELLOW, -1)
    curses.init_pair(COLOR_WIN,     curses.COLOR_GREEN,  -1)
    curses.init_pair(COLOR_TITLE,   curses.COLOR_CYAN,   -1)
    curses.init_pair(COLOR_AI,      curses.COLOR_WHITE,  -1)
    curses.init_pair(COLOR_SECTION, curses.COLOR_BLUE,   -1)


def _safe_addstr(stdscr, y: int, x: int, s: str, attr: int = 0):
    """避免超出螢幕邊界時拋例外。"""
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h:
        return
    if x < 0 or x >= w:
        return
    # 截斷超出寬度的部分
    available = w - x - 1
    if available <= 0:
        return
    try:
        stdscr.addstr(y, x, s[:available], attr)
    except curses.error:
        pass  # 最後一列最後一格寫完游標會越界，忽略即可


# ── 桌面繪製 ────────────────────────────────────────────────

def draw_table(
    stdscr,
    players: list,
    current_player: int,
    ai_players: set[int],
    deck_remaining: int,
    highlight_player: int = -1,
    msg: str = "",
    sub_msg: str = "",          # 常駐資訊列（上一手出牌）
):
    """繪製整個桌面（對手區 + 狀態列）。"""
    stdscr.clear()

    # 標題
    title = "  麻將"
    deck_info = f"  牌庫剩 {deck_remaining} 張"
    _safe_addstr(stdscr, 0, 0, title, curses.color_pair(COLOR_TITLE) | curses.A_BOLD)
    _safe_addstr(stdscr, 0, len(title) + 2, deck_info)

    row = 2
    for i, p in enumerate(players):
        is_ai   = i in ai_players
        is_turn = (i == current_player)
        is_hl   = (i == highlight_player)

        tag = f"玩家 {i}"
        if is_ai:
            tag += " [AI]"
        if is_turn:
            tag += " ◀ 出牌中"
        if is_hl:
            tag += " ← 出牌"

        sec_attr = curses.color_pair(COLOR_SECTION) | curses.A_BOLD
        _safe_addstr(stdscr, row, 0, tag, sec_attr)
        row += 1

        # ── 亮牌 + 花（同一個兩列區塊）──────────────
        # "亮:" = 亮(2col) + :(1col) = 3 terminal cols；從 col 2 開始 → tiles 在 col 5
        _safe_addstr(stdscr, row, 2, "亮:", sec_attr)
        tile_col = 5
        if p.melded_tiles:
            for t in p.melded_tiles:
                top, bot = _tile_rows(str(t))
                _safe_addstr(stdscr, row,   tile_col, top)
                _safe_addstr(stdscr, row+1, tile_col, bot)
                tile_col += 3   # 每個 CJK 字 2col + 空格 1col
            flower_col = tile_col + 2   # 兩格空白分隔
        else:
            _safe_addstr(stdscr, row, tile_col, "-")
            flower_col = tile_col + 3   # "- " + 兩格分隔

        if p.flower_tiles:
            _safe_addstr(stdscr, row, flower_col, "花:", sec_attr)
            f_tile_col = flower_col + 3
            for t in p.flower_tiles:
                top, bot = _tile_rows(str(t))
                _safe_addstr(stdscr, row,   f_tile_col, top)
                _safe_addstr(stdscr, row+1, f_tile_col, bot)
                f_tile_col += 3
        row += 2

        # ── 棄牌（兩列）─────────────────────────────
        _safe_addstr(stdscr, row, 2, "棄:", sec_attr)
        tile_col = 5
        if p.discarded_tiles:
            for t in p.discarded_tiles:
                top, bot = _tile_rows(str(t))
                _safe_addstr(stdscr, row,   tile_col, top)
                _safe_addstr(stdscr, row+1, tile_col, bot)
                tile_col += 3
        else:
            _safe_addstr(stdscr, row, tile_col, "-")
        row += 3   # 2 tile rows + 1 blank

    # 分隔線
    _safe_addstr(stdscr, row, 0, "─" * 50, curses.color_pair(COLOR_SECTION))
    row += 1

    # 常駐資訊列：上一手出的牌（dim 顯示）
    if sub_msg:
        _safe_addstr(stdscr, row, 0, sub_msg, curses.A_DIM)
        row += 1

    # 主訊息（粗體）
    if msg:
        _safe_addstr(stdscr, row, 0, msg, curses.A_BOLD)
        row += 1

    return row


def _tile_rows(label: str) -> tuple[str, str]:
    """
    將牌字串拆成上下兩列字元。
    - 兩字牌（一萬、二筒…）: 上=數字字, 下=花色字
    - 單字牌（中、東、梅…）: 上=下=同一字（重複）
    """
    if len(label) == 2:
        return label[0], label[1]
    return label[0], label[0]


def draw_hand(
    stdscr,
    player,
    player_idx: int,
    cursor: int,
    advice: dict[int, list] | None = None,
    newly_drawn: "Tile | None" = None,
    start_row: int = 0,
):
    """在 start_row 之後畫出玩家手牌（直立兩列顯示）。"""
    _safe_addstr(stdscr, start_row, 0,
                 f"玩家 {player_idx} 的手牌",
                 curses.color_pair(COLOR_WIN) | curses.A_BOLD)

    top_row = start_row + 1
    bot_row = start_row + 2
    col = 0

    for i, tile in enumerate(player.hand_tiles):
        top_ch, bot_ch = _tile_rows(str(tile))
        is_cursor = (i == cursor)
        is_new    = (tile is newly_drawn)

        if is_cursor:
            attr = curses.color_pair(COLOR_CURSOR) | curses.A_BOLD
        elif is_new:
            attr = curses.color_pair(COLOR_WIN)
        else:
            attr = curses.color_pair(COLOR_NORMAL)

        # 每個 CJK 字元佔 2 terminal columns，加 1 空格做間距 → 每格 3 cols
        _safe_addstr(stdscr, top_row, col, top_ch, attr)
        _safe_addstr(stdscr, bot_row, col, bot_ch, attr)
        col += 3

    # 聽牌建議
    advice_row = bot_row + 2
    if advice:
        _safe_addstr(stdscr, advice_row, 0,
                     "聽牌建議：",
                     curses.color_pair(COLOR_ADVICE) | curses.A_BOLD)
        advice_row += 1
        for code, ting_tiles in advice.items():
            from .tile import Tile as _Tile
            discard_tile = _Tile(code)
            ting_str = " ".join(str(t) for t in ting_tiles)
            _safe_addstr(stdscr, advice_row, 2,
                         f"打 {discard_tile} 可聽: {ting_str}",
                         curses.color_pair(COLOR_ADVICE))
            advice_row += 1

    return advice_row



def draw_hint_bar(stdscr, hint: str):
    """在畫面最底列顯示操作提示。"""
    h, w = stdscr.getmaxyx()
    hint_row = h - 1
    _safe_addstr(stdscr, hint_row, 0,
                 hint.ljust(w - 1),
                 curses.color_pair(COLOR_SECTION))


# ── 互動輸入 ────────────────────────────────────────────────

def select_from_hand(
    stdscr,
    players: list,
    player_idx: int,
    ai_players: set[int],
    deck_remaining: int,
    advice: dict[int, list] | None = None,
    newly_drawn: "Tile | None" = None,
    msg: str = "",
    sub_msg: str = "",
) -> int:
    """
    阻塞等待玩家用 ← → 選牌，Enter 確認。
    回傳選中的手牌索引。
    """
    player = players[player_idx]
    # 游標起始位置 = 摸進來的牌的實際索引（排序後不一定在最右）
    if newly_drawn is not None:
        cursor = next(
            (i for i, t in enumerate(player.hand_tiles) if t is newly_drawn),
            len(player.hand_tiles) - 1,
        )
    else:
        cursor = len(player.hand_tiles) - 1

    while True:
        row = draw_table(stdscr, players, player_idx, ai_players,
                         deck_remaining, msg=msg, sub_msg=sub_msg)
        draw_hand(stdscr, player, player_idx, cursor, advice,
                  newly_drawn, start_row=row)
        draw_hint_bar(stdscr, "← → 移動    Enter 打出    ? 顯示/隱藏聽牌建議")
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_LEFT:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_RIGHT:
            cursor = min(len(player.hand_tiles) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            return cursor
        elif key == ord('?'):
            # 切換建議顯示：由呼叫者重算 advice 傳入，此處 toggle 邏輯在 game.py
            # 這裡只回傳特殊值 -1 告知 game.py 使用者按了 ?
            return -1


def select_from_options(
    stdscr,
    players: list,
    player_idx: int,
    ai_players: set[int],
    deck_remaining: int,
    options: list[str],
    msg: str = "",
    sub_msg: str = "",
) -> int:
    """
    阻塞等待玩家用 ↑ ↓ 選擇動作，Enter 確認，Esc 略過。
    """
    player = players[player_idx]
    cursor = 0

    while True:
        row = draw_table(stdscr, players, player_idx, ai_players,
                         deck_remaining, msg=msg, sub_msg=sub_msg)
        # 手牌（不帶游標）
        row = draw_hand(stdscr, player, player_idx, cursor=-1,
                        start_row=row)
        # 選項列表
        row += 1
        _safe_addstr(stdscr, row, 0,
                     "可以：",
                     curses.color_pair(COLOR_WIN) | curses.A_BOLD)
        row += 1
        for i, label in enumerate(options):
            if i == cursor:
                attr = curses.color_pair(COLOR_CURSOR) | curses.A_BOLD
                txt = f"  ▶ {label}"
            else:
                attr = curses.color_pair(COLOR_NORMAL)
                txt = f"    {label}"
            _safe_addstr(stdscr, row, 0, txt, attr)
            row += 1

        draw_hint_bar(stdscr, "↑ ↓ 移動    Enter 確認    Esc 略過")
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(options) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            return cursor
        elif key == 27:   # ESC → 略過（選最後一項）
            return len(options) - 1


def prompt_yn(
    stdscr,
    players: list,
    player_idx: int,
    ai_players: set[int],
    deck_remaining: int,
    question: str,
    newly_drawn: "Tile | None" = None,
    sub_msg: str = "",
) -> bool:
    """
    展示手牌，並在底部問 y/n。
    """
    player = players[player_idx]

    while True:
        row = draw_table(stdscr, players, player_idx, ai_players,
                         deck_remaining, msg=question, sub_msg=sub_msg)
        draw_hand(stdscr, player, player_idx, cursor=-1,
                  newly_drawn=newly_drawn, start_row=row)
        draw_hint_bar(stdscr, "y 是    n 否")
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord('y'), ord('Y')):
            return True
        elif key in (ord('n'), ord('N')):
            return False


def setup_screen(stdscr) -> set[int]:
    """
    開局設定畫面：選擇哪些玩家由 AI 操作。
    回傳 ai_players set。
    空白鍵 Toggle，Enter 確認。
    """
    candidates = [0, 1, 2, 3]
    selected: set[int] = {1, 2, 3}   # 預設

    while True:
        stdscr.clear()
        _safe_addstr(stdscr, 0, 0, "歡迎來到終端機麻將！",
                     curses.color_pair(COLOR_TITLE) | curses.A_BOLD)
        _safe_addstr(stdscr, 2, 0, "請選擇由 AI 操作的玩家（Space 切換，Enter 開始）：")
        for i, p in enumerate(candidates):
            is_ai = p in selected
            mark  = "  [AI] " if is_ai else "  [人] "
            _safe_addstr(stdscr, 4 + i, 0, f"{mark} 玩家 {p}")
        draw_hint_bar(stdscr, "0-3 切換    a 全 AI（觀戰）    Enter 開始")
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord('0'), ord('1'), ord('2'), ord('3')):
            p = int(chr(key))
            if p in selected:
                selected.discard(p)
            else:
                selected.add(p)
        elif key in (ord('a'), ord('A')):
            selected = {0, 1, 2, 3}
        elif key in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            return selected
