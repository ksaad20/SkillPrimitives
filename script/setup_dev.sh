#!/usr/bin/env bash
# =============================================================================
# setup_dev.sh — One-command dev environment bootstrap
# =============================================================================
# Usage: ./scripts/setup_dev.sh
# Sets up the full development environment for skills-primitive zoo development.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── Step 1: Check prerequisites ──────────────────────────────────────────────
log_info "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || { log_error "python3 is required but not installed."; exit 1; }
command -v node >/dev/null 2>&1 || { log_error "Node.js is required but not installed."; exit 1; }
command -v npm >/dev/null 2>&1 || { log_error "npm is required but not installed."; exit 1; }
command -v git >/dev/null 2>&1 || { log_error "git is required but not installed."; exit 1; }

PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
log_ok "Python ${PY_VER} found"
log_ok "Node $(node --version) found"
log_ok "npm $(npm --version) found"
log_ok "git found"

# ── Step 2: Create Python virtual environment ────────────────────────────────
log_info "Setting up Python virtual environment..."
if [ -d "${VENV_DIR}" ]; then
    log_warn "Virtual environment already exists at ${VENV_DIR}"
else
    python3 -m venv "${VENV_DIR}"
    log_ok "Created virtual environment"
fi

# ── Step 3: Install Python dependencies ──────────────────────────────────────
log_info "Installing Python dependencies..."
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip setuptools wheel

if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
    pip install -r "${PROJECT_ROOT}/requirements.txt"
    log_ok "Installed requirements.txt"
else
    log_warn "No requirements.txt found — installing core deps only"
    pip install pillow numpy pyyaml jinja2 requests rich click
fi

# ── Step 4: Install Node dependencies ────────────────────────────────────────
log_info "Installing Node dependencies..."
cd "${PROJECT_ROOT}"
if [ -f "package.json" ]; then
    npm install
    log_ok "Installed npm packages"
else
    log_warn "No package.json found — skipping npm install"
fi

# ── Step 5: Create local config if missing ───────────────────────────────────
log_info "Checking local configuration..."
if [ ! -f "${PROJECT_ROOT}/.env.local" ]; then
    cat > "${PROJECT_ROOT}/.env.local" << 'EOF'
# Local development overrides
# Copy to .env and fill in your values
ZOO_OUTPUT_DIR=./zoo
BENCHMARK_TIMEOUT=30
GIF_FPS=30
GIF_DURATION=3
TWITTER_CARD_WIDTH=1200
TWITTER_CARD_HEIGHT=675
EOF
    log_ok "Created .env.local template"
fi

# ── Step 6: Pre-commit hooks (optional) ──────────────────────────────────────
if [ -d "${PROJECT_ROOT}/.git" ]; then
    log_info "Setting up git hooks..."
    if command -v pre-commit >/dev/null 2>&1; then
        pre-commit install
        log_ok "pre-commit hooks installed"
    else
        log_warn "pre-commit not installed — skipping hooks"
    fi
fi

# ── Step 7: Validate setup ───────────────────────────────────────────────────
log_info "Validating setup..."
python3 -c "import yaml, jinja2, PIL, rich; print('Core imports OK')" || {
    log_error "Python imports failed. Check your virtual environment."
    exit 1
}

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🎉  Dev environment ready!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
log_info "Quick start:"
echo "  source .venv/bin/activate"
echo "  ./scripts/build_zoo.py --help"
echo "  ./scripts/generate_gifs.py --all"
echo ""
