#!/bin/bash
# gen_remote.sh RUN ODB DEF(or -) CONFIG_MK(or -) OUT  -- runs on the fleet host; writes only under OUT
set -u
RUN=$1 ODB=$2 DEF=$3 CFG=$4 OUT=$5
mkdir -p "$OUT"
IMG=${ORFS_IMAGE:-openroad/orfs:asap7lock}
P=/OpenROAD-flow-scripts/flow/platforms/asap7
DN=""; LEFS=""
if [ "$CFG" != - ] && [ -f "$CFG" ]; then
  DN=$(sed -n 's/^export DESIGN_NAME *= *//p' "$CFG" | head -1)
  for l in $(sed -n 's/^export ADDITIONAL_LEFS *+\?= *//p' "$CFG"); do
    case $l in /src/*) l=$RUN/src/${l#/src/};; esac
    [ -f "$l" ] && LEFS="$LEFS $l"
  done
fi
cat > "$OUT/run.sh" <<IN
set -e
export PATH=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:$PATH
cd /out
if [ "$DEF" = - ]; then
  printf 'read_db $ODB\nputs "TOP [[ord::get_db_block] getName]"\nwrite_def /out/6_final.def\n' > wd.tcl
  openroad -no_init -exit wd.tcl > write_def.log 2>&1
  D=/out/6_final.def
else
  D=$DEF
  printf 'read_db $ODB\nputs "TOP [[ord::get_db_block] getName]"\n' > wd.tcl
  [ -n "$DN" ] || openroad -no_init -exit wd.tcl > write_def.log 2>&1
fi
N="$DN"; [ -n "\$N" ] || N=\$(sed -n 's/^TOP //p' write_def.log | head -1)
python3 /OpenROAD-flow-scripts/flow/util/generate_klayout_tech.py --template $P/KLayout/asap7.lyt --output /out/klayout.lyt \
  --lef-files $P/lef/asap7_tech_1x_201209.lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef $P/lef/asap7sc7p5t_28_L_1x_220121a.lef $P/lef/asap7sc7p5t_28_SL_1x_220121a.lef $LEFS > tech.log 2>&1
klayout -zz -rd tech_file=/out/klayout.lyt -rd in_def=\$D -rd design_name=\$N \
  -rd in_files="$P/gds/asap7sc7p5t_28_R_220121a.gds $P/gds/asap7sc7p5t_28_L_220121a.gds $P/gds/asap7sc7p5t_28_SL_220121a.gds" \
  -rd out_file=/out/6_final.gds -r /out/stream.py > stream.log 2>&1
echo "DESIGN \$N" >> stream.log
IN
cp "$(dirname "$0")/stream.py" "$OUT/stream.py"
docker run --rm --user "$(id -u):$(id -g)" -v "$RUN:$RUN:ro" -v "$OUT:/out" "$IMG" bash /out/run.sh
rc=$?
grep -q STREAM_OK "$OUT/stream.log" 2>/dev/null && [ -s "$OUT/6_final.gds" ] && echo "GDS_OK $(stat -c %s "$OUT/6_final.gds")" || { echo "GDS_FAIL rc=$rc"; tail -5 "$OUT"/*.log; }
