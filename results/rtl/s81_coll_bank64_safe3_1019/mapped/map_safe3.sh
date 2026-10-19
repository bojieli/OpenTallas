#!/bin/bash
# canonical ORFS mapping (synthesis + floorplan only) of the bank64 safe3 lane tile, for the uncapped fanout census.
# run from the lane root (contains src/): bash src/results/rtl/s81_coll_bank64_safe3_1019/mapped/map_safe3.sh
set -eu
cd src
S=(rtl/link/ot_link_crc32.sv rtl/lib/ot_rst_relay_tree3.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
   rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv rtl/common/ot_link_credit_rx_b64.sv rtl/common/ot_link_credit_tx_rc.sv
   rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe3.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe3.sv)
A=(); for f in "${S[@]}"; do A+=(--source "$f"); done
python3 tools/run_abi3_physical.py --view asap7 --top dsfd_coll_lane_w_safe3 --param CH_BOARD=700 "${A[@]}" \
 --macro-view ot_sram_1r1w2c_256x64_m1=physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1 \
 --macro-view ot_sram_1r1w2c_32x64_m1=physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1 \
 --macro-place-halo 10.8 10.8 --clock-port ck --clock-period-ns 0.77 --stages pnr --pnr-stop-after floorplan \
 --die-area 0 0 950.4 950.4 --core-area 2.16 2.16 948.24 948.24 --routing-layers M2 M5 --orfs-corner TC \
 --purpose characterization --nickname-tag coll_safe3_map \
 --orfs-var 'VERILOG_DEFINES=-DSYNTHESIS -DOT_S81PH_COLL_TF_CLEANUP' --orfs-var "SYNTH_KEEP_MODULES=ot_sram_showahead_b64_hit5 ot_s81ph_kp20 ot_s81ph_kff1 ot_s81ph_kff10" \
 --orfs-var NUM_CORES=8 --keep-workdir ../map_safe3/work --output ../map_safe3/physical.json
