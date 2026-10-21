"""Causal lifecycle check: native scene creation discards pre-existing loads."""
from pathlib import Path
import subprocess

import pytest


TEXT = (Path(__file__).resolve().parents[1] / 'orfs_hold_mm.tcl').read_text()


def read_proc(text):
    start = text.index('proc ot_mm_read_sdc ')
    return text[start:text.index('\n# MMFF-INSERTION', start)]


def lifecycle(text, stage):
    script = r'''
set mode {}; set events {}; array set loads {}; array set reads {}; set exceptions {}
proc set_mode {m} {set ::mode $m; if {![info exists ::loads($m)]} {set ::loads($m) {}}}
proc ot_mm_sc {} {return TC}
proc ot_mm_libs {c} {return lib_$c}
proc define_scene {name args} {
  set m [lindex $args 1]
  if {![info exists ::loads($m)]} {error "mode must exist before scene"}
  set ::loads($m) {}; lappend ::events scene:$name
}
proc read_sdc {args} {
  set m [lindex $args 1]
  if {$::events ne {scene:TC scene:BC} && ![info exists ::reads(ss)]} {error "scenes not ready"}
  incr ::reads($m)
  set ::loads($m) {pin80 wire17 fanout3 min2 max4 rise5 fall6}
  lappend ::events read:$m
}
proc log_cmd {args} {uplevel 1 $args}
proc all_clocks {} {return core}
proc set_false_path {args} {lappend ::exceptions [list $::mode {*}$args]}
''' + read_proc(text) + f'\not_mm_read_sdc /original/{stage}\n' + r'''
if {$events ne {scene:TC scene:BC read:ss read:ff}} {error "ordering or repeated evaluation: $events"}
if {$reads(ss) != 1 || $reads(ff) != 1} {error repeated}
if {$loads(ss) ne {pin80 wire17 fanout3 min2 max4 rise5 fall6} || $loads(ff) ne $loads(ss)} {error "load loss"}
if {$mode ne "ss" || !$ot_mm_active} {error "final mode"}
set expected {{ff -setup -from core}}
if {$ot_mm_stage ni {3_place.sdc 4_cts.sdc}} {lappend expected {ff -hold -from core}}
if {$exceptions ne $expected} {error "changed stage exceptions: $exceptions"}
'''
    return subprocess.run(['tclsh'], input='if {[catch {\n' + script + '\n} e]} {puts stderr $e; exit 1}\n', text=True, capture_output=True)


@pytest.mark.parametrize('stage', ['1_synth.sdc', '2_floorplan.sdc', '3_place.sdc', '4_cts.sdc'])
def test_scenes_before_single_original_read_and_unchanged_exceptions(stage):
    result = lifecycle(TEXT, stage)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('scene', ['  define_scene [ot_mm_sc] -mode ss -liberty [ot_mm_libs [ot_mm_sc]]\n', '  define_scene BC -mode ff -liberty [ot_mm_libs BC]\n'])
def test_late_scene_mutants_lose_constraints_and_refuse(scene):
    mutant = TEXT.replace(scene, '', 1).replace('  # ff mode never checks setup;', scene + '  # ff mode never checks setup;', 1)
    result = lifecycle(mutant, '3_place.sdc')
    assert result.returncode != 0
    assert 'scenes not ready' in result.stderr
