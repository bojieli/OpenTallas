#!/usr/bin/env bash
set -euo pipefail
CASE=/srv/opentallas-scratch/claude/ref_gate/s81sl_ve_r4-20261020-055315
ROOT=$(pwd)
IMAGE=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
mkdir -p work
cp "$CASE/routes/gate/work/orfs/config.mk" work/config.mk
cp "$CASE/routes/gate/work/orfs/constraint.sdc" work/constraint.sdc
cp "$CASE/routes/gate/work/orfs/io_constraints.tcl" work/io_constraints.tcl
python3 - <<'PYINNER'
from pathlib import Path
p=Path('work/config.mk');s=p.read_text();s=s.replace('export VERILOG_DEFINES = -DSYNTHESIS','export VERILOG_DEFINES = -DSYNTHESIS -DOT_S81_VE_LOADSAFE5');p.write_text(s)
PYINNER
sha256sum "$CASE/src/rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv" patched_fp.sv work/config.mk > inputs.sha256
docker image inspect "$IMAGE" > image.json
docker run --rm -v "$CASE/src:/src:ro" -v "$ROOT/patched_fp.sv:/src/rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv:ro" -v "$ROOT/work:/work" -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth > /work/make_synth.log 2>&1
 args=();for f in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*; do args+=(--liberty "$f");done
 python3 /src/tools/ref_tile/native_census.py --netlist /work/results/asap7/opentallas_ot_s81sl_ve_asap7_ref_gate/base/1_2_yosys.v --top ot_s81sl_ve --out /work/native_census.json "${args[@]}" > /work/native_census.log 2>&1
'
