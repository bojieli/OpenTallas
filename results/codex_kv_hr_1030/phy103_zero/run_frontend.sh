#!/bin/bash
set -euo pipefail
K=${1:?isolated kit directory required}
docker run --rm --name codex-kvhr1030-phy103zero-front --cpus 4 --memory 16g --memory-swap 16g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
trap "chown -R 1000:1000 /work" EXIT
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4"
TC_LIST=$($M -s print-TC_LIB_FILES | sed -n "s/^TC_LIB_FILES *[:=] *//p")
python3 -I /work/sdc_lint.py /work --liberty $TC_LIST
python3 -I /work/rtl_lint.py /work
python3 -I /work/selrange_gate.py /work
python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json
$M synth
N=$(find /work/run/results/asap7 -name 1_2_yosys.v | head -1)
python3 -I /work/adder_map_dontuse.py check --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --netlist "$N" --report /work/dont_use_check.json
python3 -I /work/core_preflight.py /work "$N" --out /work/core_preflight.json
printf "PHY_TYPED_CORE_FACE_CHECKED_BY_CORE_PREFLIGHT\n"
python3 -I /work/reg_fanout_gate.py "$N" --out /work/reg_fanout.json
D=$(find /work/run/results/asap7 -name 1_synth.odb | head -1)
printf "read_db %s\nwrite_verilog /work/1_synth_odb.v\n" "$D" > /work/synth_odb_v.tcl
openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1
python3 -I /work/core_preflight.py /work /work/1_synth_odb.v --out /work/core_preflight_odb.json
python3 -I /work/lec.py /work --netlist "$N" --out /work/lec --jobs 4
printf "PHY_ZERO_FRONTEND_DONE_NO_PLACE\n"
' > "$K/frontend.log" 2>&1
