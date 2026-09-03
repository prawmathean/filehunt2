#!/usr/bin/env python3
"""
phase1_generate.py
==================
Generator for Phase 1 of the offline Linux File-Hunt event.
Run with:  python3 phase1_generate.py

GLOBAL MECHANIC: The answer to each clue IS the name of the next file to find.
(e.g. answer "keyboard" → the next file to open is keyboard.txt)

Produces:
  - <OUTPUT_DIR>/participant_pack/   — folder given to each team
  - <OUTPUT_DIR>/filehunt_phase1.zip — distributable zip (participant_pack only)
  - <OUTPUT_DIR>/admin_answer_log.txt — base64-encoded answer key (DO NOT DISTRIBUTE)

Phase 1 has 8 stages, beginner-friendly.
Stages 1–5: plain-text riddles only.
Stage 6: ROT13 cipher (explained inline).
Stage 7: base64 encoding (noted inline).
Stage 8: password-protected zip (password = answer to stage 3 = "password").
"""

import os
import sys
import random
import string
import base64
import zipfile
import shutil
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# TUNABLE CONSTANTS — edit these to change the haystack size
# ---------------------------------------------------------------------------
OUTPUT_DIR      = "phase1_output"   # Directory that will contain all generated outputs
NUM_FOLDERS     = 256                # How many decoy folders to create in the tree
MAX_DEPTH       = 8                 # Maximum nesting depth for the folder tree
NUM_NOISE_FILES = 1024               # How many decoy (junk) files to scatter
MIN_FILE_SIZE   = 256               # bytes — minimum decoy file payload
MAX_FILE_SIZE   = 2048              # bytes — maximum decoy file payload
SEED            = None              # Set to an integer for reproducible output; None = random

# ---------------------------------------------------------------------------
# Wordlists for decoy naming
# ---------------------------------------------------------------------------
LIST1 = [
    "sixSeven", "gyat", "coy", "booby", "fanum", "sus", "goofy",
    "nineElvn", "based", "npc", "alpha", "beta", "karen", "boomer",
    "zoomer", "yeet", "bruh", "cap", "bussin", "drip", "simp", "cope",
    "seethe", "malding", "mid", "peak", "goated", "ratio", "copium",
    "hopium", "doomer", "bloomer", "gremlin", "feral", "unc", "aura",
    "delulu", "mewing", "glazing", "slay", "no-cap", "lowkey", "highkey",
    "sheesh", "sussy", "pog", "poggers", "vibe","mr_poopy-butthole", "poop", "black", "horny" , "oyas" , "rijo"
]

LIST2 = [
    "mrbeast", "pewdiepie", "crypto", "nft", "tiktok", "youtube", "reddit",
    "discord", "twitch", "amongus", "minecraft", "fortnite", "roblox",
    "spongebob", "shrek", "gigachad", "wojak", "pepe", "doge", "stonks",
    "virgin", "rizzler", "toilet", "tax", "goon", "cave", "elmo", "shark",
    "duck", "goblin", "wizard", "banana", "chair", "lettuce", "sandwich",
    "grimace", "florida", "moth", "capybara", "dorito", "katana", "glizzy", "mogger", "horny "
    "hamster", "waffle", "pickle", "nugget", "brainrot", "void", "swamp", "gooners", "alzheimers", "ragebaits", "clickbait", "fr", 
]

# Decoy file extensions (rotate randomly)
EXTENSIONS = [
    ".txt", ".dat", ".log", ".bin", ".cfg", ".tmp",
    ".jpg", ".png", ".mp3", ".doc", ".csv", ".xml", ".bak",
]

# Fake magic-byte headers (cosmetic — makes `file` output look varied)
FAKE_HEADERS = [
    b"\xFF\xD8\xFF\xE0",    # JPEG
    b"\x89PNG\r\n\x1a\n",   # PNG
    b"ID3",                 # MP3
    b"%PDF-1.4",            # PDF
    b"",                    # plain junk
]

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def rot13(text: str) -> str:
    """Apply ROT13 transformation — shift each letter 13 places through the alphabet."""
    result = []
    for ch in text:
        if 'a' <= ch <= 'z':
            result.append(chr((ord(ch) - ord('a') + 13) % 26 + ord('a')))
        elif 'A' <= ch <= 'Z':
            result.append(chr((ord(ch) - ord('A') + 13) % 26 + ord('A')))
        else:
            result.append(ch)
    return ''.join(result)


def random_decoy_name(rng: random.Random) -> str:
    """Return a random name in LIST1_LIST2 format."""
    return random.choice(LIST1) + "_" + random.choice(LIST2)


