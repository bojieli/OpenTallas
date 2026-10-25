"""CLOCK-TRUNK closed-loop structured spine: equal stages, <=rmax legs, measured re-targeting converges."""
import importlib.util
import random
from pathlib import Path
import pytest

P=Path(__file__).resolve().parent/'shallow_clock.py'
spec=importlib.util.spec_from_file_location('shallow_clock_cl',P)
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)


def geometry(n=127,seed=1):
    rnd=random.Random(seed)
    # dense E/centre, sparse W strip (ROM-like): uneven tap density as in E5
    taps=[]
    for i in range(n):
        x=rnd.uniform(20000,380000) if i%5 else rnd.uniform(20000,90000)
        taps.append(dict(name=f'ot_dtap_{i}',xy=[int(x),int(rnd.uniform(20000,440000))]))
    return dict(dbu=1000,core=[4320,4320,406080,462240],root=[172809,19],root_name='ck',
                master='BUFx24',width=1620,height=270,
                rows=[[4320,4320+270*j,54,270,7440,'MX' if j%2 else 'R0'] for j in range(1696)],
                cells=[['rom',100000,100000,160000,300000,1]],taps=taps)


def simulate(p,wire=(0.12,0.0009),cell=15.0,ff=0.8,jitter=None):
    """Toy RC: stage delay = cell + a*L + b*L^2 (L um, 2-pin legs), FF = ff*TT."""
    u=p['dbu'];xy={n['name']:n['xy'] for n in p['nodes']}|{t['name']:t['xy'] for t in p['taps']}
    par={b:a for a,b in p['edges']};arr={}
    def at(nm):
        if nm in arr:return arr[nm]
        if nm not in par:
            L=S._man(xy[nm],p['root'])/u;arr[nm]=wire[0]*L+wire[1]*L*L;return arr[nm]
        a=par[nm];L=S._man(xy[a],xy[nm])/u
        j=jitter.get(nm,0) if jitter else 0
        arr[nm]=at(a)+cell+wire[0]*L+wire[1]*L*L+j;return arr[nm]
    tap={t['name']:(at(t['name']),ff*at(t['name'])) for t in p['taps']}
    buf={n['name']:(at(n['name']),ff*at(n['name'])) for n in p['nodes']}
    return tap,buf


def test_structure_equal_stages_short_legs_free_sites(tmp_path):
    g=geometry();p=S.plan_legs(g)
    S.validate(p)
    assert all(L['seg_um']<=100.0+1e-6 for L in p['legs'])
    assert p['summary']['added_cycles']==0
    for n in p['nodes']:
        x,y=n['ll'];assert (x-4320)%54==0 and (y-4320)%270==0
        assert not (x<160000 and x+1620>100000 and y<300000 and y+270>100000)
    # every tap owns a private last leg (2-pin into the tap input)
    last=[a for a,b in p['edges'] if b.startswith('ot_dtap_')]
    assert len(last)==len(set(last))==len(g['taps'])
    S.emit_apply(p,tmp_path/'a.tcl')
    assert (tmp_path/'a.tcl').read_text().count('ot_dtsh::leaf ')==len(g['taps'])


def test_detour_path_has_requested_length():
    core=[0,0,500000,500000]
    for A,C,T in [([0,0],[100000,20000],120000),([100000,100000],[150000,300000],400000),([10,10],[10,10],50000)]:
        poly=S.leg_path(A,C,T,core)
        assert abs(sum(S._man(a,b) for a,b in zip(poly,poly[1:]))-T)<2
        assert poly[0]==A and poly[-1]==C


def test_closed_loop_converges_under_measured_feedback(tmp_path):
    g=geometry();p=S.plan_legs(g)
    rnd=random.Random(7)
    jit={n['name']:rnd.uniform(-4,4) for n in p['nodes']}   # per-buffer load/placement error the model never sees
    first=None
    for it in range(12):
        tap,buf=simulate(p,jitter=jit)
        s=S.cl_step(p,tap,buf)
        first=first or s
        if max(s)<=20:break
        S.realize(p,g)
    assert first[0]>20, first
    assert max(s)<=20, p['iters']
    S.emit_moves(p,tmp_path/'m.tcl')
    t=(tmp_path/'m.tcl').read_text()
    assert t.startswith('#') and t.count('ot_dtsh::relocate ')==len(p['nodes'])


def test_cli_roundtrip(tmp_path):
    import json,subprocess,sys
    g=geometry(40)
    geo=tmp_path/'g.tsv'
    lines=['DBU\t1000','CORE\t'+'\t'.join(map(str,g['core'])),'ROOT\t172809\t19','ROOT_NAME\tck','MASTER\tBUFx24\t1620\t270']
    lines+=['ROW\t'+'\t'.join(map(str,r[:5]))+f'\t{r[5]}' for r in g['rows']]
    lines+=['TAP\t%s\t%d\t%d\tck\tot_dtap_net'%(t['name'],*t['xy']) for t in g['taps']]
    geo.write_text('\n'.join(lines)+'\n')
    out=tmp_path/'plan.json';ap=tmp_path/'a.tcl'
    r=subprocess.run([sys.executable,str(P),str(geo),'--out',str(out),'--apply',str(ap),'--closed-loop'],capture_output=True,text=True,check=True)
    assert json.loads(r.stdout)['mode']=='closed_loop'
    p=json.loads(out.read_text());p['reps']={int(k):v for k,v in p['reps'].items()}
    tap,buf=simulate(p)
    meas=tmp_path/'m.tsv'
    meas.write_text(''.join(f'T {k} {a} {b}\n' for k,(a,b) in tap.items())+''.join(f'B {k} {a} {b}\n' for k,(a,b) in buf.items()))
    r=subprocess.run([sys.executable,str(P),str(geo),'--out',str(out),'--apply',str(tmp_path/'mv.tcl'),'--cl-step',str(meas)],capture_output=True,text=True,check=True)
    j=json.loads(r.stdout);assert j['iter']==1 and 'tt_spread' in j
