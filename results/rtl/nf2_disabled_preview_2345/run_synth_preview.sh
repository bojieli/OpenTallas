#!/bin/bash
# Disabled source preview only. Normal synth gates; never invokes a physical make goal or a duplicate LEC.
set -euo pipefail
D=$(cd "$1" && pwd)
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --name "codex-nf2-synth-preview-$$" --memory=8g --memory-swap=8g --cpus=2 \
 -v "$D/kit":/work -v "$D/baseline":/baseline:ro -v "$D/native_census.tcl":/native_census.tcl:ro \
 -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -e
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2"
if grep -q "^override export OT_HOLD_MM = 1" /work/config.mk; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1; fi
python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1
python3 -I /work/sdc_lint.py /work --liberty $(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* | grep -v FAKE) > /work/sdc_lint.log 2>&1
python3 -I /work/selrange_gate.py /work --out /work/selrange.json > /work/selrange.log 2>&1
python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json
$M synth
N=$(ls /work/run/results/asap7/*/base/1_2_yosys.v)
python3 -I /work/adder_map_dontuse.py check --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --netlist "$N" --report /work/dont_use_check.json
python3 -I /work/core_preflight.py /work "$N" --out /work/face_guard.json > /work/face_guard.log 2>&1
D=$(ls /work/run/results/asap7/*/base/1_synth.odb)
printf "read_db %s\nwrite_verilog /work/1_synth_odb.v\n" "$D" > /work/synth_odb_v.tcl
openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1
python3 -I /work/core_preflight.py /work /work/1_synth_odb.v --out /work/face_guard_odb.json > /work/face_guard_odb.log 2>&1
NF2_DB=/baseline/nf2_G_1_synth.odb NF2_OUT=/work/nf2_baseline_ff.tsv openroad -exit /native_census.tcl > /work/baseline_census.log 2>&1
NF2_DB="$D" NF2_OUT=/work/candidate_ff.tsv openroad -exit /native_census.tcl > /work/candidate_census.log 2>&1
chown -R "$HUID:$HGID" /work
' > "$D/synth_preview.log" 2>&1
printf 'SYNTH_PREVIEW_PASS\n' > "$D/RESULT"
