#!/bin/bash
set -eu
O=$(readlink -m "$1");mkdir -p "$O"
export OT_ORFS_NUM_CORES=8 NUM_CORES=8 OT_SYNTH_TIMEOUT_SECONDS=unlimited OT_FLOW_TIMEOUT_SECONDS=unlimited
S=rtl/hbm_accel/tu
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2
python3 physical/hbm_forks/psg_synth_inventory.py "$O/receipt.json" --view asap7 --top ot_hbm_accel_tu_endpoint_psg \
 --source "$S/ot_hbm_accel_tu_endpoint_psg.sv" --source "$S/ot_hcoll_port.sv" --source "$S/ot_hcoll_sram_prims.sv" \
 --source rtl/link/ot_link_afifo.sv --source rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv \
 --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv \
 --param ENABLE=1 --param REARM=1 --param NC=8 --param NOG=12 --param SYNCPHY=1 \
 --macro-view "ot_sram_1r1w_128x256_m1_r2c2=$M" \
 --clock-port clk --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 \
 --orfs-corner TC --hold-corners TC,BC --stages pnr --die-area 0 0 1400 1404 --core-area 0 0.54 1400 1403.46 \
 --place-density 0.55 --routing-layers M2 M7 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
 --purpose characterization --nickname-tag hgi_psg_synth --keep-workdir "$O/work" --output "$O/unused_physical.json"
test -s "$O/receipt.json"
