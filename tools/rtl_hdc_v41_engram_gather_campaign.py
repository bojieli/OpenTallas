#!/usr/bin/env python3
"""RTL campaign for the shipped-scale Engram hash and row gather/prefetch.

DUT: rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv (generated from the reduced hash
unit by tools/hdc_v41_engram_shipped.py, on the RELEASED Engram tables) feeding
rtl/hdc/v41/ot_hdc_engram_gather.sv, with 48 behavioural column banks and a
behavioural prefetch buffer (rtl/test/tb_hdc_engram_gather.sv).

Every expected value comes from the golden:
* hash rows: tools/hdc_golden_v41.EngramTables.hashes on the shipped tables
  (hdc_v41_engram_shipped.shipped_tables), checked in the bench, row for row;
* buffer contents: for every token and Engram layer, the 24 rows the golden
  addresses, with the synthetic table content of hdc_v41_engram_shipped.row_bytes,
  decoded by the golden's own `to_bf16((E4M3[codes] * np.exp2(sc)).astype(F))`;
  the bench dumps the buffer each time a (token, layer) becomes ready and this
  tool compares every BF16 element.

Token streams (compressed ids, which are shipped-space ids): the reduced V4.1
workload's prompt and gold tokens through the reduced compressed token map, a
tokenised English text through the reduced tokenizer and map, the pad id,
extremes (0, 99,091, the 17-bit maximum), and random streams of uniform ids in
[0, 99,092).  Modes: an ideal bank (4 cycles, no stalls), a stressed one (random
bank latency, request stalls, response gaps, input bubbles, consumer delays),
and bank latencies that stand for a UCIe hop pair and a board-link hop pair
(latency measurement).  Mutations of the gather and of the generated hash must
be caught.  Writes results/rtl/hdc_v41_engram_gather_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import hdc_v41_engram_shipped as ES  # noqa: E402
import rtl_hdc_v41_engram_campaign as EC  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_engram_gather_campaign.json"
GATHER = ROOT / "rtl/hdc/v41/ot_hdc_engram_gather.sv"
TB = ROOT / "rtl/test/tb_hdc_engram_gather.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_tb_harness.cpp"
SOURCES = [ES.PKG, ES.HASH_OUT, GATHER]
TOOLS = [ROOT / "tools/hdc_golden.py", ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_v41_engram_shipped.py",
         ROOT / "tools/rtl_hdc_v41_engram_campaign.py", Path(__file__)]
CRIT = ROOT / "results/roofline/critical_path/decode_critical_path.json"
LINT_FLAGS = EC.LINT_FLAGS
VL_FLAGS = EC.VL_FLAGS
CV = ES.SHIPPED["engram_compressed_vocab_size"]
RE_G = re.compile(r"GATHER tokens=(\d+) hash_checked=(\d+) hash_errors=(\d+) dumped=(\d+) ready_errors=(\d+) "
                  r"cycles=(\d+) lat0_min=(\d+) lat0_max=(\d+) lat0_sum=(\d+) lat1_min=(\d+) lat1_max=(\d+) "
                  r"lat1_sum=(\d+)")
# name, plusargs, token limit (None = all)
MODES = [
    ("ideal_bank_4_cycles", dict(LAT=4), None),
    ("stressed", dict(LAT=30, JIT=60, STALL=30, GAP=30, BUB=40, CDEL=400), None),
    ("ucie_hop_pair_23_cycles", dict(LAT=23), 400),
    ("board_hop_pair_209_cycles", dict(LAT=209), 400),
]
MUT_MODE = ("mutation", dict(LAT=30, JIT=60, STALL=30, GAP=30, BUB=40, CDEL=100), 150)
GATHER_MUTATIONS = [
    ("subnormal tie rounds away from even", "(rem == half && q[0])", "(rem == half)"),
    ("scale not latched for beats 1..7", "(gbeat == 0) ? gdata[DW-1 -: 8] : scl[gsel]", "gdata[DW-1 -: 8]"),
    ("layer ready one beat early", "busy[0] && cnt0 == TOTV", "busy[0] && cnt0 >= TOTV - 1"),
    ("column offset not subtracted", "in_row[ROW_W*gb +: ROW_W] - OFF;", "in_row[ROW_W*gb +: ROW_W];"),
    ("slot tag ignored at the buffer", "s1_a <= {gtag, gsel, gbeat};", "s1_a <= {1'b0, gsel, gbeat};"),
    ("overflow threshold one binade late", "X > 11'sd127", "X > 11'sd128"),
    ("NaN sign dropped", "{s, 15'h7FC0}", "{1'b0, 15'h7FC0}"),
    ("subnormal boundary one binade low", "X >= -11'sd126", "X >= -11'sd127"),
]
HASH_MUTATIONS = [
    ("hash: top digit shifted as a 4-bit digit", "<< (2*ENG_DIG_W);", "<< 8;"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- vectors --------------------------------------------------------------------------------
def streams(rng):
    red = EC.engram_tables()                         # reduced tables: its compressed token map
    prompt, gen = G.prompt_and_expected()
    real = [int(red.token_map[i]) for i in prompt + gen]
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(G.TOKENIZER))
    text = [int(red.token_map[i]) for i in tok.encode(EC.TEXT).ids if i < len(red.token_map)]
    out = [("reduced_workload_prompt_and_gold", real), ("reduced_tokenised_text", text),
           ("pad_ids", [2] * 5), ("single_position", [CV - 1]),
           ("extremes", [0, CV - 1, (1 << ES.ID_W) - 1, 2, 0, CV - 1, 1, (1 << ES.ID_W) - 1, 0])]
    k = 0
    while sum(len(s) for _, s in out) < 1800:
        n = int(rng.integers(1, 50))
        out.append((f"random_{k}", [int(i) for i in rng.integers(0, CV, n)]))
        k += 1
    return out


def build_vectors(t, rng):
    """[(first, cid, rows[layer][24])] in stream order, and per-stream counts."""
    toks, counts = [], {}
    for name, ids in streams(rng):
        for p in range(len(ids)):
            toks.append((int(p == 0), ids[p], ES.hashes(t, ids[:p + 1])))
        key = "random" if name.startswith("random_") else name
        counts[key] = counts.get(key, 0) + len(ids)
    return toks, counts


def write_vectors(path: Path, toks):
    path.write_text("".join(f"{f:x} {c:x} " + " ".join(f"{r:x}" for rows in rr for r in rows) + "\n"
                            for f, c, rr in toks))


_ROWCACHE: dict = {}


def expected_words(li, rows):
    """192 hex words (512 bits, lane 0 lowest) of one layer's 24 rows."""
    codes, scales = [], []
    for r in rows:
        key = (li, r)
        if key not in _ROWCACHE:
            _ROWCACHE[key] = ES.row_bytes(li, r)
        c, s = _ROWCACHE[key]
        codes.append(c)
        scales.append(s)
    bf = ES.decode_rows(codes, scales)                # [24, 256]
    words = []
    for col in range(len(rows)):
        for k in range(ES.BEATS):
            lanes = bf[col, 32 * k:32 * (k + 1)]
            words.append("".join(f"{int(v):04x}" for v in lanes[::-1]))
    return words


