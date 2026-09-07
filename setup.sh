#!/usr/bin/env bash
# =============================================================================
# setup.sh  —  FileHunt2 Event Setup Script
# =============================================================================
#
# Run on each participant machine with:
#
#   curl http://<YOUR_IP>:<PORT>/setup.sh | bash
#
# What this script does:
#   1. Downloads both phase zip files from the organiser's local web server
#   2. Extracts them onto the Desktop
#   3. Deletes the zip files
#   4. Renames the extracted folders to hidden dot-folders
#
# Serve this script + the zips from one terminal on the organiser's machine:
#
#   cd /path/to/your/generated/output    # folder that contains both *.zip files
#   python3 -m http.server 5566
#
# =============================================================================
# CONFIGURATION — edit these before the event if anything changes
# =============================================================================

SERVER_IP="192.168.29.202"   # IP of the organiser's machine on the LAN
SERVER_PORT="5566"            # Port python3 -m http.server is listening on

PHASE1_ZIP="filehunt_phase1.zip"   # Filename of the Phase 1 zip on the server
PHASE2_ZIP="filehunt_phase2.zip"   # Filename of the Phase 2 zip on the server

# The top-level folder name that the zip extracts into (don't change unless
# you rename participant_pack inside the zip generator scripts).
EXTRACTED_FOLDER="participant_pack"

# What to call the hidden folders on the Desktop after renaming.
# Leading dot makes them hidden from GUI file managers and plain `ls`.
PHASE1_HIDDEN=".filehunt_phase1"
PHASE2_HIDDEN=".filehunt_phase2"

# Where to put everything. $HOME/Desktop works on standard Ubuntu.
DESKTOP="$HOME/Desktop"

# =============================================================================
# Helpers
# =============================================================================

# Colours (fall back gracefully if the terminal doesn't support them)
RED='\033[0;31m';  GREEN='\033[0;32m'
YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
die()     { echo -e "${RED}[ERROR]${RESET} $*" >&2; exit 1; }

BASE_URL="http://${SERVER_IP}:${SERVER_PORT}"

# =============================================================================
# Pre-flight checks
# =============================================================================

echo -e "\n${BOLD}FileHunt2 — Event Setup${RESET}"
echo    "────────────────────────────────────────"
info "Server : $BASE_URL"
info "Desktop: $DESKTOP"
echo ""

# Ensure the Desktop folder exists
if [[ ! -d "$DESKTOP" ]]; then
    warn "Desktop folder not found at '$DESKTOP' — creating it."
    mkdir -p "$DESKTOP" || die "Cannot create '$DESKTOP'."
fi

# Check that a download tool is available
if command -v curl &>/dev/null; then
    DOWNLOADER="curl"
elif command -v wget &>/dev/null; then
    DOWNLOADER="wget"
else
    die "Neither curl nor wget is installed. Cannot download files."
fi
info "Using downloader: $DOWNLOADER"

# Check that unzip is available
command -v unzip &>/dev/null || die "unzip is not installed. Run: sudo apt install unzip"

# ---------------------------------------------------------------------------
# Install exiftool if missing  (required by Phase 2 participants)
# ---------------------------------------------------------------------------
if ! command -v exiftool &>/dev/null; then
    info "exiftool not found — installing via apt ..."
    sudo apt-get install -y libimage-exiftool-perl &>/dev/null \
      && success "exiftool installed." \
      || warn "Could not install exiftool automatically. Run: sudo apt install libimage-exiftool-perl"
else
    success "exiftool already installed ($(exiftool -ver))."
fi

echo ""

# =============================================================================
# Download helper — works with either curl or wget
# =============================================================================

download() {
    local url="$1"
    local dest="$2"
    info "Downloading $(basename "$dest") ..."
    if [[ "$DOWNLOADER" == "curl" ]]; then
        curl --fail --silent --show-error --progress-bar \
             --output "$dest" "$url" \
          || die "Download failed: $url"
    else
        wget --quiet --show-progress \
             --output-document="$dest" "$url" \
          || die "Download failed: $url"
    fi
    success "Downloaded $(basename "$dest")  ($(du -sh "$dest" | cut -f1))"
}

# =============================================================================
# Setup helper — download → extract → delete zip → rename to hidden folder
# =============================================================================

setup_phase() {
    local zip_name="$1"        # e.g. filehunt_phase1.zip
    local hidden_name="$2"     # e.g. .filehunt_phase1
    local phase_label="$3"     # e.g. "Phase 1"

    local url="${BASE_URL}/${zip_name}"
    local zip_dest="${DESKTOP}/${zip_name}"
    local extracted="${DESKTOP}/${EXTRACTED_FOLDER}"
    local final_dest="${DESKTOP}/${hidden_name}"

    echo -e "${BOLD}── $phase_label ─────────────────────────${RESET}"

    # Warn and clean up if a previous run left files behind
    if [[ -d "$final_dest" ]]; then
        warn "Hidden folder '$final_dest' already exists — removing it first."
        rm -rf "$final_dest"
    fi
    if [[ -f "$zip_dest" ]]; then
        warn "Zip '$zip_dest' already exists — removing it first."
        rm -f "$zip_dest"
    fi
    # The extraction landing zone (shared name from the zip) might also be stale
    if [[ -d "$extracted" ]]; then
        warn "Extraction folder '$extracted' already exists — removing it first."
        rm -rf "$extracted"
    fi

    # 1. Download
    download "$url" "$zip_dest"

    # 2. Extract to Desktop
    info "Extracting to Desktop ..."
    unzip -q "$zip_dest" -d "$DESKTOP" \
      || die "$phase_label: unzip failed on '$zip_dest'."

    # Confirm the expected folder appeared
    if [[ ! -d "$extracted" ]]; then
        die "$phase_label: expected folder '$extracted' not found after extraction."
    fi
    success "Extracted → $extracted"

    # 3. Delete the zip (keeps Desktop clean)
    rm -f "$zip_dest"
    success "Deleted zip file."

    # 4. Rename to a hidden dot-folder
    mv "$extracted" "$final_dest" \
      || die "$phase_label: failed to rename '$extracted' to '$final_dest'."
    success "Renamed → $final_dest  (hidden)"

    # Quick sanity check — count the files inside
    local file_count
    file_count=$(find "$final_dest" -type f | wc -l)
    success "$phase_label ready — $file_count files inside '$hidden_name'"
    echo ""
}

# =============================================================================
# Run setup for both phases
# =============================================================================

setup_phase "$PHASE1_ZIP" "$PHASE1_HIDDEN" "Phase 1"
setup_phase "$PHASE2_ZIP" "$PHASE2_HIDDEN" "Phase 2"

# =============================================================================
# Done
# =============================================================================

echo -e "${BOLD}────────────────────────────────────────${RESET}"
echo -e "${GREEN}${BOLD}All done! Both packs are ready.${RESET}"
echo ""
echo -e "  Phase 1 (beginner)  →  ${CYAN}${DESKTOP}/${PHASE1_HIDDEN}${RESET}"
echo -e "  Phase 2 (advanced)  →  ${CYAN}${DESKTOP}/${PHASE2_HIDDEN}${RESET}"
echo ""
echo -e "  Reveal with:  ${YELLOW}ls -la ~/Desktop${RESET}"
echo -e "  Enter Phase 1: ${YELLOW}cd ~/Desktop/${PHASE1_HIDDEN} && ls${RESET}"
echo ""
