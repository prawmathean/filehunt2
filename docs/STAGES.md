# Phase 1 & Phase 2 — Stage Breakdowns

## Phase 1 — Beginner Pack (8 Stages)

Designed to introduce teams to the Linux terminal, `find`, `cat`, and basic decoding. 

Stages 1–3 are plain `.txt` files containing riddles.  
Stages 4–8 use **disguised files** (fake binary headers + random extensions) and introduce **decoy clones** (multiple fake files with the same name).

| Stage | File stem | Mechanic | Puzzle | Answer |
|-------|-----------|----------|--------|--------|
| 1 | `START_HERE` | Plain `.txt` | Riddle: *"I have keys but open no locks..."* | `keyboard` |
| 2 | `keyboard` | Plain `.txt` | Riddle: *"I follow you all day but disappear at night..."* | `shadow` |
| 3 | `shadow` | Plain `.txt` | Riddle: *"I can be public or private... never reuse me..."* | `password` |
| 4 | `password` | Fake header | Riddle: *"I'm not in the sky... companies charge you monthly..."* | `cloud` |
| 5 | `cloud` | Fake header | Riddle: *"This Marvel villain snapped his fingers..."* | `thanos` |
| 6 | `thanos` | Fake header | **ROT13**: The matrix riddle is encrypted in ROT13. | `matrix` |
| 7 | `matrix` | Fake header | **Base64**: The algorithm riddle is Base64 encoded. | `algorithm` |
| 8 | `algorithm_locked` | Password Zip | **Zip file**: Requires the answer to Stage 3 (`password`) to unzip. Contains the final flag! | 🏁 Final |

---

## Phase 2 — Technical Pack (8 Stages)

Designed for advancing teams. Requires scripting, brute-forcing, debugging, and command-line forensics. **All files** use fake headers and decoy clones.

| Stage | File stem | Mechanic | Answer |
|-------|-----------|----------|--------|
| 1 | `START_HERE` | **Double Cipher**: The riddle is encrypted with ROT13, and the result is encoded in Base64. | `cipher` |
| 2 | `cipher` | **Caesar Cipher (Unknown Shift)**: The riddle is shifted (1–25). Teams must brute-force the shift to read it. | `breach` |
| 3 | `breach` | **Number Cipher**: A=1...Z=26 formatting for the riddle. | `exploit` |
| 4 | `exploit` | **Fix the Bug**: A `.py` script with an off-by-one error in a `range()`. Once fixed, it prints the payload riddle. | `payload` |
| 5 | `payload` | **EXIF Forensics (Real Image)**: The image (`geeks.jpg`) is a real photo. The riddle is hidden in the `ImageDescription` EXIF tag. | `quarantine` |
| 6 | `quarantine` | **EXIF Forensics (Fake Image)**: The riddle is embedded in the EXIF `Comment` field using `exiftool`. | `firewall` |
| 7 | `firewall` | **Brainfuck**: The file is a working `.bf` script. Run it using the provided interpreter to get the oracle riddle. | `oracle` |
| 8 | `oracle_NNNN` | **Haystack Math**: 3,000 files exist in `oracle_files/`. Teams must find the index clue file somewhere else, solve the math equation, and open the right `oracle_NNNN` file to win. | 🏁 Final |
