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
