#!/bin/bash
# TOK-S81-2 chain: L0 programme compile, legacy die-tree ages (baseline) vs bound data ages from the b2r plan_s11 bind
# (DIAGNOSTIC: the bind has 447 errors), same source, same vehicle tree_b178 (die.v a5778b98 == manifest netlist).
set -uo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
W=/srv/opentallas-scratch2/claude/wt/tok-s81-2
R=/srv/opentallas-scratch2/claude/tok-s81-2
cd "$W"
echo "SRC $(git rev-parse HEAD) dirty $(git status --porcelain | wc -l) $(date)"
python3 tools/s81_dv/layer_prog/test_bound_data.py > "$R/unit.log" 2>&1; echo "UNIT rc $?"
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,OT_ATTN_HCORE,OT_S81ENG_RR_N32,OT_S81C_HCORE_CTLA,OT_S81C_HCORE_RST_TIMED
export OT_S81_SELECTED_SOURCE_ROOT=$W OT_SVC_ALLQ=1
export OT_S81_SELECTED_ASBUILT_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_coll.json
export OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv
for m in col_h10 col_h9; do for v in x nx; do
  python3 tools/s81_dv/frame_schedule_asb.py --master "$m" --var "$v" --mem-gb 16 --out "$R/fs" --work "$R/work/${m}_$v" > "$R/fs_${m}_${v}.log" 2>&1
  echo "FS $m $v rc $? $(date +%T)"
done; done
export OT_XS_ASB_SCHEDULE_DIR=$R/fs
T=/srv/opentallas-scratch2/claude/tok-ds-12-1027/veh/tree_b178
F=/srv/opentallas-scratch2/claude/tok-ds-7-1027
( bash tools/s81_dv/tokfunc/compile_layers.sh "$W" "$T" $F/fix_r0 "$R/cc_L0_legacy" L0 > "$R/compile_L0_legacy.log" 2>&1; echo "L0 legacy rc $?" ) &
( OT_BOUND_DATA=/srv/opentallas-scratch2/claude/tok-s81-1/b2/out OT_BOUND_DATA_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_coll_s11.json OT_BOUND_DATA_DIAGNOSTIC=1 \
  bash tools/s81_dv/tokfunc/compile_layers.sh "$W" "$T" $F/fix_r0 "$R/cc_L0_bound" L0 > "$R/compile_L0_bound.log" 2>&1; echo "L0 bound rc $?" ) &
wait
rm -rf "$R/work"
echo "CHAIN_DONE $(date)"
