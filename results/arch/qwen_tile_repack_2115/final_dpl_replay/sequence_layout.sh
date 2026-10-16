#!/bin/bash
set -euo pipefail
for key in nk:025738 nl:025733; do
 t=${key%:*}; stamp=${key#*:}
 d=/srv/opentallas-scratch/claude/ref_gate/qfd_tile_${t}_rp2_45_a2-20261016-${stamp}
 cp /tmp/qtile45-sequence-layout.tcl "$d/r5_sequence/layout.tcl"
 for stage in after_dpo canonical_final; do
 docker run --rm -e R5_STAGE="$stage" -e R5_TILE="$t" -v "$d/src:/src:ro" -v "$d/r5_sequence:/out" -w /out openroad/orfs:latest bash -lc 'trap "chmod -R a+rwX /out" EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init -threads 1 /out/layout.tcl' > "$d/r5_sequence/${stage}_layout.log" 2>&1
 done
 sha256sum "$d"/r5_sequence/*.odb > "$d/r5_sequence/odb_sha256.txt"
done
