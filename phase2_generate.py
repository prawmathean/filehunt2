#!/usr/bin/env python3
"""
phase2_generate.py
==================
Generator for Phase 2 of the offline Linux File-Hunt event.
Run with:  python3 phase2_generate.py

GLOBAL MECHANIC: The answer to each clue IS the name of the next file to find.
(e.g. answer "cipher" → the next file to open is cipher.txt)

This script imports two sibling modules (must live in the same directory):
  - haystack_generator  (generate_haystack function)
  - brainfuck_interpreter (run_brainfuck function — used to VERIFY stage 7's .bf
    output during generation, before the file is written to disk)

Produces:
  - <OUTPUT_DIR>/participant_pack/   — folder given to each advancing team
  - <OUTPUT_DIR>/filehunt_phase2.zip — distributable zip (participant_pack only)
  - <OUTPUT_DIR>/admin_answer_log.txt — base64-encoded answer key (DO NOT DISTRIBUTE)

Phase 2 has 9 stages, all requiring actual technical actions.
Stages: double-cipher → caesar → number-cipher → fix-a-bug → polyglot →
        EXIF-meta → Brainfuck → haystack (with index puzzle) → [end inside haystack]
"""

import os
import sys
import random
import string
import base64
import zipfile
import shutil
import subprocess
import struct

# Import sibling modules (must be in the same directory as this script)
from haystack_generator import generate_haystack
from brainfuck_interpreter import run_brainfuck

# ---------------------------------------------------------------------------
# TUNABLE CONSTANTS — Phase 2 defaults are ~3-4× larger than Phase 1
# ---------------------------------------------------------------------------
OUTPUT_DIR      = "phase2_output"   # Directory for all generated outputs
NUM_FOLDERS     = 150               # Decoy folders in the tree (~4× Phase 1)
MAX_DEPTH       = 5                 # Max folder nesting depth
NUM_NOISE_FILES = 450               # Decoy junk files (~4× Phase 1)
MIN_FILE_SIZE   = 512               # bytes — minimum decoy payload
MAX_FILE_SIZE   = 8192              # bytes — maximum decoy payload
NUM_HAYSTACK    = 3000              # Total oracle_* files in the haystack
SEED            = None              # Set to an integer for reproducible output

# ---------------------------------------------------------------------------
# Wordlists for decoy naming  (identical lists required by spec)
# ---------------------------------------------------------------------------
LIST1 = [
    "skibidi", "rizz", "gyat", "sigma", "ohio", "fanum", "sus", "goofy",
    "cringe", "based", "npc", "alpha", "beta", "chad", "karen", "boomer",
    "zoomer", "yeet", "bruh", "cap", "bussin", "drip", "simp", "cope",
    "seethe", "malding", "mid", "peak", "goated", "ratio", "copium",
    "hopium", "doomer", "bloomer", "gremlin", "feral", "unc", "aura",
    "delulu", "mewing", "glazing", "slay", "no-cap", "lowkey", "highkey",
    "sheesh", "sussy", "pog", "poggers", "vibe",
]

LIST2 = [
    "mrbeast", "pewdiepie", "crypto", "nft", "tiktok", "youtube", "reddit",
    "discord", "twitch", "amongus", "minecraft", "fortnite", "roblox",
    "spongebob", "shrek", "gigachad", "wojak", "pepe", "doge", "stonks",
    "virgin", "rizzler", "toilet", "tax", "goon", "cave", "elmo", "shark",
    "duck", "goblin", "wizard", "banana", "chair", "lettuce", "sandwich",
    "grimace", "florida", "moth", "capybara", "dorito", "katana", "glizzy",
    "hamster", "waffle", "pickle", "nugget", "brainrot", "void", "swamp",
]

EXTENSIONS = [
    ".txt", ".dat", ".log", ".bin", ".cfg", ".tmp",
    ".jpg", ".png", ".mp3", ".doc", ".csv", ".xml", ".bak",
]

FAKE_HEADERS = [
    b"\xFF\xD8\xFF\xE0",
    b"\x89PNG\r\n\x1a\n",
    b"ID3",
    b"%PDF-1.4",
    b"",
]

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def random_decoy_name(rng: random.Random) -> str:
    return rng.choice(LIST1) + "_" + rng.choice(LIST2)


