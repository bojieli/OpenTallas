#!/bin/bash
# structural identity probe: flattened 2-instance composition vs flat parent body (cell census per type must match)
W=/srv/opentallas-scratch2/claude/s81-proute-2; R=$W/rtl
L=$(tr '\n' ' ' < $W/libs.f)
for top in slice_station__p7S_x11_comp slice_station__p7S_x11_bound; do
cat > $W/eq_$top.ys <<YS
read_verilog -sv -DSYNTHESIS $L $R/slice_station__t30__clcedefe91_bound.sv $R/slice_station__t30__cl1653104c_bound.sv $R/slice_station__p7S_x11_comp.sv $R/slice_station__p7S_x11_bound.sv
hierarchy -top $top
proc; flatten; opt_clean -purge
stat
YS
done
docker run --rm -m 8g --cpus 2 --name proute2-eqstat-$$ -v /srv/opentallas-scratch2:/srv/opentallas-scratch2 -u $(id -u):$(id -g) openroad/orfs:asap7lock bash -c "
Y=\$(ls /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys 2>/dev/null || which yosys)
for t in slice_station__p7S_x11_comp slice_station__p7S_x11_bound; do \$Y -q -s $W/eq_\$t.ys -l $W/eq_\$t.log >/dev/null 2>&1; echo \$t rc=\$?; done"
for t in slice_station__p7S_x11_comp slice_station__p7S_x11_bound; do sed -n '/Number of cells/,/^$/p' $W/eq_$t.log | tail -40 > $W/eq_$t.stat; done
diff $W/eq_slice_station__p7S_x11_comp.stat $W/eq_slice_station__p7S_x11_bound.stat && echo CENSUS_IDENTICAL; head -30 $W/eq_slice_station__p7S_x11_bound.stat
