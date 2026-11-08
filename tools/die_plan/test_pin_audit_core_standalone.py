"""Core pin audit stays importable after staging under a shallow container mount."""
import runpy
import sys
import types
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / 'physical/die_plan/s81/cores/svc/pin_audit_core.py'


def staged(tmp_path, monkeypatch, subdir='work'):
    target = tmp_path / subdir / 'pin_audit.py'
    target.parent.mkdir(parents=True)
    target.write_text(SOURCE.read_text())
    monkeypatch.setitem(sys.modules, 'odb', types.ModuleType('odb'))
    monkeypatch.delitem(sys.modules, 'native_pin_contract', raising=False)
    monkeypatch.setattr(sys, 'path', [str(target.parent)])
    return target


def test_adjacent_helper(tmp_path, monkeypatch):
    target = staged(tmp_path, monkeypatch)
    (target.parent / 'native_pin_contract.py').write_text('def native_rects_match(*args): return "adjacent"\n')
    assert runpy.run_path(str(target))['native_rects_match']() == 'adjacent'


def test_repository_ancestor_helper(tmp_path, monkeypatch):
    target = staged(tmp_path, monkeypatch, 'repo/physical/die_plan/cores')
    helper = tmp_path / 'repo/tools/die_plan/native_pin_contract.py'
    helper.parent.mkdir(parents=True)
    helper.write_text('def native_rects_match(*args): return "repository"\n')
    assert runpy.run_path(str(target))['native_rects_match']() == 'repository'


def test_missing_helper_fails_closed(tmp_path, monkeypatch):
    target = staged(tmp_path, monkeypatch)
    with pytest.raises(ModuleNotFoundError, match='requires adjacent'):
        runpy.run_path(str(target))
