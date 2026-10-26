#!/bin/bash
# dump_one.sh NAME RUN [ODB_PREF] -> /tmp/visaudit/NAME/{dump.json,cong.rpt,path_summary.json,odb.txt}
N=$1; R=$2; PREF=${3:-}
O=/tmp/visaudit/$N; mkdir -p $O
B=$(find $R/routes $R -maxdepth 9 -path '*/results/*/base' -type d 2>/dev/null | grep -v /src/ | head -1)
[ -z "$B" ] && B=$(find $R -maxdepth 10 -name '*.odb' 2>/dev/null | grep -v /src/ | head -1 | xargs -r dirname)
ODB=""
for f in $PREF 6_final.odb 5_2_route.odb 5_1_grt.odb 4_1_cts.odb 3_place.odb 3_5_place_dp.odb 3_4_place_resized.odb 3_3_place_gp.odb 3_2_place_iop.odb 2_floorplan.odb 2_1_floorplan.odb; do
  [ -s "$B/$f" ] && { ODB=$B/$f; break; }
done
echo "$ODB" > $O/odb.txt
[ -z "$ODB" ] && { echo "NO_ODB $N $R"; exit 3; }
RB=${B/results/reports}; LB=${B/results/logs}
for c in $(ls -t $RB/congestion*.rpt $B/../../../../*congestion*.rpt 2>/dev/null | head -1); do cp $c $O/cong.rpt; done
cp $R/cl/path_summary.json $O/ 2>/dev/null
printf 'read_db %s\nsource /vis/layout_dump.tcl\nexit\n' "$ODB" > $O/d.tcl
cp /tmp/visaudit/layout_dump.tcl $O/../layout_dump.tcl 2>/dev/null
timeout 1800 docker run --rm -e OT_LAYOUT_OUT=/vis/$N/dump.json -e OT_LAYOUT_CLOCKS=${CLKS:-clk} -e OT_LAYOUT_TOP=$N -v /tmp/visaudit:/vis -v $(dirname $ODB):$(dirname $ODB):ro openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /vis/$N/d.tcl > $O/dump.log 2>&1
echo "rc=$? $(tail -1 $O/dump.log) odb=$ODB cong=$(ls $O/cong.rpt 2>/dev/null)"
