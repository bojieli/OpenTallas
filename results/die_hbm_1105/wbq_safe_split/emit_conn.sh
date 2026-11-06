#!/usr/bin/env bash
set -eu
R=$(realpath "${1:?repo}"); P=$R/results/die_hbm_1105/wbq_safe_split; O=$(realpath -m "${2:?out}"); mkdir -p "$O"
YOSYS=${YOSYS:-$HOME/.local/opentallas-tools/bin/yosys}
"$YOSYS" -p "read_verilog -sv -lib $P/subs_blackbox.sv; read_verilog -sv $P/thin_wrapper.sv; hierarchy -top ot_wbq_sw; proc; write_json $O/composed.json" > "$O/conn.log"
python3 "$P/split_conn.py" "$O/composed.json" ot_wbq_sw "$O/ot_wbq_sw.conn.json"
