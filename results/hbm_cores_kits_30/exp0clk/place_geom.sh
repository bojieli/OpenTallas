#!/bin/bash
# HBM-CORES-KITS-27 exp0: kit -> lint/synth/LEC/floorplan/place (run_kit_hbm.sh place) -> AUTO-GEOM (DIE-HBM-21 review.sh, GRT 50 it). Same as hbm-cores-kits-26/place_geom.sh.
set -u
K=$1; n=$(basename $K); echo "$(date) $n place start"
bash $K/run_kit_hbm.sh $K place 32 8 > $K/run_place_k28.log 2>&1; rc=$?; echo "$(date) $n place rc=$rc $(ls $K/FAIL_* 2>/dev/null)"
if ls $K/run/results/asap7/*/base/3_place.odb >/dev/null 2>&1; then
  bash /srv/opentallas-scratch2/claude/die-hbm-21/review.sh $K $K/rev $n; echo "$(date) $n geom $(tail -1 $K/rev/review.log)"
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(\"AUTO_GEOM\",d.get(\"line\"))" $K/rev/auto_geom.json 2>&1 | cut -c1-1500
fi
echo "$(date) done"
