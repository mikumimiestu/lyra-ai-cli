import sys
import os

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
                  'COLOR_USER', 'COLOR_LYRA', 'COLOR_BORDER', 'COLOR_DIM', 'COLOR_TITLE', 'COLOR_ACCENT'):
        globals()[_name] = ''

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
    # Keep the original identity; use a readable wordmark on narrow terminals.
    if get_terminal_width() < max(len(line) for line in LOGO_LINES) + 2:
        print(f"\n  {BOLD}{COLOR_LYRA}LYRA CLI{RESET}\n")
        return
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
# ─── Permission Box UI ────────────────────────────────────────────────────────
def render_permission_box(title, details):
    """Render konfirmasi izin eksekusi hanya dengan garis atas & bawah (tanpa garis samping)."""
    term_w = get_terminal_width()
    w = min(term_w - 8, 70)
    B, T, A, Y, R, D = COLOR_BORDER, COLOR_TITLE, COLOR_ACCENT, YELLOW, RESET, COLOR_DIM

    title_str = f" 🛡️  {BOLD}{Y}{title}{R} "
    pad_title = max(4, w - str_width(title_str) - 2)
    top_b = "─" * pad_title
    
    print(f"\n  {B}──{title_str}{B}{top_b}{R}")

    for k, v in details.items():
        v_str = str(v)
        if "\n" in v_str:
            print(f"    {D}{k:<10}:{R}")
            v_lines = v_str.split("\n")
            for sub_l in v_lines:
                if not sub_l.strip():
                    continue
                highlighted = highlight_syntax(sub_l)
                print(f"      {highlighted}")
        else:
            highlighted = highlight_syntax(v_str) if k.lower() in ("command", "script", "perintah") else f"{BOLD}{WHITE}{v_str}{R}"
            print(f"    {D}{k:<10}:{R} {highlighted}")

    print(f"  {B}{'─' * w}{R}")


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
            w = min(get_terminal_width() - 8, 70)
            top_border = f"  {COLOR_BORDER}── Code{lang_label} {'─' * max(4, w - str_width(lang_label) - 9)}{RESET}"
            return top_border, state
        else:
            state['in_code'] = False
            state['lang'] = ""
            w = min(get_terminal_width() - 8, 70)
            bot_border = f"  {COLOR_BORDER}{'─' * w}{RESET}"
            return bot_border, state

    if state['in_code']:
        highlighted = highlight_syntax(line, state['lang'])
        return f"    {highlighted}", state


    # Headers
    if line.startswith("# "):
        header = line[2:].strip()
        return f"\n  {BOLD}{COLOR_LYRA}✦ {header.upper()}{RESET}\n  {COLOR_BORDER}{'─' * max(10, len(header) + 4)}{RESET}", state
    elif line.startswith("## "):
        header = line[3:].strip()
        return f"\n  {BOLD}{COLOR_TITLE}# {header}{RESET}", state
    elif line.startswith("### "):
        header = line[4:].strip()
        return f"\n  {BOLD}{COLOR_ACCENT}▶ {header}{RESET}", state

    # Lists
    if re.match(r'^\s*[-*+]\s+', line):
        content = re.sub(r'^\s*[-*+]\s+', '', line)
        formatted = format_inline_markdown(content)
        return f"  {COLOR_LYRA}●{RESET} {formatted}", state
    elif re.match(r'^\s*\d+\.\s+', line):
        match = re.match(r'^\s*(\d+)\.\s+(.*)', line)
        if match:
            num, content = match.group(1), match.group(2)
            formatted = format_inline_markdown(content)
            return f"  {COLOR_USER}{num}.{RESET} {formatted}", state

    # Blockquotes
    if line.startswith("> "):
        content = format_inline_markdown(line[2:])
        return f"  {COLOR_DIM}│ {ITALIC}{content}{RESET}", state

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
    """A compact welcome with real model, version, and working directory."""
    from config import VERSION
    width = max(12, min(get_terminal_width() - 4, 88))
    reasoning = 'reasoning ' + reasoning_effort if supports_reasoning else 'tanpa reasoning'
    print(f"\n  {COLOR_LYRA}✦{RESET} {BOLD}{COLOR_TITLE}Lyra CLI{RESET}  {COLOR_DIM}v{VERSION}{RESET}\n")
    for text in (f'{model_name} · {reasoning}', short_path(active_cwd)):
        for line in wrap_text_display_width(text, width):
            print(f"  {COLOR_DIM}{line}{RESET}")
    print(f"\n  {COLOR_TITLE}Mau ngerjain apa hari ini?{RESET}")
    hint = 'Jelaskan tugasnya, atau ketik / untuk lihat perintah.'
    for line in wrap_text_display_width(hint, width):
        print(f"  {COLOR_DIM}{line}{RESET}")
    hint = ('Enter kirim · Alt+Enter baris baru · Ctrl+D keluar'
            if EDITOR_AVAILABLE and sys.stdin.isatty() else 'Enter kirim · /help bantuan · exit keluar')
    for line in wrap_text_display_width(hint, width):
        print(f"  {COLOR_DIM}{line}{RESET}")
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
COMMANDS = [
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
    ('/reset-key', 'Ganti API key'),
    ('/help', 'Lihat bantuan lengkap'),
]


