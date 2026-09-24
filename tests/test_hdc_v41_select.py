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
import rtl_hdc_v41_select_campaign as campaign  # noqa: E402


def test_committed_record_is_current_and_passes():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    names = {c["name"] for c in record["configurations"]}
    assert names == {c[0] for c in campaign.CONFIGS}
    for cfg in record["configurations"]:
        assert cfg["pass"]
        for run in cfg["runs"].values():
            assert run["errors"] == 0 and run["outputs"] == cfg["expected_outputs"]
            assert run["latency_min"] == run["latency_max"] == run["latency_expected"] == cfg["latency_cycles"]
    assert all(n > 0 for n in record["real_data"]["golden_selection_checks"].values())
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_expected_order_follows_the_golden():
    v = np.array([1.0, 3.0, -0.0, 3.0, 0.0, -np.inf, 3.0])
    assert campaign.expected(v, np.arange(7), 3, 0) == [(1, False), (3, False), (6, False)]
    # -0 ties +0 and loses to the lower index; ascending-index emission sorts the picks
    assert campaign.expected(v, np.arange(7), 6, 1) == [(0, False), (1, False), (2, False), (3, False),
                                                        (4, False), (6, False)]
    assert campaign.expected(v, np.arange(7), 7, 1)[5] == (5, True)
    # labels, not stream positions, break ties
    assert campaign.expected(v, np.array([9, 8, 7, 6, 5, 4, 3]), 1, 0) == [(3, False)]


@pytest.mark.skipif(shutil.which("iverilog") is None, reason="needs Icarus Verilog")
def test_router_configuration_under_icarus(tmp_path):
    rng = np.random.default_rng(11)
    segs = campaign.random_segments(rng, 6, 32, 9, 150)
    fin, fexp, n_el, n_out, _ = campaign.write_vectors(segs, 6, 32, 9, 1, tmp_path, "r")
    vvp = tmp_path / "r.vvp"
    subprocess.run(["iverilog", "-g2012", "-Ptb_hdc_select.K=6", "-Ptb_hdc_select.VW=32", "-Ptb_hdc_select.IW=9",
                    "-o", str(vvp), str(campaign.TB), str(campaign.RTL)], check=True)
    out = subprocess.run(["vvp", "-n", str(vvp), f"+IN={fin}", f"+EXP={fexp}", "+BUBBLE=25", "+GAP=10"],
                         capture_output=True, text=True, check=True).stdout
    rec = campaign.parse(out)
    assert rec["pass"] and rec["outputs"] == n_out and rec["elements"] == n_el, out[-1000:]
