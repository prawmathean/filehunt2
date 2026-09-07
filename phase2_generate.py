#!/usr/bin/env python3
"""
phase2_generate.py
==================
Generator for Phase 2 of the offline Linux File-Hunt event.
Run with:  python3 phase2_generate.py

GLOBAL MECHANIC: The answer to each clue IS the name of the next file to find.

This script imports two sibling modules (same directory):
  - haystack_generator  → generate_haystack()
  - brainfuck_interpreter → run_brainfuck()  (to verify stage 7 before writing)

Key features vs Phase 1:
  - ALL clue files (including START_HERE.txt) carry random fake headers —
    participants must use `cat`, `strings`, `exiftool`, or `python3` to read them.
  - Decoy folder/file names are 1-, 2-, or 3-word combos with mixed _ / - separators,
    so single-word clue filenames (cipher.txt, breach.txt …) don't stand out.
  - Each clue file (stages 1–7) has DECOY_CLONES_PER_CLUE junk impostor copies
    with the same stem but random extensions placed in different folders.
    Participants are warned in START_HERE.txt.
  - ~3–4× bigger haystack than Phase 1.

Produces:
  - <OUTPUT_DIR>/participant_pack/
  - <OUTPUT_DIR>/filehunt_phase2.zip
  - <OUTPUT_DIR>/admin_answer_log.txt  (DO NOT DISTRIBUTE)
"""

import os
import sys
import random
import base64
import zipfile
import subprocess

from haystack_generator import generate_haystack
from brainfuck_interpreter import run_brainfuck

# ---------------------------------------------------------------------------
# TUNABLE CONSTANTS
# ---------------------------------------------------------------------------
OUTPUT_DIR            = "phase2_output"
NUM_FOLDERS           = 512
MAX_DEPTH             = 16
NUM_NOISE_FILES       = 4500
MIN_FILE_SIZE         = 512
MAX_FILE_SIZE         = 8192
NUM_HAYSTACK          = 3000
DECOY_CLONES_PER_CLUE = 3        # impostor copies per clue file
SEED                  = None

# Path to the source JPEG used for Stage 5 (EXIF / ImageDescription clue).
# Must be a real JPEG that exiftool can process.  Keep it in the same directory
# as this script, or provide an absolute path.
GEEKS_JPG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "geeks.jpg")

# ---------------------------------------------------------------------------
# Wordlists
# ---------------------------------------------------------------------------
LIST1 = [
    "sixSeven", "gyat", "coy", "booby", "fanum", "sus", "goofy",
    "nineElvn", "based", "npc", "alpha", "beta", "karen", "boomer",
    "zoomer", "yeet", "bruh", "cap", "bussin", "drip", "simp", "cope",
    "seethe", "malding", "mid", "peak", "goated", "ratio", "copium",
    "hopium", "doomer", "bloomer", "gremlin", "feral", "unc", "aura",
    "delulu", "mewing", "glazing", "slay", "no-cap", "lowkey", "highkey",
    "sheesh", "sussy", "pog", "poggers", "vibe", "mr_poopy-butthole",
    "poop", "black", "horny", "oyas", "rijo",
    "rizz", "cooked", "locked-in", "edging", "looksmaxxing", "yapping",
    "blud", "fam", "schizo", "pick-me", "trad", "woke", "opp", "banger",
    "slaps", "valid", "tweaking", "zesty", "mogged", "yikes", "clutch",
]

LIST2 = [
    "mrbeast", "pewdiepie", "crypto", "nft", "tiktok", "youtube", "reddit",
    "discord", "twitch", "amongus", "minecraft", "fortnite", "roblox",
    "spongebob", "shrek", "gigachad", "wojak", "pepe", "doge", "stonks",
    "virgin", "rizzler", "toilet", "tax", "goon", "cave", "elmo", "shark",
    "duck", "goblin", "wizard", "banana", "chair", "lettuce", "sandwich",
    "grimace", "florida", "moth", "capybara", "dorito", "glizzy", "mogger",
    "hamster", "waffle", "pickle", "nugget", "brainrot", "void", "swamp",
    "gooners", "alzheimers", "ragebaits", "clickbait", "fr",
    "grindset", "schizoposting", "backrooms", "cheems", "floppa", "bingus",
    "donkey", "twitter", "instagram", "tumblr", "linux", "debian",
    "kernel", "python", "javascript", "css", "html", "potato",
    "toaster", "giga", "soup", "bean", "gigachadette",
]