def compare(out_path: Path, toks, limit):
    """Compare the dumped buffer with the golden: (dumps, elements, mismatching elements)."""
    lines = out_path.read_text().split("\n")
    i, dumps, elems, bad, seen = 0, 0, 0, 0, set()
    while i < len(lines) and lines[i].startswith("T "):
        _, t, _, li = lines[i].split()
        t, li = int(t), int(li)
        got = lines[i + 1:i + 1 + 24 * ES.BEATS]
        exp = expected_words(li, toks[t][2][li])
        for g, e in zip(got, exp):
            elems += 32
            if g != e:
                bad += sum(g[4 * j:4 * j + 4] != e[4 * j:4 * j + 4] for j in range(32))
        bad += 32 * max(0, len(exp) - len(got))
        seen.add((t, li))
        dumps += 1
        i += 1 + 24 * ES.BEATS
    n = len(toks) if limit is None else min(limit, len(toks))
    complete = seen == {(t, li) for t in range(n) for li in range(2)}
    return dumps, elems, bad, complete


# -- simulation -----------------------------------------------------------------------------
def build(obj: Path, sources):
    subprocess.run(["verilator", *VL_FLAGS, "--top-module", "tb_hdc_engram_gather", "-Mdir", str(obj),
                    *map(str, sources), str(TB), str(HARNESS), "-CFLAGS", "-O1 -DVTOP=Vtb_hdc_engram_gather"],
                   check=True, capture_output=True)
    return obj / "Vtb_hdc_engram_gather"


