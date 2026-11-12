"""SEAM-HOP-1: G0 collector_reach (the bind's reverse-collector reach rule on the plan alone) + path_respace chain re-siting."""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import collector_reach as CR  # noqa: E402
import path_respace as PR  # noqa: E402


def _type(far=543.8):
    relays = [dict(q="rst_rl_0", d="rst_root_n", xy=[100.0, 0.0], depth=1),
              dict(q="rst_rl_1", d="rst_rl_0", xy=[100.0 + far, 0.0], depth=2),
              dict(q="rst_rl_2", d="rst_rl_0", xy=[300.0, 0.0], depth=2)]
    return dict(outline_um=[1500.0, 400.0], clock=dict(landing_contract=dict(
        collector_tree=dict(root=[0.0, 0.0], relays=relays),
        collector_local_sources=[dict(name="s", tap=1, node="rst_rl_1", xy_um=[100.0 + far, 0.0])],
        collector_children=[])))


def test_rule_matches_bind():
    rows = CR.type_findings("t", _type(543.8))
    assert [(r["kind"], r["src"], r["dst"], r["hop_um"]) for r in rows] == [("edge", "rst_rl_1", "rst_rl_0", 543.8)]
    assert CR.type_findings("t", _type(405.0)) == []              # exactly the limit is legal
    t = _type(543.8)
    t["clock"]["landing_contract"]["collector_local_sources"][0]["node"] = "rst_rl_2"   # the long edge is inactive
    assert CR.type_findings("t", t) == []


def test_g0_check_is_an_error_and_nothing_else_changes():
    class R:
        def __init__(self): self.items = []
        def err(self, c, m, **k): self.items.append(("ERROR", c, m))
    class P:
        raw = dict(partition_types={"t": _type()})
    r = R()
    s = CR.check_collector_reach(P, r)
    assert s["edges_over"] == 1 and r.items and r.items[0][:2] == ("ERROR", "collector_reach") and "543.800um exceeds 405" in r.items[0][2]
    assert hasattr(check, "run")


def test_path_respace_resites_relays_same_count():
    raw = dict(partition_types={"t": _type()})

    class Stub:
        types = raw["partition_types"]
    ops = []
    rows = PR.respace_collectors(raw, ops, 405.0, P2=Stub())
    assert len(rows) == 1 and rows[0]["status"] == "fixed" and rows[0]["worst_after"] <= 405.0
    assert len(raw["partition_types"]["t"]["clock"]["landing_contract"]["collector_tree"]["relays"]) == 3
    assert ops and all(o[1] == "set" and o[0][-1] == "xy" for o in ops)
    assert CR.type_findings("t", raw["partition_types"]["t"]) == []
