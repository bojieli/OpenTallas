#!/usr/bin/env bash
set -eu
base=$(pwd)
y=$HOME/.local/opentallas-tools/bin/yosys
p=results/native_wbk_safe_1106
for spec in old:ot_wbq_sw_split_out new:ot_wbq_sw_split_out__elastic_native;do
 IFS=: read -r n top <<< "$spec"
 "$y" -Q -p "read_verilog -sv $p/out_providers.sv $p/out_elastic_native.sv; hierarchy -check -top $top; proc; opt_clean; write_json $n.json; dffunmap; techmap; opt_clean; write_verilog -noattr -noexpr $n.v" > "$n.yosys.log" 2>&1
done
python3 "$p/count_ff.py" old.json new.json > ff_counts.json
python3 "$p/check_external_faces.py" > external_faces.summary.log
