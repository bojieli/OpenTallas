#!/bin/bash
set -eu
JOB=/srv/opentallas/jobs-overflow/erdos-w2-paired-sm-r3
SRC=/srv/opentallas/jobs-overflow/erdos-w2-source-6513ca594
export NUM_CORES=16 MAKEFLAGS=-j16 TMPDIR="$JOB/tmp" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
trap 'rc=$?; echo "$rc" > "$JOB/terminal.exit"' EXIT
cd "$SRC"
git rev-parse HEAD > "$JOB/source.commit"
git status --porcelain > "$JOB/source.dirty"
test ! -s "$JOB/source.dirty"
/srv/opentallas-scratch/admit.sh 12 -- bash -c 'python3 tools/dshbm_w2_pair_seq.py build --work "$1" && python3 tools/dshbm_w2_pair_seq.py run --work "$1"' _ "$JOB"
