#!/bin/bash
set -eu
R=/srv/opentallas/claude/closure-loop/qfd_tt_ctlm_head-native-s1-daf5f1142-arg2
B="$R/routes/qfd_tt_ctlm_head_native_s1_daf5f1142_arg2/work/orfs/results/asap7/opentallas_qfd_tt_ctlm_head_asap7_ref_qfd_tt_ctlm_head_native_s1_daf5f1142_arg2/base"
P=/var/tmp/tt-head-power-census
docker run --rm -v "$R/src:/src:ro" -v "$B:/base:ro" -v "$P:/probe" openroad/orfs:latest bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/census.tcl' > "$P/census.log" 2>&1
