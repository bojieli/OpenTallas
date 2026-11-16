import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tree_smoke_assert as T  # noqa: E402


def mk(tmp, scales, keep=True, wired=True):
    d = tmp / "tools" / "die_plan"
    d.mkdir(parents=True)
    (d / "tt_setup_repair.tcl").write_text("x")
    if keep:
        (d / "tt_setup_keep.py").write_text("x")
    (d / "gen_phys.py").write_text(("import tt_setup_keep\nSERDES_PIPE_CHAINS = {\"OT_S81_SERDES_RXNEG\": (\"u_rxf\",)}\n") if wired else "pass\n")
    (d / "rc_signal_scales.json").write_text(json.dumps(scales))
    return tmp


GOOD = {"type": {"s81": 1.0, "qwen_compute": 1.25, "s81_head": 1.13, "qwen_kvsys": 1.1}, "core": 1.1}


def test_current_tree_passes(tmp_path):
    assert T.check(mk(tmp_path, GOOD)) == []


def test_stale_trees_fail_with_named_reason(tmp_path):
    old = {"type": {"s81": 1.0, "qwen_compute": 1.25}, "core": 1.1}               # the four trees of 11-16
    probs = T.check(mk(tmp_path, old, keep=False, wired=False))
    txt = "\n".join(probs)
    assert "tt_setup_keep.py" in txt and "does not reference tt_setup_keep" in txt
    assert "no type entry for s81_head" in txt and "no type entry for qwen_kvsys" in txt
    assert T.main([str(tmp_path)]) == 1


def test_wrong_scale_fails(tmp_path):
    bad = {"type": dict(GOOD["type"], s81_head=1.0), "core": 1.1}
    assert any("s81_head = x1, expect x1.13" in p for p in T.check(mk(tmp_path, bad)))


def test_s81_tree_without_txpipe_hook_fails(tmp_path):
    t = mk(tmp_path, GOOD)
    (t / "tools/die_plan/gen_phys.py").write_text("import tt_setup_keep\n")          # keep wired, drop the hook
    probs = T.check(t, ["s81"])
    assert any("TXPIPE hook" in p for p in probs)
    assert not any("TXPIPE" in p for p in T.check(t, ["s81_head"]))                  # only S81 serdes needs it
