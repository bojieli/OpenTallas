#!/bin/bash
# usage: [SRC=TREE] run.sh JOB_DIR REFGLOB CHILD_VIEW_DIR...   (views relative to SRC, default the job src/; a trimmed snapshot needs SRC)
set -e
D=$1; G=$2; shift 2
HERE=$(cd "$(dirname "$0")" && pwd)
PF=${PF:-$HERE/../../../physical/qwen_die_masters/pinflop_ref.tcl}
B=$(ls -d $D/routes/*/work/orfs/results/asap7/*/base | head -1)
libs=""; lefs=""
for v in $(printf '%s\n' "$@" | sort -u); do c=$(basename $v); libs="$libs /src/$v/${c}_tt.lib"; lefs="$lefs /src/$v/$c.lef"; done
docker run --rm -e CHILD_LIBS="$libs" -e CHILD_LEFS="$lefs" -e REFGLOB="$G" -v ${SRC:-$D/src}:/src:ro -v $B:/base:ro -v $HERE:/m:ro -v $(readlink -f $PF):/m2/pinflop_ref.tcl:ro \
  openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /m/probe.tcl 2>&1 \
  | grep -E "^(INPUTS|OLD|NEW|FIRST|GLOB|QDM)|ERROR|Error"
