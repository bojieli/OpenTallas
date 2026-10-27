#!/bin/bash
# CLOCK-KV-R8 build: d4 pushdown + edge-entry plan (D-KV-CLK-R8) -> combo die GRT (kit signals M4-M7 + clock M8/M9, TT+FF)
# -> post chain (mesh transient on routed tree arrivals, stub STA on native stub-net SPEF incl. band trunk/comb) -> report
# -> die_sta_related (flat derates) -> render.  No balance / stubtrim / pad step exists in this chain.
set -e
D=/srv/opentallas-scratch2/claude/clock-kv-r8-1026; O=$D/b5; T=/srv/opentallas-scratch2/claude/wt/clock-kv-r1-1026/tools/die_plan
IN=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026; K=$IN/kit; PL=$D/d5/plan.json; export PYTHONPATH=$IN/pylib
echo "start $(date -Is) host $(hostname) tools $(git -C $T rev-parse --short HEAD)"
rm -rf $O; mkdir -p $O; cp $D/d5/{mesh.json,nets.json,place.json,ctree.v,plan.json} $O/
python3 $T/die_clock_mesh.py combo $O --kit $K --plan $PL --mesh-vias
MEM=${CMEM:-32} bash $O/run_combo.sh; grep -H EXIT $O/combo_TT.log $O/combo_FF.log
bash $T/die_clock_mesh_post.sh $O $PL
for C in TT FF; do python3 $T/die_sta_related.py $O --plan $PL --out $O/rel_$C --corner $C > $O/rel_$C.log 2>&1 || echo "rel $C rc=$?"; cat $O/rel_$C.log | grep -v SUMMARY; done
python3 $T/die_clock_mesh.py render $O --plan $PL --out $O/render.png || true
echo "CHAIN_DONE $(date -Is)"
