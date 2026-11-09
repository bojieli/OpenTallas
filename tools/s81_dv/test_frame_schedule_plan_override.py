"""S81-SVC-9: the frame_int plan check reads the plan named by OT_S81_FRAME_PLAN (relay events move fi_* cycles)."""
import json
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1] / 'die_plan')]

import frame_schedule_asb as F


def plan(cycles):
    return dict(partitions=[dict(name='a', type='col_h9_r0_p2__t1__x'), dict(name='b', type='col_h9_r1__t1__y')],
                ports=[dict(id='p', src=dict(part='a'), dst=dict(part='b'))],
                lanes=[dict(id='fi_W0_p2_r0r1', ports=['p'])],
                latency=dict(lanes=dict(fi_W0_p2_r0r1=dict(cycles=cycles))))


def test_plan_override_is_used(tmp_path, monkeypatch):
    p = tmp_path / 'p.json'
    p.write_text(json.dumps(plan(11)))
    monkeypatch.setenv('OT_S81_FRAME_PLAN', str(p))
    assert F.plan_lanes('col_h9') == {('r0', 'r1'): [11]}


def test_default_stays_die_plan(tmp_path, monkeypatch):
    monkeypatch.delenv('OT_S81_FRAME_PLAN', raising=False)
    (tmp_path / 'physical/die_plan/s81').mkdir(parents=True)
    (tmp_path / 'physical/die_plan/s81/die_plan.json').write_text(json.dumps(plan(2)))
    monkeypatch.setattr(F, 'ROOT', tmp_path)
    assert F.plan_lanes('col_h9') == {('r0', 'r1'): [2]}
