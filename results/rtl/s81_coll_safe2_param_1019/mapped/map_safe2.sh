#!/bin/bash
set -eu
cd src
source physical/ref_tile/dscoll_lane_w_ltr/kit.env
A=()
for f in $SRCS; do A+=(--source "$f");done
python3 tools/run_abi3_physical.py --view asap7 --top dsfd_coll_lane_w_safe2 \
 --param GFMT=1 --param EPPIPE=2 --param LCR=1 --param RXSRAM=1 --param RXLOCAL=1 --param EPRX=1 --param EPTO=1 --param EPMW=1 --param TXSAFE=1 --param CH_BOARD=700 \
 "${A[@]}" --source rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe2.sv --source rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe2.sv --source rtl/lib/ot_sram_oldread_wreg.sv --source rtl/lib/ot_rst_relay_tree3.sv \
 --macro-view ot_sram_1r1w_512x128_m4_r2c2=physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2 \
 --macro-view ot_sram_1r1w_32x128_m1=physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1 \
 --macro-place-halo 10.8 10.8 --clock-port ck --clock-period-ns 0.77 --stages pnr --pnr-stop-after floorplan --die-area 0 0 561.6 561.6 --core-area 2.16 2.16 559.44 559.44 --routing-layers M2 M5 --orfs-corner TC --purpose characterization --nickname-tag coll_safe2_sizing \
 --orfs-var 'VERILOG_DEFINES=-DSYNTHESIS -DOT_S81PH_COLL_TF_CLEANUP' --orfs-var SYNTH_KEEP_MODULES=ot_sram_showahead_hit5 --orfs-var NUM_CORES=8 --keep-workdir ../map_safe2/work --output ../map_safe2/physical.json
