#!/bin/bash
# dietop_round.sh <die round dir with a finished s_sta case> <out dir> [threads] [mem_gb] [tile_um]
# HBM die-top FULL flow shake-out (coordinator audit 2026-10-07: no HBM die had a detailed route or post-route die STA):
# the s_sta case's libs + LEFs + netlist + floorplan + placement (k = 1, every real view in place) ->
# GRT (die signals on M4-M9 only, coarse GRT tile = OT_TILE_UM, Qwen die-top method: M2/M3 carry no die signal and are
# re-pitched to set the tile) -> DRT (M4-M9) -> RCX (asap7 rcx_patterns.rules) -> die STA SS / FF on the routed
# parasitics (the s_sta checks) -> antenna + DRC counts.  Every step checkpoints and logs OT_TIME / OTMEM; a failed step
# is reported (OT_STEP_FAIL) and the flow continues where it can.  PDN / IR stay in the separate IR rounds.
set -u
SR=$(readlink -f $1); D=$2; T=${3:-48}; M=${4:-700}; TILE=${5:-9.6}
mkdir -p $D; D=$(readlink -f $D)
cp $SR/*.lef $SR/*.lib $SR/die.v $SR/place.tcl $SR/snap.tcl $D/ 2>/dev/null
python3 - $SR/run.tcl $D/dietop.tcl $TILE <<'PY'
import sys, re
src, dst, tile = sys.argv[1], sys.argv[2], sys.argv[3]
t = open(src).read()
head, tail = t.split('source /work/place.tcl', 1)
# coarse GRT tile without re-pitching tracks in a live db (dbTrackGrid_destroy segfaults): the die is built on a
# tracks file whose M2 / M3 (no die signal, no die pin) carry pitch tile / 15 from the start
mt = '/OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl'
head = head.replace(f'source {mt}', 'source /work/make_tracks_coarse.tcl').replace(f'set ::env(MAKE_TRACKS) {mt}', 'set ::env(MAKE_TRACKS) /work/make_tracks_coarse.tcl')
p_ = float(tile) / 15.0
open(dst.replace('dietop.tcl', 'make_tracks_coarse.tcl'), 'w').write('\n'.join([
    'make_tracks Pad -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080',
    'make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080',
    'make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080',
    'make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064',
    'make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064',
    'make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048',
    'make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048',
    f'make_tracks M3 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.009 -y_pitch {p_:.3f}',
    f'make_tracks M2 -x_offset 0.009 -x_pitch {p_:.3f} -y_offset 0.045 -y_pitch {p_:.3f}',
    'make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036']) + '\n')
sta = tail[tail.index('set_cmd_units'):]
out = ['proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f',
       '  regexp {VmRSS:\\s+(\\d+)} $s -> r; regexp {VmHWM:\\s+(\\d+)} $s -> h',
       '  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }',
       'proc step {name body} { set t0 [clock milliseconds]',
       '  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err"; flush stdout; return 0 }',
       '  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name; flush stdout; return 1 }',
       'set_thread_count $::env(OT_THREADS)',
       head + 'source /work/place.tcl',
       'step placed { write_db /work/ckpt_placed.odb }',
       'exit']
open(dst, 'w').write('\n'.join(out))
libs = [l for l in head.splitlines() if l.startswith(('read_liberty', 'define_corners'))]
out = ['proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f',
       '  regexp {VmRSS:\\s+(\\d+)} $s -> r; regexp {VmHWM:\\s+(\\d+)} $s -> h',
       '  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }',
       'proc step {name body} { set t0 [clock milliseconds]',
       '  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err"; flush stdout; return 0 }',
       '  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name; flush stdout; return 1 }',
       'set_thread_count $::env(OT_THREADS)'] + libs + [
       'read_db /work/ckpt_placed.odb',
       'source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl',
       'set_routing_layers -signal M4-M9 -clock M4-M9',
       'puts "OT_TILE dbu=[[ord::get_db_block] getGCellTileSize]"',
       'set_global_routing_layer_adjustment M4-M5 0.30',
       'set_global_routing_layer_adjustment M6-M9 0.146',
       'step grt { global_route -congestion_iterations 30 -allow_congestion -verbose -congestion_report_file /work/grt_congestion.rpt }',
       'step guides { write_guides /work/route.guide }',
       'step ckpt_grt { write_db /work/ckpt_grt.odb }',
       'step wl_grt { report_wire_length -net * -global_route -file /work/wirelength_grt.csv }',
       'set ok_drt [step drt { detailed_route -bottom_routing_layer M4 -top_routing_layer M9 -output_drc /work/drt_drc.rpt -droute_end_iter 20 -verbose 1 }]',
       'step ckpt_drt { write_db /work/ckpt_drt.odb }',
       'step antenna { puts "OT_ANTENNA [check_antennas -report_file /work/antenna.rpt]" }',
       'if {$ok_drt && [step rcx { define_process_corner -ext_model_index 0 X; extract_parasitics -ext_model_file /OpenROAD-flow-scripts/flow/platforms/asap7/rcx_patterns.rules; write_spef /work/die.spef }]} {',
       '  puts "OT_PARASITICS rcx" } else {',
       '  step est { set_wire_rc -signal -layer M7; set_wire_rc -clock -layer M7; estimate_parasitics -global_routing }',
       '  puts "OT_PARASITICS global_route_estimate" }',
       sta]
open(dst.replace('dietop.tcl', 'dietop_b.tcl'), 'w').write('\n'.join(out))
PY
grep -c "" $D/dietop.tcl >/dev/null
N=hfd_dietop_$(basename $D)
date -u +%FT%TZ > $D/run.start
docker run --rm --name $N --cpus=$T --memory=${M}g -e OT_THREADS=$T -v $D:/work -w /work openroad/orfs:asap7lock \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $T -no_init -exit /work/dietop.tcl > /work/dietop.log 2>&1 && /usr/bin/time -v openroad -threads $T -no_init -exit /work/dietop_b.tcl > /work/dietop_b.log 2>&1; rc=\$?; chmod -R a+rwX /work; exit \$rc"
echo $? > $D/run.exit; date -u +%FT%TZ > $D/run.end
