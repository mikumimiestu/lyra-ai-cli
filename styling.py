import sys
import os
import re

# ─── Enable ANSI color support on Windows Console ────────────────────────────
if sys.platform == "win32":
    os.system("")

# ─── Terminal Color Detection ─────────────────────────────────────────────────
def _detect_dark_bg():
    """
    Heuristic: jika COLORFDBG/COLORFG/TERM_PROGRAM menunjukkan light,
    gunakan warna gelap agar tetap terbaca. Default: anggap dark.
    """
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    color_term   = os.environ.get("COLORTERM", "").lower()
    # macOS Terminal kadang punya TERM_PROGRAM=Apple_Terminal dengan bg terang
    # Jika pengguna set env var ini kita hormati
    force_light  = os.environ.get("LYRA_LIGHT_THEME", "").lower() in ("1", "true", "yes")
    if force_light:
        return False
    return True  # default: dark background

IS_DARK = _detect_dark_bg()
USE_COLOR = sys.stdout.isatty() and 'NO_COLOR' not in os.environ and os.environ.get('TERM') != 'dumb'

# ─── ANSI Helpers ─────────────────────────────────────────────────────────────
def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_ansi(r, g, b):
    return f"\033[38;2;{r};{g};{b}m" if USE_COLOR else ""

def rgb_bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m" if USE_COLOR else ""

def interpolate_rgb(color1, color2, t):
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return r, g, b

def get_gradient_color(t):
    """Blue → Purple → Pink gradient"""
    c1 = hex_to_rgb("#33A0FF")
    c2 = hex_to_rgb("#9C4FFF")
    c3 = hex_to_rgb("#FF5EEF")
    if t < 0.5:
        return interpolate_rgb(c1, c2, t * 2.0)
    else:
        return interpolate_rgb(c2, c3, (t - 0.5) * 2.0)

# ─── Base ANSI ────────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
STRIKE = "\033[9m"

# ─── Adaptive Colors ─────────────────────────────────────────────────────────
# Pada dark theme pakai warna terang, pada light theme pakai warna lebih gelap
if IS_DARK:
    WHITE       = "\033[39m"          # bright white
    GREEN       = rgb_to_ansi(*hex_to_rgb("#4ADE80"))
    RED         = rgb_to_ansi(*hex_to_rgb("#F87171"))
    YELLOW      = rgb_to_ansi(*hex_to_rgb("#FDE68A"))
    CYAN        = rgb_to_ansi(*hex_to_rgb("#67E8F9"))
    COLOR_USER  = rgb_to_ansi(*hex_to_rgb("#A8B3CB"))   # soft blue
    COLOR_LYRA  = rgb_to_ansi(*hex_to_rgb("#B6A0DC"))   # vivid pink-purple
    COLOR_BORDER= rgb_to_ansi(*hex_to_rgb("#626271"))   # lavender
    COLOR_DIM   = rgb_to_ansi(*hex_to_rgb("#94A3B8"))   # slate-400
    COLOR_TITLE = rgb_to_ansi(*hex_to_rgb("#F8FAFC"))   # near-white
    COLOR_ACCENT= rgb_to_ansi(*hex_to_rgb("#34D399"))   # emerald
else:
    # Light background — pakai warna gelap supaya kontras
    WHITE       = "\033[39m"          # black
    GREEN       = rgb_to_ansi(*hex_to_rgb("#15803D"))
    RED         = rgb_to_ansi(*hex_to_rgb("#B91C1C"))
    YELLOW      = rgb_to_ansi(*hex_to_rgb("#854D0E"))
    CYAN        = rgb_to_ansi(*hex_to_rgb("#0E7490"))
    COLOR_USER  = rgb_to_ansi(*hex_to_rgb("#1D4ED8"))   # dark blue
    COLOR_LYRA  = rgb_to_ansi(*hex_to_rgb("#7C3AED"))   # dark purple
    COLOR_BORDER= rgb_to_ansi(*hex_to_rgb("#6D28D9"))   # violet
    COLOR_DIM   = rgb_to_ansi(*hex_to_rgb("#475569"))   # slate-600
    COLOR_TITLE = rgb_to_ansi(*hex_to_rgb("#0F172A"))   # near-black
    COLOR_ACCENT= rgb_to_ansi(*hex_to_rgb("#065F46"))   # dark emerald

# Respect redirected output and explicit plain-text mode.
if not sys.stdout.isatty() or 'NO_COLOR' in os.environ or os.environ.get('TERM') == 'dumb':
    for _name in ('RESET', 'BOLD', 'DIM', 'ITALIC', 'WHITE', 'GREEN', 'RED', 'YELLOW', 'CYAN',
                  'UNDERLINE', 'STRIKE', 'COLOR_USER', 'COLOR_LYRA', 'COLOR_BORDER', 'COLOR_DIM', 'COLOR_TITLE', 'COLOR_ACCENT'):
        globals()[_name] = ''

# ─── Mascot ───────────────────────────────────────────────────────────────────
# Nexara's pet (head only), drawn as pixel art: 27 columns x 20 pixel rows, two pixel rows per terminal row
# (half-block characters). Letters index PET_PALETTE; "." is transparent so the terminal's own
# background shows through.
PET_PALETTE = {
    'i': (38, 44, 82),
    'w': (252, 252, 255),
    's': (214, 221, 243),
    'b': (36, 104, 240),
    'l': (120, 176, 255),
    'k': (30, 31, 42),
    'p': (255, 176, 190),
    'r': (232, 84, 104),
}
PET_SPRITE = [
    '.....i...............i.....',
    '....iwi.............iwi....',
    '....iwbii.........iibwi....',
    '....iwbbwiiiiiiiiiwbbwi....',
    '...iwwbbbwwwwwwwwwbbbwwi...',
    '...iwbbwwwwwwwwwwwwwbbwi...',
    '...iwwwwwwwwwwwwwwwwwwwi...',
    '...iwwwwwwwwwlwwwwwwwwwi...',
    '..iwwwwwwwwwlwlwwwwwwwwwi..',
    '.iwwwwwwwwwwwwwwwwwwwwwwwi.',
    '.iwwwwwwwiiwwwwwiiwwwwwwwi.',
    '.iwwwwwwiwwiwwwiwwiwwwwwwi.',
    '.iwwwwwwwwwwwwwwwwwwwwwwwi.',
    '.iwwwppwwwwiiiiiwwwwppwwwi.',
    '..iwwwwwwwwirrriwwwwwwwwi..',
    '...iwwwwwwwwiiiwwwwwwwwi...',
    '....iwwwwwwwwwwwwwwwwwi....',
    '.....iisssssssssssssii.....',
    '.......iiwwwwwwwwwii.......',
    '.........iiiiiiiii.........',
]
PET_COLS = len(PET_SPRITE[0])
PET_ROWS = len(PET_SPRITE) // 2
MASCOT_MIN_COLS = 66        # sprite + gap + enough room for the text beside it
MASCOT_MIN_ROWS = 20


def color_depth():
    """24 for true colour, 8 for 256 colours, 0 when colour is off."""
    if not USE_COLOR:
        return 0
    term = os.environ.get('TERM', '').lower()
    colorterm = os.environ.get('COLORTERM', '').lower()
    if (colorterm in ('truecolor', '24bit') or term.endswith('-direct')
            or os.environ.get('TERM_PROGRAM', '') in ('iTerm.app', 'WezTerm', 'vscode', 'ghostty')):
        return 24
    if os.name == 'nt':
        # Windows terminals set neither COLORTERM nor TERM. Windows Terminal, VS Code and ConEmu do true
        # colour; so does the classic console since Windows 10 build 14931.
        if os.environ.get('WT_SESSION') or os.environ.get('ConEmuANSI') == 'ON':
            return 24
        try:
            if sys.getwindowsversion().build >= 14931:
                return 24
        except (AttributeError, OSError):
            pass
        return 0
    return 8 if '256color' in term else 0


def _xterm256(rgb):
    """Nearest colour in the xterm 256 palette (6x6x6 cube or grey ramp)."""
    levels = (0, 95, 135, 175, 215, 255)
    cube = [min(range(6), key=lambda i: abs(levels[i] - v)) for v in rgb]
    cube_rgb = tuple(levels[i] for i in cube)
    grey_index = max(0, min(23, round((sum(rgb) / 3 - 8) / 10)))
    grey = 8 + 10 * grey_index

    def distance(c):
        return sum((a - b) ** 2 for a, b in zip(rgb, c))
    if distance((grey, grey, grey)) < distance(cube_rgb):
        return 232 + grey_index
    return 16 + 36 * cube[0] + 6 * cube[1] + cube[2]


def _pet_color(rgb, foreground, depth):
    layer = 38 if foreground else 48
    if depth >= 24:
        return f"\033[{layer};2;{rgb[0]};{rgb[1]};{rgb[2]}m"
    return f"\033[{layer};5;{_xterm256(rgb)}m"


def pet_art(depth=None):
    """The pet as PET_ROWS terminal rows, each exactly PET_COLS cells wide.

    Colour codes are only written when they change from the previous cell, which keeps a row to a few
    hundred bytes instead of repeating the same escape for every cell.
    """
    depth = color_depth() if depth is None else depth
    rows = []
    for y in range(0, len(PET_SPRITE), 2):
        parts, state = [], (None, None)
        for x in range(PET_COLS):
            top, bottom = PET_PALETTE.get(PET_SPRITE[y][x]), PET_PALETTE.get(PET_SPRITE[y + 1][x])
            if top and bottom:
                char, fg, bg = '▀', top, bottom
            elif top:
                char, fg, bg = '▀', top, None
            elif bottom:
                char, fg, bg = '▄', bottom, None
            else:
                char, fg, bg = ' ', None, None
            if (fg, bg) != state:
                if state != (None, None):
                    parts.append(RESET)
                if fg:
                    parts.append(_pet_color(fg, True, depth))
                if bg:
                    parts.append(_pet_color(bg, False, depth))
                state = (fg, bg)
            parts.append(char)
        rows.append(''.join(parts) + (RESET if state != (None, None) else ''))
    return rows


def terminal_rows():
    try:
        return os.get_terminal_size().lines
    except Exception:
        return 24


def mascot_fits():
    """The pet needs colour, unicode block characters and enough room; otherwise the header is text only."""
    return (color_depth() > 0 and unicode_terminal() and get_terminal_width() >= MASCOT_MIN_COLS
            and terminal_rows() >= MASCOT_MIN_ROWS)


def gradient_text(text):
    """Blue-purple-pink wordmark (the old logo's colours); plain text when colour is off."""
    if not USE_COLOR:
        return text
    last = max(1, len(text) - 1)
    return ''.join(rgb_to_ansi(*get_gradient_color(i / last)) + BOLD + ch for i, ch in enumerate(text)) + RESET


# ─── Terminal Layout Helpers ──────────────────────────────────────────────────
import unicodedata
import textwrap

def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80

def strip_ansi(text):
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)

def char_width(char):
    """Hitung lebar kolom terminal untuk 1 karakter ANSI/Unicode (termasuk Emoji & CJK)."""
    code = ord(char)
    if code == 0xFE0F or unicodedata.category(char) == 'Mn':
        return 0
    if code < 128:
        return 1
    # Simbol star terminal (✦ U+2726 rendered sebagai 1 kolom)
    if code in (0x2726, 0x2724, 0x2725, 0x200D):
        return 1
    if unicodedata.east_asian_width(char) in ('F', 'W'):
        return 2
    # Range Emoji (0x1F000 - 0x1F9FF)
    if (0x1F000 <= code <= 0x1F9FF):
        return 2
    return 1

