#!/bin/bash
# DIE-HBM-53: place + AUTO-GEOM (no GRT) for the 4 opstore variant kits; ot-run pinned to intel1 (kits live there)
D=/srv/opentallas-scratch2/claude/die-hbm-53/ops
for K in $(awk -F"\t" "{print \$2}" $1); do (
  cd $K && ot-heavy --mem 32 -- bash $K/run_kit_hbm.sh $K place 32 16 > $K.place.log 2>&1
  echo "PLACE_RC $?" >> $K.place.log
  O=$(ls $K/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1)
  if [ -n "$O" ]; then G=$K.geom; mkdir -p $G
    python3 -c "import json,sys;json.dump(dict(id=\"dh53-\"+sys.argv[2], odb=sys.argv[1], image=\"openroad/orfs:asap7lock\", mem_gb=24, grt=False, rules_args=[\"--all-kits\",\"--title\",\"DIE-HBM-53 \"+sys.argv[2]]),open(sys.argv[3],\"w\"))" "$O" "$(basename $(dirname $(dirname $K)))-$(basename $K | cut -c1-40)" $G/check.json
    bash /srv/opentallas-scratch2/claude/wt/die-hbm-49/tools/autopilot/geom_check.sh $G > $G/geom.log 2>&1
  fi ) &
done; wait; echo ALLDONE