def simulate(exe, vec, out, args):
    cmd = [str(exe), f"+VEC={vec}", f"+OUT={out}", *(f"+{k}={v}" for k, v in args.items())]
    text = subprocess.run(cmd, capture_output=True, text=True, timeout=3600).stdout
    m = RE_G.search(text)
    if not m:
        return {"pass": False, "log": text[-1500:]}
    v = list(map(int, m.groups()))
    n = v[0]
    return {"tokens": n, "hash_checked": v[1], "hash_errors": v[2], "dumps": v[3], "ready_errors": v[4],
            "cycles": v[5],
            "latency_cycles": {"layer_1": {"min": v[6], "max": v[7], "mean": round(v[8] / max(n, 1), 2)},
                               "layer_14": {"min": v[9], "max": v[10], "mean": round(v[11] / max(n, 1), 2)}},
            "bench_pass": "DONE" in text}


def run_mode(exe, s: Path, toks, name, args, limit):
    sub = toks if limit is None else toks[:limit]
    vec, out = s / f"{name}.vec", s / f"{name}.out"
    write_vectors(vec, sub)
    rec = simulate(exe, vec, out, args)
    if "tokens" in rec:
        d, e, b, complete = compare(out, sub, None)
        rec.update(buffer_dumps_compared=d, elements_compared=e, element_mismatches=b, all_dumps_present=complete)
        rec["pass"] = bool(rec["bench_pass"] and b == 0 and complete and rec["hash_errors"] == 0 and
                           rec["hash_checked"] == len(sub) and e == len(sub) * 2 * 24 * 256)
    out.unlink(missing_ok=True)
    rec["bank_model"] = args
    return rec


def mutations(s: Path, toks):
    res = []
    name, args, limit = MUT_MODE
    ctrl = run_mode(build(s / "mut_ctrl", SOURCES), s, toks, "mut_ctrl", args, limit)
    res.append({"mutation": "none (control)", "control": True, "caught": not ctrl["pass"]})
    for i, (what, a, b) in enumerate(GATHER_MUTATIONS + HASH_MUTATIONS):
        src = GATHER if i < len(GATHER_MUTATIONS) else ES.HASH_OUT
        text = src.read_text()
        assert text.count(a) == 1, (what, text.count(a))
        d = s / f"mut{i}"
        d.mkdir()
        m = d / src.name
        m.write_text(text.replace(a, b))
        srcs = [m if p == src else p for p in SOURCES]
        try:
            rec = run_mode(build(d / "obj", srcs), d, toks, f"mut{i}", args, limit)
            caught = not rec["pass"]
            detail = {k: rec.get(k) for k in ("hash_errors", "element_mismatches", "ready_errors", "bench_pass")}
        except subprocess.CalledProcessError as e:
            caught, detail = True, {"build_failed": (e.stderr or b"")[-300:].decode(errors="replace")}
        res.append({"mutation": what, "caught": caught, "detail": detail})
        print("mutation", what, "caught" if caught else "MISSED", flush=True)
    return res


