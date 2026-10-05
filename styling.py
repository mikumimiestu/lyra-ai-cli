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

def render_header(model_name, reasoning_effort, active_cwd):
    """Render top header ala Claude CLI dengan daftar perintah utama."""
    home_dir = os.path.expanduser("~")
    cwd_short = active_cwd.replace(home_dir, "~")
    
    reasoning_label = "penalaran cepat" if reasoning_effort == "low" else "penalaran sedang"
    
    header_title = f"{BOLD}{COLOR_LYRA}Lyra CLI v2.1.1{RESET}"
    header_sub   = f"{COLOR_DIM}Model    : {RESET}{BOLD}{WHITE}{model_name}{RESET} {COLOR_DIM}({reasoning_label}) · AstByte AI{RESET}"
    header_path  = f"{COLOR_DIM}Direktori: {RESET}{COLOR_TITLE}{cwd_short}{RESET}"
    
    print(f"\n  {header_title}")
    print(f"  {header_sub}")
    print(f"  {header_path}\n")

    print(f"  {BOLD}{COLOR_ACCENT}Perintah Utama:{RESET}")
    print(f"    {BOLD}{YELLOW}/model{RESET}      {COLOR_DIM}- Buka pilihan model AI (Orpheus 6, Eurydice 6, Nebula 4, Luma 5.5){RESET}")
    print(f"    {BOLD}{YELLOW}/reasoning{RESET}  {COLOR_DIM}- Atur tingkat penalaran (cepat / sedang){RESET}")
    print(f"    {BOLD}{YELLOW}/update{RESET}     {COLOR_DIM}- Cek & perbarui Lyra CLI ke versi terbaru otomatis{RESET}")
    print(f"    {BOLD}{YELLOW}/project{RESET}    {COLOR_DIM}- Wizard pembuat project baru (React, Next.js, Laravel, FastAPI...){RESET}")
    print(f"    {BOLD}{YELLOW}/clear{RESET}      {COLOR_DIM}- Bersihkan riwayat chat{RESET}")
    print(f"    {BOLD}{YELLOW}/help{RESET}       {COLOR_DIM}- Lihat semua perintah yang tersedia{RESET}")
    print(f"    {BOLD}{YELLOW}exit{RESET}        {COLOR_DIM}- Keluar dari aplikasi{RESET}\n")



def render_full_divider(color=COLOR_BORDER):
    """Render garis pembatas panjang dari ujung ke ujung."""
    w = max(40, get_terminal_width() - 4)
    print(f"  {color}{'─' * w}{RESET}")


def render_footer_bar():
    """Render bottom toolbar ala Claude Code CLI."""
    w = max(40, get_terminal_width() - 4)
    sep = f"{COLOR_BORDER}{'─' * w}{RESET}"
    status_text = f"{COLOR_DIM}⏸ manual mode on · /model pilih model · /reasoning tingkat penalaran · /help bantuan{RESET}"
    print(f"\n  {sep}")
    print(f"  {status_text}\n")


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






