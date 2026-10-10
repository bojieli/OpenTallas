#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/md6-pg-fix-c2c07c284
python3 "$D/source/tools/fp_margin_lint.py" check "$D/fp_dump.json" --out "$D/fp_lint.json" > "$D/fp_lint.log" 2>&1
docker run --rm -e OT_PG_ODB=/receipt/corrected.odb -e OT_PG_DIAG=/receipt/rows_pins_rails.log -v "$D/source:/src:ro" -v "$D:/receipt" sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /src/tools/dsrom_markov_lookup_pg_diag.tcl" > "$D/diag.log" 2>&1
