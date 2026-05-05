#!/usr/bin/env python3
"""
Module 4 per-sample HTML QC report generator.

Consolidates four per-sample outputs from PK_IMPACT into a single
self-contained HTML file that can be opened in any browser, printed as
PDF, or emailed without external dependencies.

Inputs
------
pk_impact.tsv      -- per-drug PK impact rows
pk_summary.tsv     -- one-row sample-level summary
dose_change.svg    -- bar chart of absolute dose-change fractions
risk_tier_counts.svg -- bar chart of HIGH/MEDIUM/LOW counts

Output
------
<sample_id>.qc_report.html  -- self-contained HTML report
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Jinja2: install on-the-fly inside containers that lack it
# ---------------------------------------------------------------------------
try:
    from jinja2 import Template
except ImportError:  # pragma: no cover
    import subprocess

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--target", ".pylibs", "jinja2"],
        check=True,
    )
    sys.path.insert(0, str(Path(".pylibs").resolve()))
    from jinja2 import Template  # type: ignore[no-redef]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column mapping: internal name → display label
# ---------------------------------------------------------------------------
_DISPLAY_COLS: dict[str, str] = {
    "drug_name": "Drug",
    "drugbank_id": "DrugBank ID",
    "standard_dose_mg": "Std Dose (mg)",
    "microbiome_impact_factor": "MIF",
    "predicted_auc_multiplier": "AUC Mult.",
    "recommended_dose_mg": "Rec. Dose (mg)",
    "recommended_dose_change_fraction": "Δ Dose",
    "confidence_low": "CI Low (mg)",
    "confidence_high": "CI High (mg)",
    "pk_risk_tier": "Risk Tier",
    "dominant_species": "Dominant Species",
}

_TIER_BADGE: dict[str, str] = {
    "HIGH": '<span class="badge badge-high">HIGH</span>',
    "MEDIUM": '<span class="badge badge-medium">MEDIUM</span>',
    "LOW": '<span class="badge badge-low">LOW</span>',
}

# ---------------------------------------------------------------------------
# HTML template (Jinja2)
# All HTML/SVG variables are passed unescaped because jinja2.Template
# has autoescape=False by default.
# ---------------------------------------------------------------------------
_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>RxBiome QC Report — {{ sample_id }}</title>

  <!-- Bootstrap 5.3 CDN -->
  <link
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
    rel="stylesheet"
  />

  <style>
    /* ── Brand colours ─────────────────────────────────────────── */
    :root {
      --rxb-purple: #6B21A8;
      --rxb-blue:   #1E40AF;
      --rxb-high:   #DC2626;
      --rxb-med:    #D97706;
      --rxb-low:    #16A34A;
    }

    body { background: #f1f5f9; font-family: 'Segoe UI', system-ui, sans-serif; }

    /* ── Header ─────────────────────────────────────────────────── */
    .rxb-header {
      background: linear-gradient(135deg, var(--rxb-purple) 0%, var(--rxb-blue) 100%);
      color: white;
      padding: 2rem 2.5rem;
      border-radius: 0 0 1.25rem 1.25rem;
      box-shadow: 0 4px 24px rgba(30,64,175,.3);
    }
    .rxb-header h1  { font-size: 2rem; font-weight: 700; letter-spacing: -.5px; }
    .rxb-logo-pill  {
      display: inline-block;
      background: rgba(255,255,255,.18);
      border: 1px solid rgba(255,255,255,.4);
      border-radius: 20px;
      font-size: .7rem;
      font-weight: 700;
      padding: 3px 12px;
      letter-spacing: 1.5px;
      text-transform: uppercase;
    }

    /* ── Cards ──────────────────────────────────────────────────── */
    .rxb-card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,.07);
      border: 1px solid #e2e8f0;
    }
    .metric-val   { font-size: 2.4rem; font-weight: 700; line-height: 1; }
    .metric-label { font-size: .78rem; color: #64748b; margin-top: .4rem; }

    /* ── Section headings ───────────────────────────────────────── */
    .rxb-section-title {
      border-left: 4px solid var(--rxb-purple);
      padding-left: .8rem;
      margin: 2rem 0 1rem;
      font-weight: 600;
      color: #1e293b;
    }

    /* ── Risk tier badges ───────────────────────────────────────── */
    .badge-high   { background-color: var(--rxb-high) !important; color: #fff !important; }
    .badge-medium { background-color: var(--rxb-med)  !important; color: #fff !important; }
    .badge-low    { background-color: var(--rxb-low)  !important; color: #fff !important; }

    /* ── Data table ─────────────────────────────────────────────── */
    .pk-table thead th {
      background: #f8fafc;
      font-size: .8rem;
      white-space: nowrap;
      position: sticky;
      top: 0;
    }
    .pk-table tbody td { font-size: .82rem; vertical-align: middle; }

    /* ── SVG containers ─────────────────────────────────────────── */
    .svg-wrap svg { width: 100% !important; height: auto !important; }

    /* ── Interpretation panel ───────────────────────────────────── */
    .interp-note {
      background: #eff6ff;
      border-left: 4px solid var(--rxb-blue);
      border-radius: 0 8px 8px 0;
      padding: 1rem 1.5rem;
    }

    /* ── Footer ─────────────────────────────────────────────────── */
    .rxb-footer {
      background: #1e293b;
      color: #94a3b8;
      padding: 1.5rem;
      text-align: center;
      font-size: .8rem;
      margin-top: 3rem;
    }

    /* ── Print ──────────────────────────────────────────────────── */
    @media print {
      body { background: white !important; }
      .rxb-header {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
      .rxb-card   { box-shadow: none !important; border: 1px solid #cbd5e1; }
      .no-print   { display: none !important; }
      .rxb-footer { background: #1e293b !important; print-color-adjust: exact; }
    }
  </style>
</head>

<body>

<!-- ══════════════════════════ HEADER ══════════════════════════════════ -->
<header class="rxb-header mb-4">
  <div class="container-fluid">
    <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
      <div>
        <span class="rxb-logo-pill mb-2 d-inline-block">RxBiome Pipeline</span>
        <h1 class="mt-2 mb-1">Patient PK QC Report</h1>
        <p class="mb-0 opacity-90 fs-5">Sample: <strong>{{ sample_id }}</strong></p>
      </div>
      <div class="text-end small opacity-75 pt-1">
        <div>Generated: {{ generated_at }}</div>
        <div class="mt-1">Module 4 — PK Impact Modelling</div>
      </div>
    </div>
  </div>
</header>

<div class="container-fluid px-4">

  <!-- ══════════════════════ EXECUTIVE SUMMARY ══════════════════════════ -->
  <h2 class="rxb-section-title h5">Executive Summary</h2>

  <div class="row g-3 mb-3">
    <!-- Total drugs -->
    <div class="col-6 col-md-3">
      <div class="rxb-card p-3 text-center h-100">
        <div class="metric-val text-primary">{{ n_drugs }}</div>
        <div class="metric-label">Drugs Analysed</div>
      </div>
    </div>

    <!-- HIGH risk -->
    <div class="col-6 col-md-3">
      <div class="rxb-card p-3 text-center h-100"
           style="border-top: 4px solid var(--rxb-high)">
        <div class="metric-val" style="color:var(--rxb-high)">{{ n_high }}</div>
        <div class="metric-label">
          <span class="badge badge-high px-2">HIGH</span> Risk Drugs
        </div>
      </div>
    </div>

    <!-- MEDIUM risk -->
    <div class="col-6 col-md-3">
      <div class="rxb-card p-3 text-center h-100"
           style="border-top: 4px solid var(--rxb-med)">
        <div class="metric-val" style="color:var(--rxb-med)">{{ n_medium }}</div>
        <div class="metric-label">
          <span class="badge badge-medium px-2">MEDIUM</span> Risk Drugs
        </div>
      </div>
    </div>

    <!-- LOW risk -->
    <div class="col-6 col-md-3">
      <div class="rxb-card p-3 text-center h-100"
           style="border-top: 4px solid var(--rxb-low)">
        <div class="metric-val" style="color:var(--rxb-low)">{{ n_low }}</div>
        <div class="metric-label">
          <span class="badge badge-low px-2">LOW</span> Risk Drugs
        </div>
      </div>
    </div>
  </div>

  <!-- Key dose-change metrics -->
  <div class="row g-3 mb-4">
    <div class="col-md-6">
      <div class="rxb-card p-3">
        <div class="small text-muted mb-1">Mean Dose Change</div>
        <div class="h4 fw-bold mb-0 {{ mean_change_cls }}">{{ mean_change_pct }}%</div>
        <div class="small text-muted mt-1">
          Across all drugs for this sample (negative = reduction recommended)
        </div>
      </div>
    </div>
    <div class="col-md-6">
      <div class="rxb-card p-3">
        <div class="small text-muted mb-1">Max Absolute Dose Change</div>
        <div class="h4 fw-bold mb-0 text-warning">{{ max_change_pct }}%</div>
        <div class="small text-muted mt-1">
          Largest single-drug adjustment predicted for this sample
        </div>
      </div>
    </div>
  </div>

  <!-- ══════════════════════════ PLOTS ═══════════════════════════════════ -->
  <h2 class="rxb-section-title h5">Pharmacokinetic Plots</h2>

  <div class="row g-3 mb-4">
    <div class="col-md-6">
      <div class="rxb-card p-3 h-100">
        <h3 class="h6 text-muted fw-semibold mb-3">Absolute Dose Change by Drug</h3>
        <div class="svg-wrap">{{ dose_svg }}</div>
      </div>
    </div>
    <div class="col-md-6">
      <div class="rxb-card p-3 h-100">
        <h3 class="h6 text-muted fw-semibold mb-3">PK Risk Tier Distribution</h3>
        <div class="svg-wrap">{{ risk_svg }}</div>
      </div>
    </div>
  </div>

  <!-- ════════════════ DRUG–MICROBIOME INTERACTION TABLE ═════════════════ -->
  <h2 class="rxb-section-title h5">Drug–Microbiome Interaction Details</h2>

  <div class="rxb-card mb-4" style="overflow-x: auto">
    {{ pk_impact_table }}
  </div>

  <!-- ══════════════════ CLINICAL INTERPRETATION GUIDE ══════════════════ -->
  <h2 class="rxb-section-title h5">Risk Tier Interpretation</h2>

  <div class="row g-3 mb-4">
    <!-- HIGH -->
    <div class="col-md-4">
      <div class="rxb-card h-100"
           style="border-top: 4px solid var(--rxb-high)">
        <div class="card-header fw-semibold text-white"
             style="background: var(--rxb-high); border-radius: 0">
          HIGH Risk
        </div>
        <div class="card-body small">
          Tight confidence interval and predicted dose change &ge;20%.
          The microbiome signal is strong and consistent across multiple
          species, suggesting a robust drug–microbiome interaction.
          Requires careful attention and further investigation.
        </div>
      </div>
    </div>

    <!-- MEDIUM -->
    <div class="col-md-4">
      <div class="rxb-card h-100"
           style="border-top: 4px solid var(--rxb-med)">
        <div class="card-header fw-semibold text-dark"
             style="background: var(--rxb-med); border-radius: 0">
          MEDIUM Risk
        </div>
        <div class="card-body small">
          Moderate confidence with predicted dose adjustment &ge;10%.
          Suggestive of microbiome-mediated PK modulation. Warrants
          monitoring and documentation, especially for drugs with a
          narrow therapeutic window.
        </div>
      </div>
    </div>

    <!-- LOW -->
    <div class="col-md-4">
      <div class="rxb-card h-100"
           style="border-top: 4px solid var(--rxb-low)">
        <div class="card-header fw-semibold text-white"
             style="background: var(--rxb-low); border-radius: 0">
          LOW Risk
        </div>
        <div class="card-body small">
          Either a weak predicted effect or high model uncertainty.
          The model does not predict a clinically meaningful
          microbiome-mediated exposure shift under current assumptions.
        </div>
      </div>
    </div>
  </div>

  <!-- Model glossary -->
  <div class="interp-note mb-5">
    <h3 class="h6 fw-semibold">Model Glossary</h3>
    <ul class="small mb-0 mt-2">
      <li>
        <strong>Microbiome Impact Factor (MIF)</strong> — Mean interaction
        confidence across all detected drug-metabolising species. Higher MIF
        indicates a stronger aggregate microbial signal.
      </li>
      <li class="mt-1">
        <strong>Predicted AUC Multiplier</strong> — Non-linear scaling of MIF
        onto predicted systemic exposure shift. Values &gt;1 indicate increased
        exposure; &lt;1 indicates reduced exposure.
      </li>
      <li class="mt-1">
        <strong>Recommended Dose (mg)</strong> — Dose adjusted to restore the
        target exposure, bounded by &plusmn;50% of standard dose. Based on a
        population-level deterministic model, not patient-specific PK parameters.
      </li>
      <li class="mt-1">
        <strong>Confidence Interval</strong> — Wider intervals reflect higher
        model uncertainty (e.g. fewer or lower-confidence microbial interactions).
      </li>
      <li class="mt-1">
        <strong>Dominant Species</strong> — The gut organism with the highest
        individual interaction confidence for this drug in this sample.
      </li>
    </ul>
  </div>

</div><!-- /container -->

<!-- ══════════════════════════ FOOTER ══════════════════════════════════ -->
<footer class="rxb-footer">
  <strong>
    For research purposes only. Not intended for clinical decision-making
    or diagnostic use.
  </strong>
  <div class="mt-1 opacity-75">
    RxBiome Pipeline &middot; Module 4: PK Impact Analysis &middot;
    {{ generated_at }}
  </div>
</footer>

<!-- Bootstrap JS bundle (popper included) -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>

</body>
</html>
"""


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a self-contained per-sample HTML QC report for Module 4.",
    )
    parser.add_argument("--sample-id", required=True, help="Sample identifier")
    parser.add_argument("--pk-impact-tsv", required=True, help="Path to *.pk_impact.tsv")
    parser.add_argument("--pk-summary-tsv", required=True, help="Path to *.pk_summary.tsv")
    parser.add_argument("--dose-plot-svg", required=True, help="Path to *.dose_change.svg")
    parser.add_argument("--risk-plot-svg", required=True, help="Path to *.risk_tier_counts.svg")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# HTML table builder
