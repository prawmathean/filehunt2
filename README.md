# FileHunt2 — Linux Terminal Puzzle Hunt

A complete offline, in-person **college puzzle event** where teams race to follow a chain of hidden clues buried inside a folder full of thousands of randomly named decoy files. 

Participants must use standard Linux CLI tools (`find`, `grep`, `cat`, `strings`, `base64`, `tr`, `exiftool`) to decode clues, bypass fake file headers, run Brainfuck code, and find the final flag.

---

## 📖 Documentation

To keep this minimal, the full documentation is split into three guides:

1. [**Mechanics & Customization**](docs/MECHANICS.md) — How the game generates decoys, fake headers, and noise, plus how to tune the difficulty.
2. [**Stage Breakdowns**](docs/STAGES.md) — Exact solutions, riddles, and mechanics for all 8 stages of Phase 1 and Phase 2.
3. [**Admin Guide & Checklist**](docs/ADMIN_GUIDE.md) — Event-day checklist, how to decode the admin answer logs, and FAQs.

---

## 🚀 Quick Start (Docker)

The easiest way to distribute the game is using the provided Docker container. It comes pre-loaded with both puzzle phases and all necessary CLI tools, completely isolating the participants.

### 1. Build and push the image (Organizers)
```bash
# Generate the latest random puzzle packs
python3 phase1_generate.py
python3 phase2_generate.py

# Build the Docker image (replace 'yourname' with your Docker Hub username)
sudo docker build -t yourname/filehunt .

# Push to the cloud
sudo docker push yourname/filehunt
```

### 2. Play the game (Participants)
On the day of the event, tell teams to open a terminal and run:
```bash
sudo docker run --rm -it yourname/filehunt
```
They will be dropped directly into a custom, colored bash prompt with both phases ready to explore!

*(Note: If your event has zero internet access, see the [Admin Guide](docs/ADMIN_GUIDE.md) for offline USB Docker distribution).*

---

## 📁 Repository Layout

```text
.
├── phase1_generate.py         # Generates the Beginner Pack
├── phase2_generate.py         # Generates the Technical Pack
├── haystack_generator.py      # Used by Phase 2 for the final haystack stage
├── brainfuck_interpreter.py   # Used by Phase 2 for the esoteric cipher stage
├── Dockerfile                 # Packages the event for participants
├── docs/                      # Extensive guides and documentation
└── setup.sh                   # Legacy script for non-Docker LAN deployments
```
