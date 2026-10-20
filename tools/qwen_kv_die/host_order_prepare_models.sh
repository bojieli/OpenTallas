#!/usr/bin/env bash
set -euo pipefail
cd /work
mkdir -p libs
for f in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*.lib.gz; do
  gzip -dc "$f" > "libs/$(basename "${f%.gz}")"
done
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib libs/
python3 host_order_models.py
