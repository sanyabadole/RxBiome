FROM python:3.11-slim

# All packages needed by PK_REPORT_PLOTS and PK_REPORT_SAMPLE processes.
# Baked in so the pipeline never calls pip at runtime (no internet required).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        procps \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "pandas==2.2.1" \
        "numpy>=1.26" \
        "matplotlib==3.9.2" \
        "seaborn==0.13.2" \
        "jinja2==3.1.4" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
