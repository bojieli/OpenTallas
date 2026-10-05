#!/usr/bin/env python3
"""RTL campaign for the V4.1 decode core's SELECT unit (rtl/hdc/v41/ot_hdc_select.sv).

Every expected output comes from tools/hdc_golden_v41.py's `topk_lowest_index`
(value descending, ties to the lower index) and, for the real vectors, from
the golden's own consumers:

* random segments with MANY ties (small value alphabets holding +0/-0, +/-inf
  and subnormals; all-equal segments; coarse-quantised normals), raw bit
  patterns, runtime k from 0 to past K, indices in position order, shuffled or
  sparse, segment lengths from 1 to several K;
* real reduced DeepSeek-V4.1 data: the golden decodes the oracle workload's
  prompt and generated tokens (then continues greedily) and every indexer's
  scores (BF16, -inf where the candidate mask removed a position), every
  router's biased FP32 scores and the candidate-block scores (block maxima,
  newest block pinned to +inf, padding -inf) are streamed through the unit.
  The golden's selections (`index_select`, `experts`, the candidate keep mask)
  must equal what the vectors expect, so the vectors are the model's.

Each configuration is simulated under Verilator 4.038 twice (back to back,
and with random bubbles and idle gaps), the router configuration also under
Icarus; outputs are compared in order, `out_last` on every segment and the
first-output latency against the documented constant.  Writes
results/rtl/hdc_v41_select_campaign.json with the sha256 of every input.
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

OUT = ROOT / "results/rtl/hdc_v41_select_campaign.json"
RTL = ROOT / "rtl/hdc/v41/ot_hdc_select.sv"
TB = ROOT / "rtl/test/tb_hdc_select.sv"
HARNESS = ROOT / "rtl/test/hdc_select_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py", Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED")
LINE = re.compile(r"SELECT K=(\d+) VW=(\d+) IW=(\d+) ORDER=(\d+) segments=(\d+) elements=(\d+) outputs=(\d+) "
                  r"errors=(\d+) lat_min=(-?\d+) lat_max=(-?\d+) lat_expect=(\d+) cycles=(\d+) stall_cycles=(\d+)")
REAL_POSITIONS = 48

# name, K, VW, IW, ORDER, random segments, real sets
CONFIGS = [
    ("router_top6", 6, 32, 9, 1, 3000, ("router",)),
    ("router_top6_rank_order", 6, 32, 9, 0, 3000, ("router",)),
    ("index_topk_reduced", 16, 16, 16, 1, 2000, ("index",)),
    ("candidate_blocks_reduced", 64, 16, 12, 1, 600, ("candidate",)),
    ("index_topk_shipped", 512, 16, 16, 1, 120, ("index", "index_all")),
    ("index_topk_shipped_rank_order", 512, 16, 16, 0, 60, ("index",)),
    ("k1_edge", 1, 16, 8, 1, 1000, ()),
    ("k7_odd_rank_order", 7, 32, 10, 0, 1500, ()),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fbits(v, vw):
    """float64 values (exact in the format) -> integer bit patterns of width vw."""
    b = np.asarray(v, dtype=np.float32).view(np.uint32).astype(np.int64)
    return b >> 16 if vw == 16 else b


def from_bits(b, vw):
    b = np.asarray(b, dtype=np.uint32) << (16 if vw == 16 else 0)
    return b.view(np.float32).astype(np.float64)


def expected(vals, labels, k, order):
    """The golden's selection over the array indexed by label: (label, ninf) in emission order."""
    pos = np.argsort(labels)
    arr, lab = np.asarray(vals, np.float64)[pos], np.asarray(labels)[pos]
    sel = G.topk_lowest_index(arr, min(k, len(arr)))
    out = [(int(lab[i]), bool(arr[i] == -np.inf)) for i in sel]
    return sorted(out) if order else out


# -- random segments -----------------------------------------------------------------
def alphabet(rng, vw):
    base = [0.0, -0.0, 1.0, -1.0, 2.0, 0.5, -0.5, np.inf, -np.inf, 3.0, -3.0, 1e-3]
    sub = 2.0 ** -133 if vw == 16 else 2.0 ** -149             # smallest positive subnormal
    base += [sub, -sub, 2 * sub]
    k = int(rng.integers(2, 7))
    return np.array(rng.choice(base, k, replace=False), dtype=np.float64)


