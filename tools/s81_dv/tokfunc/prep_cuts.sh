#!/bin/bash
# TOK-FUNC-S81 step 2: die kit + slice cuts + replay benches + slice kits for the per-layer runs (the S81-LBGAP/G8
# mkcuts.sh flow on the 72-frame RTL assembly).  Light python only (cut / tb / kit); builds run on the fleet.
#   prep_cuts.sh <ref> <die.v> <port_bind.json> <land_plan.json> <out dir> [cut ...]
# cuts default: the sets in tools/s81_dv/tokfunc/sets (cut_0S cut_0N cut_7 cut_3S_ctl).
# Env (G9 netlist rerun, STEWARD-TOK-S81-G9SIM 10-21): KIT_EXTRA = extra dv_rtl_kit.py args for the die kit AND every
# cut kit (e.g. "--select rtl_extra/<sha>/rtl/.../ot_s81sl_xs4.sv:<sha256>" = the GEN-selected physical source);
# PREFER72=0 drops tools/s81_dv/tokfunc/prefer_72.f (absent at refs older than the G7 token assembly).
set -u
H=$(cd "$(dirname "$0")" && pwd); W=$(cd "$H/../../.." && pwd)
REF=$1; DIEV=$(realpath $2); PB=$(realpath $3); LP=$(realpath $4); O=$(realpath -m $5); shift 5
CUTS=${*:-cut_0S cut_0N cut_7 cut_3S_ctl}
mkdir -p $O/cuts
KD=$O/KD
P72="--prefer-list tools/s81_dv/tokfunc/prefer_72.f"; [ "${PREFER72:-1}" = 0 ] && P72=""
# a ref older than the G7 token assembly has no prefer_72.f (dv_rtl_kit reads lists at --ref): drop it there (G9 553741303)
git -C $W cat-file -e "$REF:tools/s81_dv/tokfunc/prefer_72.f" 2>/dev/null || P72=""
if [ ! -f $KD/kit.json ]; then
  python3 $W/tools/s81_dv/dv_rtl_kit.py --ref $REF --port-bind $PB --top-v $DIEV --top dv_die --out $KD ${KIT_EXTRA:-} > $O/cuts/KD.kit.log 2>&1 \
    || { echo "KD KIT FAIL"; tail -5 $O/cuts/KD.kit.log; exit 2; }
fi
one() { c=$1; C=$O/cuts/$c; K=$O/cuts/K_$c; rm -rf $C $K
  python3 $W/tools/s81_dv/dv_slice_cut.py --die-v $DIEV --kit $KD --insts $H/sets/set_$c.txt --out $C --land-plan $LP --land-model --corner tt \
    > $O/cuts/$c.cut.log 2>&1 || { echo "$c CUT FAIL: $(tail -n 2 $O/cuts/$c.cut.log)"; return 1; }
  EPP=""; [ "$c" = cut_7 ] && EPP="--ep-probe u_s_7N:u_lep.u:mf --ep-probe u_s_7S:u_lep.u:mf"
  python3 $W/tools/s81_dv/dv_slice_tb.py --ports $C/slice_ports.json --out $C $EPP >> $O/cuts/$c.cut.log 2>&1 \
    || { echo "$c TB FAIL: $(tail -n 2 $O/cuts/$c.cut.log)"; return 1; }
  python3 $W/tools/s81_dv/dv_rtl_kit.py --ref $REF --port-bind $PB --top-v $C/slice_top.sv --top slice_top --out $K --prefer-list tools/s81_dv/frame_bench.f --prefer-list tools/s81_dv/svc_rs/rs_files.sh $P72 ${KIT_EXTRA:-} > $O/cuts/$c.kit.log 2>&1 \
    || { echo "$c KIT FAIL: $(tail -n 2 $O/cuts/$c.kit.log)"; return 1; }
  mkdir -p $K/tb; cp $C/tb_slice_top.sv $K/tb/; cp $W/tools/s81_dv/run_dv_slice.sh $K/
  echo "$c OK $(head -c 160 $O/cuts/$c.kit.log | head -1)"; }
for c in $CUTS; do one $c & done; wait
