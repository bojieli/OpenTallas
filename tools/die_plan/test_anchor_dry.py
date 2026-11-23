"""ANCHORDRY (RESET-ANCHOR-TAPGUARD-1123): anchored reset relay depths vs the base plan; the bind's resolve() dry-run."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import anchor_dry as AD  # noqa: E402
import plan_gate_pre as G  # noqa: E402
import reset_anchor as RA  # noqa: E402


def _tree(rows):
    return {"relays": [dict(q=q, depth=d, xy=list(xy)) for q, d, xy in rows]}


OLD = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_1", 2, (100, 0)), ("rst_rl_2", 2, (0, 100)), ("rst_rl_3", 3, (100, 100))])
NEW = _tree([("rst_rl_0", 1, (0, 0)), ("rst_rl_1", 1, (300, 0)), ("rst_rl_2", 2, (100, 0)),
             ("rst_rl_3", 2, (0, 100)), ("rst_rl_4", 3, (100, 104))])
NOPORT = lambda tree: set()  # noqa: E731


def _type(*names, tree=OLD):
    t = {"clock": {"landing_local_resets": [dict(name=f"l{i}", raw=n, xy_um=[1.0, 1.0], consumers=[f"u_c{i}"])
                                            for i, n in enumerate(names)]}}
    t["clock"][RA.KEY] = RA.record(t, tree, HERE, 50.0)
    return t


def _plan(**types):
    return {"partition_types": types}


def test_depth_move_vs_base_fails_and_same_depth_rename_passes():
    base = _plan(S=_type("rst_rl_1", "rst_rl_3"))
    # the S81 class: names of the renumbered tree anchored on it -- rst_rl_1 is depth 1 on NEW, base had depth 2 at that path
    bad = _plan(S=_type("rst_rl_1", "rst_rl_4", tree=NEW))
    f = AD.static_findings(bad, base)
    assert len(f) == 1 and f[0].startswith("FAIL ANCHORDRY S: 1 anchored")
    assert "clock/landing_local_resets/0/raw = rst_rl_1 anchored depth 1, base rst_rl_1 depth 2 (anchor)" in f[0]
    good = _plan(S=_type("rst_rl_2", "rst_rl_4", tree=NEW))          # re-picked by depth (landing_remap / --repick)
    assert AD.static_findings(good, base) == []
    assert AD.static_findings(base, base) == []


def test_base_collector_tree_and_own_snapshot_fallbacks():
    b = {"clock": {"landing_local_resets": [dict(name="l0", raw="rst_rl_1", xy_um=[1, 1], consumers=["u_c0"])],
                   "landing_contract": {"collector_tree": copy.deepcopy(OLD)}}}
    bad = _plan(S=_type("rst_rl_1", tree=NEW))
    assert AD.static_findings(bad, _plan(S=b))[0].startswith("FAIL ANCHORDRY S:")
    assert "(collector_tree)" in AD.static_findings(bad, _plan(S=b))[0]
    own = copy.deepcopy(bad)
    own["partition_types"]["S"]["clock"]["landing_contract"] = {"collector_tree": copy.deepcopy(OLD)}
    f = AD.static_findings(own, None)
    assert len(f) == 1 and f[0].startswith("WARN ANCHORDRY-ADVISORY S:")
    assert AD.static_findings(_plan(U={"clock": {}}), None) == []


def test_dry_rows_ok_remap_and_refusal():
    raw = _plan(A=_type("rst_rl_1", "rst_rl_3"), B=_type("rst_rl_3"))
    raw["partition_types"]["B"]["clock"][RA.KEY]["tol_um"] = 2.0       # rst_rl_3 moved 4 um on NEW
    rows = AD.dry_rows(str(HERE), raw, "plan.json", tree_fn=lambda tn: NEW, ported_fn=NOPORT)
    by = {r["type"]: r for r in rows}
    assert by["A"]["status"] == "OK" and [m["to"] for m in by["A"]["receipt"]["remaps"]] == ["rst_rl_2", "rst_rl_4"]
    assert by["B"]["status"] == "FAIL" and by["B"]["detail"][0]["nearest"] == "rst_rl_4"
    lines = AD.dry_findings(rows)
    assert all(x.startswith("WARN ANCHORDRY-ADVISORY") for x in lines) and len(lines) == 2
    assert raw["partition_types"]["A"]["clock"]["landing_local_resets"][0]["raw"] == "rst_rl_1"   # dry: plan untouched


def test_plan_gate_pre_check_anchordry(tmp_path):
    assert "ANCHORDRY" in G.CLASSES
    bp, pp = tmp_path / "base.json", tmp_path / "plan.json"
    bp.write_text(json.dumps(_plan(S=_type("rst_rl_1"))))
    pp.write_text(json.dumps(_plan(S=_type("rst_rl_1", tree=NEW))))
    f = G.check_anchordry(str(tmp_path), str(pp), base=str(bp))
    assert [x.split()[:3] for x in f] == [["FAIL", "ANCHORDRY", "S:"]]
    assert G.check_anchordry(str(tmp_path), str(pp), base=None) == []
    f = G.check_anchordry(str(tmp_path), str(bp), base=str(bp), solve=True, tree_fn=lambda tn: NEW,
                         ported_fn=NOPORT)
    assert f and all(x.startswith("WARN ANCHORDRY-ADVISORY S:") for x in f)       # re-pick at the same depth: advisory


def test_cli_exit_status(tmp_path, monkeypatch, capsys):
    bp, pp = tmp_path / "base.json", tmp_path / "plan.json"
    bp.write_text(json.dumps(_plan(S=_type("rst_rl_1"))))
    pp.write_text(json.dumps(_plan(S=_type("rst_rl_1", tree=NEW))))
    monkeypatch.setattr(AD, "dry_rows", lambda *a, **k: [])
    assert AD.main(["anchor_dry.py", str(tmp_path), str(pp), "--base", str(bp)]) == 1
    assert "ANCHOR_DRY types=0 fail=1" in capsys.readouterr().out
    assert AD.main(["anchor_dry.py", str(tmp_path), str(bp), "--base", str(bp)]) == 0