def random_junk(rng: random.Random) -> bytes:
    """Return a random-sized binary blob with a random fake header prepended."""
    header = rng.choice(FAKE_HEADERS)
    size   = rng.randint(MIN_FILE_SIZE, MAX_FILE_SIZE)
    body   = bytes(rng.randint(0, 255) for _ in range(size))
    return header + body


# ---------------------------------------------------------------------------
# Folder tree builder
# ---------------------------------------------------------------------------

def build_folder_tree(root: str, rng: random.Random) -> list:
    """
    Create NUM_FOLDERS subdirectories under root with organic, uneven branching
    up to MAX_DEPTH levels deep.  Returns a list of all created folder paths
    (including root).
    """
    folders = [root]
    for _ in range(NUM_FOLDERS):
        # Pick a random existing folder as parent, but respect MAX_DEPTH.
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


# ---------------------------------------------------------------------------
# Noise file seeder
# ---------------------------------------------------------------------------

def seed_noise_files(folders: list, rng: random.Random) -> int:
    """
    Write NUM_NOISE_FILES decoy files into randomly chosen folders.
    Returns the count of files written.
    """
    for _ in range(NUM_NOISE_FILES):
        folder = rng.choice(folders)
        name   = random_decoy_name(rng) + rng.choice(EXTENSIONS)
        path   = os.path.join(folder, name)
        with open(path, 'wb') as fh:
            fh.write(random_junk(rng))
    return NUM_NOISE_FILES


# ---------------------------------------------------------------------------
# Clue file writers — Phase 1 specific
# ---------------------------------------------------------------------------

def write_clue_plain(path: str, riddle: str):
    """Write a plain-text riddle clue file."""
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(riddle.strip() + "\n")


def write_clue_rot13(path: str, plaintext: str):
    """
    Write a ROT13-encoded clue file.
    The file contains the ROT13 ciphertext of plaintext plus an inline
    explanation of what ROT13 is so teams can decode it without a hint.
    """
    ciphertext = rot13(plaintext)
    content = (
        "ROT13 is a simple letter-substitution cipher.\n"
        "Each letter in the alphabet is replaced by the letter 13 positions after it.\n"
        "For example: A→N, B→O, ... Z→M.  Applying ROT13 twice restores the original.\n"
        "Most Unix systems can decode with:  echo '<ciphertext>' | tr 'A-Za-z' 'N-ZA-Mn-za-m'\n"
        "\n"
        "Decode the following to find your next clue:\n"
        "\n"
        f"  {ciphertext}\n"
    )
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    return ciphertext


def write_clue_base64(path: str, plaintext: str):
    """
    Write a base64-encoded clue file.
    The file contains the base64 string plus a note identifying the encoding.
    """
    encoded = base64.b64encode(plaintext.encode('utf-8')).decode('ascii')
    content = (
        "This one's base64-encoded.\n"
        "Decode it with:  echo '<string>' | base64 -d\n"
        "\n"
        f"{encoded}\n"
    )
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(content)
    return encoded


