"""Independent reset/START consumers preserve clock ports and published release."""
import copy
import json
import re
from pathlib import Path
import pytest
import reset_tree as RT
import schema as S

HERE=Path(__file__).parent

def plan():
    raw=json.loads((HERE/'examples/tiny_plan.json').read_text())
    raw['reset'].update(release='wavefront',start='broadcast')
    for t in raw['partition_types'].values():
        w,h=t['outline_um']
        t.setdefault('reset',{})['local_taps_um']=[[w*.3,h*.3],[w*.7,h*.7]]
    return S.Plan(raw)

def test_consumers_preserve_clock_ports_and_output_identity():
    p=plan()
    for tn in p.types:
        before=list(S.tap_grid(p,tn)); cs=RT.consumer_taps(p,tn)
        assert cs[:len(before)]==before and len(cs)==len(before)+2
        tree=RT.for_type(p,tn)
        assert tree['n_clock_taps']==len(before)
        assert RT.consumer_count(tree)==len(cs)
        assert RT.verify(tree)==[]
        assert S.tap_grid(p,tn)==before
        lines='\n'.join(RT.rtl_lines(tree))
        n=RT.consumer_count(tree)
        for i in range(n):assert f'wire rst_n_t{i};' in lines
        for j in range(len(tree['outs'])):
            assert f'assign rst_o_{j} = rr_t{n+j};' in lines
        roles={r['q']:r['role'] for r in RT.start_relays(tree)}
        assert all(roles[f'rst_n_t{i}']=='gated' for i in range(n))
        assert '(* keep = 1 *) wire rst_n_t' in lines
    w=RT.wf_plan(p)
    for tn,t in w['types'].items():
        assert t['reset_consumers']==len(RT.consumer_taps(p,tn))
        assert t['release_after_pin']==RT.release_clocks(RT.for_type(p,tn))

def test_local_taps_reject_blocked_or_external_sites():
    for site in [[0,0],[-1,10],[100000,10]]:
        p=plan();tn=next(iter(p.types));p.types[tn]['reset']['local_taps_um']=[site]
        with pytest.raises(RT.ResetError):RT.consumer_taps(p,tn)

def test_bound_native_station_reset_uses_planned_geometry():
    import kit_rsync
    p=plan();tn=next(iter(p.types)); taps=RT.consumer_taps(p,tn)
    native={'partition_types':{tn:{'internal_stations':[{'conn':'bus:o_x','regs_um':[[taps[-1][1],taps[-1][2]]]}]}}}
    select=kit_rsync._nearest_rsel(p,tn,taps,native)
    assert select('u_ist_o_x_0')==f'rst_n_t{len(taps)-1}'

def test_extra_consumer_release_lockstep_and_mutant():
    # Every terminal is exactly D synchronous stages below the input. Compare
    # old and extra consumers cycle-by-cycle, including a falling assertion.
    p=plan();t=RT.for_type(p,next(iter(p.types)))
    rel=RT.start_relays(t); state={r['q']:0 for r in rel}
    good=[];mutant=[]
    for cyc in range(2*t['depth']+20):
        reset=int(3<=cyc<2*t['depth']+10);start=int(cyc>=6)
        src=dict(state,rst_root_n=reset,run_root=start)
        state={r['q']:src[r['d']] & (src[r['run']] if 'run' in r else 1) for r in rel}
        q=[state[f'rst_n_t{i}'] for i in range(RT.consumer_count(t))]
        assert len(set(q))==1
        good.append(q[-1]);mutant.append(reset & start) # direct reset/START bypass
    assert good!=mutant

def test_generated_rtl_lockstep_with_depth_spec_and_bypass_mutant(tmp_path):
    import shutil, subprocess
    import gen_rtl
    if not shutil.which('iverilog'):pytest.skip('iverilog unavailable')
    p=plan();t=RT.for_type(p,RT.wf_solve(p)['root_type'])
    n=RT.consumer_count(t);lat=RT.release_clocks(t)
    body='\n'.join(RT.rtl_lines(t))
    wires='\n'.join(f'wire rst_o_{j}, start_o_{j};' for j in range(len(t['outs'])))
    cells=tmp_path/'cells.sv';cells.write_text(gen_rtl.CELLS)
    rtl=tmp_path/'top.sv'
    rtl.write_text(f'''module dut(input wire clk, arst_n, start_i, output wire old_q, local_q);
{wires}
{body}
assign old_q=rst_n_t0;
assign local_q=rst_n_t{n-1};
endmodule
module tb;
reg clk=0, arst_n=0, start_i=0;
always #5 clk=~clk;
wire old_q, local_q;
dut u(clk,arst_n,start_i,old_q,local_q);
reg [{lat-1}:0] spec=0;
integer bad=0, mutant_mismatch=0, cyc=0;
always @(posedge clk) begin
spec <= {{spec[{lat-2}:0], arst_n & start_i}};
#1;
if(cyc >= {lat+2} && (old_q !== spec[{lat-1}] || local_q !== spec[{lat-1}])) bad=bad+1;
if(local_q !== (arst_n & start_i)) mutant_mismatch=mutant_mismatch+1;
cyc=cyc+1;
end
initial begin
repeat(8) @(negedge clk); arst_n=1;
repeat(5) @(negedge clk); start_i=1;
repeat({lat+8}) @(negedge clk);
$display("RESULT bad=%0d mutant=%0d",bad,mutant_mismatch);$finish;
end
endmodule''')
    exe=tmp_path/'sim'
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(cells),str(rtl)],check=True,capture_output=True,text=True)
    out=subprocess.run(['vvp',str(exe)],check=True,capture_output=True,text=True).stdout
    m=re.search(r'RESULT bad=(\d+) mutant=(\d+)',out)
    assert m and int(m[1])==0 and int(m[2])>0,out

