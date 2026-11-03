#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-ves-final-look-0452
cd "$R"
sha256sum -c input.sha256
docker run --rm --memory=8g --memory-swap=8g --cpus=1 -v "$R":/out -v "$R/input.odb":/input.odb:ro -e OT_GEOM_OUT=/out/geom.tsv openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/read.tcl > "$R/read.log" 2>&1
sha256sum -c input.sha256
printf 'LOOK_RC0 %s\n' "$(date -Is)" > status
