"""Gate C7 step K3 (ported from v41-rack-gates 36bc14e2 / 965f07d8): the plesiochronous package-link crossing
rtl/rom/ot_rom_link_cdc.sv passes its two-clock Verilator bench -- every flit once and in order at 0 / +-100 /
+-200 ppm with zero overflow, and the negative case (idle insertion too sparse for the offset) latches overflow."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/v41_link_cdc_campaign.json"


def rec():
    return json.loads(REC.read_text())


def test_sources_are_on_this_tree():
    r = rec()
    assert r["tool"] == "tools/rtl_v41_link_cdc_campaign.py" and (ROOT / r["tool"]).exists()
    for s in r["sources"]:
        assert (ROOT / s).exists(), s
    dut = (ROOT / "rtl/rom/ot_rom_link_cdc.sv").read_text()
    assert re.search(r"module\s+ot_rom_link_cdc", dut)


def test_every_positive_case_is_bit_exact_without_overflow():
    r = rec()
    pos = [c for c in r["cases"] if not c["expect_overflow"]]
    assert {c["ppm_rx_vs_tx"] for c in pos} >= {0, 100, -100, 200, -200}
    for c in pos:
        assert c["pass"] and c["mismatches"] == 0 and not c["overflow"] and not c["underflow"], c["case"]
        assert c["flits_received"] >= c["flits_requested"], c["case"]
    assert r["summary"]["all_pass"] is True
    assert r["summary"]["flits_checked"] == sum(c["flits_received"] for c in pos) == 1_410_000_000


def test_negative_case_fails_closed():
    neg = [c for c in rec()["cases"] if c["expect_overflow"]]
    assert neg and all(c["overflow"] and c["pass"] for c in neg)


def test_two_stage_synchroniser_meets_the_hop_budget():
    """The atlas quotes 3.0-4.2 RX cycles for the two-flop crossing against the 4-cycle budget (+1 output register);
    the three-flop variant is recorded beside it and is not the design."""
    r = rec()
    two = [c for c in r["cases"] if not c["expect_overflow"] and c["sync_stages"] == 2]
    assert all(c["within_cdc_budget"] for c in two)
    lat = [c["latency_rx_cycles"] for c in two]
    assert 2.99 < min(x["min"] for x in lat) and max(x["max"] for x in lat) < 4.2 + 0.01
