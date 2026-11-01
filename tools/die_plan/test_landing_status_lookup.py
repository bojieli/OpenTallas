from pathlib import Path
import subprocess


def test_cached_status_lookup_matches_old_unique_ambiguous_law_and_resets_epoch():
    text=Path(__file__).with_name('landing_placement.tcl').read_text()
    begin=text.index('proc cland_status_net {net}')
    end=text.index('unset -nocomplain cland_status_suffix',begin)
    helper=text[begin:end]
    script=r'''
set ff_blk blk
set names {plain parent.good root/other a.duplicate b/duplicate near_good parent.part.deep parent.escaped\good}
set scans 0
proc blk {method args} {
 global names scans
 if {$method eq "getNets"} {incr scans; return $names}
 if {$method eq "findNet"} {set n [lindex $args 0]; if {$n in $names} {return $n};return NULL}
 error "bad block operation"
}
foreach name $names {proc $name {method} [list return $name]}
proc old {net} {
 global ff_blk
 set n [$ff_blk findNet $net]
 if {$n ne "NULL"} {return $n}
 set candidates {};set length [string length $net]
 foreach dn [$ff_blk getNets] {
  set name [$dn getName]
  if {[string length $name]>$length && [string range $name end-[expr {$length-1}] end] eq $net && [string index $name end-$length] in {. /}} {lappend candidates $dn}
 }
 if {[llength $candidates]==1} {return [lindex $candidates 0]}
 if {[llength $candidates]>1} {error "OT_CLAND ambiguous status net $net: [llength $candidates] hierarchical matches"}
 return NULL
}
'''+helper+r'''
set expected {}
foreach key {plain good other duplicate missing near_good part.deep escaped\good} {
 set rc [catch {old $key} result]; lappend expected [list $rc $result]
}
set scans 0
set got {}
foreach key {plain good other duplicate missing near_good part.deep escaped\good} {
 set rc [catch {cland_status_net $key} result];lappend got [list $rc $result]
}
if {$got ne $expected} {error "lookup mismatch expected=$expected got=$got"}
# One cached pass for simple names plus one legacy pass for hierarchical key.
if {$scans != 2} {error "expected 2 scans, got $scans"}
# A subsequent hook invocation starts a new connectivity epoch.
lappend names next.good
proc next.good {method} {return next.good}
unset -nocomplain cland_status_suffix
set rc [catch {cland_status_net good} result]
if {!$rc || ![string match {*ambiguous*2 hierarchical matches} $result]} {error "stale cache across hooks: $rc $result"}
puts "STATUS_LOOKUP_EQ PASS"
'''
    run=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert run.returncode==0 and 'STATUS_LOOKUP_EQ PASS' in run.stdout,(run.stdout,run.stderr)
    assert not run.stderr,run.stderr
    assert 'unset -nocomplain cland_status_suffix\nforeach spec $cland_status' in text
