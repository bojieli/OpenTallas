#!/bin/bash
set -uo pipefail
K=$(pwd)
mkdir -p run
C=codex-s81-parent-residual-0148-$$
printf '%s\n' "$C" > container.txt
/usr/bin/time -v docker run --rm --name "$C" --cpus=4 --memory=16g --memory-swap=16g \
 -v "$K":/work -w /OpenROAD-flow-scripts/flow -e NUM_CORES=4 -e HUID=$(id -u) -e HGID=$(id -g) \
 openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl --physical-synth /OpenROAD-flow-scripts/flow/scripts/synth.tcl || exit 9
python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json || exit 9
python3 -I /work/rtl_lint.py /work || exit 8
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 synth
rc=$?
chown -R "$HUID:$HGID" /work/run /work/*json /work/*log /work/*ys 2>/dev/null || true
exit "$rc"
' > synth.log 2>&1
rc=$?
printf '%s\n' "$rc" > synth_exit.txt
if [ "$rc" = 0 ]; then python3 -I count_mapped.py > mapped_count.log 2>&1; rc=$?; fi
printf '%s\n' "$rc" > exit.txt
exit "$rc"
