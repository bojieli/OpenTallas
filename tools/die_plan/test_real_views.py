"""REAL-VIEWS-1119 (COORD 11-19): the die chain passes every signed, pin-matched core view (--core-view) and type view
(--kit) to die_sta_related; unsigned or pin-mismatched blocks stay on the contract with a reason."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import die_sta_related as R
import gen_phys as G
import real_views as V
from test_die_sta_core_insertion import REG, _plan

HERE = Path(__file__).resolve().parent


def test_kit_model_measured_insertion_falls_back_to_pin_register():
    kit = {"corners": {"FF": dict(lat_min_ps=40.0, lat_max_ps=210.0)}}
    m = R.kit_model(kit, "FF", "fa", REG)
    assert (m["lat_early"], m["lat_late"]) == (40.0, 210.0) and m["real"]
    assert (m["clkq_max"], m["clkq_min"], m["setup"], m["hold"]) == (68.0, 60.0, 5.6, 22.2)
    full = {"corners": {"FF": dict(lat_min_ps=1, lat_max_ps=2, clkq_max_ps=3, clkq_min_ps=4, setup_ps=5, hold_ps=6)}}
    assert R.kit_model(full, "FF", "fa", REG)["hold"] == 6.0 and R.kit_model(full, "FF", "fa")["clkq_max"] == 3.0


DEF = """VERSION 5.8 ;
UNITS DISTANCE MICRONS 1000 ;
DIEAREA ( 0 0 ) ( 100000 50000 ) ;
COMPONENTS 1 ;
    - u1 DFF + PLACED ( 0 0 ) N ;
END COMPONENTS
PINS 3 ;
    - VDD + NET VDD + SPECIAL + DIRECTION INOUT + USE POWER
      + PORT
        + LAYER M7 ( -144 -100 ) ( 144 100 )
        + FIXED ( 5000 5000 ) N ;
    - d[0] + NET d[0] + DIRECTION INPUT + USE SIGNAL
      + PORT
        + LAYER M5 ( -16 -384 ) ( 16 384 )
        + FIXED ( 10000 300 ) N ;
    - q + NET q + DIRECTION OUTPUT + USE SIGNAL
      + PORT
        + LAYER M4 ( -10 0 ) ( 10 400 )
        + FIXED ( 99700 20000 ) E ;
