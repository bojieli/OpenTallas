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


def _a0_hook(tmp_path, mutate=None):
    """OpenDB stub of the synthesized NK reset paths: DFFHQN copies, each D fed by an INV of its parent's QN"""
    hook=ROOT/'tools/qwen_romleaf/a0core/a0_reset_paths.tcl'
    path=ROOT/'tools/qwen_romleaf/a0core/a0c8_nk_reset_paths.tsv'
    flops={}
    for lev in range(4):
        for k in range(1 if lev==0 else 32):
            flops[(lev,k)]=(lev-1,0 if lev==1 else k) if lev else None
    if mutate:mutate(flops)
    lines=[]
    for (lev,k),par in flops.items():
        nm=f"rst_n__ot_rl{lev}$_DFF_P_" if k==0 else f"ot_rrs__rst_n__ot_rl{'' if lev==3 else lev}v__c{k}$_DFF_P_"
        if par is None:dn='rst_n'
        elif par[0]=='raw':dn=f'qn_{par[1]}_{par[2]}'
        else:dn=f'inv_{par[0]}_{par[1]}'
        lines.append(f'mkflop f_{lev}_{k} {{{nm}}} {dn} qn_{lev}_{k}')
    for (lev,k) in flops:
        lines.append(f'mkinv i_{lev}_{k} qn_{lev}_{k} inv_{lev}_{k}')
    stub=r"""
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1000}
proc blk {m args} {if {$m eq "getInsts"} {return $::instances}; if {$m eq "findBTerm"} {return bt}}
proc bt {m} {return bb}
proc bb {m} {return [dict get {xMin 457824 xMax 457824 yMin 669996 yMax 669996} $m]}
set instances {};set placed {};set nets {}
proc mt {pin dir m} {return [expr {$m eq "getName" ? $pin : $dir}]}
proc it {inst pin dir net m args} {
  if {$m eq "getMTerm"} {return [list mt $pin $dir]}
  if {$m eq "getNet"} {return [list nt $net]}
  if {$m eq "getInst"} {return $inst}
}
proc nt {net m} {
  if {$m eq "getName"} {return $net}
  if {$m eq "getITerms"} {return [dict get $::nets $net]}
}
proc addterm {inst pin dir net} {
  set t [list it $inst $pin $dir $net]
  dict lappend ::nets $net $t
  dict lappend ::terms $inst $t
}
proc ins {id nm master m args} {
  if {$m eq "getName"} {return $nm}
  if {$m eq "getMaster"} {return [list ms $master]}
  if {$m eq "getITerms"} {return [dict get $::terms $id]}
  if {$m eq "setLocation"} {dict set ::placed $id $args}
}
proc ms {master m} {return $master}
proc mkflop {id nm d qn} {
  interp alias {} $id {} ins $id $nm DFFHQNx1_ASAP7_75t_R
  lappend ::instances $id
  addterm $id D INPUT $d; addterm $id QN OUTPUT $qn
}
proc mkinv {id a y} {
  interp alias {} $id {} ins $id $id INVx1_ASAP7_75t_R
  lappend ::instances $id
  addterm $id A INPUT $a; addterm $id Y OUTPUT $y
}
dict set nets rst_n {}
"""
    script=stub+'\n'.join(lines)
    script+=f'\nset ::env(RESULTS_DIR) {{{tmp_path}}}\nset ::env(OT_RST_LAND_STAGES) 4\nset ::env(OT_A0_RESET_PATHS) {{{path}}}\nif {{[catch {{source {{{hook}}}}} e]}} {{puts stderr $e; exit 1}}\nputs "PLACED [dict size $placed]"\n'
    # stub objects are lists ("it inst pin ..."); make them callable as single commands
    script=script.replace('set t [list it $inst $pin $dir $net]','set t "it_[incr ::tn]"; interp alias {} $t {} it $inst $pin $dir $net')
    script=script.replace('if {$m eq "getMTerm"} {return [list mt $pin $dir]}','if {$m eq "getMTerm"} {set x "mt_[incr ::tn]"; interp alias {} $x {} mt $pin $dir; return $x}')
    script=script.replace('if {$m eq "getNet"} {return [list nt $net]}','if {$m eq "getNet"} {set x "nt_$net"; interp alias {} $x {} nt $net; return $x}')
    script=script.replace('if {$m eq "getMaster"} {return [list ms $master]}','if {$m eq "getMaster"} {set x "ms_$master"; interp alias {} $x {} ms $master; return $x}')
    script='set ::tn 0\n'+script
    return subprocess.run(['tclsh'],input=script,text=True,capture_output=True)


