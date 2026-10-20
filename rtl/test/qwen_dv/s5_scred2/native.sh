#!/usr/bin/env bash
# QW-SLICE7-LEAVES pre-gate native census (fleet). Usage: native.sh OUT TOP NAME "chparam args" SRC...
#  plain/   : the hand RTL mapped directly (ASAP7 RVT TT, recipe of ctlrepair1/native4.sh)
#  bounded/ : generic netlist -> tools/qwen_dv/bound_math_netlist.py (CTL repair4 flags) -> mapped
# census.json = rtl/test/qwen_dv/s5/ctlsafe/native_census.py (every non-clock driver incl. reset and raw ports).
set -euo pipefail
O=$1; TOP=$2; NAME=$3; CHP=$4; shift 4; SRC="$*"
mkdir -p "$O/plain" "$O/bounded"
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
python3 rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
CH=""; [[ -z "$CHP" ]] || CH="chparam $CHP $TOP;"
yosys -V > "$O/yosys_version.txt"
(
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv -D SYNTHESIS $SRC; $CH hierarchy -check -top $TOP; synth -top $TOP -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_verilog -noattr $O/plain/mapped.v" > "$O/plain/mapped.log" 2>&1 \
 && python3 rtl/test/qwen_dv/s5/ctlsafe/native_census.py "$O/plain/mapped.v" > "$O/plain/census.json" 2> "$O/plain/census.err"
echo "PLAIN rc=$?"
) &
yosys -Q -p "read_verilog -sv -D SYNTHESIS $SRC; $CH hierarchy -check -top $TOP; synth -top $TOP -flatten -noabc -nofsm -noshare; dffunmap; clean; write_json $O/bounded/generic.json" > "$O/bounded/generic.log" 2>&1
python3 tools/qwen_dv/bound_math_netlist.py "$O/bounded/generic.json" --load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-all-comb --fuse-ao --top $TOP --name $NAME --out "$O/bounded/$NAME.sv" --helpers "$O/bounded/${NAME}_helpers.sv" --record "$O/bounded/model.json" > "$O/bounded/construct.log" 2>&1
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv $O/bounded/$NAME.sv $O/bounded/${NAME}_helpers.sv; hierarchy -check -top $NAME; synth -top $NAME -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_verilog -noattr $O/bounded/mapped.v" > "$O/bounded/mapped.log" 2>&1
python3 rtl/test/qwen_dv/s5/ctlsafe/native_census.py "$O/bounded/mapped.v" > "$O/bounded/census.json" 2> "$O/bounded/census.err"
wait
for k in plain bounded; do python3 -c "import json,sys;d=json.load(open('$O/$k/census.json'));m=d['metrics'];print('$k',d['verdict'],'over32',d['nonclock_drivers_over32'],'max',d['max_nonclock_loads'],'rst_n',d['rst_n_loads'],json.dumps(m)[:600])" || true; done
echo NATIVE_DONE
