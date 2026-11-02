#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-pg-birth-0045
for c in ambiguous regional signal_rule existing_wrong_domain protected_unbound unknown_new_master swap_wrong_role; do
 docker run --rm --network none --cpus 1 --memory 4g -v "$R":/work -e PG_NEG="$c" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/negative.tcl' > "$R/negative_$c.log" 2>&1
done
