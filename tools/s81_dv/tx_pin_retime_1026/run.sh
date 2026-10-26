#!/bin/bash
# Run only through ot-run; source remains off by default pending proof and physical gates.
set -eu
R=$(dirname "$(readlink -f "$0")")
REPO=$(readlink -f "$R/../../..")
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
VL=$HOME/.local/opentallas-tools/bin/verilator
"$VL" --binary --timing -j 8 -CFLAGS -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE --top-module tb_pin_front "$REPO/rtl/lib/ot_rst_relay.sv" "$REPO/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv" "$REPO/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv" "$REPO/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$R/tb_pin_front.sv" --Mdir "$OUT/obj_front" -o sim > "$OUT/front_build.log" 2>&1
"$OUT/obj_front/sim" > "$OUT/front_run.log" 2>&1
cat "$OUT/front_run.log"
"$VL" --binary --timing --output-split 10000 --output-split-cfuncs 1000 -j 16 -CFLAGS -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE --top-module tb_tx_miter "$REPO/rtl/lib/ot_rst_relay.sv" "$REPO/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv" "$REPO/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_l20s.sv" "$REPO/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$R/tx_reference.sv" "$R/tb_tx_miter.sv" --Mdir "$OUT/obj_tx" -o sim > "$OUT/tx_build.log" 2>&1
"$OUT/obj_tx/sim" > "$OUT/tx_run.log" 2>&1
cat "$OUT/tx_run.log"
