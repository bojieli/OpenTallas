#!/bin/bash
# render.sh KIT NICK TITLE -> KIT/r2_cts.png (clock structure after CTS: trunk red, macro leaves magenta, sinks green, island yellow, ck star)
K=$(cd "$1" && pwd); R=$(dirname $(readlink -f $0))
docker run --rm --memory=8g --cpus=1 -v $K:/work -v $R:/s:ro openroad/orfs:asap7lock bash -c "P_ODB=/work/run/results/asap7/$2/base/4_cts.odb P_OUT=/work/r2_clk.csv /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /s/clk_dump.tcl" > $K/r2_render.log 2>&1
docker run --rm -v $K:/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/r2_clk.csv >/dev/null 2>&1
python3 $R/clk_render.py $K/r2_clk.csv $K/r2_cts.png "$3"
