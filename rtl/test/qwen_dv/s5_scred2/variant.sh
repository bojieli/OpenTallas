#!/usr/bin/env bash
# Constructor flag variant on an existing generic.json: OUT GENERIC_JSON TOP NAME FLAGS...  (run in openroad/orfs:asap7lock)
set -euo pipefail
O=$1; G=$2; TOP=$3; NAME=$4; shift 4
mkdir -p "$O"; FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
echo "flags: $*" > "$O/flags.txt"
python3 tools/qwen_dv/bound_math_netlist.py "$G" "$@" --top $TOP --name $NAME --out "$O/$NAME.sv" --helpers "$O/${NAME}_helpers.sv" --record "$O/model.json" > "$O/construct.log" 2>&1
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv $O/$NAME.sv $O/${NAME}_helpers.sv; hierarchy -check -top $NAME; synth -top $NAME -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_verilog -noattr $O/mapped.v" > "$O/mapped.log" 2>&1
python3 rtl/test/qwen_dv/s5/ctlsafe/native_census.py "$O/mapped.v" > "$O/census.json" 2> "$O/census.err"
python3 -c "import json;d=json.load(open('$O/census.json'));m=d['metrics'];print('VARIANT',d['verdict'],'over32',d['nonclock_drivers_over32'],'max',d['max_nonclock_loads'],'depth',m.get('depth_ps'),m.get('depth_levels'),'ff',m['clock_max_root_sinks'])"
