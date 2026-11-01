#!/bin/bash
# DIE-HEAD-53 helper l48z: kit_one_src.sh form on the dh53-l48z worktree (main 0499590af41 tools): rekit -> OT_CLAND_PINSLOT=1 -> PLACE -> AUTO-GEOM (geom_check.sh --all-kits, GRT)
set -u
t=$1; SRC=${SRC:-l48z}; D=/srv/opentallas-scratch2/claude/die-head-48; R=/srv/opentallas-scratch2/claude/wt/dh53-l48z; B=$D/dh53/l48z
O=$B/kits_$SRC/$t; mkdir -p $B/kits_$SRC; rm -rf $O
python3 /srv/opentallas-scratch2/claude/die-head-46/head_rekit_current.py $R $D/head_source_$SRC $O $t > $B/kits_$SRC/$t.rekit.log 2>&1 || { echo "$t REKIT_FAIL"; exit 2; }
grep -q "^export OT_CLAND_PINSLOT" $O/gen/$t/config.mk || echo "export OT_CLAND_PINSLOT = 1" >> $O/gen/$t/config.mk
bash $O/gen/run_kit.sh $O/gen/$t place 16 8 > $B/kits_$SRC/$t.place.log 2>&1; echo "place rc=$?" >> $B/kits_$SRC/$t.place.log
K=$O/gen/$t; P=$(ls $K/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1)
[ -n "$P" ] || { echo "$t NO_PLACE_ODB"; exit 3; }
G=$B/geom_$SRC/$t; mkdir -p $G
OUTL=$(sed -nE "s/^export DIE_AREA = 0 0 (\S+) (\S+)/\1x\2/p" $K/config.mk)
printf "{\"id\": \"dh53z-%s\", \"odb\": \"%s\", \"image\": \"openroad/orfs:asap7lock\", \"mem_gb\": 8, \"grt\": true, \"rules_args\": [\"--all-kits\", \"--outline\", \"%s\", \"--title\", \"%s $SRC DIE-HEAD-53 l48z\"]}\n" ${t//_/-} $P $OUTL $t > $G/check.json
bash $R/tools/autopilot/geom_check.sh $G > $G/geom.log 2>&1
echo "$t $(grep -h AP_AUTO_GEOM $G/geom.log | grep -v PNG | tail -1)"
