#!/usr/bin/env python3
"""The shipped DeepSeek-V4.1-Flash Engram, for the HDC: hash tables, the shipped
hash unit, the table-row content model and the row decode golden.

* `shipped_tables()` is tools/hdc_golden_v41.EngramTables run on the RELEASED
  Engram arguments (engram_vocab_size 16,000,000, compressed vocabulary 99,092,
  8 heads, n-grams up to 4, layers 1 and 14).  The golden's prime / offset /
  multiplier rules run unchanged; only the tokenizer-derived compressed token
  map is replaced by the identity, because the hash unit consumes COMPRESSED
  ids (the map is a ROM in front of it).  The compressed pad id is 2, the
  release's engram_pad_id 2 through a map that sends the first special tokens
  to themselves (first-seen order).  The derivation is checked against
  tools/build_a3_v41_ngram_hash_vectors.py (released row counts
  [384006168, 384016682] and the pinned multipliers).
* `emit_package()` writes rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv and
  `emit_hash()` writes rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv, which is
  ot_hdc_engram_hash.sv with (a) the shipped package and module name and (b) its
  digit-product stage generalised from three 4-bit digits to three
  ENG_DIG_W-bit digits (a 17-bit id needs 6-bit digits and 64-entry product
  tables).  Everything else -- the XOR prefix, the folded-digit modulo, the
  latency of 12 -- is the reduced source, text for text: the reduced module is
  the single source of truth, and tests/test_hdc_v41_engram_gather.py checks
  both generated files are current.
* `row_bytes(layer, row)` is the synthetic table content the RTL bank model
  mirrors (splitmix64 of the row address), and `decode_rows` is the golden's
  own `to_bf16((E4M3[codes] * np.exp2(sc)).astype(F))`.

Usage: python3 tools/hdc_v41_engram_shipped.py --emit
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41_engram_campaign as EC  # noqa: E402

V41 = ROOT / "rtl/hdc/v41"
PKG = V41 / "ot_hdc_engram_tables_shipped_pkg.sv"
HASH_SRC = V41 / "ot_hdc_engram_hash.sv"
HASH_OUT = V41 / "ot_hdc_engram_hash_shipped.sv"
PKG_NAME = "ot_hdc_engram_tables_shipped_pkg"
HASH_NAME = "ot_hdc_engram_hash_shipped"

SHIPPED = {
    "engram_layer_ids": [1, 14],
    "engram_max_ngram_size": 4,
    "engram_n_heads": 8,
    "engram_vocab_size": 16_000_000,
    "engram_compressed_vocab_size": 99_092,
    "engram_pad_id": 2,
    "engram_head_dim": 256,
    "vocab_size": 129_280,
}
RELEASED_ROWS = [384_006_168, 384_016_682]
ID_W = 17                      # 99,092 compressed ids
DIG_W = 6                      # three 6-bit digits cover 18 >= 17 bits
ROW_BYTES = 256                # E4M3 codes per row (engram_head_dim)
PACKED_ROW_BYTES = 264         # metadata engram.row_bytes_packed: 256 codes + 1 UE8M0 scale + 7 pad
BEATS = 8                      # gather-port beats per row
BEAT_CODES = ROW_BYTES // BEATS  # 32 codes (+ 1 side byte) per 264-bit beat


def shipped_tables():
    """EngramTables on the released arguments, with the identity compressed map."""
    cv = SHIPPED["engram_compressed_vocab_size"]
    orig = G.compressed_token_map
    G.compressed_token_map = lambda path, size: (np.arange(size, dtype=np.int64), cv)
    try:
        t = G.EngramTables(SHIPPED, cv)
    finally:
        G.compressed_token_map = orig
    rows = [int(r) for r in t.primes.reshape(len(t.layer_ids), -1).sum(1)]
    assert rows == RELEASED_ROWS, rows
    t.token_map = np.arange(1 << ID_W, dtype=np.int64)   # identity over every 17-bit id
    return t


def check_against_released_layout(t) -> dict:
    """Cross-check primes, offsets and multipliers with the DMA.NGRAM_HASH vector builder."""
    import build_a3_v41_ngram_hash_vectors as NV
    lay = NV.released_layout()["layers"]
    for li, L in enumerate(lay):
        assert [list(map(int, r)) for r in t.primes[li]] == L["primes"], li
        assert [int(o) for o in t.offsets[li]] == L["offsets"], li
        assert [int(m) for m in t.multipliers[li]] == L["multipliers"], li
    return {"released_rows": RELEASED_ROWS, "primes_offsets_multipliers_equal": True,
            "reference": "tools/build_a3_v41_ngram_hash_vectors.released_layout + PINNED_MULTIPLIERS"}


def hashes(t, cids):
    """Global row ids [layer][24] of the n-grams ending at the last of `cids` (compressed ids)."""
    return [[int(r) for r in t.hashes(list(cids), li)] for li in range(len(t.layer_ids))]


# -- generated RTL ------------------------------------------------------------------------
def emit_package() -> str:
    t = shipped_tables()
    layers, n, heads = len(t.layer_ids), t.n, t.primes.shape[2]
    cols = (n - 1) * heads
    primes = t.primes.reshape(layers, cols)
    rows = t.offsets + primes
    res_w = int(primes.max()).bit_length()
    row_w = int(rows.max() - 1).bit_length()
    nd = 1 << DIG_W
    assert SHIPPED["engram_compressed_vocab_size"] <= (1 << ID_W) and ID_W <= 3 * DIG_W
    nib = [int(t.multipliers[li, s]) * d for li in range(layers) for s in range(n) for d in range(nd)]
    assert max(nib) < (1 << 64)
    res = []
    for li in range(layers):
        for col in range(cols):
            q = int(primes[li, col])
            res.extend((d << (4 * j)) % q for j in range(16) for d in range(16))
    per_col = 16 * 16
    res_chunks = [EC._packed(res[i:i + per_col], res_w) for i in range(0, len(res), per_col)]
    nib_chunks = [EC._packed(nib[i:i + nd], 64) for i in range(0, len(nib), nd)]
    lines = [
        "`timescale 1ns/1ps",
        "// GENERATED by tools/hdc_v41_engram_shipped.py --emit from tools/hdc_golden_v41.EngramTables on",
        "// the RELEASED DeepSeek-V4.1-Flash Engram arguments (engram_vocab_size 16,000,000, compressed",
        "// vocabulary 99,092).  Do not edit.  tests/test_hdc_v41_engram_gather.py checks it is current.",
        f"package {PKG_NAME};",
        f"    localparam integer ENG_LAYERS = {layers};      // Engram layers {list(t.layer_ids)}",
        f"    localparam integer ENG_N      = {n};      // max n-gram order",
        f"    localparam integer ENG_HEADS  = {heads};",
        f"    localparam integer ENG_COLS   = {cols};     // (N-1) * HEADS hash columns per layer",
        f"    localparam integer ENG_ID_W   = {ID_W};     // compressed token id width (99,092 ids)",
        f"    localparam integer ENG_DIG_W  = {DIG_W};      // id digit width of the product tables (3 digits)",
        f"    localparam integer ENG_RES_W  = {res_w};     // residue width (largest prime {int(primes.max())})",
        f"    localparam integer ENG_ROW_W  = {row_w};     // row address width (largest table {int(rows.max())} rows)",
        f"    localparam [{ID_W - 1}:0] ENG_PAD = {ID_W}'d{t.pad};   // compressed id of the pad token",
        f"    // ENG_NIB[p*{nd} + d] = d * multiplier[layer][s], p = layer*N + s; one line per product, product 0 last",
        f"    localparam [{64 * len(nib) - 1}:0] ENG_NIB = {{",
    ]
    lines += [f"        {c}{',' if i else ''}" for i, c in reversed(list(enumerate(nib_chunks)))]
    lines += [
        "    };",
        "    // ENG_PRIME[c], ENG_OFFSET[c]: column c = layer*COLS + (s-1)*HEADS + head",
        f"    localparam [{res_w * layers * cols - 1}:0] ENG_PRIME = {EC._packed(primes.reshape(-1), res_w)};",
        f"    localparam [{row_w * layers * cols - 1}:0] ENG_OFFSET = {EC._packed(t.offsets.reshape(-1), row_w)};",
        "    // ENG_RES[(c*16 + j)*16 + d] = (d << 4j) mod prime[c]; one line per column, column 0 last",
        f"    localparam [{res_w * len(res) - 1}:0] ENG_RES = {{",
    ]
    lines += [f"        {chunk}{',' if i else ''}" for i, chunk in reversed(list(enumerate(res_chunks)))]
    lines += ["    };", "endpackage", ""]
    return "\n".join(lines)


# The reduced source's digit-product stage, and its generalisation to ENG_DIG_W-bit digits.
_PROD_OLD = """            wire [ENG_ID_W-1:0] t = w[p % ENG_N];
            localparam [64*16-1:0] TP = NIB[64*16*p +: 64*16];   // this product's 16 entries
            reg [63:0] pp0, pp1, pp2, pa, pb, prod;
            always @(posedge clk) begin
                pp0  <= TP[64*t[3:0]  +: 64];
                pp1  <= TP[64*t[7:4]  +: 64] << 4;
                pp2  <= TP[64*t[11:8] +: 64] << 8;
