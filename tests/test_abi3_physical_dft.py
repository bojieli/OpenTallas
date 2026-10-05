"""``--dft scan`` in the physical driver: off by default, config unchanged.

Scan is inserted between ORFS synthesis and floorplan, so the only flow input
it can change is the netlist; the config.mk and SDC of a route without
``--dft`` must stay byte-for-byte what every earlier record was routed with,
and a scanned route gets its own DESIGN_NICKNAME so it never shares the ORFS
results namespace with an unscanned route of the same top.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_abi3_physical as flow  # noqa: E402

BLOCK = {
    "top": "ot_rom_pkg_ctrl",
    "sources": ["rtl/rom/ot_rom_pkg_ctrl.sv"],
    "parameters": {},
    "clock_port": "clk",
    "false_path_from_ports": ["rst_n"],
}
PNR = {"corner_env": "TC", "extra_config": {"ASAP7_USE_VT": "RVT"}}


def test_default_is_no_dft():
    assert flow.resolve_dft(None, None, None, None) is None
    assert flow.resolve_dft("none", None, None, None) is None
    args = flow.build_parser().parse_args(
        ["--view", "asap7", "--top", "t", "--source", "x.sv", "--clock-period-ns", "1", "--output", "o.json"]
    )
    assert args.dft is None and args.scan_chains is None and args.scan_max_length is None


def test_scan_configuration():
    assert flow.resolve_dft("scan", None, None, None) == {
        "mode": "scan", "chains": 1, "max_length": None, "clock_mixing": "no_mix"
    }
    assert flow.resolve_dft("scan", 8, None, "mix")["chains"] == 8
    cfg = flow.resolve_dft("scan", None, 512, None)
    assert cfg["chains"] is None and cfg["max_length"] == 512


@pytest.mark.parametrize("bad", [(None, 4, None, None), ("scan", 0, None, None), ("scan", None, 0, None)])
def test_scan_options_are_checked(bad):
    with pytest.raises(ValueError):
        flow.resolve_dft(*bad)


def test_config_is_unchanged_by_the_option():
    # the config.mk never mentions DFT: scan lives in the netlist only
    lines = flow.orfs_config_lines("n", BLOCK, "asap7", PNR, 35, 0.6)
    assert not any("SCAN" in l or "DFT" in l for l in lines)


def test_dft_requires_pnr(tmp_path):
    rc = flow.main([
        "--view", "asap7", "--top", "ot_rom_pkg_ctrl", "--source", "rtl/rom/ot_rom_pkg_ctrl.sv",
        "--clock-period-ns", "1", "--stages", "synth", "--dft", "scan",
        "--output", str(tmp_path / "o.json"),
    ])
    assert rc == 2


def test_dft_only_on_supported_views(tmp_path):
    rc = flow.main([
        "--view", "sky130hd", "--top", "ot_rom_pkg_ctrl", "--source", "rtl/rom/ot_rom_pkg_ctrl.sv",
        "--clock-period-ns", "1", "--stages", "pnr", "--dft", "scan",
        "--output", str(tmp_path / "o.json"),
    ])
    assert rc == 2
