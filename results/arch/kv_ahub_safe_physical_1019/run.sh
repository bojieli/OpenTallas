#!/bin/bash
set -euo pipefail
cd /run
P=/OpenROAD-flow-scripts/flow/platforms/asap7
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
yosys -Q -q -p 'read_liberty -lib cells.lib; read_verilog native.v; hierarchy -top qkd_ahub_static_dw_safe_native; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; write_verilog -noattr tied.v' > tie.log 2>&1
cat > init.tcl <<EOF
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef zh.lef
read_lef recip.lef
read_liberty cells.lib
read_liberty zh_tt.lib
read_liberty recip_tt.lib
read_verilog tied.v
link_design qkd_ahub_static_dw_safe_native
initialize_floorplan -die_area {0 0 734.4 540} -core_area {2.16 2.16 732.24 537.84} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
write_db init.odb
exit
EOF
openroad -no_init -exit init.tcl > init.log 2>&1
openroad -no_init -exit -python floorplan.py > floorplan.log 2>&1
