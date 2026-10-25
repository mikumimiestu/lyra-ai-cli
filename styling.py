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
UNDERLINE = "\033[4m"

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
                  'UNDERLINE', 'COLOR_USER', 'COLOR_LYRA', 'COLOR_BORDER', 'COLOR_DIM', 'COLOR_TITLE', 'COLOR_ACCENT'):
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
    if not unicode_terminal() or get_terminal_width() < max(len(line) for line in LOGO_LINES) + 2:
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


def render_permission_box(title, details):
    """Rounded confirmation dialog. Commands are shown in full so nothing is approved unseen."""
    width = box_width(88)
    room = width - 4
    key_w = max((len(str(k)) for k in details), default=8) + 2
    body = []
    for key, value in details.items():
        is_code = str(key).lower() in ('command', 'script', 'perintah')
        chunks = [part for part in str(value).split('\n') if part.strip()] or ['']
        for n, chunk in enumerate(chunks):
            for m, piece in enumerate(wrap_text_display_width(chunk, max(8, room - key_w))):
                label = f'{COLOR_DIM}{str(key):<{key_w}}{RESET}' if n == 0 and m == 0 else ' ' * key_w
                shown = highlight_syntax(piece) if is_code else f'{BOLD}{piece}{RESET}'
                body.append(label + shown)
    caution = ui_symbol('⚠', '!')
    print()
    for line in render_box(body, width, color=YELLOW, title=f'{BOLD}{YELLOW}{caution} {title}{RESET}'):
        print('  ' + line)


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
            return f"  {COLOR_BORDER}{ui_symbol('╭─', '+-')}{RESET} {COLOR_DIM}{lang or 'code'}{RESET}", state
        state['in_code'] = False
        state['lang'] = ""
        return f"  {COLOR_BORDER}{ui_symbol('╰─', '+-')}{RESET}", state

    if state['in_code']:
        highlighted = highlight_syntax(line, state['lang'])
        return f"  {COLOR_BORDER}{ui_symbol('│', '|')}{RESET} {highlighted}", state

    # Headers
    if line.startswith("# "):
        return f"\n  {BOLD}{UNDERLINE}{COLOR_TITLE}{line[2:].strip()}{RESET}", state
    elif line.startswith("## "):
        return f"\n  {BOLD}{COLOR_TITLE}{line[3:].strip()}{RESET}", state
    elif line.startswith("### "):
        return f"\n  {BOLD}{COLOR_LYRA}{line[4:].strip()}{RESET}", state

    # Lists
    bullet = re.match(r'^(\s*)[-*+]\s+(.*)', line)
    if bullet:
        indent = ' ' * (len(bullet.group(1).replace('\t', '  ')) // 2 * 2)
        return f"  {indent}{COLOR_LYRA}{ui_symbol('•', '-')}{RESET} {format_inline_markdown(bullet.group(2))}", state
    numbered = re.match(r'^(\s*)(\d+)\.\s+(.*)', line)
    if numbered:
        indent = ' ' * (len(numbered.group(1).replace('\t', '  ')) // 2 * 2)
        return f"  {indent}{COLOR_LYRA}{numbered.group(2)}.{RESET} {format_inline_markdown(numbered.group(3))}", state

    # Blockquotes
    if line.startswith("> "):
        content = format_inline_markdown(line[2:])
        return f"  {COLOR_DIM}{ui_symbol('▎', '|')} {ITALIC}{content}{RESET}", state

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
    """Logo stays above; a rounded welcome card (Claude/Codex style) carries the session context."""
    from config import VERSION
    width = box_width(72, 28)
    room = width - 4
    reasoning = 'reasoning ' + reasoning_effort if supports_reasoning else 'tanpa reasoning'
    sep = ui_symbol('·', '/')
    body = [
        f'{COLOR_TITLE}Mau ngerjain apa hari ini?{RESET}',
        f'{COLOR_DIM}{fit_console_text(model_name + " " + sep + " " + reasoning, room)}{RESET}',
        f'{COLOR_DIM}{fit_console_text(short_path(active_cwd), room)}{RESET}',
    ]
    title = f'{BOLD}{COLOR_LYRA}{ui_symbol("✦", "*")} Lyra CLI{RESET} {COLOR_DIM}v{VERSION}{RESET}'
    print()
    for line in render_box(body, width, color=COLOR_BORDER, title=title):
        print('  ' + line)
    tips = f'/ perintah {sep} @ file {sep} Alt+Enter baris baru {sep} /help'
    print(f"  {COLOR_DIM}{fit_console_text(tips, width)}{RESET}")
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


def toolbar_text(model, effort, directory, supports_reasoning=True, branch=None, context_pct=None):
    model = model.removeprefix('Lyra ') if hasattr(str, 'removeprefix') else model.replace('Lyra ', '', 1)
    reasoning = effort if supports_reasoning else 'tanpa reasoning'
    separator = ui_symbol('·', '/')
    location = short_path(directory) + (' / ' + branch if branch else '')
    context = ' {} ctx ~{}%'.format(separator, context_pct) if context_pct is not None else ''
    return '{} {} {}{}  |  {}'.format(model, separator, reasoning, context, location)


try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.layout.containers import HSplit, Window, to_container, ConditionalContainer, DynamicContainer
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.data_structures import Size
    from prompt_toolkit.filters import Condition
    EDITOR_AVAILABLE = True
except ImportError:
    EDITOR_AVAILABLE = False


if EDITOR_AVAILABLE:
    class ConsoleSession(PromptSession):
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
            return layout

    class SlashCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith('/') or any(char.isspace() for char in text):
                return
            for command, description in COMMANDS:
                if command.startswith(text.lower()):
                    yield Completion(command, start_position=-len(text), display_meta=description)


class TerminalInput:
    def __init__(self, context, input_stream=None, output_stream=None, on_cycle_mode=None):
        self.context = context
        self.on_cycle_mode = on_cycle_mode
        self.session = None
        self._bindings = None
        self.branch = None
        self.notice = None   # right-aligned footer message, e.g. an available update
        # Pipes and dumb terminals keep the plain text input path.
        interactive = sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('TERM') != 'dumb'
        if EDITOR_AVAILABLE and (interactive or input_stream is not None):
            bindings = KeyBindings()

            @bindings.add('escape', 'enter')
            @bindings.add('c-j')
            def newline(event):
                event.current_buffer.insert_text('\n')

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
            )

    def _toolbar(self):
        context = dict(self.context())
        approval = context.pop('approval', 'ask')
        text = toolbar_text(**context, branch=self.branch)
        columns = self.session.app.output.get_size().columns if self.session else get_terminal_width()
        width = max(1, columns - 4)
        sep = ui_symbol('·', '/')
        pct = context.get('context_pct')
        color = RED if pct is not None and pct >= 95 else YELLOW if pct is not None and pct >= 80 else COLOR_DIM
        mode_text, mode_color = approval_footer(approval)
        rest = f' {sep} / perintah {sep} @ file {sep} Esc batal {sep} Alt+Enter baris baru'
        if str_width(mode_text + rest) <= width:
            plain = mode_text + rest
            second = f'{mode_color}{mode_text}{RESET}{COLOR_DIM}{rest}'
        else:
            plain = fit_console_text(mode_text, width)
            second = f'{mode_color}{plain}'
        if self.notice:
            notice = fit_console_text(self.notice, max(1, width - 2))
            tone = GREEN if notice.startswith(ui_symbol('✔', 'OK')) else YELLOW
            gap = width - str_width(plain) - str_width(notice)
            second += (' ' * gap if gap >= 3 else '') + f'{RESET}{tone}{notice}'
        return ANSI('  {}{}{}\n  {}{}'.format(color, fit_console_text(text, width), RESET, second, RESET))

    def read(self):
        marker = ui_symbol('›', '>')
        prompt = ' {}{}{}{} '.format(BOLD, COLOR_LYRA, marker, RESET)
        self.branch = workspace_branch(self.context().get('directory', os.getcwd()))
        if self.session is None:
            border = '+' + '-' * max(3, min(get_terminal_width() - 5, 84))
            print('  ' + border + ' pesan')
            try:
                return input(prompt)
            finally:
                print('  ' + border)
        return self.session.prompt(ANSI(prompt))


NOT_INTERACTIVE = object()   # returned by choose() when there is no real terminal to draw a menu on


def choose(title, options, selected=0, subtitle='', input_stream=None, output_stream=None, force=False):
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

    def render():
        room = max(20, get_terminal_width() - 4)
        rows = [f'  {BOLD}{COLOR_LYRA}{title}{RESET}']
        if subtitle:
            rows.append(f'  {COLOR_DIM}{fit_console_text(subtitle, room)}{RESET}')
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
    # Keep paths and multiline scripts from injecting control sequences in labels.
    value = ''.join(char if char.isprintable() else ' ' for char in value)
    return label, value[:90] + ('…' if len(value) > 90 else '')


def tool_activity(name, arguments):
    label, value = tool_call_parts(name, arguments)
    return '{}{}{}'.format(label, ' ' + ui_symbol('·', '/') + ' ' if value else '', value)


# ─── Console capabilities and file context ───────────────────────────────────
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
    if name in ('list_directory', 'read_file'):
        return 'Eksplorasi'
    if name in ('write_file', 'create_directory', 'init_project'):
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


READ_ONLY_TOOLS = ('list_directory', 'read_file', 'read_memory', 'get_system_time', 'list_reminders')
_COLLAPSE_LABELS = {'file': 'membaca {} file', 'folder': 'melihat {} folder', 'konteks': 'memeriksa {} konteks'}


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
        kind = 'file' if name == 'read_file' else 'folder' if name == 'list_directory' else 'konteks'
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

    Paragraph, list and quote text is written as it arrives, token by token, with `**bold**`,
    `*italic*` and `code` styled on the fly. Headings, rules, code blocks and tables need the whole
    line to format correctly, so those are written once their line is complete.
    """
    _MARKER_CHARS = frozenset('#`-*+_>|0123456789. \t')

    def __init__(self, write, format_line=None, render_table=None):
        self.write = write
        self.format_line = format_line or format_markdown_line
        self.render_table = render_table or render_markdown_table
        self.state = {'in_code': False, 'lang': ''}
        self.line = ''
        self.mode = None            # None (undecided) | 'block' | 'inline'
        self.table = []
        self.started = False
        self.lead_done = False
        self.bold = self.italic = self.code = self.star = False
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
        """Interrupted mid-line: only make sure no style leaks into the next prompt."""
        if self.mode == 'inline':
            self.write(RESET)

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
        if (re.match(r'^\s*\|', text) or re.match(r'^\s*```', text) or re.match(r'^#{1,3} ', text)
                or re.match(r'^\s*([-*_])\1\1', text)):
            return 'block'
        if not final and len(text) < 4 and all(char in self._MARKER_CHARS for char in text):
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
            if self.star:
                out.append('*')
            out.append(RESET + '\n')
        self.line = ''
        self.mode = None
        self.bold = self.italic = self.code = self.star = False

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
        if bullet or numbered:
            match = bullet or numbered
            indent = ' ' * (len(match.group(1).replace('\t', '  ')) // 2 * 2)
            marker = ui_symbol('•', '-') if bullet else numbered.group(2) + '.'
            out.append(f"{lead}{indent}{COLOR_LYRA}{marker}{RESET} {self.base}")
            rest = text[match.end():]
            self.skip_ws = True
        elif text.startswith('> '):
            self.base = COLOR_DIM + ITALIC
            out.append(f"{lead}{COLOR_DIM}{ui_symbol('▎', '|')} {self.base}")
            rest = text[2:]
            self.skip_ws = True
        else:
            out.append(f"{lead}{self.base}")
        for char in rest:
            self._inline(char, out)

    def _style(self):
        style = self.base
        if self.bold:
            style += BOLD
        if self.italic:
            style += ITALIC
        if self.code:
            style += INLINE_CODE_BG + COLOR_ACCENT
        return style

    def _restyle(self, out):
        out.append(RESET + self._style())

    def _inline(self, char, out):
        if self.skip_ws:
            if char in ' \t':
                return
            self.skip_ws = False
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
                out.append('*')
        if char == '*' and not self.code:
            self.star = True
            return
        if char == '`':
            self.code = not self.code
            if self.code:
                self._restyle(out)
                out.append(' ')
            else:
                out.append(' ')
                self._restyle(out)
            return
        out.append(char)
