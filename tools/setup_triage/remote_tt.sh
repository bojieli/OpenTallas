#!/bin/bash
# usage: remote_tt.sh JOB ORFS_DIR SRC_DIR OUTDIR
# Option-B sign-off re-STA of one routed job: TT setup, TT setup + consistent link budget, FF hold, SS setup (sensitivity).
# Re-uses the job's own w18_sta_{ss,ff}.tcl loads (odb/spef/sdc/post-sdc); TT swaps the std-cell and macro libs.
set -u
JOB=$1; ORFS=$2; SRC=$3; OUT=$4
mkdir -p "$OUT"; S="$ORFS/w18_sta_ss.tcl"; F="$ORFS/w18_sta_ff.tcl"
[ -f "$S" ] || { echo "TT_ERR no w18_sta_ss.tcl"; exit 3; }
odb=$(grep -m1 '^read_db' "$S" | awk '{print $2}' | sed "s#^/work#$ORFS#"); [ -f "$odb" ] || { echo "TT_ERR odb gone"; exit 4; }
# TT: std cells _RVT_SS_ -> _RVT_TT_; macros *_ss.lib -> *_tt.lib when the TT view exists (else SS, flagged)
sed 's/_RVT_SS_/_RVT_TT_/g; s/^puts "OT_CORNER ss"/puts "OT_CORNER tt"/' "$S" > $OUT/tt.tcl
for l in $(grep -o '/src/[^ ]*_ss\.lib' $OUT/tt.tcl); do
  t=${l%_ss.lib}_tt.lib
  if [ -f "$SRC/${t#/src/}" ]; then sed -i "s#$l#$t#" $OUT/tt.tcl; else echo "TT_MACRO_SS_FALLBACK $l"; fi
done
awk '/^puts "OT_CORNER/{print "read_sdc /tri/link_budget_consistent.sdc"} {print}' $OUT/tt.tcl > $OUT/ttlb.tcl
cp "$S" $OUT/ss.tcl
[ -f "$F" ] && cp "$F" $OUT/ff.tcl
run() { timeout 3600 docker run --rm --name "tt_${2}_${JOB//[^A-Za-z0-9_]/_}" -v "$ORFS:/work:ro" -v "$SRC:/src:ro" -v "$OUT:/tri" openroad/orfs:asap7lock bash -lc \
  "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /tri/$1" > $OUT/${2}.log 2>&1; echo "TRI_RC $?" >> $OUT/${2}.log; }
run tt.tcl tt & run ttlb.tcl ttlb & run ss.tcl ss & { [ -f $OUT/ff.tcl ] && run ff.tcl ff; } & wait
drc=$(grep -ho '"detailedroute__route__drc_errors": *[0-9]*' $ORFS/logs/asap7/*/base/5_2_route.json 2>/dev/null | tail -1 | grep -o '[0-9]*$')
echo "TT_DRC ${drc:-NA}"
for c in tt ttlb ss ff; do echo "== $c"; grep -E "^OT_WS |^OT_WS_|^OT_VIOL|TRI_RC|^Error|^OT_LINK_BUDGET clock" $OUT/$c.log 2>/dev/null | head -12; done
