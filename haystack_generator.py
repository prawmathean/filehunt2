#!/usr/bin/env python3
"""
haystack_generator.py
=====================
Standalone module AND CLI tool for generating a "haystack" of decoy files
with exactly ONE real file hidden among them.

Importable by phase2_generate.py:
    from haystack_generator import generate_haystack

CLI usage:
    python3 haystack_generator.py <output_dir> <word> <num_decoys>

The GLOBAL MECHANIC of the event: the answer to each clue is literally the
name of the next file to find (e.g. answer "oracle" → look for oracle_*.ext).
"""

import os
import sys
import random
import string

# ---------------------------------------------------------------------------
# Tunable constants
# ---------------------------------------------------------------------------
MIN_FILE_SIZE = 512     # bytes — minimum random-junk payload per decoy file
MAX_FILE_SIZE = 4096    # bytes — maximum random-junk payload per decoy file

# Extension rotation list (shared with noise generator style)
EXTENSIONS = [
    ".txt", ".dat", ".log", ".bin", ".cfg", ".tmp",
    ".jpg", ".png", ".mp3", ".doc", ".csv", ".xml", ".bak",
]

# Fake magic-byte headers prepended to decoy files (purely cosmetic)
FAKE_HEADERS = [
    b"\xFF\xD8\xFF\xE0",   # JPEG
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"ID3",                # MP3
    b"%PDF-1.4",           # PDF
    b"",                   # plain junk
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _digit_width(n: int) -> int:
    """Return how many decimal digits are needed to represent n-1 (0-indexed)."""
    return max(1, len(str(n - 1)))


def _random_junk(rng: random.Random) -> bytes:
    """Return a random-sized binary blob with a random fake header prepended."""
    header = rng.choice(FAKE_HEADERS)
    size   = rng.randint(MIN_FILE_SIZE, MAX_FILE_SIZE)
    body   = bytes(rng.randint(0, 255) for _ in range(size))
    return header + body


# ---------------------------------------------------------------------------
# Puzzle generators
# ---------------------------------------------------------------------------

def _make_math_puzzle(target: int, digit_width: int, rng: random.Random) -> str:
    """
    Generate a short arithmetic expression that evaluates to `target`.
    Strategy: pick two random addends a + b + adjustment = target, or
    a small multiplication chain, keeping numbers human-sized.
    Always verified by eval() before returning.
    """
    # Try a few approaches and pick the first that works.
    for _ in range(100):
        style = rng.choice(["add2", "add3", "mul_add"])

        if style == "add2":
            a = rng.randint(0, target)
            b = target - a
            expr = f"{a} + {b}"
        elif style == "add3":
            a = rng.randint(0, target)
            remaining = target - a
            b = rng.randint(0, remaining)
            c = remaining - b
            expr = f"{a} + {b} + {c}"
        else:  # mul_add
            # find a small factor
            candidates = [f for f in range(2, 20) if target % f == 0]
            if candidates:
                f = rng.choice(candidates)
                expr = f"{f} * {target // f}"
            else:
                a = rng.randint(1, max(1, target))
                expr = f"{a} + {target - a}"

        if eval(expr) == target:  # noqa: S307 — controlled, no user input
            padded = str(target).zfill(digit_width)
            return (
                f"Solve this to find the index of the real file.\n"
                f"The answer is a {digit_width}-digit number (zero-pad if needed).\n\n"
                f"  {expr} = ?\n\n"
                f"The file you want is oracle_{padded}.<ext> inside the oracle_files folder.\n"
                f"(There are many files — only one is real.)"
            )

    # Fallback: trivial identity
    padded = str(target).zfill(digit_width)
    return (
        f"Solve this to find the index of the real file.\n"
        f"The answer is a {digit_width}-digit number (zero-pad if needed).\n\n"
        f"  What is {target - 1} + 1 = ?\n\n"
        f"The file you want is oracle_{padded}.<ext> inside the oracle_files folder.\n"
        f"(There are many files — only one is real.)"
    )


def _make_logic_puzzle(target: int, digit_width: int, rng: random.Random) -> str:
    """
    Generate a number-sequence puzzle where the next value is `target`.
    Supports arithmetic sequences: a, a+d, a+2d, a+3d, ... → next = a+4d
    """
    # Choose a step size and starting value so the sequence hits target as the 5th term.
    # target = a + 4*d  → pick d, solve a.
    d = rng.choice([1, 2, 3, 5, 10])
    a = target - 4 * d
    if a < 0:
        d = 1
        a = target - 4

    seq = [a + i * d for i in range(4)]
    seq_str = ", ".join(str(x) for x in seq) + ", ?"
    padded = str(target).zfill(digit_width)

    return (
        f"Complete the sequence to find the index of the real file.\n"
        f"The answer is a {digit_width}-digit number (zero-pad if needed).\n\n"
        f"  {seq_str}\n\n"
        f"The file you want is oracle_{padded}.<ext> inside the oracle_files folder.\n"
        f"(There are many files — only one is real.)"
    )


def _make_index_puzzle(target: int, digit_width: int,
                       puzzle_type: str, rng: random.Random) -> str:
    """Dispatch to the requested puzzle style."""
    if puzzle_type == "logic":
        return _make_logic_puzzle(target, digit_width, rng)
    return _make_math_puzzle(target, digit_width, rng)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_haystack(
    base_dir: str,
    word: str,
    num_decoys: int,
    real_content: str,
    index_puzzle_type: str = "math",
    seed=None,
) -> dict:
    """
    Create a folder named f"{word}_files" inside base_dir containing
    num_decoys total files.

    File naming scheme: f"{word}_{i:0Nd}.{ext}"
        N  = number of decimal digits needed for indices 0 … num_decoys-1
        i  = zero-based index
        ext = randomly chosen from EXTENSIONS

    All files except ONE contain random junk (fake header + random bytes).
    The one real file contains real_content as plain UTF-8 text.

    Parameters
    ----------
    base_dir          : str  — Directory in which to create the haystack folder.
    word              : str  — Base word (e.g. "oracle").
    num_decoys        : int  — Total file count (including the one real file).
    real_content      : str  — Text to write into the single real file.
    index_puzzle_type : str  — "math" or "logic" (puzzle style for the clue).
    seed              : int|None — RNG seed for reproducibility.

    Returns
    -------
    dict with keys:
        "folder"       : str  — Absolute path to the created haystack folder.
        "real_index"   : int  — Zero-based index of the real file.
        "real_filename": str  — Full filename of the real file (with extension).
        "digit_width"  : int  — Zero-padding width used in filenames.
        "puzzle_text"  : str  — Ready-to-write puzzle clue text.
    """
    rng = random.Random(seed)

    dw      = _digit_width(num_decoys)
    folder  = os.path.join(base_dir, f"{word}_files")
    os.makedirs(folder, exist_ok=True)

    real_idx  = rng.randint(0, num_decoys - 1)
    real_ext  = rng.choice(EXTENSIONS)
    real_name = f"{word}_{str(real_idx).zfill(dw)}{real_ext}"

    for i in range(num_decoys):
        ext      = rng.choice(EXTENSIONS)
        filename = f"{word}_{str(i).zfill(dw)}{ext}"
        filepath = os.path.join(folder, filename)

        if i == real_idx:
            # Write the real content (override extension chosen above with real_ext)
            filepath = os.path.join(folder, real_name)
            with open(filepath, 'w', encoding='utf-8') as fh:
                fh.write(real_content)
        else:
            with open(filepath, 'wb') as fh:
                fh.write(_random_junk(rng))

    puzzle_text = _make_index_puzzle(real_idx, dw, index_puzzle_type, rng)

    return {
        "folder"       : os.path.abspath(folder),
        "real_index"   : real_idx,
        "real_filename": real_name,
        "digit_width"  : dw,
        "puzzle_text"  : puzzle_text,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 4:
        print(
            "Usage: python3 haystack_generator.py <output_dir> <word> <num_decoys>",
            file=sys.stderr,
        )
        sys.exit(1)

    out_dir    = sys.argv[1]
    word       = sys.argv[2]
    num_decoys = int(sys.argv[3])

    # Single call: use a plain real_content; the index is shown in the puzzle text.
    result = generate_haystack(
        base_dir          = out_dir,
        word              = word,
        num_decoys        = num_decoys,
        real_content      = (
            f"This is the REAL file — CLI test run, not an event pack.\n"
            f"Real index will be shown below.\n"
        ),
        index_puzzle_type = "math",
    )

    print(f"Haystack created at : {result['folder']}")
    print(f"Total files         : {num_decoys}")
    print(f"Real file index     : {result['real_index']}")
    print(f"Real filename       : {result['real_filename']}")
    print(f"Digit width         : {result['digit_width']}")
    print()
    print("--- Puzzle text ---")
    print(result["puzzle_text"])


if __name__ == "__main__":
    main()