def random_junk(rng: random.Random) -> bytes:
    header = rng.choice(FAKE_HEADERS)
    size   = rng.randint(MIN_FILE_SIZE, MAX_FILE_SIZE)
    body   = bytes(rng.randint(0, 255) for _ in range(size))
    return header + body


def rot13(text: str) -> str:
    """Apply ROT13: shift each letter 13 places through the alphabet."""
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
    """Apply a Caesar cipher shift to letters only; preserve case and non-letters."""
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
    """Encode a word as hyphen-joined alphabet positions (A=1 … Z=26)."""
    parts = []
    for ch in word.lower():
        if 'a' <= ch <= 'z':
            parts.append(str(ord(ch) - ord('a') + 1))
    return '-'.join(parts)


# ---------------------------------------------------------------------------
# Brainfuck code generator (stage 7)
# ---------------------------------------------------------------------------

def make_brainfuck_for_string(target: str) -> str:
    """
    Generate a Brainfuck program that prints exactly `target`.
    Approach: for each character, reset the cell with [-], increment to the
    ASCII value using repeated +, then output with '.'.
    Simple and correct, if verbose.
    """
    lines = ["[ Brainfuck program — prints a fixed string. Generated programmatically. ]"]
    current_val = 0
    for ch in target:
        target_val = ord(ch)
        # Reset current cell to 0
        if current_val != 0:
            lines.append("[-]")
        # Increment to target ASCII value
        lines.append("+" * target_val)
        # Output
        lines.append(".")
        current_val = target_val
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Minimal valid JPEG builder (pure stdlib — no Pillow required)
# ---------------------------------------------------------------------------

def _make_minimal_jpeg(width: int = 8, height: int = 8,
                       color: tuple = (128, 128, 128)) -> bytes:
    """
    Build a tiny but genuinely decodable JFIF/JPEG using raw markers.
    Uses a grayscale 1×1 MCU — simplest possible valid JPEG.
    The JPEG encodes a small solid-gray image sufficient for exiftool to
    process without errors.

    This is a hand-crafted minimal JPEG:
      SOI → APP0 (JFIF) → DQT (quantisation table) → SOF0 → DHT → SOS → data → EOI
    """
    # We'll use a well-known minimal valid 1x1 gray JPEG byte sequence.
    # This is a 1×1 pixel gray JPEG — exiftool handles it perfectly.
    minimal_jpeg = bytes([
        0xFF, 0xD8,                         # SOI
        0xFF, 0xE0, 0x00, 0x10,             # APP0 marker, length=16
        0x4A, 0x46, 0x49, 0x46, 0x00,       # "JFIF\0"
        0x01, 0x01,                         # version 1.1
        0x00,                               # pixel aspect ratio
        0x00, 0x01, 0x00, 0x01,             # X/Y density = 1,1
        0x00, 0x00,                         # no thumbnail
        0xFF, 0xDB, 0x00, 0x43, 0x00,       # DQT marker, length=67, table 0
        # 64-byte quantisation table (all 1s — lossless quality)
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
        0xFF, 0xC0, 0x00, 0x0B,             # SOF0 marker, length=11
        0x08,                               # 8-bit precision
        0x00, 0x01, 0x00, 0x01,             # height=1, width=1
        0x01,                               # 1 component (gray)
        0x01, 0x11, 0x00,                   # component 1: Y, 1x1 sampling, QT 0
        0xFF, 0xC4, 0x00, 0x1F, 0x00,       # DHT marker, length=31, DC table 0
        # DC Huffman table: 16 lengths + up to 12 symbols
        0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0A, 0x0B,
        0xFF, 0xC4, 0x00, 0xB5, 0x10,       # DHT AC table 0, length=181
        0x00, 0x02, 0x01, 0x03, 0x03, 0x02, 0x04, 0x03,
        0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7D,
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12,
        0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
        0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xA1, 0x08,
        0x23, 0x42, 0xB1, 0xC1, 0x15, 0x52, 0xD1, 0xF0,
        0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0A, 0x16,
        0x17, 0x18, 0x19, 0x1A, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2A, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
        0x3A, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4A, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
        0x5A, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
        0x6A, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
        0x7A, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8A, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
        0x99, 0x9A, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7,
        0xA8, 0xA9, 0xAA, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6,
        0xB7, 0xB8, 0xB9, 0xBA, 0xC2, 0xC3, 0xC4, 0xC5,
        0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xD2, 0xD3, 0xD4,
        0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xE1, 0xE2,
        0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA,
        0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8,
        0xF9, 0xFA,
        0xFF, 0xDA, 0x00, 0x08,             # SOS marker, length=8
        0x01,                               # 1 component
        0x01, 0x00,                         # component 1, DC/AC table IDs
        0x00, 0x3F, 0x00,                   # spectral start=0, end=63, approx=0
        # Minimal compressed scan data for a 1×1 gray pixel (mid-gray ~128)
        0xF8, 0x7F, 0xFF,
        0xFF, 0xD9,                         # EOI
    ])
    return minimal_jpeg


