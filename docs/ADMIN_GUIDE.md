# Admin Guide & Event Checklist

## The Admin Answer Log
After generation, each script writes `admin_answer_log.txt` to the output directory. This file is **base64-encoded** so it's not immediately human-readable if glanced at (a lightweight precaution against shoulder-surfing).

**Decode it on the day of the event:**
```bash
base64 -d phase1_output/admin_answer_log.txt
```

The decoded text lists, for every stage:
- The exact filename and full relative path of the real clue
- The answer (which is the next filename)
- For cipher stages: the plaintext, ciphertext, and shift used
- For the password zip: the required password
- For the haystack: the real index, filename, and digit width
- The full paths of all decoy impostors

> **⚠️ CRITICAL:** The admin log is **never included** in the participant zip or Docker image. Do not accidentally copy it to participant machines.

---

## Event Day Checklist (Docker Setup)

```
Before the event
────────────────
[ ] Run python3 phase1_generate.py
[ ] Run python3 phase2_generate.py
[ ] Verify admin log decodes correctly: base64 -d phase1_output/admin_answer_log.txt | head -40
[ ] Build the Docker image: sudo docker build -t yourname/filehunt .
[ ] Push to Docker Hub: sudo docker push yourname/filehunt
[ ] (Optional Offline Method) Export to USB: sudo docker save yourname/filehunt | gzip > filehunt.tar.gz

At the event
────────────
[ ] Ensure all participant machines have Docker installed.
[ ] Have teams pull/run the image: sudo docker run --rm -it yourname/filehunt
[ ] Tell teams: "Start by looking for START_HERE.txt"
[ ] Keep the decoded admin logs securely on organizer devices.

Grading
───────
[ ] When a team reports "We got it", ask for their list of puzzle answers/filenames.
[ ] Check each name against the admin log.
[ ] First correct complete list wins!
```

---

## Tools Participants Need

**Phase 1** — Standard Ubuntu tools (pre-installed in Docker):
* `ls`, `find` (Navigate the tree)
* `cat`, `less` (Read clue files)
* `strings` (Extract printable text from binary-header files)
* `base64 -d` (Decode stage 7)
* `tr 'A-Za-z' 'N-ZA-Mn-za-m'` (Decode ROT13 in stage 6)
* `unzip` (Open stage 8 password-protected zip)

**Phase 2** — Advanced tools (pre-installed in Docker):
* `python3 brainfuck_interpreter.py` (Run stage 7)
* `exiftool` (Read EXIF metadata from stages 5 and 6)
* `python3`, `nano`, `vim` (Edit and run stage 4's Python script)

---

## Frequently Asked Questions

**Q: Are the packs identical for all teams?**  
Yes. Both generators produce a single environment. Folder structure, clue locations, and answers are identical across all copies so the race is perfectly fair.

**Q: What if a team finds the clue file but can't read it?**  
They need `cat` or `strings`. Both are available. Volunteers can hint "try `strings <filename>`" if a team is stuck on the fake-header mechanic.

**Q: How does the admin verify a team's answer?**  
Decode the admin log. The team's final submission should be a list of the answers to the riddles (which double as the filenames of the stages).

**Q: Can I change the clue texts or answers?**  
Yes — they are hardcoded strings in the `main()` function of each generator. Remember to update the answers to match the riddles you write!
