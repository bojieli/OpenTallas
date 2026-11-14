"""Explicit same-edge reset pin copies preserve release and their captured source."""
import copy,json,shutil,subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
import reset_tree as R
import gen_phys as G
import gen_rtl
import bound_reset_contract as B


def tree(n=75,depth=4,start=False):
    rel=[]
    for i in range(n):
        d='rst_root_n'
        for j in range(1,depth+1):
            q=f'rst_n_t{i}' if j==depth else f'rst_rl_{i}_{j}'
            rel.append(dict(name=f'u_rrl_{i*depth+j-1}',d=d,q=q,xy=[20+2*i,20],depth=j,tap=i if j==depth else None,kind='tap' if j==depth else'pad'))
            d=q
    t=dict(type='t',entry='relayed',sync_stages=2,root=[10,10],start=start,relays=rel,taps=[f'clk_t{i}'for i in range(n)],own_depth=depth,depth=depth,n_tree=n,n_pad=n*(depth-1),max_hop_um=20+2*(n-1),reach_um=405,outs=[],core_resets=[],relay_driver=False)
    if start:t.update(start_in=[10,12],start_role='mission',tap_roles={i:'mission'for i in range(n)},start_tap=None)
    return t


def copied(t=None):
    t=t or tree()
    n=sum(len(x)for _,x in R._pin_root_loads(t));count=(n+47)//48
    return R.with_pin_root_copies(t,dict(max_loads=48,sites_um=[[10+2.16*i,10]for i in range(count)]),[300,100])


def test_parallel_copies_keep_canonical_ancestry_and_capacity():
    t=tree();new=copied(t)
    assert t['relays']==new['relays'] and t['depth']==new['depth']
    assert R.release_clocks(t)==R.release_clocks(new)==5
    copies=R.pin_root_copies(new)
    assert [len(c['loads'])for c in copies]==[48,27]
    assert sum(len(c['loads'])for c in copies)==75
    assert R.verify(new)==[]
    text='\n'.join(R.rtl_lines(new))
    assert 'u_rst_in_c1 (.clk(clk), .d(arst_n)' in text
    assert '.d(rst_root_copy_1_n)' in text
    assert new['pin_root_copies']['physical_max_hop_um']<=405


def test_start_expansion_counts_actual_d_loads_and_retains_run_entry():
    t=tree(n=75,depth=1,start=True);t['bootstrap_taps']=list(range(75));new=copied(t)
    assert new['pin_root_copies']['physical_direct_loads']==150
    assert len(R.pin_root_copies(new))==4
    body='\n'.join(R.rtl_lines(new))
    assert body.count('ot_dp_rrelay u_run_in ')==1
    assert '.d(start_i), .q(run_root)' in body


@pytest.mark.parametrize('spec',[
    {'max_loads':49,'sites_um':[[10,10],[12,10]]},
    {'max_loads':48,'sites_um':[[10,10]]},
    {'max_loads':48,'sites_um':[[11,10],[12,10]]},
    {'max_loads':48,'sites_um':[[10,10],[999,10]]},
    {'max_loads':True,'sites_um':[[10,10],[12,10]]},
])
def test_bad_opt_in_fails_closed(spec):
    with pytest.raises(R.ResetError):R.with_pin_root_copies(tree(),spec,[300,100])


def test_async_root_and_tampered_captured_loads_rejected():
    t=tree();t['entry']='sync'
    with pytest.raises(R.ResetError,match='synchronous'):copied(t)
    t=copied();t['pin_root_copies']['copies'][1]['loads'].pop()
    with pytest.raises(R.ResetError,match='inventory'):R.pin_root_copies(t)


def native_fixture(tmp_path,mutate=lambda s:s,start=False):
    t=copied(tree(start=start));f=tmp_path/'native.sv'
    text='module top(input clk,arst_n,start_i); bound u_bound(.clk(clk),.arst_n(arst_n),.start_i(start_i)); endmodule\nmodule bound(input clk,arst_n,start_i);\n'+'\n'.join(R.rtl_lines(t))+'\nendmodule\n'+gen_rtl.CELLS
    f.write_text(mutate(text))
    p=SimpleNamespace(types={'t':dict(module='top',outline_um=[300,100],clock={'landing_contract':{'collector_tree':t}})})
    return p,f,t


