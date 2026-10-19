#!/bin/bash
set -eu
cd src
python3 tools/run_abi3_physical.py --view asap7 --top ot_sram_showahead_bank64_coupon --param W=553 --param AW=3 --param WREG=1 --param LOCAL_HIT=1 --source rtl/lib/ot_sram_showahead_bank64_coupon.sv --macro-view ot_sram_1r1w2c_32x64_m1=physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1 --macro-place-halo 10.8 10.8 --clock-port clk --clock-period-ns 0.77 --stages pnr --pnr-stop-after floorplan --die-area 0 0 561.6 561.6 --core-area 2.16 2.16 559.44 559.44 --routing-layers M2 M5 --orfs-corner TC --purpose characterization --nickname-tag coll_bank64_coupon --orfs-var SYNTH_KEEP_MODULES=ot_sram_showahead_hit5_coupon --orfs-var NUM_CORES=4 --keep-workdir ../mapped/work --output ../mapped/physical.json