"""
_PROD_NEW = """            localparam integer ND = 1 << ENG_DIG_W;              // entries per product table
            wire [3*ENG_DIG_W-1:0] t = {{(3*ENG_DIG_W-ENG_ID_W){1'b0}}, w[p % ENG_N]};
            localparam [64*ND-1:0] TP = NIB[64*ND*p +: 64*ND];   // this product's 2^DIG_W entries
            reg [63:0] pp0, pp1, pp2, pa, pb, prod;
            always @(posedge clk) begin
                pp0  <= TP[64*t[ENG_DIG_W-1:0] +: 64];
                pp1  <= TP[64*t[2*ENG_DIG_W-1:ENG_DIG_W] +: 64] << ENG_DIG_W;
                pp2  <= TP[64*t[3*ENG_DIG_W-1:2*ENG_DIG_W] +: 64] << (2*ENG_DIG_W);
"""
_EDITS = [
    ("import ot_hdc_engram_tables_pkg::*;", f"import {PKG_NAME}::*;"),
    ("module ot_hdc_engram_hash (", f"module {HASH_NAME} ("),
    (_PROD_OLD, _PROD_NEW),
    ("// * The multiply by a constant is three table lookups, one per 4-bit digit of\n"
     "//   the id (ENG_NIB[p][n] = n * mult,",
     "// * The multiply by a constant is three table lookups, one per ENG_DIG_W-bit\n"
     "//   digit of the id (ENG_NIB[p][n] = n * mult,"),
    ("// * Any 12-bit id is exact (the product stays below 2^64)",
     "// * Any 17-bit id is exact (the product stays below 2^64)"),
]


def emit_hash() -> str:
    src = HASH_SRC.read_text()
    for a, b in _EDITS:
        assert src.count(a) == 1, a[:60]
        src = src.replace(a, b)
    banner = ("// GENERATED by tools/hdc_v41_engram_shipped.py --emit from rtl/hdc/v41/ot_hdc_engram_hash.sv:\n"
              f"// the shipped-scale hash unit ({PKG_NAME}: 17-bit compressed ids, primes\n"
              "// near 16,000,000, 29-bit row addresses).  Only the package, the module name and the digit\n"
              "// width of the product stage differ from the reduced source.  Do not edit.\n")
    head, rest = src.split("\n", 1)
    return head + "\n" + banner + rest


# -- table content and the row decode golden ----------------------------------------------
M64 = (1 << 64) - 1


def splitmix64(x: int) -> int:
    z = (x + 0x9E3779B97F4A7C15) & M64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return z ^ (z >> 31)


def row_bytes(layer: int, row: int):
    """(codes[256], scale byte) of layer index `layer`'s global table row `row`: synthetic content
    the bank model mirrors.  Word j = splitmix64(layer << 40 | row << 6 | j); codes are the 32
    little-endian words 0..31, and the scale comes from word 32: a uniform byte (every UE8M0 code,
    0 and 255 included) when its bit 8 is set, else 107 + (low byte mod 41), i.e. 2^-20 .. 2^20."""
    key = (layer << 40) | (row << 6)
    codes = []
    for j in range(32):
        w = splitmix64(key | j)
        codes.extend((w >> (8 * b)) & 0xFF for b in range(8))
    w = splitmix64(key | 32)
    scale = (w & 0xFF) if (w >> 8) & 1 else 107 + (w & 0xFF) % 41
    return codes, scale


def decode_rows(codes, scales):
    """The golden: rows = to_bf16((E4M3[codes] * np.exp2(sc)).astype(F)) with sc = scale byte - 127,
    as BF16 bit patterns [rows, 256]."""
    codes = np.asarray(codes, dtype=np.int64)
    sc = np.asarray(scales, dtype=np.int64) - 127
    with np.errstate(all="ignore"):
        v = G.to_bf16((G.E4M3[codes] * np.exp2(sc.astype(np.float64))[:, None]).astype(G.F))
    return (G.bits(v) >> 16).astype(np.int64)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", action="store_true", help="rewrite the shipped package and hash unit")
    args = ap.parse_args()
    t = shipped_tables()
    print(json.dumps(check_against_released_layout(t)))
    if args.emit:
        PKG.write_text(emit_package())
        HASH_OUT.write_text(emit_hash())
        print("wrote", PKG.relative_to(ROOT), HASH_OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
