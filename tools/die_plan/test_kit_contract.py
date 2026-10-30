"""PREFLIGHT-2: one passing fixture kit and one mutant per kit-contract check (kit_contract.py)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract as KC  # noqa: E402
import kit_preflight as KP  # noqa: E402

RC = """# OT_RC_CAL signal fit A
# OT_RC_CAL clock fit B
set_wire_rc -signal -resistance 2.6E-02 -capacitance 1.29E-01
set_wire_rc -clock -resistance 2.6E-02 -capacitance 1.0E-01
""" + "".join(f"set_layer_rc -layer {L} -resistance 1E-02 -capacitance 1E-01\n" for L in KC.RC_CAL_LAYERS)


def write_kit(kd):
    kd.mkdir(parents=True, exist_ok=True)
    (kd / "rtl").mkdir(exist_ok=True)
    (kd / "macros").mkdir(exist_ok=True)
    (kd / "config.mk").write_text("\n".join([
        "export DESIGN_NAME = top", "export VERILOG_FILES = /work/rtl/top.sv",
        "export DIE_AREA = 0 0 100 100", "export CORE_AREA = 4.32 4.32 95.68 95.68",
        "export CORNERS = tc bc", "export OT_VCLK_TT = 250.0000", "export OT_VCLK_FF = 202.5000",
        "export SET_RC_TCL = /work/setRC_rcx.tcl", "export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl",
        "export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl", "export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre.tcl",
        "export ADDITIONAL_LEFS = /work/macros/m.lef", "export MACRO_PLACEMENT_TCL = /work/macro_place.tcl", ""]))
    (kd / "constraint.sdc").write_text("create_clock -name clk -period 833 [get_ports clk]\n"
                                       "create_clock -name vclk -period 833\n"
                                       "set_clock_latency -source 250.0000 [get_clocks vclk]\n")
    (kd / "sdc_lint.json").write_text(json.dumps(dict(insertion_ps=250.0, insertion_ff_ps=202.5)))
    (kd / "clock_binding.json").write_text(json.dumps(dict(insertion_ps=dict(tt=250.0, ff=202.5))))
    (kd / "grt_pre.tcl").write_text('if {$::env(OT_VCLK_CORNER) eq "ff"} {\n'
                                    '  set_clock_latency -source 202.5 [get_clocks vclk]\n}\n')
    (kd / "io.tcl").write_text(
        "place_pin -pin_name {clk} -layer M5 -location {50.4120 60.0000} -pin_size {0.0480 0.4800}\n"
        "place_pin -pin_name {a} -layer M4 -location {0.0960 20.0160} -pin_size {0.1920 0.0240}\n"
        "place_pin -pin_name {y} -layer M4 -location {99.9040 20.0160} -pin_size {0.1920 0.0240}\n")
    (kd / "pins.json").write_text(json.dumps([dict(bus="clk", bit=None, layer="M5", x=50.412, y=60.0,
                                                   size=[0.048, 0.48], clock=True)]))
    (kd / "setRC_rcx.tcl").write_text(RC)
    (kd / "rtl/top.sv").write_text("module top(input clk, a, output y);\n (* keep *) reg r;\n"
                                   " always @(posedge clk) r <= a;\n assign y = r;\nendmodule\n")
    (kd / "ot_keep_regs.tcl").write_text("yosys select -set ot_kw {*}{w:* a:keep %i}\nyosys setattr -set keep 1 x\n")
    (kd / "macros/m.lef").write_text("MACRO m\n  SIZE 20 BY 20 ;\nEND m\n")
    (kd / "macro_place.tcl").write_text("foreach {master sites} {m {{40 10 R0}}} {\n  puts $master\n}\n")
    (kd / "mesh.json").write_text(json.dumps(dict(xs=[0.0, 100.0, 200.0], ys=[0.0, 50.0], taps=[], drivers={},
                                                  meta=dict(ndr="4w", mesh_vias={"None": 6}))))
    # a plan clock island clear of the static macro m (40..60 x 10..30): island_macro_clear applies and PASSes
    (kd / "island_ft.json").write_text(json.dumps(dict(arcs=[dict(rect_um=[5.0, 60.0, 25.0, 80.0])])))
    canon = KC._canon(KC.placed_pins(kd), [100.0, 100.0])
    (kd / "freeze.json").write_text(json.dumps(dict(schema="opentallas.test.core_freeze.v1", outline_um=[100.0, 100.0],
                                                    pins_canon_sha256=canon,
                                                    insertion_ff_ps=202.5)))
    return kd


@pytest.fixture
def kit(tmp_path):
    return write_kit(tmp_path / "kit")


def verdicts(kd):
    return {k: v["verdict"] for k, v in KC.run_all(kd).items()}


def test_fixture_passes_every_check(kit):
    r = KC.run_all(kit)
    # macro_instances is NA here: the fixture places by master (foreach {master sites}), no instance paths
    want = {k: "NA" if k == "macro_instances" else "PASS" for k in KC.CHECKS}
    assert {k: v["verdict"] for k, v in r.items()} == want, \
        {k: v["errors"] for k, v in r.items() if v["errors"]}


def _sub(path, old, new):
    t = path.read_text()
    assert old in t, (path, old)
    path.write_text(t.replace(old, new))


def m_corner(kd):      # single-mode tc+bc session with an unconditional global FF vclk latency (HEAD R16 phantom hold)
    (kd / "grt_pre.tcl").write_text("set_clock_latency -source 202.5 [get_clocks vclk]\n")


def m_ff(kd):          # sdc_lint FF reference off the 12.3 contract
    (kd / "sdc_lint.json").write_text(json.dumps(dict(insertion_ps=250.0, insertion_ff_ps=260.95)))


def m_clock_pin(kd):   # core_infra_impl-style proc places the entry 0.032x0.192, off the M5 track (c15b DRT-0255)
    _sub(kd / "io.tcl", "place_pin -pin_name {clk} -layer M5 -location {50.4120 60.0000} -pin_size {0.0480 0.4800}\n", "")
    (kd / "core_infra_impl.tcl").write_text("proc ot_ci_clock_entry {name x y} {\n"
                                            "  place_pin -pin_name $name -layer M5 -location [list $x $y] -pin_size {0.032 0.192}\n}\n")
    (kd / "master_core_infra.tcl").write_text("ot_ci_clock_entry {clk} 50.4 60\n")


def m_rc(kd):          # RC file without the signal-net calibration record (FLOW-RC-1)
    _sub(kd / "setRC_rcx.tcl", "# OT_RC_CAL signal fit A\n", "")


def m_dup(kd):         # same module in two listed sources
    (kd / "rtl/dup.sv").write_text("module top(input clk, a, output y); assign y = a; endmodule\n")
    _sub(kd / "config.mk", "/work/rtl/top.sv", "/work/rtl/top.sv /work/rtl/dup.sv")


def m_keep(kd):        # keep-by-name of a parameterised module instantiated with overrides ($paramod rename)
    (kd / "rtl/top.sv").write_text("module sub #(parameter W=1)(input a, output y); assign y = a; endmodule\n"
                                   "module top(input clk, a, output y);\n (* keep *) reg r;\n"
                                   " always @(posedge clk) r <= a;\n sub #(.W(2)) u(.a(r), .y(y));\nendmodule\n")
    (kd / "config.mk").write_text((kd / "config.mk").read_text() + "export SYNTH_KEEP_MODULES = sub\n")


def m_keep_hook(kd):   # keep registers but no keep-regs hook staged
    _sub(kd / "config.mk", "export SYNTH_CANONICALIZE_TCL = /work/ot_keep_regs.tcl\n", "")


def m_pins(kd):        # a placed pin moved after the plan pin hash was recorded
    _sub(kd / "io.tcl", "{99.9040 20.0160}", "{99.9040 20.2560}")


def m_mesh(kd):        # mesh with one crossing via short of its strap crossings
    M = json.loads((kd / "mesh.json").read_text())
    M["meta"]["mesh_vias"] = {"None": 5}
    (kd / "mesh.json").write_text(json.dumps(M))


def m_channel(kd):     # macro column abutting the core W edge: no W vertical channel
    (kd / "macro_place.tcl").write_text("foreach {master sites} {m {{4.32 10 R0}}} {\n}\n")


def m_entry(kd):       # macro placed under the clock entry (other foreach form: master x y orient pat)
    (kd / "macro_place.tcl").write_text("foreach {master x y orient pat} {m 40 50 R0 {*u_m}} {\n}\n")


@pytest.mark.parametrize("mutate,check", [
    (m_corner, "corner_modes"), (m_ff, "ff_binding"), (m_clock_pin, "clock_pin_geometry"), (m_rc, "rc_calibration"),
    (m_dup, "duplicate_modules"), (m_keep, "keep_hook"), (m_keep_hook, "keep_hook"), (m_pins, "pins_canonical"),
    (m_mesh, "mesh_vias"), (m_channel, "macro_channels"), (m_entry, "clock_entry_clear")])
def test_mutant_fails_its_check(kit, mutate, check):
    mutate(kit)
    r = KC.run_all(kit)
    assert r[check]["verdict"] == "FAIL", r[check]
    if mutate is not m_clock_pin:   # moving the entry into a proc only touches the entry checks
        others = {k: v["verdict"] for k, v in r.items() if k != check and v["verdict"] == "FAIL"}
        assert not others, {k: r[k]["errors"] for k in others}


def test_no_macros_no_mesh_is_na(kit):
    for f in ("macros/m.lef", "macro_place.tcl", "mesh.json"):
        (kit / f).unlink()
    _sub(kit / "config.mk", "export ADDITIONAL_LEFS = /work/macros/m.lef\n", "")
    v = verdicts(kit)
    assert v["macro_channels"] == v["clock_entry_clear"] == v["mesh_vias"] == "NA"


def test_unplaced_macros_fail_closed(kit):
    _sub(kit / "config.mk", "export MACRO_PLACEMENT_TCL = /work/macro_place.tcl\n", "")
    v = verdicts(kit)
    assert v["macro_channels"] == v["clock_entry_clear"] == "FAIL"


def test_preflight_emits_beside_freeze(kit):
    rc = KP.main([str(kit)])
    rec = json.loads((kit / "preflight.json").read_text())
    assert rec["schema"] == "opentallas.kit_preflight.v2" and set(KC.CHECKS) <= set(rec["checks"])
    assert all(rec["checks"][c]["verdict"] == ("NA" if c == "macro_instances" else "PASS") for c in KC.CHECKS)
    assert rc == int(rec["verdict"] != "PASS")


def test_contract_binding_scope(kit):
    assert KC.is_core_kit(kit)
    m_rc(kit)
    assert any(i.startswith("rc_calibration") for i in KP.check(kit)["issues"])
    fz = json.loads((kit / "freeze.json").read_text())
    fz["schema"] = "opentallas.partition_freeze.v1"
    (kit / "freeze.json").write_text(json.dumps(fz))
    r = KP.check(kit)
    assert not r["contract_binding"] and r["contract_advisory"]["rc_calibration"]["verdict"] == "FAIL"
    assert not any(i.startswith("rc_calibration") for i in r["issues"])
    assert any(i.startswith("rc_calibration") for i in KP.check(kit, contract=True)["issues"])


# ---------------------------------------------------------------- COORD 10-27 KV-KITS-7 rulings 2+3 (partition kits)
def _partition(kd):
    """the fixture as a gen_phys PARTITION kit: M7 die-clock on-ramp at its plan tap, partition freeze from plan pins."""
    import master_slice as MS
    x, y = MS.snap_on_track(kd, "M7", 50.4, 60.0)
    _sub(kd / "io.tcl", "place_pin -pin_name {clk} -layer M5 -location {50.4120 60.0000} -pin_size {0.0480 0.4800}\n",
         f"place_pin -pin_name clk -layer M7 -location {{{x:.4f} {y:.4f}}} -pin_size {{0.0320 0.7680}}   ;# interior: die spine tap\n")
    (kd / "pins.json").write_text(json.dumps([dict(bus="a", bit=None, layer="M4", x=0.0, y=20.016, face="W")]))
    (kd / "budget.json").write_text(json.dumps(dict(
        schema="opentallas.die_plan.partition_budget.v1", type="tp", outline_um=[100.0, 100.0], signal_max="M7",
        clock=dict(taps=[dict(name="clk", xy=[50.4, 60.0], kind="grid")], taps_snapped=[dict(name="clk", xy=[x, y])]))))
    recs = [dict(name="a", layer="M4", x=0.096, y=20.016), dict(name="y", layer="M4", x=99.904, y=20.016),
            dict(name="clk", layer="M7", x=round(x, 4), y=round(y, 4))]
    (kd / "plan_pins.json").write_text(json.dumps(dict(pins=recs)))
    import hashlib
    (kd / "freeze.json").write_text(json.dumps(dict(
        schema="opentallas.partition_freeze.v1", outline_um=[100.0, 100.0], pins_file="plan_pins.json",
        pins_sha256=hashlib.sha256((kd / "plan_pins.json").read_bytes()).hexdigest(),
        pins_canon_sha256=KC._canon(recs, [100.0, 100.0]))))
    return x, y


def test_partition_m7_clock_on_plan_tap_passes(kit):
    _partition(kit)
    assert not KC.is_core_kit(kit) and KC.partition_budget(kit)
    r = KC.run_all(kit)
    assert r["clock_pin_geometry"]["verdict"] == "PASS", r["clock_pin_geometry"]["errors"]
    assert r["clock_pin_geometry"]["info"]["kind"] == "partition"
    assert r["pins_canonical"]["verdict"] == "PASS", r["pins_canonical"]["errors"]


def test_partition_clock_off_plan_tap_or_layer_fails(kit):
    x, y = _partition(kit)
    t = (kit / "io.tcl").read_text()
    (kit / "io.tcl").write_text(t.replace("-layer M7", "-layer M5"))
    assert verdicts(kit)["clock_pin_geometry"] == "FAIL"
    (kit / "io.tcl").write_text(t.replace(f"{{{x:.4f} {y:.4f}}}", f"{{{x:.4f} {y + 4.32:.4f}}}"))
    v = verdicts(kit)
    assert v["clock_pin_geometry"] == "FAIL" and v["pins_canonical"] == "FAIL"


def test_core_kit_keeps_geom21_for_m7_clock(kit):
    _partition(kit)
    (kit / "budget.json").unlink()                 # no partition budget -> the core GEOM-21 rule
    assert verdicts(kit)["clock_pin_geometry"] == "FAIL"


def test_gen_phys_partition_freeze_from_plan_pins(tmp_path, monkeypatch):
    import gen_phys as G
    from types import SimpleNamespace
    P = SimpleNamespace(name="tp_plan", types={"tp": dict(outline_um=[100.0, 100.0])},
                        layer_budget=dict(partition_signal_max="M7"))
    monkeypatch.setattr(G, "tap_pins", lambda P_, tn: [("clk", 50.4, 60.0)])
    monkeypatch.setattr(G, "reset_out_pins", lambda P_, tn: [])
    pins = [("a", 0, "M4", 0.0, 20.016, "W"), ("y", 0, "M4", 100.0, 20.016, "E"), ("n", 0, "M5", 30.0, 100.0, "N")]
    recs = G.plan_pin_records(P, "tp", pins)
    assert {r["name"]: (r["x"], r["y"]) for r in recs} == {
        "a[0]": (0.096, 20.016), "y[0]": (99.904, 20.016), "n[0]": (30.0, 99.904), "clk": (50.4, 60.0)}
    kd = tmp_path / "tp"
    kd.mkdir()
    (kd / "io.tcl").write_text("".join(
        f"place_pin -pin_name {{{r['name']}}} -layer {r['layer']} -location {{{r['x']:.4f} {r['y']:.4f}}} "
        "-pin_size {0.1920 0.0240}\n" for r in recs))
    fz = G.write_partition_freeze(P, "tp", kd, recs)
    assert fz["schema"] == "opentallas.partition_freeze.v1" and "core" not in fz["schema"]
    errors, info = KC.pins_canonical(kd)
    assert not errors and info["plan_canon"] == fz["pins_canon_sha256"]
    (kd / "io.tcl").write_text((kd / "io.tcl").read_text().replace("{99.9040 20.0160}", "{99.9040 20.2560}"))
    with pytest.raises(ValueError):
        G.write_partition_freeze(P, "tp", kd, recs)


def test_island_macro_clear_mutants(kit):
    assert verdicts(kit)["island_macro_clear"] == "PASS"
    (kit / "island_ft.json").write_text(json.dumps(dict(arcs=[dict(rect_um=[55.0, 25.0, 70.0, 40.0])])))
    assert verdicts(kit)["island_macro_clear"] == "FAIL"           # island under the static macro
    (kit / "island_ft.json").write_text(json.dumps(dict(arcs=[dict(rect_um=[61.0, 10.0, 70.0, 30.0])])))
    assert verdicts(kit)["island_macro_clear"] == "PASS"
    _sub(kit / "config.mk", "export MACRO_PLACEMENT_TCL = /work/macro_place.tcl\n", "export MACRO_PLACE_HALO = 2 2\n")
    assert verdicts(kit)["island_macro_clear"] == "FAIL"           # rtl_macro_placer without the island guard
    (kit / "island_ft.json").unlink()
    assert verdicts(kit)["island_macro_clear"] == "NA"


def test_pins_canonical_plan_table_with_dir(tmp_path):
    """QK-CORES-6 (QC btab profile1713): a plan pin table carrying netlist "dir" per pin (opentallas.core_pins.v1) is
    judged on placement only (io.tcl has no direction); a moved pin still FAILs."""
    import hashlib
    kd = tmp_path / "k"
    kd.mkdir()
    rows = [dict(name="a[0]", layer="M5", x=10.02, y=0.042, face="S", dir="in"),
            dict(name="q[0]", layer="M4", x=99.958, y=20.016, face="E", dir="out")]
    doc = dict(schema="opentallas.core_pins.v1", core="k", pins=rows)
    b = json.dumps(doc).encode()
    (kd / "plan_pins.json").write_bytes(b)
    (kd / "io.tcl").write_text("".join(f"place_pin -pin_name {{{r['name']}}} -layer {r['layer']} -location "
                                       f"{{{r['x']:.4f} {r['y']:.4f}}} -pin_size {{0.024 0.084}}\n" for r in rows))
    (kd / "freeze.json").write_text(json.dumps(dict(
        outline_um=[100.0, 100.0], pins_file="cores/x/k_pins.json", pins_sha256=hashlib.sha256(b).hexdigest(),
        pins_canon_sha256=KC._canon(doc, [100.0, 100.0]))))
    errors, info = KC.pins_canonical(kd)
    assert not errors and info["plan_file"].endswith("plan_pins.json")
    (kd / "io.tcl").write_text((kd / "io.tcl").read_text().replace("{10.0200 0.0420}", "{10.0680 0.0420}"))
    errors, _ = KC.pins_canonical(kd)
    assert errors and "plan pin file" in errors[0]


def _landing_clock(kit):
    import master_slice as MS
    _partition(kit)
    name = 'fclk_in_contract'
    x, y = MS.snap_on_track(kit, 'M7', 2.0, 40.0)
    with (kit / 'constraint.sdc').open('a') as f:
        f.write(f'create_clock -name forwarded -period 833 [get_ports {name}]\n')
    with (kit / 'io.tcl').open('a') as f:
        f.write(f'place_pin -pin_name {name} -layer M7 -location {{{x:.4f} {y:.4f}}} '
                '-pin_size {0.0320 0.7680}\n')
    contract = dict(physical_qualified=False, pins=[dict(name=name, kind='clock', dir='in',
                                                       layer='M7', xy_um=[x, y])])
    (kit / 'landing_contract.json').write_text(json.dumps(contract))
    return contract


def test_partition_declared_landing_clock_keeps_all_geometry_checks(kit):
    _landing_clock(kit)
    errors, info = KC.clock_pin_geometry(kit)
    assert not errors, errors
    assert 'fclk_in_contract' in info['clock_ports']
    t = (kit / 'io.tcl').read_text()
    (kit / 'io.tcl').write_text(t.replace('-pin_size {0.0320 0.7680}', '-pin_size {0.01 0.01}'))
    assert any('pin_size' in e for e in KC.clock_pin_geometry(kit)[0])


@pytest.mark.parametrize('mutate', ['missing', 'data', 'out', 'xy', 'layer'])
def test_partition_landing_name_alone_or_wrong_contract_never_waives_geometry(kit, mutate):
    contract = _landing_clock(kit)
    p = kit / 'landing_contract.json'
    if mutate == 'missing':
        p.unlink()
    else:
        pin = contract['pins'][0]
        if mutate == 'data': pin['kind'] = 'data'
        if mutate == 'out': pin['dir'] = 'out'
        if mutate == 'xy': pin['xy_um'][1] += 4.32
        if mutate == 'layer': pin['layer'] = 'M5'
        p.write_text(json.dumps(contract))
    assert KC.clock_pin_geometry(kit)[0]


def test_pins_canonical_native_multiport_pins(tmp_path):
    """DIE-S81-32/PINEV 10-29: gen_core_kit_legacy emits a declared multiPORT pin as dbBPin/dbBox shapes, not place_pin;
    the placed pin set reads it at the rect centred on the plan pin (kit = plan: PASS), a moved rect still FAILs."""
    import hashlib
    kd = tmp_path / "k"
    kd.mkdir()
    rows = [dict(name="a[0]", layer="M5", x=10.02, y=0.042), dict(name="ck", layer="M4", x=0.096, y=15.132)]
    doc = dict(module="k", pins=rows)
    b = json.dumps(doc).encode()
    (kd / "plan_pins.json").write_bytes(b)
    mp = ("set ot_mp_bt [[ord::get_db_block] findBTerm {ck}]\n"
          'if {$ot_mp_bt eq "NULL" || $ot_mp_bt eq ""} {error "native multiPORT BTerm missing"}\n'
          "foreach ot_mp_old [$ot_mp_bt getBPins] {odb::dbBPin_destroy $ot_mp_old}\n"
          "set ot_mp_bp [odb::dbBPin_create $ot_mp_bt]\n"
          "set ot_mp_u [[ord::get_db_block] getDbUnitsPerMicron]\n"
          "$ot_mp_bp setPlacementStatus FIRM\n"
          "odb::dbBox_create $ot_mp_bp [[ord::get_db_tech] findLayer M4] [expr {int(round(0.156000*$ot_mp_u))}] "
          "[expr {int(round(15.120000*$ot_mp_u))}] [expr {int(round(0.275000*$ot_mp_u))}] [expr {int(round(15.144000*$ot_mp_u))}]\n"
          "odb::dbBox_create $ot_mp_bp [[ord::get_db_tech] findLayer M4] [expr {int(round(0.000000*$ot_mp_u))}] "
          "[expr {int(round(15.120000*$ot_mp_u))}] [expr {int(round(0.192000*$ot_mp_u))}] [expr {int(round(15.144000*$ot_mp_u))}]\n")
    (kd / "io.tcl").write_text("place_pin -pin_name {a[0]} -layer M5 -location {10.0200 0.0420} -pin_size {0.024 0.084}\n"
                               + mp)
    (kd / "pins.json").write_text(json.dumps([dict(bus="a", bit=0, layer="M5", x=10.02, y=0.042),
                                              dict(bus="ck", bit=None, layer="M4", x=0.096, y=15.132)]))
    (kd / "freeze.json").write_text(json.dumps(dict(
        outline_um=[100.0, 100.0], pins_file="cores/x/k_pins.json", pins_sha256=hashlib.sha256(b).hexdigest(),
        pins_canon_sha256=KC._canon(doc, [100.0, 100.0]))))
    assert {p["name"]: (p["layer"], p["x"], p["y"]) for p in KC.placed_pins(kd)} == {
        "a[0]": ("M5", 10.02, 0.042), "ck": ("M4", 0.096, 15.132)}
    errors, _ = KC.pins_canonical(kd)
    assert not errors, errors
    (kd / "io.tcl").write_text((kd / "io.tcl").read_text().replace("15.120000", "15.168000").replace("15.144000", "15.192000"))
    errors, _ = KC.pins_canonical(kd)
    assert errors and "plan pin file" in errors[-1]
