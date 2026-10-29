#!/bin/bash
set -euo pipefail
N=/srv/opentallas-scratch2/claude/nc-qc-2
docker run --rm --name ncqc2-mat --memory=56g --memory-swap=56g --cpus=4 -v /srv/opentallas-scratch2/claude:/srv/opentallas-scratch2/claude -w $N -e PYTHONPATH=$N/pydeps310 openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 $N/mat\" EXIT; openroad -python -exit $N/src/mat_nc.py > $N/mat/run.log 2>&1"
tail -30 $N/mat/run.log