EXTENSIONS = [
    ".txt", ".dat", ".log", ".bin", ".cfg", ".tmp",
    ".jpg", ".png", ".mp3", ".doc", ".csv", ".xml", ".bak",
]

CLUE_HEADERS = [
    (b"\xFF\xD8\xFF\xE0", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"ID3",               ".mp3"),
    (b"%PDF-1.4",          ".pdf"),
]

FAKE_HEADERS = [
    b"\xFF\xD8\xFF\xE0",
    b"\x89PNG\r\n\x1a\n",
    b"ID3",
    b"%PDF-1.4",
    b"",
]

SEPARATORS = ["_", "-", "_"]

# ---------------------------------------------------------------------------
# Helpers — naming
# ---------------------------------------------------------------------------

def random_decoy_name(rng: random.Random) -> str:
    """1-, 2-, or 3-word name with random _ / - separators."""
    n_words = rng.choices([1, 2, 3], weights=[15, 55, 30])[0]
    pool    = LIST1 + LIST2
    parts   = rng.sample(pool, k=min(n_words, len(pool)))
    if len(parts) == 1:
        return parts[0]
    sep1 = rng.choice(SEPARATORS)
    if len(parts) == 2:
        return parts[0] + sep1 + parts[1]
    sep2 = rng.choice(SEPARATORS)
    return parts[0] + sep1 + parts[1] + sep2 + parts[2]


# ---------------------------------------------------------------------------
# Helpers — content
# ---------------------------------------------------------------------------

def rot13(text: str) -> str:
    result = []
    for ch in text:
        if 'a' <= ch <= 'z':
            result.append(chr((ord(ch) - ord('a') + 13) % 26 + ord('a')))
        elif 'A' <= ch <= 'Z':
            result.append(chr((ord(ch) - ord('A') + 13) % 26 + ord('A')))
        else:
            result.append(ch)
    return ''.join(result)


def caesar_shift(text: str, shift: int) -> str:
    result = []
    for ch in text:
        if 'a' <= ch <= 'z':
            result.append(chr((ord(ch) - ord('a') + shift) % 26 + ord('a')))
        elif 'A' <= ch <= 'Z':
            result.append(chr((ord(ch) - ord('A') + shift) % 26 + ord('A')))
        else:
            result.append(ch)
    return ''.join(result)


def alpha_position_encode(word: str) -> str:
    return '-'.join(str(ord(c) - ord('a') + 1) for c in word.lower() if c.isalpha())


def random_junk(rng: random.Random) -> bytes:
    header = rng.choice(FAKE_HEADERS)
    size   = rng.randint(MIN_FILE_SIZE, MAX_FILE_SIZE)
    body   = bytes(rng.randint(0, 255) for _ in range(size))
    return header + body


def pick_clue_header(rng: random.Random) -> tuple:
    """Return a (header_bytes, extension) for a disguised clue file."""
    return rng.choice(CLUE_HEADERS)


def write_disguised_clue(folder: str, stem: str, text_content: str,
                          rng: random.Random) -> tuple:
    """Write fake-header + plain text. Returns (path, ext)."""
    header, ext = pick_clue_header(rng)
    path = os.path.join(folder, stem + ext)
    with open(path, 'wb') as fh:
        fh.write(header)
        fh.write(text_content.encode('utf-8'))
    return path, ext


