#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/claude/closure-loop/qfd_tt_ctlm_tree-native-current-s1-2984e0c51
B="$R/routes/qfd_tt_ctlm_tree_native_current_s1_2984e0c51/work/orfs/results/asap7/opentallas_qfd_tt_ctlm_tree_asap7_ref_qfd_tt_ctlm_tree_native_current_s1_2984e0c51/base"
P=/var/tmp/tt-final-ss
docker run --rm -v "$R/src:/src:ro" -v "$B:/base:ro" -v "$P:/probe" openroad/orfs:latest bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/domains.tcl' > "$P/domains.log" 2>&1
