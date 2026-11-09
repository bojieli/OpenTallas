#!/bin/bash
set -euo pipefail
cd /
R=/srv/opentallas-scratch2/claude/qc-mem9-rtl/lec64
test ! -e "$R/out/lec.json"
docker run --rm --memory=40g --memory-swap=40g --cpus=4 --name qc-mem9-rtl-lec64 \
 -v "$R/kit:/work:ro" -v "$R/out:/lecout" -v "$R/driver.py:/driver/lec.py:ro" \
 openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /driver/lec.py /work --netlist /work/netlist.v --out /lecout --reuse --jobs 4' > "$R/reuse.log" 2>&1
