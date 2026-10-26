#!/bin/bash
# PATH-QC-SRAMIF2 post-CTS census runner (diagnostic, read-only on the kit's 5_1_grt.odb): census.tcl at TT and FF.
K=$(cd "$(dirname "$0")" && pwd); IMAGE=openroad/orfs:asap7lock
B=/work/run/results/asap7/$(sed -n 's/^export DESIGN_NICKNAME = //p' "$K/config.mk" | tail -1)/base
TT=$(sed -n 's/^export OT_VCLK_TT = //p' "$K/config.mk"); FF=$(sed -n 's/^export OT_VCLK_FF = //p' "$K/config.mk")
for c in TT FF; do
  docker run --rm --name sramif2-census-$(basename $K)-$c-$$ --cpus=4 --memory=16g --memory-swap=16g -v "$K":/work -w /work \
    -e OT_CORNER=$c -e ODB=$B/${ODBN:-5_1_grt.odb} -e OT_VCLK_TT=$TT -e OT_VCLK_FF=$FF $IMAGE \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 4 -exit /work/census.tcl" > "$K/census_$c.log" 2>&1 &
done; wait
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
grep -h "CENSUS_\|Error\|ERROR" "$K"/census_TT.log "$K"/census_FF.log
grep -h "Total overflow\|overflow" "$K"/run/logs/asap7/*/base/5_1_grt.log | tail -3
