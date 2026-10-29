#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; R=/srv/opentallas-scratch2/claude/die-qc34; O=$1; ODB=$2
mkdir -p $O
docker run --rm --name dqc34-pgcensus-$$ --memory=48g --memory-swap=48g --cpus=4 -v "$Q:$Q" -w "$R" -e PYTHONPATH="$R/pydeps310" openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 $O\" EXIT; openroad -python -exit $R/src/pg_conn_census.py $R $ODB $O > $O/run.log 2>&1"
tail -25 $O/run.log
