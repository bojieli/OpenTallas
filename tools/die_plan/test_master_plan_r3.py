"""MASTER-PLAN-R3: kits consume their slice (pushdown cells for cores AND partitions, clock entry, bound M7 entry
pins, bay reservations), check_kit() static gate, die tree planned on the island lattice."""
import copy
import json

import pytest
import core_infra as CI
import master_plan as MP
import master_slice as MS
from test_core_infra import sample


def _kit(tmp_path, sl, io_lines, name="core_m"):
    sd = tmp_path / "slices"
    sd.mkdir(exist_ok=True)
    sl = dict(sl, type=name, module=name)
    (sd / f"{name}.json").write_text(json.dumps(sl))
    kd = tmp_path / "kit"
    kd.mkdir(exist_ok=True)
    (kd / "io.tcl").write_text("\n".join(io_lines) + "\n")
    (kd / "face_flops.tcl").write_text("# gpl hook\n")
    (kd / "config.mk").write_text(f"export DIE_AREA = 0 0 {sl['outline_um'][0]:g} {sl['outline_um'][1]:g}\n")
    MS.kit_apply(kd, name, sl["outline_um"], sd, None, False, kind=sl["kind"], gpl_hook=kd / "face_flops.tcl",
                 clock_ports=["clk"] if sl["kind"] == "core" else None)
    return kd


def _core_slice():
    sl = sample()
    sl["islands"] = [dict(name="clock_entry", rect_um=[427.68, 427.68, 436.32, 436.32], centre_um=[432, 432],
                          clock_pin=dict(layer="M5", xy_um=[432, 432]))]
    sl["keepouts"] = [dict(name="clock_entry_island", rect_um=[427.68, 427.68, 436.32, 436.32], kind="island",
                           use=["placement"])]
    return sl


def test_core_kit_consumes_clock_entry_and_passes_check(tmp_path):
    kd = _kit(tmp_path, _core_slice(), ["place_pin -pin_name {clk} -layer M4 -location {0.0160 100.0000} "
                                        "-pin_size {0.032 0.192}",
                                        "place_pin -pin_name {d[0]} -layer M4 -location {0.0160 110.0000}"])
    io = (kd / "io.tcl").read_text()  # clock centre snapped to the M5 track (GEOM-21, 51646a5c4d)
    assert "-pin_name {clk} -layer M5 -location {432.0120 432.0000}" in io and "{d[0]} -layer M4" in io
    # S81-CORE-LAT-R18: the core-infra step (runs after io.tcl) sets the SAME snapped full-width shape as io.tcl
    assert "ot_ci_clock_entry {clk} 432.0120 432.0000 0.048 0.48" in (kd / "master_core_infra.tcl").read_text()
    assert "placement blockage: keepout clock_entry_island" not in (kd / "master_slice.tcl").read_text()
    rep = MS.check_kit(kd)
    assert rep["verdict"] == "PASS", rep["issues"]
    assert rep["checks"]["pushdown"]["cells"] == 2


@pytest.mark.parametrize("tamper,frag", [
    (lambda kd: (kd / "io.tcl").write_text("place_pin -pin_name clk -layer M4 -location {0.016 100}\n"), "slice M5"),
    (lambda kd: (kd / "master_core_infra.tcl").write_text("ot_ci_begin\not_ci_finish\n"), "not generated"),
    (lambda kd: (kd / "config.mk").write_text("export DIE_AREA = 0 0 800 864\n"), "outline"),
    (lambda kd: (kd / "face_flops.tcl").write_text("# hook removed\n"), "sources /work/master_slice.tcl"),
])
def test_check_kit_catches_drift(tmp_path, tamper, frag):
    kd = _kit(tmp_path, _core_slice(), ["place_pin -pin_name {clk} -layer M4 -location {0.016 100}"])
    tamper(kd)
    rep = MS.check_kit(kd)
    assert rep["verdict"] == "FAIL" and any(frag in i for i in rep["issues"]), rep["issues"]


def test_check_kit_refuses_core_slice_without_pushdown(tmp_path):
    sl = _core_slice()
    sl.pop("pushdown")
    kd = _kit(tmp_path, sl, ["place_pin -pin_name {clk} -layer M4 -location {0.016 100}"])
    rep = MS.check_kit(kd)
    assert any("without pushdown" in i for i in rep["issues"])


