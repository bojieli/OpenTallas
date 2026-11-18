"""WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1700 item 2): hold release terms tree_has:<rNNN> / tree_has_sha:<sha> are true only when the die's current tree tools contain the fix."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import hold_records as HR
import kit_wave as KW

CFG = {"dies": {"s81": {"enabled": True, "src_sha": "main@" + "a" * 40}}}


def met(term, has):
    ctx = HR.Ctx(tree_has_fn=lambda die, tok: has.get((die, tok), False))
    return HR.term_met(term, {}, "s81", "item", CFG, ctx)


def test_terms_are_typed_system_checks_and_validated():
    assert "tree_has" in HR.TYPED and "tree_has_sha" in HR.TYPED and "tree_has" in HR.SYSTEM_CHECKS
    assert HR.term_error("tree_has:r620", "s81", CFG) is None
    assert HR.term_error("tree_has:620", "s81", CFG) and HR.term_error("tree_has:r12", "s81", CFG)
    assert HR.term_error("tree_has_sha:8750c256f56c", "s81", CFG) is None and HR.term_error("tree_has_sha:xyz", "s81", CFG)


def test_term_is_true_only_when_the_tree_has_it():
    assert met("tree_has:r620", {("s81", "r620"): True}) is True
    assert met("tree_has:r620", {}) is False                                       # the default (and an unreadable repo) holds
    assert met("tree_has_sha:8750c256f56c", {("s81", "8750c256f56c"): True}) is True
    assert met("tree_has:r620", {("s81", "r623"): True}) is False


def test_the_wave_context_asks_tools_lag(monkeypatch):
    """hold_ctx wires tree_has_fn to tools_lag ancestry against the die's tools base; any error means False"""
    import types
    import tools_lag as TL
    seen = []
    monkeypatch.setattr(TL, "pin_of", lambda d: d.get("pin") or "")
    monkeypatch.setattr(TL, "tree_has", lambda repo, pin, token, main_ref="main", **k: (seen.append((pin, token)) or token == "r1"))
    orig = KW._ilu.module_from_spec
    monkeypatch.setattr(KW._ilu, "module_from_spec", lambda spec: TL if getattr(spec, "name", "") == "tools_lag" else orig(spec))
    monkeypatch.setattr(KW._ilu, "spec_from_file_location", lambda name, path: types.SimpleNamespace(name=name, loader=types.SimpleNamespace(exec_module=lambda m: None)) if name == "tools_lag" else None)
    cfg = {"dies": {"s81": {"pin": "abc1234"}, "hbm": {}}}
    assert KW.tree_has_term(cfg, "s81", "r1") is True and seen == [("abc1234", "r1")]
    assert KW.tree_has_term(cfg, "s81", "r2") is False
    assert KW.tree_has_term(cfg, "hbm", "r1") is False                             # no pin known for the die: the hold stays
    assert KW.tree_has_term(cfg, "nodie", "r1") is False
