#!/bin/bash
# DIE-KV-47 2026-10-30: after the routed-DB hold ECO (kv47_eco_f/5_2_route.odb, one incremental detailed_route with every
# non-ECO net frozen): install it as the kit's 5_2_route.odb (+ ECO DRT metrics into 5_2_route.json, originals kept as
# *.p6b), then fill + finish (as die-kv-45-1030/fill_signoff.sh), kit post, tag a-kv (7e30df72969) signoff.py (fresh RCX)
# + post-route lec.py on the same 6_final.   post_eco.sh KITDIR NAME
set -uo pipefail
K=$(cd "$1" && pwd); N=$2; T=/srv/opentallas-scratch2/claude/die-kv-45-1030/t_7e30df72969/tools/die_plan
E=$K/kv47_eco_f; S=$K/kv47_status
RS=$(ls -d $K/run/results/asap7/*/base); LG=$(ls -d $K/run/logs/asap7/*/base); RP=$(ls -d $K/run/reports/asap7/*/base)
grep -q "^rc=0" $E/eco.log || { echo "ECO not rc=0" >> $S; exit 3; }
V=$(grep "Number of violations" $E/eco.log | tail -1 | awk '{print $NF}' | tr -d .)
A=$(grep -E "ANT-0002|Found .* net violations" $E/eco.log | tail -1 | grep -oE "[0-9]+ net" | awk '{print $1}')
echo "eco install $(date): final DRT violations $V antenna_nets ${A:-?}" >> $S
[ "$V" = 0 ] || { echo "ECO DRT not clean" >> $S; exit 4; }
for f in $RS/5_2_route.odb $LG/5_2_route.json $RP/5_route_drc.rpt; do [ -f $f.p6b ] || cp -p $f $f.p6b; done
cp $E/5_2_route.odb $RS/5_2_route.odb; cp $E/5_route_drc.rpt $RP/5_route_drc.rpt
python3 -I - "$LG/5_2_route.json" "$V" "${A:-}" <<'PY'
import json, sys
p, v, a = sys.argv[1], int(sys.argv[2]), sys.argv[3]
d = json.load(open(p + ".p6b"))
d["detailedroute__route__drc_errors"] = v
if a != "": d["detailedroute__antenna__violating__nets"] = int(a)
d["kv47_eco"] = "DIE-KV-47 routed-DB hold ECO: drc/antenna = the incremental ECO detailed_route + check_antennas (kv47_eco_f/eco.log); p6b metrics in 5_2_route.json.p6b"
json.dump(d, open(p, "w"), indent=2)
PY
rm -f $RS/5_3_fillcell.odb $RS/5_route.odb $RS/6_1_fill.odb $RS/6_final.*
docker run --rm --name kv47-$N-fill --cpus 16 --memory 40g --memory-swap 40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/kv47_orfs_hold_mm.log 2>&1 || exit 9; M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16"; rc=0; $M do-5_3_fillcell do-5_route do-5_route.sdc > /work/kv47_fill.log 2>&1 && $M do-finish >> /work/kv47_fill.log 2>&1 || rc=$?; chown -R 1000:1000 /work; exit $rc'
rc=$?; echo "fill+finish rc=$rc $(date)" >> $S; [ $rc = 0 ] || exit $rc
bash "$K/run_kit_kv.sh" "$K" post 32 8 > $K/kv47_kitpost.log 2>&1; echo "kitpost rc=$? $(date)" >> $S
D=$K/kv47_tag; mkdir -p $D
SIGNOFF_DOCKER=docker python3 -I $T/signoff.py run --run-dir $K/run --kit $K --corners tt,ff --ff-vclk auto --out $D/signoff --image openroad/orfs:asap7lock > $D/signoff.log 2>&1; echo "tag signoff rc=$? $(date)" >> $S
VV=$(ls $K/run/results/asap7/*/base/6_final.v | head -1); VV=/work/${VV#$K/}
docker run --rm --name kv47-$N-lec --memory=32g --cpus=8 -v $K:/work:ro -v $D:/eco -v $T:/m:ro openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /m/lec.py /work --netlist $VV --out /eco/lec" > $D/lec.log 2>&1; echo "lec rc=$? $(date)" >> $S
sha256sum $RS/6_final.odb >> $S
grep -E '^SIGNOFF|^  - ' $D/signoff.log | head -5 >> $S; tail -n 2 $D/lec.log >> $S; echo "DONE $(date)" >> $S
