#!/usr/bin/env bash
# HBM-ATTGAP (10-19): fleet driver -- (A) the sub-run attention unit pre-check on the d4g die SM master, then (B) the
# on-die cross-SM PV merge on the real N512 SU arithmetic with the RTL nodes of (A).
#   run_att_gap.sh REV KVDIR BUNDLE OUTROOT [SUBRUN=32] [LAYER=2]
# A: att_images.py unit --subrun SUBRUN (all 10 SMs x QK/PV sub-runs; must PASS, programme residency <= 1,024 words,
#    20-node merge == fixture) + 'early' schedule mutant on qk sm_SW0 sub-runs (must FAIL).
# B: att_merge_su.py vectors (pos + ORDER mutant) -> tb_su_static_arithmetic (Verilator 5.050, die lane MLAT 4 / ALAT 3 /
#    LEAF 1): base must PASS; ADDR / PHASE / DATA tb mutants and the ORDER control must FAIL.
# SKIP_UNIT=1: (B) only, on the nodes of an earlier (A).  MEM_SU: the hierarchical SU build was killed at 24 GB.
# REUSE_OBJ: an already built tb_hbm_smh_attn obj dir of the same bundle + tb (hard-linked into the work dir).
set -uo pipefail
REV=$1; KV=$2; BUNDLE=$3; OUT=$4; SUB=${5:-32}; L=${6:-2}; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
SHA=$(git -C "$WT" rev-parse "$REV")
ssh "$HOST" "mkdir -p $OUT/src $OUT/out $OUT/work_pos && rm -rf $OUT/src/*" || exit 2
git -C "$WT" archive "$SHA" tools/hbm_layer_vehicle tools/hbm_sm_attention tools/hgi_sim tools/hdc_golden_v41.py \
  tools/hdc_golden.py tools/hbm_static rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv \
  rtl/hbm_accel/generic/adapters/static_su rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc rtl/proto/ot_fp32_add_rne_pipe.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2 | ssh "$HOST" "tar -x -C $OUT/src" || exit 2
echo "$SHA" | ssh "$HOST" "cat > $OUT/src/REV"
if [ -n "${REUSE_OBJ:-}" ]; then ssh "$HOST" "[ -d $OUT/work_pos/obj_d0_p0 ] || cp -al $REUSE_OBJ $OUT/work_pos/obj_d0_p0"; fi
VL='VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator'
T="cd $OUT/src && $VL HDC_V41_ARITH=chunk8 python3 tools/hbm_layer_vehicle/att_images.py unit --kv $KV --layer $L --bundle $BUNDLE --subrun $SUB"
if [ -n "${SKIP_UNIT:-}" ]; then R1=0; else
/home/ubuntu/bin/ot-run --mem ${MEM:-64} --threads 16 --dir "$OUT" -- bash -c "$T --work $OUT/work_pos --out $OUT/out/L${L}_s${SUB}_pos.json \
  > $OUT/out/L${L}_s${SUB}_pos.log 2>&1; rc=\$?; $T --work $OUT/work_pos --smut early --sms 0 --kinds qk --out $OUT/out/L${L}_s${SUB}_mut_early.json \
  > $OUT/out/L${L}_s${SUB}_mut_early.log 2>&1; echo POS_RC \$rc EARLY_RC \$?; tail -n 1 $OUT/out/L${L}_s${SUB}_pos.log; exit \$rc"
R1=$?; fi
echo "ATT_GAP_UNIT pos_rc=$R1"
[ "$R1" = 0 ] || exit 1
NODES=$OUT/out/L${L}_s${SUB}_pos.nodes.npz
M="cd $OUT/src && export $VL && set -e; mkdir -p $OUT/merge; \
python3 tools/hbm_layer_vehicle/att_merge_su.py vectors --nodes $NODES --out $OUT/merge/vec_pos > $OUT/merge/vec_pos.log; \
python3 tools/hbm_layer_vehicle/att_merge_su.py vectors --nodes $NODES --out $OUT/merge/vec_order --order > $OUT/merge/vec_order.log; \
nops=\$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))[\"nops\"])' $OUT/merge/vec_pos/programme.json); \
d=rtl/hbm_accel/generic/adapters/static_su; \
\$VERILATOR --binary --timing --hierarchical -O1 -j 8 -CFLAGS -O0 -Wno-fatal --top-module tb_su_static_arithmetic \
 -GNOPS=\$nops -GMLAT=4 -GALAT=3 -GLEAF=1 --Mdir $OUT/merge/obj \
 \$d/arithmetic/ot_hbm_su_static_ins.sv \$d/arithmetic/ot_hbm_su_static_lane.sv \$d/arithmetic/ot_hbm_su_static_arithmetic.sv \
 \$d/arithmetic/tb_su_static_arithmetic.sv \$d/data_store/ot_hbm_su_static_data_store.sv \$d/data_store/ot_hbm_su_static_pinned_bank.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv \
 rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > $OUT/merge/build.log 2>&1; \
set +e; B=$OUT/merge/obj/Vtb_su_static_arithmetic; \
\$B +DIR=$OUT/merge/vec_pos > $OUT/merge/pos.log 2>&1; echo POS \$?; \
for m in ADDR PHASE DATA; do \$B +DIR=$OUT/merge/vec_pos +MUT_\$m > $OUT/merge/mut_\$m.log 2>&1; echo MUT_\$m \$?; done; \
\$B +DIR=$OUT/merge/vec_order > $OUT/merge/mut_ORDER.log 2>&1; echo MUT_ORDER \$?; \
grep -h 'SU_ARITH' $OUT/merge/*.log | cut -c1-240"
/home/ubuntu/bin/ot-run --mem ${MEM_SU:-96} --threads 8 --dir "$OUT" -- bash -c "$M"
echo "ATT_GAP_MERGE rc=$?"