@pytest.mark.parametrize('start',[False,True])
def test_fresh_native_contract_verifies_real_copies_and_physical_edges(tmp_path,start):
    p,f,t=native_fixture(tmp_path,start=start);c=G.install_bound_native_reset(p,'t',[f])
    assert c['native_paths']['u_rst_in_c1']=='u_bound.u_rst_in_c1'
    assert any(r['d']=='rst_root_copy_1_n'for r in c['physical_nodes'])
    assert R.for_type(p,'t')==t
    rec=B.emitted(f,'t',t)
    assert B.validate(json.loads(json.dumps(rec)),'t')
    staged=B.stage(tmp_path,rec,c)
    assert staged['native_paths']['u_rst_in_c1']=='u_bound.u_rst_in_c1'
    text=(tmp_path/'reset_tree.tcl').read_text()
    assert 'u_bound[./]u_rst_in_c1[./]*'in text and 'rentry_copy'in text


@pytest.mark.parametrize('mutate',[
 lambda s:s.replace('u_rst_in_c1 (','u_rst_in_removed ('),
 lambda s:s.replace('u_rst_in_c1 (.clk(clk), .d(arst_n)','u_rst_in_c1 (.clk(wrong_clk), .d(arst_n)'),
 lambda s:s.replace('u_rst_in_c1 (.clk(clk), .d(arst_n)','u_rst_in_c1 (.clk(clk), .d(rst_root_n)'),
 lambda s:s.replace('module bound(input clk,arst_n,start_i);','module bound(input clk,arst_n,start_i);\nwire sneaky;assign sneaky=rst_root_copy_1_n;'),
])
def test_native_wrong_missing_delayed_or_extra_load_refused(tmp_path,mutate):
    p,f,t=native_fixture(tmp_path,mutate)
    with pytest.raises(gen_rtl.GenError):G.install_bound_native_reset(p,'t',[f])


@pytest.mark.parametrize('start',[False,True])
def test_reset_lifecycle_actual_emitter_and_effective_mutant(tmp_path,start):
    if not shutil.which('iverilog'):pytest.skip('iverilog unavailable')
    t=tree(start=start);new=copied(t)
    def mod(name,tr,mut=False):
        body='\n'.join(R.rtl_lines(tr))
        if mut:body=body.replace('u_rst_in_c1 (.clk(clk), .d(arst_n)','u_rst_in_c1 (.clk(clk), .d(rst_root_n)')
        assign=','.join(f'rst_n_t{i}'for i in range(74,-1,-1))
        return f'module {name}(input clk,arst_n,start_i,output[74:0]q);\n{body}\nassign q={{{assign}}};\nendmodule\n'
    bench='''module tb;reg clk=0,arst_n=0,start_i=0;always #416.5 clk=~clk;wire[74:0]a,b,m;
nominal a0(clk,arst_n,start_i,a);copies b0(clk,arst_n,start_i,b);mutant m0(clk,arst_n,start_i,m);
integer i,checks=0,caught=0;initial begin
for(i=0;i<384;i=i+1)begin @(negedge clk);arst_n=(i>12&&i%59>4);start_i=(i>23&&i%47>6);@(posedge clk);#1;
if(i>12)begin checks=checks+1;if(a!==b)$fatal(1,"copy lifecycle differs cycle%0d",i);if(a!==m)caught=caught+1;end end
if(caught==0)$fatal(1,"mutant escaped");$display("PASS checks=%0d mutant=%0d",checks,caught);$finish;end endmodule
'''
    src=tmp_path/'tb.sv';src.write_text('`timescale 1ps/1fs\n'+gen_rtl.CELLS+mod('nominal',t)+mod('copies',new)+mod('mutant',new,True)+bench)
    exe=tmp_path/'sim';subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(src)],check=True,capture_output=True,text=True)
    p=subprocess.run(['vvp',str(exe)],check=True,capture_output=True,text=True)
    assert 'PASS checks=371'in p.stdout,p.stdout
