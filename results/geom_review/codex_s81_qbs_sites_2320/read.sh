#!/bin/bash
set -euo pipefail
P=/srv/opentallas-scratch2/claude/codex-s81-qbs-centre-2255
R=$P/codex_sites_2320
for v in LLfu LLfd NNfu; do
 M=dsfd_node_$v
 mkdir -p "$R/$M"
 docker run --rm --memory=4g --memory-swap=4g --cpus=2 -v "$P/gen3":/gen3:ro -v "$R":/out -e ODB=/gen3/${M}_c/run/results/asap7/kl_${M}_c/base/3_place.odb -e OUT=/out/$M/sites.tsv -e OT_GEOM_OUT=/out/$M/geom.tsv openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 2 -exit /out/sites.tcl > "$R/$M/read.log" 2>&1
 printf 'READ_%s_RC0 %s\n' "$M" "$(date -Is)" >> "$R/status"
done
