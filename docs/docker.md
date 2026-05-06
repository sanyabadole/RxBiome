# Docker Images

RxBiome uses a combination of community-maintained BioContainers images and two custom images maintained in the `docker/` directory.

## Custom Images

### `docker/kraken2/` — Patched Kraken2

| Field | Value |
|-------|-------|
| Base | `staphb/kraken2:2.17.1` |
| Purpose | Patches FTP → HTTPS in taxonomy download scripts |
| Used by | Database builds only (not pipeline classification) |
| Documentation | [docker/kraken2/README.md](https://github.com/sanyabadole/RxBiome/blob/dev/docker/kraken2/README.md) |

See the [Kraken2 Docker README](https://github.com/sanyabadole/RxBiome/blob/dev/docker/kraken2/README.md) for the full technical explanation.

### `docker/microberx/` — MicrobeRX Predictor

| Field | Value |
|-------|-------|
| Base | `python:3.11-slim` |
| Key packages | `torch>=2.6`, `MicrobeRX`, `pandas`, `numpy`, `requests` |
| Purpose | Custom image for the `MICROBERX_PREDICT` process |
| Security note | torch≥2.6 required for CVE-2025-32434 mitigation |

**Build:**
```bash
cd docker/microberx
docker build -t sanyabadole/rxbiome-microberx:latest .
docker push sanyabadole/rxbiome-microberx:latest
```

---

## Community Images (BioContainers / nf-core)

| Process | Container | Source |
|---------|-----------|--------|
| FASTP | `community.wave.seqera.io/library/fastp:1.1.0` | Seqera Wave |
| KNEADDATA | `quay.io/biocontainers/kneaddata:0.12.0--pyhdfd78af_1` | BioContainers |
| KRAKEN2 | `quay.io/biocontainers/kraken2:...` | BioContainers |
| BRACKEN | `quay.io/biocontainers/bracken:...` | BioContainers |
| METAPHLAN4 | `quay.io/biocontainers/metaphlan:4.1.1--pyhdfd78af_0` | BioContainers |
| HUMANN3 | `quay.io/biocontainers/humann:3.9--pyh7cba7a3_0` | BioContainers |
| MULTIQC | `quay.io/biocontainers/multiqc:...` | BioContainers |
| PK_IMPACT | `biocontainers/pandas:2.2.1` | BioContainers |
| PK_REPORT_SAMPLE | `biocontainers/pandas:2.2.1` | BioContainers |
| DRUG_SMILES_LOOKUP | `biocontainers/pandas:2.2.1` | BioContainers |

!!! note "Jinja2 in PK_REPORT_SAMPLE"
    The `PK_REPORT_SAMPLE` process uses `biocontainers/pandas:2.2.1` and installs Jinja2 at runtime via `pip install --target .pylibs jinja2`. This avoids maintaining a custom image for a single `pip install`.

---

## Singularity / HPC

All Docker containers are also available as Singularity images. Use:

```bash
nextflow run main.nf -profile singularity ...
```

Nextflow automatically pulls the appropriate Singularity image from the same BioContainers registry.

For air-gapped clusters, pre-pull all images on a machine with internet access:

```bash
# List all containers used
grep "container " modules/**/*.nf | awk '{print $NF}' | sort -u

# Pull each one
singularity pull --name myimage.sif docker://quay.io/biocontainers/...
```

---

## Docker Desktop Resource Settings (macOS / Windows)

RxBiome processes, particularly KneadData and Kraken2, need significant memory. In Docker Desktop:

**Settings → Resources → Advanced:**

| Setting | Minimum | Recommended |
|---------|---------|-------------|
| CPUs | 4 | 8 |
| Memory | 8 GB | 12–16 GB |
| Swap | 2 GB | 4 GB |
| Virtual disk | 50 GB | 100+ GB |

Insufficient resources cause processes to hang silently (the container starts but immediately runs out of memory and is killed by the OS).
