"""Explicit floorplan, pin edges and routing layers in the physical driver.

``--die-area``/``--core-area``, ``--pin-region REGEX=EDGE`` and
``--routing-layers MIN MAX`` exist so a long repeated wire (the ROM wafer's
express link, rtl/rom/ot_rom_express_link.sv) can be routed on a long, thin
die with its two ends pinned to opposite edges.  Without them the config.mk
must stay byte-for-byte what every earlier record was routed with.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_abi3_physical as flow  # noqa: E402

BLOCK = {
    "top": "ot_rom_express_link",
    "sources": ["rtl/rom/ot_rom_express_link.sv"],
    "parameters": {"W": 64},
    "clock_port": "clk",
    "false_path_from_ports": ["rst_n"],
}
PNR = {"corner_env": "TC", "extra_config": {"ASAP7_USE_VT": "RVT"}}


def _config(floorplan):
    return flow.orfs_config_lines("n", BLOCK, "asap7", PNR, 35, 0.6, None, None, floorplan)


def test_default_config_is_unchanged():
    lines = _config(None)
    assert lines == flow.orfs_config_lines("n", BLOCK, "asap7", PNR, 35, 0.6)
    assert "export CORE_UTILIZATION = 35" in lines
    assert "export CORE_ASPECT_RATIO = 1" in lines
    assert "export CORE_MARGIN = 2" in lines
    assert not any("DIE_AREA" in l or "IO_CONSTRAINTS" in l or "ROUTING_LAYER" in l for l in lines)
    assert flow.resolve_floorplan(None, None, None, None) is None


def test_explicit_area_replaces_utilisation():
    fp = flow.resolve_floorplan([0, 0, 1004, 40], [2, 2, 1002, 38], None, None)
    lines = _config(fp)
    assert "export DIE_AREA = 0 0 1004 40" in lines
    assert "export CORE_AREA = 2 2 1002 38" in lines
    # ORFS refuses more than one floorplan initialisation method.
    assert not any(l.startswith("export CORE_UTILIZATION") for l in lines)
    assert not any(l.startswith("export CORE_ASPECT_RATIO") for l in lines)


def test_pin_regions_and_layers():
    fp = flow.resolve_floorplan(None, None, ["^in_=left", "^(out|local)_=right"], ["M2", "M9"])
    lines = _config(fp)
    assert "export IO_CONSTRAINTS = /work/io_constraints.tcl" in lines
    assert "export MIN_ROUTING_LAYER = M2" in lines
    assert "export MAX_ROUTING_LAYER = M9" in lines
    tcl = flow.io_constraints_tcl(fp["pin_regions"])
    assert "set_io_pin_constraint -group -order -region left:* -pin_names [ot_match_pins {^in_}]" in tcl
    assert "-region right:* -pin_names [ot_match_pins {^(out|local)_}]" in tcl


@pytest.mark.parametrize(
    "die, core, pins",
    [
        ([0, 0, 10, 10], None, None),                 # die without core
        ([0, 0, 10, 10], [2, 2, 12, 8], None),        # core outside die
        ([0, 0, 10, 10], [5, 2, 4, 8], None),         # inverted core
        (None, None, ["^in_=north"]),                 # unknown edge
        (None, None, ["left"]),                       # no regex
    ],
)
def test_invalid_floorplan_refused(die, core, pins):
    with pytest.raises(ValueError):
        flow.resolve_floorplan(die, core, pins, None)


def test_floorplan_options_need_pnr(tmp_path):
    argv = [
        "--view", "asap7", "--top", "ot_rom_express_link",
        "--source", "rtl/rom/ot_rom_express_link.sv",
        "--clock-period-ns", "1.0", "--stages", "synth",
        "--pin-region", "^in_=left",
        "--output", str(tmp_path / "x.json"),
    ]
    assert flow.main(argv) == 2
    assert not (tmp_path / "x.json").exists()


def test_step_tcl_hook_is_emitted_and_hashed():
    fp = flow.resolve_floorplan(
        None, None, None, None, ["POST_PDN=tools/rom_express_link_place.tcl"]
    )
    hook = fp["step_tcl"][0]
    assert hook["hook"] == "POST_PDN"
    assert len(hook["sha256"]) == 64
    assert "export POST_PDN_TCL = /work/hooks/post_pdn_rom_express_link_place.tcl" in _config(fp)
    with pytest.raises(ValueError):
        flow.resolve_floorplan(None, None, None, None, ["PDN=tools/rom_express_link_place.tcl"])
    with pytest.raises(ValueError):
        flow.resolve_floorplan(None, None, None, None, ["POST_PDN=tools/no_such_hook.tcl"])
