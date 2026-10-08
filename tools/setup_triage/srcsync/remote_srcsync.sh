#!/bin/bash
# usage: remote_srcsync.sh JOB ORFS SRC OUT   (TT setup with the source-synchronous per-link split; needs srcsync.py in OUT)
set -u
JOB=$1; ORFS=$2; SRC=$3; OUT=$4; mkdir -p $OUT
S="$ORFS/w18_sta_ss.tcl"
sdc=$(grep -m1 '^read_sdc /work' $S | awk '{print $2}' | sed "s#^/work#$ORFS#")
cp $sdc $OUT/orig.sdc
# S81-style stations reference vclk on forwarded-clock ports: re-reference to the forwarded clock first
fo=$(grep -o "output \[[0-9:]*\] fo[0-9]*\|output fo[0-9]*" $(dirname $sdc)/6_final.v 2>/dev/null | head -1 | awk '{print $NF}')
[ -n "$fo" ] && fo="$fo[0]"
python3 $OUT/srcsync.py retarget $OUT/orig.sdc $OUT/orig_rt.sdc "$fo" | grep -q True && mv $OUT/orig_rt.sdc $OUT/orig.sdc && echo "RETARGETED fo=$fo"
python3 $OUT/srcsync.py reps $OUT/orig.sdc > $OUT/reps.txt
sed 's/_RVT_SS_/_RVT_TT_/g' $S | sed "s#^read_sdc /work/[^ ]*6_final.sdc#read_sdc /tri/orig.sdc#" | awk '/^puts "OT_CORNER/{exit} {print}' > $OUT/p1.tcl
for l in $(grep -o '/src/[^ ]*_ss\.lib' $OUT/p1.tcl); do t=${l%_ss.lib}_tt.lib; [ -f "$SRC/${t#/src/}" ] && sed -i "s#$l#$t#" $OUT/p1.tcl; done
while read k c p; do
  [ "$k" = input ] && echo "puts \"P1 $k $c\"; report_checks -path_delay max -from [get_ports {$p}] -format full_clock_expanded" >> $OUT/p1.tcl
  [ "$k" = output ] && echo "puts \"P1 $k $c\"; report_checks -path_delay max -to [get_ports {$p}] -format full_clock_expanded" >> $OUT/p1.tcl
done < $OUT/reps.txt
echo exit >> $OUT/p1.tcl
dk() { timeout 3600 docker run --rm -v "$ORFS:/work:ro" -v "$SRC:/src:ro" -v "$OUT:/tri" openroad/orfs:asap7lock bash -lc "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /tri/$1" > $OUT/$2 2>&1; }
dk p1.tcl p1.log
python3 - $OUT <<'PY'
import re, sys, json
out = sys.argv[1]; s = open(f"{out}/p1.log").read()
pm = {}
for blk in re.split(r"\nP1 ", s)[1:]:
    k, c = blk.split("\n", 1)[0].split()
    edges = [float(m[1]) for m in re.finditer(r"^\s*(-?[\d.]+)\s+-?[\d.]+\s+clock \S+ \((?:rise|fall) edge\)", blk, re.M)]
    if len(edges) >= 2 and re.match(r"(f_|o_|fk|core_clk|fwd|fclk|tri_fo)", c):
        # forwarded-clock link: P = capture edge - launch edge as STA waveform resolves it
        pm[f"{k}:{c}"] = round(edges[1] - edges[0], 3)
json.dump(pm, open(f"{out}/pmap.json", "w")); print("PMAP", pm)
PY
python3 $OUT/srcsync.py split $OUT/orig.sdc $OUT/pmap.json $OUT/srcsync.sdc
sed 's/_RVT_SS_/_RVT_TT_/g' $S | sed "s#^read_sdc /work/[^ ]*6_final.sdc#read_sdc /tri/srcsync.sdc#" > $OUT/p2.tcl
for l in $(grep -o '/src/[^ ]*_ss\.lib' $OUT/p2.tcl); do t=${l%_ss.lib}_tt.lib; [ -f "$SRC/${t#/src/}" ] && sed -i "s#$l#$t#" $OUT/p2.tcl; done
sed -i 's#^exit#report_checks -path_delay max -from [all_inputs -no_clocks] -format full_clock_expanded\nreport_checks -path_delay max -to [all_outputs] -format full_clock_expanded\nexit#' $OUT/p2.tcl
dk p2.tcl p2.log
grep -E "^OT_WS |TRI|^Error" $OUT/p2.log | head -5
