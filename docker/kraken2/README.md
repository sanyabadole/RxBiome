# RxBiome — Patched Kraken2 Docker Image

## Overview

This directory contains a patched `Dockerfile` for the Kraken2 taxonomic classifier used in the RxBiome pipeline.

It addresses a well-known upstream bug where `kraken2-build`'s taxonomy download scripts default to `ftp://` URLs that are frequently corrupt or truncated on modern networks, causing reproducibility failures.

## Why This Patch Exists

The upstream `staphb/kraken2` image ships `download_taxonomy.sh` with:

```bash
FTP_SERVER=ftp://ftp.ncbi.nlm.nih.gov
```

FTP connections to NCBI are routinely blocked by firewalls, throttled by cloud NATs, and prone to silent truncation of `.gz` files. The resulting corrupt taxonomy databases cause downstream Kraken2 classification to fail or produce garbage outputs — silently, with no error code.

This is a widely-documented community issue:  
[DerrickWood/kraken2 issue #515](https://github.com/DerrickWood/kraken2/issues/515)

The fix is a one-line `sed` substitution that replaces `ftp://` with `https://` in every copy of the script bundled in the image.

## Base Image

| Field         | Value                          |
|---------------|-------------------------------|
| Base image    | `staphb/kraken2:2.17.1`       |
| Registry      | [Docker Hub](https://hub.docker.com/r/staphb/kraken2) |
| Kraken2 version | 2.17.1                      |
| Patch author  | RxBiome pipeline team         |

## What the Dockerfile Does

```dockerfile
FROM staphb/kraken2:2.17.1

USER root

RUN set -eux; \
    for f in \
        /kraken2-2.17.1/download_taxonomy.sh \
        /kraken2-2.17.1/scripts/download_taxonomy.sh; \
    do \
        test -f "$f"; \
        sed -i '/^FTP_SERVER=/s|ftp://|https://|' "$f"; \
    done; \
    grep '^FTP_SERVER=' /kraken2-2.17.1/scripts/download_taxonomy.sh
```

**Step by step:**

1. `USER root` — escalates to root so the taxonomy scripts (owned by root) can be patched.
2. `for f in ...` — iterates over both the top-level and `scripts/` copy of `download_taxonomy.sh` (both are bundled in the base image; both need patching).
3. `test -f "$f"` — **fails loudly** if either file is missing (guards against silent skips if staphb changes paths in a future version).
4. `sed -i '/^FTP_SERVER=/s|ftp://|https://|'` — regex anchored to the start of a line (`^FTP_SERVER=`) so it only replaces the correct assignment, not any URL embedded in comments or other variables.
5. `grep` — verifies the replacement succeeded and prints the patched line to build logs for auditing.

## Building Locally

```bash
cd docker/kraken2
docker build -t rxbiome/kraken2:2.17.1-patched .
```

## Verifying the Patch

```bash
docker run --rm rxbiome/kraken2:2.17.1-patched \
    grep '^FTP_SERVER=' /kraken2-2.17.1/scripts/download_taxonomy.sh
# Expected output:
# FTP_SERVER=https://ftp.ncbi.nlm.nih.gov
```

## Usage in the RxBiome Pipeline

This image is **not used for Kraken2 classification** during a normal pipeline run. The nf-core community provides a separate pre-built Kraken2 classification image (`quay.io/biocontainers/kraken2`) for that purpose.

This patched image is intended for teams that need to **build a custom Kraken2 database** from scratch in a network-restricted or cloud environment where FTP is unavailable.

For the standard pipeline, the pre-built `databases/kraken2/` database directory is passed via:

```bash
nextflow run main.nf --kraken2_db /path/to/databases/kraken2 ...
```

## Reproducing a Database Build (Optional)

If you need to build the Kraken2 Standard 8GB database yourself:

```bash
docker run --rm -v $(pwd)/kraken2_db:/db \
    rxbiome/kraken2:2.17.1-patched \
    bash -c "
      kraken2-build --download-taxonomy --db /db
      kraken2-build --download-library bacteria --db /db
      kraken2-build --download-library archaea --db /db
      kraken2-build --download-library viral --db /db
      kraken2-build --build --db /db --threads 8
    "
```

> **Note:** A full standard build requires ~100 GB of disk space and several hours of compute time. For routine pipeline use, download the pre-built Standard 8 database from [BenLangmead's genome-db releases](https://benlangmead.github.io/aws-indexes/k2).

## Reproducibility Notes

| Item | Detail |
|------|--------|
| Pinned base tag | `staphb/kraken2:2.17.1` — prevents silent upstream updates |
| `set -eux` in RUN | Any unexpected build step fails loudly with its command printed |
| `test -f` guard | Build fails if staphb relocates scripts in a future minor version |
| `grep` audit | Patched URL is always visible in `docker build` logs |

## Related Files

| File | Purpose |
|------|---------|
| `docker/microberx/Dockerfile` | Custom MicrobeRX Python container |
| `modules/nf-core/kraken2/kraken2/main.nf` | Nextflow process using the nf-core Kraken2 container |
| `modules/nf-core/kraken2/kraken2/kraken2-kraken2.diff` | Local diff applied to the nf-core module |
| `conf/modules.config` | Publishing paths and ext.args for Kraken2 |
