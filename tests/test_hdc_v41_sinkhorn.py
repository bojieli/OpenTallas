"""Checks of the V4.1 hyper-connection Sinkhorn unit's campaign record, reference and arithmetic model."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gen_hdc_sinkhorn_recip_rom as gen  # noqa: E402
import rtl_hdc_v41_sinkhorn_campaign as campaign  # noqa: E402


def test_committed_record_is_current_and_passes():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    assert record["latency_cycles"] == 2 * campaign.ITERS + 1
    counts = record["unit"]["counts"]
    assert counts["real_cases"] > 0 and counts["random_cases"] >= 1_000_000
    assert counts["random_fault_cases"] > 0                       # the fail-closed classes reached the unit
    for run in record["unit"]["runs"].values():
        assert run["pass"] and run["errors"] == 0
        assert run["latency_min"] == run["latency_max"] == record["latency_cycles"]
    assert record["arithmetic"]["totals"]["errors"] == 0 and record["arithmetic"]["totals"]["ops"] > 10_000_000
    assert record["generator"]["rom_matches_generator"]
    for m in record["mutations"]:
        assert m["compiled"] and (m["caught"] or m.get("equivalent")), m["id"]
    assert all(r["pass"] for r in record["icarus"].values())
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_rom_is_the_generators():
    assert campaign.ROM.read_text() == gen.rom_text()


def test_reference_follows_the_golden_contract():
    one = np.float32(1.0)
    e = np.full((1, 4, 4), one, np.float32)
    comb, bad = campaign.sinkhorn_reference(e)
    assert not bad.any()
    # a uniform matrix stays uniform: every entry is the same binary32 value near 1/4
    assert len(set(campaign.b32(comb).ravel().tolist())) == 1 and abs(float(comb[0, 0, 0]) - 0.25) < 1e-6
    # fail closed: NaN, a negative entry, a zero row
    for poison in (np.nan, -1.0):
        x = e.copy()
        x[0, 1, 2] = poison
        assert campaign.sinkhorn_reference(x)[1].all()
    x = e.copy()
    x[0, 2, :] = 0
    assert campaign.sinkhorn_reference(x)[1].all()
    # -0 reads as +0
    x = e.copy()
    x[0, 0, 3] = -0.0
    y = e.copy()
    y[0, 0, 3] = 0.0
    assert np.array_equal(campaign.b32(campaign.sinkhorn_reference(x)[0]), campaign.b32(campaign.sinkhorn_reference(y)[0]))


def test_integer_model_matches_ieee_on_a_sample():
    counts = gen.check_model(2000, seed_=5)
    assert len(counts) == 50


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="needs Icarus Verilog")
def test_arithmetic_under_icarus(tmp_path):
    lines = campaign.edge_arith_lines()
    vec = tmp_path / "a.vec"
    vec.write_text("".join(lines))
    vvp = tmp_path / "a.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_sk_arith", "-o", str(vvp), str(campaign.TB),
                    *map(str, campaign.RTL)], check=True)
    rec = campaign.parse_arith(subprocess.run(["vvp", "-n", str(vvp), f"+IN={vec}"], capture_output=True,
                                              text=True, check=True).stdout)
    assert rec["pass"] and rec["ops"] == len(lines)
