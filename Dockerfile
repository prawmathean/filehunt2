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
# Install all tools participants need + networking & utilities
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    unzip \
    libimage-exiftool-perl \
    binutils \
    nano \
    vim \
    file \
    less \
    grep \
    findutils \
    sudo \
    iproute2 \
    net-tools \
    iputils-ping \
    curl \
    wget \
    dnsutils \
    tree \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Create player user with passwordless sudo rights
# ---------------------------------------------------------------------------
RUN useradd -m -s /bin/bash player \
    && usermod -aG sudo player \
    && echo "player ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

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
 && echo "export PS1='\[\033[1;32m\]player@filehunt\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]\$ '" >> /home/player/.bashrc

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
