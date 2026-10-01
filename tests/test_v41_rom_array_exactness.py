"""W10 item 2: the V4.1 ROM element array (the 1.2 GHz element: FAST = 1 pipeline, PP = 1 ping-pong 4096m8 slots,
the BF16 column path) is exact against golden on real checkpoint slices, and an empty go is a no-op."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
U = ROOT / "results/uarch"


def _load(name):
    rec = json.loads((U / name).read_text())
    for p, h in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
    return rec


def test_every_row_exact_at_n_2_4_8():
    rec = _load("v41_rom_array_exactness_fast_pp.json")
    assert rec["verdict"] == "PASS" and rec["params"]["FAST"] == 1 and rec["params"]["PP"] == 1
    assert {2, 4, 8} <= {c["N"] for c in rec["cases"]}
    assert {"fp8", "fp4", "bf16", "mixed"} <= {c["case"].split("_")[0] for c in rec["cases"]}
    for c in rec["cases"]:
        assert c["rows_out"] == c["rows"] == c["fp32_exact"] == c["bf16_exact"], c["case"]
        assert not c["fault"], c["case"]
        assert c["cycles_last_row"] == c["t_phase_pred"] + c["fill"]


def test_pair_mtp6_fillcut_exact():
    rec = _load("v41_rom_array_exactness_fast_pp_pair_mtp6_fillcut.json")
    assert rec["verdict"] == "PASS"
    assert {c["N"] for c in rec["cases"]} == {4, 8, 16}
    for c in rec["cases"]:
        assert c["NB"] == 2 and c["positions"] == 6 and c["fill_cuts"]
        assert c["rows_out"] == c["rows"] == c["fp32_exact"] == c["bf16_exact"], c["case"]


def test_empty_go_is_a_noop_and_the_mutant_is_caught():
    good = _load("v41_rom_array_multiphase_fast_pp.json")
    assert good["verdict"] == "PASS"
    assert any(s["empty_then_work_transitions"] > 0 for s in good["sequences"])
    bad = _load("v41_rom_array_multiphase_fast_pp_mutant.json")
    assert bad["verdict"] == "FAIL" and not bad["sequences"][0]["exact"]
    assert bad["sequences"][0]["defines"] == ["W10_MUTANT_EMPTY_GO"]
