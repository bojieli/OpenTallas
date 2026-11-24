"""LANDREMAP-RSTNODE (11-23, FABLE-RC-KV): landing_remap also takes the tap reset nodes rst_n_t<i> that a landing_raw_branches
final names, by site + kind (OLD site, + the type's outline growth), and rebuilds every all-tree raw branch from its final over
the NEW D links.  Shapes from the KV A3 +112.32 um grow: kv3_hroot finals rst_n_t11 -> rst_n_t12 (the grow renumbered the
taps), kv3_io_ft_v1 chains whose final kept its name while two relays were inserted upstream (rst_rl_53 -> rst_rl_55)."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_remap as LR  # noqa: E402

GROW = 112.32


def _r(q, d, xy, kind="wire"):
    return dict(q=q, d=d, xy=list(xy), kind=kind)


# OLD (pre-grow) tree: root rst_rl_1 -> rst_rl_2 -> tap nodes rst_n_t11 @ (500, 100), rst_n_t12 @ (900, 100)
OLD_T = {"relays": [_r("rst_rl_1", None, (0, 0)), _r("rst_rl_2", "rst_rl_1", (300, 100)),
                    _r("rst_n_t11", "rst_rl_2", (500, 100), "tap"), _r("rst_n_t12", "rst_rl_2", (900, 100), "tap")]}
# NEW (grown east by GROW): a tap inserted west renumbers; the old t11 site (east of the cut, + GROW) is now rst_n_t12
NEW_T = {"relays": [_r("rst_rl_1", None, (0, 0)), _r("rst_rl_2", "rst_rl_1", (300, 100)),
                    _r("rst_n_t11", "rst_rl_2", (200, 100), "tap"), _r("rst_n_t12", "rst_rl_2", (500 + GROW, 100), "tap"),
                    _r("rst_n_t13", "rst_rl_2", (900 + GROW, 100), "tap")]}


def _type(final, base="rst_rl_1", mid="rst_rl_2", w=1000.0, n=2):
    brs = [{"name": f"fs_{i}", "base": base, "stages": [{"original": mid, "xy_um": [300, 100]},
                                                         {"original": final, "xy_um": [500, 100]}]} for i in range(n)]
    brs.append({"name": "ring", "base": "rst_rl_2", "stages": [{"original": "cland_reset_ft0_i"}]})
    return {"outline_um": [w, 400.0], "clock": {"landing_raw_branches": brs}}


def _plans(old_t, new_t):
    return {"partition_types": {"T": old_t}}, {"partition_types": {"T": new_t}}


def _run(old, new, otree=OLD_T, ntree=NEW_T, **kw):
    kw.setdefault("resets", "rstnode")
    return LR.remap_plan(old, new, HERE, HERE, adopt=False, tree_fn=lambda raw, tn: otree if raw is old else ntree, **kw)


def _brs(p, tn="T"):
    return p["partition_types"][tn]["clock"]["landing_raw_branches"]


def test_grow_renames_stale_final_by_old_site_plus_growth():
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t11", w=1000 + GROW))
    rec = _run(old, new)
    assert [b["stages"][-1]["original"] for b in _brs(new)[:2]] == ["rst_n_t12", "rst_n_t12"]
    assert _brs(new)[2]["stages"][0]["original"] == "cland_reset_ft0_i"          # landing-side relay never touched
    assert rec["rstnodes"] == [dict(type="T", renames={"rst_n_t11": "rst_n_t12"}, finals_renamed=2, chains=[])]
    assert rec["rstnode_unresolved"] == []


def test_inserted_upstream_relays_rebuild_the_chain_from_its_final():
    nt = {"relays": OLD_T["relays"][:2] + [_r("rst_rl_3", "rst_rl_2", (350, 100)), _r("rst_n_t11", "rst_rl_3", (500, 100), "tap")]}
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t11"))
    rec = _run(old, new, ntree=nt)
    b = _brs(new)[0]
    assert b["base"] == "rst_rl_2" and [s["original"] for s in b["stages"]] == ["rst_rl_3", "rst_n_t11"]
    assert b["stages"][0]["xy_um"] == [300, 100]                                  # stage sites kept
    assert rec["rstnodes"][0]["finals_renamed"] == 0 and len(rec["rstnodes"][0]["chains"]) == 2


def test_no_grow_plan_is_unchanged():
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t11"))
    before = copy.deepcopy(new)
    rec = _run(old, new, ntree=OLD_T)
    assert new == before and rec["rstnodes"] == [] and rec["rstnode_unresolved"] == []


def test_name_already_renamed_since_old_is_kept():
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t12", w=1000 + GROW))
    rec = _run(old, new)
    assert [b["stages"][-1]["original"] for b in _brs(new)[:2]] == ["rst_n_t12", "rst_n_t12"] and rec["rstnodes"] == []


def test_rename_is_per_branch_not_per_name():
    # branch 1 was deliberately repointed to t11 since OLD (OLD had t12 there): only branch 0 is stale
    ot, nt = _type("rst_n_t11"), _type("rst_n_t11", w=1000 + GROW)
    ot["clock"]["landing_raw_branches"][1]["stages"][-1]["original"] = "rst_n_t12"
    old, new = _plans(ot, nt)
    _run(old, new)
    assert [b["stages"][-1]["original"] for b in _brs(new)[:2]] == ["rst_n_t12", "rst_n_t11"]


def test_no_unique_node_at_old_site_is_listed_unresolved_not_fatal():
    nt = {"relays": NEW_T["relays"][:2] + [_r("rst_n_t11", "rst_rl_2", (200, 100), "tap")]}
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t11", w=1000 + GROW))
    rec = _run(old, new, ntree=nt)
    assert [(u["type"], u["name"], u["candidates"]) for u in rec["rstnode_unresolved"]] == [("T", "rst_n_t11", [])]
    assert _brs(new)[0]["stages"][-1]["original"] == "rst_n_t11"


def test_kind_must_match():
    nt = copy.deepcopy(NEW_T)
    nt["relays"][3]["kind"] = "pad"
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t11", w=1000 + GROW))
    rec = _run(old, new, ntree=nt)
    assert rec["rstnode_unresolved"] and _brs(new)[0]["stages"][-1]["original"] == "rst_n_t11"


def test_old_identity_from_stored_collector_tree_first():
    ot = _type("rst_n_t11")
    ot["clock"]["landing_contract"] = {"collector_tree": OLD_T}
    old, new = _plans(ot, _type("rst_n_t11", w=1000 + GROW))
    calls = []

    def tf(raw, tn):
        calls.append(raw is old)
        return NEW_T
    LR.remap_plan(old, new, HERE, HERE, adopt=False, resets="rstnode", tree_fn=tf)
    assert calls == [False] and _brs(new)[0]["stages"][-1]["original"] == "rst_n_t12"


def test_r8_clone_uses_its_base_type():
    old = {"partition_types": {"T": _type("rst_n_t11")}}
    new = {"partition_types": {"T__r8deadbeef": _type("rst_n_t11", w=1000 + GROW)}}
    rec = LR.remap_plan(old, new, HERE, HERE, adopt=False, resets="rstnode", tree_fn=lambda raw, tn: OLD_T if raw is old else NEW_T)
    assert _brs(new, "T__r8deadbeef")[0]["stages"][-1]["original"] == "rst_n_t12" and rec["rstnodes"][0]["type"] == "T__r8deadbeef"


def test_resel_mode_walks_up_from_the_renamed_final():
    seen = {}

    def resel(old_raw, new_raw, names, plan_dir):
        seen["final"] = _brs(old_raw)[0]["stages"][-1]["original"]      # reset_resel reads the OLD final
        return {"T": dict(exports=[], raw=[], skipped=[], kept=[])}
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t11", w=1000 + GROW))
    rec = _run(old, new, resets="resel", resel_fn=resel, keep_xy=False, ident_fn=lambda raw, tn: {})
    assert seen["final"] == "rst_n_t12" and _brs(old)[0]["stages"][-1]["original"] == "rst_n_t11"   # OLD itself untouched
    assert _brs(new)[0]["stages"][-1]["original"] == "rst_n_t12" and rec["rstnodes"][0]["finals_renamed"] == 2


@pytest.mark.parametrize("mode", ["identity", "anchor"])
def test_every_mode_ends_with_the_reset_node_pass(mode):
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t11", w=1000 + GROW))
    _run(old, new, resets=mode, ident_fn=lambda raw, tn: {}, ported_fn=lambda tree: set(), tol_um=1.0)
    assert _brs(new)[0]["stages"][-1]["original"] == "rst_n_t12"


def test_cli_prints_reset_node_summary(monkeypatch, tmp_path, capsys):
    old, new = _plans(_type("rst_n_t11"), _type("rst_n_t11", w=1000 + GROW))
    (tmp_path / "old.json").write_text(json.dumps(old))
    (tmp_path / "new.json").write_text(json.dumps(new))
    real = LR.remap_plan
    monkeypatch.setattr(LR, "remap_plan", lambda o, n, *a, **k: real(
        o, n, *a, **dict(k, tree_fn=lambda raw, tn: OLD_T if raw is o else NEW_T)))
    assert LR.main(["x", str(tmp_path / "old.json"), str(tmp_path / "new.json"), str(tmp_path / "out.json"), "--resets", "rstnode",
                    "--receipt", str(tmp_path / "r.json")]) == 0
    out = capsys.readouterr().out
    assert "2 final(s) renamed" in out and "rstnode T: finals renamed 2" in out
    assert _brs(json.loads((tmp_path / "out.json").read_text()))[0]["stages"][-1]["original"] == "rst_n_t12"
