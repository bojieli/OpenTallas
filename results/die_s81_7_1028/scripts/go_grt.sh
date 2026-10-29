#!/bin/bash
# DIE-S81-7 (copy of DIE-S81-5 go_grt.sh, paths only): die GRT incl clock for kit variant $1 = die_trial signal kit (M4-M7 adj 0.75) + region=partition link_htree
# clock (M8-M9) in ONE global_route, 50 congestion iterations, -critical_nets_percentage 0, TT + FF in parallel.
# Launch: ot-run --mem 120 --threads 16 --dir $O -- bash go_grt.sh A
set -u
V=${1:?variant}
WT=/srv/opentallas-scratch2/claude/wt/die-s81-7; O=/srv/opentallas-scratch2/claude/die-s81-7; R=$WT/results/die_s81_7_1028/scripts; PL=/srv/opentallas-scratch2/claude/die-s81-5/plan_s5.json
K=$O/kit_$V; CK=$O/clk_$V
echo START $(date) host $(hostname) code $(git -C $WT rev-parse --short HEAD) plan $(sha256sum $PL | cut -c1-12) variant $V
mkdir -p $CK; cp $K/clock/{ctree.v,ctree.tcl,tree.json} $CK/; cp $CK/ctree.tcl $CK/ctree_ck89.tcl
for C in TT FF; do
  OC=$O/out_${V}_$C; mkdir -p $OC
  CORNER=$C ADJ=0.75 python3 $R/mk_combo_dcm.py $K $CK $OC > $O/mk_${V}_$C.log 2>&1 || { echo MK_FAIL $C; exit 1; }
  if [ "${CKNDR:-0}" = 1 ]; then   # COORD 01:4x: clock on a 2W2S NDR (M8/M9 width 0.08 / spacing 0.08 = 2x the 0.04 / 0.04 LEF default); layers stay disjoint (signal M4-M7, clock M8-M9)
    sed -i "/^create_clock -name dck /a create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.08 M9 0.08}\\nassign_ndr -ndr CK2W2S -all_clocks" $OC/combo.tcl
    grep -c "assign_ndr" $OC/combo.tcl
  fi
  docker run -d --name dies81-7$V-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM \
    -v $K:/work:ro -v $OC:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait dies81-7$V-$C; docker rm dies81-7$V-$C >/dev/null; done
echo COMBO_DONE $(date)
for C in TT FF; do OC=$O/out_${V}_$C; grep -E "^(M[1-9]|Total) " $OC/combo_$C.log | tail -10; grep -E "GRT-0101|GRT-0103|GRT-0115|critical" $OC/combo_$C.log | head -3; tail -2 $OC/combo_$C.log; done
echo GRT_DONE $(date)
