"""The ROM array's communication engines: the committed campaign record is current,
passes, and was bit exact on the golden's real MoE traces; the routed records close
at 1 GHz on the campaign's own sources."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "results/rtl/rom_collectives_campaign.json"
PHYS = ROOT / "results/physical_abi3/asap7/rom/collectives"


def _record():
    return json.loads(RECORD.read_text())


def test_record_is_current():
    record = _record()
    assert record["input_sha256"], "no inputs recorded"
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_every_case_passes_and_the_golden_traces_were_checked():
    record = _record()
    assert record["status"] == "pass"
    assert all(c["pass"] for c in record["moe_cases"])
    for c in record["moe_cases"]:
        assert c["moe_mismatches"] == 0 and c["done"] == c["tokens"] and c["chunks_checked"] == 5 * c["tokens"]
        assert c["expert_side_errors"] == 0 and c["actquant_mismatches"] == 0
    real = [c for c in record["moe_cases"] if c["trace"] == "real"]
    assert real and all(c["tokens"] == record["traces"]["real_moe_instances"] for c in real)
    assert record["traces"]["real_moe_instances"] == record["traces"]["real_positions"] * 40
    # both dispatch modes, back-pressure and starved credits were exercised
    builds = {c["build"] for c in record["moe_cases"]}
    assert {"multicast", "unicast", "multicast_credits8"} <= builds
    assert any(c["up_credit_stalls"] + c["down_credit_stalls"] > 0 for c in record["moe_cases"])
    # the tensor group's one-shot all-reduce through the fabric router: four identical replicas
    assert record["tensor_allreduce_cases"]
    for c in record["tensor_allreduce_cases"]:
        assert c["pass"] and c["errors"] == 0 and c["replicas_checked"] == 4 * c["reductions"] > 0
    assert "rtl/rom/ot_rom_fabric_router.sv" in record["input_sha256"]
    for c in record["kv_argmax_cases"]:
        assert c["kv"]["pass"] and c["argmax"]["pass"]
        assert c["kv"]["deliveries"] == c["kv"]["expected_deliveries"] > 0


def test_summary_figures_follow_from_the_cases():
    record = _record()
    s = record["summary"]
    sus = next(c for c in record["moe_cases"] if c["build"] == "multicast" and c["label"] == "real_sustained")
    assert s["sustained_cycles_per_token_real"] == sus["steady_cycles_per_token"]
    # the combine's single input port is the bound: one flit per cycle, 7 results of 1 + 5 flits
    assert s["combine_ingest_bound_cycles_per_token"] == 42
    assert s["sustained_cycles_per_token_real"] < 1.1 * s["combine_ingest_bound_cycles_per_token"]
    assert s["dispatch_control_bubbles_multicast_unstressed"] == 0
    assert s["dispatch_flits_per_token_multicast"] == 4.0


def test_routed_records_close_at_one_gigahertz_on_the_campaign_sources():
    record = _record()
    tops = sorted(p.name for p in PHYS.iterdir() if (p / "physical.json").exists())
    assert {"ot_rom_moe_dispatch", "ot_rom_moe_expert_port", "ot_rom_moe_combine", "ot_rom_mcast_node",
            "ot_rom_argmax_reduce"} <= set(tops)
    for name in tops:
        phys = json.loads((PHYS / name / "physical.json").read_text())
        design = phys["design"]
        assert design["closed"] is True and phys["acceptance"]["status"] == "pass", name
        assert design["fmax_hz"] >= 1e9 and design["clock_period_ns"] <= 1.0, name
        for src in design["sources"]:
            assert src["path"] in record["input_sha256"], (name, src["path"])
            assert src["sha256"] == record["input_sha256"][src["path"]], (name, src["path"])
