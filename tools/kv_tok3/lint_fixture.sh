#!/bin/bash
# KV-TOK3 10-19: elaboration control of the startup-repaired N-step fixture on an EXISTING archived cut (copied, never
# mutated): generate authority/fault bind from the copy, build the bench tb exactly as run_kv_attn_mu.sh does, then
# Verilator 5.050 --lint-only (full elaboration incl. every hierarchical reference of the fixture).  No simulation.
# usage: lint_fixture.sh ARCHIVED_CUT_DIR KSRC OUTDIR
set -u
SRC=$1; KSRC=$2; OUT=$3; H=$(cd "$(dirname "$0")" && pwd)/tools/qwen_layerbench
[ -e "$OUT" ] && { echo "REFUSED: $OUT exists"; exit 2; }
mkdir -p $OUT; cp -r $SRC $OUT/cut; SL=$OUT/cut
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
python3 -I $H/gen_kva_authority.py --cut-dir $SL --out $SL || exit 2
TOP=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['top'])" $SL/slice.json)
python3 $H/slice_smoke.py $SL/slice.json --out $OUT/tb_$TOP.sv --src 'i_n_clk_hbm_.*=hck' || exit 2
MAC=$KSRC/physical/qkd_astk_strip/macros
QKDEF=""; case "$TOP" in qwk_stk_*) QKDEF="+define+KVA_QK_ONLY";; esac
CC=dut.kvs_attn.u_attn.ctl.g_ld.codec.fault_cause
/usr/bin/time -v -o $OUT/lint.time verilator --lint-only --timing $QKDEF +define+KVA_CODEC_CAUSE=$CC -Wno-fatal -Wno-lint -Wno-style \
  -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-MULTIDRIVEN --top-module tb_$TOP -GMUT=0 \
  +define+SLICE_DRIVE=\"$H/drive_qwk_slice_attn_mu.svh\" +define+IDLE_EDGES=200 +define+TAIL_EDGES=50 +incdir+$H +incdir+$SL \
  -f $SL/$TOP.f $MAC/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v $MAC/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v \
  $KSRC/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v $OUT/tb_$TOP.sv \
  $H/kva_authority_path.sv $H/kva_identity_scoreboard_n.sv > $OUT/lint.log 2>&1
rc=$?; echo "LINT rc=$rc errors=$(grep -c '%Error' $OUT/lint.log)"; grep -m12 '%Error' $OUT/lint.log; exit $rc
