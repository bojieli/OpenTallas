#!/bin/bash
# run under ot-run: each variant = patch ORFS synth scripts with that kit's native_bb.py, then `make synth`
set -uo pipefail
R=$1
for v in main fix neg; do
  K=$R/$v
  docker run --rm --name qc59s-$v-$$ --cpus=1 --memory=4g --memory-swap=4g -v $K:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
    python3 -I /work/native_bb.py scripts/synth_preamble.tcl --physical-synth scripts/synth.tcl || exit 9; \
    make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 synth; rc=\$?; chown -R $(id -u):$(id -g) /work; exit \$rc" > $K/make_synth.log 2>&1
  echo "$v rc=$?" | tee $K/rc.txt
done
