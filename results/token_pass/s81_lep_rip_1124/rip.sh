#!/bin/bash
# S81-LEPFLF-HOLD: measure lep ri latency per define profile (hab top = s_7N HOST_EN 1 form), P_PROD 1 (die opt-ins).
set -u
B=$(pwd); T=/srv/opentallas-scratch2/claude/s81-allfix-int/amd1_tree
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
L=$T/rtl/dsrom_sys/s81_link; SL=$T/rtl/dsrom_sys/s81_dv/slice
COMMON=$(sed -n '/^COMMON="/,/"$/p' bench.sh | sed 's/^COMMON="//; s/"$//' | sed "s#\$T#$T#g; s#\$L#$L#g; s#\$SL#$SL#g")
D="+define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2"
run() { n=$1; shift
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style +incdir+$L $D "$@" \
    --top-module tb_s81sl_lep_hab -Mdir $B/rip_$n $COMMON orig.sv tb_riphab.sv -GP_PROD=1 --build-jobs 8 \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $B/rbuild_$n.log 2>&1 || { echo "BUILD_FAILED $n"; grep -m5 %Error $B/rbuild_$n.log; return; }
  $B/rip_$n/Vtb_s81sl_lep_hab > $B/rip_$n.log 2>&1; grep "^RIT" $B/rip_$n.log | awk '{print $2}' > $B/rit_$n.txt
  echo "$n: $(grep -m1 -E '^(PASS|FAIL) ' $B/rip_$n.log | cut -c1-60) | ri beats $(wc -l < $B/rit_$n.txt) first $(head -1 $B/rit_$n.txt)"
}
run rip0 &
run rip1 +define+OT_S81SL_LEP_RIP1 &
run rip3 +define+OT_S81SL_LEP_RIP3 &
run kit_mu_LP_t2 +define+OT_S81SL_LEP_CRP2 +define+OT_S81SL_LEP_WREP5 +define+OT_S81SL_LEP_RIP3 +define+OT_S81SL_LEP_ROS3 &
run crp2_wrep5_ros3 +define+OT_S81SL_LEP_CRP2 +define+OT_S81SL_LEP_WREP5 +define+OT_S81SL_LEP_ROS3 &
wait
for n in rip1 rip3 kit_mu_LP_t2 crp2_wrep5_ros3; do
  python3 -I - $B/rit_rip0.txt $B/rit_$n.txt $n <<'PY'
import sys,collections
a=[int(x) for x in open(sys.argv[1])]; b=[int(x) for x in open(sys.argv[2])]
n=min(len(a),len(b)); d=collections.Counter(b[i]-a[i] for i in range(n))
print(f"{sys.argv[3]} vs rip0: beats {len(a)}/{len(b)} per-beat ri delta (cycles) {dict(sorted(d.items()))}")
PY
done
