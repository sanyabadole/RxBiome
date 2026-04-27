#!/usr/bin/env bash
set -euo pipefail
python bin/taxonomic_consensus.py \
  --bracken tests/data/mock_bracken.txt \
  --metaphlan tests/data/mock_metaphlan.txt \
  --bracken-threshold 0.0001 \
  --metaphlan-threshold 0.01 \
  --output tests/data/consensus_output.tsv

echo "=== OUTPUT ==="
cat tests/data/consensus_output.tsv

echo ""
echo "=== VALIDATION ==="
# Bacteroides uniformis and Akkermansia should be HIGH (in both)
# Faecalibacterium prausnitzii should be HIGH (in both)
# Blautia obeum should be MEDIUM (MetaPhlAn only)
# Clostridium perfringens should be LOW or absent (below both thresholds)
python - <<'EOF'
import pandas as pd
df = pd.read_csv("tests/data/consensus_output.tsv", sep="\t")
assert df[df.species == "Bacteroides uniformis"]["confidence"].values[0] == "HIGH", "FAIL: Bacteroides should be HIGH"
assert df[df.species == "Akkermansia muciniphila"]["confidence"].values[0] == "HIGH", "FAIL: Akkermansia should be HIGH"
assert df[df.species == "Blautia obeum"]["confidence"].values[0] == "MEDIUM", "FAIL: Blautia should be MEDIUM"
print("ALL ASSERTIONS PASSED ✓")
print(df[["species","confidence","final_abundance"]].to_string(index=False))
EOF

echo ""
echo "=== MODULE 2→3 JOIN VALIDATION ==="
python - <<'EOF'
import pandas as pd

consensus = pd.read_csv("tests/data/consensus_output.tsv", sep="\t")
high_conf = set(consensus[consensus.confidence.isin(["HIGH","MEDIUM"])].species)

pathways = pd.read_csv("tests/data/mock_humann3_pathabundance.txt",
                       sep="\t", comment="#", header=None,
                       names=["pathway","abundance"])
pathways["species"] = pathways["pathway"].str.extract(r'\|(.+)$')

# Keep only species-stratified rows for HIGH/MEDIUM confidence species
filtered = pathways[
    pathways["species"].notna() &
    pathways["species"].isin(high_conf)
]

# Clostridium perfringens is LOW confidence — must be excluded
assert "Clostridium perfringens" not in filtered["species"].values, \
    "FAIL: LOW-confidence species leaked into functional profile"

# HIGH confidence species must be present
assert "Bacteroides uniformis" in filtered["species"].values, \
    "FAIL: HIGH-confidence Bacteroides missing from functional profile"

print("MODULE 2→3 JOIN ASSERTIONS PASSED ✓")
print(filtered[["pathway","abundance","species"]].to_string(index=False))
EOF
