"""CLK-TOOL-1 tests for tools/clk/ot_clk.py (P0 config -> die_trial argv, P1 fail-closed stage-model registry)."""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ot_clk as O  # noqa: E402

CONFIGS = sorted((HERE / "configs").glob("*.yaml"))
DIES = {p.stem for p in CONFIGS}


def cfg(name):
    return O.load_config(HERE / "configs" / f"{name}.yaml")


def reg():
    return O.load_registry()


def flags(argv):
    """argv -> {flag: value or True} (die_trial kit: every flag at most once except --tree-opt)"""
    out, i = {}, 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            nxt = argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else True
            if a == "--tree-opt":
                out.setdefault(a, []).append(nxt)
            else:
                out[a] = nxt
            i += 1 if nxt is True else 2
        else:
            i += 1
    return out


def test_all_five_dies_have_a_config():
    assert {"qc", "s81", "kv", "hbm", "head"} <= DIES


@pytest.mark.parametrize("path", CONFIGS, ids=lambda p: p.stem)
def test_mini_yaml_matches_pyyaml(path):
    mini = O.mini_yaml(path.read_text())
    assert mini["schema"] == O.SCHEMA_CFG
    yaml = pytest.importorskip("yaml")
    assert mini == yaml.safe_load(path.read_text())


def test_brace_expansion_bash_order():
    assert O.brace("c_{E,W}{0..1}_x") == ["c_E0_x", "c_E1_x", "c_W0_x", "c_W1_x"]
    assert len(O.brace("c_{E,W}{0..5}_{bf,bn,tf,tn}_{00,01,10,11}")) == 192


def test_no_die_names_in_tool_code():
    src = (HERE / "ot_clk.py").read_text().lower()
    assert not re.search(r"\b(qwen|qc|s81|hbm|kv|head)\b", src.split('"""', 2)[2])


# ------------------------------------------------------------------------------------------------- P0: argv per die
def test_qc_argv_reproduces_trial14_flags():
    f = flags(O.kit_argv(cfg("qc"), "OUT", "CAL", None))
    assert f["--tree-form"] == "link_htree" and f["--rep-um"] == "250" and f["--leaf-um"] == "200"
    assert f["--clock-cell"] == "inv2" and f["--region-dme"] == "delay"
    assert f["--region-dme-early"] == "1" and f["--region-dme-early-ff"] == "0.87"
    assert f["--region-dme-stage-cal"] == "CAL" and f["--region-dme-workers"] == "24"
    assert sorted(f["--tree-opt"]) == ["dme_feed_centroid=1", "region_stub=1"]
    only = f["--region-dme-only"].split(",")
    assert len(only) == 204 and only[0] == "c_E0_bf_00" and only[192] == "sl_E0_su_c"
    assert len(f["--region-dme-early-merge-only"].split(",")) == 192
    assert len(f["--region-dme-snake"].split(",")) == 204
    assert "--region-dme-early-mode" not in f and "--clock-rc" not in f


def test_s81_argv_reproduces_go15_flags(tmp_path):
    c = cfg("s81")
    m = tmp_path / "map.json"
    m.write_text(json.dumps({"part_region": {"p1": "rB", "p2": "rA", "p3": "rB"}}))
    c["inputs"]["region_map"] = str(m)
    f = flags(O.kit_argv(c, "OUT"))
    assert f["--region-dme-only"] == "rA,rB"
    assert f["--region-dme-early"] == "1.78" and f["--region-dme-early-ff"] == "1.53"
    assert f["--region-dme-early-mode"] == "merge" and f["--region-dme-snake"] == "all"
    assert f["--cell-paths"] is True and f["--tree-opt"] == ["dme_feed_centroid=1"]
    assert "--region-dme-stage-cal" not in f        # go15 ran on die_trial's built-in BUFx24 model


def test_kv_hbm_head_argv():
    kv = flags(O.kit_argv(cfg("kv"), "OUT"))
    assert kv["--clock-cell"] == "inv" and kv["--rep-um"] == "150" and kv["--tap-pad"].endswith("pad_it2.json")
    assert "--region-dme" not in kv
    hbm = flags(O.kit_argv(cfg("hbm"), "OUT"))
    assert hbm["--clock-cell"] == "inv2" and hbm["--tree-form"] == "link_htree" and hbm["--rep-um"] == "250"
    head = flags(O.kit_argv(cfg("head"), "OUT"))
    assert head["--tree-form"] == "spine_fishbone" and head["--rep-um"] == "200" and head["--tree-site-slide"]
    assert "--tree-site-legal" not in head and "--feed" not in head


