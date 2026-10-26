#!/usr/bin/env python3
"""Replay actual banded gather pins against the preserved full geometry."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import types
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/'tools/hier_contract'),str(R/'tools/s81'),str(R/'tools')]
import pin_align as PA
import banded_terminal as BT
import dsrom_s81_fulldie as G

CASES=dict(
    # r8c historical: R0 station west of the hard W port rW2
    r8d=dict(out='results/physical/die_iter_1012/s81/r8d_banded_1015',
             plan='results/physical/die_iter_1012/s81/hcp_home_growth_1015/plan_r8c.json.gz', pins=None,
             old='g_hr_W2_o_d1_sp_gather_0', prev='f_hr_W2_o_1', port='rW2', side='W',
             slices=[(0,275),(276,551),(552,758)]),
    # S-DIE r2 2026-10-15: GEN19b's only pin_align FAIL, the mirror (MY station east of the hard E port rE2)
    gen19b=dict(out='results/physical/die_iter_1012/s81/gen19b_banded_e_1015', plan=None, pins=None,
                old='f_hr_E2_o_4', prev='f_hr_E2_o_3', port='rE2', side='E', slices=None))

def main(case='r8d', plan_arg=None, pins_arg=None):
    C=CASES[case]
    out=R/C['out']; out.mkdir(parents=True,exist_ok=True)
    plan_path=Path(plan_arg) if plan_arg else R/C['plan']
    pp_path=Path(pins_arg) if pins_arg else out/'source_pins.lef.gz'
    plan=json.load(gzip.open(plan_path));ii={a[0]:a for a in plan['insts']}
    pins=PA.read_pins([gzip.decompress(pp_path.read_bytes()).decode()])
    def pts(n,port):
        a=ii[n];it=types.SimpleNamespace(x=a[2],y=a[3],orient=a[6]);w,h,ps=pins[a[1]]
        return [PA.place(it,w,h,ps[f'{port}[{i}]']) for i in range(759)]
    old,prev,load,port=C['old'],C['prev'],'sp_gather',C['port']
    obs=[(a[0],a[2],a[3],a[4],a[5]) for a in plan['insts']]
    proposal=BT.propose(pts(prev,'dq'),pts(load,port),pts(old,'dq'),obs,old,ii[old][4],PA,side=C['side'],
                       hard_short=100.0 if C['side']=='E' else 0.0)
    assert proposal is not None
    if C['slices']:
        assert [(a['lo'],a['hi']) for a in proposal]==C['slices']
    # Exercise the exact generator rewire, not only a geometric suggestion.
    objects=[G.Inst(a[0],a[1],a[2],a[3],a[4],a[5],orient=a[6],kind=a[7],region=a[8]) for a in plan['insts']]
    it=next(i for i in objects if i.name==old)
    ib=('actual_in','local',759,[(prev,'dq'),(old,'di')])
    ob=('actual_out','local',759,[(old,'dq'),(load,port+'[0:758]')])
    cb=('actual_clock','clock',1,[('sp_collective','pll_stream'),(old,'ck')])
    m=dict(insts=objects,buses=[ib,ob,cb],pdir={},spread_stations={})
    new=BT.apply(G,m,it,proposal,ib,ob)
    assert len(m['insts'])==len(objects)+2
    assert all(n!=old for b in m['buses'] for n,_ in b[3])
    assert sum(b[2] for b in m['buses'] if b[0].startswith('actual_in_'))==759
    assert sum(b[2] for b in m['buses'] if b[0].startswith('actual_out_'))==759
    assert m['buses'][-1][3][1:]==[(n.name,'ck') for n in new]
    # Generate exact new per-bit physical pin rectangles, then read them back
    # through the same LEF parser used by the full die pin-align gate.
    G.FACE_PIN_INSET=.048
    lefs=[]
    for n,p in zip(new,proposal):
        mst=G.Q.Master(n.master,n.w,n.h,3,'Banded real register stage')
        G._faces_r8(m,mst,n,m['pdir'][n.master])
        lefs.append(G.lef_text(mst,1,{k:v[1] for k,v in m['pdir'][n.master].items()})[0])
    parsed=PA.read_pins(lefs);B=pts(load,port);A=pts(prev,'dq');Q=pts(old,'dq')
    checks=[]
    for n,p in zip(new,proposal):
        w,h,ps=parsed[n.master];count=p['hi']-p['lo']+1;sl=slice(p['lo'],p['hi']+1)
        Di=[PA.place(n,w,h,ps[f'di[{i}]']) for i in range(count)]
        Dq=[PA.place(n,w,h,ps[f'dq[{i}]']) for i in range(count)]
        pi,po=PA.bundle(A[sl],Di),PA.bundle(Dq,B[sl])
        assert pi['verdict']!='FAIL' and po['verdict']!='FAIL'
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1])<=450 for a,b in zip(A[sl],Di))
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1])<=max(abs(q[0]-b[0])+abs(q[1]-b[1]),100.0 if C['side']=='E' else 0.0)+1e-6
                   for a,b,q in zip(Dq,B[sl],Q[sl]))
        checks.append(dict(name=n.name,input=pi,output=po))
    report=dict(scope='Exact historical geometry rewire/pin proof; canonical2417 fullgeometry must be independently built',
        status='LOCAL_SEAM_GEOMETRY_PASS',input_plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        source_pins_sha256=hashlib.sha256(pp_path.read_bytes()).hexdigest(),proposal=proposal,
        checks=checks,instances_before=len(objects),instances_after=len(m['insts']),
        case=case,side=C['side'],state_bits_before=759,state_bits_after=759,cycles_added=0,
        clock_roots_added=len(proposal)-1,
        actual_RTL_equivalence='results/rtl/s81_hstn_split_1015 (5616edgePASS, middleband swapmutantFAIL)',
        qualification='No route/native clock/timing claim; actual new leaf views/phi-R/CTS/TT/FF/DRC remain OPEN')
    (out/'banded_geometry.json').write_text(json.dumps(report,indent=1)+'\n')
    (out/'new_station_pins.lef').write_text('\n'.join(lefs))
    print(json.dumps(dict(status=report['status'],case=case,groups=len(proposal),state_bits=759,cycles_added=0,
                         max_input_um=max(p['input_max_um'] for p in proposal),max_output_um=max(p['output_max_um'] for p in proposal))))
if __name__=='__main__':main(*sys.argv[1:])
