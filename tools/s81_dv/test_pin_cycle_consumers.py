"""S81-PLAN-1: pin_cycle_consumers golden checks pass on a consistent toy plan and catch every +-1 / ignored-event mutant."""
import copy
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('pcc', Path(__file__).with_name('pin_cycle_consumers.py'))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def toy():
    lanes = {'dn_s_0S_L0': 5, 'up_s_0S_L0': 6, 'fi_E0_p1_r0r1': 2, 'fi_E1_p1_r0r1': 2, 'fi_E0_p1_r1r0': 2,
             'rt_E0_in_0': 30, 'xtier__s_3N_C__gunit': 23}
    pcd = {'dn_s_0S_L0': 3, 'up_s_0S_L0': 1, 'fi_E0_p1_r0r1': 9, 'fi_E1_p1_r0r1': 9, 'rt_E0_in_0': 2,
           'xtier__s_3N_C__gunit': 1}
    parts = [dict(name='a0', type='col_h9_r0__t1'), dict(name='a1', type='col_h9_r1__t1'),
             dict(name='b0', type='col_h9_r0__t2'), dict(name='b1', type='col_h9_r1__t2')]
    ports = [dict(id='p0', src=dict(part='a0'), dst=dict(part='a1')), dict(id='p1', src=dict(part='b0'), dst=dict(part='b1')),
             dict(id='p2', src=dict(part='a1'), dst=dict(part='a0'))]
    pl = [dict(id='fi_E0_p1_r0r1', ports=['p0']), dict(id='fi_E1_p1_r0r1', ports=['p1']),
          dict(id='fi_E0_p1_r1r0', ports=['p2'])]
    base = dict(partitions=parts, ports=ports, lanes=pl, latency=dict(lanes={k: dict(cycles=v) for k, v in lanes.items()}))
    plan = copy.deepcopy(base)
    for k, d in pcd.items():
        plan['latency']['lanes'][k]['cycles'] += d
    ev = dict(pin_cycle_deltas=pcd)
    G, _ = M.golden(base, ev)
    table = dict(plan_digest=M.plan_digest(plan), lanes={k: dict(cycles=v) for k, v in G.items()})
    bind = dict(buses=[dict(lane=k, bound_stages=v, plan_cycles=v) for k, v in G.items()])
    offs = dict(slices={'u_s_0S': dict(dn=[G['dn_s_0S_L0']], up=[G['up_s_0S_L0'] + 1])})
    routes = dict(leaves=[dict(slice='u_s_0S', leaf=0, local_command_edges=0, local_partial_edges=1)])
    return base, plan, ev, G, pcd, table, bind, offs, routes


def test_consistent_passes_and_mutants_fail():
    base, plan, ev, G, pcd, table, bind, offs, routes = toy()
    assert M.class_map(pcd)['verdict'] == 'PASS'
    assert M.check_plan(G, plan)['verdict'] == 'PASS'
    assert M.check_table(G, table, plan)['verdict'] == 'PASS'
    assert M.check_bind(G, bind, pcd)['verdict'] == 'PASS'
    assert M.check_leaf(G, offs, routes)['verdict'] == 'PASS'
    for lane in pcd:
        for d in (1, -1):
            p = copy.deepcopy(plan)
            p['latency']['lanes'][lane]['cycles'] += d
            assert M.check_plan(G, p)['first'][0]['lane'] == lane
            t = copy.deepcopy(table)
            t['lanes'][lane]['cycles'] += d
            assert M.check_table(G, t, plan)['verdict'] == 'FAIL'
            b = copy.deepcopy(bind)
            next(x for x in b['buses'] if x['lane'] == lane)['bound_stages'] += d
            assert M.check_bind(G, b, pcd)['verdict'] == 'FAIL'
    o = copy.deepcopy(offs)
    o['slices']['u_s_0S']['dn'][0] -= pcd['dn_s_0S_L0']        # leaf compiler ignores the event
    assert M.check_leaf(G, o, routes)['verdict'] == 'FAIL'
    assert M.check_table(G, dict(table, plan_digest='stale'), plan)['verdict'] == 'FAIL'


def test_frame_schedule():
    base, plan, ev, G, pcd, *_ = toy()
    good = dict(plan_consistency=[dict(link='frame_int r0->r1 (band port to band port)', rtl_asbuilt=[11]),
                                  dict(link='frame_int r1->r0 (band port to band port)', rtl_asbuilt=[2])])
    assert M.check_frame(plan, G, pcd, {'col_h9_x': good})['verdict'] == 'PASS'
    stale = copy.deepcopy(good)
    stale['plan_consistency'][0]['rtl_asbuilt'] = [2]               # as-built 2-flop seam, stations not traced
    r = M.check_frame(plan, G, pcd, {'col_h9_x': stale})
    assert r['verdict'] == 'FAIL' and 'r0->r1' in r['fails'][0]
    p = copy.deepcopy(plan)                                         # instances disagree: one schedule cannot carry it
    p['latency']['lanes']['fi_E1_p1_r0r1']['cycles'] += 1
    G2 = dict(G, fi_E1_p1_r0r1=G['fi_E1_p1_r0r1'] + 1)
    assert any('differ between frame instances' in f for f in M.check_frame(p, G2, pcd, {})['fails'])


def test_unmapped_class_fails():
    assert M.class_map({'zz_new_lane': 1})['verdict'] == 'FAIL'
