#!/usr/bin/env python3
"""
brainfuck_interpreter.py
========================
A correct, complete Brainfuck interpreter that works in two modes:

  CLI mode   : python3 brainfuck_interpreter.py some_file.bf
               Reads the .bf file, executes it, prints raw output — nothing else.

  Module mode: from brainfuck_interpreter import run_brainfuck
               run_brainfuck(code, input_str="") -> str

Supports all 8 standard Brainfuck operators: > < + - . , [ ]
  - Tape    : 30 000 cells, unsigned bytes (0-255, wrapping)
  - [ / ]   : bracket matching pre-computed into a jump table before
              execution — no naive O(n) rescanning per iteration.
  - ,       : reads one character from input_str (or NUL if exhausted).
  - Comments: any character that is not one of the 8 operators is ignored.
"""

import sys


# ---------------------------------------------------------------------------
# Core interpreter
# ---------------------------------------------------------------------------

def _build_jump_table(clean_code: list) -> dict:
    """
    Pre-compute matching [ ] pairs from a list of operator characters.
    Returns a dict mapping every '[' index to its matching ']' index
    and vice-versa.  Raises ValueError on unmatched brackets.
    """
    table = {}
    stack = []
    for pos, ch in enumerate(clean_code):
        if ch == '[':
            stack.append(pos)
        elif ch == ']':
            if not stack:
                raise ValueError(f"Unmatched ']' at operator-position {pos}")
            open_pos = stack.pop()
            table[open_pos] = pos
            table[pos] = open_pos
    if stack:
        raise ValueError(f"Unmatched '[' at operator-position(s): {stack}")
    return table


def run_brainfuck(code: str, input_str: str = "") -> str:
    """
    Execute a Brainfuck program and return everything it printed as a string.

    Parameters
    ----------
    code      : str  — Brainfuck source (comments / whitespace are ignored).
    input_str : str  — Characters fed to ',' instructions in order.
                       If exhausted, further ',' reads yield chr(0).

    Returns
    -------
    str — The concatenated output of all '.' instructions.
    """
    TAPE_SIZE = 30_000

    # Keep only the 8 recognised operators; everything else is a comment.
    operators = set('><+-.,[]')
    clean_code = [ch for ch in code if ch in operators]

    jump_table = _build_jump_table(clean_code)

    tape    = bytearray(TAPE_SIZE)  # unsigned-byte cells, all start at 0
    ptr     = 0                     # tape data pointer
    ip      = 0                     # instruction pointer
    output  = []                    # accumulated output characters
    inp_pos = 0                     # next character index in input_str

    while ip < len(clean_code):
        cmd = clean_code[ip]

        if cmd == '>':
            ptr = (ptr + 1) % TAPE_SIZE

        elif cmd == '<':
            ptr = (ptr - 1) % TAPE_SIZE

        elif cmd == '+':
            tape[ptr] = (tape[ptr] + 1) & 0xFF      # wraps 255 → 0

        elif cmd == '-':
            tape[ptr] = (tape[ptr] - 1) & 0xFF      # wraps 0 → 255

        elif cmd == '.':
            output.append(chr(tape[ptr]))

        elif cmd == ',':
            if inp_pos < len(input_str):
                tape[ptr] = ord(input_str[inp_pos]) & 0xFF
                inp_pos += 1
            else:
                tape[ptr] = 0   # EOF / no remaining input → NUL byte

        elif cmd == '[':
            if tape[ptr] == 0:
                ip = jump_table[ip]   # jump forward past matching ']'

        elif cmd == ']':
            if tape[ptr] != 0:
                ip = jump_table[ip]   # jump back to matching '['

        ip += 1

    return ''.join(output)


# ---------------------------------------------------------------------------
# CLI entry point — participants use:  python3 brainfuck_interpreter.py file.bf
# Output must be clean (just the program's output, nothing else).
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 brainfuck_interpreter.py <file.bf>", file=sys.stderr)
        sys.exit(1)

    bf_path = sys.argv[1]
    try:
        with open(bf_path, 'r', encoding='utf-8', errors='replace') as fh:
            code = fh.read()
    except FileNotFoundError:
        print(f"Error: file not found: {bf_path}", file=sys.stderr)
        sys.exit(1)

    result = run_brainfuck(code)
    # Write exactly what the Brainfuck program produced — no extra newline.
    sys.stdout.write(result)


if __name__ == "__main__":
    main()
