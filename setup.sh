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

SERVER_IP="172.40.0.143"   # IP of the organiser's machine on the LAN
SERVER_PORT="8888"            # Port python3 -m http.server is listening on

PHASE1_ZIP="filehunt_phase1.zip"   # Filename of the Phase 1 zip on the server
PHASE2_ZIP="filehunt_phase2.zip"   # Filename of the Phase 2 zip on the server

# Folder names inside the respective zip files
PHASE1_FOLDER="filehunt_phase1"
PHASE2_FOLDER="filehunt_phase2"

# Destination folder names on Desktop:
# Phase 1 is visible ("filehunt_phase1")
# Phase 2 is hidden initially (".filehunt_phase2")
PHASE1_DEST="filehunt_phase1"
PHASE2_DEST=".filehunt_phase2"

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
    local extracted_name="$2"  # e.g. filehunt_phase1
    local dest_name="$3"       # e.g. filehunt_phase1 or .filehunt_phase2
    local phase_label="$4"     # e.g. "Phase 1"

    local url="${BASE_URL}/${zip_name}"
    local zip_dest="${DESKTOP}/${zip_name}"
    local extracted="${DESKTOP}/${extracted_name}"
    local final_dest="${DESKTOP}/${dest_name}"

    echo -e "${BOLD}── $phase_label ─────────────────────────${RESET}"

    # Warn and clean up if a previous run left files behind
    if [[ -d "$final_dest" ]]; then
        warn "Destination folder '$final_dest' already exists — removing it first."
        rm -rf "$final_dest"
    fi
    if [[ -d "$extracted" && "$extracted" != "$final_dest" ]]; then
        warn "Stale extracted folder '$extracted' exists — removing it first."
        rm -rf "$extracted"
    fi
    if [[ -f "$zip_dest" ]]; then
        warn "Zip '$zip_dest' already exists — removing it first."
        rm -f "$zip_dest"
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

    # 4. Rename to destination folder if needed (e.g. to hide Phase 2)
    if [[ "$extracted" != "$final_dest" ]]; then
        mv "$extracted" "$final_dest" \
          || die "$phase_label: failed to rename '$extracted' to '$final_dest'."
        success "Renamed → $final_dest (hidden)"
    else
        success "Kept visible at → $final_dest"
    fi

    # Quick sanity check — count the files inside
    local file_count
    file_count=$(find "$final_dest" -type f | wc -l)
    success "$phase_label ready — $file_count files inside '$dest_name'"
    echo ""
}

# =============================================================================
# Run setup for both phases
# =============================================================================

setup_phase "$PHASE1_ZIP" "$PHASE1_FOLDER" "$PHASE1_DEST" "Phase 1"
setup_phase "$PHASE2_ZIP" "$PHASE2_FOLDER" "$PHASE2_DEST" "Phase 2"

# =============================================================================
# Done
# =============================================================================

echo -e "${BOLD}────────────────────────────────────────${RESET}"
echo -e "${GREEN}${BOLD}All done! Both packs are ready.${RESET}"
echo ""
echo -e "  Phase 1 (visible)   →  ${CYAN}${DESKTOP}/${PHASE1_DEST}${RESET}"
echo -e "  Phase 2 (hidden)    →  ${CYAN}${DESKTOP}/${PHASE2_DEST}${RESET}"
echo ""
echo -e "  View hidden files: ${YELLOW}ls -la ~/Desktop${RESET}"
echo -e "  Enter Phase 1:     ${YELLOW}cd ~/Desktop/${PHASE1_DEST} && ls${RESET}"
echo ""
