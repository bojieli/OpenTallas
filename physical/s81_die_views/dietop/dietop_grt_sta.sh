#!/bin/bash
# S81-DIE dietop_grt_sta.sh <real case dir (floorplan.odb placed, k = 1)> <out dir> <sta kit dir> [threads] [mem_gb] [tile_um] [iters]
# Academic-validation die flow (OWNER STEER 2026-10-07 19:00): FULL-die global route on the real pins (k = 1, no
# bundling) -> GRT checkpoint + guides -> estimate_parasitics -global_routing -> die.spef (GRT parasitics) -> die STA
# SS and FF (OpenSTA in OpenROAD) on that SPEF with the kit's libs (closed views + interim pin-registered libs) and the
# CTS-validated clock plan latencies.  No flat full-die detail route (representative regions: dietop_region.sh).
# GRT settings as dietop_round.sh (coarse M2/M3 track grid, die signals M4-M9, M4-M5 30 % / M6-M9 14.6 % adjustment).
set -u
SR=$(readlink -f $1); D=$2; K=$(readlink -f $3); T=${4:-48}; M=${5:-400}; TILE=${6:-9.6}; CI=${7:-30}
mkdir -p $D; D=$(readlink -f $D)
cp $SR/*.lef $D/ 2>/dev/null; ln -f $SR/floorplan.odb $D/placed.odb 2>/dev/null || cp $SR/floorplan.odb $D/placed.odb
SRC=$(cat $K/src_root)
cat > $D/grt.tcl <<T
proc mem {tag} { set f [open /proc/self/status]; set s [read \$f]; close \$f
  regexp {VmRSS:\\s+(\\d+)} \$s -> r; regexp {VmHWM:\\s+(\\d+)} \$s -> h
  puts "OTMEM \$tag rss_mb=[expr {\$r/1024}] hwm_mb=[expr {\$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 \$body} err]} { puts "OT_STEP_FAIL \$name \$err"; flush stdout; return 0 }
  puts "OT_TIME step=\$name s=[format %.1f [expr {([clock milliseconds]-\$t0)/1000.0}]]"; mem \$name; flush stdout; return 1 }
set_thread_count $T
step load { read_db /work/placed.odb }
step coarse { set b [ord::get_db_block]; set p [expr {$TILE/15.0}]
  foreach ln {M2 M3} { odb::dbTrackGrid_destroy [\$b findTrackGrid [[ord::get_db_tech] findLayer \$ln]]
    make_tracks \$ln -x_offset 0.009 -x_pitch \$p -y_offset 0.009 -y_pitch \$p } }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_SS_nldm_*.lib*] { read_liberty \$l }
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_routing_layers -signal M4-M9 -clock M4-M9
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M9 0.146
set_global_routing_layer_adjustment M8-M9 ${OT_M89_ADJ:-0.146}
step grt { global_route -congestion_iterations $CI -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt }
step guides { write_guides /work/route.guide }
step ckpt_grt { write_db /work/ckpt_grt.odb }
step wl { report_wire_length -net * -global_route -file /work/wirelength_grt.csv }
step spef { estimate_parasitics -global_routing -spef_file /work/die_grt.spef }
step netlist { write_verilog /work/die_grt.v }
T
# OT_DIE_REPAIR=1 (H-REACH 2026-10-16, owner ruling HANDOFF 0cl): native-aware repeaters on the die nets before GRT
# (shared tools/die_repeaters step: -max_wire_length ${OT_DIE_REPAIR_MAX_WIRE:-160} um, 260 ps max_transition, BUFx4..8, clock/reset nets
# untouched); the GRT container then also mounts the STA kit (/kit) and the source root (kit lib paths), and the die STA
# reads the repaired netlist die_rep.v.  Default off: the script is byte-for-byte the old flow.
GV="-v $D:/work"
if [ "${OT_DIE_REPAIR:-0}" = 1 ]; then
  grep -q '__hp ' $K/die.v && { echo "OT_DIE_REPAIR refuses a kit with planning hold pads (__hp masters in die.v)" > $D/repair.refused; exit 1; }
  # DIE-FLOW 10-17: the shared die-net repeater step (tools/die_repeaters; die_repair.tcl = its S81 call + outputs)
  python3 $SRC/tools/die_repeaters/step.py copy $D > /dev/null || exit 1
  { python3 $SRC/tools/die_repeaters/step.py tcl --design s81 --report /work/die_repeaters.json --libs-file /kit/libs_tt.txt \
      --std-corner TT --legalize snap ${OT_DIE_REPAIR_MAX_WIRE:+--max-wire-um $OT_DIE_REPAIR_MAX_WIRE} || exit 1
    sed -n '/^# ---- outputs/,$p' $SRC/physical/s81_die_views/dietop/die_repair.tcl; } > $D/die_repair.tcl || exit 1
  sed -i 's#^foreach l \[glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_\*_RVT_SS_nldm_\*.lib\*\] { read_liberty \$l }$#if {[catch {source /work/die_repair.tcl} e]} { puts "OT_DIE_REPAIR FAIL $e"; exit 3 }#' $D/grt.tcl
  grep -q 'source /work/die_repair.tcl' $D/grt.tcl || { echo "OT_DIE_REPAIR hook not placed" > $D/repair.refused; exit 1; }
  GV="$GV -v $K:/kit -v $SRC:$SRC:ro"
fi
date -u +%FT%TZ > $D/grt.start
docker run --rm --name s81_grt_$(basename $(dirname $D))_$(basename $D) --cpus=$T --memory=${M}g $GV -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/grt.tcl > /work/grt.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
echo $? > $D/grt.exit; date -u +%FT%TZ > $D/grt.end
if [ "${OT_DIE_REPAIR:-0}" = 1 ]; then
  grep -q 'OT_DIE_REPAIR DONE' $D/grt.log && [ -s $D/die_rep.v ] && python3 $SRC/tools/die_repeaters/step.py check $D/die_repeaters.json > $D/die_repeaters.txt \
    || { echo "OT_DIE_REPAIR did not complete / FAIL: $(cat $D/die_repeaters.txt 2>/dev/null)" > $D/sta.skip; exit 1; }
fi
SP=$(ls $D/die_grt.spef* 2>/dev/null | head -1)
[ -n "$SP" ] || { echo "no spef" > $D/sta.skip; exit 1; }
# die STA, one OpenROAD/OpenSTA session per corner, kit tcl unchanged except the SPEF path
for c in ss tt ff; do   # owner option B: setup TT, hold FF, SS sensitivity
  sed -e "s#/kit/die.spef#/run/$(basename $SP)#g" $K/sta_$c.tcl | sed -e "s#> /kit/#> /run/#g" > $D/sta_$c.tcl
  if [ "${OT_DIE_REPAIR:-0}" = 1 ]; then   # repaired netlist + the repeater cells' own corner library
    C=$(echo $c | tr a-z A-Z)
    sed -i -e "s#read_verilog /kit/die.v#read_verilog /run/die_rep.v#" \
      -e "s#^foreach l \$libs { read_liberty \$l }#foreach l \$libs { read_liberty \$l }; foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*] { read_liberty \$l }#" $D/sta_$c.tcl
    grep -q 'read_verilog /run/die_rep.v' $D/sta_$c.tcl && grep -q "RVT_${C}_nldm" $D/sta_$c.tcl || { echo "repair STA rewrite failed $c" > $D/sta.skip; exit 1; }
  fi
  docker run --rm --name s81_sta_${c}_$(basename $(dirname $D))_$(basename $D) --cpus=8 --memory=${M}g -v $D:/run -v $K:/kit -v $SRC:$SRC:ro -w /run openroad/orfs:asap7lock \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v sta -no_init -exit /run/sta_$c.tcl > /run/sta_$c.log 2>&1; chmod -R a+rwX /run" &
done
wait
date -u +%FT%TZ > $D/sta.end
