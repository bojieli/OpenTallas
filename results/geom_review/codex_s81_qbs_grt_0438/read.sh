#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qbs-grt-audit-0438
cd "$R"
sha256sum -c input.sha256
docker run --rm --memory=4g --memory-swap=4g --cpus=1 -v "$R":/out -v "$R/input.odb":/input.odb:ro -e ODB=/input.odb -e OUT=/out/sites.tsv -e OT_GEOM_OUT=/out/geom.tsv openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/sites_audit.tcl > "$R/read.log" 2>&1
sha256sum -c input.sha256
printf 'AUDIT_RC0 %s\n' "$(date -Is)" > status