def short_path(directory):
    home = os.path.expanduser('~')
    if directory == home:
        return '~'
    if directory.startswith(home + os.sep):
        return '~' + directory[len(home):]
    return directory


def toolbar_text(model, effort, directory, supports_reasoning=True):
    model = model.removeprefix('Lyra ') if hasattr(str, 'removeprefix') else model.replace('Lyra ', '', 1)
    reasoning = effort if supports_reasoning else 'tanpa reasoning'
    return '{} · {}  |  {}'.format(model, reasoning, short_path(directory))


try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import ANSI
    EDITOR_AVAILABLE = True
except ImportError:
    EDITOR_AVAILABLE = False


if EDITOR_AVAILABLE:
    class SlashCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith('/') or any(char.isspace() for char in text):
                return
            for command, description in COMMANDS:
                if command.startswith(text.lower()):
                    yield Completion(command, start_position=-len(text), display_meta=description)


class TerminalInput:
    def __init__(self, context, input_stream=None, output_stream=None):
        self.context = context
        self.session = None
        self._bindings = None
        # Pipes and dumb terminals keep the plain text input path.
        interactive = sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'
        if EDITOR_AVAILABLE and (interactive or input_stream is not None):
            bindings = KeyBindings()

            @bindings.add('escape', 'enter')
            @bindings.add('c-j')
            def newline(event):
                event.current_buffer.insert_text('\n')

            @bindings.add('tab')
            def complete_command(event):
                buffer = event.current_buffer
                if buffer.complete_state:
                    buffer.complete_next()
                    return
                matches = list(SlashCompleter().get_completions(buffer.document, None))
                if len(matches) == 1:
                    buffer.apply_completion(matches[0])
                elif matches:
                    buffer.start_completion(select_first=True)

            self._bindings = bindings
            self.session = PromptSession(
                history=InMemoryHistory(),
                completer=SlashCompleter(),
                complete_while_typing=True,
                key_bindings=bindings,
                bottom_toolbar=self._toolbar,
                prompt_continuation='    ',
                style=Style.from_dict({
                    'bottom-toolbar': 'noreverse',
                    'completion-menu.completion': 'bg:#292b30 #d6d7df',
                    'completion-menu.completion.current': 'bg:#514568 #ffffff',
                    'completion-menu.meta.completion': 'bg:#292b30 #a8a8b5',
                    'completion-menu.meta.completion.current': 'bg:#514568 #ffffff',
                }),
                input=input_stream,
                output=output_stream,
                reserve_space_for_menu=5,
            )

    def _toolbar(self):
        context = self.context()
        text = toolbar_text(**context)
        width = max(1, get_terminal_width() - 4)
        if len(text) > width:
            text = text[:max(0, width - 1)] + '…'
        return ANSI('  {}{}{}'.format(COLOR_DIM, text, RESET))

    def read(self):
        prompt = '  {}{}›{} '.format(BOLD, COLOR_LYRA, RESET)
        if self.session is None:
            return input(prompt)
        return self.session.prompt(
            ANSI(prompt),
            rprompt=ANSI('{} / perintah{}'.format(COLOR_DIM, RESET)),
        )


def tool_activity(name, arguments):
    """Describe only paths/commands useful to the user, never file contents."""
    labels = {
        'list_directory': ('Lihat folder', 'path'),
        'read_file': ('Baca', 'filepath'),
        'write_file': ('Tulis file', 'filepath'),
        'create_directory': ('Buat folder', 'dirpath'),
        'execute_command': ('Jalankan', 'command'),
        'init_project': ('Buat project', 'project_name'),
        'save_memory': ('Simpan memori', None),
        'read_memory': ('Baca memori', None),
        'get_system_time': ('Lihat waktu komputer', None),
        'set_reminder': ('Buat pengingat', None),
        'list_reminders': ('Lihat pengingat', None),
        'cancel_reminder': ('Batalkan pengingat', None),
    }
    label, key = labels.get(name, ('Tool ' + name, None))
    value = str(arguments.get(key, '')) if key else ''
    # Keep paths and multiline scripts from injecting control sequences in labels.
    value = ''.join(char if char.isprintable() else ' ' for char in value)
    return '{}{}{}'.format(label, ' · ' if value else '', value[:90] + ('…' if len(value) > 90 else ''))
