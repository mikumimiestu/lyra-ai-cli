"""A tiny VT100 screen model, just enough to check what prompt_toolkit really leaves on a terminal.

It understands printable text, \\r \\n \\b, cursor movement (A B C D G H), erase (J K), autowrap on/off
and cursor-position requests (6n). Everything else (colours, modes, titles) is ignored. Lines that
scroll off the top are kept in `scrollback`, so tests can prove history is not lost.
"""
import re


class Screen:
    def __init__(self, rows=30, cols=100):
        self.rows, self.cols = rows, cols
        self.grid = [[' '] * cols for _ in range(rows)]
        self.row = self.col = 0
        self.autowrap = True
        self.scrollback = []
        self.replies = []          # responses owed to 6n cursor-position requests
        self._pending = ''

    # -- output ---------------------------------------------------------
    def lines(self):
        return [''.join(line).rstrip() for line in self.grid]

    def text(self):
        return '\n'.join(self.lines()).rstrip('\n')

    def history(self):
        return [''.join(line).rstrip() for line in self.scrollback] + self.lines()

    def find(self, needle):
        """Row index of the first screen line containing needle, or None."""
        for index, line in enumerate(self.lines()):
            if needle in line:
                return index
        return None

    # -- input ----------------------------------------------------------
    def feed(self, data):
        data = self._pending + data
        self._pending = ''
        i, n = 0, len(data)
        while i < n:
            ch = data[i]
            if ch == '\x1b':
                if i + 1 >= n:
                    self._pending = data[i:]
                    return
                nxt = data[i + 1]
                if nxt == '[':
                    match = re.compile(r'[0-?]*[ -/]*[@-~]').match(data, i + 2)
                    if not match:
                        self._pending = data[i:]
                        return
                    self._csi(match.group(0))
                    i = match.end()
                    continue
                if nxt == ']':                      # OSC ... BEL or ST
                    end = min([p for p in (data.find('\x07', i), data.find('\x1b\\', i)) if p >= 0], default=-1)
                    if end < 0:
                        self._pending = data[i:]
                        return
                    i = end + (1 if data[end] == '\x07' else 2)
                    continue
                i += 2
                continue
            if ch == '\r':
                self.col = 0
            elif ch == '\n':
                self._linefeed()
            elif ch == '\b':
                self.col = max(0, self.col - 1)
            elif ch == '\t':
                self.col = min(self.cols - 1, (self.col // 8 + 1) * 8)
            elif ch >= ' ' and ch != '\x7f':
                self._put(ch)
            i += 1

    # -- internals ------------------------------------------------------
    def _linefeed(self):
        if self.row == self.rows - 1:
            self.scrollback.append(self.grid.pop(0))
            self.grid.append([' '] * self.cols)
        else:
            self.row += 1

    def _put(self, ch):
        if self.col >= self.cols:
            if self.autowrap:
                self.col = 0
                self._linefeed()
            else:
                self.col = self.cols - 1
        self.grid[self.row][self.col] = ch
        self.col += 1

    def _csi(self, body):
        final, params = body[-1], body[:-1]
        private = params.startswith('?')
        numbers = [int(p) if p.isdigit() else 0 for p in params.lstrip('?').split(';')] if params.lstrip('?') else []
        first = numbers[0] if numbers and numbers[0] else 1
        if private:
            if final in 'hl' and 7 in numbers:
                self.autowrap = final == 'h'
            return
        if final == 'A':
            self.row = max(0, self.row - first)
        elif final == 'B':
            self.row = min(self.rows - 1, self.row + first)
        elif final == 'C':
            self.col = min(self.cols - 1, self.col + first)
        elif final == 'D':
            self.col = max(0, self.col - first)
        elif final == 'G':
            self.col = min(self.cols - 1, first - 1)
        elif final in 'Hf':
            self.row = min(self.rows - 1, (numbers[0] or 1) - 1) if numbers else 0
            self.col = min(self.cols - 1, (numbers[1] or 1) - 1) if len(numbers) > 1 else 0
        elif final == 'J':
            mode = numbers[0] if numbers else 0
            if mode == 0:
                self._erase_line(0)
                for r in range(self.row + 1, self.rows):
                    self.grid[r] = [' '] * self.cols
            elif mode in (2, 3):
                self.grid = [[' '] * self.cols for _ in range(self.rows)]
        elif final == 'K':
            self._erase_line(numbers[0] if numbers else 0)
        elif final == 'n' and numbers == [6]:
            self.replies.append(f'\x1b[{self.row + 1};{self.col + 1}R')

    def _erase_line(self, mode):
        line = self.grid[self.row]
        if mode == 0:
            for c in range(self.col, self.cols):
                line[c] = ' '
        elif mode == 1:
            for c in range(0, min(self.col + 1, self.cols)):
                line[c] = ' '
        else:
            self.grid[self.row] = [' '] * self.cols
