#!/usr/bin/env python3
"""
phase1_generate.py
==================
Generator for Phase 1 of the offline Linux File-Hunt event.
Run with:  python3 phase1_generate.py

GLOBAL MECHANIC: The answer to each clue IS the name of the next file to find.
(e.g. answer "keyboard" → hunt for a file called "keyboard" with ANY extension)

Key features:
  - Decoy folders/files use 1-, 2-, or 3-word names with mixed separators (_/-),
    making single-word clue filenames blend in (they are no longer obviously different).
  - Clue files for stages 4–8 carry a random fake header (JPEG/PNG/MP3/PDF magic bytes)
    followed immediately by plain-text content.  Use `cat` or `strings` to read them.
  - Each clue file (stages 4–8) has DECOY_CLONES_PER_CLUE impostor copies placed in
    different folders with different extensions — all containing random junk.
    Only the real clue file has readable text.  Participants are warned in START_HERE.txt.
  - Stages 1–3 remain plain .txt with no fake header (beginner-friendly).

Produces:
  - <OUTPUT_DIR>/participant_pack/   — folder given to each team
  - <OUTPUT_DIR>/filehunt_phase1.zip — distributable zip (participant_pack only)
  - <OUTPUT_DIR>/admin_answer_log.txt — base64-encoded answer key (DO NOT DISTRIBUTE)
"""

import os
import sys
import random
import base64
import zipfile
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# TUNABLE CONSTANTS
# ---------------------------------------------------------------------------
OUTPUT_DIR            = "phase1_output"
NUM_FOLDERS           = 256       # decoy folders in the tree
MAX_DEPTH             = 8         # max nesting depth
NUM_NOISE_FILES       = 1024      # random junk files
MIN_FILE_SIZE         = 256       # bytes — min junk payload
MAX_FILE_SIZE         = 2048      # bytes — max junk payload
DECOY_CLONES_PER_CLUE = 3        # how many impostor copies of each clue to place
SEED                  = None      # int for reproducible output, None = random

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
]

LIST2 = [
    "mrbeast", "pewdiepie", "crypto", "nft", "tiktok", "youtube", "reddit",
    "discord", "twitch", "amongus", "minecraft", "fortnite", "roblox",
    "spongebob", "shrek", "gigachad", "wojak", "pepe", "doge", "stonks",
    "virgin", "rizzler", "toilet", "tax", "goon", "cave", "elmo", "shark",
    "duck", "goblin", "wizard", "banana", "chair", "lettuce", "sandwich",
    "grimace", "florida", "moth", "capybara", "dorito", "katana", "glizzy",
    "mogger", "hamster", "waffle", "pickle", "nugget", "brainrot", "void",
    "swamp", "gooners", "alzheimers", "ragebaits", "clickbait", "fr",
]

EXTENSIONS = [
    ".txt", ".dat", ".log", ".bin", ".cfg", ".tmp",
    ".jpg", ".png", ".mp3", ".doc", ".csv", ".xml", ".bak",
]

# Headers for clue files (stages 4+) and junk files.
# Each entry: (bytes_header, matching_extension)
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

# Separators used to join words in multi-word decoy names
SEPARATORS = ["_", "-", "_"]   # underscore is more common, dash occasionally

# ---------------------------------------------------------------------------
# Helpers — naming
# ---------------------------------------------------------------------------

def random_decoy_name(rng: random.Random) -> str:
    """
    Return a 1-, 2-, or 3-word decoy name with randomly chosen separators.
    Examples: "gyat", "booby_mrbeast", "sus-roblox_goated", "npc_fortnite-toilet"
    """
    n_words = rng.choices([1, 2, 3], weights=[15, 55, 30])[0]
    pool    = LIST1 + LIST2          # draw from both pools for variety
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


def random_junk(rng: random.Random) -> bytes:
    header = rng.choice(FAKE_HEADERS)
    size   = rng.randint(MIN_FILE_SIZE, MAX_FILE_SIZE)
    body   = bytes(rng.randint(0, 255) for _ in range(size))
    return header + body


