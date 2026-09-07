# FileHunt2 Mechanics & Customization

## Global Mechanics

### Answer → Next Filename
The core rule of the event: the answer to the current stage's puzzle or riddle is the **filename** (without extension) of the next clue to find.

If the answer is `keyboard`, teams must use `find . -name "keyboard.*"` to locate the file.

### Variable-length Decoy Names
To prevent single-word clue filenames from standing out (e.g., finding `keyboard.txt` in a sea of `red_apple.txt`), all decoy files and folders use 1-, 2-, or 3-word combinations with mixed `_` and `-` separators. Clue files blend seamlessly into the environment.

### Fake Headers on Clue Files
Many clue files prepend standard magic bytes (e.g., JPEG, PNG, MP3, PDF) before the actual plain-text clue. 
Opening `cloud.jpg` in an image viewer will fail, but running `strings cloud.jpg` or `cat cloud.jpg` will reveal the text.

### Decoy Clone Files
For every real clue file (e.g., `keyboard.jpg`), the generator places multiple **impostor clones** (e.g., `keyboard.pdf`, `keyboard.mp3`) in different, randomly chosen folders. 
These impostors contain random binary junk. Participants must check all files matching the name until they find the one with readable text.

### Noise File Generation
The generator produces thousands of noise files (junk files). These are filled with random bytes (via `os.urandom`) ranging from a configurable `MIN_FILE_SIZE` to `MAX_FILE_SIZE`.

---

## Tunable Constants

Every number that controls the event size or difficulty is a named constant at the very top of each generator script.

```python
# phase1_generate.py
OUTPUT_DIR            = "phase1_output"
NUM_FOLDERS           = 256    # ← increase for a bigger tree
NUM_NOISE_FILES       = 1024   # ← increase for more junk files
MAX_DEPTH             = 8      # ← increase for deeper nesting
DECOY_CLONES_PER_CLUE = 3      # ← increase for more impostor copies
SEED                  = None   # ← set to an int for reproducible packs
```

**To make the event harder:** increase `NUM_FOLDERS`, `NUM_NOISE_FILES`, `MAX_DEPTH`, and `DECOY_CLONES_PER_CLUE`.

**For reproducible identical packs:** set `SEED = 42` (or any integer). Both scripts will produce the same folder structure and file placement every run. Useful for testing or regenerating after a disk wipe.
