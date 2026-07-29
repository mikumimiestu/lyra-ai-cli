import sys
import os

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

# ─── ANSI Helpers ─────────────────────────────────────────────────────────────
def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_ansi(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

def rgb_bg(r, g, b):
    return f"\033[48;2;{r};{g};{b}m"

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

# ─── Adaptive Colors ─────────────────────────────────────────────────────────
# Pada dark theme pakai warna terang, pada light theme pakai warna lebih gelap
if IS_DARK:
    WHITE       = "\033[97m"          # bright white
    GREEN       = rgb_to_ansi(*hex_to_rgb("#4ADE80"))
    RED         = rgb_to_ansi(*hex_to_rgb("#F87171"))
    YELLOW      = rgb_to_ansi(*hex_to_rgb("#FDE68A"))
    CYAN        = rgb_to_ansi(*hex_to_rgb("#67E8F9"))
    COLOR_USER  = rgb_to_ansi(*hex_to_rgb("#60A5FA"))   # soft blue
    COLOR_LYRA  = rgb_to_ansi(*hex_to_rgb("#E879F9"))   # vivid pink-purple
    COLOR_BORDER= rgb_to_ansi(*hex_to_rgb("#A78BFA"))   # lavender
    COLOR_DIM   = rgb_to_ansi(*hex_to_rgb("#94A3B8"))   # slate-400
    COLOR_TITLE = rgb_to_ansi(*hex_to_rgb("#F8FAFC"))   # near-white
    COLOR_ACCENT= rgb_to_ansi(*hex_to_rgb("#34D399"))   # emerald
else:
    # Light background — pakai warna gelap supaya kontras
    WHITE       = "\033[30m"          # black
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

# ─── Logo ─────────────────────────────────────────────────────────────────────
LOGO_LINES = [
    "   ██╗  ██╗   ██╗██████╗  █████╗     ██████╗██╗     ██╗",
    "   ██║  ╚██╗ ██╔╝██╔══██╗██╔══██╗   ██╔════╝██║     ██║",
    "   ██║   ╚████╔╝ ██████╔╝███████║   ██║     ██║     ██║",
    "   ██║    ╚██╔╝  ██╔══██╗██╔══██║   ██║     ██║     ██║",
    "   ███████╗██║   ██║  ██║██║  ██║   ╚██████╗███████╗██║",
    "   ╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝    ╚═════╝╚══════╝╚═╝",
]

def print_logo():
    max_y = len(LOGO_LINES) - 1
    max_x = max(len(line) for line in LOGO_LINES) - 1

    scores = []
    for y, line in enumerate(LOGO_LINES):
        for x, char in enumerate(line):
            if char not in (" ", "╗", "╔", "╝", "╚"):
                score = x * 1.2 + (max_y - y) * 1.0
                scores.append(score)
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 1

    print()
    for y, line in enumerate(LOGO_LINES):
        colored = ""
        for x, char in enumerate(line):
            if char == " ":
                colored += " "
            else:
                score = x * 1.2 + (max_y - y) * 1.0
                t = (score - min_score) / (max_score - min_score) if max_score > min_score else 0.5
                r, g, b = get_gradient_color(t)
                colored += rgb_to_ansi(r, g, b) + BOLD + char
        print(colored + RESET)
    print()


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


# ─── Permission Box UI ────────────────────────────────────────────────────────
def render_permission_box(title, details):
    """Render box konfirmasi izin eksekusi yang rapi dan presisi."""
    w = min(get_terminal_width() - 8, 76)
    B, T, A, Y, R, D = COLOR_BORDER, COLOR_TITLE, COLOR_ACCENT, YELLOW, RESET, COLOR_DIM

    title_str = f" 🛡️  {BOLD}{Y}{title}{R} "
    pad_title = max(0, w - 2 - str_width(title_str))
    
    print(f"\n  {B}╭──{title_str}{B}{'─' * pad_title}╮{R}")
    for k, v in details.items():
        k_str = f"{D}{k:<10}: {R}"
        v_str = f"{BOLD}{WHITE}{v}{R}"
        vis_len = str_width(k_str + v_str)
        pad = max(0, w - 4 - vis_len)
        print(f"  {B}│{R}  {k_str}{v_str}{' ' * pad}  {B}│{R}")
    print(f"  {B}╰{'─' * w}╯{R}")


# ─── Markdown Renderer & Code Highlighting ────────────────────────────────────
import re

CODE_BG = rgb_bg(30, 41, 59) if IS_DARK else rgb_bg(241, 245, 249)
INLINE_CODE_BG = rgb_bg(39, 39, 42) if IS_DARK else rgb_bg(228, 228, 231)

KEYWORDS = r'\b(def|class|import|from|return|if|else|elif|for|while|try|except|const|let|var|function|async|await|export|default|require|echo|public|private|protected|fn|struct|enum|interface|type|nil|None|True|False|null|true|false)\b'

def highlight_syntax(code_line, lang=""):
    """Syntax highlighting sederhana menggunakan ANSI."""
    if not code_line:
        return ""
    
    # Comments
    if code_line.strip().startswith(("#", "//", "/*", "*")):
        return f"{COLOR_DIM}{ITALIC}{code_line}{RESET}"

    line = code_line
    # Highlight strings
    line = re.sub(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)', rf"{GREEN}\1{RESET}", line)
    # Highlight keywords
    line = re.sub(KEYWORDS, rf"{CYAN}{BOLD}\1{RESET}", line)
    # Highlight numbers
    line = re.sub(r'\b(\d+)\b', rf"{YELLOW}\1{RESET}", line)
    return line


def format_inline_markdown(text):
    """Format bold, italic, dan inline code dalam teks."""
    if not text:
        return ""
    
    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', rf"{INLINE_CODE_BG}{COLOR_ACCENT} \1 {RESET}", text)
    # Bold: **bold**
    text = re.sub(r'\*\*([^*]+)\*\*', rf"{BOLD}{WHITE}\1{RESET}", text)
    # Italic: *italic* or _italic_
    text = re.sub(r'\*([^*]+)\*', rf"{ITALIC}\1{RESET}", text)
    text = re.sub(r'_([^_]+)_', rf"{ITALIC}\1{RESET}", text)
    
    return text


def format_markdown_line(line, state):
    """Format baris tunggal Markdown untuk terminal."""
    stripped = line.strip()

    # Code block toggle
    if stripped.startswith("```"):
        if not state['in_code']:
            state['in_code'] = True
            lang = stripped[3:].strip()
            state['lang'] = lang
            lang_label = f" [{lang.upper()}]" if lang else ""
            w = min(get_terminal_width() - 8, 72)
            top_border = f"{COLOR_BORDER}┌── Code{lang_label} {'─' * max(0, w - str_width(lang_label) - 9)}┐{RESET}"
            return top_border, state
        else:
            state['in_code'] = False
            state['lang'] = ""
            w = min(get_terminal_width() - 8, 72)
            bot_border = f"{COLOR_BORDER}└{'─' * w}┘{RESET}"
            return bot_border, state

    if state['in_code']:
        highlighted = highlight_syntax(line, state['lang'])
        return f"{COLOR_BORDER}│{RESET} {highlighted}", state

    # Headers
    if line.startswith("# "):
        header = line[2:].strip()
        return f"\n{BOLD}{COLOR_LYRA}✦ {header.upper()}{RESET}\n{COLOR_BORDER}{'─' * len(header)}{RESET}", state
    elif line.startswith("## "):
        header = line[3:].strip()
        return f"\n{BOLD}{COLOR_TITLE}# {header}{RESET}", state
    elif line.startswith("### "):
        header = line[4:].strip()
        return f"{BOLD}{COLOR_ACCENT}▶ {header}{RESET}", state

    # Lists
    if re.match(r'^\s*[-*+]\s+', line):
        content = re.sub(r'^\s*[-*+]\s+', '', line)
        formatted = format_inline_markdown(content)
        return f"  {COLOR_LYRA}•{RESET} {formatted}", state
    elif re.match(r'^\s*\d+\.\s+', line):
        match = re.match(r'^\s*(\d+)\.\s+(.*)', line)
        if match:
            num, content = match.group(1), match.group(2)
            formatted = format_inline_markdown(content)
            return f"  {COLOR_USER}{num}.{RESET} {formatted}", state

    # Blockquotes
    if line.startswith("> "):
        content = format_inline_markdown(line[2:])
        return f"{COLOR_DIM}│ {ITALIC}{content}{RESET}", state

    # Horizontal Rule
    if stripped in ("---", "***", "___"):
        w = min(get_terminal_width() - 8, 72)
        return f"{COLOR_BORDER}{'─' * w}{RESET}", state

    # Regular line
    formatted = format_inline_markdown(line)
    return f"{WHITE}{formatted}{RESET}", state


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


# ─── Chat Bubble UI Helpers ───────────────────────────────────────────────────
def render_ai_bubble_top():
    """Render bagian atas card AI Lyra secara presisi."""
    w = min(get_terminal_width() - 8, 76)
    B, L, R = COLOR_BORDER, COLOR_LYRA, RESET
    clean_title = " ✦ Lyra "
    pad_title = max(0, w - 2 - str_width(clean_title))
    
    print(f"\n  {B}╭──{L}{BOLD}{clean_title}{R}{B}{'─' * pad_title}╮{R}")


def render_ai_bubble_bottom():
    """Render bagian bawah card AI Lyra secara presisi."""
    w = min(get_terminal_width() - 8, 76)
    B, R = COLOR_BORDER, RESET
    print(f"  {B}╰{'─' * w}╯{R}\n")


def format_markdown_line_bubble(line, state, width=None):
    """
    Format baris Markdown dan bungkus teks (word wrap) agar 100% presisi terbingkai di dalam card AI.
    Returns: (list_of_formatted_rows, state)
    """
    if width is None:
        width = min(get_terminal_width() - 8, 76)
    
    content_w = width - 4  # 2 spasi kiri margin, 2 spasi kanan margin

    stripped = line.strip()

    # Handling Code block borders & inner lines
    if stripped.startswith("```"):
        formatted, state = format_markdown_line(line, state)
        vis_len = str_width(formatted)
        pad = max(0, content_w - vis_len)
        return [f"  {COLOR_BORDER}│{RESET}  {formatted}{' ' * pad}  {COLOR_BORDER}│{RESET}"], state

    if state['in_code']:
        formatted, state = format_markdown_line(line, state)
        vis_len = str_width(formatted)
        pad = max(0, content_w - vis_len)
        return [f"  {COLOR_BORDER}│{RESET}  {formatted}{' ' * pad}  {COLOR_BORDER}│{RESET}"], state

    # Format baris dengan markdown renderer terlebih dahulu
    formatted, state = format_markdown_line(line, state)

    # Cek apakah lebar tampilan melebihi content_w
    if str_width(formatted) > content_w and not line.startswith(("#", "```", "---")):
        wrapped = wrap_text_display_width(formatted, content_w)
        rows = []
        for w_line in wrapped:
            vis_len = str_width(w_line)
            pad = max(0, content_w - vis_len)
            rows.append(f"  {COLOR_BORDER}│{RESET}  {w_line}{' ' * pad}  {COLOR_BORDER}│{RESET}")
        return rows, state
    else:
        vis_len = str_width(formatted)
        pad = max(0, content_w - vis_len)
        return [f"  {COLOR_BORDER}│{RESET}  {formatted}{' ' * pad}  {COLOR_BORDER}│{RESET}"], state


# ─── Thinking Card UI Helpers ─────────────────────────────────────────────────
def render_thinking_top():
    """Render bagian atas card Thinking Process."""
    w = min(get_terminal_width() - 8, 76)
    D, R = COLOR_DIM, RESET
    clean_title = " 🧠 Thinking Process "
    pad_title = max(0, w - 2 - str_width(clean_title))
    
    print(f"\n  {D}╭──{BOLD}{COLOR_USER}{clean_title}{R}{D}{'─' * pad_title}╮{R}")


def render_thinking_bottom():
    """Render bagian bawah card Thinking Process."""
    w = min(get_terminal_width() - 8, 76)
    D, R = COLOR_DIM, RESET
    print(f"  {D}╰{'─' * w}╯{R}")


def format_thinking_line_bubble(line, width=None):
    """Format baris penalaran (thinking) dalam warna dim & italic."""
    if width is None:
        width = min(get_terminal_width() - 8, 76)
    content_w = width - 4
    plain_text = strip_ansi(line)
    if str_width(plain_text) > content_w:
        wrapped = wrap_text_display_width(plain_text, content_w)
        rows = []
        for wl in wrapped:
            vis_len = str_width(wl)
            pad = max(0, content_w - vis_len)
            rows.append(f"  {COLOR_DIM}│{RESET}  {COLOR_DIM}{ITALIC}{wl}{RESET}{' ' * pad}  {COLOR_DIM}│{RESET}")
        return rows
    else:
        vis_len = str_width(plain_text)
        pad = max(0, content_w - vis_len)
        return [f"  {COLOR_DIM}│{RESET}  {COLOR_DIM}{ITALIC}{plain_text}{RESET}{' ' * pad}  {COLOR_DIM}│{RESET}"]





