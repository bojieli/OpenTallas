#!/bin/bash
# probe.sh NAME MEMGB KITDIR CMD... : memory-capped docker probe running the epyc1 host toolchain (chroot, host / read-only,
# only KITDIR writable).  Used while ot-heavy's user systemd bus is down on epyc1 (2026-10-25).
N=$1; M=$2; K=$3; shift 3
mkdir -p $K/tmp
docker run --rm --name otdead-$N -m ${M}g -v /:/h:ro -v $K:/h$K openroad/orfs:asap7lock chroot --userspec=1000:1000 /h \
  bash -c "export HOME=/home/ubuntu TMPDIR=$K/tmp CCACHE_DIR=$K/tmp/ccache PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin; cd $K && $*"
