import sys

# Helper functions for terminal coloring (ANSI True Color)
def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_ansi(r, g, b):
    return f"\033[38;2;{r};{g};{b}m"

def interpolate_rgb(color1, color2, t):
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return r, g, b

def get_gradient_color(t):
    # Gradient: Blue (#33A0FF) -> Purple (#9C4FFF) -> Pink/Magenta (#FF5EEF)
    c1 = hex_to_rgb("#33A0FF")
    c2 = hex_to_rgb("#9C4FFF")
    c3 = hex_to_rgb("#FF5EEF")
    
    if t < 0.5:
        return interpolate_rgb(c1, c2, t * 2.0)
    else:
        return interpolate_rgb(c2, c3, (t - 0.5) * 2.0)

# Colors and formatting constants
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[90m"
WHITE = "\033[97m"
GREEN = "\033[32m"
RED = "\033[31m"

COLOR_USER = rgb_to_ansi(*hex_to_rgb("#33A0FF"))
COLOR_LYRA = rgb_to_ansi(*hex_to_rgb("#FF5EEF"))
COLOR_BORDER = rgb_to_ansi(*hex_to_rgb("#9C4FFF"))

LOGO_LINES = [
    "                 ▄██████▄                              ✦",
    "               ▄████▀▀████▄",
    "             ▄████▀    ▀████▄",
    "           ▄████▀        ▀████▄",
    "          ████▀            ▀▀▀▀▀",
    "         ████▀         ▄██████████▄",
    "        ▀▀▀▀         ▄████▀▀    ▀████▄",
    "                   ▄████▀          ████",
    "                 ▄████▀          ▄████▀",
    "               ▄████▀          ▄████▀",
    "              ▀██████████████████▀"
]

def print_logo():
    max_y = len(LOGO_LINES) - 1
    max_x = max(len(line) for line in LOGO_LINES) - 1
    
    # Calculate min/max scores for normalization
    min_score = float('inf')
    max_score = float('-inf')
    for y, line in enumerate(LOGO_LINES):
        for x, char in enumerate(line):
            if char != " ":
                score = x * 1.2 + (max_y - y) * 1.0
                if score < min_score:
                    min_score = score
                if score > max_score:
                    max_score = score

    # Print with gradient
    print()
    for y, line in enumerate(LOGO_LINES):
        colored_line = ""
        for x, char in enumerate(line):
            if char == " ":
                colored_line += " "
            elif char == "✦":
                r, g, b = hex_to_rgb("#FFA8FF")
                colored_line += rgb_to_ansi(r, g, b) + char
            else:
                score = x * 1.2 + (max_y - y) * 1.0
                t = (score - min_score) / (max_score - min_score) if max_score > min_score else 0.5
                r, g, b = get_gradient_color(t)
                colored_line += rgb_to_ansi(r, g, b) + char
        print(colored_line + RESET)
    print()
