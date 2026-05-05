#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 5.2 static PK cohort plot generation.")
    parser.add_argument("--cohort-drug-summary", required=True)
    parser.add_argument("--cohort-sample-summary", required=True)
    parser.add_argument("--drug-plot-output", required=True)
    parser.add_argument("--sample-plot-output", required=True)
    return parser.parse_args()


def _write_bar_svg(labels: list[str], values: list[float], title: str, y_label: str, out_path: Path) -> None:
    width, height = 1000, 450
    left, right, top, bottom = 100, 20, 60, 120
    plot_w, plot_h = width - left - right, height - top - bottom
    max_val = max(values) if values else 1.0
    max_val = max(max_val, 1e-9)
    n = max(len(values), 1)
    gap = 14
    bar_w = max((plot_w - (n - 1) * gap) / n, 8)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<text x="{width/2}" y="30" text-anchor="middle" font-size="20" font-family="Arial">{title}</text>',
        f'<text x="24" y="{top + plot_h/2}" transform="rotate(-90 24,{top + plot_h/2})" text-anchor="middle" font-size="12" font-family="Arial">{y_label}</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#333" stroke-width="2"/>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#333" stroke-width="2"/>',
    ]

    for i, (label, value) in enumerate(zip(labels, values, strict=False)):
        x = left + i * (bar_w + gap)
        h = (value / max_val) * (plot_h * 0.9)
        y = top + plot_h - h
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="#2A9D8F"/>')
        lines.append(f'<text x="{x + bar_w/2:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-size="9" font-family="Arial">{value:.3f}</text>')
        lines.append(f'<text x="{x + bar_w/2:.1f}" y="{top + plot_h + 16}" text-anchor="middle" font-size="9" font-family="Arial">{label}</text>')

    lines.append("</svg>")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    drug = pd.read_csv(args.cohort_drug_summary, sep="\t")
    sample = pd.read_csv(args.cohort_sample_summary, sep="\t")

    top_drugs = drug.sort_values("mean_recommended_dose_change_fraction", ascending=False).head(10)
    _write_bar_svg(
        labels=[str(x) for x in top_drugs["drug_name"].tolist()],
        values=[float(abs(x)) for x in top_drugs["mean_recommended_dose_change_fraction"].tolist()],
        title="Top Drugs by Absolute Mean Dose-Change Fraction",
        y_label="abs(mean dose-change fraction)",
        out_path=Path(args.drug_plot_output),
    )

    sample_sorted = sample.sort_values("max_abs_recommended_dose_change_fraction", ascending=False)
    _write_bar_svg(
        labels=[str(x) for x in sample_sorted["sample_id"].tolist()],
        values=[float(x) for x in sample_sorted["max_abs_recommended_dose_change_fraction"].tolist()],
        title="Max Absolute Dose-Change Fraction by Sample",
        y_label="max abs dose-change fraction",
        out_path=Path(args.sample_plot_output),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
