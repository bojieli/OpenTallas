#!/bin/bash
set -euo pipefail
N=/srv/opentallas-scratch2/claude/nc-qc-2; O=$1; ODB=$2; mkdir -p $O
docker run --rm --name ncqc2-census-$$ --memory=48g --memory-swap=48g --cpus=4 -v /srv/opentallas-scratch2/claude:/srv/opentallas-scratch2/claude -w $N -e PYTHONPATH=$N/pydeps310 openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 $O\" EXIT; openroad -python -exit $N/src/pg_conn_census.py $N $ODB $O > $O/run.log 2>&1"
tail -25 $O/run.log
