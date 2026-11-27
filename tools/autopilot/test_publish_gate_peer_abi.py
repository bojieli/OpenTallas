"""P-PEER-ABI wiring: publish_gate refuses a candidate whose cross-die pair mismatches the live peer."""
import json
import sys
import tempfile
from pathlib import Path

import publish_gate as PG

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_peer_abi as TP  # noqa: E402
import test_publish_gate as TG  # noqa: E402


def test_peer_abi_check_blocks_kv_against_live_qc(tmp_path):
    kvb, qcb = TP.kv(tmp_path), TP.qc(tmp_path)
    r = PG.peer_abi_check("/none", "/x/physical/die_plan/qwen_kvsys/p.json", kvb, {"qwen_compute": ("/none", qcb)}, tool_root=str(Path(PG.__file__).resolve().parents[2]))
    assert r["verdict"] == "FAIL" and "PEER-ABI-MISMATCH" in r["why"] and "QC-KV:status" in r["why"] and "change: KV" in r["why"]
    ok = PG.peer_abi_check("/none", "/x/physical/die_plan/qwen_kvsys/p.json", TP.kv(tmp_path, 1, "kv1"), {"qwen_compute": ("/none", qcb)}, tool_root=str(Path(PG.__file__).resolve().parents[2]))
    assert ok["verdict"] == "PASS"


def test_missing_guard_module_fails_closed_with_rt_and_advisory_without(tmp_path):
    assert PG.peer_abi_check("/none", "/x/die_plan/qwen_kvsys/p.json", None, {}, tool_root=str(tmp_path))["verdict"] == "FAIL"
    assert PG.peer_abi_check("/none", "/x/die_plan/qwen_kvsys/p.json", None, {})["verdict"] == "ADVISORY"


def _gate(tg, peer_verdict):
    tree, plan = TG.mk_tree(tg.td)

    def static(host, t, p, ab, ps):
        r = TG.hash_static(host, t, p, ab, ps)
        r["peer_abi"] = {"verdict": peer_verdict, "why": "PEER-ABI-MISMATCH: x"}
        return r
    return tree, plan, tg.gate(tree, plan, static=static)


def test_run_gate_verdict_and_apply_refuse_on_peer_abi_fail():
    tg = TG.Gate("test_good_tree_passes_and_applies")
    tg.setUp()
    tree, plan, rec = _gate(tg, "FAIL")
    assert rec["verdict"] == "FAIL" and "peer_abi" in rec["advisory"]
    why = PG.require_pass(tg.c, "kv", str(tree), TG.MANIFEST, TG.cand(tree, plan)["plan_sha256"])
    assert "peer_abi" in why
    tg2 = TG.Gate("test_good_tree_passes_and_applies")
    tg2.setUp()
    _t, _p, rec2 = _gate(tg2, "PASS")
    assert rec2["verdict"] == "PASS"


def test_run_gate_ships_live_peers_from_the_coord_config(monkeypatch):
    tg = TG.Gate("test_good_tree_passes_and_applies")
    tg.setUp()
    cfg = json.loads((tg.c / "autopilot/kit_wave.json").read_text())
    cfg["dies"]["qwen_compute"] = {"src": "/live/qc", "kit_rtl": {"bind_out": "/live/qc_bind"}}
    cfg["dies"]["kv"]["src"] = "/x/old"
    (tg.c / "autopilot/kit_wave.json").write_text(json.dumps(cfg))
    tree, plan = TG.mk_tree(tg.td)
    rec = tg.gate(tree, plan, static=TG.hash_static)
    assert rec["peer_abi_peers"] == {"qwen_compute": ["/live/qc", "/live/qc_bind"]}
