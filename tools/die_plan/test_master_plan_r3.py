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
    io = (kd / "io.tcl").read_text()
    assert "-pin_name {clk} -layer M5 -location {432.0000 432.0000}" in io and "{d[0]} -layer M4" in io
    assert "ot_ci_clock_entry {clk} 432 432" in (kd / "master_core_infra.tcl").read_text()
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
