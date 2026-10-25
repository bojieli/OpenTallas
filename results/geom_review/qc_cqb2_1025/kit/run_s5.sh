#!/bin/bash
# QC-CQB2 vmr_s5: run ORFS make targets (args) in docker on this kit; log run_<tag>.log.  Usage: run_s5.sh TAG target...
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); TAG=$1; shift
IMAGE=openroad/orfs:asap7lock
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) tag $TAG targets $* start $(date -Is)" >> "$K/image.txt"
docker run --rm --name qccqb2-s5-$TAG-$$ --cpus=8 --memory=24g --memory-swap=24g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in $*; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_$TAG.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $TAG $(date -Is) rc $rc" >> "$K/image.txt"
tail -3 "$K/run_$TAG.log"; exit $rc
