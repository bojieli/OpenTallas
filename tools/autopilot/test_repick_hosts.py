import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW


def test_frozen_hosts_outside_the_current_gen_hosts_are_replaced(tmp_path):
    cfg = tmp_path / "kit_wave.json"
    cfg.write_text(json.dumps({"dies": {"kv": {"gen_hosts": ["epyc7", "epyc9"]}}}))
    sp = {"die": "kv", "hub": "intel2", "hosts": ["intel1", "intel2", "epyc7"], "place_prefer": ["intel1", "epyc7"], "roam_hosts": ["intel1", "epyc7"]}
    out = KW.repick_stage_hosts(sp, cfg)
    assert out["hosts"] == ["epyc7", "epyc9"] and out["place_prefer"] == ["epyc7"] and out["roam_hosts"] == ["epyc7"]
    assert sp["hosts"] == ["intel1", "intel2", "epyc7"]                       # the input is not mutated
    ok = {"die": "kv", "hub": "intel2", "hosts": ["epyc7"], "place_prefer": []}
    assert KW.repick_stage_hosts(ok, cfg) is ok
    assert KW.repick_stage_hosts(sp, tmp_path / "missing.json") is sp


def _cfg(tmp_path, hosts):
    cfg = tmp_path / "kit_wave.json"
    cfg.write_text(json.dumps({"dies": {"qwen_compute": {"gen_hosts": hosts}}}))
    return cfg


def test_private_pin_with_tree_is_kept(tmp_path, capsys):
    """KW-REPICK-PIN 11-24: QC-CB-PROBE pinned epyc11 (holds its private tree), gen_hosts lacked epyc11 -> place re-picked off the tree, rc=97 x4"""
    cfg = _cfg(tmp_path, ["intel1", "epyc8", "epyc2"])
    sp = {"die": "qwen_compute", "hub": "intel2", "private": {"lane": "QC-CB-PROBE"}, "src": "/srv/x/QC-CB-PROBE/cC/tree", "gen_host": "epyc11",
          "hosts": ["epyc11"], "place_prefer": ["epyc11"], "roam_hosts": ["epyc11"]}
    seen = []
    out = KW.repick_stage_hosts(sp, cfg, tree_state=lambda h, hub, src: seen.append((h, src)) or True)
    assert out is sp and out["hosts"] == ["epyc11"] and seen == [("epyc11", "/srv/x/QC-CB-PROBE/cC/tree")]
    assert "KW_HOSTS pin kept" in capsys.readouterr().out


def test_private_pin_repicked_when_tree_missing_or_host_down(tmp_path, capsys):
    cfg = _cfg(tmp_path, ["intel1", "epyc8"])
    base = {"die": "qwen_compute", "hub": "intel2", "private": {"lane": "L"}, "src": "/t", "gen_host": "epyc11",
            "hosts": ["epyc11"], "place_prefer": ["epyc11"], "roam_hosts": ["epyc11"]}
    for st, why in ((False, "tree missing"), (None, "host down")):
        out = KW.repick_stage_hosts(dict(base), cfg, tree_state=lambda h, hub, src, st=st: st)
        assert out["hosts"] == ["intel1", "epyc8"] and out["place_prefer"] == [] and out["roam_hosts"] == []
        assert "re-picked" in capsys.readouterr().out.replace("\n", " ") and True
    # mixed: one pinned host keeps its tree, one lacks it, the hub is dropped as before; the log names each reason
    sp = dict(base, hosts=["epyc11", "epyc10", "intel2"], place_prefer=["epyc10", "epyc11"], roam_hosts=["epyc10", "epyc11"])
    out = KW.repick_stage_hosts(sp, cfg, tree_state=lambda h, hub, src: h == "epyc11")
    assert out["hosts"] == ["epyc11", "intel1", "epyc8"] and out["place_prefer"] == ["epyc11"] and out["roam_hosts"] == ["epyc11"]
    txt = capsys.readouterr().out
    assert "epyc10 (tree missing)" in txt and "intel2 (hub)" in txt and "pin kept" in txt


def test_wave_spec_repick_unchanged_and_never_probes(tmp_path):
    cfg = _cfg(tmp_path, ["intel1"])
    sp = {"die": "qwen_compute", "hub": "intel2", "hosts": ["epyc11"], "place_prefer": [], "roam_hosts": []}
    out = KW.repick_stage_hosts(sp, cfg, tree_state=lambda *a: (_ for _ in ()).throw(AssertionError("probed a wave spec")))
    assert out["hosts"] == ["intel1"]


def test_pinned_tree_state_reads_probe_output():
    class R:
        def __init__(self, o): self.stdout = o
    assert KW.pinned_tree_state("epyc11", "intel2", "/t", run=lambda *a, **k: R("KW_TREE_YES\n")) is True
    assert KW.pinned_tree_state("epyc11", "intel2", "/t", run=lambda *a, **k: R("KW_TREE_NO\n")) is False
    assert KW.pinned_tree_state("epyc11", "intel2", "/t", run=lambda *a, **k: R("ssh: connect refused")) is None
    def boom(*a, **k): raise KW.subprocess.TimeoutExpired("ssh", 20)
    assert KW.pinned_tree_state("epyc11", "intel2", "/t", run=boom) is None
    assert KW.pinned_tree_state("epyc11", "intel2", "", run=boom) is False