# ------------------------------------------------------------------------------------- P1: fail-closed stage model
def test_registry_coefficients_are_untampered():
    for e in reg().values():
        assert e["coeff_sha"] == O.coeff_sha(e), e["id"]


def test_qc_stage_check_passes_and_writes_the_same_cal():
    ok, e, why = O.stage_check(cfg("qc"), reg())
    assert ok, why
    src = json.loads((HERE.parent.parent / "results/die_qc21_1028/inv2_stage_cal_trial13b.json").read_text())
    d = O.stage_cal_file(e)
    for k in ("leg", "tap", "leg_FF", "tap_FF"):
        assert d[k] == src[k]


def test_geometric_forms_need_no_stage_model():
    for d in ("kv", "hbm", "head"):
        assert O.stage_check(cfg(d), reg())[0]


def test_s81_go15_without_cal_is_rejected():
    ok, _, why = O.stage_check(cfg("s81"), reg())
    assert not ok and "no implicit default" in why[0]


def test_mutant_stale_bufx24_model_on_inv2_tree_is_rejected():
    """DIE-S81-17: the BUFx24 1x ladder model priced an inv2 tree (wire 0.014 vs fitted 0.162 ps/um)."""
    c = cfg("s81")
    c["stage_model"] = {"entry": "builtin_bufx24_1x_ladder"}
    ok, _, why = O.stage_check(c, reg())
    assert not ok
    assert any("cell=CKINVDCx16_ASAP7_75t_R" in w and "BUFx24" in w for w in why)


def test_s81_with_its_routed_inv2_fit_passes():
    c = cfg("s81")
    c["stage_model"] = {"entry": "inv2_ndr_s81_go15", "corners": ["TT", "FF"]}
    ok, e, why = O.stage_check(c, reg())
    assert ok, why
    assert e["leg"][1] == pytest.approx(0.161722)


def test_wrong_polarity_rc_corner_and_tamper_are_rejected():
    r = reg()
    c = cfg("qc")
    c2 = copy.deepcopy(c)
    c2["stack"]["cell"] = "inv"                     # single inverters: polarity inv, not pair
    assert not O.stage_check(c2, r)[0]
    c3 = copy.deepcopy(c)
    c3["stack"]["clock_rc"] = "1x"
    assert not O.stage_check(c3, r)[0]
    c4 = copy.deepcopy(c)
    c4["stage_model"]["edge"] = "fall"
    assert not O.stage_check(c4, r)[0]
    b = copy.deepcopy(cfg("s81"))
    b["stack"]["cell"] = "buf"
    b["stage_model"] = {"entry": "builtin_bufx24_1x_ladder", "corners": ["TT", "FF"]}
    assert not O.stage_check(b, r)[0]               # built-in model has no FF fit
    r2 = copy.deepcopy(r)
    r2["inv2_ndr_qc_trial13b"]["leg"][1] = 0.014
    assert not O.stage_check(c, r2)[0]
    c5 = copy.deepcopy(c)
    c5["stage_model"]["coeff_sha"] = "0" * 16
    assert not O.stage_check(c5, r)[0]
    c6 = copy.deepcopy(c)
    c6["stage_model"]["entry"] = "nope"
    assert not O.stage_check(c6, r)[0]


