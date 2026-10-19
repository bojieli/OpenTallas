#!/bin/bash
set -euo pipefail
for mode in r7w ovl; do
 if [ "$mode" = r7w ]; then top=qkd_d2d_static; else top=qkd_d2d_static_ovl; fi
 # Native combinational and sequential cell interfaces are read as library cells.
 # Every sequential source copy is independently lowered by proc/techmap.
 yosys -Q -T -p "read_verilog -lib native_interfaces.v sram_bb.v; read_verilog -sv ${mode}_reset24_kept.v; hierarchy -top ${top}_reset24; proc; opt -full; techmap; opt -full; dfflibmap -liberty seq.lib; techmap -map invmap.v; opt_clean; write_json ${mode}.kept_native.json; write_verilog ${mode}.kept_native.v" > ${mode}.kept_native.log 2>&1
 python3 source_census.py ${mode}.kept_native.json ${top}_reset24 > ${mode}.kept_native.census.json
done
