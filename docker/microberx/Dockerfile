FROM python:3.11-slim

# MicrobeRX stack may install parmed without a matching wheel; building its C++ extension requires g++.
# torch>=2.6 satisfies loaders used by MicrobeRX/datamol (CVE-2025-32434 guard).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        build-essential \
        procps \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "torch>=2.6" MicrobeRX pandas numpy requests \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y --purge \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
