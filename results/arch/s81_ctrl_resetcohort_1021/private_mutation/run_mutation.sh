#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum input_place.odb reset_cohort.tcl src/physical/common_flow/clock_split_km.tcl src/physical/s81_ctrl_rg3/clock_split_hclk.tcl src/rtl/dsrom_sys/s81_ph/ctrl/ot_s81ph_ctrl_pcr.sv > mutation_inputs.sha256
docker run --rm --memory=12g -v "$PWD:/work" -v "$PWD/src:/src:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 2 -no_init -exit /work/mutation.tcl' > mutation.log 2>&1
cat mutation.log
