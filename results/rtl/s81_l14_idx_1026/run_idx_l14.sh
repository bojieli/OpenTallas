#!/bin/bash
# TOK-DS-4 2026-10-26: chained L14 indexer benches on the rank-3 fixture (the rank whose key quarter holds the new key).
#  (1) svc: tb_dsdv_svc_att_ik +img = the compiled IK_ROW frame on dsdv_svc_att x 16 sids; golden = lower_idx layout
#      writes of the fixture attn.idx.newkey.  base PASS; RTL MUT 4 (region hash w/o j[15:12]) / MUT 5 (scale byte of
#      key c^1) and compiler mutant ik_kb (KB without the rank offset) must FAIL.  The observed writes are dumped.
#  (2) rg3: tb_dsdv_idx_rg3 +IMG = the compiled IDX_S job (rank-3 quarter, 131,072 keys) on 8 rg3 + 16 dsfd_ctrl_rg3 +
#      HBM model; HBM = state keys + the svc base dump; expected = fixture attn.idx.score.  base PASS; chain mutant
#      (HBM delta = the svc MUT 4 dump: the new key written by the wrong slice) and RTL MUT 3 must FAIL.
# usage: run_idx_l14.sh <worktree> <fixture L14 dir> <out> <rg3 build dir (base + m3 objs)>
set -uo pipefail
W=$1; FX=$2; O=$3; RB=$4
V=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"; cd "$W"
python3 tools/s81_dv/layer_prog/lower_idx.py images --fixtures "$FX" --out "$O/img" || exit 2
# ---- (1) svc builds (small) + runs
SRC="rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv
 rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv
 rtl/dsrom_sys/s81_dv/svc_rs/test/tb_dsdv_svc_att_ik.sv"
for m in 0 4 5; do
  B=$O/svc_obj/m$m; mkdir -p $B
  "$V" --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DSVCQ_ENG_FG3 -DTB_MUT=$m \
    --top-module tb_dsdv_svc_att_ik -Mdir $B $SRC > $O/svc_build_m$m.log 2>&1 &
done
wait
for m in 0 4 5; do [ -x $O/svc_obj/m$m/Vtb_dsdv_svc_att_ik ] || { echo "SVC BUILD FAIL m$m"; tail $O/svc_build_m$m.log; exit 3; }; done
svc() { "$O/svc_obj/m$2/Vtb_dsdv_svc_att_ik" +img=$O/img/svc/$3 +dump=$O/dump_$1.txt > $O/svc_$1.log 2>&1;
        echo "svc $1: $(grep -h '^SVCIK ' $O/svc_$1.log | tail -1)"; }
svc base 0 base; svc mut4 4 base; svc mut5 5 base; svc ik_kb 0 ik_kb
[ "${SVC_ONLY:-0}" = 1 ] && exit 0
# ---- (2) rg3: HBM images = state + svc dumps
for c in base chain_mut4; do
  d=$O/img/rg3_$c; mkdir -p $d; cp $O/img/rg3/job.hex $O/img/rg3/exp.hex $d/
done
python3 tools/s81_dv/layer_prog/lower_idx.py merge $O/img/rg3/hbm_state.hex $O/dump_base.txt $O/img/rg3_base/hbm.hex
python3 tools/s81_dv/layer_prog/lower_idx.py merge $O/img/rg3/hbm_state.hex $O/dump_mut4.txt $O/img/rg3_chain_mut4/hbm.hex
rg3() { /usr/bin/time -v "$RB/$2/obj/Vtb_dsdv_idx_rg3" +IMG=$O/img/rg3_$3 > $O/rg3_$1.log 2>&1;
        echo "rg3 $1: $(grep -h -E '^TB_IDXRD (PASS|FAIL)$' $O/rg3_$1.log | tail -1) | $(grep -h TB_IDXRD_STATS $O/rg3_$1.log | tail -1) | wall=$(grep -h 'Elapsed (wall' $O/rg3_$1.log | awk '{print $NF}')"; }
rg3 base base base & rg3 chain_mut4 base chain_mut4 & rg3 mut3 m3 base &
wait
echo "all done $(date)"