# ---------------------------------------------------------------------------
def _build_pk_table(df: pd.DataFrame) -> str:
    """Return a Bootstrap-styled HTML table string for the pk_impact data."""
    display = df[[c for c in _DISPLAY_COLS if c in df.columns]].copy()
    display = display.rename(columns=_DISPLAY_COLS)

    # Format numeric columns to readable precision
    for col in ("MIF", "AUC Mult."):
        if col in display.columns:
            display[col] = display[col].apply(
                lambda v: f"{v:.4f}" if pd.notna(v) else "—"
            )
    for col in ("Std Dose (mg)", "Rec. Dose (mg)", "CI Low (mg)", "CI High (mg)"):
        if col in display.columns:
            display[col] = display[col].apply(
                lambda v: f"{v:.1f}" if pd.notna(v) else "—"
            )
    if "Δ Dose" in display.columns:
        display["Δ Dose"] = display["Δ Dose"].apply(
            lambda v: f"{v * 100:+.1f}%" if pd.notna(v) else "—"
        )

    # Replace Risk Tier text with coloured Bootstrap badges
    if "Risk Tier" in display.columns:
        display["Risk Tier"] = display["Risk Tier"].map(
            lambda t: _TIER_BADGE.get(str(t), str(t))
        )

    html = display.to_html(
        classes="table table-striped table-hover table-sm pk-table mb-0",
        index=False,
        escape=False,
        border=0,
    )
    return f'<div class="p-2">{html}</div>'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()
    log.info("Generating QC report for sample: %s", args.sample_id)

    pk_impact = pd.read_csv(args.pk_impact_tsv, sep="\t")
    pk_summary = pd.read_csv(args.pk_summary_tsv, sep="\t")
    dose_svg = Path(args.dose_plot_svg).read_text(encoding="utf-8")
    risk_svg = Path(args.risk_plot_svg).read_text(encoding="utf-8")

    # Extract one-row summary metrics (default to zero if missing)
    if pk_summary.empty:
        log.warning("pk_summary.tsv is empty — defaulting all metrics to 0.")
        n_drugs = n_high = n_medium = n_low = 0
        mean_change = max_change = 0.0
    else:
        row = pk_summary.iloc[0]
        n_drugs    = int(row.get("n_drugs", 0))
        n_high     = int(row.get("n_high_risk", 0))
        n_medium   = int(row.get("n_medium_risk", 0))
        n_low      = int(row.get("n_low_risk", 0))
        mean_change = float(row.get("mean_dose_change_fraction", 0.0))
        max_change  = float(row.get("max_abs_dose_change_fraction", 0.0))

    mean_change_pct = f"{mean_change * 100:+.1f}"
    max_change_pct  = f"{max_change  * 100:.1f}"
    # CSS class drives the colour of the mean dose change value
    mean_change_cls = "text-danger" if mean_change < 0 else "text-success"

    template = Template(_HTML_TEMPLATE)
    html = template.render(
        sample_id=args.sample_id,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        n_drugs=n_drugs,
        n_high=n_high,
        n_medium=n_medium,
        n_low=n_low,
        mean_change_pct=mean_change_pct,
        max_change_pct=max_change_pct,
        mean_change_cls=mean_change_cls,
        dose_svg=dose_svg,
        risk_svg=risk_svg,
        pk_impact_table=_build_pk_table(pk_impact),
    )

    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    log.info("Written: %s", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
