#!/usr/bin/env bash
# QW-S5-SCRED 10-21 pre-gate native census of ONE bounded variant (run inside openroad/orfs:asap7lock on the fleet).
# Usage: native_k.sh OUT TOP NAME "chparam args" SRC...   constructor flags = the red2 k79 kit flags, load cap $CAP (default 8)
# OUT/NAME.sv + NAME_helpers.sv = the kit netlist; OUT/census.json = rtl/test/qwen_dv/s5/ctlsafe/native_census.py on its
# ASAP7 RVT TT mapping (every non-clock driver incl. reset and raw ports, TT stage depth).
set -euo pipefail
O=$1; TOP=$2; NAME=$3; CHP=$4; shift 4; SRC="$*"; mkdir -p "$O"
FLOW=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
F="--load-cap ${CAP:-8} --transparent-inverters --retain-mux --shared-helpers --retain-keep"
python3 rtl/test/qwen_dv/s5/ctlsafe/merge_lib.py "$FLOW" "$O/cells.lib"
CH=""; [[ -z "$CHP" ]] || CH="chparam $CHP $TOP;"
yosys -V > "$O/yosys_version.txt"; echo "chparam: $CHP" > "$O/flags.txt"; echo "flags: $F" >> "$O/flags.txt"
yosys -Q -p "read_verilog -sv -D SYNTHESIS $SRC; $CH hierarchy -check -top $TOP; synth -top $TOP -flatten -noabc -nofsm -noshare; dffunmap; clean; write_json $O/generic.json" > "$O/generic.log" 2>&1
python3 tools/qwen_dv/bound_math_netlist.py "$O/generic.json" $F --top $TOP --name $NAME --out "$O/$NAME.sv" --helpers "$O/${NAME}_helpers.sv" --record "$O/model.json" > "$O/construct.log" 2>&1
rm -f "$O/generic.json"
yosys -Q -p "read_liberty -lib $O/cells.lib; read_verilog -sv $O/$NAME.sv $O/${NAME}_helpers.sv; hierarchy -check -top $NAME; synth -top $NAME -flatten -noabc; dfflibmap -liberty $FLOW/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty $O/cells.lib; clean; stat -liberty $O/cells.lib; write_verilog -noattr $O/mapped.v" > "$O/mapped.log" 2>&1
python3 rtl/test/qwen_dv/s5/ctlsafe/native_census.py "$O/mapped.v" > "$O/census.json" 2> "$O/census.err"
sha256sum "$O/mapped.v" "$O/$NAME.sv" "$O/${NAME}_helpers.sv" > "$O/sha256.txt"; grep -i "chip area" "$O/mapped.log" | tail -1 >> "$O/sha256.txt"; gzip -f "$O/mapped.v"
python3 -c "import json;d=json.load(open('$O/census.json'));m=d['metrics'];print('VARIANT $NAME',d['verdict'],'over32',d['nonclock_drivers_over32'],'max',d['max_nonclock_loads'],'rst_n',d['rst_n_loads'],'depth',m.get('depth_ps'),m.get('depth_levels'),'ff',m['clock_max_root_sinks'],'in2out',m.get('in_to_out_bits'))"
echo NATIVE_K_DONE