def test_a0_physical_hook_verifies_same_index_chains(tmp_path):
    p=_a0_hook(tmp_path)
    assert p.returncode==0 and not p.stderr,p.stderr
    assert 'PLACED 97' in p.stdout and 'same-index parents verified' in p.stdout and 'chains (no live load) {}' in p.stdout


def test_a0_physical_hook_accepts_only_whole_dead_chains(tmp_path):
    def dead(f):
        for lev in (1,2,3):
            for k in (19,30):f.pop((lev,k))
    p=_a0_hook(tmp_path,dead)
    assert p.returncode==0 and not p.stderr,p.stderr
    assert 'PLACED 91' in p.stdout and '{19 30}' in p.stdout


def test_a0_physical_hook_mutants_caught(tmp_path):
    def rotated(f):     # the run2 netlist: level-2 copy 18 fed by level-1 copy 17
        f[(2,18)]=(1,17)
    def partial(f):     # a dead parent under a live child (the run2 failure shape)
        f.pop((1,17))
    def polarity(f):    # D straight on the parent's QN (the old rewire): inverted reset
        f[(3,5)]=('raw',2,5)
    def bypass(f):      # level-3 copy fed by a level-1 copy: one stage skipped
        f[(3,7)]=(1,7)
    for mut,msg in ((rotated,'not same-index parent'),(partial,'missing parent 1,17'),(polarity,'inverted'),
                    (bypass,'not same-index parent')):
        p=_a0_hook(tmp_path,mut)
        assert p.returncode!=0 and msg in p.stderr,(mut.__name__,p.stderr[-300:])


def test_release_clock_stays_exact_833_without_custom_frequency_waiver():
    import clock_entry_constraints as C
    assert C.signoff_period(dict(kind='cluster',clock='cts',route=dict(period_ps=770,signoff_period_ps=833)))==833.0
    try:C.signoff_period(dict(kind='cluster',clock='cts',route=dict(period_ps=770,signoff_period_ps=1000)))
    except ValueError:pass
    else:raise AssertionError('arbitrary clock override admitted')


def test_chain_families_pair_copy_k_to_copy_k():
    """QC-A0R: an intermediate family whose loads are the D pins of the next equally wide family pairs k -> k"""
    def ff(d,q):
        return dict(type='$_DFF_P_',port_directions=dict(C='input',D='input',Q='output'),connections=dict(C=[2],D=[d],Q=[q]))
    cells={};nets={}
    for lev in range(1,4):
        bits=[100*lev+k for k in range(4)]
        # RTL star: every level-L copy reads the canonical level-(L-1) copy (bit 0); names sort out of order
        for k,q in enumerate(bits):cells[f'z{(7*k)%4}_l{lev}_{k}']=ff(1 if lev==1 else 100*(lev-1),q)
        nets[f'rst_n__ot_rl{lev}v']=dict(bits=bits)
    cells['load']=dict(type='$_AND_',port_directions=dict(A='input',B='input',Y='output'),connections=dict(A=[303],B=[5],Y=[6]))
    nl=dict(modules=dict(top=dict(attributes=dict(top='1'),ports={},cells=cells,netnames=nets)))
    _,rs=RS.analyse(nl,32,RS.DEFAULT_RE)
    by={r['family']:r for r in rs}
    assert all(r['status']=='OK' for r in rs)
    assert by['rst_n__ot_rl1v']['chain'] and by['rst_n__ot_rl2v']['chain'] and not by['rst_n__ot_rl3v']['chain']
    for lev in (1,2):
        cmds=by[f'rst_n__ot_rl{lev}v']['cmds']
        for k in range(1,4):
            child=[c for c in cells if c.endswith(f'_l{lev+1}_{k}')][0]
            assert f'connect -port \\{child} D \\ot_rrs__rst_n__ot_rl{lev}v__c{k}' in cmds,(lev,k)