def _partition_slice():
    sl = sample()
    sl["kind"] = "partition"
    sl.pop("core_clock_port")
    sl["pushdown"]["clock_repeaters"] = [dict(name="crep0", xy_um=[200.0, 200.0], cell="BUFx24_ASAP7_75t_R",
                                              rect_um=[197.84, 197.84, 202.16, 202.16],
                                              ft_ports=[dict(name="mp_crep0_i", dir="in", layer="M5",
                                                             xy_um=[200.0, 200.0]),
                                                        dict(name="mp_crep0_o", dir="out", layer="M5",
                                                             xy_um=[202.16, 200.0])])]
    sl["islands"] = [dict(name="island", rect_um=[427.68, 427.68, 436.32, 436.32], centre_um=[432, 432])]
    sl["keepouts"] = [dict(name="island", rect_um=[427.68, 427.68, 436.32, 436.32], kind="island", use=["placement"])]
    sl["bays"] = [dict(name="bay0", rect_um=[10, 10, 50, 20], kind="station", bits=64, layer="M7")]
    sl["entry_pins"] = [dict(name="ep0", pin="x_i[0]", layer="M7", xy_um=[30.0, 15.0], bay="bay0"),
                        dict(name="ep1", pin=None, layer="M7", xy_um=[32.0, 15.0], bay="bay0")]
    return sl


def test_partition_kit_pushdown_island_repeater_and_entry_pins(tmp_path):
    kd = _kit(tmp_path, _partition_slice(), ["place_pin -pin_name {x_i[0]} -layer M4 -location {0.016 15}"],
              name="part_t")
    plan = json.loads((kd / "core_infra_plan.json").read_text())
    assert {c["name"] for c in plan["cells"]} == {"mp_isl0_ck0", "mp_isl0_rst0", "mp_crep0"}
    assert plan["reserved_bays"][0]["name"] == "bay0" and plan["unbound_entry_pins"] == 1
    tcl = (kd / "master_slice.tcl").read_text()
    assert "placement blockage: island" not in tcl and "placement blockage: keepout island" not in tcl
    assert "ot_ci_entry {x_i[0]} 30 15" in (kd / "master_core_infra.tcl").read_text()
    assert "{x_i[0]} -layer M7 -location {30.0000 15.0000}" in (kd / "io.tcl").read_text()
    rep = MS.check_kit(kd)
    assert rep["verdict"] == "PASS", rep["issues"]


def _lattice(nx, ny, pitch, skew=0.0):
    sites, leaves = [], []
    for i in range(2 * nx + 1):
        for j in range(2 * ny + 1):
            xy = (i * pitch / 2 + (skew if (i, j) == (1, 1) else 0.0), j * pitch / 2)
            sites.append(dict(id=len(sites), xy=xy, role="clock_entry" if i % 2 and j % 2 else "die_node", inst=None))
            if i % 2 and j % 2:
                leaves.append(len(sites) - 1)
    return sites, leaves


def test_island_tree_symmetric_lattice_passes_on_islands():
    sites, leaves = _lattice(4, 4, 300.0)
    g, nodes = MP.island_tree(sites, leaves)
    assert g["verdict"] == "PASS", g["causes"]
    assert g["nodes_off_island"] == 0 and g["path_len_um"]["spread"] == 0
    assert g["leaves"] == 16 and g["internal_nodes"] == 15
    assert all(n["site"] is not None for n in nodes)


def test_island_tree_reports_asymmetry_and_leg_gaps():
    sites, leaves = _lattice(4, 4, 300.0, skew=60.0)
    g, _ = MP.island_tree(sites, leaves)
    assert g["verdict"] == "FAIL" and g["path_len_um"]["spread"] > 20 and "spread" in g["causes"][0]
    far = [dict(id=0, xy=(0.0, 0.0), role="clock_entry", inst=None),
           dict(id=1, xy=(2000.0, 0.0), role="clock_entry", inst=None),
           dict(id=2, xy=(1000.0, 0.0), role="die_node", inst=None)]
    g, _ = MP.island_tree(far, [0, 1])
    assert g["leg_repeater_gap_fails"] == 2 and g["verdict"] == "FAIL"


def _tree_slice():
    s = sample()
    s["core_tree"] = {"clock_port": "ck", "nodes": [
        dict(name="root", master="BUFx16f_ASAP7_75t_R", xy_um=[430, 430], parent="port:ck"),
        dict(name="n0", master="BUFx8_ASAP7_75t_R", xy_um=[200, 200], parent="root"),
        dict(name="n1", master="BUFx8_ASAP7_75t_R", xy_um=[600, 600], parent="root")],
        "leaves": [dict(node="n0", sinks=["u0/CLK", "u1/CLK"]), dict(node="n1", sinks=["u2/CLK", "u3/CLK"])]}
    return s


def test_core_trunk_refused_without_pg_model_and_over_sram_pg():
    s = _tree_slice()
    with pytest.raises(CI.InfraError, match="NOT RUN"):
        CI.emit_tcl(s)
    # an SRAM M5 PG stripe column blocking the vertical leg of both L routes root -> n1 (x 590..610, y 300..700)
    # and the M4 horizontal at y 600 / y 430: both orientations blocked -> refused
    s["pg_obstructions_um"] = {"M5": [[590, 300, 610, 700], [425, 300, 435, 700]], "M4": []}
    with pytest.raises(CI.InfraError, match="PG clearance FAIL"):
        CI.emit_tcl(s)
    s["pg_obstructions_um"] = {"M5": [[590, 300, 610, 700]], "M4": []}   # route via x=430 vertical is clear
    assert "ot_ci_tree_begin" in CI.emit_tcl(s)
    assert CI.trunk_pg_clearance(s, CI.compile_slice(s))["verdict"] == "PASS"


