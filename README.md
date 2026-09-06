# FileHunt2 — Offline Linux File-Hunt Event Generator

A set of standalone Python 3 scripts that generate a complete offline,
in-person **college puzzle event** where teams race to follow a chain of
hidden clues buried inside a folder full of thousands of decoy files.
No internet access required — every mechanic is solvable using only
standard Ubuntu CLI tools plus `exiftool` and a Brainfuck interpreter
(both pre-installed on every event machine).

---

## Table of Contents

1. [How the Event Works](#how-the-event-works)
2. [Repository Layout](#repository-layout)
3. [Requirements](#requirements)
4. [Quick Start](#quick-start)
5. [The Four Scripts](#the-four-scripts)
   - [brainfuck_interpreter.py](#brainfuck_interpreterpy)
   - [haystack_generator.py](#haystack_generatorpy)
   - [phase1_generate.py](#phase1_generatepy)
   - [phase2_generate.py](#phase2_generatepy)
6. [Global Mechanics](#global-mechanics)
   - [Answer → Next Filename](#answer--next-filename)
   - [Variable-length Decoy Names](#variable-length-decoy-names)
   - [Fake Headers on Clue Files](#fake-headers-on-clue-files)
   - [Decoy Clone Files](#decoy-clone-files)
   - [Noise File Generation](#noise-file-generation)
7. [Phase 1 — Stage-by-Stage Breakdown](#phase-1--stage-by-stage-breakdown)
8. [Phase 2 — Stage-by-Stage Breakdown](#phase-2--stage-by-stage-breakdown)
9. [Admin Answer Log](#admin-answer-log)
10. [Tunable Constants](#tunable-constants)
11. [Event Day Checklist](#event-day-checklist)
12. [Tools Participants Need](#tools-participants-need)
13. [Frequently Asked Questions](#frequently-asked-questions)

---

## How the Event Works

Teams (2–3 people each) receive an identical copy of a folder tree.
Inside are thousands of randomly named junk files and a small number of
real **clue files**. Each clue contains a puzzle whose answer is the
**filename** (without extension) of the next clue to find.

```
Solve START_HERE.txt → answer "keyboard"
  → find keyboard.<ext> anywhere in the tree → answer "shadow"
  → find shadow.<ext> anywhere in the tree → ...
  → final stage: congratulations message
```

Teams note every filename they visit along the way.
The first team to finish reports **"We got it"** to a volunteer
and hands over their complete list of filenames.
Volunteers verify against the admin answer log.

**No network access is used at any point — the entire event is offline.**

---

## Repository Layout

```
filehunt2/
├── brainfuck_interpreter.py   # Brainfuck interpreter — CLI tool + importable module
├── haystack_generator.py      # Haystack builder — standalone module + CLI
├── phase1_generate.py         # Generates the Phase 1 (beginner) event pack
├── phase2_generate.py         # Generates the Phase 2 (advanced) event pack
└── README.md                  # This file
```

Generated output (git-ignored, never committed):

```
phase1_output/
├── participant_pack/          # Copy this to every team's machine
├── filehunt_phase1.zip        # Distributable zip (participant_pack only)
└── admin_answer_log.txt       # base64-encoded answer key — DO NOT distribute

phase2_output/
├── participant_pack/
├── filehunt_phase2.zip
└── admin_answer_log.txt
```

---

## Requirements

- **Python 3.8+** — standard library only (no pip installs needed)
- **`zip` CLI** — used by phase1_generate.py for the password-protected zip
  (stage 8). Pre-installed on all standard Ubuntu/Debian systems.
- **`exiftool`** — used by phase2_generate.py to embed a clue in JPEG EXIF
  metadata (stage 6). Must be pre-installed on build machines AND event
  machines. Falls back gracefully if missing (appends text after JPEG EOI).

Check availability:
```bash
zip --version
exiftool -ver
```

---

## Quick Start

```bash
# Clone / enter the repo
cd filehunt2

# Generate Phase 1 pack (beginner teams)
python3 phase1_generate.py

# Generate Phase 2 pack (advancing teams)
python3 phase2_generate.py

# Distribute to teams
# → copy  phase1_output/filehunt_phase1.zip  to every team machine
# → KEEP  phase1_output/admin_answer_log.txt  for organizers only

# Decode the admin answer key on the day
base64 -d phase1_output/admin_answer_log.txt
```

Each script is fully self-contained, takes zero arguments, and produces
a complete working pack in a single run.

---

## The Four Scripts

### `brainfuck_interpreter.py`

A correct, complete Brainfuck interpreter.

**As a CLI tool** — this is how participants use it at the event:
```bash
python3 brainfuck_interpreter.py firewall.bf
# prints exactly:  the next file is named oracle
```

**As an importable module** — used internally by `phase2_generate.py`
to *verify* the generated `.bf` file before it is written to disk:
```python
from brainfuck_interpreter import run_brainfuck
output = run_brainfuck(code_string)   # returns str
```

Interpreter spec:
| Feature | Detail |
|---------|--------|
| Tape size | 30,000 cells |
| Cell type | Unsigned byte, wraps 0↔255 |
| `[` / `]` | Pre-computed jump table — O(1) per jump, no rescanning |
| `,` | Reads from `input_str` arg; yields `\0` when exhausted |
| Comments | Any non-operator character is silently ignored |
| CLI output | Raw program output only — no extra prints, no trailing newline added |

---

### `haystack_generator.py`

Builds a folder of numbered decoy files where exactly **one** is real.

**Importable** — called by `phase2_generate.py`:
```python
from haystack_generator import generate_haystack

result = generate_haystack(
    base_dir          = "/path/to/pack",
    word              = "oracle",
    num_decoys        = 3000,
    real_content      = "Congrats! ...",
    index_puzzle_type = "math",   # or "logic"
    seed              = None,
)
# result keys: folder, real_index, real_filename, digit_width, puzzle_text
```

**Standalone CLI**:
```bash
python3 haystack_generator.py <output_dir> <word> <num_decoys>

# example:
python3 haystack_generator.py /tmp/test oracle 3000
```

What it creates:
```
oracle_files/
├── oracle_0000.jpg   ← random junk
├── oracle_0001.dat   ← random junk
...
├── oracle_2454.dat   ← THIS ONE contains real_content (plain text)
...
└── oracle_2999.bin   ← random junk
```

The returned `puzzle_text` is a short math or number-sequence puzzle
(e.g. `5 * 1 = ?`) whose answer is the zero-padded real index, which
the caller writes to a clue file elsewhere in the tree.

**Puzzle types:**
- `"math"` — arithmetic expression: `14 + 32 + 7 = ?`
- `"logic"` — number sequence: `3, 6, 9, 12, ?`

---

### `phase1_generate.py`

Generates the **Phase 1 (beginner)** event pack — 8 stages, ramping
from simple wordplay riddles up to light encoding puzzles.

**Run:**
```bash
python3 phase1_generate.py
```

**Tunable constants at the top of the file:**

| Constant | Default | What it controls |
|----------|---------|-----------------|
| `OUTPUT_DIR` | `"phase1_output"` | Where to write everything |
| `NUM_FOLDERS` | `256` | Decoy folders in the tree |
| `MAX_DEPTH` | `8` | Max folder nesting depth |
| `NUM_NOISE_FILES` | `1024` | Random junk files |
| `MIN_FILE_SIZE` | `256` | Bytes — min junk payload |
| `MAX_FILE_SIZE` | `2048` | Bytes — max junk payload |
| `DECOY_CLONES_PER_CLUE` | `3` | Impostor copies per clue file |
| `SEED` | `None` | Set to an int for reproducible output |

---

### `phase2_generate.py`

Generates the **Phase 2 (advanced)** event pack — 8 stages, every one
requiring a real technical action (no wordplay riddles).
~3–4× bigger haystack than Phase 1.

Imports `generate_haystack` from `haystack_generator.py` and
`run_brainfuck` from `brainfuck_interpreter.py` — both must be in
the same directory.

**Run:**
```bash
python3 phase2_generate.py
```

**Tunable constants:**

| Constant | Default | What it controls |
|----------|---------|-----------------|
| `OUTPUT_DIR` | `"phase2_output"` | Where to write everything |
| `NUM_FOLDERS` | `512` | Decoy folders |
| `MAX_DEPTH` | `16` | Max nesting depth |
| `NUM_NOISE_FILES` | `4500` | Junk files |
| `MIN_FILE_SIZE` | `512` | Bytes — min junk payload |
| `MAX_FILE_SIZE` | `8192` | Bytes — max junk payload |
| `NUM_HAYSTACK` | `3000` | Total oracle_* files |
| `DECOY_CLONES_PER_CLUE` | `3` | Impostor copies per clue |
| `SEED` | `None` | RNG seed |

---

## Global Mechanics

### Answer → Next Filename

The answer to every puzzle is the **stem** (name without extension) of
the next file to find. Files can have *any* extension — `.jpg`, `.mp3`,
`.pdf`, etc. Participants must search by name, not extension:

```bash
find . -name "keyboard.*"
find . -name "shadow.*"
```

### Variable-length Decoy Names

Decoy folders and files use **1-, 2-, or 3-word names** randomly joined
by `_` or `-`:

```
gyat
sus-roblox
npc_fortnite-toilet
simp-nft-sandwich
```

This means single-word clue filenames like `keyboard`, `shadow`, and
`cipher` look identical in structure to many decoys — teams cannot
visually filter by name length.

Word distribution: ~15% 1-word, ~55% 2-word, ~30% 3-word.
Words are drawn from two wordlists of internet slang / meme / pop-culture
terms, listed in full inside each generator script.

### Fake Headers on Clue Files

**Phase 1 (stages 4–8) and Phase 2 (all stages):**
Every clue file carries a random fake magic-byte header before its
plain-text content, and gets the matching file extension:

| Header bytes | Extension | `file` command output |
|---|---|---|
| `\xFF\xD8\xFF\xE0` | `.jpg` | JPEG image data |
| `\x89PNG\r\n\x1a\n` | `.png` | PNG image data |
| `ID3` | `.mp3` | MPEG ADTS, layer III |
| `%PDF-1.4` | `.pdf` | PDF document |

The content is still **plain readable ASCII** after the header.
Participants read it with:
```bash
cat shadow.jpg          # header bytes may look garbled in terminal but text follows
strings shadow.jpg      # cleanest — shows only printable strings
```

**Phase 1 stages 1–3** stay plain `.txt` with no fake header (beginner-friendly).

### Decoy Clone Files

For every real clue file with stem `X`, there are `DECOY_CLONES_PER_CLUE`
(default 3) **impostor copies** scattered in different folders:

```
participant_pack/
├── some_folder/
│   └── password.jpg      ← REAL clue (fake header + readable riddle inside)
├── another_folder/
│   └── password.png      ← junk impostor
├── deep/nested/folder/
│   └── password.dat      ← junk impostor
└── elsewhere/
    └── password.bak      ← junk impostor
```

All four files have the same stem. Only the real one has readable text
inside. Impostors contain random binary garbage.

Teams are warned in `START_HERE.txt`:
> *"Each clue file has 3 impostor copies with the same name but junk inside.
> Only ONE copy of each clue has real text."*

This forces teams to actually read every candidate file, not just find
it by name and assume it's correct.

### Noise File Generation

In addition to decoy clones, `NUM_NOISE_FILES` completely unrelated
junk files are scattered throughout the tree with randomly chosen
LIST1_LIST2-style names and extensions. Content is a random fake
magic-byte header followed by random bytes. These have nothing to do
with any clue — they are pure volume to make searching harder.

---

## Phase 1 — Stage-by-Stage Breakdown

**8 stages.** Stages 1–3: plain text riddles, `.txt`, no encoding.
Stages 4–8: disguised files (fake header + random extension), with decoy clones.

| Stage | File stem | Extension | Mechanic | Answer |
|-------|-----------|-----------|----------|--------|
| 1 | `START_HERE` | `.txt` | Plain riddle: *"I have keys but open no locks..."* | `keyboard` |
| 2 | `keyboard` | `.txt` | Plain riddle: *"I follow you all day but disappear at night..."* | `shadow` |
| 3 | `shadow` | `.txt` | Plain riddle: *"I can be public or private... never reuse me..."* | `password` |
| 4 | `password` | random | Plain riddle (fake header): *"I'm not in the sky... companies charge you monthly..."* | `cloud` |
| 5 | `cloud` | random | Plain riddle (fake header): *"This Marvel villain snapped his fingers..."* | `thanos` |
| 6 | `thanos` | random | ROT13 cipher — ciphertext + inline explanation | `matrix` |
| 7 | `matrix` | random | base64 — encoded string + note | `algorithm` |
| 8 | `algorithm_locked` | `.zip` | Password-protected zip — password = `"password"` (answer to stage 3) | 🏁 Final |

**Stage 6 detail (ROT13):**
The file explains what ROT13 is, gives the decode command, and shows
the ciphertext of `"the next file is named matrix"`.
```
echo 'gur arkg svyr vf anzrq zngevk' | tr 'A-Za-z' 'N-ZA-Mn-za-m'
```

**Stage 7 detail (base64):**
The file says `"This one's base64-encoded."` and shows the encoded form
of `"the next file is named algorithm"`.
```bash
echo 'dGhlIG5leHQgZmlsZSBpcyBuYW1lZCBhbGdvcml0aG0=' | base64 -d
```

**Stage 8 detail (password-protected zip):**
- The zip is created via the system `zip` CLI (Python's zipfile cannot
  set passwords on write).
- The password is `"password"` — the callback answer from stage 3.
  Teams who kept notes will remember it; others must backtrack.
- Inside: `FINAL.txt` with the congratulations message.
- Decoy junk zips with the same filename are placed in other folders.
```bash
unzip -P password algorithm_locked.zip
```

---

## Phase 2 — Stage-by-Stage Breakdown

**8 stages, fully technical.** Every stage requires an actual command-line
action. No wordplay riddles. All clue files carry fake headers.

| Stage | File stem | Extension | Mechanic | Answer |
|-------|-----------|-----------|----------|--------|
| 1 | `START_HERE` | random | Double-cycle cipher: ROT13 → then base64 the result | `cipher` |
| 2 | `cipher` | random | Caesar cipher, unknown shift (1–25). Brute-force all 25. | `breach` |
| 3 | `breach` | random | Number cipher: A=1, B=2 … Z=26, hyphen-separated | `exploit` |
| 4 | `exploit` | `.py` | Fix the bug Python script — off-by-one in `range()` | `payload` |
| 5 | `payload` | `.jpg` | Polyglot file: JPEG magic bytes then plain ASCII text | `quarantine` |
| 6 | `quarantine` | `.jpg` | EXIF metadata: clue in the `Comment` EXIF field | `firewall` |
| 7 | `firewall` | `.bf` | Brainfuck program — run it to get the answer | `oracle` |
| 8 | `oracle_NNNN` | random | 3000-file haystack — solve a math puzzle for the index | 🏁 Final |

---

**Stage 1 (double-cycle cipher):**
```
Plaintext  →  ROT13  →  base64  →  shown in file
```
File only says "more than one decoding step is required."
Teams must figure out the order themselves.
```bash
echo 'Z3VyIGFya2cgc3Z5ciB2ZiBhbnpycSBwdmN1cmU=' | base64 -d | tr 'A-Za-z' 'N-ZA-Mn-za-m'
```

---

**Stage 2 (Caesar, unknown shift):**
The ciphertext is shown with the hint "shifted by an unknown amount,
1 through 25." Teams must try all 25 possible shifts (trivial with a
short script or online tool) and pick the one that makes English sense.
The actual shift used is recorded in the admin log.

---

**Stage 3 (number cipher):**
The word `exploit` is encoded as `5-24-16-12-15-9-20` (A=1…Z=26).
The file shows the number string and the decoding rule.

---

**Stage 4 (fix the bug):**
```python
# BUG: range(1, n) should be range(1, n+1)
def compute_total(n):
    total = 0
    for i in range(1, n):   # off-by-one here
        total += i
    return total

result = compute_total(10)
if result == 55:            # 1+2+…+10 = 55; bug gives 1+…+9 = 45
    print("the next file is named payload")
```
As-is the script prints nothing. Fix the range, run it, get the answer.
The file is a plain `.py` — no fake header (it must be runnable as Python).
Decoy clones with other extensions are still placed.

---

**Stage 5 (polyglot / fake-header file):**
`payload.jpg` starts with real JPEG magic bytes (`\xFF\xD8\xFF\xE0`)
but is immediately followed by plain ASCII text. It will look broken
in an image viewer but `strings` / `cat` reveals the clue.
```bash
strings payload.jpg
# or
cat payload.jpg
```

---

**Stage 6 (EXIF metadata):**
`quarantine.jpg` is a genuine decodable JPEG (1×1 pixel, generated
entirely from stdlib bytes — no Pillow required). The clue is embedded
in the EXIF `Comment` field via `exiftool`.
```bash
exiftool quarantine.jpg | grep Comment
# or
strings quarantine.jpg | grep firewall
```
If `exiftool` is not available at generation time, the script falls back
to appending the clue text after the JPEG's EOI marker (`\xFF\xD9`),
which `strings` still finds. The admin log records which method was used.

---

**Stage 7 (Brainfuck):**
`firewall.bf` is a generated Brainfuck program. The generator
*programmatically verifies* its output using `run_brainfuck()` before
writing the file — if verification fails, generation halts with an error
rather than silently placing a broken puzzle.
```bash
python3 brainfuck_interpreter.py firewall.bf
# output:  the next file is named oracle
```

---

**Stage 8 (haystack):**
A folder named `oracle_files/` contains 3,000 files named
`oracle_0000.<ext>` through `oracle_2999.<ext>`. All but one contain
random binary junk. The one real file contains the final congratulations
message.

Elsewhere in the tree there is an **index clue file** — a randomly
named file (not called "oracle") containing a math puzzle whose answer
is the zero-padded index of the real file, e.g.:

```
Solve this to find the index of the real file.
The answer is a 4-digit number (zero-pad if needed).

  14 + 32 + 7 = ?

The file you want is oracle_0053.<ext> inside the oracle_files folder.
(There are many files — only one is real.)
```

Teams must:
1. Find the index clue (it has a random decoy-style name — no hint)
2. Solve the arithmetic
3. Open `oracle_NNNN.<ext>` in the `oracle_files/` folder

The real oracle file content (the final message):
```
Congrats! You've found everything.
You might've kept track of every riddle and puzzle you've solved so far.
If not, go back and collect all that. Take note of the file names.

Now, tell "We got it" to any of the Volunteers or Organizers,
and hand over the list of file names to them.
```

---

## Admin Answer Log

After generation, each script writes `admin_answer_log.txt` to the
output directory. This file is **base64-encoded** so it's not
immediately human-readable if glanced at.

```
# Phase 1 Admin Answer Log — base64-encoded.
# Decode with:  base64 -d admin_answer_log.txt
# DO NOT share this file with participants!

UEVBU0UgMSAtIEFETUlOIEFOU1dFUiBMT0c...
```

**Decode it:**
```bash
base64 -d phase1_output/admin_answer_log.txt
```

The decoded text lists, for every stage:
- The exact filename and full relative path of the real clue
- The answer / next filename
- For cipher stages: plaintext, ciphertext, and shift/encoding used
- For the password zip: the password
- For the haystack: the real index, real filename, and digit width
- The full paths of all decoy clone impostors

The admin log is **never included** in the participant zip. The
`.gitignore` also blocks it from being committed. A safety-net rule
blocks any file named `admin_answer_log.txt` from being committed
regardless of location.

---

## Tunable Constants

Every number that controls the event size or difficulty is a named
constant at the very top of each generator script.

```python
# phase1_generate.py
NUM_FOLDERS           = 256    # ← increase for a bigger tree
NUM_NOISE_FILES       = 1024   # ← increase for more junk files
MAX_DEPTH             = 8      # ← increase for deeper nesting
DECOY_CLONES_PER_CLUE = 3     # ← increase for more impostor copies
SEED                  = None   # ← set to an int for reproducible packs
```

**To make Phase 1 harder:** increase `NUM_FOLDERS`, `NUM_NOISE_FILES`,
`MAX_DEPTH`, and `DECOY_CLONES_PER_CLUE`.

**For reproducible identical packs:** set `SEED = 42` (or any integer).
Both scripts will produce the same folder structure and file placement
every run. Useful for testing or regenerating after a disk wipe.

---

## Event Day Checklist

```
Before the event
────────────────
[ ] Run python3 phase1_generate.py  (and/or phase2_generate.py)
[ ] Verify admin log decodes correctly:
      base64 -d phase1_output/admin_answer_log.txt | head -40
[ ] Copy filehunt_phase1.zip to a USB / shared drive
[ ] DO NOT copy admin_answer_log.txt anywhere near the participant machines
[ ] Confirm zip, exiftool, python3, and strings are installed on event machines
[ ] Copy brainfuck_interpreter.py to event machines (for phase 2 participants)

At the event
────────────
[ ] Unzip participant pack on each machine:
      unzip filehunt_phase1.zip
[ ] Tell teams: "Start from START_HERE.txt in the root folder"
[ ] Keep the decoded admin log on organizer devices for answer verification

Grading
───────
[ ] Team reports "We got it" → ask for their list of file names (in order)
[ ] Check each name against the admin log
[ ] First correct complete list wins
```

---

## Tools Participants Need

**Phase 1** — all standard Ubuntu tools:

| Tool | Usage |
|------|-------|
| `ls`, `find` | Navigate the tree and locate files by name |
| `cat` | Read clue files (works through fake headers) |
| `strings` | Extract printable text from binary-header files |
| `base64 -d` | Decode stage 7 |
| `tr 'A-Za-z' 'N-ZA-Mn-za-m'` | Decode ROT13 (stage 6) |
| `unzip -P <password>` | Open stage 8 password-protected zip |
| `python3` | Optional — useful for writing brute-force scripts |

**Phase 2** — additionally:

| Tool | Usage |
|------|-------|
| `python3 brainfuck_interpreter.py` | Run stage 7's Brainfuck program |
| `exiftool` | Read EXIF metadata from stage 6's JPEG |
| `python3` | Required — run and fix stage 4's Python script |

---

## Frequently Asked Questions

**Q: Can I run both phases at the same event?**
Yes. Phase 1 is for all beginner teams. Advancing teams (first to finish
Phase 1) can be given the Phase 2 pack as a second challenge.

**Q: Are the packs identical for all teams?**
Yes. Both generators produce a single zip you copy to every machine.
Folder structure, clue locations, and answers are identical across all
copies. Only one pack exists per phase.

**Q: What if a team finds the clue file but can't read it?**
They need `cat` or `strings`. Both are always available on Ubuntu.
Volunteers can hint "try `strings <filename>`" if a team is stuck
on the fake-header mechanic.

**Q: What if `exiftool` isn't available at generation time?**
The generator falls back to appending the clue text after the JPEG's
EOI marker. `strings quarantine.jpg | grep firewall` still finds it.
The admin log records which method was used for that run.

**Q: How does the admin verify a team's answer?**
Decode the admin log: `base64 -d admin_answer_log.txt`.
Each stage lists the exact clue filename. The team's list should contain
those filenames in order. The zip password and haystack real index are
also in the log for verification.

**Q: Can I change the clue texts or answers?**
Yes — they are hardcoded strings in the `main()` function of each
generator. Search for the stage comment (e.g. `# STAGE 6`) and edit
the text and answer string. Remember to also update the log entry for
that stage.

**Q: What is `SEED` for?**
Setting `SEED` to any integer makes the random number generator
deterministic — you get the exact same folder tree, file placements,
and random shifts every time. Useful for testing, debugging, or
regenerating an identical pack after a failure. Leave it as `None`
for a fresh random layout each run.

**Q: How do I make the event harder?**
- Increase `DECOY_CLONES_PER_CLUE` — more impostor copies to sift through
- Increase `NUM_NOISE_FILES` — more raw junk
- Increase `MAX_DEPTH` — deeper folder nesting
- Increase `NUM_FOLDERS` — more total folders to search
- Increase `NUM_HAYSTACK` in Phase 2 — bigger oracle needle-in-haystack

**Q: Why is the admin log base64-encoded?**
So that a quick glance at the file on screen (or in a terminal history)
doesn't accidentally reveal answers. It's a lightweight precaution — not
cryptographic security. Organisers should still keep the file off
participant machines.
