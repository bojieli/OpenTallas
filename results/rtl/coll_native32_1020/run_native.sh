#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
R=$PWD;A=results/rtl/coll_native32_1020;N=$R/native_q
mkdir -p "$N";cp "$A/native_config.mk" "$N/config.mk";cp "$A/constraint.sdc" "$N/constraint.sdc";cp "$A/native_dump.tcl" "$N/native_dump.tcl"
docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' > "$N/image.id"
sha256sum rtl/rom/*native32.sv rtl/hdc/ot_hdc_fp32_add_lat{,_fan32}.sv rtl/hdc/ot_hdc_fp32_add_lat7_fan32_native.v physical/asap7_memory_macros_v2/ot_sram_1r1w2c_{128,256}x64_m1/*lib > "$N/input_identity.sha256"
docker run --rm -v "$R:/src:ro" -v "$N:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work synth' > "$N/synth.log" 2>&1
docker run --rm -v "$R:/src:ro" -v "$N:/work" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /work/native_dump.tcl > "$N/census.log" 2>&1
