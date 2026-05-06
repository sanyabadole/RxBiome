#!/usr/bin/env bash
# =============================================================================
#  RxBiome — Quick Setup Script
#  Checks prerequisites, downloads sample data and reference databases,
#  and verifies everything is ready before your first pipeline run.
#
#  Usage: bash quick_setup.sh [--skip-databases] [--skip-samples] [--help]
# =============================================================================

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
ok()      { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
header()  { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${RESET}"; \
            echo -e "${BOLD}${CYAN}  $*${RESET}"; \
            echo -e "${BOLD}${CYAN}══════════════════════════════════════════${RESET}"; }

# ── Argument parsing ──────────────────────────────────────────────────────────
SKIP_DATABASES=false
SKIP_SAMPLES=false

for arg in "$@"; do
  case $arg in
    --skip-databases) SKIP_DATABASES=true ;;
    --skip-samples)   SKIP_SAMPLES=true ;;
    --help|-h)
      echo "Usage: bash quick_setup.sh [--skip-databases] [--skip-samples]"
      echo ""
      echo "  --skip-databases   Skip downloading reference databases (Kraken2, MetaPhlAn, KneadData)"
      echo "  --skip-samples     Skip downloading example FASTQ files"
      exit 0
      ;;
  esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
ERRORS=0

require() {
  local cmd="$1" msg="${2:-}"
  if command -v "$cmd" &>/dev/null; then
    ok "$cmd found → $(command -v "$cmd")"
  else
    error "$cmd not found. ${msg}"
    ERRORS=$(( ERRORS + 1 ))
  fi
}

check_version() {
  local label="$1" actual="$2" required="$3"
  if [[ "$(printf '%s\n' "$required" "$actual" | sort -V | head -1)" == "$required" ]]; then
    ok "$label version $actual (≥ $required required)"
  else
    warn "$label version $actual is below recommended $required"
  fi
}

download_if_missing() {
  local url="$1" dest="$2"
  if [[ -f "$dest" ]]; then
    ok "Already exists: $dest"
  else
    info "Downloading $(basename "$dest") …"
    wget --quiet --show-progress -O "$dest" "$url" || \
      curl -L --progress-bar -o "$dest" "$url"
  fi
}

# =============================================================================
header "1 / 5 — Checking Prerequisites"
# =============================================================================

# Nextflow
require nextflow "Install via: curl -s https://get.nextflow.io | bash && sudo mv nextflow /usr/local/bin/"
if command -v nextflow &>/dev/null; then
  NF_VER=$(nextflow -version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  check_version "Nextflow" "$NF_VER" "23.04.0"
fi

# Java
require java "Nextflow bundles Java — re-install Nextflow or install Java 17+ manually."
if command -v java &>/dev/null; then
  JAVA_VER=$(java -version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
  ok "Java version: $JAVA_VER"
fi

# Docker
require docker "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
if command -v docker &>/dev/null; then
  if docker info &>/dev/null 2>&1; then
    ok "Docker daemon is running"
    DOCKER_MEM=$(docker info 2>/dev/null | grep -i 'total memory' | grep -oE '[0-9]+(\.[0-9]+)? GiB' || echo "unknown")
    info "Docker memory available: $DOCKER_MEM"
    if [[ "$DOCKER_MEM" != "unknown" ]]; then
      MEM_GB=$(echo "$DOCKER_MEM" | grep -oE '[0-9]+(\.[0-9]+)?')
      if (( $(echo "$MEM_GB < 6" | bc -l 2>/dev/null || echo 0) )); then
        warn "Docker has less than 6 GB RAM. Go to Docker Desktop → Settings → Resources and increase memory."
      fi
    fi
  else
    error "Docker is installed but not running. Start Docker Desktop first."
    ERRORS=$(( ERRORS + 1 ))
  fi
fi

# wget or curl
if command -v wget &>/dev/null; then
  ok "wget found"
elif command -v curl &>/dev/null; then
  ok "curl found (wget preferred for database downloads)"
else
  error "Neither wget nor curl found. Install one to download databases."
  ERRORS=$(( ERRORS + 1 ))
fi

# Python (optional)
if command -v python3 &>/dev/null; then
  PY_VER=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
  ok "python3 $PY_VER (optional — only needed for SMILES pre-resolution)"
else
  warn "python3 not found — needed only for local SMILES pre-resolution (bin/drug_smiles_lookup.py)"
fi

if [[ $ERRORS -gt 0 ]]; then
  echo ""
  error "$ERRORS prerequisite(s) missing. Fix the above issues and re-run this script."
  exit 1
fi

ok "All required prerequisites satisfied."

# =============================================================================
header "2 / 5 — Verifying Pipeline Directory"
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "$SCRIPT_DIR/main.nf" ]]; then
  error "main.nf not found in $SCRIPT_DIR — run this script from the rxbiome/ directory."
  exit 1
