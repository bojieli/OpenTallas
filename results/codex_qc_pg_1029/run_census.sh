#!/bin/bash
set -euo pipefail
root=/srv/opentallas-scratch2/claude/codex-qc-pg-1029
input=/srv/opentallas-scratch2/claude/codex-qc-1029/mechanics6
mkdir -p "$root/census"
sudo docker run --rm --name codex-qc-pg-census-1029 \
  -v "$root/pg_census.py:/pg_census.py:ro" \
  -v "$input:/in:ro" -v "$root/census:/out" \
  openroad/orfs:latest bash -c \
  'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap "chown -R 1000:1000 /out" EXIT; openroad -python -exit /pg_census.py --odb /in/clock_grafted.odb --out /out --expect-cells 49496'