def pick_clue_header(rng: random.Random) -> tuple:
    """Return a random (header_bytes, extension) pair for a disguised clue file."""
    return rng.choice(CLUE_HEADERS)


def write_disguised_clue(folder: str, stem: str, text_content: str,
                          rng: random.Random) -> tuple:
    """
    Write the real clue file with a random fake header before its readable text.
    Returns (full_path, chosen_extension).
    """
    header, ext = pick_clue_header(rng)
    path = os.path.join(folder, stem + ext)
    with open(path, 'wb') as fh:
        fh.write(header)
        fh.write(text_content.encode('utf-8'))
    return path, ext


def write_plain_clue(folder: str, filename: str, text_content: str) -> str:
    """Write a plain .txt clue file (used for stages 1-3)."""
    path = os.path.join(folder, filename)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text_content.strip() + "\n")
    return path


def place_decoy_clones(stem: str, real_folder: str, folders: list,
                        rng: random.Random, n: int):
    """
    Place n junk impostor files named <stem>.<random_ext> in different random
    folders (never the same folder as the real file).  Content is pure junk.
    Returns list of placed paths.
    """
    other_folders = [f for f in folders if f != real_folder]
    if not other_folders:
        other_folders = folders     # fallback if only one folder exists
    placed = []
    chosen_folders = rng.choices(other_folders, k=n)
    for folder in chosen_folders:
        ext  = rng.choice(EXTENSIONS)
        path = os.path.join(folder, stem + ext)
        with open(path, 'wb') as fh:
            fh.write(random_junk(rng))
        placed.append(path)
    return placed


# ---------------------------------------------------------------------------
# Folder tree builder
# ---------------------------------------------------------------------------

def build_folder_tree(root: str, rng: random.Random) -> list:
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


# ---------------------------------------------------------------------------
# Noise file seeder
# ---------------------------------------------------------------------------

def seed_noise_files(folders: list, rng: random.Random):
    for _ in range(NUM_NOISE_FILES):
        folder = rng.choice(folders)
        name   = random_decoy_name(rng) + rng.choice(EXTENSIONS)
        path   = os.path.join(folder, name)
        with open(path, 'wb') as fh:
            fh.write(random_junk(rng))


# ---------------------------------------------------------------------------
# ROT13 / base64 clue writers (stages 6 & 7 — also disguised)
# ---------------------------------------------------------------------------

def write_rot13_clue(folder: str, stem: str, plaintext: str,
                      rng: random.Random) -> tuple:
    ciphertext = rot13(plaintext)
    content = (
        "ROT13 is a simple letter-substitution cipher.\n"
        "Each letter is replaced by the letter 13 positions later in the alphabet.\n"
        "Example: A→N, B→O, ... Z→M.  ROT13 applied twice restores the original.\n"
        "Decode with:  echo '<ciphertext>' | tr 'A-Za-z' 'N-ZA-Mn-za-m'\n"
        "\n"
        "Decode the following:\n"
        "\n"
        f"  {ciphertext}\n"
    )
    path, ext = write_disguised_clue(folder, stem, content, rng)
    return path, ext, ciphertext


def write_base64_clue(folder: str, stem: str, plaintext: str,
                       rng: random.Random) -> tuple:
    encoded = base64.b64encode(plaintext.encode('utf-8')).decode('ascii')
    content = (
        "This one's base64-encoded.\n"
        "Decode with:  echo '<string>' | base64 -d\n"
        "\n"
        f"{encoded}\n"
    )
    path, ext = write_disguised_clue(folder, stem, content, rng)
    return path, ext, encoded


# ---------------------------------------------------------------------------
# Password-protected zip builder (stage 8)
# ---------------------------------------------------------------------------

