"""Fast checks of the DS-ROM near-HBM pricing record (the full replay is `python3 tools/dsrom_nearhbm.py --check`)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dsrom_nearhbm as N  # noqa: E402

REC = json.loads(N.OUT.read_text())


def test_sources_pinned():
    for k, rel in N.SRC.items():
        assert REC["source_sha256"][k] == N.sha(rel), k


def test_ledger_and_physical_recompute():
    assert json.loads(json.dumps(N.ledger())) == REC["q1_ledger"]
    assert json.loads(json.dumps(N.physical())) == REC["physical"]


def test_baseline_reproduces_s58():
    r = {v["variant"]: v for v in REC["variants"]}["base"]
    assert abs(r["ar_us_1m"] - 390.06) < 0.02 and abs(r["mtp_tok_s_1m"] - 3809.4) < 0.2
    assert abs(r["ar_us_200k"] - 373.05) < 0.02 and abs(r["mtp_tok_s_200k"] - 4176.7) < 0.2


def test_scan_bytes_and_paths():
    s = REC["q1_ledger"]["by_ctx"]["1048576"]["index_scan"]
    assert s["L20_die_MB"] == 262144 * 68 / 1e6
    assert s["L20_us"]["hbm_aggregate"] == 4.952          # 3,000 B/cycle at 1.2 GHz
    assert s["L20_us"]["routed_idx_keys_bus"] > s["L20_us"]["hbm_aggregate"]   # the routed bus is 68% of HBM
    assert REC["q1_ledger"]["paths"]["routed_idx_keys_bus"]["Bpc"] == 2048.0


def test_verdicts():
    inc = REC["increments"]
    for ctx in ("1048576", "200000"):
        # proximity buys no latency: the same stack-major select placed centrally prices identically
        assert inc[f"nh_scan_vs_central4_chase@{ctx}"] == {"ar_pct": 0.0, "mtp_pct": 0.0}
        # exact near-HBM attention only adds crossings
        assert inc[f"nh_attn_exact_vs_base@{ctx}"]["ar_pct"] < 0
        assert inc[f"nh_both_vs_nh_scan@{ctx}"]["ar_pct"] < 0
    assert REC["physical"]["shoreline_power_density"]["verdict_nominal"] == "PASS"
    a = REC["physical"]["die_area_delta_mm2"]
    assert a["s58_corrected_margin_mm2"] < 0 < a["s58_margin_nh_scan_mm2"]
