#!/bin/bash
# CORE-HBM-OTHER: pin-reg audit + odb stats for every kit in this dir that has a 1_synth.odb and no pin_reg_audit.json yet
D=$(cd "$(dirname "$0")" && pwd)
for k in "$D"/*/; do k=${k%/}; n=$(basename "$k")
  o=$(ls "$k"/run/results/asap7/*/base/1_synth.odb 2>/dev/null | head -1); [ -n "$o" ] || continue
  [ -s "$k/pin_reg_audit.json" ] && [ -s "$k/odb_stats.json" ] && continue
  rel=${o#$D/}
  docker run --rm --name "coreother-audit-$(echo $n | tr -c 'A-Za-z0-9_.\n-' _)" --memory 16g -v "$D":/c openroad/orfs:asap7lock bash -lc \
   "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /c; ODB=/c/$rel OUT=/c/$n/pin_reg_audit.json openroad -python -exit /c/pin_reg_audit.py > /c/$n/pin_reg_audit.log 2>&1; ODB=/c/$rel OUT=/c/$n/odb_stats.json openroad -python -exit /c/odb_stats.py > /c/$n/odb_stats.log 2>&1; chown -R $(id -u):$(id -g) /c/$n/pin_reg_audit.* /c/$n/odb_stats.*"
  echo "$n $(grep -h PIN_REG_AUDIT $k/pin_reg_audit.log | head -1 | cut -c1-150) | $(grep -h ODB_STATS $k/odb_stats.log)"
done
