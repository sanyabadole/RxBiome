# Mathematical Methods

This page provides a comprehensive reference for every quantitative decision in the RxBiome PK impact model.

## 1. Microbiome Impact Factor (MIF)

The **Microbiome Impact Factor** is a sample-level, drug-specific score summarising how strongly the detected gut microbiome is predicted to interact with a given drug.

### 1.1 MicrobeRX Pairwise Scoring

For each species \(k\) present in the consensus taxonomy and each drug \(d\):

\[
s_{\text{base},d,k} = \text{TanimotoSimilarity}\!\left(\text{fp}(d),\; \text{fp}_{\text{ref},d,k}\right)
\]

where \(\text{fp}(d)\) is the Morgan circular fingerprint (radius 2, 2048 bits) of the drug's canonical SMILES, and \(\text{fp}_{\text{ref},d,k}\) is the reference fingerprint from the MicrobeRX database for species \(k\)'s known interactions with drug \(d\).

Tanimoto similarity:

\[
T(A, B) = \frac{|A \cap B|}{|A \cup B|} = \frac{\mathbf{a} \cdot \mathbf{b}}{|\mathbf{a}|^2 + |\mathbf{b}|^2 - \mathbf{a} \cdot \mathbf{b}}
\]

### 1.2 Abundance-Weighted Aggregation

The per-species scores are weighted by the species' relative abundance in the sample:

\[
\text{MIF}_d = \sum_{k=1}^{K} s_{\text{base},d,k} \times a_k
\]

where \(a_k\) is the relative abundance of species \(k\) (ranging 0–1, sum across all species = 1).

This ensures that a highly interactive species present at 0.001% contributes negligibly compared to one present at 10%.

---

## 2. MIF Scaling (Saturation Transform)

Raw MIF values are unbounded in practice (if many highly similar species are present). To prevent model saturation and maintain biological realism, a **Michaelis–Menten–type transform** is applied:

\[
\boxed{\text{MIF}_{\text{scaled}} = \frac{\text{MIF}_{\text{raw}}}{\text{MIF}_{\text{raw}} + s}}
\]

| Parameter | Symbol | Default | Config key |
|-----------|--------|---------|------------|
| Scale factor | \(s\) | 0.5 | `pk_mif_scale_factor` |

**Properties of this transform:**
- \(\text{MIF}_{\text{raw}} = 0 \Rightarrow \text{MIF}_{\text{scaled}} = 0\)
- \(\text{MIF}_{\text{raw}} = s \Rightarrow \text{MIF}_{\text{scaled}} = 0.5\) (half-maximal)
- \(\text{MIF}_{\text{raw}} \to \infty \Rightarrow \text{MIF}_{\text{scaled}} \to 1\)

The default \(s = 0.5\) was chosen so that a MIF of 0.5 (moderate multi-species interaction) maps to a scaled value of exactly 0.5.

---

## 3. Clearance Effect

Gut bacterial enzymes (CYP-equivalent reactions, glucuronidases, sulfatases) can increase **apparent oral clearance** of drugs. The fractional change in clearance is modelled as:

\[
\Delta\text{CL}_{\text{frac}} = \text{clip}\!\left(\text{MIF}_{\text{scaled}} \times 0.3,\; \text{CL}_{\min},\; \text{CL}_{\max}\right)
\]

The ×0.3 coefficient reflects the empirical observation that microbiome-mediated metabolism rarely exceeds 30% of total clearance for most drugs (see Zimmermann et al., *Science* 2019).

**Default bounds:**
- \(\text{CL}_{\min} = -0.5\) — allows for microbiome to *reduce* clearance (e.g. by producing CYP-competing metabolites)
- \(\text{CL}_{\max} = 0.8\) — caps at 80% increase (hard physiological maximum)

---

## 4. AUC Shift

AUC and clearance are related by:

\[
\text{AUC} = \frac{F \cdot D}{\text{CL}}
\]