def place_decoy_clones(stem: str, real_folder: str, folders: list,
                        rng: random.Random, n: int) -> list:
    """Place n junk impostor files (same stem, random ext) in different folders."""
    other = [f for f in folders if f != real_folder] or folders
    placed = []
    for folder in rng.choices(other, k=n):
        ext  = rng.choice(EXTENSIONS)
        path = os.path.join(folder, stem + ext)
        with open(path, 'wb') as fh:
            fh.write(random_junk(rng))
        placed.append(path)
    return placed


# ---------------------------------------------------------------------------
# Brainfuck generator (stage 7)
# ---------------------------------------------------------------------------

def make_brainfuck_for_string(target: str) -> str:
    lines = ["[ Brainfuck: prints a fixed string. Generated programmatically. ]"]
    for ch in target:
        lines.append("[-]")
        lines.append("+" * ord(ch))
        lines.append(".")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Minimal valid JPEG builder (stdlib only — for stage 6 exiftool embedding)
# ---------------------------------------------------------------------------

def _make_minimal_jpeg() -> bytes:
    return bytes([
        0xFF,0xD8, 0xFF,0xE0,0x00,0x10, 0x4A,0x46,0x49,0x46,0x00,
        0x01,0x01, 0x00, 0x00,0x01,0x00,0x01, 0x00,0x00,
        0xFF,0xDB,0x00,0x43,0x00,
        *([0x01]*64),
        0xFF,0xC0,0x00,0x0B, 0x08, 0x00,0x01,0x00,0x01, 0x01, 0x01,0x11,0x00,
        0xFF,0xC4,0x00,0x1F,0x00,
        0x00,0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0A,0x0B,
        0xFF,0xC4,0x00,0xB5,0x10,
        0x00,0x02,0x01,0x03,0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7D,
        0x01,0x02,0x03,0x00,0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,0x13,0x51,0x61,0x07,
        0x22,0x71,0x14,0x32,0x81,0x91,0xA1,0x08,0x23,0x42,0xB1,0xC1,0x15,0x52,0xD1,0xF0,
        0x24,0x33,0x62,0x72,0x82,0x09,0x0A,0x16,0x17,0x18,0x19,0x1A,0x25,0x26,0x27,0x28,
        0x29,0x2A,0x34,0x35,0x36,0x37,0x38,0x39,0x3A,0x43,0x44,0x45,0x46,0x47,0x48,0x49,
        0x4A,0x53,0x54,0x55,0x56,0x57,0x58,0x59,0x5A,0x63,0x64,0x65,0x66,0x67,0x68,0x69,
        0x6A,0x73,0x74,0x75,0x76,0x77,0x78,0x79,0x7A,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
        0x8A,0x92,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9A,0xA2,0xA3,0xA4,0xA5,0xA6,0xA7,
        0xA8,0xA9,0xAA,0xB2,0xB3,0xB4,0xB5,0xB6,0xB7,0xB8,0xB9,0xBA,0xC2,0xC3,0xC4,0xC5,
        0xC6,0xC7,0xC8,0xC9,0xCA,0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,0xD8,0xD9,0xDA,0xE1,0xE2,
        0xE3,0xE4,0xE5,0xE6,0xE7,0xE8,0xE9,0xEA,0xF1,0xF2,0xF3,0xF4,0xF5,0xF6,0xF7,0xF8,
        0xF9,0xFA,
        0xFF,0xDA,0x00,0x08, 0x01, 0x01,0x00, 0x00,0x3F,0x00,
        0xF8,0x7F,0xFF,
        0xFF,0xD9,
    ])


# ---------------------------------------------------------------------------
# Folder tree + noise
# ---------------------------------------------------------------------------

def build_folder_tree(root: str, rng: random.Random) -> list:
    folders = [root]
    for _ in range(NUM_FOLDERS):
        candidates = [f for f in folders
                      if os.path.relpath(f, root).count(os.sep) < MAX_DEPTH]
        if not candidates:
            candidates = [root]
        parent = rng.choice(candidates)
        path   = os.path.join(parent, random_decoy_name(rng))
        os.makedirs(path, exist_ok=True)
        folders.append(path)
    return folders


