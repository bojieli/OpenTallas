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
    assert all(L['seg_um']<=1.2*100.0 for L in p['legs'])  # legal-site snap may stretch a hop slightly
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


def test_depth0_terminal_clusters_hold_leaf_fanout_taps():
    """CLOCK-RESET S1: legacy start level 1 leaves fanout*leaf_fanout tap legs on a terminal
    cluster (8 for 4/2 on 127 taps); depth0 caps every cluster net at max(fanout, leaf_fanout) legs."""
    g=geometry()
    def max_legs(p): return max(len(c['legs']) for c in p['clusters'])
    legacy=S.plan_legs(g,fanout=4,leaf_fanout=2,rmax_um=120)
    fixed=S.plan_legs(g,fanout=4,leaf_fanout=2,rmax_um=120,depth0=True)
    assert max_legs(legacy)==8
    assert max_legs(fixed)<=4
    term=[c for c in fixed['clusters'] if any(fixed['legs'][i]['child'][0]=='tap' for i in c['legs'])]
    assert term and all(len(c['legs'])<=2 for c in term)
    assert sorted(t for c in term for t in c['taps'])==sorted(t['name'] for t in g['taps'])
    # one more bisection level: equal stage count kept, honest insertion cost (+1 level of legs)
    assert legacy['summary']['trunk_levels']<fixed['summary']['trunk_levels']<=legacy['summary']['trunk_levels']+2
    assert S.plan_legs(g,fanout=4,leaf_fanout=2,rmax_um=120)['summary']==legacy['summary']   # default unchanged


def test_island_compact_leg_starts():
    """CLOCK-RESET S1b: with island_um every cluster's leg-start buffers sit in one compact island
    (max pairwise <= island span) on free sites, even where the cluster point is crowded."""
    g=geometry()
    # crowd the region around every tap: a row-filling cell band 30 um wide around each tap row
    for t in g['taps'][:40]:
        x,y=t['xy'];g['cells'].append([f"crowd_{t['name']}",x-15000,y-3000,x+15000,y+3000,0])
    p=S.plan_legs(g,depth0=True,island_um=10.0)
    S.validate(p)
    starts={}
    for L in p['legs']:
        if L['parent'] is not None: starts.setdefault(L['parent'],[]).append(L['bufs'][0])
    xy={n['name']:n['xy'] for n in p['nodes']}
    span=lambda names:max(S._man(xy[a],xy[b]) for a in names for b in names)/1000
    assert max(span(v) for v in starts.values())<=10.0+1e-6
    # no two planned buffers overlap, none on the crowd cells
    ll=[tuple(n['ll']) for n in p['nodes']];assert len(ll)==len(set(ll))


def test_compensation_cap_survives_feedback():
    g=geometry(20)
    p=S.plan_legs(g,leg_extra_um=15.0)
    assert max(L['xmax'] for L in p['legs']) <= 15000
    for _ in range(4):
        tap,buf=simulate(p)
        # Deliberately large unmatched local-tree delay must remain a reported
        # residual; the controller cannot absorb it into unlimited trunk wire.
        for nm in list(tap)[:4]:
            a,b=tap[nm];tap[nm]=(a+190,b+150)
        S.cl_step(p,tap,buf)
        assert all(0<=L['x']<=15000 for L in p['legs'])
        S.realize(p,g)
    assert p['summary']['added_cycles']==0


@pytest.mark.parametrize('bad',[-1.0,float('nan'),float('inf')])
def test_compensation_cap_rejects_invalid(bad):
    with pytest.raises(ValueError,match='leg_extra_um'):
        S.plan_legs(geometry(5),leg_extra_um=bad)


def test_spatial_2d_split_keeps_points_and_avoids_long_slabs():
    pts=[dict(name=f'{x}_{y}',xy=[x,y]) for x in range(4) for y in range(4)]
    new=S.split_spatial_2d(pts);old=S.split(pts,4)
    names=lambda gs: sorted(p['name'] for g in gs for p in g)
    span=lambda g: sum(max(p['xy'][i] for p in g)-min(p['xy'][i] for p in g) for i in (0,1))
    assert names(new)==names(old)==names([pts])
    assert [len(g) for g in new]==[4,4,4,4]
    assert max(map(span,new)) < max(map(span,old))


def test_macro_corridors_keep_clock_wires_off_blocked_rectangles():
    g=geometry(20)
    p=S.plan_legs(g,avoid_macros=True)
    for q in p['wire_paths'].values():
        for a,b in zip(q,q[1:]):
            assert a[0]==b[0] or a[1]==b[1]
            for x0,y0,x1,y1 in p['obstacles']:
                if a[1]==b[1]:
                    assert not (y0<a[1]<y1 and min(a[0],b[0])<x1 and max(a[0],b[0])>x0)
                else:
                    assert not (x0<a[0]<x1 and min(a[1],b[1])<y1 and max(a[1],b[1])>y0)
    assert {t['name'] for t in p['taps']}=={t['name']for t in g['taps']}
    assert all(L['xmax']==0 for L in p['legs'])
    assert p['summary']['added_cycles']==0


def test_even_sampling_edge_adds_only_common_input_stage():
    g=geometry(20);g['master']='INVx13_ASAP7_75t_R'
    p=S.plan_legs(g,even_stages=True)
    pars={b:a for a,b in p['edges']};counts=[]
    for t in p['taps']:
        count=0;name=t['name']
        while name in pars:
            name=pars[name];count+=1
        counts.append(count)
    assert len(set(counts))==1
    assert counts[0]%2==0
    assert p['summary']['trunk_levels']%2==0
    assert p['summary']['added_cycles']==0
