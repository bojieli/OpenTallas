import importlib.util
from pathlib import Path

import pytest


P = Path(__file__).resolve().parents[1] / 'physical/die_plan/qwen_kvsys/cores/harden/pin_audit_core.py'
spec = importlib.util.spec_from_file_location('kv_core_pin_audit', P)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_interior_clock_shape_and_wrong_axis_controls():
    pin = dict(face='interior', x=302.4, y=220.32)
    box = (302.376, 220.08, 302.424, 220.56)
    assert audit.box_ok(pin, box, 604.8, 440.64)
    assert not audit.box_ok(pin, tuple(v + .01 if i % 2 else v for i, v in enumerate(box)), 604.8, 440.64)
    assert not audit.box_ok(pin, tuple(v + .01 if not i % 2 else v for i, v in enumerate(box)), 604.8, 440.64)


def test_interior_requires_whole_box_inside_die():
    assert not audit.box_ok(dict(face='interior', x=0, y=1), (-.024, .76, .024, 1.24), 10, 10)


def test_legacy_face_still_requires_die_edge():
    pin = dict(face='W', x=0, y=1)
    assert audit.box_ok(pin, (0, .76, .048, 1.24), 10, 10)
    assert not audit.box_ok(pin, (.1, .76, .148, 1.24), 10, 10)


def test_unknown_face_fails_closed():
    with pytest.raises(KeyError):
        audit.box_ok(dict(face='interoir', x=1, y=1), (.976, .76, 1.024, 1.24), 10, 10)
