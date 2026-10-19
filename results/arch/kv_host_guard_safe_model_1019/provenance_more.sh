#!/bin/bash
set -euo pipefail
docker run --rm --network none -v "$PWD/provenance:/out" openroad/orfs:asap7lock bash -lc 'for f in /OpenROAD-flow-scripts/flow/scripts/util.tcl /OpenROAD-flow-scripts/flow/platforms/asap7/PDN.tcl /OpenROAD-flow-scripts/flow/platforms/asap7/config.mk; do if [ -f "$f" ]; then cp "$f" /out/; fi; done; rg -n "proc orfs_write_db|global_connect" /OpenROAD-flow-scripts/flow/scripts/util.tcl > /out/write_db_locations.txt'
