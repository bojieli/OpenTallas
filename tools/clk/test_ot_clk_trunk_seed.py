"""C-DIECLOCK-TRUNK-UNPINNED: a die clock regen seeds from the plan's clock.spine.tree_of_record by default (sha12-verified);
the from-scratch opt-out is explicit (eco: {base_tree: none, reason}); a bound-trunk plan with neither is refused; a plan
without a bound trunk builds from scratch as before."""
import hashlib
import json

import pytest

import ot_clk as O


def cfg(plan, **kw):
    c = dict(schema=O.SCHEMA_CFG, die="d", event={"name": "e"}, inputs={"plan": str(plan)},
             stack={"cell": "inv", "clock_rc": "ndr"}, top={"form": "link_htree", "rep_um": 150},
             region={"form": "none"}, residual={}, extra_argv=[])
    c.update(kw)
    return c


def sha12(b):
    return hashlib.sha256(b).hexdigest()[:12]


def write_plan(tmp_path, tor=True, trunk=True, bad=None):
    d = tmp_path / "plan"
    (d / "clk").mkdir(parents=True)
    files = {"tree_json": ("clk/tree.json", b'{"nodes": {}, "taps": []}\n'), "ctree_v": ("clk/ctree.v", b"module ctree;\nendmodule\n"),
             "spef_tt": ("clk/ctree_TT.spef", b"*SPEF\n")}
    sp = dict(layers=["M8", "M9"], root_um=[0, 0], topology="link_htree")
    if trunk:
        sp["trunk"] = dict(layer="M9", node_x_um=10.0, lane_x_um=11.0, riser_um=1.0)
    if tor:
        sp["tree_of_record"] = {}
        for k, (rel, body) in files.items():
            (d / rel).write_bytes(body)
            sp["tree_of_record"][k] = dict(path=rel, sha12=sha12(body) if k != bad else "0" * 12)
    p = d / "die_plan.json"
    p.write_text(json.dumps(dict(clock=dict(spine=sp))))
    return p


def test_default_seeds_from_tree_of_record(tmp_path):
    plan = write_plan(tmp_path)
    c, prov = O.resolve_eco(cfg(plan))
    assert prov["mode"] == "tree_of_record"
    assert c["eco"]["base_tree"] == str(plan.parent / "clk" / "tree.json")
    assert c["eco"]["plan_root"] == str(plan.parent.resolve())
    assert set(prov["files"]) == {"tree_json", "ctree_v", "spef_tt"}
    a = O.kit_argv(c, tmp_path / "out" / "kit")
    assert a[a.index("--tree-json") + 1] == str(tmp_path / "out" / "eco" / "tree_eco.json")
    ea = O.eco_argv(c, tmp_path / "out" / "kit", None, None, str(plan), "/t/die_plan/die_trial.py")
    assert ea[1] == str(plan.parent / "clk" / "tree.json")


def test_eco_options_without_base_tree_keep_options_and_seed(tmp_path):
    plan = write_plan(tmp_path)
    c, prov = O.resolve_eco(cfg(plan, eco=dict(resite_types=["hd_tile"]), extra_argv=["--plan-root", "/r"]))
    assert prov["mode"] == "tree_of_record" and c["eco"]["resite_types"] == ["hd_tile"]
    assert "plan_root" not in c["eco"]                    # the kit's --plan-root is the eco plan root
    c2, _ = O.resolve_eco(cfg(plan, eco=dict(base_tree="tree_of_record")))
    assert c2["eco"]["base_tree"].endswith("clk/tree.json")


def test_sha_mismatch_fails(tmp_path):
    for k in ("tree_json", "ctree_v", "spef_tt"):
        plan = write_plan(tmp_path / k, bad=k)
        with pytest.raises(O.ConfigError, match=f"{O.TRUNK_CLASS}.*{k}"):
            O.resolve_eco(cfg(plan))


def test_missing_file_fails(tmp_path):
    plan = write_plan(tmp_path)
    (plan.parent / "clk" / "ctree_TT.spef").unlink()
    with pytest.raises(O.ConfigError, match="spef_tt"):
        O.resolve_eco(cfg(plan))


