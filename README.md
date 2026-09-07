# FileHunt2 — Linux Terminal Puzzle Hunt

A complete offline, in-person **college puzzle event** where teams race to follow a chain of hidden clues buried inside a folder full of thousands of randomly named decoy files. 

Participants must use standard Linux CLI tools (`find`, `grep`, `cat`, `strings`, `base64`, `tr`, `exiftool`) to decode clues, bypass fake file headers, run Brainfuck code, and find the final flag.

---


## 🚀 Quick Start (Docker)

The recommended way to run and distribute the challenge is using Docker. It provides a complete, isolated Linux environment with all puzzle phases and tools pre-configured.

> **Requirements:** A Linux machine (Ubuntu, Debian, Arch, Fedora, etc.) with Docker installed.

### Installing Docker (if needed)

- **Ubuntu / Debian:**
  ```bash
  sudo apt update && sudo apt install -y docker.io
  sudo systemctl enable --now docker
  ```

- **Arch Linux:**
  ```bash
  sudo pacman -S docker
  sudo systemctl enable --now docker
  ```

- **Fedora:**
  ```bash
  sudo dnf install -y docker
  sudo systemctl enable --now docker
  ```

*(Optional: Run `sudo usermod -aG docker $USER` and log back in to use `docker` without `sudo`)*

### 1. To try it (Run the docker instance) : 
Open a terminal on your Linux machine and run:
```bash
sudo docker run --rm -it praw56/filehunt
```
Docker will pull the image and drop you directly into an interactive bash shell with the puzzle packs ready.

---

### 2. How to Build it yourselves
If you want to regenerate packs with fresh seeds _(generate the files all by yourself)_

```bash
python3 phase1_generate.py
python3 phase2_generate.py
```

---

## 📁 Repository Layout

```text
.
├── phase1_generate.py         # Generates the Beginner Pack
├── phase2_generate.py         # Generates the Technical Pack
├── haystack_generator.py      # Used by Phase 2 for the final haystack stage
├── brainfuck_interpreter.py   # Used by Phase 2 for the esoteric cipher stage
├── Dockerfile                 # Packages the event for participants
├── docs/                      # Detailed documentation
└── setup.sh                   # Script for non-Docker LAN deployments
```

---
## 📖 Documentation

To keep things organized and minimal, the full documentation is split into three guides:

1. [**Mechanics & Customization**](docs/MECHANICS.md) — How the game generates decoys, fake headers, and noise, plus how to tune the difficulty.
2. [**Stage Breakdowns**](docs/STAGES.md) — Exact solutions, riddles, and mechanics for all 8 stages of Phase 1 and Phase 2.
3. [**Admin Guide & Checklist**](docs/ADMIN_GUIDE.md) — Event-day checklist, how to decode the admin answer logs, and FAQs.

---

## ☕ Support the Developer

If you find this project fun or useful for your events, consider supporting the dev:

- [prajwal-56.github.io](https://prajwal-56.github.io/donate)
