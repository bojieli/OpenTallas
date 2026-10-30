"""S81-CORE-LAT-R14 10-27: undeclared multi-root cores are refused; face_guard skip names every clock root.
S81-CORE-LAT-R20 10-27: DECLARED multi-root cores (recipe multi_root + spec clock_entry_domains) get one clock / entry per root.
    python3 -m pytest -q -p no:cacheprovider --noconftest test_gen_core_kit_legacy_multiroot.py"""
import json
import pytest
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402

CRS4 = {"top": "dsfd_cfifo_crs4", "clock_port": "cr",
        "clock_ports": ["cr", "cr_s", "xk[0]", "xk[1]", "xk[2]", "xk[3]"], "reset_ports": ["rst"]}


def test_clock_roots_fold_bus_bits():
    assert G.clock_roots(CRS4) == ["cr", "cr_s", "xk"]
    assert G.clock_roots({"clock_port": "ck"}) == ["ck"]
    assert G.clock_roots({"clock_port": "clk", "clock_ports": ["clk[0]"]}) == ["clk"]


def test_single_root_not_refused():
    assert G.multi_root_refusal("m", {"clock_port": "ck", "clock_ports": ["ck"]}) is None
    assert G.multi_root_refusal("m", {"clock_port": "ck"}) is None


def test_multi_root_refused_names_every_root():
    msg = G.multi_root_refusal("dsfd_cfifo_crs4", CRS4)
    assert msg and "multi-root" in msg and "['cr', 'cr_s', 'xk']" in msg


