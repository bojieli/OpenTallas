#!/usr/bin/env bash
set -euo pipefail
# PROPOSAL: run only after owner reviews actual GEN join and ot-run admission.
[[ ${HG9_Q1_SYNTH_REVIEWED:-0} == 1 ]] || { echo 'PREP ONLY: no q1 SYNTH admission' >&2; exit 2; }
K=$(realpath "${1:?fresh owned copy of generated current q1 kit}")
[[ -f "$K/census_synth.tcl" && ! -e "$K/run/results/asap7/hc_qkd_ectlk_q1__243_648x172_8/base/1_synth.odb" ]]
IMAGE=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker run --rm --cpus=4 --memory=12g --memory-swap=12g -v "$K":/work -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -s <<'INNER'
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1
# Existing q0 normal source-lint library inventory; no STA/corner execution.
mapfile -t LINT_LIBS < <(find /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -maxdepth 1 -type f -name 'asap7sc7p5t_*RVT_*.lib*' ! -name '*FAKE*' | sort)
(( ${#LINT_LIBS[@]} > 0 ))
python3 -I /work/sdc_lint.py /work --liberty "${LINT_LIBS[@]}" > /work/sdc_lint.log 2>&1
python3 -I /work/selrange_gate.py /work --out /work/selrange.json > /work/selrange.log 2>&1
PD=/OpenROAD-flow-scripts/flow/platforms/asap7
python3 -I /work/adder_map_dontuse.py gen --platform-dir "$PD" --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 synth
N=/work/run/results/asap7/hc_qkd_ectlk_q1__243_648x172_8/base/1_2_yosys.v
python3 -I /work/adder_map_dontuse.py check --platform-dir "$PD" --netlist "$N" --report /work/dont_use_check.json
openroad -exit /work/census_synth.tcl > /work/census_synth.log 2>&1
printf 'HG9_Q1_SYNTH_MODEL_PASS: normal SYNTH/dont-use+unplaced census only; noLEC/FP/STA/route\n'
INNER
