"""A single macro PG strap keeps real tracks; tight pairs remain coarse cuts."""
from pathlib import Path
import subprocess
SRC=Path(__file__).with_name('pg_pair_cap.tcl')
TRACKS='228600 228648 228696 228744 228792 228840 228888 228936 228984 229032 229080 229128'
def tcl(s):
 p=subprocess.run(['tclsh'],input='source {'+str(SRC)+'}\n'+s,text=True,capture_output=True,check=True)
 assert not p.stderr,p.stderr
 return p.stdout

def test_actual_single_macro_strap_has_at_least_five_legal_tracks():
 s=tcl('puts [ot_pgcap_min_free_tracks {'+TRACKS+'} 228780 228900 887653 976967 570 {{228696 887653 228984 976967}}]\n')
 assert int(s.strip())==7  # two boundary tracks exactly meet the PG-width spacing

def test_tight_pair_never_reopens_the_zero_one_track_case():
 s=tcl('puts [ot_pgcap_min_free_tracks {'+TRACKS+'} 228780 228900 0 100 570 {{228500 0 228800 100} {228880 0 229200 100}}]\n')
 assert int(s.strip())==1 and int(s.strip())<3
 # Dropping the second PG guard is the negative control for pair preservation.
 mutant=tcl('puts [ot_pgcap_min_free_tracks {'+TRACKS+'} 228780 228900 0 100 570 {{228500 0 228800 100}}]\n')
 assert int(mutant.strip())>=3

def test_selected_track_obstruction_keeps_wide_spacing_and_eol_guard():
 s=tcl(r'''
namespace eval odb {proc dbObstruction_create {blk L a b c d} {puts "OBS $a $b $c $d";return guard}}
proc L {m args} {return 24}
proc blk {m args} {return die}
proc die {m args} {return [dict get {yMin 0 yMax 1226880} $m]}
set ::ot_pgtt_obs {}
puts "N [ot_pgcap_guard_tracks blk L {'''+TRACKS+r'''} 228780 887737 228900 976883 84]"
puts "CLEANUP $::ot_pgtt_obs"
''')
 assert 'OBS 228732 887653 228948 976967' in s
 assert 'N 5' in s and 'CLEANUP guard' in s

def test_m5_mode_fails_closed_without_track_truth_cleanup():
 # Minimal objects suffice because dependency check precedes the database walk.
 s=tcl(r'''
namespace eval ord {proc get_db_block {} {return blk};proc get_db_tech {} {return tech}}
proc blk {m args} {return die}
proc die {m args} {return [dict get {xMin 0 yMin 0 xMax 604800 yMax 1226880} $m]}
set ::env(OT_PGCAP_FINITE_EXTENT) 1
set ::env(OT_PGCAP_M5_LEGAL_TRACKS) 1
unset -nocomplain ::env(OT_PG_TRACK_TRUTH)
puts "BAD [catch {ot_pgcap_add} e] $e"
''')
 assert 'BAD 1 OT_PGCAP_M5_LEGAL_TRACKS requires finite extent and active PG-track-truth cleanup' in s


def test_real_pair_is_preserved_even_when_it_straddles_a_gcell_boundary():
    s=tcl('puts [ot_pgcap_tight_pair {228696 0 228984 100} {{228696 0 228984 100} {228900 0 229188 100}}]\n')
    assert s.strip()=='1'
    isolated=tcl('puts [ot_pgcap_tight_pair {228696 0 228984 100} {{228696 0 228984 100} {228900 200 229188 300}}]\n')
    assert isolated.strip()=='0'