def test_generator_refuses_undeclared_multi_root(tmp_path):
    """a multi-root core whose recipe does not declare multi_root stays refused (fail closed)."""
    rec = json.loads((HERE / "recipes.json").read_text())
    rec["dsfd_cfifo_crs4"].pop("multi_root", None)
    rp = tmp_path / "recipes.json"
    rp.write_text(json.dumps(rec))
    r = subprocess.run([sys.executable, str(HERE / "gen_core_kit_legacy.py"), "--module", "dsfd_cfifo_crs4",
                        "--recipes", str(rp), "--out", str(tmp_path / "k"), "--suffix", "t", "--trial"],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "multi-root core ['cr', 'cr_s', 'xk']" in r.stderr, r.stderr[-1500:]
    assert "declare recipe multi_root" in r.stderr
    assert not (tmp_path / "k" / "dsfd_cfifo_crs4_t").exists()


# ---- S81-CORE-LAT-R20: DECLARED multi-root cores ------------------------------------------------------------------
REL = {"clock_relationship": {"kind": "same_pll_fixed_phase", "ratio": [1, 1], "phase_ps": 0},
       "clock_data_paths": "related_same_frequency"}
DOM = {"core": {"ratio": [1, 1], "ports": ["cr"], "inputs": ["ri", "st", "rst", "lk"], "outputs": ["xa", "xb", "cc", "x2", "rs"]},
       "lane0": {"ratio": [1, 1], "ports": ["xk[0]"], "inputs": ["xl0"], "outputs": []},
       "lane1": {"ratio": [1, 1], "ports": ["xk[1]"], "inputs": ["xl1"], "outputs": []},
       "lane2": {"ratio": [1, 1], "ports": ["xk[2]"], "inputs": ["xl2"], "outputs": []},
       "lane3": {"ratio": [1, 1], "ports": ["xk[3]"], "inputs": ["xl3"], "outputs": []},
       "core_s": {"ratio": [1, 1], "ports": ["cr_s"], "inputs": [], "outputs": ["rd"]}}
FULL = dict(CRS4, clock_entry_domains=DOM, **REL)


def test_contract_single_root_is_none():
    assert G.multi_root_contract("m", {"clock_port": "ck"}, {}) is None
    assert G.multi_root_contract("m", {"clock_port": "ck", "clock_ports": ["ck"]}, {"multi_root": True}) is None


def test_contract_crs4_roots_entries_frames():
    mr = G.multi_root_contract("dsfd_cfifo_crs4", FULL, {"multi_root": True})
    assert [r["clock"] for r in mr["roots"]] == ["clk", "clk_cr_s", "clk_xk"]
    assert [r["pins"] for r in mr["roots"]] == [["cr"], ["cr_s"], ["xk[0]", "xk[1]", "xk[2]", "xk[3]"]]
    assert mr["domain_of_bus"]["xl2"] == "xk[2]" and mr["domain_of_bus"]["rd"] == "cr_s" and mr["domain_of_bus"]["rst"] == "cr"
    assert ["clk_xk", "clk"] in mr["pairs"] and len(mr["pairs"]) == 6


def _refused(spec, rec=None):
    with pytest.raises(SystemExit) as e:
        G.multi_root_contract("dsfd_cfifo_crs4", spec, {"multi_root": True} if rec is None else rec)
    return str(e.value)


def test_contract_refuses_async_or_ratio():
    assert "same_pll_fixed_phase" in _refused(dict(FULL, clock_relationship={"kind": "async"}))
    assert "related_same_frequency" in _refused(dict(FULL, clock_data_paths="async"))
    d = json.loads(json.dumps(DOM)); d["lane0"]["ratio"] = [1, 2]
    assert "ratio" in _refused(dict(FULL, clock_entry_domains=d))


def test_contract_refuses_missing_or_double_root_and_bus():
    d = json.loads(json.dumps(DOM)); del d["lane3"]
    assert "domain root pins" in _refused(dict(FULL, clock_entry_domains=d))
    d = json.loads(json.dumps(DOM)); d["lane0"]["ports"] = ["xk[0]", "xk[1]"]
    msg = _refused(dict(FULL, clock_entry_domains=d))
    assert "exactly one" in msg and "xk[1]" in msg
    d = json.loads(json.dumps(DOM)); d["lane1"]["inputs"] = ["xl1", "ri"]
    assert "IO bus ri in two domains" in _refused(dict(FULL, clock_entry_domains=d))
    assert "no clock_entry_domains" in _refused(dict(FULL, clock_entry_domains={}))


def test_check_io_every_bus_in_a_domain():
    mr = G.multi_root_contract("dsfd_cfifo_crs4", FULL, {"multi_root": True})
    G.multi_root_check_io("m", mr, ["ri", "st", "lk", "xl0", "xl1", "xl2", "xl3"], ["xa", "xb", "cc", "x2", "rs", "rd"], ["rst"])
    with pytest.raises(SystemExit, match="buses without a domain"):
        G.multi_root_check_io("m", mr, ["ri", "st", "lk", "xl0", "xl1", "xl2", "xl3", "zz"],
                              ["xa", "xb", "cc", "x2", "rs", "rd"], ["rst"])


def test_multi_root_sdc_lints_clean():
    mr = G.multi_root_contract("dsfd_cfifo_crs4", FULL, {"multi_root": True})
    txt = G.multi_root_sdc(G.sdc(833.0, 250.0, 20.0, ["cr"], ["rst"], "dsfd_cfifo_crs4"), mr, 833.0)
    assert txt.count("create_clock -name clk") == 3 and "[get_ports {xk}]" in txt
    for c in ("clk", "clk_cr_s", "clk_xk"):
        assert f"-from [get_clocks vclk] -to [get_clocks {c}] -setup 30.0000" in txt
    assert "set_clock_groups" not in txt and "set_false_path" not in txt   # inter-root paths are timed
    errs = G.sdc_lint.lint(txt, period_ps=833.0, insertion_ps=250.0, insertion_tol_ps=20.0,
                           clock_ports=["cr", "cr_s", "xk"], inputs=["ri", "st", "lk", "xl0", "xl1", "xl2", "xl3", "rst"],
                           outputs=["xa", "xb", "cc", "x2", "rs", "rd"], io_floor_ps={})
    assert errs == [], errs


def test_generator_kits_declared_crs4(tmp_path):
    r = subprocess.run([sys.executable, str(HERE / "gen_core_kit_legacy.py"), "--module", "dsfd_cfifo_crs4",
                        "--out", str(tmp_path), "--suffix", "t", "--trial"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    kd = tmp_path / "dsfd_cfifo_crs4_t"
    sdc_ = (kd / "constraint.sdc").read_text()
    assert [l.split()[2] for l in sdc_.splitlines() if l.startswith("create_clock")] == ["clk", "clk_cr_s", "clk_xk", "vclk"]
    cr = json.loads((kd / "clock_roots.json").read_text())
    assert [e["pin"] for e in cr["entries"]] == ["cr", "cr_s", "xk[0]", "xk[1]", "xk[2]", "xk[3]"]
    assert cr["budget_ps"]["tt"] == 250.0 and abs(cr["budget_ps"]["ff"] - 202.5) < 1e-6
    assert all(e["plan_xy_um"] for e in cr["entries"])
    core = json.loads((kd / "core.json").read_text())
    assert {k for k, v in core["boundary_role"].items() if v == "clk"} == {"cr", "cr_s", "xk"}
    assert json.loads((kd / "boundary_guard_context.json").read_text())["clock_ports"] == ["cr", "cr_s", "xk"]
    assert r"set tb_port_re {^(cr|cr_s|xk)(\[[0-9]+\])?$}" in (kd / "tap_balance.tcl").read_text()
    fps = (kd / "core_face_post_synth.tcl").read_text()
    assert "ot_fc_ck_of" in fps and "connect $ot_fc_ck\n" not in fps
    assert "set ::ot_fc_map [dict create" in (kd / "core_clock_map.tcl").read_text()
    assert "{xl3} {xk[3]}" in (kd / "core_clock_map.tcl").read_text()
    assert "global ot_fc" not in fps and "$::ot_fc_map" in fps   # sourced inside a proc (synth_odb.tcl)
    assert "set ot_pg_virtual {}" in (kd / "postcts_gate.tcl").read_text()
    assert "get_property $ot_pg_clock sources" in (kd / "postcts_gate.tcl").read_text()
    assert "set_propagated_clock [get_clocks {clk clk_cr_s clk_xk}]" in (kd / "corners.tcl").read_text()
    assert "OT_CORE_SKIP = cr cr_s xk rst" in (kd / "config.mk").read_text()
    fz = json.loads((kd / "freeze.json").read_text())
    assert fz["clocks"] == ["cr", "cr_s", "xk"] and fz["multi_root"]["entries"] == 6


def test_generator_multi_root_master_slice_fail_closed(tmp_path):
    # R21: multi-root cores now accept a master slice with clock_entries[] (one per root; the kit_apply refusals of
    # the single-entry form are unit-tested in tools/die_plan/test_master_slice.py). Without a slice: fail closed.
    r = subprocess.run([sys.executable, str(HERE / "gen_core_kit_legacy.py"), "--module", "dsfd_cfifo_crs4",
                        "--out", str(tmp_path), "--suffix", "t", "--master-slice", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "master-plan slice for 'dsfd_cfifo_crs4' not found" in r.stderr, r.stderr[-1500:]
    assert "master slices carry one clock entry" not in r.stderr


def test_multi_root_postcts_preserves_virtual_selector_and_all_roots(tmp_path):
    import shutil
    shutil.copyfile(HERE / "core_face_post_synth.tcl", tmp_path / "core_face_post_synth.tcl")
    shutil.copyfile(G.TOOL / "postcts_gate.tcl", tmp_path / "postcts_gate.tcl")
    (tmp_path / "corners.tcl").write_text("set_propagated_clock [get_clocks clk]\n")
    mr = G.multi_root_contract("dsfd_cfifo_crs4", FULL, {"multi_root": True})
    G.multi_root_tcl_patches(tmp_path, mr)
    t = (tmp_path / "postcts_gate.tcl").read_text()
    assert "get_property $ot_pg_clock sources" in t
    assert "set_clock_latency -source $ot_pg_bound $ot_pg_virtual" in t
    assert "set_propagated_clock [get_clocks {clk clk_cr_s clk_xk}]" in t
    assert "foreach ot_rc [get_clocks {clk clk_cr_s clk_xk}]" in t
    assert "set_propagated_clock [get_clocks vclk]" not in t


def test_multi_root_postcts_rejects_missing_virtual_selector(tmp_path):
    import shutil
    shutil.copyfile(HERE / "core_face_post_synth.tcl", tmp_path / "core_face_post_synth.tcl")
    t = (G.TOOL / "postcts_gate.tcl").read_text()
    (tmp_path / "postcts_gate.tcl").write_text(t.replace("get_property $ot_pg_clock sources", "get_property $ot_pg_clock period"))
    (tmp_path / "corners.tcl").write_text("set_propagated_clock [get_clocks clk]\n")
    mr = G.multi_root_contract("dsfd_cfifo_crs4", FULL, {"multi_root": True})
    with pytest.raises(AssertionError, match="virtual-clock selector changed"):
        G.multi_root_tcl_patches(tmp_path, mr)