def build_password_zip(zip_abs_path: str, password: str, inner_content: str):
    """
    Create a password-protected zip at zip_abs_path (must be an ABSOLUTE path
    — critical if cwd changes before calling the system zip CLI).
    Uses the system `zip` CLI via subprocess because Python's zipfile module
    cannot set passwords on write.
    Inner file is named FINAL.txt.
    Raises RuntimeError if the zip was not created successfully.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        inner_file = os.path.join(tmpdir, "FINAL.txt")
        with open(inner_file, 'w', encoding='utf-8') as fh:
            fh.write(inner_content)

        # IMPORTANT: pass zip_abs_path as an absolute path because the zip
        # CLI resolves the output relative to its cwd, not the Python cwd.
        # We stay in our Python cwd but give zip an absolute destination.
        cmd = [
            "zip", "--password", password,
            zip_abs_path,   # absolute output path
            "FINAL.txt",    # file to include (relative to cwd=tmpdir)
        ]
        result = subprocess.run(
            cmd,
            cwd=tmpdir,     # run zip from the temp dir so FINAL.txt is found
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Stage 8: `zip` CLI failed (exit {result.returncode}).\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        if not os.path.isfile(zip_abs_path):
            raise RuntimeError(
                f"Stage 8: zip CLI reported success but output file was not created: {zip_abs_path}"
            )


# ---------------------------------------------------------------------------
# Admin answer log
# ---------------------------------------------------------------------------

def write_admin_log(output_dir: str, log_entries: list):
    """
    Build a plain-text log from log_entries (list of strings),
    base64-encode it, and write it to admin_answer_log.txt in output_dir.
    log_entries: each item is one stage's text block.
    """
    header = (
        "PHASE 1 — ADMIN ANSWER LOG\n"
        "==========================\n"
        "This file is base64-encoded.\n"
        "Decode with:  base64 -d admin_answer_log.txt\n"
        "DO NOT distribute this file to participants.\n\n"
    )
    log_text = header + "\n\n".join(log_entries)
    encoded  = base64.b64encode(log_text.encode('utf-8')).decode('ascii')

    log_path = os.path.join(output_dir, "admin_answer_log.txt")
    with open(log_path, 'w', encoding='utf-8') as fh:
        fh.write("# Phase 1 Admin Answer Log — base64-encoded.\n")
        fh.write("# Decode with:  base64 -d admin_answer_log.txt\n")
        fh.write("# DO NOT share this file with participants!\n\n")
        fh.write(encoded + "\n")

    return log_path


# ---------------------------------------------------------------------------
# Participant-pack zip builder
# ---------------------------------------------------------------------------

def zip_participant_pack(pack_dir: str, zip_path: str):
    """
    Zip the entire participant_pack folder into zip_path using Python's
    zipfile module.  The admin_answer_log.txt lives one level up and is
    never included here.
    """
    pack_name = os.path.basename(pack_dir)
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

    # ---- Set up output directories ----
    abs_output   = os.path.abspath(OUTPUT_DIR)
    pack_dir     = os.path.join(abs_output, "participant_pack")
    os.makedirs(pack_dir, exist_ok=True)

    # ---- Build decoy folder tree ----
    print("[1/5] Building folder tree ...")
    folders = build_folder_tree(pack_dir, rng)

    # ---- Seed noise files ----
    print("[2/5] Seeding noise files ...")
    seed_noise_files(folders, rng)

    # ---- Place clue files ----
    print("[3/5] Placing clue files ...")
    log_entries = []

    # --- Stage 1: START_HERE.txt in pack root ---
    stage1_path = os.path.join(pack_dir, "START_HERE.txt")
    stage1_text = (
        'I have keys but open no locks. I have space but no room.\n'
        "You can enter, but you can't go inside. What am I?\n"
    )
    write_clue_plain(stage1_path, stage1_text)
    log_entries.append(
        "STAGE 1\n"
        f"  Clue file : START_HERE.txt\n"
        f"  Full path : {os.path.relpath(stage1_path, abs_output)}\n"
        f"  Answer    : keyboard\n"
        f"  Next file : keyboard.txt"
    )

    # --- Stage 2: keyboard.txt in a random folder ---
    stage2_folder = rng.choice(folders)
    stage2_path   = os.path.join(stage2_folder, "keyboard.txt")
    stage2_text   = (
        "I follow you all day but disappear at night.\n"
        "The brighter the light, the darker I get. What am I?\n"
    )
    write_clue_plain(stage2_path, stage2_text)
    log_entries.append(
        "STAGE 2\n"
        f"  Clue file : keyboard.txt\n"
        f"  Full path : {os.path.relpath(stage2_path, abs_output)}\n"
        f"  Answer    : shadow\n"
        f"  Next file : shadow.txt"
    )

    # --- Stage 3: shadow.txt in a random folder ---
    stage3_folder = rng.choice(folders)
    stage3_path   = os.path.join(stage3_folder, "shadow.txt")
    stage3_text   = (
        "I can be public or private.\n"
        "Cyber-savvy people never reuse me across different websites,\n"
        "and I'm best when I'm long, random, and changed regularly.\n"
        "What am I?\n"
    )
    write_clue_plain(stage3_path, stage3_text)
    log_entries.append(
        "STAGE 3\n"
        f"  Clue file : shadow.txt\n"
        f"  Full path : {os.path.relpath(stage3_path, abs_output)}\n"
        f"  Answer    : password\n"
        f"  Next file : password.txt"
    )

    # --- Stage 4: password.txt in a random folder ---
    stage4_folder = rng.choice(folders)
    stage4_path   = os.path.join(stage4_folder, "password.txt")
    stage4_text   = (
        "I'm not in the sky, but almost everyone stores their photos and files\n"
        "in me these days. You can't touch me, but companies happily charge\n"
        "you a monthly fee for space inside me. What am I (one word)?\n"
    )
    write_clue_plain(stage4_path, stage4_text)
    log_entries.append(
        "STAGE 4\n"
        f"  Clue file : password.txt\n"
        f"  Full path : {os.path.relpath(stage4_path, abs_output)}\n"
        f"  Answer    : cloud\n"
        f"  Next file : cloud.txt"
    )

    # --- Stage 5: cloud.txt in a random folder ---
    stage5_folder = rng.choice(folders)
    stage5_path   = os.path.join(stage5_folder, "cloud.txt")
    stage5_text   = (
        "This Marvel villain snapped his fingers and wiped out half of all\n"
        "life in the universe. Name him.\n"
    )
    write_clue_plain(stage5_path, stage5_text)
    log_entries.append(
        "STAGE 5\n"
        f"  Clue file : cloud.txt\n"
        f"  Full path : {os.path.relpath(stage5_path, abs_output)}\n"
        f"  Answer    : thanos\n"
        f"  Next file : thanos.txt"
    )

    # --- Stage 6: thanos.txt — ROT13 ---
    stage6_folder   = rng.choice(folders)
    stage6_path     = os.path.join(stage6_folder, "thanos.txt")
    stage6_plaintext = "the next file is named matrix"
    stage6_cipher   = write_clue_rot13(stage6_path, stage6_plaintext)
    log_entries.append(
        "STAGE 6  (ROT13)\n"
        f"  Clue file  : thanos.txt\n"
        f"  Full path  : {os.path.relpath(stage6_path, abs_output)}\n"
        f"  Plaintext  : {stage6_plaintext}\n"
        f"  Ciphertext : {stage6_cipher}\n"
        f"  Answer     : matrix\n"
        f"  Next file  : matrix.txt"
    )

    # --- Stage 7: matrix.txt — base64 ---
    stage7_folder    = rng.choice(folders)
    stage7_path      = os.path.join(stage7_folder, "matrix.txt")
    stage7_plaintext = "the next file is named algorithm"
    stage7_encoded   = write_clue_base64(stage7_path, stage7_plaintext)
    log_entries.append(
        "STAGE 7  (base64)\n"
        f"  Clue file  : matrix.txt\n"
        f"  Full path  : {os.path.relpath(stage7_path, abs_output)}\n"
        f"  Plaintext  : {stage7_plaintext}\n"
        f"  Base64     : {stage7_encoded}\n"
        f"  Answer     : algorithm\n"
        f"  Next file  : algorithm_locked.zip"
    )

    # --- Stage 8: algorithm_locked.zip — password-protected ---
    stage8_folder = rng.choice(folders)
    stage8_zip    = os.path.join(stage8_folder, "algorithm_locked.zip")
    # Use absolute path — critical! zip CLI resolves output relative to its own cwd.
    stage8_zip_abs = os.path.abspath(stage8_zip)
    stage8_password = "password"   # callback to stage 3's answer
    stage8_final_content = (
        'Congrats! You\'ve found everything.\n'
        'You might\'ve kept track of every riddle and puzzle you\'ve solved so far.\n'
        'If not, go back and collect all that. Take note of the file names.\n'
        '\n'
        'Now, tell "We got it" to any of the Volunteers or Organizers,\n'
        'and hand over the list of file names to them.\n'
    )

    print("    [Stage 8] Building password-protected zip ...")
    build_password_zip(stage8_zip_abs, stage8_password, stage8_final_content)
    log_entries.append(
        "STAGE 8  (password-protected zip — FINAL)\n"
        f"  Clue file  : algorithm_locked.zip\n"
        f"  Full path  : {os.path.relpath(stage8_zip_abs, abs_output)}\n"
        f"  Password   : {stage8_password}   (← same as the answer to stage 3)\n"
        f"  Inner file : FINAL.txt\n"
        f"  Content    : (see specification — congratulations message)\n"
        f"  NOTE       : This is the final stage of Phase 1."
    )

    # ---- Write admin answer log ----
    print("[4/5] Writing admin answer log ...")
    log_path = write_admin_log(abs_output, log_entries)

    # ---- Zip participant pack ----
    print("[5/5] Creating distributable zip ...")
    zip_path = os.path.join(abs_output, "filehunt_phase1.zip")
    zip_participant_pack(pack_dir, zip_path)

    # ---- Summary ----
    total_folders = sum(1 for _ in os.walk(pack_dir)) - 1  # exclude root itself
    total_files   = sum(len(fns) for _, _, fns in os.walk(pack_dir))

    print()
    print("=" * 60)
    print("PHASE 1 GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Participant pack   : {pack_dir}")
    print(f"  Distributable zip  : {zip_path}")
    print(f"  Admin answer log   : {log_path}")
    print(f"  Folders created    : {total_folders}")
    print(f"  Total files        : {total_files}  (noise + 8 clue files)")
    print(f"  Clue stages        : 8")
    print()
    print("  *** DO NOT distribute admin_answer_log.txt to participants! ***")
    print("  *** Hand out only filehunt_phase1.zip.                      ***")


if __name__ == "__main__":
    main()
