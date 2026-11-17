#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/qc-types-r/aliasprep
exec docker run --rm -v "$R":/out openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -s /out/frontend.ys" > "$R/frontend.log" 2>&1
