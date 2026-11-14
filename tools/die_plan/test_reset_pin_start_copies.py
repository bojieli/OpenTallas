"""Explicit START pin source replication keeps the sampled RESET/START lifecycle."""
import copy,json,shutil,subprocess
from types import SimpleNamespace
from pathlib import Path
import pytest
import reset_tree as R
import gen_rtl,gen_phys as G,bound_reset_contract as B
from test_reset_pin_root_copies import tree


def spec(signals=('reset','start')):
    s=dict(max_loads=48,signals=list(signals),sites_um=[[10,10],[12.16,10]])
    if list(signals)==['start']:s['sites_um']=[[10,12],[12.16,12]]
    if set(signals)=={'reset','start'}:s['start_sites_um']=[[10,12],[12.16,12]]
    return s


def test_pair_explicit_only_and_real_loads():
    t=tree(start=True);new=R.with_pin_root_copies(t,spec(),[300,100])
    assert t['relays']==new['relays'] and R.release_clocks(t)==R.release_clocks(new)==5
    assert [len(c['loads'])for c in R.pin_start_copies(new)]==[48,27]
    assert [len(c['loads'])for c in R.pin_root_copies(new)]==[48,27]
    assert R.verify(new)==[]
    default=R.with_pin_root_copies(t,dict(max_loads=48,sites_um=[[10,10],[12.16,10]]))
    assert 'pin_start_copies'not in default
    assert 'u_run_in_c1'not in '\n'.join(R.rtl_lines(default))


def test_start_only_does_not_silently_change_reset():
    t=R.with_pin_root_copies(tree(start=True),spec(('start',)))
    assert 'pin_root_copies'not in t
    assert 'pin_start_copies'in t
    src='\n'.join(R.rtl_lines(t));assert 'ot_dp_rrelay u_rst_in ('in src
    assert 'u_rst_in_c1'not in src and 'u_run_in_c1'in src


@pytest.mark.parametrize('bad',[
    dict(max_loads=48,signals=[],sites_um=[[10,10]]),
    dict(max_loads=48,signals=['clock'],sites_um=[[10,10]]),
    dict(max_loads=48,signals=['start','start'],sites_um=[[10,12],[12.16,12]]),
    dict(max_loads=48,signals=[['start']],sites_um=[[10,12]]),
    dict(max_loads=48,signals=['reset','start'],sites_um=[[10,10],[12.16,10]]),
    dict(max_loads=48,signals=['reset'],sites_um=[[10,10],[12.16,10]],start_sites_um=[[10,12],[12.16,12]]),
])
def test_ambiguous_or_missing_signal_metadata_rejected(bad):
    with pytest.raises(R.ResetError):R.with_pin_root_copies(tree(start=True),bad)


def test_start_requires_actual_tree_and_matching_entry_site():
    with pytest.raises(R.ResetError,match='actual START'):R.with_pin_root_copies(tree(),spec(('start',)))
    s=spec();s['start_sites_um'][0]=[11,12]
    with pytest.raises(R.ResetError,match='original pin'):R.with_pin_root_copies(tree(start=True),s)


def native(tmp_path,mutate=lambda s:s):
    t=R.with_pin_root_copies(tree(start=True),spec(),[300,100])
    text='module top(input clk,arst_n,start_i);bound u_bound(.clk(clk),.arst_n(arst_n),.start_i(start_i));endmodule\nmodule bound(input clk,arst_n,start_i);\n'+'\n'.join(R.rtl_lines(t))+'\nendmodule\n'+gen_rtl.CELLS
    f=tmp_path/'native.sv';f.write_text(mutate(text))
    p=SimpleNamespace(types={'t':dict(module='top',outline_um=[300,100],clock={'landing_contract':{'collector_tree':t}})})
    return p,f,t


def test_paired_fresh_native_source_and_all_copy_sites(tmp_path):
    p,f,t=native(tmp_path);c=G.install_bound_native_reset(p,'t',[f])
    assert c['native_paths']['u_run_in_c1']=='u_bound.u_run_in_c1'
    assert any(x['d']=='run_root_copy_1'for x in c['physical_nodes'])
    r=B.emitted(f,'t',t);B.stage(tmp_path,r,c)
    text=(tmp_path/'reset_tree.tcl').read_text()
    assert 'u_bound[./]u_run_in_c1[./]*'in text and 'sentry_copy'in text


