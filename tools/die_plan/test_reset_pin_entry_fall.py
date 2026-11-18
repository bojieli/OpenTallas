"""Measured negedge-before-posedge entries, exact counted frame and wrong-edge control."""
from types import SimpleNamespace
import copy, json, re, shutil, subprocess
from pathlib import Path
import pytest
import gen_rtl as G
import reset_tree as R


def tree():
    return dict(type='t',entry='relayed',sync_stages=2,root=[10,10],start=True,
                relays=[dict(name='u_rrl_0',d='rst_root_n',q='rst_n_t0',xy=[12,10],depth=1,tap=0,kind='tap')],
                taps=['clk'],own_depth=1,depth=1,n_tree=1,n_pad=0,max_hop_um=2,reach_um=405,outs=[],
                core_resets=[],relay_driver=False,start_in=[10,12],start_role='mission',tap_roles={0:'mission'},start_tap=None)


def configured(t=None, flag=True):
    return R._type_pin_entry_fall(SimpleNamespace(types={'t':{'reset':{'pin_entry_fall':flag}}}), 't',t or tree())


def wrapper(t, module):
    return ('module '+module+'(input clk,rst_raw_n_in,p_start,output rst_raw_n_out,start);\n'+
            '\n'.join(R.rtl_lines(t,src='rst_raw_n_in',start_src='p_start'))+
            '\nassign rst_raw_n_out=rst_root_n;assign start=run_root;endmodule\n')


def test_absent_off_preserves_source_and_release_count():
    t=tree();p=SimpleNamespace(types={'t':{'reset':{}}})
    assert R._type_pin_entry_fall(p,'t',t) is t
    assert configured(t,False) is t
    assert not G.uses_entry_fall({'partition_types':p.types})
    new=configured(t)
    assert R.release_clocks(new)==R.release_clocks(t)
    text='\n'.join(R.rtl_lines(new))
    assert 'ot_dp_rrelay_fn u_rst_in ' in text and 'ot_dp_rrelay_fn u_run_in ' in text
    assert 'ot_dp_rgate u_rrl_0 ' in text
    assert G.uses_entry_fall({'partition_types':{'t':{'reset':{'pin_entry_fall':True}}}})


def test_unqualified_root_or_copies_refused():
    t=tree();t['entry']='sync'
    with pytest.raises(R.ResetError,match='synchronous relayed'):configured(t)
    t=tree();t['pin_root_copies']={'copies':[]}
    with pytest.raises(R.ResetError,match='own measured'):configured(t)
    with pytest.raises(R.ResetError,match='boolean'):configured(flag=1)


BENCH=r'''
`timescale 1ps/1fs
module tb;
 parameter real T=833.0, PHASE=310.0, DUTY=459.0, DATA_R=300.0, DATA_S=300.0;
 parameter integer JR=1,JS=1;
 reg sc=0,rc=0,rs=0,ss=0;wire rw,sw,r,s,mr,ms;
 integer sn=-1,rn=-1,errors=0,mutants=0;
 function automatic ra(input integer n);ra=n>=0 && (n%5==0 || n%5==2 || n%5==3);endfunction
 function automatic sa(input integer n);sa=n>=0 && (n%7==0 || n%7==1 || n%7==4);endfunction
 initial begin #1 sc=1;forever #(T/2) sc=~sc;end
 initial begin #(PHASE+1) rc=1;forever begin #(DUTY)rc=0;#(T-DUTY)rc=1;end end
 always @(posedge sc)begin sn=sn+1;rs<=ra(sn);ss<=sa(sn);end
 assign #(DATA_R) rw=rs;assign #(DATA_S) sw=ss;
 actual dut(rc,rw,sw,r,s);wrong_edge mutant(rc,rw,sw,mr,ms);
 always @(posedge rc)begin
  rn=rn+1;#0.01;
  if(rn>=3)begin
   if(r!==ra(rn-JR)||s!==sa(rn-JS))errors=errors+1;
   if(mr!==ra(rn-JR)||ms!==sa(rn-JS))mutants=mutants+1;
  end
  if(rn==90)begin $display("RESULT errors%0d mutants%0d",errors,mutants);if(errors)$fatal(1,"count frame");$finish;end
 end
endmodule
'''


def test_emitted_two_bit_entries_against_count_frame_and_wrong_edge(tmp_path):
    if not shutil.which('iverilog'):pytest.skip('iverilog required for minimum component')
    import math
    sv=G.CELLS+G.ENTRY_FALL_CELLS+wrapper(configured(),'actual')+wrapper(tree(),'wrong_edge')+BENCH
    (tmp_path/'dut.sv').write_text(sv)
    # Measured TT/FF phase/duty/transport extrema, independent RESET and START data.
    cases=[(p,d,r,s) for p,d in [(310.139438,459.119133),(518.806744,669.841683),
                               (290.908732,450.816462),(477.716412,639.132973)]
                     for r,s in [(300.857,300.349),(371.5235,371.2764),(219.602,219.244),(261.3891,261.1713)]]
    total_mutants=0
    for i,(phase,duty,dr,ds) in enumerate(cases):
        jr=1-math.floor((phase+duty-dr)/833);js=1-math.floor((phase+duty-ds)/833)
        cmd=['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim')]
        cmd += [f'-Ptb.{k}={v}' for k,v in dict(PHASE=phase,DUTY=duty,DATA_R=dr,DATA_S=ds,JR=jr,JS=js).items()]
        compile=subprocess.run(cmd+[str(tmp_path/'dut.sv')],capture_output=True,text=True)
        assert compile.returncode==0,compile.stderr
        run=subprocess.run(['vvp',str(tmp_path/'sim')],capture_output=True,text=True)
        assert run.returncode==0,(i,run.stdout,run.stderr)
        m=re.search(r'RESULT errors(\d+) mutants(\d+)',run.stdout);assert m
        assert int(m[1])==0;total_mutants+=int(m[2])
    assert total_mutants>0