# ---------------------------------------------------------------- S81-CORE-LAT-R18: every clock-pin setter checked
def test_core_infra_clock_entry_is_snapped_full_shape_from_kit_tracks(tmp_path):
    """The shared core-infra emitter uses the io step's snap (kit make_tracks.tcl + DIE_AREA origin) and size."""
    sl = _core_slice()
    plan = CI.compile_slice(sl)
    assert CI.clock_entry_shape(plan) == (432.012, 432.0, 0.048, 0.48)          # ASAP7 platform M5 grid
    kd = tmp_path / "k"
    kd.mkdir()
    (kd / "make_tracks.tcl").write_text("make_tracks M5 -x_offset 0.036 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048\n")
    assert CI.clock_entry_shape(plan, kd)[:2] == MS.snap_on_track(kd, "M5", 432, 432) == (431.988, 432.0)
    assert "ot_ci_clock_entry {clk} 431.9880 432.0000 0.048 0.48" in CI.emit_tcl(sl, kd)


def test_check_kit_fails_unsnapped_core_infra_clock_entry(tmp_path):
    """The qbank/sstn c16 form: io.tcl snapped, master_core_infra.tcl re-places the pin at the unsnapped plan centre
    with the small shape.  The old check_kit compared master_core_infra.tcl to the (old) emitter and only looked at
    io.tcl -> PASS; now every clock-pin setter is checked."""
    kd = _kit(tmp_path, _core_slice(), ["place_pin -pin_name {clk} -layer M4 -location {0.0160 100.0000} "
                                        "-pin_size {0.032 0.192}"])
    rep = MS.check_kit(kd)
    assert rep["verdict"] == "PASS", rep["issues"]
    assert [c.split()[1] for c in rep["checks"]["slice_pins"]["clock_settings"]] == ["place_pin", "ot_ci_clock_entry"]
    f = kd / "master_core_infra.tcl"
    good = f.read_text()
    f.write_text(good.replace("ot_ci_clock_entry {clk} 432.0120 432.0000 0.048 0.48", "ot_ci_clock_entry {clk} 432 432"))
    iss = MS.check_kit(kd)["issues"]
    assert any("master_core_infra.tcl" in i and "off the M5 routing track" in i for i in iss), iss
    assert any("master_core_infra.tcl" in i and "pin_size" in i for i in iss), iss
    assert any("different shapes" in i for i in iss), iss
    # a third setter anywhere in the kit (also in owned files) is seen too
    f.write_text(good)
    (kd / "extra_hook.tcl").write_text("place_pin -pin_name clk -layer M5 -location {432.0120 432.0000} -pin_size {0.032 0.192}\n")
    iss = MS.check_kit(kd)["issues"]
    assert any("extra_hook.tcl" in i and "pin_size" in i for i in iss), iss


def test_core_infra_tcl_clock_entry_refuses_small_or_off_track(tmp_path):
    import subprocess
    from pathlib import Path
    stub = """
namespace eval ord { proc get_db_tech {} { return ftech } }
proc ftech {cmd args} { return fM5 }
proc fblk {cmd args} { switch -- $cmd { findBTerm { return fbt } findTrackGrid { return ftg } } }
proc fbt {cmd args} { return INPUT }
proc ftg {cmd args} { return {12 60 108} }
proc place_pin {args} { puts "PLACED $args" }
set ::ot_ci_b fblk; set ::ot_ci_u 1000
foreach c {{clk 0.060 1 0.048 0.48} {clk 0.048 1 0.048 0.48} {clk 0.060 1 0.032 0.192} {clk 0.060 1}} {
  if {[catch {ot_ci_clock_entry {*}$c} e]} { puts "ERR $e" }
}
"""
    lib = Path(CI.__file__).with_suffix(".tcl").read_text()
    p = subprocess.run(["tclsh"], input=lib + stub, text=True, capture_output=True)
    out = p.stdout.splitlines()
    assert out[0] == "PLACED -pin_name clk -layer M5 -location {0.060 1} -pin_size {0.048 0.48}", p.stdout + p.stderr
    assert out[1].startswith("ERR OT_CORE_INFRA_CLOCK_ENTRY_OFF_TRACK")
    assert out[2].startswith("ERR OT_CORE_INFRA_CLOCK_ENTRY_SIZE")
    assert out[3].startswith("ERR wrong # args")
