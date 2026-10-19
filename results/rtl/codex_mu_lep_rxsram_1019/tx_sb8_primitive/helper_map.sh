#!/bin/bash
set -eu
cd src
python3 tools/run_abi3_physical.py --view asap7 --top ot_sram_oldread_wreg --param W=553 --param AW=9 --param SB=8 --param GA=4 --param GROUP_IO=1 --source rtl/lib/ot_sram_oldread_wreg.sv --macro-view ot_sram_1r1w_512x128_m4_r2c2=physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2 --macro-place-halo 10.8 10.8 --clock-port clk --clock-period-ns .77 --stages pnr --pnr-stop-after floorplan --die-area 0 0 900 900 --core-area 2.16 2.16 897.84 897.84 --routing-layers M2 M5 --orfs-corner TC --purpose characterization --nickname-tag txhelper_groups --orfs-var NUM_CORES=8 --keep-workdir ../helper_map/work --output ../helper_map/physical.json