def str_width(text):
    """Hitung total lebar kolom tampilan di terminal (menghiraukan kode ANSI)."""
    clean = strip_ansi(text)
    return sum(char_width(c) for c in clean)


# ─── Rounded boxes (welcome card, permission dialog) ─────────────────────────
def box_width(maximum=88, minimum=24):
    return max(minimum, min(get_terminal_width() - 4, maximum))


def render_box(lines, width, color=None, title=''):
    """Rounded box in the style of modern agent CLIs. `lines` are pre-wrapped to width - 4."""
    color = COLOR_BORDER if color is None else color
    if unicode_terminal():
        tl, tr, bl, br, h, v = '╭', '╮', '╰', '╯', '─', '│'
    else:
        tl, tr, bl, br, h, v = '+', '+', '+', '+', '-', '|'
    inner = width - 2
    if title:
        label = f' {title} '
        top = f'{color}{tl}{h}{RESET}{label}{color}{h * max(1, inner - 1 - str_width(label))}{tr}{RESET}'
    else:
        top = f'{color}{tl}{h * inner}{tr}{RESET}'
    out = [top]
    for text in lines:
        pad = max(0, width - 4 - str_width(text))
        out.append(f'{color}{v}{RESET} {text}{" " * pad} {color}{v}{RESET}')
    out.append(f'{color}{bl}{h * inner}{br}{RESET}')
    return out


HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
COMMAND_ROWS = 10          # longest command shown in full in a confirmation
HEREDOC_PREVIEW = 3        # lines of an inline file body shown before "… +N baris"


def command_preview(command, width, full=False):
    """(rows, truncated) for a command: wrapped lines, with long inline file bodies (cat <<EOF) and very long
    scripts folded. The command lines themselves, and everything after a body, always stay visible."""
    lines = [line for line in str(command).split('\n')]
    while lines and not lines[-1].strip():
        lines.pop()
    rows, truncated, index = [], False, 0
    while index < len(lines):
        line = lines[index]
        rows.append(('cmd', line))
        index += 1
        found = HEREDOC_START.search(line)
        if not found:
            continue
        marker = found.group(2)
        end = next((j for j in range(index, len(lines)) if lines[j].strip() == marker), len(lines))
        body = lines[index:end]
        if full or len(body) <= HEREDOC_PREVIEW + 1:
            rows.extend(('cmd', b) for b in body)
        else:
            rows.extend(('cmd', b) for b in body[:HEREDOC_PREVIEW])
            rows.append(('more', f'… +{len(body) - HEREDOC_PREVIEW} baris isi file'))
            truncated = True
        index = end
    out = []
    for kind, text in rows:
        if kind == 'more':
            out.append(('more', text))
        else:
            out.extend(('cmd', piece) for piece in wrap_text_display_width(text, width) or [''])
    if not full and len(out) > COMMAND_ROWS + HEREDOC_PREVIEW:
        hidden = len(out) - 8
        out = out[:6] + [('more', f'… +{hidden} baris')] + out[-2:]
        truncated = True
    return out, truncated


def render_permission_box(title, details, full=False):
    """Compact confirmation, a few lines instead of a framed box.

    A command is shown next to a bar. Long inline file bodies and very long scripts are folded (the command
    itself and anything after a body stay visible); `full=True` shows everything. Returns True when something
    was folded so the caller can offer "v" to view it all. Everything else (folder, limits, sizes) is one dim line.
    """
    width = max(30, get_terminal_width() - 6)
    heading = title[len('Konfirmasi '):] if title.startswith('Konfirmasi ') else title
    bar = f"{YELLOW}{ui_symbol('│', '|')}{RESET}"
    folded = False
    print()
    print(f"  {BOLD}{YELLOW}{ui_symbol('⚠', '!')} {heading}{RESET}")
    info, warnings = [], []
    for key, value in details.items():
        text = str(value)
        if key == 'Perintah':
            rows, cut = command_preview(text, width, full)
            folded = folded or cut
            for kind, piece in rows:
                print(f"    {bar} " + (f"{COLOR_DIM}{piece}{RESET}" if kind == 'more' else highlight_syntax(piece)))
        elif key == 'Direktori':
            info.append('di ' + short_path(text))
        elif key == 'Timeout':
            info.append('batas ' + text.replace(' detik', ' dtk'))
        elif key in ('Path', 'Target Path'):
            info.append(short_path(text))
        elif key == 'Penggantian':
            info.append(text + ' penggantian')
        elif key == 'Peringatan':
            warnings.append(text)
        elif key == 'Operasi' and 'Perintah' not in details:
            info.insert(0, f"{BOLD}{text}{RESET}{COLOR_DIM}")
        elif key in ('Ukuran', 'Nama', 'Tipe Project'):
            info.append(text)
        else:
            info.append(f"{key.lower()} {text}")
    if info:
        line = (' ' + ui_symbol('·', '-') + ' ').join(info)
        for piece in wrap_text_display_width(strip_ansi(line), width) if '\033' not in line else [line]:
            print(f"    {COLOR_DIM}{piece}{RESET}")
    for text in warnings:
        for piece in wrap_text_display_width(text, width):
            print(f"    {YELLOW}{ui_symbol('⚠', '!')} {piece}{RESET}")
    return folded


# ─── Markdown Renderer & Code Highlighting ────────────────────────────────────
import re

CODE_BG = rgb_bg(30, 41, 59) if IS_DARK else rgb_bg(241, 245, 249)
INLINE_CODE_BG = rgb_bg(39, 39, 42) if IS_DARK else rgb_bg(228, 228, 231)

KEYWORDS_PAT = r'\b(?:def|class|import|from|return|if|else|elif|for|while|try|except|const|let|var|function|async|await|export|default|require|echo|public|private|protected|fn|struct|enum|interface|type|nil|None|True|False|null|true|false)\b'
SYNTAX_PATTERN = re.compile(rf'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)|({KEYWORDS_PAT})|(\b\d+\b)')

def highlight_syntax(code_line, lang=""):
    """Syntax highlighting presisi tanpa merusak ANSI escape sequence."""
    if not code_line:
        return ""
    
    # Comments
    if code_line.strip().startswith(("#", "//", "/*", "*")):
        return f"{COLOR_DIM}{ITALIC}{code_line}{RESET}"

    def replacer(match):
        groups = match.groups()
        s_group = groups[0] if len(groups) > 0 else None
        k_group = groups[1] if len(groups) > 1 else None
        n_group = groups[2] if len(groups) > 2 else None
        if s_group is not None:
            return f"{GREEN}{s_group}{RESET}"
        elif k_group is not None:
            return f"{CYAN}{BOLD}{k_group}{RESET}"
        elif n_group is not None:
            return f"{YELLOW}{n_group}{RESET}"
        return match.group(0)


    return SYNTAX_PATTERN.sub(replacer, code_line)



LINK_PATTERN = re.compile(r'(!?)\[([^\]\n]*)\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')


def link_label(text, url, image=False):
    """`text (url)` with the text underlined; an image shows its alt text; a bare url is not repeated."""
    clean = re.sub(r'\*\*|`|__', '', text).strip()
    label = (f'[gambar: {clean}]' if clean else '[gambar]') if image else (clean or url)
    shown = f"{UNDERLINE}{COLOR_ACCENT}{label}{RESET}"
    return shown if label == url else f"{shown} {COLOR_DIM}({url}){RESET}"


def format_inline_markdown(text):
    """Format bold, italic, strikethrough, inline code and links in one line of text."""
    if not text:
        return ""
    protected = []

    def keep(rendered):
        protected.append(rendered)
        return f"\x00{len(protected) - 1}\x00"

    # Links first: their urls often hold underscores and asterisks that must not be read as emphasis.
    text = LINK_PATTERN.sub(lambda m: keep(link_label(m.group(2), m.group(3), bool(m.group(1)))), text)
    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', lambda m: keep(f"{INLINE_CODE_BG}{COLOR_ACCENT} {m.group(1)} {RESET}"), text)
    # Strikethrough: ~~text~~
    text = re.sub(r'~~([^~]+)~~', rf"{STRIKE}\1{RESET}", text)
    # Bold: **bold**
    text = re.sub(r'\*\*([^*]+)\*\*', rf"{BOLD}{WHITE}\1{RESET}", text)
    # Italic: *italic* or _italic_
    text = re.sub(r'\*([^*]+)\*', rf"{ITALIC}\1{RESET}", text)
    text = re.sub(r'_([^_]+)_', rf"{ITALIC}\1{RESET}", text)
    return re.sub(r'\x00(\d+)\x00', lambda m: protected[int(m.group(1))], text)


def task_box(mark):
    """Checkbox glyph for a markdown task item: [ ] or [x]."""
    done = mark in ('x', 'X')
    return (f"{COLOR_DIM}{ui_symbol('☒', '[x]')}{RESET}" if done else f"{COLOR_LYRA}{ui_symbol('☐', '[ ]')}{RESET}")


