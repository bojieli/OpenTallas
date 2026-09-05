"""Platform memory macros in the physical driver's place-and-route lane.

Gate G2 (docs/OPENTALLAS_REDESIGN_PLAN.md) wants the memory system present in
the routed netlist as placed macros, and every record to date has macro_count
0: the driver could count macros but had no way to supply one.
``--memory-macro`` names a macro the place-and-route platform itself ships and
emits the ADDITIONAL_LEFS / ADDITIONAL_LIBS / SYNTH_BLACKBOXES lines ORFS's own
macro-bearing designs use; ``--macro-place-halo`` overrides the platform's
MACRO_PLACE_HALO.  None of it may change what a run without the options
produces -- the config.mk of every earlier routed record must stay
byte-identical, which is asserted here against the recorded artifact hashes --
and none of it may touch the closure rule.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_abi3_physical as flow  # noqa: E402

RECORDS = sorted((ROOT / "results/physical_abi3").glob("*/*/pnr.json"))

LANE_BLOCK = {
    "top": "ot_a3_lane_pipelined",
    "sources": [
        "rtl/ot_fp32_rne_pkg.sv",
        "rtl/abi3/ot_a3_lane_pkg.sv",
        "rtl/abi3/ot_a3_lane_pipelined.sv",
    ],
    "parameters": {"ADDER_STAGES": 3, "ACC_SLOTS": 8},
    "clock_port": "clk",
    "false_path_from_ports": ["rst_n"],
}

BASE_ARGV = ["--view", "asap7", "--clock-period-ns", "6.0", "--output", "x.json"]

# A resolved macro block of the shape resolve_memory_macros returns, so the
# emission and recording can be checked without the container.
FAKE_MACRO = {
    "platform": "asap7",
    "requested": ["fakeram_512x8"],
    "macros": [
        {
            "name": "fakeram_512x8",
            "lef": {"path": "/platforms/asap7/lef/fakeram_512x8.lef", "sha256": "a" * 64},
            "lib": {"path": "/platforms/asap7/lib/NLDM/fakeram_512x8.lib", "sha256": "b" * 64},
            "capacity_bits": 4096,
            "footprint": {"width_um": 4.18, "height_um": 42.0, "area_um2": 175.56},
        }
    ],
    "additional_lefs": ["/platforms/asap7/lef/fakeram_512x8.lef"],
    "additional_libs": ["/platforms/asap7/lib/NLDM/fakeram_512x8.lib"],
    "synth_blackboxes": ["fakeram_512x8"],
    "macro_place_halo": {"x_um": 10.0, "y_um": 10.0, "source": "platform default", "emitted_in_config": False},
}


def _with_halo(x: float, y: float) -> dict:
    block = json.loads(json.dumps(FAKE_MACRO))
    block["macro_place_halo"] = {
        "x_um": x, "y_um": y, "source": "command line", "emitted_in_config": True,
    }
    return block


def _asap7() -> tuple[dict, dict]:
    view = flow.VIEWS["asap7"]
    return view, view["corners"]["TT"]


def _docker_image_present() -> bool:
    proc = flow.run(["docker", "image", "inspect", flow.ORFS_IMAGE, "--format", "{{.Id}}"], timeout=300)
    return proc.returncode == 0


IMAGE_PRESENT = _docker_image_present()


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------


def test_macro_options_are_absent_unless_given():
    args = flow.build_parser().parse_args(BASE_ARGV)
    assert args.memory_macro == []
    assert args.macro_place_halo is None


def test_macro_options_parse():
    args = flow.build_parser().parse_args(
        BASE_ARGV
        + ["--memory-macro", "fakeram_512x8", "--memory-macro", "fakeram_256x64",
           "--macro-place-halo", "6", "8.5"]
    )
    assert args.memory_macro == ["fakeram_512x8", "fakeram_256x64"]
    assert args.macro_place_halo == [6.0, 8.5]


def test_halo_alone_places_nothing_and_is_refused():
    view, _ = _asap7()
    with pytest.raises(flow.FlowError):
        flow.resolve_memory_macros("asap7", view, [], [6.0, 6.0])
    assert flow.resolve_memory_macros("asap7", view, [], None) is None


def test_macro_names_that_are_not_platform_macro_names_are_refused():
    view, _ = _asap7()
    for bad in ("../../etc/passwd", "fakeram 512x8", "fakeram;rm -rf /", "-fakeram", ""):
        with pytest.raises(flow.FlowError):
            flow.resolve_memory_macros("asap7", view, [bad], None)


def test_a_view_without_place_and_route_has_no_macros():
    view = dict(flow.VIEWS["asap7"])
    view["pnr"] = None
    with pytest.raises(flow.FlowError):
        flow.resolve_memory_macros("asap7", view, ["fakeram_512x8"], None)


# --------------------------------------------------------------------------
# The config.mk without the options is byte-for-byte what every record had
# --------------------------------------------------------------------------


def test_no_macro_lines_without_the_option():
    view, _ = _asap7()
    lines = flow.orfs_config_lines("nick", LANE_BLOCK, "asap7", view["pnr"], 35, 0.6)
    assert not any(
        line.startswith(("export ADDITIONAL_LEFS", "export ADDITIONAL_LIBS",
                         "export SYNTH_BLACKBOXES", "export MACRO_PLACE_HALO"))
        for line in lines
    )
    assert flow.memory_macro_config_lines(None) == []


@pytest.mark.skipif(not RECORDS, reason="no routed records present")
def test_every_routed_record_config_mk_is_still_reproduced_byte_for_byte():
    """The recorded config.mk hash of each earlier route, rebuilt by this driver."""
    checked = 0
    for path in RECORDS:
        record = json.loads(path.read_text(encoding="utf-8"))
        pnr = record.get("place_and_route")
        if not pnr:
            continue
        artifact = pnr.get("artifacts", {}).get("config.mk")
        if not artifact:
            continue
        design = record["design"]
        block = {
            "top": design["top"],
            "sources": [entry["path"] for entry in design["sources"]],
            "parameters": design["parameters"],
            "clock_port": design["clock_port"],
            "false_path_from_ports": design["false_path_from_ports"],
        }
        view = flow.VIEWS[record["view"]["name"]]
        lines = flow.orfs_config_lines(
            pnr["design_nickname"],
            block,
            pnr["platform"],
            view["pnr"],
            pnr["core_utilization_percent"],
            pnr["place_density"],
            pnr.get("signal_integrity_constraints"),
            # A record that named memory macros carries their lines in its own
            # config.mk, so the rebuild must be handed them back.  Passing None
            # here would have silently exempted every macro-bearing record from
            # the only test that binds a config.mk to its hash -- and the first
            # such record (asap7/a3_g2_cluster) would have failed instead of
            # being checked.
            pnr.get("memory_macros"),
        )
        text = "\n".join(lines) + "\n"
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == artifact["sha256"], path
        assert pnr.get("memory_macros") is None or pnr["metrics"].get("macro_count")
        checked += 1
    assert checked >= 1


# --------------------------------------------------------------------------
# What the macro option emits
# --------------------------------------------------------------------------


def test_macro_lines_are_the_orfs_mechanism_and_come_last():
    view, _ = _asap7()
    lines = flow.orfs_config_lines("nick", LANE_BLOCK, "asap7", view["pnr"], 35, 0.6, None, FAKE_MACRO)
    assert lines[-3:] == [
        "export ADDITIONAL_LEFS = /platforms/asap7/lef/fakeram_512x8.lef",
        "export ADDITIONAL_LIBS = /platforms/asap7/lib/NLDM/fakeram_512x8.lib",
        "export SYNTH_BLACKBOXES = fakeram_512x8",
    ]
    # The platform default halo is recorded but never emitted.
    assert not any(line.startswith("export MACRO_PLACE_HALO") for line in lines)
    # Everything before the macro lines is the config every earlier record had.
    assert lines[:-3] == flow.orfs_config_lines("nick", LANE_BLOCK, "asap7", view["pnr"], 35, 0.6)


def test_an_overridden_halo_is_emitted_and_the_platform_default_is_not():
    lines = flow.memory_macro_config_lines(_with_halo(6.0, 8.5))
    assert lines[-1] == "export MACRO_PLACE_HALO = 6 8.5"
    assert flow.memory_macro_config_lines(FAKE_MACRO)[-1] == "export SYNTH_BLACKBOXES = fakeram_512x8"


def test_two_macros_share_one_line_each():
    block = json.loads(json.dumps(FAKE_MACRO))
    block["additional_lefs"].append("/platforms/asap7/lef/fakeram_256x64.lef")
    block["additional_libs"].append("/platforms/asap7/lib/NLDM/fakeram_256x64.lib")
    block["synth_blackboxes"].append("fakeram_256x64")
    lines = flow.memory_macro_config_lines(block)
    assert lines[0].endswith("fakeram_512x8.lef /platforms/asap7/lef/fakeram_256x64.lef")
    assert lines[2] == "export SYNTH_BLACKBOXES = fakeram_512x8 fakeram_256x64"


def test_the_sdc_is_untouched_by_macros():
    # The macro views are a config.mk matter: sdc_text takes no macro argument
    # at all, so a macro-bearing route is constrained by the SDC it would have
    # had without one.
    assert "macro" not in " ".join(inspect.signature(flow.sdc_text).parameters)
    view, _ = _asap7()
    text = flow.sdc_text(view, LANE_BLOCK, 6.0, None)
    assert "fakeram" not in text and "MACRO" not in text and "LEF" not in text


def test_capacity_is_read_from_the_views_and_says_which_one():
    bits, source = flow.macro_capacity({"lef_property_depth": 512, "lef_property_width": 8})
    assert bits == 4096 and source.startswith("LEF PROPERTY")
    bits, source = flow.macro_capacity({"liberty_address_width": 9, "liberty_word_width": 8})
    assert bits == 4096 and source.startswith("liberty memory()")
    bits, source = flow.macro_capacity({})
    assert bits is None and "neither" in source


# --------------------------------------------------------------------------
# Resolution against the pinned image's own platform files
# --------------------------------------------------------------------------


@pytest.mark.skipif(not IMAGE_PRESENT, reason="pinned ORFS image not present")
def test_asap7_macro_resolves_to_the_platforms_own_views():
    view, _ = _asap7()
    block = flow.resolve_memory_macros("asap7", view, ["fakeram_512x8"], None)
    assert block["platform"] == "asap7"
    macro = block["macros"][0]
    assert macro["name"] == "fakeram_512x8"
    # The identity is the platform's: paths inside the image, nothing copied.
    assert macro["lef"]["path"] == "/OpenROAD-flow-scripts/flow/platforms/asap7/lef/fakeram_512x8.lef"
    assert macro["lib"]["path"].startswith("/OpenROAD-flow-scripts/flow/platforms/asap7/lib/")
    assert len(macro["lef"]["sha256"]) == 64 and len(macro["lib"]["sha256"]) == 64
    # docs/CHIP_ARCHITECTURE_DESIGN.md section 11.2: 4,096 bits, 4.18 x 42.00 um.
    assert macro["capacity_bits"] == 4096
    assert macro["capacity_bytes"] == 512.0
    assert (macro["footprint"]["width_um"], macro["footprint"]["height_um"]) == (4.18, 42.0)
    assert macro["lef_class"] == "BLOCK"
    assert macro["liberty"]["address_width"] == 9 and macro["liberty"]["word_width"] == 8
    # The macro liberty is in its own units, and the record says so rather
    # than quietly reporting one model's number under another's.
    assert macro["liberty"]["time_unit_matches_standard_cells"] is False
    assert block["capacity_bits_total"] == 4096
    assert block["config_lines"] == flow.memory_macro_config_lines(block)


@pytest.mark.skipif(not IMAGE_PRESENT, reason="pinned ORFS image not present")
def test_the_platform_default_halo_is_recorded_with_its_source():
    view, _ = _asap7()
    block = flow.resolve_memory_macros("asap7", view, ["fakeram_512x8"], None)
    halo = block["macro_place_halo"]
    assert (halo["x_um"], halo["y_um"]) == (10.0, 10.0)
    assert halo["emitted_in_config"] is False
    assert "platforms/asap7/config.mk" in halo["source"]
    assert "MACRO_PLACE_HALO" in halo["source"]

    overridden = flow.resolve_memory_macros("asap7", view, ["fakeram_512x8"], [6.0, 8.5])
    assert overridden["macro_place_halo"] == {
        "x_um": 6.0,
        "y_um": 8.5,
        "source": "command line",
        "emitted_in_config": True,
        "used_by": halo["used_by"],
    }
    assert "export MACRO_PLACE_HALO = 6 8.5" in overridden["config_lines"]


@pytest.mark.skipif(not IMAGE_PRESENT, reason="pinned ORFS image not present")
def test_an_unknown_macro_fails_and_names_what_the_platform_offers():
    view, _ = _asap7()
    with pytest.raises(flow.FlowError) as excinfo:
        flow.resolve_memory_macros("asap7", view, ["fakeram_9999x9999"], None)
    message = str(excinfo.value)
    assert "fakeram_9999x9999" in message
    assert "fakeram_512x8" in message


@pytest.mark.skipif(not IMAGE_PRESENT, reason="pinned ORFS image not present")
def test_sky130hd_has_no_ram_view_so_a_macro_route_is_refused_not_faked():
    view = flow.VIEWS["sky130hd"]
    with pytest.raises(flow.FlowError) as excinfo:
        flow.resolve_memory_macros("sky130hd", view, ["fakeram_512x8"], None)
    assert "fakeram_512x8" in str(excinfo.value)


# --------------------------------------------------------------------------
# The driver refuses what it cannot do, and the closure rule is untouched
# --------------------------------------------------------------------------


def test_host_stages_cannot_see_container_macros(tmp_path, capsys):
    original = flow.ROOT
    try:
        pinned = tmp_path / "pinned"
        (pinned / "rtl").mkdir(parents=True)
        (pinned / "rtl/a.sv").write_text("module a(); endmodule\n", encoding="utf-8")
        code = flow.main([
            "--view", "asap7", "--clock-period-ns", "2.0", "--stages", "synth,sta,pnr",
            "--top", "a", "--source", "rtl/a.sv", "--memory-macro", "fakeram_512x8",
            "--source-root", str(pinned), "--output", str(tmp_path / "out.json"),
        ])
        assert code == 2
        assert "--memory-macro is a place-and-route option" in capsys.readouterr().err
        assert not (tmp_path / "out.json").exists()
    finally:
        flow.ROOT = original


def _routed_record(macro_count: int, drc: int, memory_macros: dict | None) -> dict:
    metrics = {
        "setup_wns_ns": 1.0, "hold_wns_ns": 0.1, "drc_errors": drc,
        "antenna_violating_nets": 0, "antenna_violating_pins": 0,
        "max_slew_violations": 0, "max_cap_violations": 0, "max_fanout_violations": 0,
        "fmax_hz": 1e8, "standard_cell_count": 365, "standard_cell_area_um2": 1.0,
        "core_area_um2": 2.0, "utilization_fraction": 0.5, "macro_count": macro_count,
    }
    pnr = {"metrics": metrics, "clock_period_ns": 2.0}
    if memory_macros:
        pnr["memory_macros"] = memory_macros
    status = flow.STATUS_PASS if drc == 0 else flow.STATUS_NOT_MET
    return {"status": status, "place_and_route": pnr, "design": {}}


def test_macros_do_not_change_the_closure_rule():
    clean = _routed_record(1, 0, FAKE_MACRO)
    flow.augment_design(clean, lanes=None, mac_per_cycle=None, evidence=[], lane_regex=None, netlists=[])
    assert clean["design"]["closed"] is True

    # A placed macro does not excuse a dirty route.
    dirty = _routed_record(1, 3, FAKE_MACRO)
    flow.augment_design(dirty, lanes=None, mac_per_cycle=None, evidence=[], lane_regex=None, netlists=[])
    assert dirty["design"]["closed"] is False

    # And no macro does not stop a clean one closing, as before.
    macroless = _routed_record(0, 0, None)
    flow.augment_design(macroless, lanes=None, mac_per_cycle=None, evidence=[], lane_regex=None, netlists=[])
    assert macroless["design"]["closed"] is True
    assert macroless["place_and_route"].get("memory_macros") is None
