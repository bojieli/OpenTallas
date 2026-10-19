#!/bin/bash
set -euo pipefail
for mode in r7w ovl; do
 if [ "$mode" = r7w ];then top=qkd_d2d_static_safe24; else top=qkd_d2d_static_ovl_safe24;fi
 yosys -Q -T -p "read_verilog -lib native_interfaces.v sram_bb.v; read_verilog -sv ${mode}_reuse/${top}.v; hierarchy -check -top ${top}; proc; opt -full; techmap; opt -full; check -assert; write_json ${mode}.native.json; write_verilog ${mode}.native.v" > ${mode}.native.log 2>&1
 python3 transparent_roles.py ${mode}.native.json ${top} > ${mode}.roles.json
 gzip -c ${mode}.roles.json > ${mode}.roles.json.gz
done
echo COLLECT_SYNTH_PASS
