#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs:asap7lock bash -lc '
 p=/OpenROAD-flow-scripts/flow/platforms/asap7
 for name in before after_ties placed; do
  cp "$p"/lib/NLDM/*RVT_TT*.lib* "/work/$name/"
 done
 sha256sum "$p"/lef/asap7_tech_1x_201209.lef "$p"/lef/asap7sc7p5t_28_R_1x_220121a.lef "$p"/openRoad/make_tracks.tcl "$p"/setRC.tcl > /work/platform_SHA256SUMS
 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /work/tools/hbm_int8_tie_place/geometry.py /work/placed.odb /work/geometry.json
 '
python3 tools/hbm_int8_tie_place/plot.py geometry.json placement.png
for name in before after_ties placed; do
 (cd "$name" && sha256sum raw.json *.lib* > SHA256SUMS)
 if python3 tools/hbm_int8_tie_place/strict_replay.py "$name" "audit_$name" > "audit_$name.log" 2>&1; then
  test "$name" != before
 else
  test "$name" = before
  grep -q 'undriven loaded net' "audit_$name.log"
 fi
done