def test_kit_refuses_to_run_die_trial_on_a_failed_check(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(O.subprocess, "call", lambda *a, **k: called.append(a) or 0)
    with pytest.raises(SystemExit) as ex:
        O.main(["kit", str(HERE / "configs" / "s81.yaml"), "--out", str(tmp_path / "o")])
    assert "STAGE MODEL CHECK FAIL" in str(ex.value) and not called


def test_kit_passes_registry_cal_to_die_trial(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(O.subprocess, "call", lambda cmd, **k: seen.append(cmd) or 0)
    assert O.main(["kit", str(HERE / "configs" / "qc.yaml"), "--out", str(tmp_path / "o")]) == 0
    f = flags(seen[0][2:])
    cal = json.loads(Path(f["--region-dme-stage-cal"]).read_text())
    assert cal["leg"] == reg()["inv2_ndr_qc_trial13b"]["leg"]
    rec = json.loads((tmp_path / "o" / "ot_clk_argv.json").read_text())
    assert rec["stage_check"] == "PASS"


def test_legacy_argv_reports_fail_but_renders(tmp_path, capsys):
    c = tmp_path / "s81.yaml"
    m = tmp_path / "map.json"
    m.write_text(json.dumps({"part_region": {"p": "r"}}))
    c.write_text((HERE / "configs" / "s81.yaml").read_text().replace(
        cfg("s81")["inputs"]["region_map"], str(m)))
    assert O.main(["argv", str(c), "--legacy"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["stage_check"] == "FAIL" and "--region-dme-stage-cal" not in out["argv"]


def test_json_diff_keys_names_meta_only_differences():
    a = {"meta": {"x": 1, "clock_cell": "inv2"}, "nodes": [1, 2]}
    b = {"meta": {"x": 1}, "nodes": [1, 2]}
    assert O.json_diff_keys(a, b) == ["meta.clock_cell"]
    assert O.json_diff_keys({"nodes": [1]}, {"nodes": [2]}) == ["nodes"]


def test_s81_go16_draft_passes_with_the_routed_s81_fit():
    ok, e, why = O.stage_check(cfg("s81_go16"), reg())
    assert ok and e["id"] == "inv2_ndr_s81_go15", why


def _rebase_cfg(tmp_path, pins_file, sidecar=False):
    pd = tmp_path / "ev"
    pd.mkdir()
    plan = {"partition_types": {"t": {"hard_cores": [{"inst": "u", "pins_file": pins_file}]}}}
    (pd / "plan.json").write_text(json.dumps(plan))
    if sidecar:
        (pd / "die_io.json").write_text("[]")
    c = cfg("head")
    c["inputs"] = dict(plan=str(pd / "plan.json"),
                       pins_rebase={"from": "../../wt/gone-bind/", "to_repo": ""})
    return c


def test_pins_rebase_points_a_deleted_worktree_plan_at_repo_pin_tables(tmp_path):
    rel = "physical/die_plan/s81_head/cores/elemA_pins.json"
    c = _rebase_cfg(tmp_path, "../../wt/gone-bind/" + rel)
    plan, prov = O.rebase_plan(c, tmp_path / "out")
    p = json.loads(Path(plan).read_text())
    got = p["partition_types"]["t"]["hard_cores"][0]["pins_file"]
    assert Path(got) == (O.REPO / rel).resolve() and Path(got).is_file()
    assert prov["pins_files"]["../../wt/gone-bind/" + rel]["repo_path"] == rel
    assert O.kit_argv(c, tmp_path / "out" / "kit", plan=plan)[1] == plan


def test_pins_rebase_refuses_missing_foreign_or_sidecar(tmp_path):
    for i, (pf, side) in enumerate((("../../wt/gone-bind/physical/no_such_pins.json", False),
                                    ("../../wt/other/physical/die_plan/s81_head/cores/elemA_pins.json", False),
                                    ("../../wt/gone-bind/../../../../etc/passwd", False),
                                    ("../../wt/gone-bind/physical/die_plan/s81_head/cores/elemA_pins.json", True))):
        d = tmp_path / str(i)
        d.mkdir()
        with pytest.raises(O.ConfigError):
            O.rebase_plan(_rebase_cfg(d, pf, side), d / "out")


def test_configs_without_rebase_pass_the_plan_through(tmp_path):
    c = cfg("kv")
    assert O.rebase_plan(c, tmp_path) == (c["inputs"]["plan"], None)

def test_reference_prefers_generated_copy(tmp_path):
    (tmp_path / "tree.json").write_text("{}")
    assert O.reference_file(tmp_path, "tree.json").name == "tree.json"
    (tmp_path / "tree_GENERATED.json").write_text("{}")
    assert O.reference_file(tmp_path, "tree.json").name == "tree_GENERATED.json"


# ---------------------------------------------------------------------------- P2: QC clock of record (CLK-TOOL-3)
def test_qc_trial25_argv_matches_kit25_flags():
    """DIE-QC-25 kit25.sh t25: trial14 flags + ev_qc25 + trial24 refit cal + --rep-on-leg + --rep-off-leg-max 50"""
    c = cfg("qc_trial25")
    f = flags(O.kit_argv(c, "OUT", "CAL", None))
    t14 = flags(O.kit_argv(cfg("qc"), "OUT", "CAL", None))
    assert f["--rep-on-leg"] is True and f["--rep-off-leg-max"] == "50"
    assert "--rep-on-leg" not in t14 and "--rep-off-leg-max" not in t14
    assert {k: v for k, v in f.items() if not k.startswith("--rep-o")} == t14
    ok, e, why = O.stage_check(c, reg())
    assert ok, why
    src = json.loads((HERE.parent.parent / "results/die_qc25_1028/inv2_stage_cal_trial24.json").read_text()) \
        if (HERE.parent.parent / "results/die_qc25_1028/inv2_stage_cal_trial24.json").is_file() else None
    d = O.stage_cal_file(e)
    assert d["leg"] == [13.934059, 0.09766, 0.000161, 10.457359]
    assert d["leg_FF"] == [11.782508, 0.086044, 0.00015, 7.743809]
    if src is not None:
        for k in ("leg", "tap", "leg_FF", "tap_FF"):
            assert d[k] == src[k]


def test_kit_runs_the_named_die_trial_and_records_it(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(O.subprocess, "call", lambda cmd, **k: seen.append(cmd) or 0)
    dt = tmp_path / "die_plan" / "die_trial.py"
    dt.parent.mkdir()
    dt.write_text("# stand-in\n")
    assert O.main(["kit", str(HERE / "configs" / "qc_trial25.yaml"), "--out", str(tmp_path / "o"),
                   "--die-trial", str(dt)]) == 0
    assert seen[0][1] == str(dt.resolve())
    rec = json.loads((tmp_path / "o" / "ot_clk_argv.json").read_text())["die_trial"]
    assert rec["path"] == str(dt.resolve()) and len(rec["sha256"]) == 16


def test_builtin_ladder_rejects_ndr_and_accepts_its_measured_wire_stack():
    # The built-in coefficients were fitted on 1x wires. A BUFx24 NDR
    # request used to pass because the registry accidentally labelled them NDR.
    c = cfg("s81")
    c["stack"]["cell"] = "buf"
    c["stage_model"] = {"entry": "builtin_bufx24_1x_ladder"}
    ok, _, why = O.stage_check(c, reg())
    assert not ok and any("clock_rc=ndr" in x and "clock_rc=1x" in x for x in why)
    c["stack"]["clock_rc"] = "1x"
    assert O.stage_check(c, reg())[0]


def test_reach_keys_map_to_die_trial_flags_and_default_off():
    # CLK-TOOL-4: global FEED reach is a generic config key of every die (no die name in the tool)
    c = cfg("hbm")
    base = O.kit_argv(c, "OUT")
    assert "--rep-reach-max" not in base and "--rep-actual-max" not in base
    c["top"]["rep_reach_max"] = 450
    c["top"]["rep_actual_max"] = 450.0
    f = flags(O.kit_argv(c, "OUT"))
    assert f["--rep-reach-max"] == "450" and f["--rep-actual-max"] == "450"


def _replay_dirs(tmp_path, new_meta, ref_meta, cell="CKINVDCx16_ASAP7_75t_R", ref_cell=None):
    out, ref = tmp_path / "o", tmp_path / "ref"
    (out / "kit" / "clock").mkdir(parents=True)
    ref.mkdir()
    for d, meta, c in ((out / "kit" / "clock", new_meta, cell), (ref, ref_meta, ref_cell or cell)):
        (d / "tree.json").write_text(json.dumps({"meta": meta, "nodes": [1, 2]}))
        (d / "ctree.v").write_text(f"module ctree (root);\n  {c} n0 (.A(root), .Y(t0));\nendmodule\n")
    c = {"die": "x", "event": {"name": "e", "reference_clock_dir": str(ref)}}
    return c, out


def test_replay_schema_added_clock_cell_is_meta_only_when_ctree_agrees(tmp_path):
    c, out = _replay_dirs(tmp_path, {"v": 1, "clock_cell": "inv2"}, {"v": 1})
    v = O.compare_replay(c, "cfg", out, True, [], None)
    assert v["replay"] == "IDENTICAL_EXCEPT_META"
    t = v["files"]["tree.json"]
    assert t["meta_added"] == ["meta.clock_cell"] and t["clock_cell_check"]["consistent"]


def test_replay_mutant_clock_cell_contradicting_ctree_is_different(tmp_path):
    c, out = _replay_dirs(tmp_path, {"v": 1, "clock_cell": "buf"}, {"v": 1})     # ctree has CKINV, meta says buf
    assert O.compare_replay(c, "cfg", out, True, [], None)["replay"] == "DIFFERENT"


def test_replay_changed_ctree_is_different_even_if_meta_only_in_tree(tmp_path):
    c, out = _replay_dirs(tmp_path, {"v": 1, "clock_cell": "buf"}, {"v": 1}, cell="BUFx24_ASAP7_75t_R",
                          ref_cell="CKINVDCx16_ASAP7_75t_R")
    assert O.compare_replay(c, "cfg", out, True, [], None)["replay"] == "DIFFERENT"


def test_replay_compare_only_does_not_run_die_trial(tmp_path, monkeypatch):
    monkeypatch.setattr(O.subprocess, "call", lambda *a, **k: pytest.fail("die_trial must not run"))
    assert O.main(["replay", str(HERE / "configs" / "qc_trial25.yaml"), "--out", str(tmp_path / "o"),
                   "--compare-only"]) == 2          # no kit/clock dir -> refused, nothing run


def test_region_actual_max_maps_to_die_trial_flag_and_default_off():
    c = cfg("s81_go16")
    c["region"]["only"] = None
    assert "--region-dme-actual-max" not in O.kit_argv(c, "OUT")
    c["region"]["actual_max"] = 405.0
    assert flags(O.kit_argv(c, "OUT"))["--region-dme-actual-max"] == "405"


def test_refit_registers_a_per_stack_entry_the_config_then_accepts(tmp_path):
    sys.path.insert(0, str(HERE.parent / "die_plan"))
    import test_fit_dme_stage_cal as TF
    tp, pre = TF._tree_and_arr(tmp_path)
    rp = tmp_path / "reg.json"
    rp.write_text(O.REGISTRY.read_text())
    argv = ["refit", str(HERE / "configs" / "s81_go16.yaml"), "--registry", str(rp), "--tree", str(tp),
            "--arr-prefix", str(pre), "--id", "inv2_ndr_refit_test", "--tap", "0.042", "5e-6",
            "-o", str(tmp_path / "cal.json"), "--write"]
    assert O.main(argv) == 0
    e = [x for x in json.loads(rp.read_text())["entries"] if x["id"] == "inv2_ndr_refit_test"][0]
    assert e["key"]["cell"] == O.CELLS["inv2"] and e["key"]["clock_rc"] == "ndr" and e["key"]["corners"] == ["TT", "FF"]
    assert e["fit"]["TT"]["legs"] == 40 and e["fit"]["TT"]["rms_built_ps"] is not None
    assert (tmp_path / "cal.built_with.json").is_file()      # old model of this config priced against the routed legs
    c = cfg("s81_go16")
    c["stage_model"]["entry"] = "inv2_ndr_refit_test"
    assert O.stage_check(c, O.load_registry(rp))[0]
    with pytest.raises(O.ConfigError):                      # duplicate id refused
        O.main(argv)


def test_duty_clock_cal_follows_the_cell_coord_1029():
    sys.path.insert(0, str(HERE.parent / "die_plan"))
    import clock_duty as CD
    assert CD.gate_clock_cal("inv2") == "spice_edge" and CD.gate_clock_cal("inv") == "spice_edge"
    assert CD.gate_clock_cal("buf") == "spice_cell" and CD.gate_clock_cal("mixed") == "spice_cell"
    assert CD.gate_clock_cal("inv2", "spice") == "spice"     # explicit choice kept
    with pytest.raises(ValueError):
        CD.gate_clock_cal("buf", "spice_buf_edge")
