O=/srv/opentallas-scratch2/claude/die-head-21/meas
head -9 $O/ring21.tcl > $O/ring21b.tcl; cat $O/ring21b_tail.tcl >> $O/ring21b.tcl
D=/srv/opentallas-scratch2/claude/die-head-20/kits/hd_tile_grtp
docker run --rm --name dh21-ring-2 -m 16g --cpus 4 -v $D:/work -v $O:/out -e ODB=/work/run/results/asap7/dp_hd_tile/base/5_1_grt.odb -e SPEF=/work/meas17g/grt.spef openroad/orfs:asap7lock bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/ring21b.tcl" > $O/out/ring21b.log 2>&1
grep -v -E "^\[WARNING|^read_|^  DFF" $O/out/ring21b.log | sed -n 5,200p
