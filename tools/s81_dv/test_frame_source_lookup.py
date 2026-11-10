"""S81-PLAN-1 11-10: frame masters and landed-schedule source hashes resolve under the FRAME source root."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[1] / 'die_plan'),
                str(Path(__file__).resolve().parent / 'layer_prog')]

import frame_bench as FB
import frame_return_plan as FRP

SRC = 'm/col_hz.sv'


def _root(tmp_path):
    r = tmp_path / 'froot'
    (r / 'm').mkdir(parents=True)
    (r / SRC).write_text('module col_hz_l4_lp_asb_x(input a);\nendmodule\n')
    (r / 'man.json').write_text(json.dumps(dict(base='.', files=[SRC])))
    return r


def test_frame_master_from_frame_manifest(tmp_path, monkeypatch):
    r = _root(tmp_path)
    monkeypatch.delenv('OT_S81_SELECTED_ASBUILT_MANIFEST', raising=False)
    monkeypatch.setenv('OT_S81_FRAME_SOURCE_ROOT', str(r))
    monkeypatch.setenv('OT_S81_FRAME_ASBUILT_MANIFEST', 'man.json')
    path, body = FB.frame_module_source('col_hz_l4_lp_asb_x')
    assert Path(path).resolve() == (r / SRC).resolve() and 'input a' in body


def test_frame_master_without_frame_manifest_unchanged(monkeypatch):
    for k in ('OT_S81_FRAME_ASBUILT_MANIFEST', 'OT_S81_FRAME_SOURCE_ROOT', 'OT_S81_SELECTED_ASBUILT_MANIFEST'):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(ValueError, match='no selected definition and no canonical wrapper'):
        FB.frame_module_source('col_hz_l4_lp_asb_x')


def _phase(sched):
    return FRP.plan_phase('col_hz', [], None, None, 1, frame_schedule=str(sched), land_e=None)


def test_landed_schedule_hashes_frame_root(tmp_path, monkeypatch):
    """the hash check reads schedule sources under OT_S81_FRAME_SOURCE_ROOT, and still refuses a changed byte"""
    r = _root(tmp_path)
    sched = tmp_path / 's.json'
    sched.write_text(json.dumps(dict(source_sha256={SRC: hashlib.sha256((r / SRC).read_bytes()).hexdigest()})))
    monkeypatch.setenv('OT_S81_FRAME_SOURCE_ROOT', str(r))
    monkeypatch.setattr(FRP, 'load_topology', lambda m: {})
    monkeypatch.setattr(FRP, 'emission', lambda m: ({}, 0))
    monkeypatch.setattr(FRP, 'x_shift', lambda e: 0)
    with pytest.raises(AssertionError, match='landed frame schedule requires'):   # hash check passed
        _phase(sched)
    (r / SRC).write_text('module col_hz_l4_lp_asb_x(input b);\nendmodule\n')
    with pytest.raises(AssertionError, match='stale landed schedule'):
        _phase(sched)