def random_values(rng, n, vw):
    mode = rng.integers(0, 6)
    if mode <= 1:                                              # small alphabet: many ties
        v = rng.choice(alphabet(rng, vw), n)
    elif mode == 2:                                            # all equal
        v = np.full(n, rng.choice(alphabet(rng, vw)))
    elif mode == 3:                                            # coarse-quantised normals
        v = np.round(rng.standard_normal(n) * 4) / 4
    else:                                                      # raw bit patterns, NaN excluded
        b = rng.integers(0, 1 << vw, n)
        e = (b >> (vw - 9)) & 0xFF
        m = b & ((1 << (vw - 9)) - 1)
        b = np.where((e == 0xFF) & (m != 0), b & ~((1 << (vw - 9)) - 1), b)
        if mode == 5:                                          # few distinct patterns
            b = rng.choice(b[: max(1, n // 8)], n)
        v = from_bits(b, vw)
    return from_bits(fbits(v, vw), vw)                         # exact in the format


def random_segments(rng, K, vw, iw, nseg):
    segs = []
    kmax = (1 << int(np.ceil(np.log2(K + 1)))) - 1             # in_k's range
    cap = min(1 << iw, max(8 * K, 64))
    for _ in range(nseg):
        r = rng.random()
        n = int(1 if r < 0.05 else rng.integers(1, K + 1) if r < 0.3 else
                rng.integers(max(1, K - 2), K + 3) if r < 0.45 else rng.integers(K, min(cap, 4 * K + 8) + 1))
        n = max(1, min(n, 1 << iw))
        r = rng.random()
        k = K if r < 0.6 else int(rng.integers(0, kmax + 1))
        vals = random_values(rng, n, vw)
        r = rng.random()
        if r < 0.6:
            labels = np.arange(n)
        elif r < 0.8:
            labels = rng.permutation(n)
        else:
            labels = rng.choice(1 << iw, n, replace=False)
        segs.append((vals, labels, k))
    return segs


# -- real reduced-model data -----------------------------------------------------------
def real_sets(positions):
    """Stream the golden decode; return the SELECT inputs its three consumers see,
    each checked against the golden's own selection."""
    prompt, gen = G.prompt_and_expected()
    model = G.Model()
    state = model.new_state()
    seq = list(prompt) + list(gen)
    sets = {"router": [], "index": [], "candidate": []}
    checks = {"router": 0, "index": 0, "candidate": 0}
    for p in range(positions):
        tr = {}
        logits = model.decode_token(seq[p], p, state, trace=tr)
        if p + 1 >= len(seq):
            seq.append(int(np.argmax(logits)))
        for L in range(model.L):
            if f"L{L}.router" in tr:
                v = np.asarray(tr[f"L{L}.router"], np.float32).astype(np.float64)
                assert [i for i, _ in expected(v, np.arange(len(v)), model.k_exp, 1)] == tr[f"L{L}.experts"]
                sets["router"].append((v, np.arange(len(v)), model.k_exp))
                checks["router"] += 1
            if f"L{L}.index_scores" in tr:
                s = np.asarray(tr[f"L{L}.index_scores"], np.float64)
                n = len(s)
                assert [i for i, _ in expected(s, np.arange(n), model.topk, 1)] == tr[f"L{L}.index_select"]
                sets["index"].append((s, np.arange(n), model.topk))
                checks["index"] += 1
                if L == model.cand_src:
                    b = model.cand_b
                    nb = -(-n // b)
                    bs = np.concatenate([s, np.full(nb * b - n, -np.inf)]).reshape(nb, b).max(axis=1)
                    bs[(n - 1) // b] = np.inf
                    keep = model.candidate_blocks(s, n)[::b]
                    got = {i for i, ninf in expected(bs, np.arange(nb), model.cand_k, 1) if not ninf}
                    assert got == set(np.nonzero(keep)[0].tolist())
                    sets["candidate"].append((bs, np.arange(nb), model.cand_k))
                    checks["candidate"] += 1
    return sets, checks, {"positions": positions, "tokens": seq[:positions + 1],
                          "index_topk": model.topk, "candidate_topk_blocks": model.cand_k,
                          "candidate_block_size": model.cand_b, "router_topk": model.k_exp}


def write_vectors(segs, K, vw, iw, order, d: Path, tag):
    """Stimulus and expected files; the unit clamps a runtime k above K to K."""
    fin, fexp = d / f"{tag}.in", d / f"{tag}.exp"
    lines_in, lines_exp = [], []
    n_el = n_out = 0
    for vals, labels, k in segs:
        b = fbits(vals, vw)
        for j, (x, lab) in enumerate(zip(b, labels)):
            lines_in.append(f"{int(x):x} {int(lab):x} {int(j == len(b) - 1)} {k}\n")
        exp = expected(vals, labels, min(k, K), order)
        lines_exp.append(f"S {len(exp)}\n")
        lines_exp += [f"{i:x} {int(ninf)}\n" for i, ninf in exp]
        n_el += len(b)
        n_out += len(exp)
    fin.write_text("".join(lines_in))
    fexp.write_text("".join(lines_exp))
    h = hashlib.sha256(fin.read_bytes() + fexp.read_bytes()).hexdigest()
    return fin, fexp, n_el, n_out, h


def parse(out):
    m = LINE.search(out)
    if not m:
        return {"pass": False, "log": out[-2000:]}
    k, vw, iw, order, segs, el, outs, err, lmin, lmax, lexp, cyc, stall = map(int, m.groups())
    return {"segments": segs, "elements": el, "outputs": outs, "errors": err, "latency_min": lmin,
            "latency_max": lmax, "latency_expected": lexp, "cycles": cyc, "stall_cycles": stall,
            "pass": "PASS" in out and err == 0}


def run(positions) -> dict:
    sets, checks, real_meta = real_sets(positions)
    configs, ok = [], True
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        lint = {}
        for name, K, vw, iw, order, nseg, real in CONFIGS:
            r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, f"-GK={K}", f"-GVW={vw}", f"-GIW={iw}",
                                f"-GORDER={order}", "--top-module", "ot_hdc_select", str(RTL)],
                               capture_output=True, text=True)
            lint[name] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:10]}
            ok &= r.returncode == 0
        for ci, (name, K, vw, iw, order, nseg, real) in enumerate(CONFIGS):
            rng = np.random.default_rng(1000 + ci)
            segs = random_segments(rng, K, vw, iw, nseg)
            n_rand = len(segs)
            real_counts = {}
            for kind in real:
                src = sets["index" if kind == "index_all" else kind]
                for vals, labels, k in src:
                    segs.append((vals, labels, K if kind == "index_all" else k))
                real_counts[kind] = len(src)
            # real segments interleaved with random ones, reproducibly
            perm = np.random.default_rng(2000 + ci).permutation(len(segs))
            segs = [segs[i] for i in perm]
            fin, fexp, n_el, n_out, vec_sha = write_vectors(segs, K, vw, iw, order, s, name)
            obj = s / f"obj_{name}"
            subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "--top-module",
                            "tb_hdc_select", f"-GK={K}", f"-GVW={vw}", f"-GIW={iw}", f"-GORDER={order}",
                            "-Mdir", str(obj), str(RTL), str(TB), str(HARNESS), "-CFLAGS", "-O1"],
                           check=True, capture_output=True)
            runs = {}
            for mode, bub, gap, seed in (("back_to_back", 0, 0, 1), ("bubbles_and_gaps", 30, 20, 7)):
                out = subprocess.run([str(obj / "Vtb_hdc_select"), f"+IN={fin}", f"+EXP={fexp}", f"+BUBBLE={bub}",
                                      f"+GAP={gap}", f"+SEED={seed}"], capture_output=True, text=True).stdout
                rec = parse(out)
                rec.update({"simulator": "verilator", "bubble_percent": bub, "gap_percent": gap, "seed": seed})
                rec["pass"] = rec["pass"] and rec.get("segments") == len(segs) and rec.get("outputs") == n_out \
                    and rec.get("elements") == n_el
                runs[mode] = rec
            if ci == 0:
                vvp = s / "icarus.vvp"
                subprocess.run(["iverilog", "-g2012", f"-Ptb_hdc_select.K={K}", f"-Ptb_hdc_select.VW={vw}",
                                f"-Ptb_hdc_select.IW={iw}", f"-Ptb_hdc_select.ORDER={order}", "-o", str(vvp),
                                str(TB), str(RTL)], check=True, capture_output=True)
                out = subprocess.run(["vvp", "-n", str(vvp), f"+IN={fin}", f"+EXP={fexp}", "+BUBBLE=30",
                                      "+GAP=20", "+SEED=7"], capture_output=True, text=True).stdout
                rec = parse(out)
                rec.update({"simulator": "icarus", "bubble_percent": 30, "gap_percent": 20, "seed": 7})
                rec["pass"] = rec["pass"] and rec.get("segments") == len(segs) and rec.get("outputs") == n_out
                runs["icarus_bubbles_and_gaps"] = rec
            cfg_ok = all(r["pass"] for r in runs.values())
            ok &= cfg_ok
            configs.append({"name": name, "K": K, "value_width": vw, "index_width": iw,
                            "order": "ascending index" if order else "rank",
                            "latency_cycles": K + 2 + (K if order else 0),
                            "random_segments": n_rand, "real_segments": real_counts, "elements": n_el,
                            "expected_outputs": n_out, "vectors_sha256": vec_sha, "runs": runs,
                            "pass": cfg_ok})
            print(name, "pass" if cfg_ok else "FAIL", {m: (r.get("errors"), r.get("cycles")) for m, r in runs.items()},
                  flush=True)
    status = "pass" if ok and all(checks[k] > 0 for k in checks) else "fail"
    return {
        "schema": "opentallas.hdc-v41-select-campaign.v1",
        "status": status,
        "claim_boundary": "functional cycle-level RTL simulation of the SELECT unit alone against "
                          "tools/hdc_golden_v41.py topk_lowest_index; clock rate is not claimed here -- "
                          "see results/physical_abi3/asap7/hdc/v41/.",
        "semantics": "k largest values, ties to the lower index, -0 == +0; NaN outside the contract",
        "latency_definition": "clock edges from the edge that accepts a segment's last element to the edge "
                              "that registers its first output: K + 2 (+ K for ascending-index order)",
        "real_data": dict(real_meta, golden_selection_checks=checks),
        "configurations": configs,
        "verilator_lint": {"flags": list(LINT_FLAGS), "configurations": lint},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (RTL, TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--positions", type=int, default=REAL_POSITIONS)
    args = parser.parse_args()
    result = run(args.positions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
