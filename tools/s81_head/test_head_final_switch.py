"""HEAD-PLAN-1: head_final_switch.py 3-way unit composition (clean apply, already applied, conflict, preservation)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('hfs', HERE / 'head_final_switch.py')
hfs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hfs)


def plan(**over):
    p = dict(schema='opentallas.die_plan.v1', note='n', clock={'a': {'x': 1, 'y': 2}}, reset={},
             partition_types={'t1': {'clock': {'k': 1}, 'contents': []}, 't2': {'clock': {'k': 2}}},
             partitions=[{'name': 'p1', 'type': 't1'}], ports=[], lanes=[], latency={'lanes': {}})
    p.update(over)
    return p


def test_units_cut_top_clock_deep():
    u = hfs.units(plan())
    assert ('top', 'clock', 'a', 'x') in u and ('tkey', 't1', 'clock') in u


def test_disjoint_events_compose_and_conflict_detected():
    base = plan()
    e1 = plan(); e1['partition_types']['t1']['clock'] = {'k': 9}
    e2 = plan(); e2['clock'] = {'a': {'x': 1, 'y': 5}}
    cur = json.loads(json.dumps(base))
    for ev in (e1, e2):
        for k, (va, vb) in hfs.delta(base, ev).items():
            assert hfs.same(hfs.get_unit(cur, k), va)
            hfs.set_unit(cur, k, vb)
    assert cur['partition_types']['t1']['clock'] == {'k': 9} and cur['clock']['a'] == {'x': 1, 'y': 5}
    # a third event built on an OLD value of the same unit is a conflict (composed value != its base value)
    e3_base = plan(); e3_base['partition_types']['t1']['clock'] = {'k': 3}
    e3 = plan(); e3['partition_types']['t1']['clock'] = {'k': 4}
    (k, (va, vb)), = hfs.delta(e3_base, e3).items()
    assert not hfs.same(hfs.get_unit(cur, k), va)


def test_cli_conflict_exit_3(tmp_path):
    base = plan(); ev_from = plan(); ev_from['partition_types']['t2']['clock'] = {'k': 7}
    ev_to = plan(); ev_to['partition_types']['t2']['clock'] = {'k': 8}
    for n, p in (('b', base), ('f', ev_from), ('t', ev_to)):
        (tmp_path / (n + '.json')).write_text(json.dumps(p))
    (tmp_path / 's.json').write_text('{}')
    spec_ = dict(base=dict(plan=str(tmp_path / 'b.json'), sidecar=str(tmp_path / 's.json')),
                 events=[dict(id='E', kind='diff', **{'from': str(tmp_path / 'f.json'), 'to': str(tmp_path / 't.json')})])
    (tmp_path / 'spec.json').write_text(json.dumps(spec_))
    r = subprocess.run([sys.executable, '-I', str(HERE / 'head_final_switch.py'), str(tmp_path / 'spec.json'),
                        str(tmp_path / 'out')], capture_output=True, text=True)
    assert r.returncode == 3 and 'CONFLICTS 1' in r.stdout
