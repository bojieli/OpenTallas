#!/bin/bash
# STW-S81d-TOK 10-22: per-layer cut kits on the cap30 framecal die (3b4b975d = cap30 64d4be888 + 22 chained-frame reset
# stations). Kits from the EXECUTED bind (--bind-case + --bind-snapshot-bytes at the GEN ref 528fc3c9f), DIE kit wrappers
# (die_sim_wrappers on this die.v) applied, --landing-reset none (wrappers carry OT_RST_LAND), frame x-lane flight model.
set -u
T=/home/ubuntu/wt/s81d-tok-1022; W=/srv/opentallas-scratch/claude/stw-s81d-tok/fc30; G=/srv/opentallas-scratch/claude/stw-s81c-cap30/gen-main
B=$W/bind/bind; REF=528fc3c9f; REPO=/home/ubuntu/OpenTallas; O=$W/cuts; mkdir -p $O
CUTS=${*:-cut_0S cut_0N cut_7 cut_3S_ctl}
KA=(--repo $REPO --ref $REF --port-bind $B/port_bind.json --bind-case $B/bind_case.json --bind-snapshot-bytes --bind-root-bytes)
cd $T
if [ ! -f $W/KD/kit.json ]; then
  python3 tools/s81_dv/dv_rtl_kit.py "${KA[@]}" --top-v $B/die.v --top dv_die --out $W/KD > $W/KD.kit.log 2>&1 || { echo "KD KIT FAIL"; tail -5 $W/KD.kit.log; exit 2; }
fi
head -1 $W/KD.kit.log
one() { c=$1; C=$O/$c; K=$O/K_$c; rm -rf $C $K
  python3 tools/s81_dv/dv_slice_cut.py --repo $REPO --die-v $B/die.v --kit $W/KD --insts tools/s81_dv/tokfunc/sets/set_$c.txt --out $C \
     --land-plan $G/land.json --land-model --corner tt --landing-reset none > $O/$c.cut.log 2>&1 || { echo "$c CUT FAIL: $(tail -n 2 $O/$c.cut.log)"; return 1; }
  EPP=""; [ "$c" = cut_7 ] && EPP="--ep-probe u_s_7N:u_lep.u:mf --ep-probe u_s_7S:u_lep.u:mf"
  python3 tools/s81_dv/dv_slice_tb.py --ports $C/slice_ports.json --out $C $EPP >> $O/$c.cut.log 2>&1 || { echo "$c TB FAIL: $(tail -n 2 $O/$c.cut.log)"; return 1; }
  python3 tools/s81_dv/dv_rtl_kit.py "${KA[@]}" --top-v $C/slice_top.sv --top slice_top --out $K --prefer-list tools/s81_dv/frame_bench.f \
     --prefer-list tools/s81_dv/svc_rs/rs_files.sh --prefer-list tools/s81_dv/tokfunc/prefer_72.f > $O/$c.kit.log 2>&1 || { echo "$c KIT FAIL: $(tail -n 2 $O/$c.kit.log)"; return 1; }
  mkdir -p $K/tb; cp $C/tb_slice_top.sv $K/tb/; cp tools/s81_dv/run_dv_slice.sh $K/
  python3 $(dirname $0)/apply_wrap_fc30.py $W $K > $O/$c.wrap.log 2>&1 || { echo "$c WRAP FAIL: $(tail -n 3 $O/$c.wrap.log)"; return 1; }
  echo "$c OK $(head -1 $O/$c.kit.log) | $(tail -1 $O/$c.wrap.log)"; }
for c in $CUTS; do one $c & done; wait
