#!/bin/bash
set -eu
OUT=/srv/opentallas-scratch/claude/codex-s81-tx-ring-2208/phase4
mkdir -p "$OUT"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal -Wno-WIDTH --top-module tb_tx_ring_phase -GPH=0 -GD=4 -GK=2 rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_tx_region_ring.sv tools/s81_dv/tx_export_1021/tb_tx_ring_phase.sv --Mdir "$OUT/obj_4_2_0" -o sim > "$OUT/build_4_2_0.log" 2>&1
"$OUT/obj_4_2_0/sim" > "$OUT/run_4_2_0.log" 2>&1
cat "$OUT/run_4_2_0.log"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal -Wno-WIDTH --top-module tb_tx_ring_phase -GPH=9000 -GD=4 -GK=2 rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_tx_region_ring.sv tools/s81_dv/tx_export_1021/tb_tx_ring_phase.sv --Mdir "$OUT/obj_4_2_9000" -o sim > "$OUT/build_4_2_9000.log" 2>&1
"$OUT/obj_4_2_9000/sim" > "$OUT/run_4_2_9000.log" 2>&1
cat "$OUT/run_4_2_9000.log"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal -Wno-WIDTH --top-module tb_tx_ring_phase -GPH=-9000 -GD=4 -GK=2 rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_tx_region_ring.sv tools/s81_dv/tx_export_1021/tb_tx_ring_phase.sv --Mdir "$OUT/obj_4_2_-9000" -o sim > "$OUT/build_4_2_-9000.log" 2>&1
"$OUT/obj_4_2_-9000/sim" > "$OUT/run_4_2_-9000.log" 2>&1
cat "$OUT/run_4_2_-9000.log"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal -Wno-WIDTH --top-module tb_tx_ring_phase -GPH=0 -GD=8 -GK=3 rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_tx_region_ring.sv tools/s81_dv/tx_export_1021/tb_tx_ring_phase.sv --Mdir "$OUT/obj_8_3_0" -o sim > "$OUT/build_8_3_0.log" 2>&1
"$OUT/obj_8_3_0/sim" > "$OUT/run_8_3_0.log" 2>&1
cat "$OUT/run_8_3_0.log"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal -Wno-WIDTH --top-module tb_tx_ring_phase -GPH=9000 -GD=8 -GK=3 rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_tx_region_ring.sv tools/s81_dv/tx_export_1021/tb_tx_ring_phase.sv --Mdir "$OUT/obj_8_3_9000" -o sim > "$OUT/build_8_3_9000.log" 2>&1
"$OUT/obj_8_3_9000/sim" > "$OUT/run_8_3_9000.log" 2>&1
cat "$OUT/run_8_3_9000.log"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal -Wno-WIDTH --top-module tb_tx_ring_phase -GPH=-9000 -GD=8 -GK=3 rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/idx/dsdv_tx_region_ring.sv tools/s81_dv/tx_export_1021/tb_tx_ring_phase.sv --Mdir "$OUT/obj_8_3_-9000" -o sim > "$OUT/build_8_3_-9000.log" 2>&1
"$OUT/obj_8_3_-9000/sim" > "$OUT/run_8_3_-9000.log" 2>&1
cat "$OUT/run_8_3_-9000.log"
