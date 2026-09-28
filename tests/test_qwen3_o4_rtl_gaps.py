"""Checks of tools/qwen3_o4_rtl_gaps.py, results/arch/qwen3_o4_rtl_gaps.json and docs/ARCH_QWEN3_O4_RTL_SPEC.md.

1. The doc's gap table is the JSON's gap table, row for row and cell for cell.
2. The requirement, die-split and contract figures re-derive from the tool (no weights needed).
3. The INT8 numerics on synthetic rows: the pieces the contract relies on are exact, the contract equals the golden
   matvec of the codes followed by one scale multiply, and the harness's scale-inside-the-product order is not the
   contract's (the finding the record carries on real Qwen3-8B rows).
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import qwen3_o4_rtl_gaps as T  # noqa: E402

REC = json.loads(T.OUT.read_text())
DOC = T.DOC.read_text()


def doc_gap_rows():
    body = DOC.split("<!-- gap-table:begin -->")[1].split("<!-- gap-table:end -->")[0]
    rows = []
    for line in body.strip().splitlines():
        if not re.match(r"^\| G\d+ \|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        rows.append(cells)
    return rows


def test_doc_gap_table_matches_json():
    doc = doc_gap_rows()
    js = [[g["id"], g["block"], g["current"], g["required"], g["size"], g["owner"]] for g in REC["gaps"]]
    assert [r[0] for r in doc] == [r[0] for r in js], "gap ids differ between the doc and the JSON"
    for d, j in zip(doc, js):
        assert d == j, f"gap {j[0]} differs between the doc and the JSON"


def test_json_gaps_are_the_tools():
    assert REC["gaps"] == T.GAPS
    for g in REC["gaps"]:
        assert g["size"] in REC["size_legend"]
        assert g["owner"] in ("Codex", "Claude")
    # every RTL-side gap is Codex's; only model- and golden-side gaps are Claude's
    claude = {g["id"] for g in REC["gaps"] if g["owner"] == "Claude"}
    assert claude == {"G13", "G14", "G15", "G16"}


def test_requirements_and_die_split_rederive():
    assert json.loads(json.dumps(T.requirements())) == REC["requirements"]
    assert json.loads(json.dumps(T.die_split())) == REC["die_split"]
    assert [c.split()[0] for c in REC["numeric_contract"]] == [f"C{i}" for i in range(8)]


def test_die_split_reproduces_the_o4_ledger():
    tp = REC["die_split"]["tp2"]
    assert tp["rom_mm2_per_die"] == pytest.approx(T.O4["target_rom_mm2"] + T.O4["drafter_rom_mm2"], abs=0.01)
    assert tp["rom_read_headroom"] == T.O4["rom_read_headroom"]
    cut = REC["die_split"]["layer_cut"]
    assert cut["P"] == 20 and cut["row"]["both_fit"]
    assert cut["ar_tokens_s"] < 0.6 * T.O4["ar_tokens_s"]


def test_ucie_exchange_arithmetic():
    u = REC["requirements"]["ucie"]
    assert u["all_reduce_bytes_per_direction"] == 4096 * 4           # FP32 partials, as tools/hdc_golden.fold adds
    assert u["exchanges_per_token"] == 2 * 36 + 1
    assert u["fp32_cycles_per_token"] > T.O4["extra_chain_cycles"]    # O4 priced BF16 partials


def test_matrix_cycles_match_the_pair_replay():
    m = REC["requirements"]["matrices_per_die"]
    assert [m[k]["cycles"] for k in ("qkv", "o", "gate_up", "down")] == [128, 88, 512, 264]
    assert m["lm_head"]["cycles"] == T.O4["as_built"]["unit_busy"]["lm_head"]


def test_synthetic_numerics():
    n = T.numerics(rows=24, real=False)
    assert n["pieces_exact"] and n["embedding_dequant_exact"]
    for r in n["matrices"].values():
        assert r["products_exact_fp32"] and r["codes_exact_in_bf16"] and r["scales_are_bf16"]
        if "harness_equals_golden_per_mac" in r:
            assert r["harness_equals_golden_per_mac"]
    assert not n["bit_exact_with_harness_order"]


def test_contract_is_golden_matvec_of_codes_then_one_multiply():
    rng = np.random.default_rng(1)
    w = T.G.to_bf16(rng.standard_normal((8, 256)).astype(np.float32) * 0.05)
    q, s = T.quantize_rows(w)
    x = rng.standard_normal(256).astype(np.float32)
    y, t = T.contract_mv(x, q, s, 4)
    assert np.array_equal(t, T.G.matvec(q.astype(np.float32), x, 4))
    assert np.array_equal(T._bits(y), T._bits(T.G.mul(t, s)))
    assert q.dtype == np.int8 and q.min() >= -128 and q.max() <= 127


def test_record_numerics_verdict():
    n = REC["numerics"]
    assert n["pieces_exact"] and not n["bit_exact_with_harness_order"]
    assert n["harness_order_rows_differing"] > 0
