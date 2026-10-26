#!/bin/bash
# TOK-DS-6 2026-10-26: chained L14 indexer benches at SHARD_K = 3 (lower_bk option D: a rank's keys over 3 dies, one
# HBM stack a die) on the rank-3 fixture.  The new key p = 524287 is in rank 3 shard die 2 ([480598, 524288), 43,690
# keys); shard dies 0 / 1 hold 43,691 keys and write no IK_ROW.
#  (1) svc (die 2): tb_dsdv_svc_att_ik +img = the compiled IK_ROW frame of the shard-2 svc job on dsdv_svc_att x 16 sids;
#      golden = lower_idx layout writes.  base PASS; RTL MUT 4 / MUT 5 and compiler mutant ik_kb must FAIL.
#  (2) rg3: tb_dsdv_idx_rg3 +IMG = the compiled IDX_S job of the shard on 8 rg3 + 16 dsfd_ctrl_rg3 + HBM model.
#      base_d2: HBM = shard-2 state keys + the svc base dump; expected = fixture attn.idx.score[480598:524288].
#      base_d0: shard 0 (43,691 keys, [393216, 436907)), HBM = state keys only.
#      Must FAIL: chain_mut4 (HBM delta = svc MUT 4 dump), mut3 (RTL MUT 3), shard_k1 (compiler mutant: the TOK-DS-4
#      whole-quarter IDX_S spec B 393216 N 131072 on the shard-2 HBM / expectation).
# usage: run_idx_k3.sh <worktree> <fixture L14 dir> <out> <rg3 build dir (base + m3 objs)>
set -uo pipefail
W=$1; FX=$2; O=$3; RB=$4
V=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"; cd "$W"
git -C "$W" rev-parse HEAD > "$O/source_sha.txt"; git -C "$W" status --short -- tools rtl > "$O/source_dirty.txt"
for d in 0 2; do python3 tools/s81_dv/layer_prog/lower_idx.py images --fixtures "$FX" --out "$O/img_d$d" --k 3 --die $d > "$O/img_d$d.json" || exit 2; done
# ---- (1) svc builds (small) + runs (shard die 2 owns the new key)
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
svc() { "$O/svc_obj/m$2/Vtb_dsdv_svc_att_ik" +img=$O/img_d2/svc/$3 +dump=$O/dump_$1.txt > $O/svc_$1.log 2>&1;
        echo "svc $1: $(grep -h '^SVCIK ' $O/svc_$1.log | tail -1)"; }
svc base 0 base; svc mut4 4 base; svc mut5 5 base; svc ik_kb 0 ik_kb
[ "${SVC_ONLY:-0}" = 1 ] && exit 0
# ---- (2) rg3: HBM images = state + svc dumps
I=$O/img_d2/rg3
for c in base_d2 chain_mut4 shard_k1; do d=$O/img/rg3_$c; mkdir -p $d; cp $I/job.hex $I/exp.hex $d/; done
cp $I/job_shard_k1.hex $O/img/rg3_shard_k1/job.hex
python3 tools/s81_dv/layer_prog/lower_idx.py merge $I/hbm_state.hex $O/dump_base.txt $O/img/rg3_base_d2/hbm.hex
python3 tools/s81_dv/layer_prog/lower_idx.py merge $I/hbm_state.hex $O/dump_mut4.txt $O/img/rg3_chain_mut4/hbm.hex
cp $O/img/rg3_base_d2/hbm.hex $O/img/rg3_shard_k1/hbm.hex
d=$O/img/rg3_base_d0; mkdir -p $d; cp $O/img_d0/rg3/job.hex $O/img_d0/rg3/exp.hex $d/; cp $O/img_d0/rg3/hbm_state.hex $d/hbm.hex
rg3() { /usr/bin/time -v "$RB/$2/obj/Vtb_dsdv_idx_rg3" +IMG=$O/img/rg3_$3 > $O/rg3_$1.log 2>&1;
        echo "rg3 $1: $(grep -h -E '^TB_IDXRD (PASS|FAIL)$' $O/rg3_$1.log | tail -1) | $(grep -h TB_IDXRD_STATS $O/rg3_$1.log | tail -1) | wall=$(grep -h 'Elapsed (wall' $O/rg3_$1.log | awk '{print $NF}')"; }
rg3 base_d2 base base_d2 & rg3 base_d0 base base_d0 & rg3 chain_mut4 base chain_mut4 & rg3 mut3 m3 base_d2 & rg3 shard_k1 base shard_k1 &
wait
echo "all done $(date)"