def test_opt_out_needs_a_reason(tmp_path):
    plan = write_plan(tmp_path, tor=False)
    for e in (dict(base_tree="none"), dict(base_tree="none", reason=""), dict(base_tree="none", reason="  ")):
        with pytest.raises(O.ConfigError, match="reason"):
            O.resolve_eco(cfg(plan, eco=e))
    with pytest.raises(O.ConfigError):
        O.resolve_eco(cfg(plan, eco=dict(base_tree="none", reason="x", resite_types=["t"])))
    c, prov = O.resolve_eco(cfg(plan, eco=dict(base_tree="none", reason="tile re-form, not an ECO")))
    assert prov == dict(mode="opt_out", reason="tile re-form, not an ECO") and "eco" not in c
    assert "--tree-json" not in O.kit_argv(c, tmp_path / "kit")


def test_bound_trunk_without_tree_of_record_is_refused(tmp_path):
    plan = write_plan(tmp_path, tor=False)
    with pytest.raises(O.ConfigError, match=O.TRUNK_CLASS):
        O.resolve_eco(cfg(plan))


def test_plan_without_bound_trunk_builds_from_scratch(tmp_path):
    plan = write_plan(tmp_path, tor=False, trunk=False)
    c, prov = O.resolve_eco(cfg(plan))
    assert prov["mode"] == "scratch" and "eco" not in c
    with pytest.raises(O.ConfigError, match=O.TRUNK_CLASS):       # asked for the tree of record, the plan has none
        O.resolve_eco(cfg(plan, eco=dict(resite_types=["t"])))


def test_explicit_base_tree_and_missing_plan_pass_through(tmp_path):
    plan = write_plan(tmp_path, tor=False)
    c0 = cfg(plan, eco=dict(base_tree="/b/tree.json"))
    c, prov = O.resolve_eco(c0)
    assert c is c0 and prov["mode"] == "config"
    c1 = cfg(tmp_path / "gone.json")
    c, prov = O.resolve_eco(c1)
    assert c is c1 and prov["mode"] == "unchecked"
    with pytest.raises(O.ConfigError):
        O.resolve_eco(cfg(plan, eco=dict(base_tree="/b", reason="x")))


def test_argv_command_seeds_also_under_legacy(tmp_path, capsys):
    plan = write_plan(tmp_path)
    y = tmp_path / "c.yaml"
    y.write_text(f"schema: {O.SCHEMA_CFG}\ndie: d\nevent:\n  name: e\ninputs:\n  plan: {plan}\nstack:\n  cell: inv\n"
                 f"top:\n  form: link_htree\n  rep_um: 150\n")
    for extra in ([], ["--legacy"]):
        assert O.main(["argv", str(y), "--out", str(tmp_path / "o")] + extra) == 0
        out = json.loads(capsys.readouterr().out)
        assert "--tree-json" in out["argv"] and out["trunk_seed"]["mode"] == "tree_of_record"


def test_opt_out_config_renders_from_scratch_under_legacy(tmp_path, capsys):
    plan = write_plan(tmp_path, tor=False)
    y = tmp_path / "c.yaml"
    y.write_text(f"schema: {O.SCHEMA_CFG}\ndie: d\nevent:\n  name: e\ninputs:\n  plan: {plan}\nstack:\n  cell: inv\n"
                 f"top:\n  form: link_htree\n  rep_um: 150\neco:\n  base_tree: none\n  reason: \"tile re-form\"\n")
    assert O.main(["argv", str(y), "--out", str(tmp_path / "o"), "--legacy"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "--tree-json" not in out["argv"] and out["trunk_seed"]["mode"] == "opt_out"


def test_explicit_tree_json_in_extra_argv_passes_through(tmp_path):
    for tor in (True, False):
        plan = write_plan(tmp_path / str(tor), tor=tor)
        c0 = cfg(plan, extra_argv=["--tree-json", "/s/stamped.json"])
        c, prov = O.resolve_eco(c0)
        assert c is c0 and prov["mode"] == "explicit_tree_json"
        assert O.kit_argv(c, tmp_path / "kit").count("--tree-json") == 1


def test_eco_argv_passes_every_plan_root(tmp_path):
    plan = write_plan(tmp_path)
    c, _ = O.resolve_eco(cfg(plan, inputs={"plan": str(plan), "plan_root": ["/r1", "/r2"]}))
    ea = O.eco_argv(c, tmp_path / "kit", None, None, str(plan), "/t/die_plan/die_trial.py")
    assert [ea[k + 1] for k, x in enumerate(ea) if x == "--plan-root"] == ["/r1", "/r2"]
