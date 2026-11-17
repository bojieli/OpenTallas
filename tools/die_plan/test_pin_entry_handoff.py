"""Two-register production handoff and its explicit +1 boot epoch."""
from types import SimpleNamespace
from pathlib import Path
import copy,json,shutil,subprocess
import pytest
import pin_entry_handoff as H
import gen_rtl as G
import reset_tree as R
import schema
from test_reset_pin_entry_fall import tree,wrapper


def configured(t=None,s=None):
    p=SimpleNamespace(types={'t':{'reset':{'pin_entry_handoff':s or {'clock_buffers':30,'physical_form':'post_route_branch_fork'}}}})
    return H.configure(p,'t',t or tree(),R.ResetError)


def test_default_and_explicit_hardware_cycle_contract():
    t=tree();p=SimpleNamespace(types={'t':{'reset':{}}});assert H.configure(p,'t',t) is t
    new=configured();assert R.entry_stages(t)==1 and R.entry_stages(new)==2
    assert R.release_clocks(new)==R.release_clocks(t)+1
    rtl='\n'.join(R.rtl_lines(new));assert rtl.count('ot_dp_rrelay_handoff ')==2
    phy=H.physical_contract(new);assert phy['status']=='PLANNED_NOT_BUILT_BY_GEN'
    assert phy['clock_buffers']==30 and phy['required_capture_pins']==phy['required_local_handoff_pins']==2
    price=H.summary(new)['pin_entry_handoff'];assert price['added_flops']==2 and price['added_whole_boot_cycles']==1 and price['added_arithmetic_cycles']==0
    tcl=R.tcl_text(new)
    assert '*u_rst_in[./]q*' in tcl and '*u_rst_in[./]cap*' in tcl
    assert '*u_run_in[./]q*' in tcl and '*u_run_in[./]cap*' in tcl
    # Each graph key follows the final local-clock Q, never the phase-capture Q.
    assert 'rtr_place rst_root_n {*u_rst_in[./]q*}' in tcl
    assert 'rtr_place run_root {*u_run_in[./]q*}' in tcl
    for change in [dict(entry='sync'),dict(pin_entry_fall=True),dict(pin_entry_delay={'reset':1}),dict(pin_root_copies={1:2})]:
        q=tree();q.update(change)
        with pytest.raises(R.ResetError):configured(q)
    for spec in [dict(clock_buffers=0,physical_form='post_route_branch_fork'),dict(clock_buffers=30,physical_form='already_built')]:
        with pytest.raises(R.ResetError):configured(s=spec)


def test_published_wavefront_accounts_for_new_boot_stage():
    here=Path(__file__).resolve().parent
    raw=json.loads((here/'examples/s81_pair/s81_pair_plan.json').read_text())
    raw.setdefault('reset',{}).update(release='wavefront',start='broadcast')
    old=R.wf_plan(schema.Plan(copy.deepcopy(raw)))
    raw['partition_types']['fa'].setdefault('reset',{})['pin_entry_handoff']={'clock_buffers':30,'physical_form':'post_route_branch_fork'}
    assert schema.validate(raw)==[]
    p=schema.Plan(raw);new=R.wf_plan(p)
    assert new['types']['fa']['entry_stages']==2
    assert new['max_release']==old['max_release']+1
    for name,row in new['parts'].items():
        if row['type']=='fa':
            assert row['release']==old['parts'][name]['release']+1
            assert row['entry_stages']!=1 # old-cycle accounting negative control
        else:assert row['release']==old['parts'][name]['release']


BENCH=r'''
`timescale 1ps/1fs
module tb;
 reg clk=0,r=0,s=0;wire qr,qs,mr,ms;reg er,es,rr,rs;integer n=0,errors=0,missing=0,oldcycle=0;
 always #5 clk=~clk;
 actual dut(clk,r,s,qr,qs);missing_stage mutant(clk,r,s,mr,ms);
 always @(negedge clk)begin n=n+1;r<=n>5&&(n%4==1||n%4==2);s<=n>5&&(n%4==2||n%4==3);end
 always @(posedge clk)begin
  er<=r;es<=s;rr<=er;rs<=es;#0.01;
  if(n>7)begin
   if(qr!==rr||qs!==rs)errors=errors+1;
   if(mr!==rr||ms!==rs)missing=missing+1;
   if(qr!==er||qs!==es)oldcycle=oldcycle+1;
  end
  if(n==100)begin $display("RESULT errors%0d missing%0d oldcycle%0d",errors,missing,oldcycle);if(errors||!missing||!oldcycle)$fatal(1,"handoff");$finish;end
 end
endmodule
'''


def test_emitted_two_bit_handoff_against_golden_and_two_mutants(tmp_path):
    if not shutil.which('iverilog'):pytest.skip('iverilog required')
    t=configured();w=wrapper(t,'actual');mw=wrapper(t,'missing_stage').replace('ot_dp_rrelay_handoff','ot_dp_rrelay_handoff_missing')
    mutant=H.CELL_RTL.replace('ot_dp_rrelay_handoff','ot_dp_rrelay_handoff_missing').replace('q<=cap','q<=d')
    f=tmp_path/'dut.sv';f.write_text(G.CELLS+H.CELL_RTL+mutant+w+mw+BENCH)
    c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim'),str(f)],capture_output=True,text=True);assert c.returncode==0,c.stderr
    p=subprocess.run(['vvp',str(tmp_path/'sim')],capture_output=True,text=True);assert p.returncode==0,p.stdout+p.stderr
    assert 'RESULT errors0 missing' in p.stdout
