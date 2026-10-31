#!/bin/bash
# DIE-HEAD-45: l44 pinslot re-kit (head_rekit_current.py on main b2cd2d28d2a, source head_source_l44) -> PLACE -> AUTO-GEOM (main geom_check.sh --all-kits, GRT)
set -u
t=$1; C=/srv/opentallas-scratch2/claude; D=$C/die-head-45; R=$C/wt/die-head-45
O=$D/kits/$t
python3 $D/head_rekit_current.py $R $D/head_source_l44 $O $t > $D/kits/$t.rekit.log 2>&1 || { echo "$t REKIT_FAIL"; exit 2; }
grep -c OT_CLAND_PINSLOT $O/gen/$t/*.mk $O/gen/$t/*.sh 2>/dev/null | grep -v ":0" > $D/kits/$t.pinslot.txt
bash $O/gen/run_kit.sh $O/gen/$t place 16 8 > $D/kits/$t.place.log 2>&1; echo "place rc=$?" >> $D/kits/$t.place.log
K=$O/gen/$t; P=$(ls $K/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1)
[ -n "$P" ] || { echo "$t NO_PLACE_ODB"; exit 3; }
G=$D/geom/$t; mkdir -p $G
OUTL=$(sed -nE "s/^export DIE_AREA = 0 0 (\S+) (\S+)/\1x\2/p" $K/config.mk)
printf "{\"id\": \"dh45-%s\", \"odb\": \"%s\", \"image\": \"openroad/orfs:asap7lock\", \"mem_gb\": 8, \"grt\": true, \"rules_args\": [\"--all-kits\", \"--outline\", \"%s\", \"--title\", \"%s l44 pinslot DIE-HEAD-45\"]}\n" ${t//_/-} $P $OUTL $t > $G/check.json
bash $R/tools/autopilot/geom_check.sh $G > $G/geom.log 2>&1
echo "$t $(grep -h AP_AUTO_GEOM $G/geom.log | grep -v PNG | tail -1)"
