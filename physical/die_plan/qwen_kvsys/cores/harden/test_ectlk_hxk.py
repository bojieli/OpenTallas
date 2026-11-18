"""KV-KT-E0 11-18: the ECTLK HXK parameter (ectlk_hxk.py) -- committed sources agree at 13, --set rewrites all six."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _mod():
    s = importlib.util.spec_from_file_location("ectlk_hxk", HERE / "ectlk_hxk.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_committed_sources_agree_at_the_views_of_record():
    m = _mod()
    v = m.values()
    assert set(v) == set(m.MODS) | {"CORE_HXK"}
    assert m.one(v) == 13        # the signed q0..q3 views; 15 only in the event that adopts re-hardened views


def test_rewrite_moves_every_default_and_the_guard():
    m = _mod()
    cols, wrap = m.rewrite(m.COLS.read_text(), m.WRAP.read_text(), 15)
    assert m.one(m.values(cols, wrap)) == 15
    back = m.rewrite(cols, wrap, 13)
    assert back == (m.COLS.read_text(), m.WRAP.read_text())


def test_a_partial_edit_fails_closed():
    m = _mod()
    cols = m.COLS.read_text().replace("parameter integer HXK = 13) (", "parameter integer HXK = 15) (", 1)
    try:
        m.one(m.values(cols, m.WRAP.read_text()))
    except ValueError as e:
        assert "disagree" in str(e)
    else:
        raise AssertionError("mixed HXK defaults accepted")
