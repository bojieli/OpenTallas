#!/bin/bash
set -euo pipefail
lane=/srv/opentallas-scratch/claude/codex-s81-ctrl-bank64
prior=/srv/opentallas-scratch/claude/ref_gate/s81ctrl_rg2_sram-20261019-090615
model=$lane/placed_model
mkdir -p "$model/work"
cp -a "$lane/synth/results" "$lane/synth/objects" "$lane/synth/logs" "$lane/synth/reports" "$model/work/"
cp -a "$prior/routes/gate/work/orfs/hooks" "$model/work/"
cp "$lane/synth/config.mk" "$model/work/config.mk"
cat >> "$model/work/config.mk" <<'CFG'
export DIE_AREA = 0 0 531.25 250
export CORE_AREA = 2.16 2.16 529.09 247.84
export MACRO_PLACEMENT_TCL = /model/place.tcl
CFG
docker run --rm -e LEC_CHECK=0 -v "$prior/src":/src:ro -v "$lane/rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv":/src/rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_afifo_g_sram.sv:ro -v "$lane/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1":/bankmodel:ro -v "$model":/model -v "$model/work":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base place' > "$model/driver.log" 2>&1
