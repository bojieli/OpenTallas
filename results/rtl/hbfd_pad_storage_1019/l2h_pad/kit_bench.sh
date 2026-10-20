#!/bin/bash
# Kit bench for hbfd_pad SAFE_STORAGE (L2H-PAD 10-19). Run from the repo root (closure daemon source checkout).
#   kit_bench.sh pass   RUN  -> 72-shape x 7000-edge golden differential, prints PAD_STORAGE_PASS shapes=72 ...
#   kit_bench.sh mut<m> RUN  -> mutant m (1 wrong slot, 2 early warmup, 3 extra edge, 4 collision/unlanded reset)
#                               asserted on the kit shape W=17 N=115: must FAIL with PAD_MUTANT_WITNESS mutant=<m> W=17 N=115
set -u
MODE=$1; RUN=$2; mkdir -p "$RUN"
cp rtl/hbm_accel/die_glue/hbfd_pad.sv "$RUN/hbfd_pad.sv"
cp rtl/hbm_accel/die_glue/tb_hbfd_pad_storage.sv "$RUN/tb.sv"
cp rtl/hdc/ot_hdc_delay.sv "$RUN/delay.sv"
cp physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$RUN/macro.sv"
cd "$RUN"
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && PATH="$_d:$PATH"; done; export PATH
verilator --version
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -j 4 --top-module tb_hbfd_pad_storage \
  tb.sv hbfd_pad.sv delay.sv macro.sv -o vpad > build.log 2>&1 || { echo PAD_BUILD_FAIL; tail -30 build.log; exit 3; }
case "$MODE" in
  pass) ./obj_dir/vpad; exit $? ;;
  mut[1-4]) m=${MODE#mut}; ./obj_dir/vpad +ASSERT_MUTANT=$m +ASSERT_W=17 +ASSERT_N=115; exit $? ;;
  *) echo "usage: kit_bench.sh pass|mut1..4 RUN"; exit 2 ;;
esac