def seed_noise_files(folders: list, rng: random.Random):
    for _ in range(NUM_NOISE_FILES):
        folder = rng.choice(folders)
        name   = random_decoy_name(rng) + rng.choice(EXTENSIONS)
        with open(os.path.join(folder, name), 'wb') as fh:
            fh.write(random_junk(rng))


# ---------------------------------------------------------------------------
# Admin log + zip
# ---------------------------------------------------------------------------

def write_admin_log(output_dir: str, log_entries: list) -> str:
    header = (
        "PHASE 2 — ADMIN ANSWER LOG\n"
        "==========================\n"
        "Decode with:  base64 -d admin_answer_log.txt\n"
        "DO NOT distribute to participants.\n\n"
    )
    encoded  = base64.b64encode((header + "\n\n".join(log_entries)).encode()).decode()
    log_path = os.path.join(output_dir, "admin_answer_log.txt")
    with open(log_path, 'w', encoding='utf-8') as fh:
        fh.write("# Phase 2 Admin Answer Log — base64-encoded.\n")
        fh.write("# Decode with:  base64 -d admin_answer_log.txt\n")
        fh.write("# DO NOT share with participants!\n\n")
        fh.write(encoded + "\n")
    return log_path


def zip_participant_pack(pack_dir: str, zip_path: str):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _, filenames in os.walk(pack_dir):
            for fn in filenames:
                full    = os.path.join(dirpath, fn)
                arcname = os.path.relpath(full, os.path.dirname(pack_dir))
                zf.write(full, arcname)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    rng = random.Random(SEED)

    abs_output = os.path.abspath(OUTPUT_DIR)
    pack_dir   = os.path.join(abs_output, "participant_pack")
    os.makedirs(pack_dir, exist_ok=True)

    print("[1/6] Building folder tree ...")
    folders = build_folder_tree(pack_dir, rng)

    print("[2/6] Seeding noise files ...")
    seed_noise_files(folders, rng)

    print("[3/6] Placing clue files ...")
    log_entries = []

    # ----------------------------------------------------------------
    # STAGE 1 — START_HERE — double-cycle cipher (ROT13 → base64)
    # ----------------------------------------------------------------
    s1_plain  = "the next file is named cipher"
    s1_rot13  = rot13(s1_plain)
    s1_b64    = base64.b64encode(s1_rot13.encode()).decode()

    s1_text = (
        "Welcome to Phase 2.\n"
        "\n"
        f"NOTE: Each clue file has {DECOY_CLONES_PER_CLUE} impostor copies "
        "with the same name but junk inside. Only ONE copy of each clue has real text.\n"
        "Files can have any extension. Use `cat`, `strings`, or `exiftool` to read them.\n"
        "\n"
        "This message has been encoded — more than one decoding step is required.\n"
        "(Figure out which encodings and how many.)\n"
        "\n"
        f"{s1_b64}\n"
    )
    s1_path, s1_ext = write_disguised_clue(pack_dir, "START_HERE", s1_text, rng)
    decoys1 = place_decoy_clones("START_HERE", pack_dir, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 1  (ROT13 → base64)\n"
        f"  Clue file    : START_HERE{s1_ext}  (fake header + text)\n"
        f"  Full path    : {os.path.relpath(s1_path, abs_output)}\n"
        f"  Plaintext    : {s1_plain}\n"
        f"  After ROT13  : {s1_rot13}\n"
        f"  After base64 : {s1_b64}\n"
        f"  Decoys       : {[os.path.relpath(p, abs_output) for p in decoys1]}\n"
        f"  Answer       : cipher\n"
        f"  Next file    : cipher  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 2 — cipher — Caesar, unknown shift
    # ----------------------------------------------------------------
    shift       = rng.randint(1, 25)
    s2_plain    = "the next file is named breach"
    s2_cipher   = caesar_shift(s2_plain, shift)
    s2_text     = (
        "HINT: Caesar cipher (same family as what you did previously).\n"
        "Shifted by an unknown amount, 1 through 25. Brute-force it.\n"
        "\n"
        f"{s2_cipher}\n"
    )
    s2_folder = rng.choice(folders)
    s2_path, s2_ext = write_disguised_clue(s2_folder, "cipher", s2_text, rng)
    decoys2 = place_decoy_clones("cipher", s2_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 2  (Caesar — unknown shift)\n"
        f"  Clue file    : cipher{s2_ext}  (fake header)\n"
        f"  Full path    : {os.path.relpath(s2_path, abs_output)}\n"
        f"  Plaintext    : {s2_plain}\n"
        f"  Shift        : {shift}\n"
        f"  Ciphertext   : {s2_cipher}\n"
        f"  Decoys       : {[os.path.relpath(p, abs_output) for p in decoys2]}\n"
        f"  Answer       : breach\n"
        f"  Next file    : breach  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 3 — breach — A=1…Z=26 number cipher
    # ----------------------------------------------------------------
    s3_answer  = "exploit"
    s3_encoded = alpha_position_encode(s3_answer)
    s3_text    = (
        "Decode the number sequence below.\n"
        "A=1, B=2, C=3, ... Z=26.  Numbers separated by hyphens.\n"
        "\n"
        f"{s3_encoded}\n"
    )
    s3_folder = rng.choice(folders)
    s3_path, s3_ext = write_disguised_clue(s3_folder, "breach", s3_text, rng)
    decoys3 = place_decoy_clones("breach", s3_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 3  (A=1…Z=26)\n"
        f"  Clue file    : breach{s3_ext}  (fake header)\n"
        f"  Full path    : {os.path.relpath(s3_path, abs_output)}\n"
        f"  Answer word  : {s3_answer}\n"
        f"  Encoded      : {s3_encoded}\n"
        f"  Decoys       : {[os.path.relpath(p, abs_output) for p in decoys3]}\n"
        f"  Answer       : exploit\n"
        f"  Next file    : exploit  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 4 — exploit — fix-the-bug Python script
    # Extension stays .py (must be executable as Python — can't have a binary header).
    # Decoy clones get random extensions with junk.
    # ----------------------------------------------------------------
    buggy_script = '''\
# There is exactly ONE bug in this script. Find it, fix it, then run it.
# When fixed, the script will print its message.

def compute_total(n):
    total = 0
    for i in range(1, n):   # BUG IS HERE
        total += i
    return total

result = compute_total(10)

if result == 55:
    print("the next file is named payload")
'''
    s4_folder = rng.choice(folders)
    s4_path   = os.path.join(s4_folder, "exploit.py")
    with open(s4_path, 'w', encoding='utf-8') as fh:
        fh.write(buggy_script)
    # Decoy clones: junk files named exploit.<random ext>
    decoys4 = place_decoy_clones("exploit", s4_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 4  (fix-the-bug .py)\n"
        f"  Clue file    : exploit.py  (plain Python — no fake header)\n"
        f"  Full path    : {os.path.relpath(s4_path, abs_output)}\n"
        f"  Bug          : range(1, n) should be range(1, n+1)\n"
        f"  Expected out : the next file is named payload\n"
        f"  Decoys       : {[os.path.relpath(p, abs_output) for p in decoys4]}\n"
        f"  Answer       : payload\n"
        f"  Next file    : payload  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 5 — payload.jpg — real photo with clue in EXIF ImageDescription
    #
    # geeks.jpg is copied into the pack as "payload.jpg".
    # The clue is embedded in the EXIF ImageDescription field via exiftool.
    # Participants run:  exiftool payload.jpg
    # and read the ImageDescription (or Description) field.
    #
    # Fallback: if exiftool is unavailable at generation time, the clue
    # text is appended after the JPEG EOI marker so `strings` still finds it.
    # ----------------------------------------------------------------
    s5_clue   = "the next file is named quarantine"
    s5_folder = rng.choice(folders)
    s5_path   = os.path.join(s5_folder, "payload.jpg")

    # Verify source image exists before we start
    if not os.path.isfile(GEEKS_JPG_PATH):
        raise RuntimeError(
            f"Stage 5: source image not found: {GEEKS_JPG_PATH}\n"
            "Make sure geeks.jpg is in the same directory as phase2_generate.py."
        )

    # Copy geeks.jpg → payload.jpg (keeps the original untouched)
    import shutil as _shutil
    _shutil.copy2(GEEKS_JPG_PATH, s5_path)

    # Embed the clue in the EXIF ImageDescription field
    s5_exiftool_ok = False
    try:
        r5 = subprocess.run(
            [
                "exiftool",
                f"-ImageDescription={s5_clue}",
                "-overwrite_original",
                s5_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        s5_exiftool_ok = (r5.returncode == 0 and os.path.isfile(s5_path))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if not s5_exiftool_ok:
        # Fallback: append after EOI so `strings` finds it
        with open(s5_path, 'ab') as fh:
            fh.write(b"\n" + s5_clue.encode('utf-8') + b"\n")

    s5_embed = "EXIF ImageDescription via exiftool" if s5_exiftool_ok else "appended after EOI (fallback)"

    decoys5 = place_decoy_clones("payload", s5_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 5  (real JPEG — EXIF ImageDescription)\n"
        f"  Clue file    : payload.jpg  (geeks.jpg copy)\n"
        f"  Full path    : {os.path.relpath(s5_path, abs_output)}\n"
        f"  Embed method : {s5_embed}\n"
        f"  Hidden text  : {s5_clue}\n"
        f"  Read with    : exiftool payload.jpg\n"
        f"  Field name   : ImageDescription (or 'Description' in short output)\n"
        f"  Decoys       : {[os.path.relpath(p, abs_output) for p in decoys5]}\n"
        f"  Answer       : quarantine\n"
        f"  Next file    : quarantine  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 6 — quarantine.jpg — EXIF metadata (real JPEG + exiftool)
    # ----------------------------------------------------------------
    s6_clue   = "the next file is named firewall"
    s6_folder = rng.choice(folders)
    s6_path   = os.path.join(s6_folder, "quarantine.jpg")

    with open(s6_path, 'wb') as fh:
        fh.write(_make_minimal_jpeg())

    exiftool_ok = False
    try:
        r = subprocess.run(
            ["exiftool", f"-Comment={s6_clue}", "-overwrite_original", s6_path],
            capture_output=True, text=True, timeout=30,
        )
        exiftool_ok = (r.returncode == 0 and os.path.isfile(s6_path))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if not exiftool_ok:
        with open(s6_path, 'ab') as fh:
            fh.write(b"\n" + s6_clue.encode() + b"\n")

    if not os.path.isfile(s6_path):
        raise RuntimeError("Stage 6: quarantine.jpg was not created.")

    embed_method = "EXIF Comment via exiftool" if exiftool_ok else "appended after EOI"
    decoys6 = place_decoy_clones("quarantine", s6_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 6  (EXIF metadata)\n"
        f"  Clue file    : quarantine.jpg  (real JPEG)\n"
        f"  Full path    : {os.path.relpath(s6_path, abs_output)}\n"
        f"  Embed method : {embed_method}\n"
        f"  Hidden text  : {s6_clue}\n"
        f"  Read with    : exiftool quarantine.jpg  OR  strings quarantine.jpg | grep firewall\n"
        f"  Decoys       : {[os.path.relpath(p, abs_output) for p in decoys6]}\n"
        f"  Answer       : firewall\n"
        f"  Next file    : firewall  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 7 — firewall.bf — Brainfuck (verified before writing)
    # ----------------------------------------------------------------
    s7_target = "the next file is named oracle"
    bf_code   = make_brainfuck_for_string(s7_target)

    bf_out = run_brainfuck(bf_code)
    if bf_out != s7_target:
        raise RuntimeError(
            f"Stage 7 BF verification FAILED!\n"
            f"  Expected : {repr(s7_target)}\n"
            f"  Got      : {repr(bf_out)}"
        )

    s7_folder = rng.choice(folders)
    s7_path   = os.path.join(s7_folder, "firewall.bf")
    with open(s7_path, 'w', encoding='utf-8') as fh:
        fh.write(bf_code)
    # Decoy clones of firewall: junk with random ext (not .bf — avoid confusion)
    decoys7 = place_decoy_clones("firewall", s7_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 7  (Brainfuck — verified)\n"
        f"  Clue file    : firewall.bf\n"
        f"  Full path    : {os.path.relpath(s7_path, abs_output)}\n"
        f"  BF output    : {s7_target}\n"
        f"  Verified     : YES\n"
        f"  Run with     : python3 brainfuck_interpreter.py firewall.bf\n"
        f"  Decoys       : {[os.path.relpath(p, abs_output) for p in decoys7]}\n"
        f"  Answer       : oracle\n"
        f"  Next step    : find oracle_files folder and solve the index puzzle"
    )

    # ----------------------------------------------------------------
    # STAGE 8 — Haystack (oracle_files) + index puzzle clue
    # ----------------------------------------------------------------
    print("[4/6] Generating oracle haystack ...")
    s8_real_content = (
        "Congrats! You've found everything.\n"
        "You might've kept track of every riddle and puzzle you've solved so far.\n"
        "If not, go back and collect all that. Take note of the file names.\n"
        "\n"
        'Now, tell "We got it" to any of the Volunteers or Organizers,\n'
        "and hand over the list of file names to them.\n"
    )

    haystack_result = generate_haystack(
        base_dir          = pack_dir,
        word              = "oracle",
        num_decoys        = NUM_HAYSTACK,
        real_content      = s8_real_content,
        index_puzzle_type = "math",
        seed              = SEED,
    )

    # Index-puzzle clue file: random decoy-style name, NOT "oracle"
    clue_name   = random_decoy_name(rng) + ".txt"
    clue_folder = rng.choice(folders)
    clue_path   = os.path.join(clue_folder, clue_name)
    with open(clue_path, 'w', encoding='utf-8') as fh:
        fh.write(haystack_result["puzzle_text"])

    log_entries.append(
        "STAGE 8  (haystack)\n"
        f"  Haystack dir   : {os.path.relpath(haystack_result['folder'], abs_output)}\n"
        f"  Total files    : {NUM_HAYSTACK}\n"
        f"  Real index     : {haystack_result['real_index']}\n"
        f"  Real filename  : {haystack_result['real_filename']}\n"
        f"  Digit width    : {haystack_result['digit_width']}\n"
        f"  Index clue     : {os.path.relpath(clue_path, abs_output)}  ({clue_name})\n"
        f"  END OF PHASE 2 — real oracle file contains the congratulations message."
    )

    # ---- Admin log ----
    print("[5/6] Writing admin answer log ...")
    log_path = write_admin_log(abs_output, log_entries)

    # ---- Distributable zip ----
    print("[6/6] Creating distributable zip ...")
    zip_path = os.path.join(abs_output, "filehunt_phase2.zip")
    zip_participant_pack(pack_dir, zip_path)

    # ---- Summary ----
    total_folders = sum(1 for _ in os.walk(pack_dir)) - 1
    total_files   = sum(len(fns) for _, _, fns in os.walk(pack_dir))

    print()
    print("=" * 60)
    print("PHASE 2 GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Participant pack      : {pack_dir}")
    print(f"  Distributable zip     : {zip_path}")
    print(f"  Admin answer log      : {log_path}")
    print(f"  Folders created       : {total_folders}")
    print(f"  Total files           : {total_files}")
    print(f"  Clue stages           : 8 (stage 8 end = real oracle file)")
    print(f"  Oracle haystack       : {NUM_HAYSTACK} files, real index = {haystack_result['real_index']}")
    print(f"  Decoy clones per clue : {DECOY_CLONES_PER_CLUE}")
    print(f"  BF verification       : PASSED")
    print()
    print("  *** DO NOT distribute admin_answer_log.txt to participants! ***")
    print("  *** Hand out only filehunt_phase2.zip.                      ***")


if __name__ == "__main__":
    main()
