#!/bin/bash
# usage: render.sh ODB OUTDIR TITLE
set -euo pipefail
R=/srv/opentallas-scratch2/claude/S81-KVTC-PINS/kitrepo; odb=$1; o=$2; t=$3; mkdir -p $o
pl=/OpenROAD-flow-scripts/flow/platforms/asap7
printf 'read_lef %s/lef/asap7_tech_1x_201209.lef\nforeach f [glob %s/lef/asap7sc7p5t_*_RVT_1x_*.lef] { read_lef $f }\nread_db /db/%s\nsource /src/tools/ref_tile/layout_dump.tcl\n' $pl $pl $(basename $odb) > $o/dump.tcl
printf 'read_db /db/%s\nsource /src/tools/ref_tile/layout_dump.tcl\n' $(basename $odb) > $o/dump.tcl
docker run --rm --memory 16g --user $(id -u):$(id -g) -e OT_LAYOUT_OUT=/o/dump.json -e OT_LAYOUT_CLOCKS=ck -e OT_LAYOUT_TOP="$t" -v $R:/src:ro -v $(dirname $odb):/db:ro -v $o:/o openroad/orfs:asap7lock bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /o/dump.tcl' > $o/dump.log 2>&1
python3 -I $R/tools/ref_tile/layout_png.py $o/dump.json $o --title "$t" 2>&1 | tail -n 2
ls $o
