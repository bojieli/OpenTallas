#!/bin/bash
set -euo pipefail
for key in nk:025738 nl:025733; do
 t=${key%:*}; stamp=${key#*:}
 d=/srv/opentallas-scratch/claude/ref_gate/qfd_tile_${t}_rp2_45_a2-20261016-${stamp}
 out="$d/r5_sequence"
 mkdir -p "$out"
 cp "$d/r5_diag/viol_names.txt" "$out/viol_names.txt"
 cp /tmp/qtile45-r5-sequence.tcl "$out/sequence.tcl"
 docker run --rm -e R5_KIT_PRE_DPL=/src/physical/ref_tile/qfd_tile_${t}_rp2_45_a2/pre_dpl.tcl -v "$d/routes/gate/work/orfs:/work:ro" -v "$d/src:/src:ro" -v "$out:/out" -w /out openroad/orfs:latest bash -lc 'trap "chmod -R a+rwX /out" EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init -threads 8 /out/sequence.tcl' > "$out/sequence.log" 2>&1
done
