# =============================================================================
# FileHunt2 — Docker Image
# =============================================================================
# Build:
#   docker build -t filehunt .
#
# Run (interactive terminal):
#   docker run --rm -it filehunt
#
# Save to file (for USB distribution):
#   docker save filehunt | gzip > filehunt.tar.gz
#
# Load on participant machine:
#   docker load < filehunt.tar.gz
#   docker run --rm -it filehunt
# =============================================================================

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# ---------------------------------------------------------------------------
# Install all tools participants need
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    python3 \
    unzip \
    libimage-exiftool-perl \
    binutils \
    nano \
    vim \
    file \
    less \
    grep \
    findutils \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Create a non-root participant user
# ---------------------------------------------------------------------------
RUN useradd -m -s /bin/bash player

# ---------------------------------------------------------------------------
# Copy the Brainfuck interpreter — accessible from anywhere as:
#   python3 /usr/local/bin/brainfuck_interpreter.py <file.bf>
# ---------------------------------------------------------------------------
COPY brainfuck_interpreter.py /usr/local/bin/brainfuck_interpreter.py
RUN chmod +x /usr/local/bin/brainfuck_interpreter.py

# ---------------------------------------------------------------------------
# Copy the generated phase packs
# ---------------------------------------------------------------------------
COPY phase1_output/filehunt_phase1  /home/player/filehunt_phase1
COPY phase2_output/filehunt_phase2  /home/player/.filehunt_phase2

# Copy the participant quick guide
COPY PARTICIPANT_README.md          /home/player/PARTICIPANT_README.md

# ---------------------------------------------------------------------------
# Welcome banner & Custom Prompt (PS1) shown every time the shell opens
# ---------------------------------------------------------------------------
RUN echo ''                                                             >> /home/player/.bashrc \
 && echo 'echo ""'                                                      >> /home/player/.bashrc \
 && echo 'echo "=================================================="'   >> /home/player/.bashrc \
 && echo 'echo "    Welcome to the Linux File Hunt!               "'   >> /home/player/.bashrc \
 && echo 'echo "=================================================="'   >> /home/player/.bashrc \
 && echo 'echo "  Phase 1 folder : ~/filehunt_phase1/             "'   >> /home/player/.bashrc \
 && echo 'echo "  Phase 2 folder : ~/.filehunt_phase2/  (hidden)  "'   >> /home/player/.bashrc \
 && echo 'echo ""'                                                      >> /home/player/.bashrc \
 && echo 'echo "  Quick guide    : cat ~/PARTICIPANT_README.md     "'   >> /home/player/.bashrc \
 && echo 'echo "  Start here     : ls ~/filehunt_phase1/           "'   >> /home/player/.bashrc \
 && echo 'echo "=================================================="'   >> /home/player/.bashrc \
 && echo 'echo ""'                                                      >> /home/player/.bashrc \
 && echo "export PS1='\[\033[1;36m\][FileHunt2]\[\033[0m\] \[\033[1;32m\]player0\[\033[0m\]:\[\033[1;33m\]\w\[\033[0m\]$ '" >> /home/player/.bashrc

# ---------------------------------------------------------------------------
# Fix ownership of everything in home
# ---------------------------------------------------------------------------
RUN chown -R player:player /home/player

# ---------------------------------------------------------------------------
# Drop into /home/player as the participant user
# ---------------------------------------------------------------------------
WORKDIR /home/player
USER player

CMD ["/bin/bash"]
