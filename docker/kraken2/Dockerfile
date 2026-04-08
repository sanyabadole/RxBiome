# Patched Kraken2 image for reproducible NCBI taxonomy downloads.
#
# Upstream staphb/kraken2 uses kraken2-build scripts that default to ftp:// for
# taxonomy files; many networks see corrupt/truncated .gz downloads over FTP.
# Switching the wget base URL to https:// matches the community workaround and
# matches DerrickWood/kraken2 issue discussions around FTP flakiness.
# solution found at - https://github.com/DerrickWood/kraken2/issues/515
#
# Base image: https://hub.docker.com/r/staphb/kraken2
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
