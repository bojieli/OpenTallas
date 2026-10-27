#!/bin/bash
# usage: run_grt.sh DIR NAME  (DIR has abstracts/ grt/)
D=$1; N=$2
cd $D
echo "image openroad/orfs:latest $(docker image inspect --format '{{.Id}}' openroad/orfs:latest) host $(hostname) start $(date -Is) mem 24g cpus 8" > run.image.txt
docker run --rm --name kvq5grt-$N --cpus=8 --memory=24g --memory-swap=24g -v $D:/work -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /work/grt/grt.tcl; rc=\$?; chown -R \$HUID:\$HGID /work; exit \$rc" > run.log 2>&1
rc=$?
echo "end $(date -Is) exit $rc" >> run.image.txt
echo "OT_DOCKER_EXIT $rc" >> run.log
