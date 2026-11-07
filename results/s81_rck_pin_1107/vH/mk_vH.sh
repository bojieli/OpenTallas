#!/bin/bash
# S81-RCK-6 11-07: vH t16. Same RTL and netlist as vG. Stage resume from vG 3_4_place_resized.
set -e
G=/srv/opentallas-scratch3/claude/s81-rck-5/vG/serdes__t16/gen
V=$G/serdes__t16
H=/srv/opentallas-scratch3/claude/s81-rck-6/vH
K=$H/serdes__t16
[ ! -e $K ] || { echo "exists $K"; exit 1; }
mkdir -p $H
rsync -a --exclude run/ --exclude lec/ --exclude 'lec_async.*' --exclude 'run_*.log' --exclude '.kwrs*' --exclude 'FAIL_*' $V/ $K/
cp -p $V/lec_async.sh $K/
mkdir -p $K/run
cp -al $V/run/. $K/run/
R=$K/run/results/asap7/dp_serdes__t16/base; L=$K/run/logs/asap7/dp_serdes__t16/base
rm -f $R/3_5_place_dp.odb $R/3_place.odb $R/3_place.sdc $R/4_* $R/ot_clock_taps.json $L/3_5_* $L/4_*
# netlist proof runs in vG: same 1_2_yosys.v; lec.py parked so no second 64 GB LEC starts
mv $K/lec.py $K/lec.py.parked_vG_proof
cp /tmp/s81-rck-6/fixed_exports.tcl $K/landing_exports.tcl
python3 -I /tmp/s81-rck-6/edit_vH.py $K
sed 's/local st=(x do-floorplan do-place do-cts do-grt)/local st=(x do-floorplan "do-3_5_place_dp do-3_place" do-cts do-grt)/' $G/run_kit.sh > $H/run_kit.sh
grep -c 'do-3_5_place_dp do-3_place' $H/run_kit.sh
echo '{"start":"place","note":"S81-RCK-6 vH: detail place only, on vG 3_4_place_resized"}' > $K/resume.json
sha256sum $V/run/results/asap7/dp_serdes__t16/base/1_2_yosys.v $R/1_2_yosys.v | cut -c1-16
du -sh $K