fi
ok "Pipeline directory: $SCRIPT_DIR"

cd "$SCRIPT_DIR"

# =============================================================================
header "3 / 5 — Downloading Example Sample Data"
# =============================================================================

if [[ "$SKIP_SAMPLES" == true ]]; then
  warn "Skipping sample data download (--skip-samples)"
else
  info "Downloading SRR413665 + SRR413666 paired-end gut metagenomes from ENA …"
  info "Total size: ~2 GB. This may take a few minutes."
  mkdir -p raw_data

  download_if_missing \
    "https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR413/SRR413665/SRR413665_1.fastq.gz" \
    "raw_data/SRR413665_1.fastq.gz"

  download_if_missing \
    "https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR413/SRR413665/SRR413665_2.fastq.gz" \
    "raw_data/SRR413665_2.fastq.gz"

  download_if_missing \
    "https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR413/SRR413666/SRR413666_1.fastq.gz" \
    "raw_data/SRR413666_1.fastq.gz"

  download_if_missing \
    "https://ftp.sra.ebi.ac.uk/vol1/fastq/SRR413/SRR413666/SRR413666_2.fastq.gz" \
    "raw_data/SRR413666_2.fastq.gz"

  ok "Sample FASTQ files ready in raw_data/"

  # Write samplesheet if it doesn't already exist
  if [[ ! -f "samplesheet.csv" ]]; then
    info "Writing samplesheet.csv …"
    cat > samplesheet.csv << 'EOF'
sample,fastq_1,fastq_2
SRR413665,raw_data/SRR413665_1.fastq.gz,raw_data/SRR413665_2.fastq.gz
SRR413666,raw_data/SRR413666_1.fastq.gz,raw_data/SRR413666_2.fastq.gz
EOF
    ok "samplesheet.csv written"
  else
    ok "samplesheet.csv already exists — not overwritten"
  fi
fi

# =============================================================================
header "4 / 5 — Downloading Reference Databases"
# =============================================================================

if [[ "$SKIP_DATABASES" == true ]]; then
  warn "Skipping database downloads (--skip-databases)"
else
  info "Database downloads require ~17 GB of disk space and may take 30–60 minutes."
  info "You can skip this step and provide your own paths via --kraken2_db etc."
  echo ""

  # ── Kraken2 ──────────────────────────────────────────────────────────────
  info "── Kraken2 Standard 8 GB index ──"
  mkdir -p databases/kraken2

  K2_TARBALL="databases/kraken2/k2_standard_08gb_20240112.tar.gz"
  K2_MARKER="databases/kraken2/hash.k2d"

  if [[ -f "$K2_MARKER" ]]; then
    ok "Kraken2 database already present (databases/kraken2/)"
  else
    download_if_missing \
      "https://genome-idx.s3.amazonaws.com/kraken/k2_standard_08gb_20240112.tar.gz" \
      "$K2_TARBALL"
    info "Extracting Kraken2 database …"
    tar -xzf "$K2_TARBALL" -C databases/kraken2
    rm -f "$K2_TARBALL"
    ok "Kraken2 database ready → databases/kraken2/"
  fi

  # ── MetaPhlAn 4 ──────────────────────────────────────────────────────────
  info "── MetaPhlAn 4 database ──"
  mkdir -p databases/metaphlan

  MPA_MARKER="databases/metaphlan/mpa_vJan25_CHOCOPhlAnSGB_202503.pkl"
  MPA_TARBALL="databases/metaphlan/mpa_vJan25_CHOCOPhlAnSGB_202503.tar"

  if [[ -f "$MPA_MARKER" ]]; then
    ok "MetaPhlAn database already present (databases/metaphlan/)"
  else
    download_if_missing \
      "http://cmprod1.cibio.unitn.it/biobakery4/metaphlan_databases/mpa_vJan25_CHOCOPhlAnSGB_202503.tar" \
      "$MPA_TARBALL"
    info "Extracting MetaPhlAn database …"
    tar -xf "$MPA_TARBALL" -C databases/metaphlan
    rm -f "$MPA_TARBALL"
    # Create mpa_latest symlink so MetaPhlAn can auto-detect the index
    ln -sf mpa_vJan25_CHOCOPhlAnSGB_202503 databases/metaphlan/mpa_latest 2>/dev/null || true
    ok "MetaPhlAn 4 database ready → databases/metaphlan/"
  fi

  # ── KneadData host database ───────────────────────────────────────────────
  info "── KneadData human host database (hg37dec_v0.1) ──"
  mkdir -p databases/kneaddata_human

  KD_MARKER="databases/kneaddata_human/hg37dec_v0.1.1.bt2"

  if [[ -f "$KD_MARKER" ]]; then
    ok "KneadData host database already present (databases/kneaddata_human/)"
  else
    info "Downloading 6 Bowtie2 index files (~4 GB total) …"
    KD_BASE="https://huttenhower.sph.harvard.edu/kneaddata_databases/Homo_sapiens_hg37_and_Human_herpesvirus_5_Bowtie2_v0.1_Huttenhower"
    for suffix in 1 2 3 4 rev.1 rev.2; do
      download_if_missing \
        "${KD_BASE}/hg37dec_v0.1.${suffix}.bt2" \
        "databases/kneaddata_human/hg37dec_v0.1.${suffix}.bt2"
    done
    ok "KneadData host database ready → databases/kneaddata_human/"
  fi
