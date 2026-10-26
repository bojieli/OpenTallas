"""METHODOLOGY 12.7c: kits consume a master-plan slice (tools/die_plan/master_slice.py, gen.py phys --master-slice)."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import master_slice as MS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TINY = HERE / "examples/tiny_plan.json"


def good_slice(**kw):
    sl = {
        "schema": MS.SCHEMA, "die": "tiny", "kind": "partition", "type": "src", "module": "tiny_src_part",
        "instances": ["p_src"], "plan": "tools/die_plan/examples/tiny_plan.json", "plan_sha256": "aa",
        "master_plan_sha256": "mp1", "frozen": False, "outline_um": [864.0, 864.0],
        "keepouts": [
            {"name": "isl_c", "rect_um": [420.0, 420.0, 444.0, 444.0], "kind": "island", "use": ["placement"]},
            {"name": "shield", "rect_um": [100.0, 0.0, 104.32, 864.0], "kind": "clock_shield", "layers": ["M8", "M9"]},
        ],
        "islands": [{"name": "isl_c", "rect_um": [420.0, 420.0, 444.0, 444.0], "centre_um": [432.0, 432.0],
                     "use": "clock_driver+reset", "via_stack": ["M9", "M5"],
                     "clock_pin": {"layer": "M5", "xy_um": [432.0, 432.0]},
                     "pg_rails": "die M8/M9 stripes on the 4.32 lattice"}],
        "bays": [{"name": "bay_w0", "rect_um": [10.0, 200.0, 40.0, 260.0], "owner": "src", "kind": "station",
                  "bits": 64, "cell_area_um2": 120.0, "fill": 0.4, "layer": "M7", "paths": ["L0"]}],
        "entry_pins": [
            {"name": "e0", "pin": "din[0]", "layer": "M7", "xy_um": [0.0, 210.0], "bay": "bay_w0", "path": "L0", "bit": 0},
            {"name": "e1", "pin": None, "layer": "M7", "xy_um": [0.0, 211.0], "bay": "bay_w0", "path": "L0", "bit": 1},
        ],
        "hard_cores": [],
        "latency": {"common_clock_latency_ps": {"TT": 250, "FF": 202.5}, "tol_ps": 40, "early_taps": False},
        "corridors": [{"path": "L0", "layer": "M7", "bits": 64, "polyline_um": [[0, 210], [864, 210]], "band_um": 4}],
        "gates": {"reach": "PASS", "bay_fill": "NOT RUN"},
    }
    sl.update(kw)
    return sl


def write_slices(d, **kw):
    d.mkdir(parents=True, exist_ok=True)
    for t in ("src", "mid", "sink"):
        sl = good_slice(type=t, module=f"tiny_{t}_part", **kw)
        (d / f"{t}.json").write_text(json.dumps(sl, indent=1))
    return d


def test_validate_good_and_load(tmp_path):
    assert MS.validate(good_slice()) == []
    p = tmp_path / "src.json"
    p.write_text(json.dumps(good_slice()))
    assert MS.load(p)["type"] == "src"
    assert MS.find(tmp_path, "src") == p
    with pytest.raises(MS.SliceError):
        MS.find(tmp_path, "nope")


@pytest.mark.parametrize("mut,frag", [
    (lambda s: s.update(schema="x.v0"), "schema"),
    (lambda s: s.update(kind="tile"), "kind"),
    (lambda s: s.update(outline_um=[0, 5]), "outline_um"),
    (lambda s: s["keepouts"][0].update(rect_um=[900, 0, 950, 10]), "outside the outline"),
    (lambda s: s["keepouts"][0].update(rect_um=[5, 5, 5, 9]), "empty rect"),
    (lambda s: s["keepouts"][0].update(kind="moat"), "kind expected"),
    (lambda s: s["keepouts"][1].update(layers=[]), "keeps nothing out"),
    (lambda s: s["islands"][0].update(centre_um=[0, 0]), "centre_um"),
    (lambda s: s["bays"][0].update(kind="parking"), "kind expected"),
    (lambda s: s["entry_pins"][0].update(bay="nobay"), "not a bay"),
    (lambda s: s["entry_pins"][1].update(pin="din[0]"), "also bound"),
    (lambda s: s["entry_pins"][0].update(xy_um=[-5, 1]), "outside the outline"),
    (lambda s: s.update(gates={"reach": "MAYBE"}), "gates"),
    (lambda s: s.update(frozen="yes"), "frozen"),
    (lambda s: s.pop("master_plan_sha256"), "master_plan_sha256"),
])
def test_validate_bad(tmp_path, mut, frag):
    sl = good_slice()
    mut(sl)
    errs = MS.validate(sl)
    assert any(frag in e for e in errs), errs
    p = tmp_path / "src.json"
    p.write_text(json.dumps(sl))
    with pytest.raises(MS.SliceError):
        MS.load(p)


def test_check_against_outline_and_stale():
    sl = good_slice()
    assert MS.check_against(sl, [864.0, 864.0005])
    with pytest.raises(MS.SliceError, match="outline"):
        MS.check_against(sl, [864.0, 865.0])
    assert MS.check_against(sl, [864, 864], "mp1")
    with pytest.raises(MS.SliceError, match="stale"):
        MS.check_against(sl, [864, 864], "mp2")


def test_emit_tcl_contents():
    tcl = MS.emit_tcl(good_slice())
    assert "ot_ms_blockage $ms_b 420000 420000 444000 444000" in tcl          # island + island keepout
    assert tcl.count("# placement blockage:") == 2
    assert "ot_ms_obstruction $ms_b M8 100000 0 104320 864000" in tcl
    assert "ot_ms_obstruction $ms_b M9 100000 0 104320 864000" in tcl
    assert "odb::dbBlockage_create $b $x0 $y0 $x1 $y1" in tcl
    assert "odb::dbObstruction_create $b $l $x0 $y0 $x1 $y1" in tcl
    assert "dict set ot_master_bays {bay_w0}" in tcl and "rect_um {10 200 40 260}" in tcl
    assert "place_pin -pin_name {din[0]} -layer M7 -location {0.0000 210.0000} -pin_size {0.032 0.192}" in tcl
    assert "place_pin -pin_name {e1}" not in tcl and "dict set ot_master_entry_pins {e1}" in tcl
    assert tcl.count("place_pin") == 1
    assert "getDbUnitsPerMicron] != 1000" in tcl
    assert tcl.count("{") == tcl.count("}")
    assert "ot_master_bays" in MS.emit_tcl(good_slice(bays=[], entry_pins=[]))


def test_stamp():
    st = MS.stamp(good_slice(frozen=True))
    assert st == dict(slice_sha256=MS.digest(good_slice(frozen=True)), master_plan_sha256="mp1", type="src", frozen=True)
    assert MS.digest(good_slice()) != MS.digest(good_slice(frozen=True))


def test_required_plan_and_env(monkeypatch):
    monkeypatch.delenv("OT_MASTER_PLAN_REQUIRED", raising=False)
    assert not MS.required({})
    assert not MS.required(None)
    assert not MS.required({"master_plan": {"required": "yes"}})
    assert MS.required({"master_plan": {"required": True, "sha256": "x"}})
    monkeypatch.setenv("OT_MASTER_PLAN_REQUIRED", "1")
    assert MS.required({}) and MS.required(None)
    monkeypatch.setenv("OT_MASTER_PLAN_REQUIRED", "0")
    assert not MS.required({})


def _gen(tmp_path, out, *extra, plan=TINY, env=None):
    e = dict(os.environ)
    e.pop("OT_MASTER_PLAN_REQUIRED", None)
    e.update(env or {})
    return subprocess.run([sys.executable, str(HERE / "gen.py"), "phys", str(plan), "--out", str(out),
                           "--types", "src", *extra], capture_output=True, text=True, env=e)


def _tree(d):
    return {str(p.relative_to(d)): p.read_bytes() for p in sorted(Path(d).rglob("*")) if p.is_file()}


def _required_plan(tmp_path, sha="mp1"):
    raw = json.loads(TINY.read_text())
    raw["master_plan"] = {"required": True, "sha256": sha}
    p = tmp_path / "plan_req.json"
    p.write_text(json.dumps(raw))
    return p


def test_gen_phys_no_flag_unchanged(tmp_path):
    r = _gen(tmp_path, tmp_path / "a")
    assert r.returncode == 0, r.stderr
    kd = tmp_path / "a/src"
    assert not (kd / "master_slice.json").exists() and not (kd / "master_slice.tcl").exists()
    assert "master_plan" not in json.loads((kd / "budget.json").read_text())
    assert (kd / "face_flops.tcl").read_text() == (HERE / "face_flops.tcl").read_text()
    # a required-flag env of 0 / a non-True plan value change nothing
    r2 = _gen(tmp_path, tmp_path / "b", env={"OT_MASTER_PLAN_REQUIRED": "0"})
    assert r2.returncode == 0, r2.stderr
    assert _tree(tmp_path / "a/src") == _tree(tmp_path / "b/src")


def test_gen_phys_with_slice(tmp_path):
    sd = write_slices(tmp_path / "slices")
    r = _gen(tmp_path, tmp_path / "k", "--master-slice", str(sd))
    assert r.returncode == 0, r.stdout + r.stderr
    kd = tmp_path / "k/src"
    assert json.loads((kd / "master_slice.json").read_text())["type"] == "src"
    assert "OT_MASTER_SLICE type=src" in (kd / "master_slice.tcl").read_text()
    assert (kd / "face_flops.tcl").read_text().startswith(MS.HOOK_LINE)
    bud = json.loads((kd / "budget.json").read_text())
    assert bud["master_plan"] == MS.stamp(json.loads((sd / "src.json").read_text()))
    # all other kit files are those of the no-slice kit
    base = tmp_path / "base"
    assert _gen(tmp_path, base).returncode == 0
    a, b = _tree(base / "src"), _tree(kd)
    extra = set(b) - set(a)
    assert extra == {"master_slice.json", "master_slice.tcl"}
    assert {k for k in a if a[k] != b[k]} == {"face_flops.tcl", "budget.json"}


def test_gen_phys_outline_mismatch_refused(tmp_path):
    sd = tmp_path / "s"
    sd.mkdir()
    (sd / "src.json").write_text(json.dumps(good_slice(outline_um=[864.0, 432.0],
                                                       keepouts=[], islands=[], bays=[], entry_pins=[], corridors=[])))
    r = _gen(tmp_path, tmp_path / "k", "--master-slice", str(sd))
    assert r.returncode == 1 and "outline" in r.stdout


def test_gen_phys_required_refusal_and_trial(tmp_path):
    plan = _required_plan(tmp_path)
    r = _gen(tmp_path, tmp_path / "k0", plan=plan)
    assert r.returncode != 0 and "sign-off kit refused: no master-plan slice" in r.stderr
    assert not (tmp_path / "k0").exists()                       # refused before anything is written
    r = _gen(tmp_path, tmp_path / "k1", env={"OT_MASTER_PLAN_REQUIRED": "1"})
    assert r.returncode != 0 and "METHODOLOGY 12.7c" in r.stderr
    r = _gen(tmp_path, tmp_path / "k2", "--trial", plan=plan)
    assert r.returncode == 0, r.stderr
    assert json.loads((tmp_path / "k2/src/budget.json").read_text())["master_plan"] == MS.TRIAL
    assert not (tmp_path / "k2/src/master_slice.tcl").exists()


def test_gen_phys_required_stale_and_frozen(tmp_path):
    plan = _required_plan(tmp_path, sha="mp2")
    sd = write_slices(tmp_path / "s", frozen=True)
    r = _gen(tmp_path, tmp_path / "k", "--master-slice", str(sd), plan=plan)
    assert r.returncode == 1 and "stale" in r.stdout
    plan = _required_plan(tmp_path, sha="mp1")
    sd2 = write_slices(tmp_path / "s2", frozen=False)
    r = _gen(tmp_path, tmp_path / "k2", "--master-slice", str(sd2), plan=plan)
    assert r.returncode != 0 and "not from a frozen master plan" in r.stderr
    r = _gen(tmp_path, tmp_path / "k3", "--master-slice", str(sd), plan=plan)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads((tmp_path / "k3/src/budget.json").read_text())["master_plan"]["frozen"] is True


def test_kit_apply_core(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_MASTER_PLAN_REQUIRED", raising=False)
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "face_flops.tcl").write_text("puts ff\n")
    assert MS.kit_apply(kd, "core_x", [10, 10]) is None and sorted(os.listdir(kd)) == ["face_flops.tcl"]
    monkeypatch.setenv("OT_MASTER_PLAN_REQUIRED", "1")
    with pytest.raises(SystemExit, match="12.7c"):
        MS.precheck(None, False, None, "core_x")
    MS.precheck(None, True, None, "core_x")
    assert MS.kit_apply(kd, "core_x", [10, 10], trial=True) == MS.TRIAL
    sd = tmp_path / "s"
    sd.mkdir()
    sl = good_slice(kind="core", type="core_x", module="core_x", outline_um=[10, 10], frozen=True, keepouts=[],
                    islands=[], bays=[], entry_pins=[], corridors=[])
    (sd / "core_x.json").write_text(json.dumps(sl))
    st = MS.kit_apply(kd, "core_x", [10, 10], sd, None, kind="core", gpl_hook=kd / "face_flops.tcl")
    assert st["type"] == "core_x" and (kd / "keepout_phys.tcl").is_file()
    assert (kd / "face_flops.tcl").read_text() == MS.HOOK_LINE + "puts ff\n"
    with pytest.raises(MS.SliceError, match="kind"):
        MS.kit_apply(kd, "core_x", [10, 10], sd, None, kind="partition")


@pytest.mark.parametrize("gen", [
    "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py",
    "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py",
    "physical/die_plan/s81/cores/svc/gen_core_kit_s81.py",
    "physical/die_plan/s81/cores/eng/gen_core_kit.py",
    "physical/die_plan/hbm/cores/harden/gen_core_kit.py",
    "physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py",
    "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py",
])
def test_core_generators_wired(gen):
    """Static check (the generators need closed views / spec trees): flag, early refusal, kit hook, freeze stamp."""
    p = ROOT / gen
    if not p.is_file():
        pytest.skip(f"{gen} not in this checkout")
    s = p.read_text()
    assert "MS.add_args(ap)" in s
    assert s.index("MS.precheck(a.master_slice, a.trial") < s.index("shutil.rmtree(kd)")
    i = s.index("ms = MS.kit_apply(kd, ")
    assert s.index('(kd / "face_flops.tcl").write_text(') < i < s.index('(kd / "config.mk").write_text(')
    assert 'gpl_hook=kd / "face_flops.tcl"' in s and 'kind="core"' in s
    assert s.index('fz["master_plan"] = ms') < s.index('(kd / "freeze.json").write_text(')