END PINS
NETS 0 ;
END NETS
"""


def test_def_pins_after_components_and_orientation(tmp_path):
    f = tmp_path / "6_final.def"
    f.write_text(DEF)
    p = V.def_pins(f)
    assert set(p) == {"d[0]", "q"}                                   # power pins skipped
    assert p["d[0]"] == ("M5", 10.0, 0.3)
    assert p["q"][0] == "M4" and abs(p["q"][1] - 99.9) < 1e-9 and abs(p["q"][2] - 20.0) < 1e-9   # E: (x,y)->(y,-x)


def _plan_tree(tmp_path, view_pins, plan_pins, signed=True):
    raw = _plan(early=False)
    raw["partition_types"]["fa"]["hard_cores"][0]["pins_file"] = "pins/cmod.json"
    pd = tmp_path / "physical" / "die_plan" / "dz"
    (pd / "pins").mkdir(parents=True)
    (pd / "pins" / "cmod.json").write_text(json.dumps(plan_pins))
    (pd / "plan.json").write_text(json.dumps(raw))
    vd = tmp_path / "views" / "cmod"
    vd.mkdir(parents=True)
    for c in ("tt", "ff"):
        (vd / f"cmod_{c}.lib").write_text("library(x) {}\n")
    (vd / "pins.json").write_text(json.dumps(view_pins))
    if signed:
        (vd / "signoff.json").write_text(json.dumps({"verdict": "SIGNED"}))
    return pd / "plan.json", tmp_path / "views"


PINS = {"pins": [{"name": "clk", "layer": "M5", "x": 1.0, "y": 0.0}, {"name": "d", "layer": "M5", "x": 2.0, "y": 0.0}]}


def test_signed_core_with_matching_pins_is_real(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "parse_etm", lambda path, load: {})       # dummy libs
    plan, root = _plan_tree(tmp_path, PINS, PINS)
    args, st = V.resolve_cores(json.loads(plan.read_text()), plan, [root], tmp_path / "rv")
    assert st["cmod"]["status"] == "REAL" and st["cmod"]["verdict"] == "SIGNED"
    assert len(args) == 1 and args[0].startswith("--core-view=cmod=")
    vdir = Path(args[0].split("=", 2)[2])
    assert (vdir / "cmod_tt.lib").exists() and json.loads((vdir / "provenance.json").read_text())["kit"]["pins_sha256"]


def test_unsigned_or_moved_core_stays_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "parse_etm", lambda path, load: {})       # dummy libs
    plan, root = _plan_tree(tmp_path / "a", PINS, PINS, signed=False)
    args, st = V.resolve_cores(json.loads(plan.read_text()), plan, [root], tmp_path / "a" / "rv")
    assert args == [] and st["cmod"]["status"] == "CONTRACT" and "verdict None" in st["cmod"]["reasons"][-1]
    moved = {"pins": [dict(PINS["pins"][0]), dict(PINS["pins"][1], x=2.5)]}
    plan, root = _plan_tree(tmp_path / "b", PINS, moved)
    args, st = V.resolve_cores(json.loads(plan.read_text()), plan, [root], tmp_path / "b" / "rv")
    assert args == [] and st["cmod"]["status"] == "CONTRACT" and "pins mismatch" in st["cmod"]["reasons"][-1]


def test_type_kit_from_export_digest_needs_pin_match(tmp_path, monkeypatch):
    monkeypatch.setattr(G, "type_pins", lambda P, t: [("d", 0, "M5", 10.0, 0.0, "S")])
    kit = {"corners": {"TT": dict(lat_min_ps=50.0, lat_max_ps=260.0), "FF": dict(lat_min_ps=40.0, lat_max_ps=200.0)}}
    el = lambda pins, verdict="LOCAL_PASS_NEEDS_PARENT": dict(verdict=verdict, kit=kit, pins=pins, record="h:/x/signoff.json")
    plan = _plan(early=False)
    good = {"elements": {"fa__a1_1108": el({"d[0]": ["M5", 10.0, 0.3]}), "fb": el({"d[0]": ["M5", 10.05, 0.3]}),
                         "fx": el({"d[0]": ["M5", 10.0, 0.3]})}}
    args, st = V.resolve_types(plan, None, tmp_path, False, [good])
    assert st["fa"]["status"] == "REAL" and st["fa"]["verdict"] == "LOCAL_PASS_NEEDS_PARENT"   # re-sign suffix stripped
    assert st["fb"]["status"] == "CONTRACT" and "moved 1" in st["fb"]["reasons"][-1]          # 50 nm along the face
    assert args == [f"--kit=fa={tmp_path / 'kits' / 'fa.json'}"]
    assert json.loads((tmp_path / "kits" / "fa.json").read_text())["corners"]["FF"]["lat_max_ps"] == 200.0
    bad = {"elements": {"fa": el({"d[0]": ["M5", 10.0, 0.3]}, verdict="NOT SIGNED")}}
    _, st = V.resolve_types(plan, None, tmp_path, False, [bad])
    assert st["fa"]["status"] == "CONTRACT" and "NOT SIGNED" in st["fa"]["reasons"][-1]


def test_report_prints_measured_next_to_contract(tmp_path, capsys):
    cls = dict(pairs=12, worst_hold_slack_ps=-120.0, kit_contract_hold=dict(worst_hold_bound_ps=-80.0),
               hold_measured=dict(hold_margin_ps=14.5, pairs_measured=10, pairs_unmeasured=2, neg_pairs=0,
                                  status="BLOCKED(kits)"))
    (tmp_path / "die_sta_related.json").write_text(json.dumps({"corners": {"FF": {"classes": {"intra": cls}}}}))
    assert V.report(tmp_path) == 0
    out = capsys.readouterr().out
    assert "CONTRACT all-pair -120.0 kit-contract -80.0 | MEASURED 14.5 (10 measured, 2 unmeasured" in out
    assert json.loads((tmp_path / "hold_report.json").read_text())[0]["measured_hold_ps"] == 14.5


STUB_RV = r'''import sys, pathlib
a = sys.argv[1:]
if a[0] == "report":
    print("HOLD-REPORT stub"); sys.exit(0)
o = pathlib.Path(a[a.index("--out") + 1]); o.mkdir(parents=True, exist_ok=True)
(o / "args.txt").write_text("--core-view=cmod=/v/cmod\n--kit=fa=/k/fa.json\n"); print("REAL_VIEWS cores 1/1 types 1/2")
'''
STUB_STA = r'''import sys, pathlib
a = sys.argv[1:]
o = pathlib.Path(a[a.index("--out") + 1]); o.mkdir(parents=True, exist_ok=True)
(o / "argv.txt").write_text("\n".join(a))
'''
OK = "import sys; open(sys.argv[sys.argv.index('--out') + 1], 'w').write('{}')\n"


def _chain(tmp_path, kit_fallback):
    t = tmp_path / "tools" / "die_plan"
    (tmp_path / "tools" / "s81_head").mkdir(parents=True)
    t.mkdir(parents=True)
    shutil.copy(HERE / "die_chain_ca.sh", t)
    (t / "real_views.py").write_text(STUB_RV)
    (t / "die_sta_related.py").write_text(STUB_STA + ("# def kit_model(spec, corner, name, reg=None)\n" if kit_fallback else ""))
    for f in ("count_align_plan.py", "count_align_bind.py"):
        (t / f).write_text(OK)
    (tmp_path / "tools" / "s81_head" / "landed_phase_ocv.py").write_text(OK)
    (tmp_path / "plan.json").write_text("{}")
    env = dict(os.environ)
    env.pop("CA_TOOLS", None)
    r = subprocess.run(["bash", str(t / "die_chain_ca.sh"), str(tmp_path / "proof"), str(tmp_path / "plan.json"),
                        str(tmp_path / "out"), "inv2", "--extra"], env=env, capture_output=True, text=True)
    chain = (tmp_path / "out" / "CHAIN.log").read_text()
    argv = lambda d: (tmp_path / "out" / d / "argv.txt").read_text().split("\n")
    return r, chain, argv


def test_chain_passes_views_to_both_sta_runs(tmp_path):
    r, chain, argv = _chain(tmp_path, kit_fallback=True)
    assert r.returncode == 0, r.stderr
    assert "REAL_VIEWS cores 1/1 types 1/2" in chain and "HOLD-REPORT stub" in chain
    for d in ("sta_ca", "sta_legacy"):
        a = argv(d)
        assert "--core-view=cmod=/v/cmod" in a and "--kit=fa=/k/fa.json" in a and a[-1] == "--extra"


def test_chain_drops_kits_for_tools_without_register_fallback(tmp_path):
    r, chain, argv = _chain(tmp_path, kit_fallback=False)
    assert r.returncode == 0, r.stderr
    assert "kits SKIPPED" in chain
    a = argv("sta_ca")
    assert "--core-view=cmod=/v/cmod" in a and not any(x.startswith("--kit=") for x in a)


def test_core_view_without_boundary_arcs_stays_contract(tmp_path, monkeypatch):
    plan, root = _plan_tree(tmp_path, PINS, PINS)

    def etm(path, load):
        raise SystemExit(f"{path}: missing boundary arcs (out 0 setup 9 hold 9)")
    monkeypatch.setattr(R, "parse_etm", etm)
    args, st = V.resolve_cores(json.loads(plan.read_text()), plan, [root], tmp_path / "rv")
    assert args == [] and st["cmod"]["status"] == "CONTRACT"
    assert "ETM unusable (tt: missing boundary arcs" in st["cmod"]["reasons"][-1]
