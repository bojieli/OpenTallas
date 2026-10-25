"""Reachable equally deep reset copies: opt-in source mechanism + lockstep/reset-depth mutant."""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
import ref_tile as RT
sp=importlib.util.spec_from_file_location('distributed_copies',ROOT/'physical/common_flow/ot_rst_copies.py')
RS=importlib.util.module_from_spec(sp);sp.loader.exec_module(RS)

def generate(td):
    script='''set ::env(DESIGN_NAME) example
set ::env(OT_PIN_REGS) 0
set ::env(OT_RST_LAND) 1
set ::env(OT_RST_LAND_STAGES) 4
set ::env(OT_RST_LAND_DISTRIBUTED) 1
set ::env(OT_PIN_REGS_CLOCK) ck
set ::env(OT_PIN_REGS_RESET_PORTS) rst_n
set ::env(OT_RST_COPIES_MAX) 32
set ::env(OT_RST_LAND_COPIES) rst_n=4
set ::env(OT_RST_LAND_FIRST_COPIES) rst_n=1
set ::env(RESULTS_DIR) {%s}
proc yosys {args} {
 if {[lindex $args 0] eq "tee"} {
  set f [open [lindex $args 3] w]
  puts $f {input [0:0] ck
input [0:0] rst_n
output [0:0] q}
  close $f
 }
}
source {%s}
'''%(td,ROOT/'physical/common_flow/ot_pin_regs.tcl')
    p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert p.returncode==0 and not p.stderr,p.stderr
    return (td/'ot_rst_land_wrapper.v').read_text()

def test_optin_source_and_schema(tmp_path):
    text=generate(tmp_path)
    assert 'rst_n__ot_rl1c <= {3{rst_n__ot_rl0}};' in text
    assert 'rst_n__ot_rl2c <= {3{rst_n__ot_rl1}};' in text
    assert 'rst_n__ot_rl2v = {rst_n__ot_rl2c, rst_n__ot_rl2}' in text
    spec=dict(top='example',clock_port='ck',reset_ports=['rst_n'],reset_landing=dict(enable=True,stages=4,
        distributed_chain=True,copies=dict(rst_n=32),first_copies=dict(rst_n=1)),reset_relay_split=dict(max_loads=32))
    assert RT.reset_landing_plan(spec)['reset_release_cycles']==4
    assert '--orfs-var OT_RST_LAND_DISTRIBUTED=1' in RT.reset_landing_vars(spec)

def test_distributed_family_identity_and_wrong_stage_mutant():
    def ff(d,q):
        return dict(type='$_DFF_P_',port_directions=dict(C='input',D='input',Q='output'),connections=dict(C=[2],D=[d],Q=[q]))
    cells={};nets={}
    for lev in range(1,4):
        bits=[100*lev+k for k in range(4)]
        for k,q in enumerate(bits):cells[f'l{lev}_{k}']=ff(1 if lev==1 else 100*(lev-1),q)
        nets[f'rst_n__ot_rl{lev}v']=dict(bits=bits)
    nl=dict(modules=dict(top=dict(attributes=dict(top='1'),ports={},cells=cells,netnames=nets)))
    _,rs=RS.analyse(nl,32,RS.DEFAULT_RE)
    assert len(rs)==3 and all(r['status']=='OK' for r in rs)
    nl['modules']['top']['cells']['l2_1']['connections']['D']=[1]
    _,rs=RS.analyse(nl,32,RS.DEFAULT_RE)
    assert any('REFUSED' in r['status'] for r in rs)

