#!/usr/bin/env bash
# HBM-COLLFUSE2 (10-20): MEASURE the fused last-RS/first-AG Qwen AR step (lever L1) on the release COLL source (GEN2e4 11bf17f45,
# COLL files byte-identical to gen2e3 9787e078a).  tb_xdie_hbm_step 'rs' kind with --frames P IS an exchange-and-add step: both
# dies TX frame f from sector SB+f/4 and reduce the SAME local frame f with the landed peer frame (xdie_hbm_step_compile.py
# compile_die: TX Sd.vm(v,f,d,sec) and local operand Sd.vm(R-13,f,d,sec(f))), each die publishes local+peer (2-operand IEEE
# sum, order-free) for all P frames = the fused step of the TP8 hypercube's last dimension (RS16+AG16 -> one 32-frame step).
# usage: run_fx.sh SRC OUT
set -u
SRC=$(realpath "$1"); OUT=$(realpath -m "$2"); mkdir -p "$OUT"
S4=$SRC/rtl/hbm_accel/generic/collective/xdie/run_xdie_hbm_step4.sh
# reference steps of the as-is chain (qw rs64/rs32/rs16/rs4) + causal mutants, unchanged script
bash "$S4" "$SRC" "$OUT/s4" qw  > "$OUT/s4_qw.summary" 2>&1; echo "s4 qw rc=$?" >> "$OUT/rc.txt"
bash "$S4" "$SRC" "$OUT/s4m" mut > "$OUT/s4_mut.summary" 2>&1; echo "s4 mut rc=$?" >> "$OUT/rc.txt"
# fused-specific negative: die 1 frame 1 local operand read from another frame (TX src != reduce src) at the fused size 32
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
C="python3 $SRC/tools/xdie_hbm_step_compile.py"
echo done > "$OUT/done.txt"
