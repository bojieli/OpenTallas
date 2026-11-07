#!/bin/bash
# gen_kits.sh: generate one kit: CORE VIEW FORM TAG TYPE(opsa|opsb)
S=/srv/opentallas-scratch3/claude/die-hbm-83-opsg; R=$S/repo; F=results/die_hbm_1106/opsg_gp; P=/srv/opentallas-scratch2/claude/kw24/hbm_d44v_7281a
C=$1; VW=$2; FM=$3; T=$4; TY=$5
OUT=$S/kits/${C}_$T; mkdir -p $OUT $S/log
[ $TY = opsa ] && IF='u_t.u_g.g_bank[{k}].u_b.g_m11n.u_m' || IF='u_g.g_bank[{k}].u_b.g_m11n.u_m'
cd $R && prlimit --as=48000000000 python3 physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py --views $S/v/views.json --view "$C@$VW" --out $OUT --recipe-key ${C}__gp \
  --clock-pin-entry on --core-macros off --util 0.40 --max-fanout 8 --sigmax M6 --orfs-var ADDER_MAP_FILE= --orfs-var OT_HOLD_REPAIR_SCOPE=reg2reg \
  --macro-placement $F/place_$FM.json --macro-inst-fmt "$IF" --reg-guide-boxes $F/boxes_${FM}_$TY.json --cts-delaybuf-strip \
  --clock-regions $P/core_clock_regions.json > $S/log/gen_${C}_$T.log 2>&1
echo "GEN rc=$? $C $T $(ls -d $OUT/*/freeze.json 2>/dev/null)"; tail -2 $S/log/gen_${C}_$T.log | cut -c1-300