def test_reset_lockstep_and_dropped_stage_mutant(tmp_path):
    if not shutil.which('iverilog'):return
    wrapper=generate(tmp_path)
    bench='''
module example__ot_pr_core(input ck,input rst_n,output reg q);
always @(posedge ck) q<=rst_n;
endmodule
module tb;
reg ck=0; always #5 ck=~ck;
reg rst_n=0; reg [3:0] reference=0; reg gold=0; wire q;
example dut(ck,rst_n,q);
always @(posedge ck) begin reference<={reference[2:0],rst_n}; gold<=reference[3]; end
integer i;
initial begin
 repeat(9) @(negedge ck);
 for(i=0;i<80;i=i+1) begin
  rst_n=(i%7!=0);
  @(negedge ck);
  if(q!==gold) $fatal(1,"RESET_DEPTH_MISMATCH");
 end
 $display("RESET_LOCKSTEP_PASS");$finish;
end
endmodule
'''
    for mutant in (False,True):
        w=wrapper.replace('.rst_n(rst_n__ot_rl3)','.rst_n(rst_n__ot_rl2)') if mutant else wrapper
        src=tmp_path/('mutant.sv' if mutant else 'good.sv');src.write_text(w+bench)
        exe=tmp_path/('mutant.vvp' if mutant else 'good.vvp')
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(src)],check=True,capture_output=True)
        p=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
        assert (p.returncode!=0 if mutant else 'RESET_LOCKSTEP_PASS' in p.stdout)


def test_a0_physical_hook_reconnects_only_previous_equal_depth_level(tmp_path):
    hook=ROOT/'tools/qwen_romleaf/a0core/a0_reset_paths.tcl'
    path=ROOT/'tools/qwen_romleaf/a0core/a0c8_nk_reset_paths.tsv'
    stub=r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1000}
proc blk {m args} {if {$m eq "getInsts"} {return $::instances}; if {$m eq "findBTerm"} {return bt}}
proc bt {m} {return bb}
proc bb {m} {return [dict get {xMin 457824 xMax 457824 yMin 669996 yMax 669996} $m]}
proc master {m} {return DFFHQNx1}
proc mtD {m} {return [expr {$m eq "getName" ? "D":"INPUT"}]}
proc mtQ {m} {return [expr {$m eq "getName" ? "Q":"OUTPUT"}]}
proc ins {id m args} {
  if {$m eq "getName"} {return [dict get $::names $id]}
  if {$m eq "getMaster"} {return master}
  if {$m eq "getITerms"} {return [list ${id}D ${id}Q]}
  if {$m eq "setLocation"} {dict set ::placed $id $args}
}
proc pin {id role m args} {
  if {$m eq "getMTerm"} {return mt$role}
  if {$m eq "getNet"} {return net$id}
  if {$m eq "connect"} {dict set ::connections $id [lindex $args 0]}
}
set instances {};set names {};set connections {};set placed {}
for {set lev 0} {$lev<4} {incr lev} {
 for {set k 0} {$k<($lev==0 ? 1:32)} {incr k} {
  set id i${lev}_${k};lappend instances $id
  if {$k==0} {set nm "rst_n__ot_rl${lev}\$_DFF_P_"} else {
    set fam [expr {$lev==3 ? "":"$lev"}]
    set nm "ot_rrs__rst_n__ot_rl${fam}v__c${k}\$_DFF_P_"
  }
  dict set names $id $nm
  interp alias {} $id {} ins $id
  interp alias {} ${id}D {} pin $id D
  interp alias {} ${id}Q {} pin $id Q
 }
}
'''
    script=stub+f'\nset ::env(RESULTS_DIR) {{{tmp_path}}}\nset ::env(OT_RST_LAND_STAGES) 4\nset ::env(OT_A0_RESET_PATHS) {{{path}}}\nsource {{{hook}}}\n'
    script+='''
if {[dict size $placed]!=97} {error "missing reset flops"}
if {[dict get $connections i3_17] ne "neti2_17"} {error "bypassed previous stage"}
if {[dict get $connections i1_17] ne "neti0_0"} {error "entry parent changed"}
puts PHYSICAL_DEPTH_PASS
'''
    p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
    assert p.returncode==0 and not p.stderr,p.stderr
    assert 'PHYSICAL_DEPTH_PASS' in p.stdout


def test_release_clock_stays_exact_833_without_custom_frequency_waiver():
    import clock_entry_constraints as C
    assert C.signoff_period(dict(kind='cluster',clock='cts',route=dict(period_ps=770,signoff_period_ps=833)))==833.0
    try:C.signoff_period(dict(kind='cluster',clock='cts',route=dict(period_ps=770,signoff_period_ps=1000)))
    except ValueError:pass
    else:raise AssertionError('arbitrary clock override admitted')
