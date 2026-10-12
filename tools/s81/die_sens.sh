#!/bin/bash
# s81-die-iter (2026-10-12) post-GRT die checks, run by die_iter_chain.sh after the nominal STA:
#   die_sens.sh <run dir M (grt/ kit/ a_real/)> <src snapshot S> <tag>
# 1. CLOCK PIN CHECK on the GRT checkpoint: every relay / station / stage view (master ~ rly|stn|stg|relay|station) must
#    carry a clock pin in its LEF master AND have it connected (Qwen KV qkd_rly_* lacked theirs: the die could not time
#    a relay hop). Forwarded-link stations dsfd_stn* are clocked by their forwarded clock fiN (lib setup/hold related_pin
#    fi0); that counts as their clock pin. All other macros are listed too. grt/ckpin.log, verdict line OT_CKPIN_SUMMARY.
# 2. OCV bound: TT setup / FF hold with set_timing_derate -early 0.95 -late 1.05 (cells + nets) on the GRT SPEF.
# 3. GRT-vs-DRT parasitic error bar (results/physical/die_region_drt_1012/README.md): routed cap +40 % median / +144 % p95
#    over GRT -> TT setup / FF hold on the GRT SPEF with every cap x1.40 and x2.44 (tools/s81/spef_cap_scale.py).
# 4. Region DRT: if the die GRT total overflow is 0, pick + stage the S81 windows (tools/die_region_drt) and start them.
set -uo pipefail
M=$(readlink -f $1); S=$(readlink -f $2); TAG=$3; G=$M/grt; K=$M/kit; SRC=$(cat $K/src_root)
st(){ echo "$(date -u +%FT%TZ) $*" >> $M/STATUS.log; }
cat > $G/ckpin.tcl <<'T'
read_db /work/ckpt_grt.odb
set b [ord::get_db_block]
set rx_rel {rly|stn|stg|relay|station}
array set n {}; array set noc {}; array set unc {}
foreach i [$b getInsts] {
  set m [$i getMaster]; if {![$m isBlock]} { continue }
  set mn [$m getName]; set cks {}
  foreach mt [$m getMTerms] { set p [$mt getName]
    if {[$mt getSigType] eq "CLOCK" || [regexp {^(ck[hs]?|clk|cw|ck_col|clk_[a-z0-9]+|fi[0-9]*|refclk)(\[[0-9]+\])?$} $p]} { lappend cks $p } }
  if {![info exists n($mn)]} { set n($mn) 0; set noc($mn) 0; set unc($mn) 0 }
  incr n($mn)
  if {[llength $cks] == 0} { incr noc($mn); continue }
  set ok 0
  foreach it [$i getITerms] { if {[lsearch -exact $cks [[$it getMTerm] getName]] >= 0 && [$it getNet] ne "NULL"} { set ok 1 } }
  if {!$ok} { incr unc($mn) }
}
set rbad 0; set rn 0; set obad 0
foreach mn [lsort [array names n]] {
  set cls [expr {[regexp $rx_rel $mn] ? "relay" : "other"}]
  if {$cls eq "relay"} { incr rn $n($mn); incr rbad [expr {$noc($mn) + $unc($mn)}] } else { incr obad [expr {$noc($mn) + $unc($mn)}] }
  if {$noc($mn) || $unc($mn) || $cls eq "relay"} { puts "OT_CKPIN class=$cls master=$mn insts=$n($mn) no_clock_pin=$noc($mn) clock_unconnected=$unc($mn)" }
}
puts "OT_CKPIN_SUMMARY relay_station_insts=$rn relay_station_bad=$rbad other_macro_bad=$obad verdict=[expr {$rbad == 0 ? "PASS" : "FAIL"}]"
T
/srv/opentallas-scratch/admit.sh 40 -- docker run --rm --name dieit_${TAG}_ckpin --cpus=4 --memory=60g -v $G:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/ckpin.tcl > /work/ckpin.log 2>&1; chmod -R a+rwX /work"
st "CKPIN $(grep -h OT_CKPIN_SUMMARY $G/ckpin.log || echo no-summary)"
SP=$(ls $G/die_grt.spef* | head -1)
for f in 1.40 2.44; do python3 $S/tools/s81/spef_cap_scale.py $SP $G/die_grt_c${f/./}.spef --factor $f >> $G/sens_scale.log 2>&1 & done; wait
mk(){ # mk <corner> <case> <spef basename> <derate 0|1>
  sed -e "s#/kit/die.spef#/run/$3#g" -e "s#> /kit/\([a-z_]*\)\.rpt#> /run/sens_$2_\1.rpt#g" $K/sta_$1.tcl > $G/sens_$2.tcl
  [ "$4" = 1 ] && sed -i "s#^source /kit/latency_$1.tcl#&\nset_timing_derate -early 0.95\nset_timing_derate -late 1.05\nputs OT_OCV_DERATE#" $G/sens_$2.tcl
  /srv/opentallas-scratch/admit.sh 100 -- docker run --rm --name dieit_${TAG}_sens_$2 --cpus=8 --memory=200g -v $G:/run -v $K:/kit -v $SRC:$SRC:ro -w /run \
    openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; sta -no_init -exit /run/sens_$2.tcl > /run/sens_$2.log 2>&1; chmod -R a+rwX /run"; }
SPB=$(basename $SP)
mk tt tt_ocv $SPB 1 & mk ff ff_ocv $SPB 1 &
mk tt tt_c140 die_grt_c140.spef 0 & mk ff ff_c140 die_grt_c140.spef 0 &
mk tt tt_c244 die_grt_c244.spef 0 & mk ff ff_c244 die_grt_c244.spef 0 &
wait
{ for c in tt ff; do echo "$c nominal $(grep -E '^(worst slack|tns)' $G/sta_$c.log | tr '\n' ' ')"
    for k in ocv c140 c244; do echo "$c $k $(grep -E '^(worst slack|tns)' $G/sens_${c}_$k.log | tr '\n' ' ')"; done; done; } > $G/sens.txt
st "SENS $(tr '\n' ';' < $G/sens.txt)"
OV=$(awk '$1=="Total"{v=$NF;f=1} END{print f ? v+0 : "unknown"}' $G/grt.log)
if [ "${OV:-1}" = 0 ]; then
  R=/srv/opentallas-scratch/claude/region-drt/s81_$TAG; mkdir -p $R
  python3 $S/tools/die_region_drt/region_drt.py pick --guide $G/route.guide --def $M/a_real/floorplan_placed.def --lef $M/a_real/*.lef \
     --congestion-rpt $G/grt_congestion.rpt --out $R/windows.json > $R/pick.out 2>&1 || { st REGION_PICK_FAIL; exit 0; }
  python3 -c "import json;[print(w['name'], ','.join(str(v) for v in w['win'])) for w in json.load(open('$R/windows.json'))['windows']]" |
  while read w WB; do
    python3 $S/tools/die_region_drt/region_drt.py stage --ckpt $G/ckpt_grt.odb --spef $SP --libs $K/libs_{c}.txt --clock-lat $K/latency_{c}.tcl \
       --out $R/$w --win $WB --threads 16 --mem 120 > $R/stage_$w.log 2>&1 && (cd $R/$w && nohup ./start_region.sh > start.out 2>&1 &)
  done
  st "REGION_DRT staged $R ($(ls -d $R/*/ 2>/dev/null | wc -l) windows)"
else
  st "REGION_DRT not staged: GRT total overflow $OV (needs 0)"
fi