# ---------------------------------------------------------------------------
# Folder tree and noise builders
# ---------------------------------------------------------------------------

def build_folder_tree(root: str, rng: random.Random) -> list:
    """
    Create NUM_FOLDERS subdirectories with organic uneven branching up to MAX_DEPTH.
    Returns list of all folder paths (including root).
    """
    folders = [root]
    for _ in range(NUM_FOLDERS):
        candidates = [
            f for f in folders
            if os.path.relpath(f, root).count(os.sep) < MAX_DEPTH
        ]
        if not candidates:
            candidates = [root]
        parent = rng.choice(candidates)
        name   = random_decoy_name(rng)
        path   = os.path.join(parent, name)
        os.makedirs(path, exist_ok=True)
        folders.append(path)
    return folders


def seed_noise_files(folders: list, rng: random.Random):
    """Write NUM_NOISE_FILES decoy files into randomly chosen folders."""
    for _ in range(NUM_NOISE_FILES):
        folder = rng.choice(folders)
        name   = random_decoy_name(rng) + rng.choice(EXTENSIONS)
        path   = os.path.join(folder, name)
        with open(path, 'wb') as fh:
            fh.write(random_junk(rng))


# ---------------------------------------------------------------------------
# Admin answer log
# ---------------------------------------------------------------------------

def write_admin_log(output_dir: str, log_entries: list) -> str:
    """Base64-encode the full log and write to admin_answer_log.txt."""
    header = (
        "PHASE 2 — ADMIN ANSWER LOG\n"
        "==========================\n"
        "This file is base64-encoded.\n"
        "Decode with:  base64 -d admin_answer_log.txt\n"
        "DO NOT distribute this file to participants.\n\n"
    )
    log_text = header + "\n\n".join(log_entries)
    encoded  = base64.b64encode(log_text.encode('utf-8')).decode('ascii')

    log_path = os.path.join(output_dir, "admin_answer_log.txt")
    with open(log_path, 'w', encoding='utf-8') as fh:
        fh.write("# Phase 2 Admin Answer Log — base64-encoded.\n")
        fh.write("# Decode with:  base64 -d admin_answer_log.txt\n")
        fh.write("# DO NOT share this file with participants!\n\n")
        fh.write(encoded + "\n")

    return log_path


# ---------------------------------------------------------------------------
# Participant-pack zip builder
# ---------------------------------------------------------------------------