def format_markdown_line(line, state):
    """Format baris tunggal Markdown untuk terminal."""
    stripped = line.strip()

    # Code block toggle
    if stripped.startswith("```"):
        if not state['in_code']:
            state['in_code'] = True
            lang = stripped[3:].strip()
            state['lang'] = lang
            return f"  {COLOR_BORDER}{ui_symbol('╭─', '+-')}{RESET} {COLOR_DIM}{lang or 'code'}{RESET}", state
        state['in_code'] = False
        state['lang'] = ""
        return f"  {COLOR_BORDER}{ui_symbol('╰─', '+-')}{RESET}", state

    if state['in_code']:
        highlighted = highlight_syntax(line, state['lang'])
        return f"  {COLOR_BORDER}{ui_symbol('│', '|')}{RESET} {highlighted}", state

    # Headers (# to ######; closing hashes and emphasis markers are dropped, the heading style already stands out)
    heading = re.match(r'^(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$', line)
    if heading:
        level = len(heading.group(1))
        text = re.sub(r'\*\*|__', '', heading.group(2)).strip()
        style = {1: BOLD + UNDERLINE + COLOR_TITLE, 2: BOLD + COLOR_TITLE, 3: BOLD + COLOR_LYRA,
                 4: BOLD + COLOR_ACCENT}.get(level, BOLD + COLOR_DIM)
        return f"\n  {style}{text}{RESET}", state

    # Lists
    bullet = re.match(r'^(\s*)[-*+]\s+(.*)', line)
    if bullet:
        indent = ' ' * (len(bullet.group(1).replace('\t', '  ')) // 2 * 2)
        task = re.match(r'^\[( |x|X)\]\s+(.*)', bullet.group(2))
        if task:
            return f"  {indent}{task_box(task.group(1))} {format_inline_markdown(task.group(2))}", state
        return f"  {indent}{COLOR_LYRA}{ui_symbol('•', '-')}{RESET} {format_inline_markdown(bullet.group(2))}", state
    numbered = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
    if numbered:
        indent = ' ' * (len(numbered.group(1).replace('\t', '  ')) // 2 * 2)
        return f"  {indent}{COLOR_LYRA}{numbered.group(2)}.{RESET} {format_inline_markdown(numbered.group(3))}", state

    # Blockquotes
    quote = re.match(r'^((?:>[ \t]?)+)', line)
    if line.startswith("> ") and quote:
        depth = quote.group(1).count('>')
        content = format_inline_markdown(line[quote.end():])
        return f"  {COLOR_DIM}{(ui_symbol('▎', '|') + ' ') * depth}{ITALIC}{content}{RESET}", state

    # Horizontal Rule
    if stripped in ("---", "***", "___"):
        w = min(get_terminal_width() - 4, 100)
        return f"  {COLOR_BORDER}{'─' * w}{RESET}", state

    # Regular line
    formatted = format_inline_markdown(line)
    return f"  {WHITE}{formatted}{RESET}", state


def wrap_text_display_width(text, max_width):
    """
    Memotong/membungkus teks secara presisi berdasarkan LEBAR KOLOM DISPLAY TERMINAL (str_width).
    Menangani ANSI, Emojis, dan karakter Unicode secara akurat.
    """
    if str_width(text) <= max_width:
        return [text]

    words = text.split(" ")
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip() if current_line else word
        if str_width(test_line) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            if str_width(word) > max_width:
                sub_line = ""
                for char in word:
                    if str_width(sub_line + char) <= max_width:
                        sub_line += char
                    else:
                        lines.append(sub_line)
                        sub_line = char
                current_line = sub_line
            else:
                current_line = word

    if current_line:
        lines.append(current_line)

    return lines


# ─── Markdown Table Grid Renderer ─────────────────────────────────────────────

def parse_markdown_table(lines):
    rows = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        parts = [p.strip() for p in stripped.split("|")[1:-1]]
        if not parts:
            continue
        # Skip line pemisah markdown seperti |---|---| atau |:---|---:|
        if all(re.match(r'^:?-+:?$', p) for p in parts if p):
            continue
        rows.append(parts)
    if not rows:
        return [], []
    headers = rows[0]
    data_rows = rows[1:]
    return headers, data_rows


def render_markdown_table(table_lines, max_width=None):
    """
    Render tabel markdown sebagai tabel grid presisi tinggi ala Claude CLI terminal.
    Mendukung wrapping isi sel, alignment, dan batas Unicode box drawing.
    """
    headers, rows = parse_markdown_table(table_lines)
    if not headers:
        return []

    num_cols = len(headers)
    term_w = max_width if max_width else get_terminal_width()
    avail_w = max(40, term_w - 6)
    
    border_overhead = (3 * num_cols) + 1
    usable_w = max(num_cols * 10, avail_w - border_overhead)

    # Hitung lebar maksimal tiap kolom
    max_lens = [str_width(h) for h in headers]
    for row in rows:
        for i in range(num_cols):
            val = row[i] if i < len(row) else ""
            max_lens[i] = max(max_lens[i], str_width(val))

    total_req = sum(max_lens)
    if total_req <= usable_w:
        col_widths = list(max_lens)
    else:
        col_widths = []
        for l in max_lens:
            w = max(10, int((l / max(1, total_req)) * usable_w))
            col_widths.append(w)

    def wrap_cell(text, width):
        if str_width(text) <= width:
            return [format_inline_markdown(text)]
        words = text.split(" ")
        lines = []
        cur_words = []
        cur_plain = ""
        for w in words:
            test_plain = f"{cur_plain} {w}".strip() if cur_plain else w
            if str_width(strip_ansi(format_inline_markdown(test_plain))) <= width:
                cur_words.append(w)
                cur_plain = test_plain
            else:
                if cur_words:
                    lines.append(format_inline_markdown(" ".join(cur_words)))
                if str_width(w) > width:
                    sub = ""
                    for ch in w:
                        if str_width(sub + ch) <= width:
                            sub += ch
                        else:
                            lines.append(format_inline_markdown(sub))
                            sub = ch
                    cur_words = [sub] if sub else []
                    cur_plain = sub
                else:
                    cur_words = [w]
                    cur_plain = w
        if cur_words:
            lines.append(format_inline_markdown(" ".join(cur_words)))
        return lines if lines else [""]

    B = COLOR_BORDER
    R = RESET

    top_line = f"  {B}┌" + "┬".join("─" * (w + 2) for w in col_widths) + f"┐{R}"
    sep_line = f"  {B}├" + "┼".join("─" * (w + 2) for w in col_widths) + f"┤{R}"
    bot_line = f"  {B}└" + "┴".join("─" * (w + 2) for w in col_widths) + f"┘{R}"

    output_lines = [top_line]

    def render_row_block(row_cells, is_header=False):
        wrapped_cells = []
        max_h = 1
        for i in range(num_cols):
            val = row_cells[i] if i < len(row_cells) else ""
            w_lines = wrap_cell(val, col_widths[i])
            wrapped_cells.append(w_lines)
            max_h = max(max_h, len(w_lines))

        row_lines = []
        for h in range(max_h):
            line_parts = []
            for i in range(num_cols):
                cell_line = wrapped_cells[i][h] if h < len(wrapped_cells[i]) else ""
                vis_w = str_width(cell_line)
                pad = max(0, col_widths[i] - vis_w)
                if is_header:
                    cell_str = f" {BOLD}{COLOR_TITLE}{cell_line}{RESET}{' ' * pad} "
                else:
                    cell_str = f" {cell_line}{' ' * pad} "
                line_parts.append(cell_str)
            row_lines.append(f"  {B}│{R}" + f"{B}│{R}".join(line_parts) + f"{B}│{R}")
        return row_lines

    output_lines.extend(render_row_block(headers, is_header=True))
    output_lines.append(sep_line)

    for idx, r in enumerate(rows):
        output_lines.extend(render_row_block(r, is_header=False))
        if idx < len(rows) - 1:
            output_lines.append(sep_line)

    output_lines.append(bot_line)
    return output_lines


# ─── Full-Page Header & Footer Helpers ─────────────────────────────────────────

def render_header(model_name, reasoning_effort, active_cwd, supports_reasoning=True):
    """Welcome header: Nexara's pet beside four lines of context, or the same four lines as plain text."""
    from config import VERSION
    sep = ui_symbol('·', '/')
    model = model_name[len('Lyra '):] if model_name.startswith('Lyra ') else model_name
    reasoning = reasoning_effort if supports_reasoning else 'tanpa reasoning'
    art = pet_art() if mascot_fits() else None
    room = max(10, get_terminal_width() - 4 - (PET_COLS + 3 if art else 0))
    mark = ui_symbol('✦', '*') + ' ' if art is None else ''
    lines = [
        f"{mark}{gradient_text('Lyra CLI')}{COLOR_DIM}  v{VERSION}{RESET}",
        f"{COLOR_TITLE}Mau ngerjain apa hari ini?{RESET}",
        f"{COLOR_DIM}{fit_console_text(f'{model} {sep} {reasoning} {sep} {short_path(active_cwd)}', room)}{RESET}",
        f"{COLOR_DIM}{fit_console_text(f'/ perintah {sep} @ file {sep} /help', room)}{RESET}",
    ]
    print()
    if art is None:
        for line in lines:
            print('  ' + line)
    else:
        top = 3                                               # the text block sits slightly above the middle
        for index, row in enumerate(art):
            text = lines[index - top] if 0 <= index - top < len(lines) else ''
            print('  ' + row + ('   ' + text if text else ''))
    print()


def render_full_divider(color=COLOR_BORDER):
    width = max(1, min(get_terminal_width() - 4, 88))
    print(f"  {color}{'─' * width}{RESET}")


def render_footer_bar():
    print(f"  {COLOR_DIM}/ perintah · /help bantuan{RESET}")


def format_clean_thinking_line(line):
    """Format baris penalaran tanpa box border."""
    plain = strip_ansi(line)
    if not plain.strip():
        return ""
    return f"  {COLOR_DIM}{ITALIC}{plain}{RESET}"


# ─── Legacy Chat Bubble UI Helpers (Compatibility) ────────────────────────────
def render_ai_bubble_top():
    pass

def render_ai_bubble_bottom():
    pass

def format_markdown_line_bubble(line, state, width=None):
    row, state = format_markdown_line(line, state)
    return [row], state

def render_thinking_top():
    print(f"  {COLOR_DIM}{ITALIC}🧠 Process penalaran...{RESET}")

def render_thinking_bottom():
    print()

def format_thinking_line_bubble(line, width=None):
    formatted = format_clean_thinking_line(line)
    return [formatted] if formatted else []








# ─── Interactive command editor ──────────────────────────────────────────────
APPROVAL_MODES = ('ask', 'edits', 'all')


def approval_footer(mode):
    """Footer segment for the approval mode: (text, ansi colour)."""
    arrows = ui_symbol('▸▸', '>>')
    if mode == 'all':
        return f'{arrows} AUTO SEMUA {ui_symbol("·", "-")} perintah jalan tanpa tanya (Shift+Tab ganti)', f'{BOLD}{RED}'
    if mode == 'edits':
        return f'{arrows} auto-setuju edit file (Shift+Tab ganti)', YELLOW
    return f'{arrows} tanya dulu (Shift+Tab ganti)', COLOR_DIM


COMMANDS = [
    ('/init', 'Buat atau perbarui LYRA.md untuk project ini'),
    ('/instruksi', 'Lihat LYRA.md yang sedang dimuat'),
    ('/undo', 'Urungkan perubahan file terakhir dari Lyra'),
    ('/compact', 'Ringkas percakapan agar konteks longgar'),
    ('/resume', 'Lanjutkan percakapan yang tersimpan'),
    ('/mode', 'Atur persetujuan: tanya, edit, atau semua'),
    ('/restart', 'Mulai ulang Lyra (setelah update)'),
    ('/status', 'Lihat ringkasan sesi dan konfigurasi'),
    ('/todos', 'Lihat daftar tugas yang sedang berjalan'),
    ('/details', 'Buka detail aktivitas terakhir'),
    ('/model', 'Pilih model Lyra'),
    ('/reasoning', 'Atur penalaran low / medium'),
    ('/memory', 'Lihat dan kelola catatan'),
    ('/time', 'Lihat waktu komputer'),
    ('/reminder', 'Kelola pengingat desktop'),
    ('/project', 'Buat project lewat wizard'),
    ('/cd', 'Pindah direktori kerja'),
    ('/ls', 'Lihat isi folder'),
    ('/run', 'Jalankan perintah dengan konfirmasi'),
    ('/history', 'Lihat percakapan terakhir'),
    ('/clear', 'Bersihkan percakapan'),
    ('/update', 'Cek pembaruan aplikasi'),
    ('/version', 'Lihat versi terpasang'),
    ('/login', 'Masuk dengan akun AstByte'),
    ('/logout', 'Keluar dari akun AstByte'),
    ('/kuota', 'Lihat sisa token hari ini'),
    ('/reset-key', 'Ganti API key'),
    ('/help', 'Lihat bantuan lengkap'),
]



# Longer help for `/help <perintah>`: usage, what it does, aliases, examples and caveats.
COMMAND_DETAILS = {
    '/init': {'usage': '/init', 'desc': 'Meminta Lyra mempelajari project di folder kerja (struktur, README, file manifest) lalu menulis LYRA.md: tujuan, struktur, perintah tes dan build, serta konvensi. Bila LYRA.md sudah ada, Lyra memeriksa dan memperbaruinya.',
              'examples': ['/init'], 'notes': ['Lyra menulis lewat write_file atau edit_file, jadi diff dan izin tetap muncul dulu.', 'LYRA.md dibaca otomatis di sesi berikutnya. Lihat yang dimuat dengan /instruksi.']},
    '/instruksi': {'usage': '/instruksi', 'desc': 'Menampilkan file LYRA.md yang sedang dimuat untuk sesi ini beserta ukurannya.',
                   'examples': ['/instruksi'], 'notes': ['LYRA.md dicari dari folder kerja ke atas sampai root repositori (atau folder home). Yang paling dekat diutamakan.', 'Isinya ikut dikirim ke API Lyra pada setiap pesan; maksimal 20 KB per file dan 40 KB total.']},
    '/undo': {'usage': '/undo [list]', 'desc': 'Mengembalikan perubahan file terakhir yang dibuat Lyra (write_file atau edit_file). Diff ditampilkan dan izin diminta dulu. File yang dibuat Lyra dihapus saat diurungkan.',
              'examples': ['/undo', '/undo list'], 'notes': ['Mengingat 20 perubahan terakhir, untuk file sampai 2 MB.', 'Perubahan lewat perintah terminal (sed, git, dan sebagainya) tidak bisa diurungkan.']},
    '/compact': {'usage': '/compact [fokus]', 'desc': 'Meringkas semua percakapan sebelum permintaan terakhir menjadi satu ringkasan pendek, supaya konteks (ctx di footer) longgar kembali.',
                 'examples': ['/compact', '/compact fokus ke tes yang gagal'], 'notes': ['Permintaan terakhir dan tool yang sedang berjalan tetap utuh.', 'Butuh satu panggilan ke model, jadi memakai sedikit kuota.']},
    '/resume': {'usage': '/resume [hapus]', 'desc': 'Membuka menu percakapan tersimpan lalu melanjutkan yang kamu pilih. Percakapan disimpan otomatis setelah satu giliran selesai.',
                'examples': ['/resume', '/resume hapus'], 'notes': ['Tersimpan di ~/.amagi_sessions (30 terbaru), hanya bisa dibaca penggunamu.', '/resume hapus menghapus semuanya. LYRA_NO_HISTORY=1 mematikan penyimpanan.', 'amagi --continue langsung melanjutkan yang terakhir saat membuka aplikasi.']},
    '/mode': {'usage': '/mode [ask|edit|all]', 'desc': 'Mengatur seberapa banyak Lyra boleh jalan tanpa bertanya. Tanpa argumen, menampilkan mode sekarang. Shift+Tab juga berganti mode.',
              'examples': ['/mode', '/mode edit', '/mode ask'], 'notes': ['ask: setiap tulis file dan perintah meminta izin (bawaan).', 'edit: penulisan file otomatis disetujui, perintah terminal tetap bertanya.', 'all: semuanya otomatis; meminta konfirmasi y/n. Perintah berbahaya (rm -rf, sudo, git push --force, ...) tetap meminta izin.', 'Mode tidak disimpan; setiap sesi baru mulai dari ask.']},
    '/restart': {'usage': '/restart', 'desc': 'Memulai ulang Lyra dengan versi yang terpasang, misalnya setelah /update, tanpa mengetik amagi lagi.',
                 'examples': ['/restart'], 'notes': ['Percakapan sekarang tidak ikut; /resume bisa melanjutkannya.']},
    '/status': {'usage': '/status', 'desc': 'Ringkasan sesi: versi, model, reasoning, direktori, branch, cara masuk, ukuran percakapan, tugas, persetujuan, perubahan yang bisa diurungkan, riwayat, daemon, dan terminal.',
                'examples': ['/status'], 'notes': ['API key dan token tidak pernah ditampilkan.']},
    '/todos': {'usage': '/todos', 'desc': 'Menampilkan daftar tugas yang sedang dikerjakan Lyra pada pekerjaan multi-langkah.',
               'aliases': ['/todo'], 'examples': ['/todos'], 'notes': ['Lyra membuat dan memperbarui daftar ini sendiri.']},
    '/details': {'usage': '/details', 'desc': 'Membuka detail lima aktivitas tool terakhir (hasil lengkap perintah dan file yang dibaca).',
                 'examples': ['/details'], 'notes': ['Riwayat aktivitas maksimal 20, hanya di memori.']},
    '/model': {'usage': '/model', 'desc': 'Membuka menu model Lyra. Pilihan disimpan sebagai default untuk sesi berikutnya. Model yang mendukung penalaran lanjut ke pilihan tingkat penalaran.',
               'examples': ['/model'], 'notes': ['Gerakkan dengan ↑ ↓, Enter memilih, angka langsung memilih, Esc membatalkan.']},
    '/reasoning': {'usage': '/reasoning', 'desc': 'Memilih tingkat penalaran: Cepat (low) atau Sedang (medium). Hanya berlaku untuk model yang mendukung penalaran.',
                   'aliases': ['/effort'], 'examples': ['/reasoning'], 'notes': ['Tersimpan sebagai default.']},
    '/memory': {'usage': '/memory', 'desc': 'Membaca, menambah, atau menghapus catatan jangka panjang di ~/.amagi_memory.md. Isinya ikut dibaca Lyra pada setiap pesan.',
                'aliases': ['/mem'], 'examples': ['/memory'], 'notes': ['Lyra juga bisa menyimpan catatan sendiri saat kamu minta "ingat ini".']},
    '/time': {'usage': '/time', 'desc': 'Menampilkan tanggal, waktu, dan zona waktu komputermu.',
              'aliases': ['/jam', '/tanggal'], 'examples': ['/time']},
    '/reminder': {'usage': '/reminder', 'desc': 'Menu pengingat: buat, lihat, batalkan, atau pastikan daemon latar belakang aktif. Notifikasi muncul saat waktunya tiba.',
                  'aliases': ['/remind', '/alarm'], 'examples': ['/reminder'], 'notes': ['Waktu bisa 10m, 1h, 30s, atau 14:30.', 'Komputer harus tetap menyala.']},
    '/project': {'usage': '/project', 'desc': 'Wizard membuat project baru: pilih tipe lewat menu, lalu isi nama dan folder tujuan.',
                 'examples': ['/project'], 'notes': ['Tipe: react, next, vue, laravel, php, express, django, fastapi, flutter, node.', 'Perlu runtime framework yang bersangkutan (misalnya Node.js untuk React).']},
    '/cd': {'usage': '/cd <folder>', 'desc': 'Pindah direktori kerja aktif. Lyra membaca dan menulis file relatif terhadap folder ini.',
            'examples': ['/cd ~/projects/web', '/cd ..']},
    '/ls': {'usage': '/ls [folder]', 'desc': 'Menampilkan isi folder (dua tingkat). Tanpa argumen memakai direktori kerja aktif.',
            'examples': ['/ls', '/ls src']},
    '/run': {'usage': '/run <perintah>', 'desc': 'Menjalankan perintah terminal dari direktori aktif, lewat konfirmasi eksekusi yang menampilkan seluruh perintah.',
             'examples': ['/run git status', '/run python -m pytest'], 'notes': ['Mengikuti mode persetujuan: mode all tidak bertanya, kecuali perintah berbahaya.']},
    '/history': {'usage': '/history', 'desc': 'Menampilkan ringkasan 10 pesan terakhir dari percakapan aktif.',
                 'examples': ['/history'], 'notes': ['Untuk percakapan yang sudah ditutup, pakai /resume.']},
    '/clear': {'usage': '/clear', 'desc': 'Membersihkan percakapan aktif, daftar tugas, dan konteks, lalu memulai percakapan baru.',
               'examples': ['/clear'], 'notes': ['Percakapan sebelumnya tetap tersimpan dan bisa dilanjutkan lewat /resume.', 'Memori jangka panjang tidak ikut terhapus.']},
    '/update': {'usage': '/update', 'desc': 'Memeriksa versi terbaru di GitHub dan menawarkan pembaruan. Setelah selesai, jalankan /restart.',
                'aliases': ['/check-update'], 'examples': ['/update', '/restart']},
    '/version': {'usage': '/version', 'desc': 'Menampilkan versi Lyra CLI yang terpasang.',
                 'aliases': ['/v'], 'examples': ['/version'], 'notes': ['Di luar aplikasi: amagi --version.']},
    '/login': {'usage': '/login', 'desc': 'Masuk dengan akun AstByte. CLI menampilkan kode dan membuka browser; setujui di halaman AstByte lalu kembali ke terminal.',
               'examples': ['/login'], 'notes': ['Password tidak pernah diketik di CLI.', 'Memberi kuota token harian sesuai tier akunmu.']},
    '/logout': {'usage': '/logout', 'desc': 'Keluar dari akun AstByte di perangkat ini.',
                'examples': ['/logout'], 'notes': ['Pakai /login atau /reset-key untuk masuk lagi.']},
    '/kuota': {'usage': '/kuota', 'desc': 'Menampilkan sisa token harian, tier, waktu reset, dan apakah saldo developer aktif sebagai cadangan.',
               'aliases': ['/quota'], 'examples': ['/kuota'], 'notes': ['Hanya untuk login akun. Persentase sisa juga tampil di footer.']},
    '/reset-key': {'usage': '/reset-key', 'desc': 'Menghapus API key tersimpan lalu meminta key pengganti.',
                   'examples': ['/reset-key'], 'notes': ['Variabel ASTBYTE_API_KEY, bila diatur, dibaca lebih dulu daripada key tersimpan.']},
    '/help': {'usage': '/help [perintah]', 'desc': 'Tanpa argumen menampilkan semua perintah. Dengan nama perintah menampilkan penjelasan, alias, dan contohnya.',
              'aliases': ['/'], 'examples': ['/help', '/help model', '/help mode']},
}

COMMAND_ALIASES = {alias: name for name, info in COMMAND_DETAILS.items() for alias in info.get('aliases', [])}


def resolve_command(text):
    """Map what the user typed (`model`, `/model`, `/mem`) to a canonical command, or None."""
    name = str(text or '').strip().lower()
    if not name:
        return None
    if name != '/' and not name.startswith('/'):
        name = '/' + name
    name = COMMAND_ALIASES.get(name, name)
    return name if name in COMMAND_DETAILS else None


def suggest_commands(text, limit=3):
    import difflib
    name = str(text or '').strip().lower().lstrip('/')
    pool = [c[1:] for c, _ in COMMANDS] + [a[1:] for a in COMMAND_ALIASES if len(a) > 2]
    return ['/' + m for m in difflib.get_close_matches(name, pool, n=limit, cutoff=0.6)]


def short_path(directory):
    home = os.path.expanduser('~')
    if directory == home:
        return '~'
    if directory.startswith(home + os.sep):
        return '~' + directory[len(home):]
    return directory


def toolbar_text(model, effort, directory, supports_reasoning=True, branch=None, context_pct=None, quota=None):
    model = model.removeprefix('Lyra ') if hasattr(str, 'removeprefix') else model.replace('Lyra ', '', 1)
    reasoning = effort if supports_reasoning else 'tanpa reasoning'
    separator = ui_symbol('·', '/')
    location = short_path(directory) + (' / ' + branch if branch else '')
    context = ' {} ctx ~{}%'.format(separator, context_pct) if context_pct is not None else ''
    context += ' {} {}'.format(separator, quota) if quota else ''
    return '{} {} {}{}  |  {}'.format(model, separator, reasoning, context, location)


try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.layout.containers import HSplit, Window, to_container, ConditionalContainer, DynamicContainer
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.data_structures import Size
    from prompt_toolkit.filters import Condition
    EDITOR_AVAILABLE = True
except ImportError:
    EDITOR_AVAILABLE = False


if EDITOR_AVAILABLE:
    class ConsoleSession(PromptSession):
        def __init__(self, *args, live=None, **kwargs):
            self._live = live           # must exist before PromptSession builds the layout
            super().__init__(*args, **kwargs)

        def _terminal_size(self):
            output = getattr(getattr(self, 'app', None), 'output', None) or getattr(self, '_output', None)
            return output.get_size() if output else Size(rows=24, columns=get_terminal_width())

        def _can_frame(self):
            size = self._terminal_size()
            return size.rows >= 7 and size.columns >= 24

        def _get_default_buffer_control_height(self):
            size = self._terminal_size()
            if size.rows < 7 or size.columns < 24:
                return Dimension(min=1)
            return super()._get_default_buffer_control_height()

        def _frame_height(self):
            width = max(1, self._terminal_size().columns - 6)
            rows = sum(max(1, (str_width(line) + width - 1) // width) for line in self.default_buffer.document.lines)
            # Autocomplete reserves buffer rows even before its menu is visible.
            # Account for those rows plus BOTH borders; a 3-row frame cannot
            # contain a 3-row buffer, regardless of the physical window size.
            minimum = self._get_default_buffer_control_height().min
            return min(8, max(rows, minimum, 1) + 2)

        def _ruled(self, body):
            """Composer between two full-width rules, as in Claude Code, instead of a closed box."""
            glyph = '─' if unicode_terminal() else '-'
            def rule():
                return Window(height=1, char=glyph, style='class:composer.rule')
            return HSplit([rule(), body, rule()], height=self._frame_height)

        def _create_layout(self):
            layout = super()._create_layout()
            if isinstance(layout.container, HSplit):
                body = layout.container.children[0]
                framed_body = to_container(self._ruled(body))
                layout.container.children[0] = DynamicContainer(lambda: framed_body if self._can_frame() else body)
                toolbar = layout.container.children[-1]
                layout.container.children[-1] = ConditionalContainer(
                    toolbar, filter=Condition(lambda: self._terminal_size().rows >= 7))
                live = self._live
                if live is not None:
                    # Above the composer: the answer line being streamed, then the status line.
                    streaming = Window(FormattedTextControl(lambda: ANSI(live.partial)), wrap_lines=True,
                                       dont_extend_height=True)
                    status = Window(FormattedTextControl(lambda: ANSI(live.status_text())), dont_extend_height=True)
                    layout.container.children[0:0] = [
                        to_container(ConditionalContainer(streaming, filter=Condition(lambda: bool(live.partial)))),
                        to_container(ConditionalContainer(status, filter=Condition(live.status_visible))),
                    ]
            return layout

    class SlashCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if text.lower().startswith('/help ') and text.count(' ') == 1:
                partial = text[6:].lstrip('/').lower()
                for command, description in COMMANDS:
                    if command[1:].startswith(partial):
                        yield Completion(command[1:], start_position=-len(partial), display_meta=description)
                return
            if not text.startswith('/') or any(char.isspace() for char in text):
                return
            for command, description in COMMANDS:
                if command.startswith(text.lower()):
                    yield Completion(command, start_position=-len(text), display_meta=description)


class TerminalInput:
    def __init__(self, context, input_stream=None, output_stream=None, on_cycle_mode=None, live=None):
        self.context = context
        self.live = live
        self.on_cycle_mode = on_cycle_mode
        self.session = None
        self._bindings = None
        self.branch = None
        self._hinted = False
        self.notice = None   # right-aligned footer message, e.g. an available update
        # Pipes and dumb terminals keep the plain text input path.
        interactive = sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'
        if EDITOR_AVAILABLE and (interactive or input_stream is not None):
            bindings = KeyBindings()

            idle = Condition(lambda: live is None or not live.busy)

            @bindings.add('escape', 'enter', filter=idle)
            @bindings.add('c-j')
            def newline(event):
                event.current_buffer.insert_text('\n')

            if live is not None:
                @bindings.add('escape', filter=~idle, eager=True)
                def cancel_turn(event):
                    live.request_cancel()

                @bindings.add('c-c')
                def interrupt(event):
                    if live.busy:
                        live.request_cancel()
                    else:
                        event.current_buffer.reset()

                @bindings.add('c-d', filter=idle & Condition(lambda: not self.session.default_buffer.text))
                def leave(event):
                    live.submit_eof()

            @bindings.add('s-tab')
            def cycle_mode(event):
                if self.on_cycle_mode:
                    self.on_cycle_mode()
                event.app.invalidate()

            @bindings.add('tab')
            def complete_command(event):
                buffer = event.current_buffer
                if buffer.complete_state:
                    buffer.complete_next()
                    return
                matches = list(self.completer.get_completions(buffer.document, None))
                if len(matches) == 1:
                    buffer.apply_completion(matches[0])
                elif matches:
                    buffer.start_completion(select_first=True)

            self._bindings = bindings
            self.completer = WorkspaceCompleter(lambda: self.context()['directory'])
            self.session = ConsoleSession(
                history=InMemoryHistory(),
                completer=self.completer,
                complete_while_typing=True,
                key_bindings=bindings,
                bottom_toolbar=self._toolbar,
                prompt_continuation='  ',
                style=Style.from_dict({
                    'bottom-toolbar': 'noreverse',
                    'composer.rule': '#8b7bb8' if IS_DARK else '#7c3aed',
                    'composer.border': '#7d708f' if IS_DARK else '#88789a',
                    'composer.label': '#b6a0dc' if IS_DARK else '#7c3aed',
                    'completion-menu.completion': 'bg:#292b30 #d6d7df',
                    'completion-menu.completion.current': 'bg:#514568 #ffffff',
                    'completion-menu.meta.completion': 'bg:#292b30 #a8a8b5',
                    'completion-menu.meta.completion.current': 'bg:#514568 #ffffff',
                }),
                input=input_stream,
                output=output_stream,
                reserve_space_for_menu=3,
                erase_when_done=True,
                live=live,
                **({'refresh_interval': 0.1} if live is not None else {}),
            )
            if live is not None:
                self.session.app.ttimeoutlen = 0.05      # a lone Esc must cancel at once
                def accept(buffer):
                    text = buffer.text.strip()
                    if text:
                        live.submit(text)
                    return False        # keep the application running; the buffer is cleared
                self.session.default_buffer.accept_handler = accept

    def _toolbar(self):
        context = dict(self.context())
        approval = context.pop('approval', 'ask')
        quota_pct = context.pop('quota_pct', None)
        text = toolbar_text(**context, branch=self.branch)
        columns = self.session.app.output.get_size().columns if self.session else get_terminal_width()
        width = max(1, columns - 4)
        sep = ui_symbol('·', '/')
        pct = context.get('context_pct')
        low_quota = quota_pct is not None
        color = (RED if (pct is not None and pct >= 95) or (low_quota and quota_pct <= 10)
                 else YELLOW if (pct is not None and pct >= 80) or (low_quota and quota_pct <= 25) else COLOR_DIM)
        mode_text, mode_color = approval_footer(approval)
        queued = self.live.inbox.qsize() if self.live is not None else 0
        queue_text = f' {sep} {queued} pesan antre' if queued else ''
        rest = f' {sep} / perintah {sep} @ file {sep} Esc batal {sep} Alt+Enter baris baru'
        if str_width(mode_text + queue_text + rest) <= width:
            plain = mode_text + queue_text + rest
            second = f'{mode_color}{mode_text}{RESET}{YELLOW}{queue_text}{RESET}{COLOR_DIM}{rest}'
        else:
            plain = fit_console_text(mode_text + queue_text, width)
            second = f'{mode_color}{plain}'
        if self.notice:
            notice = fit_console_text(self.notice, max(1, width - 2))
            tone = GREEN if notice.startswith(ui_symbol('✔', 'OK')) else YELLOW
            gap = width - str_width(plain) - str_width(notice)
            second += (' ' * gap if gap >= 3 else '') + f'{RESET}{tone}{notice}'
        return ANSI('  {}{}{}\n  {}{}'.format(color, fit_console_text(text, width), RESET, second, RESET))

    def run_live(self):
        """Own the terminal for the whole session (main thread); the worker thread feeds read()."""
        live = self.live

        def attach():
            import asyncio
            live.attach(self.session.app, asyncio.get_running_loop())

        try:
            self.session.prompt(ANSI(' {}{}{}{} '.format(BOLD, COLOR_LYRA, ui_symbol('›', '>'), RESET)), pre_run=attach)
        except (EOFError, KeyboardInterrupt):
            pass
        finally:
            live.detach()

    def read(self):
        if self.live is not None:
            self.branch = workspace_branch(self.context().get('directory', os.getcwd()))
            return self.live.read()
        marker = ui_symbol('›', '>')
        prompt = ' {}{}{}{} '.format(BOLD, COLOR_LYRA, marker, RESET)
        self.branch = workspace_branch(self.context().get('directory', os.getcwd()))
        if self.session is None:
            if not EDITOR_AVAILABLE and not self._hinted:
                self._hinted = True
                print(f"  {COLOR_DIM}Editor sederhana: paket prompt_toolkit belum terpasang, jadi menu panah, autocomplete, "
                      f"dan input beberapa baris tidak aktif.{RESET}")
                print(f"  {COLOR_DIM}Pasang dengan: {sys.executable} -m pip install prompt_toolkit{RESET}\n")
            return input(prompt)
        return self.session.prompt(ANSI(prompt))


NOT_INTERACTIVE = object()   # returned by choose() when there is no real terminal to draw a menu on


TERMINAL_RUNNER = None   # set by the live console: runs blocking terminal code with the live area suspended


def choose(title, options, selected=0, subtitle='', input_stream=None, output_stream=None, force=False, body=None):
    """Arrow-key menu (see _choose). Inside the live console the live area is suspended while it shows."""
    runner = TERMINAL_RUNNER
    if runner is not None and input_stream is None and output_stream is None and not force:
        return runner(lambda: _choose(title, options, selected, subtitle, body=body))
    return _choose(title, options, selected, subtitle, input_stream, output_stream, force, body=body)


def _screen_rows():
    try:
        return os.get_terminal_size().lines
    except (OSError, ValueError):
        return 24


def _display_rows(line, width):
    """Screen rows one (ANSI-styled) line takes once the terminal wraps it."""
    return max(1, -(-str_width(strip_ansi(line)) // max(1, width)))


def _fit_body(lines, spare):
    """Trim pre-formatted lines so the whole panel fits on screen; says how many were left out."""
    width = max(20, get_terminal_width() - 1)
    room = max(3, _screen_rows() - spare)
    out, used = [], 0
    for index, line in enumerate(lines):
        need = _display_rows(line, width)
        if used + need > room - (1 if index < len(lines) - 1 else 0):
            out.append(f'  {COLOR_DIM}… {len(lines) - index} baris lagi{RESET}')
            break
        out.append(line)
        used += need
    return out


def _choose(title, options, selected=0, subtitle='', input_stream=None, output_stream=None, force=False, body=None):
    """Arrow-key menu. `options` is a list of (label, description).

    Returns the chosen index, None when cancelled (Esc, q, Ctrl+C), or NOT_INTERACTIVE when stdin or
    stdout is not a terminal (or prompt_toolkit is missing) so the caller can fall back to typed input.
    """
    interactive = EDITOR_AVAILABLE and (force or (sys.stdin.isatty() and sys.stdout.isatty()
                                                  and os.environ.get('TERM') != 'dumb'))
    if not interactive or not options:
        return NOT_INTERACTIVE
    from prompt_toolkit.application import Application
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.controls import FormattedTextControl

    count = len(options)
    state = {'index': max(0, min(int(selected), count - 1))}
    body_lines = _fit_body(list(body), count + 6 + (1 if subtitle else 0)) if body else []

    def render():
        room = max(20, get_terminal_width() - 4)
        rows = [f'  {BOLD}{COLOR_LYRA}{title}{RESET}']
        if subtitle:
            rows.append(f'  {COLOR_DIM}{fit_console_text(subtitle, room)}{RESET}')
        rows.append('')
        if body_lines:
            rows.extend(body_lines)
            rows.append('')
        label_w = max(str_width(label) for label, _ in options)
        for number, (label, description) in enumerate(options):
            active = number == state['index']
            pointer = f'{BOLD}{COLOR_LYRA}{ui_symbol("❯", ">")}{RESET}' if active else ' '
            name = f'{BOLD}{label}{RESET}' if active else label
            gap = ' ' * (label_w - str_width(label) + 2)
            detail = f'{gap}{COLOR_DIM}{fit_console_text(description, max(4, room - label_w - 10))}{RESET}' if description else ''
            rows.append(f'  {pointer} {number + 1}. {name}{detail}')
        rows.append('')
        arrows = ui_symbol('↑↓', 'Atas/Bawah')
        rows.append(f'  {COLOR_DIM}{arrows} pilih {ui_symbol("·", "-")} Enter konfirmasi {ui_symbol("·", "-")} angka langsung {ui_symbol("·", "-")} Esc batal{RESET}')
        return ANSI('\n'.join(rows))

    bindings = KeyBindings()

    @bindings.add('up')
    @bindings.add('k')
    def move_up(event):
        state['index'] = (state['index'] - 1) % count

    @bindings.add('down')
    @bindings.add('j')
    def move_down(event):
        state['index'] = (state['index'] + 1) % count

    @bindings.add('enter')
    def confirm(event):
        event.app.exit(result=state['index'])

    @bindings.add('escape', eager=True)
    @bindings.add('q')
    @bindings.add('c-c')
    @bindings.add('c-d')
    def cancel(event):
        event.app.exit(result=None)

    for digit in range(1, min(count, 9) + 1):
        @bindings.add(str(digit))
        def pick(event, digit=digit):
            event.app.exit(result=digit - 1)

    application = Application(layout=Layout(Window(FormattedTextControl(render), dont_extend_height=True)),
                              key_bindings=bindings, full_screen=False, erase_when_done=True,
                              input=input_stream, output=output_stream)
    return application.run()


def show_panel(lines, title='', input_stream=None, output_stream=None, force=False):
    """Read-only panel, closed with Enter, Esc, q or space. Leaves no trace on the screen once closed.

    Returns True after showing it, or NOT_INTERACTIVE when there is no terminal (the caller prints instead).
    """
    runner = TERMINAL_RUNNER
    if runner is not None and input_stream is None and output_stream is None and not force:
        return runner(lambda: _panel(lines, title))
    return _panel(lines, title, input_stream, output_stream, force)


def _panel(lines, title='', input_stream=None, output_stream=None, force=False):
    interactive = EDITOR_AVAILABLE and (force or (sys.stdin.isatty() and sys.stdout.isatty()
                                                  and os.environ.get('TERM') != 'dumb'))
    if not interactive:
        return NOT_INTERACTIVE
    from prompt_toolkit.application import Application
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.controls import FormattedTextControl

    shown = _fit_body(list(lines), 4 + (1 if title else 0))

    def render():
        rows = []
        if title:
            rows.append(f'  {BOLD}{COLOR_LYRA}{title}{RESET}')
        rows.extend(shown)
        rows.append('')
        rows.append(f'  {COLOR_DIM}Enter / Esc untuk menutup{RESET}')
        return ANSI('\n'.join(rows))

    bindings = KeyBindings()

    @bindings.add('enter')
    @bindings.add('escape', eager=True)
    @bindings.add('q')
    @bindings.add(' ')
    @bindings.add('c-c')
    @bindings.add('c-d')
    def close(event):
        event.app.exit(result=True)

    application = Application(layout=Layout(Window(FormattedTextControl(render), dont_extend_height=True)),
                              key_bindings=bindings, full_screen=False, erase_when_done=True,
                              input=input_stream, output=output_stream)
    return application.run()


BAND_BG = rgb_bg(48, 48, 54) if IS_DARK else rgb_bg(228, 228, 234)


def render_user_band(text, max_rows=12):
    """Echo a submitted message as a full-width shaded band, like Claude Code's transcript."""
    width = max(24, get_terminal_width())
    room = width - 4
    marker = ui_symbol('›', '>')
    rows = []
    for raw in text.replace('\t', '    ').split('\n'):
        rows.extend(wrap_text_display_width(raw, room) or [''])
    hidden = max(0, len(rows) - max_rows)
    if hidden:
        rows = rows[:max_rows - 1] + [f'… +{hidden + 1} baris']
    print()
    for index, row in enumerate(rows):
        lead = f'{BOLD}{COLOR_LYRA}{marker}{RESET}{BAND_BG}' if index == 0 else ' '
        pad = ' ' * max(0, room - str_width(row))
        print(f'{BAND_BG} {lead} {row}{pad}{RESET}')


def tool_call_parts(name, arguments):
    """(label, value) for a tool call; value is only a path/command, never file contents."""
    labels = {
        'list_directory': ('Lihat folder', 'path'),
        'read_file': ('Baca', 'filepath'),
        'write_file': ('Tulis', 'filepath'),
        'edit_file': ('Ubah', 'filepath'),
        'search': ('Cari', 'pattern'),
        'create_directory': ('Buat folder', 'dirpath'),
        'execute_command': ('Jalankan', 'command'),
        'init_project': ('Buat project', 'project_name'),
        'save_memory': ('Simpan memori', None),
        'read_memory': ('Baca memori', None),
        'get_system_time': ('Lihat waktu komputer', None),
        'set_reminder': ('Buat pengingat', None),
        'list_reminders': ('Lihat pengingat', None),
        'cancel_reminder': ('Batalkan pengingat', None),
        'update_todos': ('Daftar tugas', None),
    }
    label, key = labels.get(name, ('Tool ' + name, None))
    value = str(arguments.get(key, '')) if key else ''
    if name == 'search' and not value:
        value = str(arguments.get('glob', ''))
    if name == 'execute_command':
        written = re.match(r"\s*(?:cat|tee)\s+(?:>>?\s*)?([^\s<>|;&]+)[^\n]*<<", value) or re.match(r"\s*cat\s*>>?\s*([^\s<>|;&]+)\s*<<", value)
        if written:
            return 'Tulis (shell)', written.group(1)[:90]
        value = value.split('\n', 1)[0] + (' …' if '\n' in value.strip() else '')
    # Keep paths and multiline scripts from injecting control sequences in labels.
    value = ''.join(char if char.isprintable() else ' ' for char in value)
    return label, value[:90] + ('…' if len(value) > 90 else '')


def tool_activity(name, arguments):
    label, value = tool_call_parts(name, arguments)
    return '{}{}{}'.format(label, ' ' + ui_symbol('·', '/') + ' ' if value else '', value)


# ─── Console capabilities and file context ───────────────────────────────────
def clear_terminal():
    """Wipe the visible screen so the shell looks fresh again. Does nothing (returns False) off a terminal."""
    try:
        if not (sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'):
            return False
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()
        return True
    except (AttributeError, ValueError, OSError):
        return False


def unicode_terminal():
    if os.environ.get('LYRA_ASCII', '').lower() in ('1', 'true', 'yes') or os.environ.get('TERM') == 'dumb':
        return False
    try:
        '╭─✦✓'.encode(sys.stdout.encoding or getattr(sys.__stdout__, 'encoding', None) or 'utf-8')
        return True
    except (UnicodeError, LookupError):
        return False


def ui_symbol(symbol, fallback):
    return symbol if unicode_terminal() else fallback


def fit_console_text(text, width):
    text = ''.join(char for char in str(text) if char.isprintable())
    if str_width(text) <= width:
        return text
    suffix = ui_symbol('…', '~')
    result = ''
    for char in text:
        if str_width(result + char + suffix) > width:
            break
        result += char
    return result + suffix if width else ''


def workspace_branch(directory):
    import subprocess
    try:
        result = subprocess.run(['git', 'symbolic-ref', '--quiet', '--short', 'HEAD'],
                                cwd=directory, capture_output=True, text=True, timeout=0.5)
        return fit_console_text(result.stdout.strip(), 32) if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


REFERENCE_PATTERN = re.compile(r'(?<!\S)@(?:"([^"\n]+)"|\'([^\'\n]+)\'|([^\s]+))')


def prepare_user_message(text, directory):
    """Attach only explicitly mentioned text files, bounded before any API call."""
    attachments = []
    seen = set()
    total = 0
    for match in REFERENCE_PATTERN.finditer(text):
        reference = next(value for value in match.groups() if value is not None)
        filename = os.path.abspath(os.path.join(directory, os.path.expanduser(reference)))
        real = os.path.normcase(os.path.realpath(filename))
        if real in seen:
            continue
        if len(seen) >= 8:
            raise ValueError('Maksimal 8 referensi file per pesan.')
        try:
            with open(filename, 'rb') as handle:
                data = handle.read(128 * 1024 + 1)
        except OSError as error:
            raise ValueError(f'Tidak bisa membaca @{reference}: {error.strerror}') from error
        if len(data) > 128 * 1024 or total + len(data) > 256 * 1024:
            raise ValueError('Referensi terlalu besar: maksimal 128 KB per file dan 256 KB per pesan.')
        if b'\0' in data:
            raise ValueError(f'@{reference} adalah file biner. Gunakan file teks.')
        try:
            content = data.decode('utf-8-sig')
        except UnicodeDecodeError as error:
            raise ValueError(f'@{reference} bukan teks UTF-8.') from error
        attachments.append(f'\n[Referensi file: {reference}]\n{content}\n[Akhir referensi file]')
        total += len(data)
        seen.add(real)
    return text + ('\n' + '\n'.join(attachments) if attachments else '')


if EDITOR_AVAILABLE:
    class WorkspaceCompleter(SlashCompleter):
        def __init__(self, directory):
            self.directory = directory

        def get_completions(self, document, complete_event):
            yield from super().get_completions(document, complete_event)
            match = re.search(r'(?:^|\s)@("?)([^"\n]*)$', document.text_before_cursor)
            if not match:
                return
            quote, partial = match.groups()
            if not quote and any(char.isspace() for char in partial):
                return
            expanded = os.path.expanduser(partial)
            parent, prefix = os.path.split(expanded)
            folder = os.path.join(self.directory(), parent)
            try:
                with os.scandir(folder) as entries:
                    choices = sorted((entry.name, entry.is_dir()) for entry in entries
                                     if entry.name.lower().startswith(prefix.lower()) and not entry.name.startswith('.'))[:60]
            except OSError:
                return
            for name, is_directory in choices:
                suggestion = os.path.join(os.path.dirname(partial), name)
                if is_directory:
                    suggestion += os.sep
                needs_quotes = bool(quote or ' ' in suggestion)
                value = '@' + ('"' + suggestion + ('"' if not is_directory else '') if needs_quotes else suggestion)
                length = len(partial) + len(quote) + 1
                yield Completion(value, start_position=-length, display=name + (os.sep if is_directory else ''),
                                 display_meta='folder' if is_directory else 'sertakan file')


# ─── Activity groups and change previews ─────────────────────────────────────
def activity_group(name, arguments):
    if name in ('list_directory', 'read_file', 'search'):
        return 'Eksplorasi'
    if name in ('write_file', 'edit_file', 'create_directory', 'init_project'):
        return 'Perubahan'
    if name == 'execute_command':
        command = str(arguments.get('command', ''))
        return 'Pengujian' if re.search(r'\b(pytest|unittest|vitest|jest)\b|\bnpm (?:run )?test\b', command) else 'Terminal'
    return 'Konteks'


def _result_summary(name, text, failed, cancelled):
    """One short line describing what a tool did (Claude-style result line)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    first = lines[0].lstrip('✅❌✖⚠️ ') if lines else ''
    if cancelled:
        return 'Dibatalkan'
    if name == 'execute_command':
        code = re.search(r'Exit Code:\s*(-?\d+)', text)
        return ('Gagal · exit ' if failed else 'Selesai · exit ') + (code.group(1) if code else '?')
    if failed:
        return first or 'Gagal'
    if name == 'read_file':
        return 'Membaca {} baris'.format(len(text.splitlines()))
    if name == 'list_directory':
        return '{} entri'.format(len(lines))
    if name == 'search':
        return 'Tidak ada hasil' if first.startswith('Tidak ada hasil') else '{} hasil'.format(len([l for l in lines if not l.startswith('…')]))
    return first or 'Selesai'


def _output_preview(text, limit=4):
    """First few lines of command output, without the STDOUT/STDERR markers."""
    body = [line for line in text.splitlines()[1:] if line.strip() and line.strip() not in ('STDOUT:', 'STDERR:')]
    return body[:limit], max(0, len(body) - limit)


TODO_STATUSES = ('pending', 'in_progress', 'completed')


def normalize_todos(raw):
    """Validate a model-supplied todo list. Raises ValueError with a user-facing message."""
    if not isinstance(raw, list) or not raw:
        raise ValueError('todos harus berupa daftar yang tidak kosong.')
    if len(raw) > 20:
        raise ValueError('Maksimal 20 item tugas.')
    items = []
    for entry in raw:
        if isinstance(entry, str):
            entry = {'content': entry}
        if not isinstance(entry, dict):
            raise ValueError('Setiap tugas harus berupa teks atau objek dengan "content".')
        content = entry.get('content', entry.get('task', entry.get('title', '')))
        content = ''.join(char if char.isprintable() else ' ' for char in str(content)).strip()
        status = str(entry.get('status', 'pending')).strip().lower().replace('-', '_').replace(' ', '_')
        if not content:
            raise ValueError('Isi tugas tidak boleh kosong.')
        if status not in TODO_STATUSES:
            raise ValueError('Status harus salah satu dari: ' + ', '.join(TODO_STATUSES) + '.')
        items.append({'content': content[:160], 'status': status})
    return items


def render_todo_lines(items, indent='     '):
    """Checklist lines: done items struck through, the active one bold."""
    width = max(8, get_terminal_width() - len(indent) - 6)
    lines = []
    for item in items:
        text = fit_console_text(item['content'], width)
        if item['status'] == 'completed':
            lines.append(f"{indent}{COLOR_DIM}{ui_symbol('☒', '[x]')} \033[9m{text}{RESET}" if USE_COLOR
                         else f"{indent}{ui_symbol('☒', '[x]')} {text}")
        elif item['status'] == 'in_progress':
            lines.append(f"{indent}{BOLD}{COLOR_LYRA}{ui_symbol('◼', '[>]')}{RESET} {BOLD}{text}{RESET}")
        else:
            lines.append(f"{indent}{COLOR_DIM}{ui_symbol('☐', '[ ]')}{RESET} {text}")
    return lines


READ_ONLY_TOOLS = ('list_directory', 'read_file', 'search', 'read_memory', 'get_system_time', 'list_reminders')
_COLLAPSE_LABELS = {'file': 'membaca {} file', 'folder': 'melihat {} folder', 'cari': 'mencari {} kali',
                    'konteks': 'memeriksa {} konteks'}


class ActivityLog:
    def __init__(self):
        self.entries = []
        self.group = None
        self.started_at = None
        self.files_read = 0
        self.read_files = set()
        self.rewrite = None        # None = detect a real terminal; tests may force True/False
        self._open = False         # a collapsed summary line is the last thing on screen
        self._counts = {}

    def _can_rewrite(self):
        if self.rewrite is not None:
            return self.rewrite
        return sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'

    def close_group(self):
        """Other output reached the screen, so the next read-only step starts a new summary line."""
        self._open = False
        self._counts = {}

    def begin_turn(self):
        import time
        self.group = None
        self.close_group()
        self.started_at = time.monotonic()
        self.files_read = 0
        self.read_files = set()

    def _print_header(self, name, arguments):
        label, value = tool_call_parts(name, arguments)
        room = max(8, get_terminal_width() - 4)
        shown = fit_console_text(value, max(1, room - str_width(label) - 2)) if value else ''
        detail = f'{COLOR_DIM}({shown}){RESET}' if value else ''
        print(f'\n{COLOR_LYRA}{ui_symbol("●", "*")}{RESET} {BOLD}{label}{RESET}{detail}')

    def start(self, name, arguments):
        self.group = activity_group(name, arguments)
        if name in READ_ONLY_TOOLS:
            return                      # shown as one collapsed line once the step succeeds
        self.close_group()
        self._print_header(name, arguments)

    def _collapse(self, name):
        kind = {'read_file': 'file', 'list_directory': 'folder', 'search': 'cari'}.get(name, 'konteks')
        if not self._can_rewrite():
            self._counts = {}
        self._counts[kind] = self._counts.get(kind, 0) + 1
        parts = [_COLLAPSE_LABELS[key].format(count) for key, count in self._counts.items()]
        text = ', '.join(parts)
        text = fit_console_text(text[:1].upper() + text[1:], max(8, get_terminal_width() - 4))
        if self._open and self._can_rewrite():
            sys.stdout.write('\033[1A\r\033[2K')
        else:
            print()
        print(f'{COLOR_DIM}{ui_symbol("●", "*")} {text}{RESET}')
        self._open = True

    def finish(self, name, arguments, result):
        text = str(result)
        clean = text.lstrip('❌✖⚠️ ').lower()
        exit_code = re.search(r'Exit Code:\s*(-?\d+)', text)
        failed = clean.startswith(('error', 'gagal')) or bool(exit_code and int(exit_code.group(1)) != 0)
        cancelled = 'dibatalkan' in clean
        if name == 'read_file' and not failed and not cancelled:
            self.read_files.add(os.path.normcase(os.path.abspath(str(arguments.get('filepath', '')))))
            self.files_read = len(self.read_files)
        label = fit_console_text(tool_activity(name, arguments), max(8, get_terminal_width() - 8))
        self.entries.append((label, text[:12000]))
        self.entries = self.entries[-20:]
        if name in READ_ONLY_TOOLS:
            if not failed and not cancelled:
                self._collapse(name)
                return
            self.close_group()
            self._print_header(name, arguments)
        color = RED if failed else COLOR_DIM if cancelled else COLOR_DIM
        summary = fit_console_text(_result_summary(name, text, failed, cancelled), max(8, get_terminal_width() - 8))
        connector = ui_symbol('⎿', 'L')
        print(f'  {COLOR_DIM}{connector}{RESET}  {color}{summary}{RESET}')
        if name == 'execute_command' and not cancelled:
            preview, more = _output_preview(text)
            for line in preview:
                print(f'     {COLOR_DIM}{fit_console_text(line, max(8, get_terminal_width() - 8))}{RESET}')
            if more:
                print(f'     {COLOR_DIM}… +{more} baris (/details){RESET}')
        if name == 'update_todos' and not failed:
            try:
                for line in render_todo_lines(normalize_todos(arguments.get('todos'))):
                    print(line)
            except ValueError:
                pass

    def complete_turn(self):
        import time
        if self.started_at is None:
            return
        self.close_group()
        elapsed = max(0, time.monotonic() - self.started_at)
        separator = ui_symbol('·', '/')
        text = f'Selesai {separator} {elapsed:.0f}s'
        if self.files_read:
            text += f' {separator} {self.files_read} file dibaca'
        text += f' {separator} {time.strftime("%H:%M")}'
        print(f'\n{COLOR_DIM}{ui_symbol("✻", "*")} {text}{RESET}\n')
        self.started_at = None

    def show_details(self):
        print(f'\n{COLOR_LYRA}{ui_symbol("●", "*")}{RESET} {BOLD}Detail aktivitas terakhir{RESET}')
        if not self.entries:
            print(f'  {COLOR_DIM}Belum ada aktivitas tool.{RESET}')
        for label, text in self.entries[-5:]:
            print(f'\n  {COLOR_LYRA}{label}{RESET}')
            for line in text.splitlines()[:50]:
                print(f'  {COLOR_DIM}{ui_symbol("│", "|")}{RESET} ' + fit_console_text(line, max(8, get_terminal_width() - 6)))
            if len(text.splitlines()) > 50 or len(text) >= 12000:
                print(f'  {COLOR_DIM}[detail dipotong]{RESET}')
        print()


ADD_BG = rgb_bg(20, 62, 36) if IS_DARK else rgb_bg(209, 250, 224)
DEL_BG = rgb_bg(82, 28, 34) if IS_DARK else rgb_bg(254, 215, 215)


def render_diff_preview(before, after, filename):
    """Line-numbered diff with red/green bars, like Claude Code's edit preview."""
    import difflib
    diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm='', n=2))
    added = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    removed = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    connector = ui_symbol('⎿', 'L')
    new_file = not before
    head = 'File baru' if new_file else 'Perubahan'
    print(f'  {COLOR_DIM}{connector}{RESET}  {COLOR_DIM}{head} {ui_symbol("·", "/")} {RESET}{GREEN}+{added}{RESET} {RED}-{removed}{RESET}')
    if not diff:
        print(f'     {COLOR_DIM}Tidak ada perubahan baris teks.{RESET}')
        return
    width = max(12, get_terminal_width() - 6)
    old_no = new_no = 0
    shown = 0
    for line in diff:
        if line.startswith(('---', '+++')):
            continue
        if line.startswith('@@'):
            match = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)', line)
            if match:
                old_no, new_no = int(match.group(1)), int(match.group(2))
            if shown:
                print(f'     {COLOR_DIM}{ui_symbol("⋮", ":")}{RESET}')
            continue
        if shown >= 60:
            break
        sign, text = line[:1], line[1:]
        if sign == '+':
            number, bg, fg = new_no, ADD_BG, GREEN
            new_no += 1
        elif sign == '-':
            number, bg, fg = old_no, DEL_BG, RED
            old_no += 1
        else:
            number, bg, fg = new_no, '', COLOR_DIM
            old_no += 1
            new_no += 1
        body = fit_console_text(sign + text, width - 6)
        pad = ' ' * max(0, width - 6 - str_width(body)) if bg else ''
        print(f'   {COLOR_DIM}{number:>4}{RESET} {bg}{fg}{body}{pad}{RESET}')
        shown += 1
    remaining = sum(1 for line in diff if line[:1] in '+- ' and not line.startswith(('---', '+++'))) - shown
    if remaining > 0:
        print(f'     {COLOR_DIM}[preview dipotong; {remaining} baris lainnya]{RESET}')


class StreamRenderer:
    """Incremental markdown renderer for streamed answers.

    Paragraph, list and quote text is written as it arrives, word by word, with `**bold**`,
    `*italic*` and `code` styled on the fly. Headings, rules, code blocks and tables need the whole
    line to format correctly, so those are written once their line is complete.

    With wrap=True long lines are broken at word boundaries and continuation lines keep the text
    indent, instead of the terminal cutting a word in half and restarting at column 0.
    """
    _MARKER_CHARS = frozenset('#`-*+_>|0123456789. \t[]xX')      # [ ] x X: the start of a task item

    def __init__(self, write, format_line=None, render_table=None, wrap=False, width=None):
        self.write = write
        self.wrap = wrap
        self.width_fn = width or get_terminal_width
        self.col = self.indent = 0          # columns used on this line / where wrapped text resumes
        self.word = []                      # pieces of the word being built (text and zero-width style codes)
        self.word_w = 0
        self.word_style = ''
        self.spaces = 0                     # spaces waiting to be written; dropped at a wrap or line end
        self.format_line = format_line or format_markdown_line
        self.render_table = render_table or render_markdown_table
        self.state = {'in_code': False, 'lang': ''}
        self.line = ''
        self.mode = None            # None (undecided) | 'block' | 'inline'
        self.table = []
        self.started = False
        self.lead_done = False
        self.bold = self.italic = self.code = self.star = False
        self.strike = self.tilde = self.bang = False     # ~~strike~~, a lone ~ and a ! that may start an image
        self.link = None                                 # a [text](url) candidate being collected
        self.item_start = False                          # still at the start of a list item (task boxes)
        self.skip_ws = False
        self.base = ''

    # -- public ---------------------------------------------------------
    def feed(self, text):
        out = []
        for char in text:
            self._char(char, out)
        if out:
            self.write(''.join(out))

    def finish(self):
        out = []
        if self.line.strip() or self.mode == 'inline':
            self._newline(out)
        self._flush_table(out)
        if out:
            self.write(''.join(out))

    def abort(self):
        """Interrupted mid-line: show the word in progress and make sure no style leaks into the next prompt."""
        if self.mode == 'inline':
            out = []
            self._flush_word(out)
            self.write(''.join(out) + RESET)

    # -- line machinery -------------------------------------------------
    def _char(self, char, out):
        if char == '\r':
            return
        if char == '\n':
            self._newline(out)
        elif self.mode is None:
            self.line += char
            self._decide(out, final=False)
        elif self.mode == 'block':
            self.line += char
        else:
            self._inline(char, out)

    def _classify(self, text, final):
        if self.state['in_code']:
            return 'block'
        if (re.match(r'^\s*\|', text) or re.match(r'^\s*```', text) or re.match(r'^#{1,6}[ \t]', text)
                or re.match(r'^\s*([-*_])\1\1', text)):
            return 'block'
        if not final and len(text.lstrip()) < 7 and all(char in self._MARKER_CHARS for char in text):   # "###### " needs 7
            return None
        return 'inline'

    def _decide(self, out, final):
        if not self.line.strip():
            return
        kind = self._classify(self.line, final)
        if kind == 'block':
            self.mode = 'block'
        elif kind == 'inline':
            self._begin_inline(out)

    def _newline(self, out):
        if self.mode is None:
            if not self.line.strip() and not self.state['in_code']:
                if self.started:
                    out.append('\n')
                self.line = ''
                return
            if self.mode is None and self.line.strip():
                self._decide(out, final=True)
            elif self.state['in_code']:
                self.mode = 'block'
        if self.mode == 'block':
            self._finish_block(out)
        elif self.mode == 'inline':
            self._flush_pending(out)
            self._flush_word(out)
            out.append(RESET + '\n')
        self.line = ''
        self.mode = None
        self.col = self.indent = self.spaces = 0
        self.bold = self.italic = self.code = self.star = False
        self.strike = self.tilde = self.bang = False
        self.link = None
        self.item_start = False

    # -- block lines ----------------------------------------------------
    def _lead(self):
        if self.lead_done:
            return '  '
        self.lead_done = True
        return f"{COLOR_LYRA}{ui_symbol('●', '*')}{RESET} "

    def _with_lead(self, formatted):
        if self.lead_done or not formatted.strip():
            return formatted
        self.lead_done = True
        lines = formatted.split('\n')
        for i, text in enumerate(lines):
            if text.strip():
                lines[i] = f"{COLOR_LYRA}{ui_symbol('●', '*')}{RESET} {text[2:] if text.startswith('  ') else text}"
                break
        return '\n'.join(lines)

    def _flush_table(self, out):
        if self.table:
            for row in self.render_table(self.table):
                out.append(row + '\n')
            self.table = []

    def _finish_block(self, out):
        if self.line.strip().startswith('|') and not self.state['in_code']:
            self.table.append(self.line)
            return
        self._flush_table(out)
        formatted, self.state = self.format_line(self.line, self.state)
        out.append(self._with_lead(formatted) + '\n')
        self.started = True

    # -- streamed lines -------------------------------------------------
    def _begin_inline(self, out):
        self._flush_table(out)
        text = self.line
        lead = self._lead()
        self.started = True
        self.mode = 'inline'
        self.base = WHITE
        rest = text
        bullet = re.match(r'^(\s*)[-*+]\s', text)
        numbered = re.match(r'^(\s*)(\d+)\.\s', text)
        task = re.match(r'^(\s*)(?:[-*+]|\d+\.)\s\[( |x|X)\]\s', text)
        if task:
            indent = ' ' * (len(task.group(1).replace('\t', '  ')) // 2 * 2)
            out.append(f"{lead}{indent}{task_box(task.group(2))} {self.base}")
            rest = text[task.end():]
            self.skip_ws = True
        elif bullet or numbered:
            match = bullet or numbered
            indent = ' ' * (len(match.group(1).replace('\t', '  ')) // 2 * 2)
            marker = ui_symbol('•', '-') if bullet else numbered.group(2) + '.'
            out.append(f"{lead}{indent}{COLOR_LYRA}{marker}{RESET} {self.base}")
            rest = text[match.end():]
            self.skip_ws = True
            self.item_start = True
        elif text.startswith('> '):
            quote = re.match(r'^((?:>[ \t]?)+)', text)
            self.base = COLOR_DIM + ITALIC
            out.append(f"{lead}{COLOR_DIM}{(ui_symbol('▎', '|') + ' ') * quote.group(1).count('>')}{self.base}")
            rest = text[quote.end():]
            self.skip_ws = True
        else:
            out.append(f"{lead}{self.base}")
        self.col = self.indent = str_width(''.join(out[-1:]))
        for char in rest:
            self._inline(char, out)

    def _style(self):
        style = self.base
        if self.bold:
            style += BOLD
        if self.italic:
            style += ITALIC
        if self.strike:
            style += STRIKE
        if self.code:
            style += INLINE_CODE_BG + COLOR_ACCENT
        return style

    def _restyle(self, out):
        self._code(RESET + self._style(), out)

    # -- word wrapping --------------------------------------------------
    def _limit(self):
        return max(20, self.width_fn() - 1)     # never touch the last column: terminals wrap there

    def _code(self, codes, out):
        """Zero-width output (colours); travels with the word so a wrap cannot separate them."""
        if not self.wrap:
            out.append(codes)
            return
        if not self.word:
            self.word_style = self._style()
        self.word.append(codes)

    def _text(self, char, out):
        if not self.wrap:
            out.append(char)
            return
        if char in ' \t':
            self._flush_word(out)
            if self.col > self.indent:
                self.spaces += 1
            return
        self.item_start = False
        if not self.word:
            self.word_style = self._style()
        self.word.append(char)
        self.word_w += char_width(char)
        if self.word_w >= self._limit() - self.indent:       # one word longer than a whole line: cut it
            self._flush_word(out, force=True)

    def _flush_word(self, out, force=False):
        if not self.word:
            return
        if self.col > self.indent and self.col + self.spaces + self.word_w > self._limit():
            out.append(RESET + '\n' + ' ' * self.indent + self.word_style)      # wrap: the gap is dropped
            self.col = self.indent
        elif self.spaces:
            out.append(' ' * self.spaces)
            self.col += self.spaces
        self.spaces = 0
        out.append(''.join(self.word))
        self.col += self.word_w
        self.word, self.word_w = [], 0
        if force:
            out.append(RESET + '\n' + ' ' * self.indent + self._style())
            self.col = self.indent

    def _inline(self, char, out):
        if self.skip_ws:
            if char in ' \t':
                return
            self.skip_ws = False
        if self.link is not None and self._link_char(char, out):
            return
        if self.star:
            self.star = False
            if char == '*':
                self.bold = not self.bold
                self._restyle(out)
                return
            if self.italic:
                self.italic = False
                self._restyle(out)
            elif char not in ' \t':
                self.italic = True
                self._restyle(out)
            else:
                self._text('*', out)
        if self.tilde:
            self.tilde = False
            if char == '~':
                self.strike = not self.strike
                self._restyle(out)
                return
            self._text('~', out)
        if self.bang:
            self.bang = False
            if char == '[':
                self.link = {'stage': 'text', 'text': '', 'url': '', 'image': True}
                return
            self._text('!', out)
        if not self.code:
            if char == '*':
                self.star = True
                return
            if char == '~':
                self.tilde = True
                return
            if char == '!':
                self.bang = True
                return
            if char == '[':
                self.link = {'stage': 'text', 'text': '', 'url': '', 'image': False}
                return
        if char == '`':
            self.code = not self.code
            if self.code:
                self._restyle(out)
                self._text(' ', out)
            else:
                self._text(' ', out)
                self._restyle(out)
            return
        self._text(char, out)

    # -- links, images and task boxes ------------------------------------
    def _flush_pending(self, out):
        """End of line: whatever was waiting for a partner character is plain text after all."""
        if self.link is not None:
            self._abort_link(out, closed=self.link['stage'] != 'text', with_url=self.link['stage'] == 'url')
        if self.star:
            self._text('*', out)
        if self.tilde:
            self._text('~', out)
        if self.bang:
            self._text('!', out)

    def _link_char(self, char, out):
        """Feed one char to the link candidate. True when consumed; False when the candidate was dropped."""
        link = self.link
        if link['stage'] == 'text':
            if char == ']':
                link['stage'] = 'wait'
            else:
                link['text'] += char
                if len(link['text']) > 200:
                    self._abort_link(out, closed=False)
            return True
        if link['stage'] == 'wait':
            if char == '(':
                link['stage'] = 'url'
                return True
            if self.item_start and link['text'] in (' ', 'x', 'X') and char in ' \t' and not link['image']:
                self.link = None                                  # "- [ ] task": a checkbox, not a link
                self._checkbox(link['text'], out)
                return False
            self._abort_link(out, closed=True)
            return False
        if char == ')':
            self._finish_link(out)
        else:
            link['url'] += char
            if len(link['url']) > 600:
                self._abort_link(out, closed=True, with_url=True)
        return True

    def _checkbox(self, mark, out):
        done = mark in ('x', 'X')
        self._code(COLOR_DIM if done else COLOR_LYRA, out)
        for ch in (ui_symbol('☒', '[x]') if done else ui_symbol('☐', '[ ]')):
            self._text(ch, out)
        self._restyle(out)

    def _abort_link(self, out, closed, with_url=False):
        link, self.link = self.link, None
        literal = ('!' if link['image'] else '') + '[' + link['text'] + (']' if closed else '')
        if with_url:
            literal += '(' + link['url']
        for ch in literal:
            self._text(ch, out)

    def _finish_link(self, out):
        link, self.link = self.link, None
        url = link['url'].strip()
        if url.startswith('<') and '>' in url:
            url = url[1:url.index('>')]
        url = url.split()[0] if url.split() else ''
        if not url:
            for ch in ('!' if link['image'] else '') + '[' + link['text'] + ']()':
                self._text(ch, out)
            return
        clean = re.sub(r'\*\*|`|__', '', link['text']).strip()
        label = (f'[gambar: {clean}]' if clean else '[gambar]') if link['image'] else (clean or url)
        self._code(UNDERLINE + COLOR_ACCENT, out)
        for ch in label:
            self._text(ch, out)
        self._restyle(out)
        if label != url:
            self._text(' ', out)
            self._code(COLOR_DIM, out)
            for ch in f'({url})':
                self._text(ch, out)
            self._restyle(out)
