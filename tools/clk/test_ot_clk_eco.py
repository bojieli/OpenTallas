"""CLK-ECO-1: an ot_clk config with an eco section renders die_trial kit --tree-json on OUT/eco/tree_eco.json and the
tree_eco argv from the config (plan root from the kit's --plan-root, region map, stage cal, resite types)."""
import pytest
import ot_clk as O


def cfg(**eco):
    return dict(schema=O.SCHEMA_CFG, die="d", event={"name": "e"}, inputs={"plan": "/p/plan.json"},
                stack={"cell": "inv", "clock_rc": "ndr"}, top={"form": "link_htree", "rep_um": 150},
                region={"form": "none"}, residual={}, extra_argv=["--plan-root", "/p/root"],
                **({"eco": eco} if eco else {}))


def test_kit_argv_adds_tree_json_only_with_eco(tmp_path):
    a0 = O.kit_argv(cfg(), tmp_path / "kit")
    assert "--tree-json" not in a0
    a1 = O.kit_argv(cfg(base_tree="/b/tree.json"), tmp_path / "kit")
    assert a1[a1.index("--tree-json") + 1] == str(tmp_path / "eco" / "tree_eco.json")


def test_eco_argv_from_config(tmp_path):
    c = cfg(base_tree="/b/tree.json", resite_types=["hd_x"], max_leaf_leg_um=2, lift_tol_ps=1)
    a = O.eco_argv(c, tmp_path / "kit", "/k/cal.json", "/r/reg.json", "/p/plan.json", "/t/die_plan/die_trial.py")
    assert a[1:3] == ["/b/tree.json", "/p/plan.json"]
    assert a[a.index("--plan-root") + 1] == "/p/root" and a[a.index("--tools") + 1] == "/t/die_plan"
    assert a[a.index("--resite-types") + 1] == "hd_x" and a[a.index("--stage-cal") + 1] == "/k/cal.json"
    assert a[a.index("--regions") + 1] == "/r/reg.json"


def test_eco_rejects_unknown_keys_and_double_tree(tmp_path):
    with pytest.raises(O.ConfigError):
        O.eco_argv(cfg(base_tree="/b", bogus=1), tmp_path / "kit", None, None, "/p", "/t/die_trial.py")
    c = cfg(base_tree="/b")
    c["extra_argv"] += ["--tree-json", "/x.json"]
    with pytest.raises(O.ConfigError):
        O.kit_argv(c, tmp_path / "kit")


def test_eco_calib_and_balance_argv(tmp_path):
    c = cfg(base_tree="/b/tree.json", calib="/run/eco3", balance_types=["hd_x", "hd_y"], balance_ps=20)
    a = O.eco_argv(c, tmp_path / "kit", None, None, "/p/plan.json", "/t/die_plan/die_trial.py")
    assert a[a.index("--calib") + 1] == "/run/eco3" and a[a.index("--balance-types") + 1] == "hd_x,hd_y"
    assert a[a.index("--balance-ps") + 1] == "20"
    with pytest.raises(O.ConfigError):            # balancing needs a routed run to measure on
        O.eco_argv(cfg(base_tree="/b", balance_types=["hd_x"]), tmp_path / "kit", None, None, "/p", "/t/die_trial.py")
