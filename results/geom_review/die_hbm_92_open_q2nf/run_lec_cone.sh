#!/bin/bash
# DIE-HBM-92-OPEN/Q2NF: one bounded rerun of the cfg_vA native LEC with the vA1 recipe (replica match, parity 1024,
# preseed plan in lec_hints.json) and a larger per-cone budget (OT_LEC_CONE_S 3600; default 600 timed out 2 CRC codec cones).
set -euo pipefail
K=/srv/opentallas-scratch2/claude/die-hbm-92-open/q2nf/kit_cfg_vA_lec
cat > "$K/lec_inner.sh" <<'IN'
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/lec.py /work --out /work/lec_cone3600 > /work/lec_cone3600.log 2>&1; rc=$?
chown -R 1000:1000 /work/lec_cone3600 /work/lec_cone3600.log; exit $rc
IN
docker run --rm --name dh92q2nf-cfgA-lec --memory=40g --memory-swap=40g --cpus=8 -e OT_LEC_REPLICA_MATCH=1 -e OT_LEC_PARITY_TERMS=1024 -e OT_LEC_CONE_S=3600 -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash /work/lec_inner.sh
