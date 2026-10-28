#!/bin/bash
# TOK-DS-12 chain: main 542a4f321 + TOK-DS-12 plan-LK gate -> re-extract 4 as-built frame calendars -> L0 + L2 compile
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
W=/srv/opentallas-scratch2/claude/wt/tok-ds-12-1027
R=/srv/opentallas-scratch2/claude/tok-ds-12-1027
cd "$W"
echo "SRC $(git rev-parse HEAD) $(date)"
python3 tools/s81_dv/test_asb_direct_schedule.py > "$R/unit.log" 2>&1
python3 tools/s81_dv/test_asb_schedule_gate.py >> "$R/unit.log" 2>&1
python3 tools/s81_dv/layer_prog/test_xs_asb_profile.py >> "$R/unit.log" 2>&1
for m in col_h10 col_h9; do for v in x nx; do
  python3 tools/s81_dv/frame_schedule_asb.py --master "$m" --var "$v" --mem-gb 16 --out "$R/fs" --work "$R/work/${m}_$v" > "$R/fs_${m}_${v}.log" 2>&1
  echo "FS $m $v rc 0 $(date +%T)"
done; done
bash tools/s81_dv/tokfunc/mk_vehicle_current.sh "$W" /srv/opentallas-scratch2/claude/tok-ds-dskr/veh/tree_fc31 "$R/veh" > "$R/veh.log" 2>&1
export OT_S81_SELECTED_DEFINES=DSFD_PQ_STATIC_X2,S81CTRL_SRAM_FIFO,S81CTRL_SRAM_P192,S81CTRL_NATIVE32,OT_COLL_NATIVE32,OT_COLL_NATIVE32_OFF,OT_S81ENG_TAP_N32R2,OT_S81SL_KV_TRANSPORT,OT_SVC_ALLQ,SU_SMU_T,OT_ATTN_HCORE,OT_S81ENG_RR_N32,OT_S81C_HCORE_CTLA,OT_S81C_HCORE_RST_TIMED
export OT_S81_SELECTED_SOURCE_ROOT=$W OT_SVC_ALLQ=1
export OT_S81_SELECTED_ASBUILT_MANIFEST=physical/die_plan/s81/bind/asbuilt_b178_coll.json
export OT_S81_SELECTED_CHILD_FILES=rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv
export OT_XS_ASB_SCHEDULE_DIR=$R/fs
F=/srv/opentallas-scratch2/claude/tok-ds-7-1027
( bash tools/s81_dv/tokfunc/compile_layers.sh "$W" "$R/veh/tree_b178" $F/fix_r0 "$R/cc_L0" L0 > "$R/compile_L0.log" 2>&1; echo "L0 rc $?" ) &
( OT_IDX_SHARD_DIE=0 bash tools/s81_dv/tokfunc/compile_layers.sh "$W" "$R/veh/tree_b178" $F/fix_r3new "$R/cc_L2" L2 > "$R/compile_L2.log" 2>&1; echo "L2 rc $?" ) &
wait
echo "CHAIN_DONE $(date)"
