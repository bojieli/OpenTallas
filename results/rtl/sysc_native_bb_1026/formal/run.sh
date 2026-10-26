#!/bin/bash
set -eu
docker run --rm --cpus=2 --memory=4g --memory-swap=4g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/lec.py /work --netlist /work/gate.v --out /work/good --jobs 2
set +e
python3 -I /work/lec.py /work --netlist /work/mutant.v --out /work/bad --jobs 2
r=$?
set -e
test "$r" = 1
'
