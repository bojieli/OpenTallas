"""ABSPATH-1122 (FLOW-OPS-R2, COORD): absolute plan inputs outside the plan's tree are refused (missing) or warned (present,
live plans) and `localize` copies them into the plan tree."""
import json
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402


def mk(tmp_path, refs):
    tree = tmp_path / "srv" / "tree"
    (tree / "tools" / "die_plan").mkdir(parents=True)
    pd = tree / "physical" / "die_plan" / "s81_head" / "plan_of_record"
    pd.mkdir(parents=True)
    plan = pd / "plan_c.json"
    plan.write_text(json.dumps({"partition_types": {"hd": {"clock": {"sink_bins_file": refs[0]}}},
                                "provenance": {"plan": refs[-1]}, "x": [{"census": r} for r in refs[1:]]}))
    return tree, plan


def test_missing_outside_fails_present_outside_warns_until_cutoff(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "ABS_RE", __import__("re").compile(r"^/.*\.json$"))
    monkeypatch.delenv("OT_PLAN_ABSPATH", raising=False)
    snap = tmp_path / "snap"; snap.mkdir(); (snap / "b.json").write_text("{}")
    tree, plan = mk(tmp_path, [str(snap / "gone.json"), str(snap / "b.json"), str(tmp_path / "srv/tree/in.json")])
    (tree / "in.json").write_text("{}")
    f = G.abspath_findings(str(plan), today="2026-11-22")
    assert f[0].startswith("WARN ABSPATH-MISSING 1") and "gone.json" in f[0]                # live plans: warn only
    assert G.abspath_findings(str(plan), level="fail", today="2026-11-22")[0].startswith("FAIL ABSPATH-MISSING")
    assert f[1].startswith("WARN ABSPATH-OUTSIDE 1") and "b.json" in f[1] and "in.json" not in f[1]
    assert "localize --plan" in f[-1]
    g = G.abspath_findings(str(plan), today="2026-11-29")
    assert g[0].startswith("FAIL ABSPATH-MISSING") and g[1].startswith("FAIL ABSPATH-OUTSIDE")
    assert all(x.startswith("WARN") for x in G.abspath_findings(str(plan), level="warn", today="2026-11-29"))
    assert "provenance" not in " ".join(f)                                    # records are not inputs


def test_localize_copies_and_rewrites_tree_relative(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "ABS_RE", __import__("re").compile(r"^/.*\.json$"))
    snap = tmp_path / "snap"; snap.mkdir(); (snap / "bins.json").write_text('{"bins": []}')
    tree, plan = mk(tmp_path, [str(snap / "bins.json"), str(snap / "gone.json")])
    out = plan.with_name("plan_l.json")
    n, left = G.localize(str(plan), str(out))
    assert n == 1 and left == [str(snap / "gone.json")]
    d = json.loads(out.read_text())
    rel = d["partition_types"]["hd"]["clock"]["sink_bins_file"]
    assert rel.startswith("physical/die_plan/s81_head/plan_of_record/inputs/") and rel.endswith("_bins.json")
    assert (tree / rel).read_text() == '{"bins": []}'
    assert d["provenance"]["plan"] == str(snap / "gone.json")                  # records untouched
    assert G.abspath_findings(str(out), today="2026-11-29")[0].startswith("FAIL ABSPATH-MISSING 1")


def test_default_pattern_sees_srv_paths():
    assert G.abs_refs({"a": "/srv/opentallas-scratch2/claude/kw45/x.json", "note": "/srv/y", "b": "physical/x",
                       "tap_offset": {"proof": "/srv/opentallas-scratch2/claude/kv-clk-r2/runs/e9/proof"}}) == \
        [("/a", "/srv/opentallas-scratch2/claude/kw45/x.json")]
