from pathlib import Path
import subprocess

SOURCE=Path(__file__).with_name('pair_skew.tcl')


def test_actual_tc_bc_tag_shape_requires_same_corner_for_raw_and_path():
    script=r'''
set ::ot_ps_lib_only 1
source @SOURCE@
proc get_full_name {c} {return $c}
proc clk {m} {return {0 4.165e-10}}
proc pin {m} {return vertex}
proc vertex {args} {set ::index 0; return iterator}
proc iterator {method} {
 switch $method {
  has_next {return [expr {$::index<2}]}
  next {incr ::index;return path$::index}
  finish {return}
 }
}
proc path1 {m} {if {$m eq "tag"} {return {3328 tc ^max clk ^ (clock prop) clk_src source crpr_pin null}};return 2.489944e-10}
proc path2 {m} {if {$m eq "tag"} {return {4092 BC ^max clk ^ (clock prop) clk_src source crpr_pin null}};return 2.062063e-10}
set ::ot_ps_method tag
if {[ot_ps_ckarr pin clk max] ne ""} {error "must reject unselected multicorners"}
set ::env(OT_PS_CORNER) tc
if {abs([ot_ps_ckarr pin clk max]-248.9944)>1e-5} {error "wrong selected TC arrival"}
set ::env(OT_PS_CORNER) BC
if {abs([ot_ps_ckarr pin clk max]-206.2063)>1e-5} {error "wrong selected BC arrival"}
rename vertex real_vertex
proc vertex {args} {error "tag API unavailable"}
if {![catch {ot_ps_ckarr pin clk max} why] || ![string match {*requires clock-tag API*} $why]} {error "must not blend cornerless properties"}
rename vertex {}
rename real_vertex vertex
proc get_pins {args} {return pin}
proc find_timing_paths {args} {
 set i [lsearch -exact $args -corner]
 if {$i<0 || [lindex $args [expr {$i+1}]] ne "BC"} {error "credited path corner differs"}
 return {}
}
set ::ot_ps_R [dict create launch {launch/CLK clk 250 200}]
ot_ps_path launch capture/D max
proc find_timing_paths {args} {error "invalid selected corner"}
if {![catch {ot_ps_path launch capture/D max} why] || ![string match {*OT_PS_CORNER path search failed*} $why]} {error "explicit corner errors must propagate"}
'''.replace('@SOURCE@',str(SOURCE))
    p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert p.returncode==0 and not p.stderr,p.stderr