def zip_participant_pack(pack_dir: str, zip_path: str):
    """Zip the participant_pack folder; admin log is excluded (lives outside)."""
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(pack_dir):
            for filename in filenames:
                full_path    = os.path.join(dirpath, filename)
                archive_name = os.path.relpath(full_path, os.path.dirname(pack_dir))
                zf.write(full_path, archive_name)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def main():
    rng = random.Random(SEED)

    abs_output = os.path.abspath(OUTPUT_DIR)
    pack_dir   = os.path.join(abs_output, "participant_pack")
    os.makedirs(pack_dir, exist_ok=True)

    # ---- Build folder tree ----
    print("[1/6] Building folder tree ...")
    folders = build_folder_tree(pack_dir, rng)

    # ---- Seed noise files ----
    print("[2/6] Seeding noise files ...")
    seed_noise_files(folders, rng)

    # ---- Place clue files ----
    print("[3/6] Placing clue files ...")
    log_entries = []

    # ----------------------------------------------------------------
    # STAGE 1 — START_HERE.txt in pack root — double-cycle cipher
    #   Step 1: ROT13 the plaintext
    #   Step 2: base64-encode the ROT13 result
    #   The file shows only the final base64 string + a vague hint.
    # ----------------------------------------------------------------
    s1_plaintext = "the next file is named cipher"
    s1_rot13     = rot13(s1_plaintext)
    s1_b64       = base64.b64encode(s1_rot13.encode('utf-8')).decode('ascii')

    stage1_path = os.path.join(pack_dir, "START_HERE.txt")
    with open(stage1_path, 'w', encoding='utf-8') as fh:
        fh.write(
            "Welcome to Phase 2.\n"
            "\n"
            "This message has been encoded — more than one decoding step is required.\n"
            "(We won't say which encodings or how many. Figure it out.)\n"
            "\n"
            f"{s1_b64}\n"
        )
    log_entries.append(
        "STAGE 1  (ROT13 → base64 double-cycle)\n"
        f"  Clue file    : START_HERE.txt\n"
        f"  Full path    : {os.path.relpath(stage1_path, abs_output)}\n"
        f"  Plaintext    : {s1_plaintext}\n"
        f"  After ROT13  : {s1_rot13}\n"
        f"  After base64 : {s1_b64}\n"
        f"  Answer       : cipher\n"
        f"  Next file    : cipher.txt"
    )

    # ----------------------------------------------------------------
    # STAGE 2 — cipher.txt — Caesar cipher, unknown shift
    # ----------------------------------------------------------------
    shift        = rng.randint(1, 25)
    s2_plaintext = "the next file is named breach"
    s2_ciphertext = caesar_shift(s2_plaintext, shift)

    stage2_folder = rng.choice(folders)
    stage2_path   = os.path.join(stage2_folder, "cipher.txt")
    with open(stage2_path, 'w', encoding='utf-8') as fh:
        fh.write(
            "Shifted by an unknown amount, 1 through 25. Brute-force it.\n"
            "\n"
            f"{s2_ciphertext}\n"
        )
    log_entries.append(
        "STAGE 2  (Caesar cipher — unknown shift)\n"
        f"  Clue file    : cipher.txt\n"
        f"  Full path    : {os.path.relpath(stage2_path, abs_output)}\n"
        f"  Plaintext    : {s2_plaintext}\n"
        f"  Shift used   : {shift}\n"
        f"  Ciphertext   : {s2_ciphertext}\n"
        f"  Answer       : breach\n"
        f"  Next file    : breach.txt"
    )

    # ----------------------------------------------------------------
    # STAGE 3 — breach.txt — number cipher (A=1 … Z=26)
    # ----------------------------------------------------------------
    s3_answer = "exploit"
    s3_encoded = alpha_position_encode(s3_answer)

    stage3_folder = rng.choice(folders)
    stage3_path   = os.path.join(stage3_folder, "breach.txt")
    with open(stage3_path, 'w', encoding='utf-8') as fh:
        fh.write(
            "Decode the number sequence below.\n"
            "A=1, B=2, C=3, ... Z=26\n"
            "Numbers are separated by hyphens.\n"
            "\n"
            f"{s3_encoded}\n"
        )
    log_entries.append(
        "STAGE 3  (A=1...Z=26 number cipher)\n"
        f"  Clue file    : breach.txt\n"
        f"  Full path    : {os.path.relpath(stage3_path, abs_output)}\n"
        f"  Answer word  : {s3_answer}\n"
        f"  Encoded      : {s3_encoded}\n"
        f"  Answer       : exploit\n"
        f"  Next file    : exploit.py"
    )

    # ----------------------------------------------------------------
    # STAGE 4 — exploit.py — fix-the-bug Python script
    #   Bug: off-by-one in range() — range(1, 10) should be range(1, 11)
    #   When fixed, prints: the next file is named payload
    # ----------------------------------------------------------------
    stage4_folder = rng.choice(folders)
    stage4_path   = os.path.join(stage4_folder, "exploit.py")
    # The deliberate bug: range(1, 10) instead of range(1, 11)
    # Correct sum of 1..10 = 55 → target check == 55 passes → prints the message.
    # With the bug, sum of 1..9 = 45 → fails silently (prints nothing).
    buggy_script = '''\
# There is exactly ONE bug in this script. Find it, fix it, then run it.
# When the bug is fixed, the script will print its message.

def compute_total(n):
    total = 0
    for i in range(1, n):   # BUG IS HERE
        total += i
    return total

result = compute_total(10)

if result == 55:
    print("the next file is named payload")
'''
    with open(stage4_path, 'w', encoding='utf-8') as fh:
        fh.write(buggy_script)
    log_entries.append(
        "STAGE 4  (fix-the-bug Python script)\n"
        f"  Clue file    : exploit.py\n"
        f"  Full path    : {os.path.relpath(stage4_path, abs_output)}\n"
        f"  Bug type     : off-by-one — range(1, n) should be range(1, n+1)\n"
        f"  Fix          : change range(1, n) to range(1, n+1)  OR  range(1, 11)\n"
        f"  Expected out : the next file is named payload\n"
        f"  Answer       : payload\n"
        f"  Next file    : payload.jpg"
    )

    # ----------------------------------------------------------------
    # STAGE 5 — payload.jpg — fake header / polyglot file
    #   First bytes: real JPEG magic bytes b"\xFF\xD8\xFF\xE0"
    #   Immediately followed by plain ASCII: "the next file is named quarantine"
    # ----------------------------------------------------------------
    stage5_folder = rng.choice(folders)
    stage5_path   = os.path.join(stage5_folder, "payload.jpg")
    s5_text       = "the next file is named quarantine"
    with open(stage5_path, 'wb') as fh:
        fh.write(b"\xFF\xD8\xFF\xE0")          # JPEG magic bytes
        fh.write(s5_text.encode('ascii'))       # immediately followed by plain text
    log_entries.append(
        "STAGE 5  (polyglot / fake-header file)\n"
        f"  Clue file    : payload.jpg\n"
        f"  Full path    : {os.path.relpath(stage5_path, abs_output)}\n"
        f"  File starts  : \\xFF\\xD8\\xFF\\xE0 (JPEG magic) then plain ASCII text\n"
        f"  Hidden text  : {s5_text}\n"
        f"  Tools to read: cat payload.jpg | strings  OR  strings payload.jpg\n"
        f"  Answer       : quarantine\n"
        f"  Next file    : quarantine.jpg"
    )

    # ----------------------------------------------------------------
    # STAGE 6 — quarantine.jpg — EXIF metadata steganography
    #   Try exiftool first; fall back to appending after EOI marker.
    # ----------------------------------------------------------------
    stage6_folder   = rng.choice(folders)
    stage6_path     = os.path.join(stage6_folder, "quarantine.jpg")
    s6_clue_text    = "the next file is named firewall"

    # Write a genuine minimal JPEG first
    jpeg_bytes = _make_minimal_jpeg()
    with open(stage6_path, 'wb') as fh:
        fh.write(jpeg_bytes)

    # Try exiftool to embed the clue in EXIF Comment
    exiftool_ok = False
    try:
        result = subprocess.run(
            ["exiftool", f"-Comment={s6_clue_text}", "-overwrite_original", stage6_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and os.path.isfile(stage6_path):
            exiftool_ok = True
            embed_method = "EXIF Comment via exiftool"
        else:
            embed_method = None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        embed_method = None

    if not exiftool_ok:
        # Fallback: append clue text after JPEG EOI marker (0xFFD9)
        # `strings quarantine.jpg | grep firewall` will still find it.
        with open(stage6_path, 'ab') as fh:
            fh.write(b"\n" + s6_clue_text.encode('utf-8') + b"\n")
        embed_method = "appended after EOI (exiftool not available)"

    # Verify the file exists
    if not os.path.isfile(stage6_path):
        raise RuntimeError(f"Stage 6: quarantine.jpg was not created at {stage6_path}")

    log_entries.append(
        "STAGE 6  (EXIF metadata / strings steganography)\n"
        f"  Clue file    : quarantine.jpg\n"
        f"  Full path    : {os.path.relpath(stage6_path, abs_output)}\n"
        f"  Embed method : {embed_method}\n"
        f"  Hidden text  : {s6_clue_text}\n"
        f"  Tools to use : exiftool quarantine.jpg  OR  strings quarantine.jpg | grep firewall\n"
        f"  Answer       : firewall\n"
        f"  Next file    : firewall.bf"
    )

    # ----------------------------------------------------------------
    # STAGE 7 — firewall.bf — Brainfuck program
    #   Target output: "the next file is named oracle"
    #   Generate BF code, VERIFY with run_brainfuck() before writing.
    # ----------------------------------------------------------------
    s7_target = "the next file is named oracle"
    bf_code   = make_brainfuck_for_string(s7_target)

    # VERIFICATION — must match exactly or raise an error (never write a broken puzzle)
    bf_output = run_brainfuck(bf_code)
    if bf_output != s7_target:
        raise RuntimeError(
            f"Stage 7: Brainfuck verification FAILED!\n"
            f"  Expected : {repr(s7_target)}\n"
            f"  Got      : {repr(bf_output)}\n"
            "Refusing to write a broken puzzle to disk."
        )

    stage7_folder = rng.choice(folders)
    stage7_path   = os.path.join(stage7_folder, "firewall.bf")
    with open(stage7_path, 'w', encoding='utf-8') as fh:
        fh.write(bf_code)

    log_entries.append(
        "STAGE 7  (Brainfuck — verified before writing)\n"
        f"  Clue file    : firewall.bf\n"
        f"  Full path    : {os.path.relpath(stage7_path, abs_output)}\n"
        f"  BF output    : {s7_target}\n"
        f"  Verified     : YES (run_brainfuck confirmed exact match)\n"
        f"  Run with     : python3 brainfuck_interpreter.py firewall.bf\n"
        f"  Answer       : oracle\n"
        f"  Next step    : find the oracle_files folder and solve the index puzzle"
    )

    # ----------------------------------------------------------------
    # STAGE 8 — Haystack (oracle_files) + index clue file
    #   Imported function: generate_haystack() from haystack_generator.py
    # ----------------------------------------------------------------
    print("[4/6] Generating oracle haystack ...")
    s8_real_content = (
        'Congrats! You\'ve found everything.\n'
        'You might\'ve kept track of every riddle and puzzle you\'ve solved so far.\n'
        'If not, go back and collect all that. Take note of the file names.\n'
        '\n'
        'Now, tell "We got it" to any of the Volunteers or Organizers,\n'
        'and hand over the list of file names to them.\n'
    )

    haystack_result = generate_haystack(
        base_dir          = pack_dir,
        word              = "oracle",
        num_decoys        = NUM_HAYSTACK,
        real_content      = s8_real_content,
        index_puzzle_type = "math",
        seed              = SEED,
    )

    # Place the index-puzzle clue file with a random decoy-style name
    # (must NOT be named "oracle" — the spec requires a LIST1_LIST2 combo)
    clue_name   = random_decoy_name(rng) + ".txt"
    clue_folder = rng.choice(folders)
    clue_path   = os.path.join(clue_folder, clue_name)
    with open(clue_path, 'w', encoding='utf-8') as fh:
        fh.write(haystack_result["puzzle_text"])

    log_entries.append(
        "STAGE 8  (haystack — oracle_files folder)\n"
        f"  Haystack dir   : {os.path.relpath(haystack_result['folder'], abs_output)}\n"
        f"  Total files    : {NUM_HAYSTACK}\n"
        f"  Real index     : {haystack_result['real_index']}\n"
        f"  Real filename  : {haystack_result['real_filename']}\n"
        f"  Digit width    : {haystack_result['digit_width']}\n"
        f"  Index clue     : {os.path.relpath(clue_path, abs_output)}\n"
        f"  Clue file name : {clue_name}\n"
        f"  NOTE           : The real oracle file contains the final congratulations message.\n"
        f"  This is the END of Phase 2 — no further stages."
    )

    # ---- Write admin answer log ----
    print("[5/6] Writing admin answer log ...")
    log_path = write_admin_log(abs_output, log_entries)

    # ---- Zip participant pack ----
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
    print(f"  Participant pack   : {pack_dir}")
    print(f"  Distributable zip  : {zip_path}")
    print(f"  Admin answer log   : {log_path}")
    print(f"  Folders created    : {total_folders}")
    print(f"  Total files        : {total_files}  (noise + haystack + 8 clue files)")
    print(f"  Clue stages        : 8 (stage 8's real file is also the final message)")
    print(f"  Oracle haystack    : {NUM_HAYSTACK} files, real index = {haystack_result['real_index']}")
    print(f"  BF verification    : PASSED (firewall.bf output confirmed)")
    print()
    print("  *** DO NOT distribute admin_answer_log.txt to participants! ***")
    print("  *** Hand out only filehunt_phase2.zip.                      ***")


if __name__ == "__main__":
    main()