For a fractional change in clearance \(\Delta\text{CL}_{\text{frac}}\), the fractional change in AUC is:

\[
\Delta\text{AUC}_{\text{frac}} = \frac{1}{1 + \Delta\text{CL}_{\text{frac}}} - 1 = \frac{-\Delta\text{CL}_{\text{frac}}}{1 + \Delta\text{CL}_{\text{frac}}}
\]

After clipping to bounds \([\text{AUC}_{\min}, \text{AUC}_{\max}]\):

\[
\boxed{\Delta\text{AUC}_{\text{frac}} = \text{clip}\!\left(\frac{-\Delta\text{CL}_{\text{frac}}}{1 + \Delta\text{CL}_{\text{frac}}},\; \text{AUC}_{\min},\; \text{AUC}_{\max}\right)}
\]

---

## 5. Dose Adjustment Recommendation

By the principle of proportional dose adjustment to maintain target AUC:

\[
\boxed{\text{dose\_adj} = -\Delta\text{AUC}_{\text{frac}}}
\]

Interpretation:
- \(\text{dose\_adj} > 0\): microbiome raises AUC → suggest dose *decrease*
- \(\text{dose\_adj} < 0\): microbiome lowers AUC → suggest dose *increase*

---

## 6. Uncertainty Quantification

The 95% confidence interval is modelled with a linear uncertainty grow with effect size:

\[
\sigma = \alpha \times |\Delta\text{AUC}_{\text{frac}}| + \beta
\]

| Symbol | Parameter | Default |
|--------|-----------|---------|
| \(\alpha\) | `pk_ci_base_uncertainty_scale` | 0.15 |
| \(\beta\) | `pk_ci_min_offset` | 0.05 |

The 95% CI is approximated as:

\[
[\text{dose\_adj} - 1.96\sigma,\; \text{dose\_adj} + 1.96\sigma]
\]

**Rationale:** The minimum offset \(\beta = 0.05\) ensures no prediction claims a CI narrower than ±9.8%, reflecting irreducible uncertainty from unmodelled patient variation. The scale \(\alpha = 0.15\) means that a 30% dose change recommendation has CI width ≈ ±13.4%.

---

## 7. Risk Tier Classification

| Tier | Condition | Clinical interpretation |
|------|-----------|------------------------|
| **HIGH** | \(|\text{dose\_adj}| > 0.20\) | Clinically relevant — > 20% dose shift |
| **MEDIUM** | \(0.10 < |\text{dose\_adj}| \leq 0.20\) | Borderline — warrants monitoring |
| **LOW** | \(|\text{dose\_adj}| \leq 0.10\) | Negligible microbiome impact predicted |

---

## 8. Cohort Statistics

For the cohort report, per-drug summary statistics are computed across all \(N\) samples:

\[
\bar{x}_d = \frac{1}{N}\sum_{i=1}^{N} \text{dose\_adj}_{d,i}
\]

\[
\text{SD}_d = \sqrt{\frac{1}{N-1}\sum_{i=1}^{N} \left(\text{dose\_adj}_{d,i} - \bar{x}_d\right)^2}
\]

The mean ± 1 SD is plotted as horizontal error bars in the lower panel of the cohort heatmap.

---

## References

1. Zimmermann M, Zimmermann-Kogadeeva M, Wegmann R, Goodman AL. *Mapping human microbiome drug metabolism by gut bacteria and their genes.* **Nature** 2019;570:462–467.
2. Spanogiannopoulos P, Bess EN, Carmody RN, Turnbaugh PJ. *The microbial pharmacists within us: a metagenomic view of xenobiotic metabolism.* **Nat Rev Microbiol** 2016;14:273–287.
3. Dempsey JL, Cui JY. *Microbiome is a functional modifier of P450 drug metabolism.* **Curr Pharmacol Rep** 2019;5:481–490.