def build_password_zip(zip_abs_path: str, password: str, inner_content: str):
    """
    Create a password-protected zip at zip_abs_path (MUST be absolute —
    the zip CLI resolves its output path relative to its own cwd, not Python's cwd).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        inner_file = os.path.join(tmpdir, "FINAL.txt")
        with open(inner_file, 'w', encoding='utf-8') as fh:
            fh.write(inner_content)
        cmd = ["zip", "--password", password, zip_abs_path, "FINAL.txt"]
        result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"Stage 8: `zip` CLI failed (exit {result.returncode}).\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        if not os.path.isfile(zip_abs_path):
            raise RuntimeError(
                f"Stage 8: zip CLI reported success but file missing: {zip_abs_path}"
            )


# ---------------------------------------------------------------------------
# Admin log + zip
# ---------------------------------------------------------------------------

def write_admin_log(output_dir: str, log_entries: list) -> str:
    header = (
        "PHASE 1 — ADMIN ANSWER LOG\n"
        "==========================\n"
        "Decode with:  base64 -d admin_answer_log.txt\n"
        "DO NOT distribute this file to participants.\n\n"
    )
    encoded  = base64.b64encode((header + "\n\n".join(log_entries)).encode()).decode()
    log_path = os.path.join(output_dir, "admin_answer_log.txt")
    with open(log_path, 'w', encoding='utf-8') as fh:
        fh.write("# Phase 1 Admin Answer Log — base64-encoded.\n")
        fh.write("# Decode with:  base64 -d admin_answer_log.txt\n")
        fh.write("# DO NOT share this file with participants!\n\n")
        fh.write(encoded + "\n")
    return log_path


def zip_participant_pack(pack_dir: str, zip_path: str):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _, filenames in os.walk(pack_dir):
            for filename in filenames:
                full     = os.path.join(dirpath, filename)
                arcname  = os.path.relpath(full, os.path.dirname(pack_dir))
                zf.write(full, arcname)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    rng = random.Random(SEED)

    abs_output = os.path.abspath(OUTPUT_DIR)
    pack_dir   = os.path.join(abs_output, "participant_pack")
    os.makedirs(pack_dir, exist_ok=True)

    print("[1/5] Building folder tree ...")
    folders = build_folder_tree(pack_dir, rng)

    print("[2/5] Seeding noise files ...")
    seed_noise_files(folders, rng)

    print("[3/5] Placing clue files ...")
    log_entries = []

    # ----------------------------------------------------------------
    # STAGE 1 — START_HERE.txt — plain text, always in pack root
    # ----------------------------------------------------------------
    stage1_path = os.path.join(pack_dir, "START_HERE.txt")
    stage1_text = (
        'Welcome to the File Hunt!\n'
        '\n'
        'The answer to each puzzle is the NAME (not extension) of the next file.\n'
        'Files can have any extension — .jpg, .mp3, .pdf, etc.\n'
        'Some files may need `cat` or `strings` to read.\n'
        f'NOTE: Each clue file has {DECOY_CLONES_PER_CLUE} impostor copies with '
        'the same name but junk inside.\n'
        'Only ONE copy of each clue has real text — the rest are traps.\n'
        '\n'
        '--- YOUR FIRST PUZZLE ---\n'
        '\n'
        'I have keys but open no locks. I have space but no room.\n'
        "You can enter, but you can't go inside. What am I?\n"
    )
    write_plain_clue(pack_dir, "START_HERE.txt", stage1_text)
    log_entries.append(
        "STAGE 1\n"
        f"  Clue file : START_HERE.txt\n"
        f"  Full path : {os.path.relpath(stage1_path, abs_output)}\n"
        f"  Extension : .txt (plain, no fake header)\n"
        f"  Answer    : keyboard\n"
        f"  Next file : keyboard  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 2 — keyboard — plain .txt
    # ----------------------------------------------------------------
    s2_folder = rng.choice(folders)
    s2_path   = write_plain_clue(s2_folder, "keyboard.txt",
        "I follow you all day but disappear at night.\n"
        "The brighter the light, the darker I get. What am I?\n"
    )
    log_entries.append(
        "STAGE 2\n"
        f"  Clue file : keyboard.txt\n"
        f"  Full path : {os.path.relpath(s2_path, abs_output)}\n"
        f"  Extension : .txt (plain)\n"
        f"  Answer    : shadow\n"
        f"  Next file : shadow  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 3 — shadow — plain .txt
    # ----------------------------------------------------------------
    s3_folder = rng.choice(folders)
    s3_path   = write_plain_clue(s3_folder, "shadow.txt",
        "I can be public or private.\n"
        "Cyber-savvy people never reuse me across different websites,\n"
        "and I'm best when I'm long, random, and changed regularly.\n"
        "What am I?\n"
    )
    log_entries.append(
        "STAGE 3\n"
        f"  Clue file : shadow.txt\n"
        f"  Full path : {os.path.relpath(s3_path, abs_output)}\n"
        f"  Extension : .txt (plain)\n"
        f"  Answer    : password\n"
        f"  Next file : password  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 4 — password — disguised (fake header + plain text inside)
    # ----------------------------------------------------------------
    s4_folder = rng.choice(folders)
    s4_path, s4_ext = write_disguised_clue(s4_folder, "password",
        "I'm not in the sky, but almost everyone stores their photos and files\n"
        "in me these days. You can't touch me, but companies happily charge\n"
        "you a monthly fee for space inside me. What am I (one word)?\n",
        rng
    )
    decoys4 = place_decoy_clones("password", s4_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 4\n"
        f"  Clue file : password{s4_ext}  (fake header, plain text inside)\n"
        f"  Full path : {os.path.relpath(s4_path, abs_output)}\n"
        f"  Read with : cat password{s4_ext}   OR   strings password{s4_ext}\n"
        f"  Decoy clones ({DECOY_CLONES_PER_CLUE}): {[os.path.relpath(p, abs_output) for p in decoys4]}\n"
        f"  Answer    : cloud\n"
        f"  Next file : cloud  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 5 — cloud — disguised
    # ----------------------------------------------------------------
    s5_folder = rng.choice(folders)
    s5_path, s5_ext = write_disguised_clue(s5_folder, "cloud",
        "This Marvel villain snapped his fingers and wiped out half of all\n"
        "life in the universe. Name him.\n",
        rng
    )
    decoys5 = place_decoy_clones("cloud", s5_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 5\n"
        f"  Clue file : cloud{s5_ext}  (fake header)\n"
        f"  Full path : {os.path.relpath(s5_path, abs_output)}\n"
        f"  Decoy clones ({DECOY_CLONES_PER_CLUE}): {[os.path.relpath(p, abs_output) for p in decoys5]}\n"
        f"  Answer    : thanos\n"
        f"  Next file : thanos  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 6 — thanos — ROT13, disguised
    # ----------------------------------------------------------------
    s6_folder = rng.choice(folders)
    s6_path, s6_ext, s6_cipher = write_rot13_clue(
        s6_folder, "thanos", "the next file is named matrix", rng
    )
    decoys6 = place_decoy_clones("thanos", s6_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 6  (ROT13)\n"
        f"  Clue file  : thanos{s6_ext}  (fake header)\n"
        f"  Full path  : {os.path.relpath(s6_path, abs_output)}\n"
        f"  Plaintext  : the next file is named matrix\n"
        f"  Ciphertext : {s6_cipher}\n"
        f"  Decoys     : {[os.path.relpath(p, abs_output) for p in decoys6]}\n"
        f"  Answer     : matrix\n"
        f"  Next file  : matrix  (any extension)"
    )

    # ----------------------------------------------------------------
    # STAGE 7 — matrix — base64, disguised
    # ----------------------------------------------------------------
    s7_folder = rng.choice(folders)
    s7_path, s7_ext, s7_encoded = write_base64_clue(
        s7_folder, "matrix", "the next file is named algorithm", rng
    )
    decoys7 = place_decoy_clones("matrix", s7_folder, folders, rng,
                                  DECOY_CLONES_PER_CLUE)
    log_entries.append(
        "STAGE 7  (base64)\n"
        f"  Clue file  : matrix{s7_ext}  (fake header)\n"
        f"  Full path  : {os.path.relpath(s7_path, abs_output)}\n"
        f"  Plaintext  : the next file is named algorithm\n"
        f"  Base64     : {s7_encoded}\n"
        f"  Decoys     : {[os.path.relpath(p, abs_output) for p in decoys7]}\n"
        f"  Answer     : algorithm\n"
        f"  Next file  : algorithm_locked.zip"
    )

    # ----------------------------------------------------------------
    # STAGE 8 — algorithm_locked.zip — password-protected (FINAL)
    # The zip extension is fixed; we still place junk decoy zips.
    # ----------------------------------------------------------------
    s8_folder  = rng.choice(folders)
    s8_zip     = os.path.join(s8_folder, "algorithm_locked.zip")
    s8_zip_abs = os.path.abspath(s8_zip)   # MUST be absolute for zip CLI
    s8_password = "password"               # = answer to stage 3

    s8_final_content = (
        "Congrats! You've found everything.\n"
        "You might've kept track of every riddle and puzzle you've solved so far.\n"
        "If not, go back and collect all that. Take note of the file names.\n"
        "\n"
        'Now, tell "We got it" to any of the Volunteers or Organizers,\n'
        "and hand over the list of file names to them.\n"
    )

    print("    [Stage 8] Building password-protected zip ...")
    build_password_zip(s8_zip_abs, s8_password, s8_final_content)

    # Junk decoy zips (same filename, but NOT password-protected — unzipping them
    # gives garbage, which is the tell, but teams have to try first).
    decoys8 = []
    other8  = [f for f in folders if f != s8_folder]
    if not other8:
        other8 = folders
    for decoy_folder in rng.choices(other8, k=DECOY_CLONES_PER_CLUE):
        d_path = os.path.join(decoy_folder, "algorithm_locked.zip")
        with open(d_path, 'wb') as fh:
            fh.write(random_junk(rng))
        decoys8.append(d_path)

    log_entries.append(
        "STAGE 8  (password-protected zip — FINAL)\n"
        f"  Clue file  : algorithm_locked.zip\n"
        f"  Full path  : {os.path.relpath(s8_zip_abs, abs_output)}\n"
        f"  Password   : {s8_password}   (= answer to stage 3)\n"
        f"  Inner file : FINAL.txt\n"
        f"  Decoy zips : {[os.path.relpath(p, abs_output) for p in decoys8]}\n"
        f"  NOTE       : Decoy zips are junk — real one opens with `unzip -P password`"
    )

    # ---- Admin log ----
    print("[4/5] Writing admin answer log ...")
    log_path = write_admin_log(abs_output, log_entries)

    # ---- Distributable zip ----
    print("[5/5] Creating distributable zip ...")
    zip_path = os.path.join(abs_output, "filehunt_phase1.zip")
    zip_participant_pack(pack_dir, zip_path)

    # ---- Summary ----
    total_folders = sum(1 for _ in os.walk(pack_dir)) - 1
    total_files   = sum(len(fns) for _, _, fns in os.walk(pack_dir))

    print()
    print("=" * 60)
    print("PHASE 1 GENERATION COMPLETE")
    print("=" * 60)
    print(f"  Participant pack      : {pack_dir}")
    print(f"  Distributable zip     : {zip_path}")
    print(f"  Admin answer log      : {log_path}")
    print(f"  Folders created       : {total_folders}")
    print(f"  Total files           : {total_files}  (noise + clues + decoy clones)")
    print(f"  Clue stages           : 8")
    print(f"  Decoy clones per clue : {DECOY_CLONES_PER_CLUE}")
    print()
    print("  *** DO NOT distribute admin_answer_log.txt to participants! ***")
    print("  *** Hand out only filehunt_phase1.zip.                      ***")


if __name__ == "__main__":
    main()
