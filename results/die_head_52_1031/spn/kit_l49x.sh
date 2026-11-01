#!/bin/bash
# DIE-HEAD-52 helper spn: l49x (= l49s + 51 raw-export pin moves) kit = head_spn_l49s.py rekit (realized stations + istations.tcl, WFALL tools) -> PLACE -> AUTO-GEOM GRT
set -u
t=$1; D=/srv/opentallas-scratch2/claude/die-head-48; R=/srv/opentallas-scratch2/claude/wt/dh51-wfall; TOOL=/srv/opentallas-scratch2/claude/wt/dh51-spn/tools/s81_head/head_spn_l49s.py
K0=$D/dh52spn/kits_l49x; O=$K0/$t; mkdir -p $K0; rm -rf $O
python3 $TOOL rekit $R $D/head_source_l49x $O $t > $K0/$t.rekit.log 2>&1 || { echo "$t REKIT_FAIL"; exit 2; }
grep -q "^export OT_CLAND_PINSLOT" $O/gen/$t/config.mk || echo "export OT_CLAND_PINSLOT = 1" >> $O/gen/$t/config.mk
ls -la $O/gen/$t/istations.tcl >> $K0/$t.rekit.log
bash $O/gen/run_kit.sh $O/gen/$t ${GOAL:-place} 16 8 > $K0/$t.place.log 2>&1; echo "place rc=$?" >> $K0/$t.place.log
K=$O/gen/$t; P=$(ls $K/run/results/asap7/*/base/3_place.odb 2>/dev/null | head -1)
[ -n "$P" ] || { echo "$t NO_PLACE_ODB"; exit 3; }
G=$D/dh52spn/geom_l49x/$t; mkdir -p $G
OUTL=$(sed -nE "s/^export DIE_AREA = 0 0 (\S+) (\S+)/\1x\2/p" $K/config.mk)
printf "{\"id\": \"dh52-%s\", \"odb\": \"%s\", \"image\": \"openroad/orfs:asap7lock\", \"mem_gb\": 8, \"grt\": true, \"rules_args\": [\"--all-kits\", \"--outline\", \"%s\", \"--title\", \"%s l49x DIE-HEAD-52\"]}\n" ${t//_/-} $P $OUTL $t > $G/check.json
bash $R/tools/autopilot/geom_check.sh $G > $G/geom.log 2>&1
echo "$t $(grep -h AP_AUTO_GEOM $G/geom.log | grep -v PNG | tail -n 1)"
