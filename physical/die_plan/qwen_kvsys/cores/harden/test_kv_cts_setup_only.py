"""KV-KITS-13: gen_core_kit_kv --cts-setup-only (SIGNOFF-MODES-2 one timing mode per corner, HBM-CORES-R11 form):
no hold repair in the single-mode tc+bc CTS step, setup-only repair chained after the effective POST_CTS hook."""
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location("gk", Path(__file__).with_name("gen_core_kit_kv.py"))
gk = importlib.util.module_from_spec(spec); spec.loader.exec_module(gk)


def test_chains_effective_post_cts_and_skips_cts_repair(tmp_path):
    cfg = ["export POST_CTS_TCL = /work/leaf_affinity.tcl", "export CORNERS = tc bc"]
    r = gk.cts_setup_only(tmp_path, cfg)
    assert r["previous_post_cts"] == "/work/leaf_affinity.tcl"
    assert "export SKIP_CTS_REPAIR_TIMING = 1" in cfg
    assert gk._effective_hook(cfg, "POST_CTS_TCL") == "/work/post_cts_setup.tcl"
    t = (tmp_path / "post_cts_setup.tcl").read_text()
    assert t.count("source {/work/leaf_affinity.tcl}") == 1
    assert t.index("source {/work/leaf_affinity.tcl}") < t.index("repair_timing_helper -setup")
    body = [l for l in t.splitlines() if not l.lstrip().startswith("#")]
    assert not any("repair_timing" in l and "-setup" not in l for l in body)   # never a hold repair


def test_override_hook_wins_and_no_prev(tmp_path):
    cfg = ["export POST_CTS_TCL = /work/a.tcl", "override export POST_CTS_TCL = /work/b.tcl", "export POST_CTS_TCL = /work/c.tcl"]
    assert gk._effective_hook(cfg, "POST_CTS_TCL") == "/work/b.tcl"
    cfg2 = []
    r = gk.cts_setup_only(tmp_path, cfg2)
    assert r["previous_post_cts"] is None and "source {" not in (tmp_path / "post_cts_setup.tcl").read_text()