@pytest.mark.parametrize('mutate',[
    lambda s:s.replace('u_run_in_c1 (.clk(clk), .d(start_i)','u_run_in_c1 (.clk(clk), .d(run_root)'),
    lambda s:s.replace('u_run_in_c1 (.clk(clk), .d(start_i)','u_run_in_c1 (.clk(wrong), .d(start_i)'),
    lambda s:s.replace('u_run_in_c1 (','missing_start_copy ('),
    lambda s:s.replace('module bound(input clk,arst_n,start_i);','module bound(input clk,arst_n,start_i);wire sneaky;assign sneaky=run_root_copy_1;'),
])
def test_start_native_bad_stage_clock_missing_or_extra_load_refused(tmp_path,mutate):
    p,f,t=native(tmp_path,mutate)
    with pytest.raises(gen_rtl.GenError):G.install_bound_native_reset(p,'t',[f])


def test_pair_reset_and_start_lifecycle_and_start_delay_mutant(tmp_path):
    if not shutil.which('iverilog'):pytest.skip('iverilog unavailable')
    old=tree(start=True);new=R.with_pin_root_copies(old,spec(),[300,100])
    def mod(name,t,mut=False):
        body='\n'.join(R.rtl_lines(t))
        if mut:body=body.replace('u_run_in_c1 (.clk(clk), .d(start_i)','u_run_in_c1 (.clk(clk), .d(run_root)')
        return f'module {name}(input clk,arst_n,start_i,output[74:0]q);\n{body}\nassign q={{{",".join(f"rst_n_t{i}"for i in range(74,-1,-1))}}};\nendmodule\n'
    bench='''module tb;reg clk=0,arst_n=0,start_i=0;always #416.5 clk=~clk;wire[74:0]a,b,m;
nominal a0(clk,arst_n,start_i,a);copies b0(clk,arst_n,start_i,b);mutant m0(clk,arst_n,start_i,m);
integer i,checks=0,caught=0;initial begin for(i=0;i<384;i=i+1)begin @(negedge clk);arst_n=(i>12&&i%59>4);start_i=(i>23&&i%47>6);@(posedge clk);#1;
if(i>12)begin checks=checks+1;if(a!==b)$fatal(1,"paired lifecycle differs%0d",i);if(a!==m)caught=caught+1;end end
if(caught==0)$fatal(1,"START mutant escaped");$display("PASS checks=%0d mutant=%0d",checks,caught);$finish;end endmodule
'''
    src=tmp_path/'tb.sv';src.write_text('`timescale 1ps/1fs\n'+gen_rtl.CELLS+mod('nominal',old)+mod('copies',new)+mod('mutant',new,True)+bench)
    exe=tmp_path/'sim';subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(src)],check=True,capture_output=True,text=True)
    p=subprocess.run(['vvp',str(exe)],check=True,capture_output=True,text=True);assert 'PASS checks=371'in p.stdout,p.stdout


def test_control_copy_sinks_use_sites_without_reset_recursion(monkeypatch):
    import taps
    from test_explicit_control_taps import plan
    p=plan();p.types['src']['reset']['pin_root_copies']=spec()
    monkeypatch.setattr(R,'for_type',lambda *a,**k:pytest.fail('recursive reset solve'))
    out=taps.control_pin_sinks(p,'src')
    assert ('u_rst_in_c1',12.16,10.0)in out and ('u_run_in_c1',12.16,12.0)in out
    base=sum(v[2]for v in taps.sink_sites(p,'src',control=False))
    assert sum(v[2]for v in taps.sink_sites(p,'src'))==base+len(out)
    p.types['src']['reset']['pin_root_copies']=dict(max_loads=48,sites_um=[[10,10],[12.16,10]])
    out=taps.control_pin_sinks(p,'src');assert not any(n=='u_run_in_c1'for n,*_ in out)


def test_captured_control_copy_sites_win_over_absent_config(monkeypatch):
    import taps
    from test_explicit_control_taps import plan
    p=plan();t=R.with_pin_root_copies(tree(start=True),spec(),[300,100]);p._bound_native_reset_contracts={'src':dict(tree=t,placement_sites={'u_run_in_c1':[13.5,12]})}
    monkeypatch.setattr(R,'for_type',lambda *a,**k:pytest.fail('recursive reset solve'))
    monkeypatch.setattr(R,'_start_sites',lambda *a,**k:(tuple(t['start_in']),[]))
    out=taps.control_pin_sinks(p,'src');assert ('u_run_in_c1',13.5,12.0)in out and ('u_rst_in_c1',12.16,10.0)in out