def test_physical_hook_uses_local_reset_sites_without_extra_clock_pins(tmp_path):
    import gen_phys
    p=plan();tn=next(iter(p.types));before=S.tap_grid(p,tn)
    kit=gen_phys.write_type_kit(p,tn,tmp_path,[])
    hook=(kit/'reset_taps.tcl').read_text()
    assert 'set rt_consumer_taps_um {' in hook
    assert f'{{{len(before)} ' in hook
    assert len(S.tap_grid(p,tn))==len(before)
    assert 'rt_consumer_taps_um' in hook and 'round($y * $rt_dbu)' in hook

def test_pipelined_local_consumers_kept_and_sparse_tree_count():
    p=plan();raw=copy.deepcopy(p.raw);raw['reset']['release']='pipelined';raw['reset'].pop('start',None)
    p=S.Plan(raw);tn=next(iter(p.types));t=RT.for_type(p,tn)
    assert t['local_reset_taps'] and RT.consumer_count(t)==len(RT.consumer_taps(p,tn))
    assert RT.verify(t)==[] and '(* keep = 1 *) wire rst_n_t' in '\n'.join(RT.rtl_lines(t))
    assert RT.consumer_count({'n_clock_taps':0})==0

def test_replan_native_initialized_leaf_keeps_one_reset_driver(tmp_path):
    import kit_rsync
    p=plan();tn=next(iter(p.types));raw=copy.deepcopy(p.raw)
    raw['partition_types'][tn]['reset']['leaf_um']=raw['partition_types'][tn]['reset']['local_taps_um'][-1]
    pn=tmp_path/'plan.json';pn.write_text(json.dumps(raw));p=S.Plan(raw,pn)
    before=copy.deepcopy(raw)
    for t in before['partition_types'].values():t['reset'].pop('local_taps_um',None);t['reset'].pop('leaf_um',None)
    old=RT.for_type(S.Plan(before),tn)
    new_leaf=RT.leaf_tap(p,tn);assert new_leaf!=0
    kd=tmp_path/'kit';kd.mkdir();b=kd/'toy_bound.sv';c=kd/'bind_cells.sv'
    b.write_text('module toy_bound (\ninput wire clk,\ninput wire arst_n,\ninput wire [3:0] x\n);\n'+
                 '\n'.join(RT.rtl_lines(old))+'\nwire rst_n = rst_n_t0;\nendmodule\n')
    c.write_text('module ot_dp_st #(parameter W=1) (input wire clk);\nendmodule\n')
    (kd/'kit_rtl.json').write_text(json.dumps({'files':[str(b),str(c)],'bound_module':'toy_bound'}))
    for _ in range(2):
        assert kit_rsync.main([str(pn),tn,str(kd)])==0
        text=b.read_text()
        assert 'wire rst_n = ' not in text
        assert len(re.findall(r'assign rst_n = rst_n_t\d+;',text))==1
        assert f'assign rst_n = rst_n_t{new_leaf};' in text
        assert text.count('wire rst_n;')==1


def test_explicit_reset_seed_does_not_consume_or_qualify_sink_budget(monkeypatch):
    import taps
    p = plan()
    tn = next(iter(p.types))
    p.types[tn].setdefault("clock", {}).update(tap_mode="explicit", taps=[dict(name="clk", xy=[30, 30])])
    def budget(*args, **kwargs):
        raise ValueError("actual sink budget remains blocked")
    monkeypatch.setattr(taps, "explicit_taps", budget)
    assert RT._taps(p, tn) == taps.explicit_tap_sites(p, tn)
    with pytest.raises(ValueError, match="sink budget remains blocked"):
        S.tap_grid(p, tn)
    p.types[tn]["clock"]["taps"][0]["xy"] = [-1, -1]
    RT._TAPS.clear()
    with pytest.raises(ValueError, match="outline/halo/tap spacing"):
        RT._taps(p, tn)
