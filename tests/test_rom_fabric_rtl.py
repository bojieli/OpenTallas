import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_array_campaign as array  # noqa: E402
import rtl_rom_fabric_campaign as fabric  # noqa: E402

PHYS = ROOT / "results/physical_abi3/asap7/rom"


def _current(record):
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_router_record_is_current_and_passes():
    record = json.loads(fabric.OUT.read_text())
    assert record["status"] == "pass"
    assert all(v["returncode"] == 0 for k, v in record["verilator_lint"].items() if k != "flags")
    runs = record["router_random_traffic"]
    assert len(runs) == len(fabric.RUNS)
    for run in runs:
        assert run["pass"] and run["errors"] == 0, run
        assert run["multicast_packets"] > 0 and run["dropped_packets"] > 0, run
    assert {512} <= {run["flit_bits"] for run in runs}
    _current(record)


def test_array_record_covers_the_rtl_controller_switch_and_multicast():
    record = json.loads(array.OUT.read_text())
    assert record["status"] == "pass"
    for name in ("rtl/rom/ot_rom_pkg_ctrl.sv", "rtl/rom/ot_rom_fabric_router.sv"):
        assert name in record["input_sha256"]
    cfgs = record["configurations"]
    for cfg in cfgs:
        assert cfg["pass"] and cfg["mismatches"] == 0, cfg["packages"]
        assert cfg["generated_tokens"] == 3 * cfg["users"] and cfg["users_completed"] == cfg["users"]
    assert any(c["lm_head_multicast"] for c in cfgs)
    assert any(c["stall_percent"] > 0 and c["users"] > c["packages"] for c in cfgs)
    # a one-user multicast step is shorter than the chained one
    for e in record["multicast_effect"]:
        if e["users"] == 1:
            assert e["switch_multicast_cycles"] < e["switch_chain_cycles"], e
    _current(record)


def test_physical_records_route_the_campaign_sources():
    record = json.loads(fabric.OUT.read_text())
    for top in ("ot_rom_fabric_router", "ot_rom_pkg_ctrl"):
        phys = json.loads((PHYS / top / "physical.json").read_text())
        design = phys["design"]
        assert design["top"] == top and "pnr" in phys["stages_completed"], top
        assert design["clock_period_ns"] <= 1.0 and design["drc"] == 0, top
        for src in design["sources"]:
            assert src["sha256"] == record["input_sha256"][src["path"]], (top, src["path"])
        # text reports only: no netlists committed
        assert not list((PHYS / top).rglob("*.v")), top