def slack(modes, clock_hz):
    """Prefetch slack against the committed decode critical path: the rows of layer L must be in the
    buffer before layer L starts (the step starts when the token id is known)."""
    crit = json.loads(CRIT.read_text())
    out = {}
    for design in ("array_batch1", "wafer_batch1"):
        per = crit["deepseek_v41_flash"][design]["per_layer_critical_path_us"]
        start1 = per["-1"] + per["0"]
        start14 = per["-1"] + sum(per[str(i)] for i in range(14))
        rec = {"layer_1_start_us": round(start1, 4), "layer_14_start_us": round(start14, 4)}
        for m in ("ucie_hop_pair_23_cycles", "board_hop_pair_209_cycles"):
            lat = modes[m]["latency_cycles"]
            g1, g14 = lat["layer_1"]["max"] / clock_hz * 1e6, lat["layer_14"]["max"] / clock_hz * 1e6
            rec[m] = {"rows_ready_us_layer_1": round(g1, 4), "slack_us_layer_1": round(start1 - g1, 4),
                      "rows_ready_us_layer_14": round(g14, 4), "slack_us_layer_14": round(start14 - g14, 4)}
        out[design] = rec
    return {"clock_hz": clock_hz, "source": str(CRIT.relative_to(ROOT)) +
            " deepseek_v41_flash.<design>.per_layer_critical_path_us (embedding + layers before L)",
            "note": "slack of the ROW GATHER alone; the Engram wkv matvec, key norm and delivery that follow the "
                    "rows run on the same side branch and are priced by tools/decode_critical_path.py",
            "designs": out}


def run(quick=False) -> dict:
    rng = np.random.default_rng(1441)
    t = ES.shipped_tables()
    layout = ES.check_against_released_layout(t)
    toks, counts = build_vectors(t, rng)
    if quick:
        toks = toks[:60]
    lint = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_engram_gather",
                           str(ES.PKG), str(GATHER)], capture_output=True, text=True)
    lint_h = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, "--top-module", "ot_hdc_engram_hash_shipped",
                             str(ES.PKG), str(ES.HASH_OUT)], capture_output=True, text=True)
    modes = {}
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        exe = build(s / "obj", SOURCES)
        for name, args, limit in (MODES[:1] if quick else MODES):
            modes[name] = run_mode(exe, s, toks, name, args, limit)
            print(name, "pass" if modes[name].get("pass") else "FAIL",
                  {k: modes[name].get(k) for k in ("elements_compared", "element_mismatches", "latency_cycles")},
                  flush=True)
        muts = [] if quick else mutations(s, toks)
    clock = json.loads(CRIT.read_text())["clock"]["hz"]
    ok = (all(m.get("pass") for m in modes.values()) and lint.returncode == 0 and lint_h.returncode == 0
          and all(m["caught"] != bool(m.get("control")) for m in muts))
    return {
        "schema": "opentallas.hdc-v41-engram-gather-campaign.v1",
        "status": "pass" if ok else "fail",
        "claim_boundary": "functional cycle-level Verilator simulation of the shipped-table hash unit and the "
                          "row gather/prefetch against the golden, with BEHAVIOURAL column banks and a "
                          "behavioural buffer; table CONTENT is synthetic (the shipped tables are not in this "
                          "repository) and the bank latencies are parameters, not ROM measurements.  Area and "
                          "clock are in results/physical_abi3/asap7/hdc/v41/.",
        "released_layout": layout,
        "tokens": len(toks), "tokens_by_stream": counts,
        "rows_per_token": 48, "elements_per_token": 48 * 256,
        "contract": {"hash_ids": "any 17-bit compressed id (the model's are < 99,092); pad id 2",
                     "decode": "every E4M3 code (NaN codes give the golden's +-0x7FC0) and every UE8M0 scale byte "
                               "0..255 (255 = 2^128, as the golden's exp2) -- no code is outside the contract"},
        "modes": modes,
        "mutations": muts,
        "prefetch_slack": slack(modes, clock) if not quick else None,
        "verilator_lint": {"flags": list(LINT_FLAGS),
                           "ot_hdc_engram_gather": {"returncode": lint.returncode,
                                                    "messages": lint.stderr.strip().splitlines()[:10]},
                           "ot_hdc_engram_hash_shipped": {"returncode": lint_h.returncode,
                                                          "messages": lint_h.stderr.strip().splitlines()[:10]}},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (*SOURCES, ES.HASH_SRC, TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    rec = run(args.quick)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(rec["status"])
    return 0 if rec["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
