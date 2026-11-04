from pathlib import Path
import subprocess


def test_instance_group_index_preserves_regex_membership_order_and_new_epoch():
    text=Path(__file__).with_name('landing_placement.tcl').read_text()
    begin=text.index('proc cland_group_insts {prefix}')
    end=text.index('proc cland_occupy',begin)
    helper=text[begin:end]
    script=r'''
set ff_blk blk
set names {u_ff/a root.u_ff/b root/u_ff/c u_ff/u_ff/d root.u_ff not_u_ff/e root.u_ff_extra/f root/g[0]/z root/g1/z root/u$ff/y}
set scans 0
proc blk {method} {global names scans;if {$method ne "getInsts"} {error bad};incr scans;return $names}
foreach name $names {proc $name {method} [list return $name]}
proc old {prefix} {
 global ff_blk
 set hit {}
 foreach i [$ff_blk getInsts] {
  if {[regexp [format {(^|[/.])%s[/.]} $prefix] [$i getName]]} {lappend hit $i}
 }
 return $hit
}
'''+helper+r'''
set expected {}
foreach key {u_ff missing root u_ff_extra {g[0]} {g.*} {u$ff}} {lappend expected [old $key]}
set scans 0;set got {}
foreach key {u_ff missing root u_ff_extra {g[0]} {g.*} {u$ff}} {lappend got [cland_group_insts $key]}
if {$expected ne $got} {error "membership/order mismatch expected=$expected got=$got"}
# One index pass, plus three exact legacy-regex fallbacks.
if {$scans != 4} {error "expected4 scans, got$scans"}
lappend names fresh/u_ff/new
proc fresh/u_ff/new {method} {return fresh/u_ff/new}
unset -nocomplain cland_instance_index
if {[cland_group_insts u_ff] ne [old u_ff]} {error "index stale across source epochs"}
puts "INSTANCE_GROUP_EQ PASS"
'''
    run=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert run.returncode==0 and 'INSTANCE_GROUP_EQ PASS' in run.stdout,(run.stdout,run.stderr)
    assert not run.stderr,run.stderr
    assert 'unset -nocomplain cland_instance_index\nproc cland_group_insts' in text
    assert text.count('foreach i [cland_group_insts $prefix]')==4