fi

# =============================================================================
header "5 / 5 — Final Verification"
# =============================================================================

READY=true

# Check databases
for db_dir in databases/kraken2 databases/metaphlan databases/kneaddata_human; do
  if [[ -d "$db_dir" && "$(ls -A "$db_dir" 2>/dev/null)" ]]; then
    ok "$db_dir — present"
  else
    warn "$db_dir — missing or empty (run without --skip-databases to download)"
    READY=false
  fi
done

# Check sample data
if [[ -f "raw_data/SRR413665_1.fastq.gz" && -f "raw_data/SRR413666_1.fastq.gz" ]]; then
  ok "raw_data/ — FASTQ files present"
else
  warn "raw_data/ — sample FASTQ files not found (run without --skip-samples to download)"
  READY=false
fi

# Check samplesheet
if [[ -f "samplesheet.csv" ]]; then
  ok "samplesheet.csv — present"
else
  warn "samplesheet.csv — not found (will be created automatically if samples are downloaded)"
  READY=false
fi

echo ""
if [[ "$READY" == true ]]; then
  echo -e "${GREEN}${BOLD}✔  Setup complete! You are ready to run the pipeline.${RESET}"
  echo ""
  echo -e "${BOLD}Run with host decontamination:${RESET}"
  echo "  nextflow run main.nf \\"
  echo "    -profile local,docker \\"
  echo "    --input samplesheet.csv \\"
  echo "    --drugs tests/drug_library_test.csv \\"
  echo "    --kraken2_db databases/kraken2 \\"
  echo "    --metaphlan4_db databases/metaphlan \\"
  echo "    --metaphlan4_index mpa_vJan25_CHOCOPhlAnSGB_202503 \\"
  echo "    --host_db databases/kneaddata_human \\"
  echo "    --host_bowtie2_prefix hg37dec_v0.1 \\"
  echo "    --outdir results/ \\"
  echo "    --max_cpus 4 --max_memory 10.GB"
  echo ""
  echo -e "${BOLD}Run without host decontamination (faster):${RESET}"
  echo "  nextflow run main.nf \\"
  echo "    -profile local,docker \\"
  echo "    --input samplesheet.csv \\"
  echo "    --drugs tests/drug_library_test.csv \\"
  echo "    --kraken2_db databases/kraken2 \\"
  echo "    --metaphlan4_db databases/metaphlan \\"
  echo "    --metaphlan4_index mpa_vJan25_CHOCOPhlAnSGB_202503 \\"
  echo "    --skip_host_decontamination true \\"
  echo "    --outdir results/ \\"
  echo "    --max_cpus 4 --max_memory 10.GB"
else
  echo -e "${YELLOW}${BOLD}⚠  Setup incomplete — see warnings above.${RESET}"
  echo "   Re-run this script after resolving the warnings, or provide your own paths."
fi

echo ""
echo -e "${CYAN}Full documentation: https://sanyabadole.github.io/RxBiome/${RESET}"
