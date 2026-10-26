#!/bin/bash
# tile_snap.sh HOST RUNDIR TAG OUTDIR [CLOCKS]
# Finds the most advanced ORFS odb under RUNDIR on HOST, dumps its geometry with tools/ref_tile/layout_dump.tcl in the
# ORFS image, copies back the dump + ORFS final_*.webp / cts webps, renders floorplan/density PNGs with layout_png.py
# and computes pin-edge stats (tile_stats.py).  Read-only on the remote run (writes only under /tmp/visrom-<tag>).
set -u
H=$1; R=$2; T=$3; O=$4; CLK=${5:-ck}
WT=/home/ubuntu/wt/vis-rom-1016
mkdir -p $O
SSH="ssh -o ConnectTimeout=15 -o ControlPath=none"
$SSH $H "mkdir -p /tmp/visrom-$T" && scp -q -o ControlPath=none $WT/tools/ref_tile/layout_dump.tcl $H:/tmp/visrom-$T/ || exit 2
$SSH $H bash -s "$R" "$T" "$CLK" <<'EOS'
R=$1; T=$2; CLK=$3; W=/tmp/visrom-$T
ODB=""
for s in 6_final 6_1_fill 5_route 5_3_fillcell 5_2_route 5_1_grt 4_1_cts 4_cts 3_5_place_dp 3_4_place_resized 3_3_place_gp 3_2_place_iop 2_1_floorplan; do
  ODB=$(find $R -path '*/results/asap7/*' -name "$s.odb" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
  [ -n "$ODB" ] && break
done
echo "ODB $ODB"
RPT=$(find $R -path '*/reports/asap7/*/base' -type d -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
echo "RPT $RPT"
[ -n "$RPT" ] && for f in $RPT/*.webp $RPT/5_global_route.rpt $RPT/congestion.rpt; do [ -f $f ] && cp $f $W/; done
LOG=$(find $R -path '*/logs/asap7/*' -name '5_1_grt.log' 2>/dev/null | head -1); [ -n "$LOG" ] && cp $LOG $W/
[ -z "$ODB" ] && exit 0
D=$(dirname $ODB); B=$(basename $ODB)
printf 'read_db /work/%s\nsource /ld/layout_dump.tcl\nexit\n' "$B" > $W/ld.tcl
docker run --rm -e OT_LAYOUT_OUT=/ld/dump.json -e OT_LAYOUT_CLOCKS=$CLK -e OT_LAYOUT_TOP=$T -v $D:/work:ro -v $W:/ld openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /ld/ld.tcl > $W/ld.log 2>&1
tail -2 $W/ld.log
EOS
scp -q -o ControlPath=none "$H:/tmp/visrom-$T/*" $O/ 2>/dev/null
$SSH $H "rm -rf /tmp/visrom-$T"
for w in $O/*.webp; do [ -f "$w" ] && python3 -c "import sys;from PIL import Image;Image.open(sys.argv[1]).save(sys.argv[1][:-5]+'.png')" $w && rm $w; done
if [ -s $O/dump.json ]; then
  python3 $WT/tools/ref_tile/layout_png.py $O/dump.json $O --title "$T" > $O/render.log 2>&1
  python3 /tmp/visrom/tools/tile_stats.py $O/dump.json > $O/stats.json
fi
ls $O
