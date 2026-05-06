# Databases

RxBiome requires three reference databases for a full run. This page covers downloading and configuring each one.

## Summary Table

| Database | Parameter | Required | Typical size |
|----------|-----------|----------|-------------|
| Kraken2 | `--kraken2_db` | Yes | ~8 GB (Standard 8) |
| MetaPhlAn 4 | `--metaphlan4_db` + `--metaphlan4_index` | Yes | ~5 GB |
| KneadData host | `--host_db` + `--host_bowtie2_prefix` | Only if host removal enabled | ~4 GB |
| HUMAnN3 nucleotide | `--humann3_nucleotide_db` | Optional | ~15 GB |
| HUMAnN3 protein | `--humann3_protein_db` | Optional | ~25 GB |

---

## Kraken2

```bash
# Download Standard 8 GB pre-built index (recommended for most analyses)
mkdir -p databases/kraken2
cd databases/kraken2
wget https://genome-idx.s3.amazonaws.com/kraken/k2_standard_08gb_20240112.tar.gz
tar -xzf k2_standard_08gb_20240112.tar.gz
rm k2_standard_08gb_20240112.tar.gz
```

Run with:
```
--kraken2_db databases/kraken2
```

---

## MetaPhlAn 4

```bash
mkdir -p databases/metaphlan
metaphlan --install --index mpa_vJan25_CHOCOPhlAnSGB_202503 \
          --bowtie2db databases/metaphlan
```

Or download Bowtie2 index files directly:

```bash
mkdir -p databases/metaphlan
cd databases/metaphlan
# Download all .bt2l files + .pkl file for mpa_vJan25_CHOCOPhlAnSGB_202503
wget http://cmprod1.cibio.unitn.it/biobakery4/metaphlan_databases/mpa_vJan25_CHOCOPhlAnSGB_202503.tar
tar -xf mpa_vJan25_CHOCOPhlAnSGB_202503.tar
```

Run with:
```
--metaphlan4_db databases/metaphlan \
--metaphlan4_index mpa_vJan25_CHOCOPhlAnSGB_202503
```

---

## KneadData Host Database (Human)

Only required when `--skip_host_decontamination false` (the default).

```bash
mkdir -p databases/kneaddata_human
kneaddata_database --download human_genome bowtie2 databases/kneaddata_human
```

Or download from the Biobakery data server directly (hg37dec_v0.1):

```bash
mkdir -p databases/kneaddata_human
cd databases/kneaddata_human
# Each .bt2 file is ~700 MB–1 GB
for f in 1 2 3 4 rev.1 rev.2; do
  wget https://huttenhower.sph.harvard.edu/kneaddata_databases/Homo_sapiens_hg37_and_Human_herpesvirus_5_Bowtie2_v0.1_Huttenhower/hg37dec_v0.1.${f}.bt2
done
```

Run with:
```
--host_db databases/kneaddata_human \
--host_bowtie2_prefix hg37dec_v0.1
```

---

## HUMAnN3 (Optional)

```bash
# ChocoPhlAn nucleotide database (~15 GB)
humann_databases --download chocophlan full databases/humann3/chocophlan

# UniRef protein database (~25 GB)
humann_databases --download uniref uniref90_diamond databases/humann3/uniref

# Utility mapping
humann_databases --download utility_mapping full databases/humann3/utility_mapping
```

Run with:
```
--humann3_nucleotide_db databases/humann3/chocophlan \
--humann3_protein_db databases/humann3/uniref
```

If these parameters are omitted, functional profiling is silently skipped and the pipeline continues with Module 3 onwards.

---

## Recommended Directory Layout

```
rxbiome/
└── databases/
    ├── kraken2/           # hash.k2d, taxo.k2d, opts.k2d, ...
    ├── metaphlan/         # mpa_vJan25_*.bt2l, *.pkl, ...
    ├── kneaddata_human/   # hg37dec_v0.1.*.bt2
    └── humann3/           # chocophlan/, uniref/, utility_mapping/
```
