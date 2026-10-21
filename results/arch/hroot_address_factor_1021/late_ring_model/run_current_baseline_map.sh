#!/bin/bash
set -euo pipefail
cd /work
yosys -V > tool_version.txt
sha256sum *.sv libs/*.lib > inputs.sha256
L=''
for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
for top in current_baseline;do
 yosys -l "$top.map.log" -p "$L read_verilog -sv $top.sv; hierarchy -check -top $top; synth -flatten -top $top; abc -liberty libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean; stat; write_verilog -noattr $top.mapped.v" > "$top.stdout.log" 2>&1
done
echo MODEL_MAP_DONE
