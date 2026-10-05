import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41_engram_campaign as campaign  # noqa: E402


def test_engram_tables_are_generated_from_the_golden():
    assert campaign.emit_tables() == campaign.TABLES.read_text()


def test_committed_record_is_current_and_passes():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    for unit in ("fdiv", "fsqrt"):
        assert record[unit]["mismatches"] == 0 and record[unit]["checked"] == record[unit]["operands"]
    assert record["fsqrt"]["qualified_equivalence"]["mismatches"] == 0
    for unit, count in (("engram_hash", "positions"), ("softplus", "arguments")):
        for sim in ("verilator", "icarus"):
            run = record[unit][sim]
            assert run["errors"] == 0 and run["checked"] == record[unit][count], (unit, sim)
    assert record["softplus"]["router_arguments"] > 0
    assert record["engram_hash"]["positions_by_stream"]["oracle_workload"] > 0
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_physical_records_close_at_one_gigahertz_on_the_campaign_sources():
    record = json.loads(campaign.OUT.read_text())
    for top in ("ot_hdc_engram_hash", "ot_hdc_softplus"):
        phys = json.loads((ROOT / f"results/physical_abi3/asap7/hdc/v41/{top}/physical.json").read_text())
        design = phys["design"]
        assert design["top"] == top
        assert design["closed"] is True and phys["acceptance"]["status"] == "pass", top
        assert design["fmax_hz"] >= 1e9 and design["clock_period_ns"] <= 1.0, top
        for src in design["sources"]:
            assert src["path"] in record["input_sha256"], (top, src["path"])
            assert src["sha256"] == record["input_sha256"][src["path"]], (top, src["path"])
