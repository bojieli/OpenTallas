#!/usr/bin/env python3
"""RTL campaign for the V4.1 threshold SELECT (rtl/hdc/v41/ot_hdc_tselect.sv).

The unit replaces ot_hdc_select on the indexer's top-512: a W-lane radix select
(hi-digit histogram while the scores stream in, a lo-digit histogram of the
boundary bucket, then one compaction pass) whose output is already in position
order.  Every expected output comes from tools/hdc_golden_v41.py's
`topk_lowest_index` (value descending, ties to the lower index, -0 == +0),
emitted in ascending position order with the selected value and a -inf flag:

* random segments with MANY ties (small value alphabets holding +0/-0, +/-inf
  and subnormals, all-equal segments, coarse-quantised normals, raw BF16 bit
  patterns with NaN excluded), runtime k from 0 to past K, ascending positions
  dense or sparse, random lane masks (empty lanes and empty beats), lengths
  from one element to the full line memory;
* real reduced DeepSeek-V4.1 data from rtl_hdc_v41_select_campaign.real_sets:
  every indexer's BF16 scores (-inf where the candidate mask removed a
  position) and the candidate-block scores, each checked there against the
  golden's own `index_select` / keep mask;
* the two-level decomposition the critical path prices: a long score array is
  split into G contiguous position ranges, each range's top-k is selected by
  the RTL, the G RTL outputs are concatenated in range order and selected
  again by the RTL, and the result must equal the golden's top-k of the whole
  array;
* a mutation check: each of a list of single-point RTL mutations must make the
  (reduced) campaign fail.

Verilator 4.038 back to back and with random bubbles and idle gaps; one
configuration also under Icarus.  Writes results/rtl/hdc_v41_tselect_campaign.json.
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
import rtl_hdc_v41_select_campaign as SC  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_tselect_campaign.json"
RTL = ROOT / "rtl/hdc/v41/ot_hdc_tselect.sv"
TB = ROOT / "rtl/test/tb_hdc_tselect.sv"
HARNESS = ROOT / "rtl/test/hdc_tselect_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/rtl_hdc_v41_select_campaign.py", Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED")
LINE = re.compile(r"TSELECT W=(\d+) VW=(\d+) IW=(\d+) K=(\d+) segments=(\d+) beats=(\d+) elements=(\d+) "
                  r"outputs=(\d+) out_beats=(\d+) errors=(\d+) lat0_min=(-?\d+) lat0_max=(-?\d+) cycles=(\d+)")
VW = 16


def lat0(w):
    """LAT0 for W lanes: walk 1 (DRAIN 10 + 8 two-edge steps), walk 2 (10 + 16), pass-3 pipeline:
    read, compare, prefix, select, z, NCR compaction stages, NCR rotate stages, output."""
    ncr = (int(np.log2(w)) + 1) // 2
    return 26 + 26 + 5 + 2 * ncr


# name, W, IW, K, AW, random segments, real sets, hierarchy trials
CONFIGS = [
    ("index_topk_shipped_w64", 64, 16, 512, 10, 160, ("index", "index_all"), 12),
    ("index_topk_shipped_w32", 32, 16, 512, 11, 60, ("index",), 4),
    ("index_topk_reduced_w8", 8, 16, 16, 10, 1500, ("index",), 40),
    ("candidate_blocks_reduced_w16", 16, 12, 64, 8, 600, ("candidate",), 0),
    ("k7_w4_edge", 4, 10, 7, 8, 1500, (), 40),
]
MUTATION_CONFIG = ("mutation_w8", 8, 16, 16, 8, 400, (), 8)
MUTATIONS = [
    ("tie to the higher index", "c2_pre[(LW+1)*l +: LW+1]} < rem", "c2_pre[(LW+1)*l +: LW+1]} <= rem"),
    # (walking right only on a strict excess, `>` for `>=`, is an EQUIVALENT mutant: it lands on a lower
    # bucket with quota 0 and threshold {B, max lo}, which selects the same set -- so it is not listed)
    ("boundary quota ignores the count above it", "mq <= wrest;", "mq <= wkq;"),
    ("-0 not canonicalised to +0", "fkey = (v[VW-2:0] == 0) ?", "fkey = (v[VW-1:0] == 0) ?"),
    ("strict threshold compare dropped", "c1_gt_d[gl] = lv && (k > tkey);", "c1_gt_d[gl] = lv && (k >= tkey);"),
    ("pass-2 histogram ignores the boundary bucket", "k[VW-1 -: RB] == bsel);", "1'b1);"),
    ("tie remainder not carried across beats", "else if (c2_v) rem <=", "else if (1'b0) rem <="),
    ("compaction shift counts the lane itself", "sel_inc[(LW+1)*(gl-1) +: LW+1];", "sel_inc[(LW+1)*gl +: LW+1];"),
    ("tree walk starts two edges early", "localparam integer DRAIN = 3 + RB - 1;", "localparam integer DRAIN = 3 + RB - 3;"),
    ("empty lanes counted in the histogram", "e  = hs_ing ? s0_lv[gl] :", "e  = hs_ing ? 1'b1 :"),
    ("rotate ignores the running fill", "if (cp_v) frun <= cp_l ?", "if (1'b0) frun <= cp_l ?"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bits16(v):
    return (np.asarray(v, np.float32).view(np.uint32) >> 16).astype(np.int64)


def expected(vals, k):
    """Golden selection of the array (stream order = position order): sorted positions."""
    v = np.asarray(vals, np.float64)
    return sorted(int(i) for i in G.topk_lowest_index(v, min(k, len(v))))


def random_segment(rng, W, iw, K, AW):
    cap = min((1 << AW) * W, 1 << iw)
    r = rng.random()
    n = int(1 if r < 0.04 else rng.integers(1, K + 1) if r < 0.25 else
            rng.integers(max(1, K - 2), K + 3) if r < 0.4 else
            rng.integers(K, min(cap, 8 * K + 8) + 1) if r < 0.85 else rng.integers(1, cap // 2 + 1))
    n = max(1, min(n, cap // 2))                  # leave room for empty lanes
    kmax = (1 << int(np.ceil(np.log2(K + 1)))) - 1
    k = K if rng.random() < 0.6 else int(rng.integers(0, kmax + 1))
    vals = SC.random_values(rng, n, VW)
    if rng.random() < 0.6:
        pos = np.arange(n)
    else:
        pos = np.sort(rng.choice(1 << iw, n, replace=False))
    return vals, pos, k


def to_beats(rng, vals, pos, W, dense):
    """Pack an ordered segment into beats with random lane masks: list of [(val bits, pos) or None] * W."""
    b = bits16(vals)
    beats, i, n = [], 0, len(b)
    while i < n:
        lanes = [None] * W
        if dense:
            fill = np.ones(W, bool)
        else:
            p = rng.choice([1.0, 0.9, 0.5, 0.1, 0.0], p=[0.5, 0.2, 0.15, 0.1, 0.05])
            fill = rng.random(W) < p
        for j in range(W):
            if fill[j] and i < n:
                lanes[j] = (int(b[i]), int(pos[i]))
                i += 1
        beats.append(lanes)
    if not beats:
        beats.append([None] * W)
    return beats


def write_vectors(segs, W, K, d: Path, tag):
    """segs: list of (beats, k, expected [(pos, valbits, ninf)])."""
    fin, fexp = d / f"{tag}.in", d / f"{tag}.exp"
    li, le = [], []
    n_el = n_out = n_beats = 0
    for beats, k, exp in segs:
        for bi, lanes in enumerate(beats):
            lv = sum(1 << j for j, e in enumerate(lanes) if e is not None)
            fields = " ".join(f"{e[0]:x} {e[1]:x}" if e else "0 0" for e in lanes)
            li.append(f"{int(bi == len(beats) - 1)} {k} {lv:x} {fields}\n")
            n_el += sum(e is not None for e in lanes)
        n_beats += len(beats)
        le.append(f"S {len(exp)} {len(beats)}\n")
        le += [f"{p:x} {vb:x} {int(ni)}\n" for p, vb, ni in exp]
        n_out += len(exp)
    fin.write_text("".join(li))
    fexp.write_text("".join(le))
    h = hashlib.sha256(fin.read_bytes() + fexp.read_bytes()).hexdigest()
    return fin, fexp, dict(elements=n_el, expected_outputs=n_out, beats=n_beats, vectors_sha256=h)


def seg_record(rng, vals, pos, k, K, W, dense=False):
    b = bits16(vals)
    sel = expected(vals, min(k, K))
    exp = [(int(pos[i]), int(b[i]), bool(vals[i] == -np.inf)) for i in sel]
    return (to_beats(rng, vals, pos, W, dense), k, exp)


def parse(out):
    m = LINE.search(out)
    if not m:
        return {"pass": False, "log": out[-2000:]}
    (w, vw, iw, k, segs, beats, el, outs, obeats, err, lmin, lmax, cyc) = map(int, m.groups())
    return {"segments": segs, "beats": beats, "elements": el, "outputs": outs, "out_beats": obeats,
            "errors": err, "lat0_min": lmin, "lat0_max": lmax, "cycles": cyc,
            "pass": "PASS" in out and err == 0}


def build(obj: Path, rtl: Path, W, iw, K, AW):
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "--top-module", "tb_hdc_tselect",
                    f"-GW={W}", f"-GIW={iw}", f"-GK={K}", f"-GAW={AW}", "-Mdir", str(obj), str(rtl), str(TB),
                    str(HARNESS), "-CFLAGS", "-O1"], check=True, capture_output=True)
    return obj / "Vtb_hdc_tselect"


def simulate(binary, fin, fexp, bub=0, gap=0, seed=1, out=None):
    args = [str(binary), f"+IN={fin}", f"+EXP={fexp}", f"+BUBBLE={bub}", f"+GAP={gap}", f"+SEED={seed}"]
    if out:
        args.append(f"+OUT={out}")
    return parse(subprocess.run(args, capture_output=True, text=True).stdout)


def read_out(path: Path):
    segs, cur = [], []
    for ln in path.read_text().splitlines():
        if ln == "E":
            segs.append(cur)
            cur = []
        else:
            p, v, ni = ln.split()
            cur.append((int(p, 16), int(v, 16), int(ni)))
    return segs


def hierarchy(rng, binary, W, iw, K, trials, s: Path, tag):
    """Local top-k of G contiguous ranges on the RTL, then the RTL merge of the G outputs."""
    locs, arrays = [], []
    for t in range(trials):
        g = int(rng.choice([2, 4, 4, 4, 8]))
        per = int(rng.integers(max(1, K // 2), min((1 << iw) // g, 32 * K) + 1))
        n = g * per
        vals = SC.random_values(rng, n, VW)
        if rng.random() < 0.3:                   # heavy ties across the boundary between ranges
            vals = np.asarray(rng.choice([1.0, 0.5, -0.0, 0.0, 2.0], n), np.float64)
        pos = np.arange(n)
        arrays.append((vals, g, per))
        for d in range(g):
            sl = slice(d * per, (d + 1) * per)
            locs.append(seg_record(rng, vals[sl], pos[sl], K, K, W))
    fin, fexp, st1 = write_vectors(locs, W, K, s, f"{tag}_local")
    r1 = simulate(binary, fin, fexp, out=s / f"{tag}_local.out")
    got = read_out(s / f"{tag}_local.out") if r1.get("pass") else []
    merges, i = [], 0
    for vals, g, per in arrays:
        cat = [e for d in range(g) for e in got[i + d]] if got else []
        i += g
        b = bits16(vals)
        full = expected(vals, K)
        exp = [(int(p), int(b[p]), bool(vals[p] == -np.inf)) for p in full]
        cvals = np.array([SC.from_bits(np.array([vb]), VW)[0] for _, vb, _ in cat]) if cat else np.zeros(0)
        cpos = np.array([p for p, _, _ in cat], np.int64)
        merges.append((to_beats(rng, cvals, cpos, W, False), K, exp))
    fin2, fexp2, st2 = write_vectors(merges, W, K, s, f"{tag}_merge")
    r2 = simulate(binary, fin2, fexp2, bub=20, gap=10, seed=3)
    return {"trials": trials, "local_segments": len(locs), "local": dict(st1, **r1), "merge": dict(st2, **r2),
            "pass": bool(r1.get("pass") and r2.get("pass") and len(got) == len(locs))}


def config_segments(ci, W, iw, K, AW, nseg, real, sets):
    rng = np.random.default_rng(3000 + ci)
    segs = [seg_record(rng, *random_segment(rng, W, iw, K, AW), K, W) for _ in range(nseg)]
    counts = {}
    for kind in real:
        src = sets["index" if kind == "index_all" else kind]
        for vals, labels, k in src:
            segs.append(seg_record(rng, vals, np.asarray(labels), K if kind == "index_all" else k, K, W,
                                   dense=True))
        counts[kind] = len(src)
    # one full-memory segment of ties and one dense full-memory random segment
    n = min((1 << AW) * W, 1 << iw)
    segs.append(seg_record(rng, np.full(n, 1.0), np.arange(n), K, K, W, dense=True))
    segs.append(seg_record(rng, SC.random_values(rng, n, VW), np.arange(n), K, K, W, dense=True))
    perm = np.random.default_rng(4000 + ci).permutation(len(segs))
    return [segs[i] for i in perm], counts, nseg + 2


def run_config(ci, cfg, sets, s: Path, rtl=RTL, icarus=False, modes=None):
    name, W, iw, K, AW, nseg, real, htrials = cfg
    segs, counts, n_rand = config_segments(ci, W, iw, K, AW, nseg, real, sets)
    fin, fexp, st = write_vectors(segs, W, K, s, name)
    binary = build(s / f"obj_{name}", rtl, W, iw, K, AW)
    runs = {}
    for mode, bub, gap, seed in modes or (("back_to_back", 0, 0, 1), ("bubbles_and_gaps", 30, 20, 7)):
        rec = simulate(binary, fin, fexp, bub, gap, seed)
        rec.update({"simulator": "verilator", "bubble_percent": bub, "gap_percent": gap, "seed": seed})
        rec["pass"] = bool(rec["pass"] and rec.get("segments") == len(segs) and rec.get("outputs") ==
                           st["expected_outputs"] and rec.get("elements") == st["elements"] and
                           rec.get("lat0_min", -1) >= lat0(W) and rec.get("lat0_max", 99) <= lat0(W) + 1)
        runs[mode] = rec
    if icarus:
        vvp = s / f"{name}.vvp"
        subprocess.run(["iverilog", "-g2012", f"-Ptb_hdc_tselect.W={W}", f"-Ptb_hdc_tselect.IW={iw}",
                        f"-Ptb_hdc_tselect.K={K}", f"-Ptb_hdc_tselect.AW={AW}", "-o", str(vvp), str(TB), str(rtl)],
                       check=True, capture_output=True)
        out = subprocess.run(["vvp", "-n", str(vvp), f"+IN={fin}", f"+EXP={fexp}", "+BUBBLE=30", "+GAP=20",
                              "+SEED=7"], capture_output=True, text=True).stdout
        rec = parse(out)
        rec.update({"simulator": "icarus", "bubble_percent": 30, "gap_percent": 20, "seed": 7})
        rec["pass"] = bool(rec["pass"] and rec.get("segments") == len(segs) and
                           rec.get("outputs") == st["expected_outputs"])
        runs["icarus_bubbles_and_gaps"] = rec
    hier = hierarchy(np.random.default_rng(5000 + ci), binary, W, iw, K, htrials, s, name) if htrials else None
    ok = all(r["pass"] for r in runs.values()) and (hier is None or hier["pass"])
    return {"name": name, "lanes": W, "value_width": VW, "index_width": iw, "K": K, "line_address_width": AW,
            "latency_cycles": f"2 x beats + {lat0(W)} (+1 when the final pass-3 beat overflows the partial line)",
            "lat0": lat0(W), "random_segments": n_rand, "real_segments": counts, **st, "runs": runs,
            "two_level": hier, "pass": ok}


def mutations(s: Path, sets):
    """The unmutated RTL must pass the mutation configuration (the control), each mutant must fail it."""
    out = []
    src = RTL.read_text()
    cdir = s / "mut_control"
    cdir.mkdir()
    ctrl = run_config(90, MUTATION_CONFIG, sets, cdir, modes=(("back_to_back", 0, 0, 1),))
    out.append({"mutation": "none (control)", "caught": not ctrl["pass"], "control": True,
                "detail": {k: v.get("errors") for k, v in ctrl["runs"].items()}})
    print("mutation control", "pass" if ctrl["pass"] else "FAIL", flush=True)
    for i, (what, a, b) in enumerate(MUTATIONS):
        assert src.count(a) == 1, (what, src.count(a))
        mdir = s / f"mut{i}"
        mdir.mkdir()
        m = mdir / "ot_hdc_tselect.sv"
        m.write_text(src.replace(a, b))
        try:
            rec = run_config(90, MUTATION_CONFIG, sets, mdir, rtl=m, modes=(("back_to_back", 0, 0, 1),))
            caught = not rec["pass"]
            detail = {k: v.get("errors") for k, v in rec["runs"].items()}
        except subprocess.CalledProcessError as e:
            caught, detail = True, {"build_failed": e.stderr[-300:] if e.stderr else ""}
        out.append({"mutation": what, "caught": caught, "detail": detail})
        print("mutation", what, "caught" if caught else "MISSED", flush=True)
    return out


def run(positions, quick=False) -> dict:
    src = RTL.read_text()
    for what, a, _ in MUTATIONS:                   # every mutation site exists exactly once
        assert src.count(a) == 1, (what, src.count(a))
    sets, checks, real_meta = SC.real_sets(positions)
    configs, ok = [], True
    lint = {}
    for name, W, iw, K, AW, *_ in CONFIGS:
        r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, f"-GW={W}", f"-GIW={iw}", f"-GK={K}",
                            f"-GAW={AW}", "--top-module", "ot_hdc_tselect", str(RTL)], capture_output=True, text=True)
        lint[name] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:10]}
        ok &= r.returncode == 0
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        for ci, cfg in enumerate(CONFIGS[2:3] if quick else CONFIGS):
            rec = run_config(ci, cfg, sets, s, icarus=(cfg[0] == "k7_w4_edge"))
            ok &= rec["pass"]
            configs.append(rec)
            print(cfg[0], "pass" if rec["pass"] else "FAIL",
                  {m: (r.get("errors"), r.get("lat0_min"), r.get("lat0_max")) for m, r in rec["runs"].items()},
                  "two-level", None if rec["two_level"] is None else rec["two_level"]["pass"], flush=True)
        muts = [] if quick else mutations(s, sets)
        ok &= all(m["caught"] != bool(m.get("control")) for m in muts)
    status = "pass" if ok and all(checks[k] > 0 for k in checks) else "fail"
    return {
        "schema": "opentallas.hdc-v41-tselect-campaign.v1",
        "status": status,
        "claim_boundary": "functional cycle-level RTL simulation of the threshold SELECT alone (behavioural line "
                          "memory in the bench) against tools/hdc_golden_v41.py topk_lowest_index; clock rate and "
                          "area are in results/physical_abi3/asap7/hdc/v41/ot_hdc_tselect_w64/.",
        "semantics": "k largest values, ties to the lower index, -0 == +0, emitted in ascending position order; "
                     "NaN outside the contract; input positions must ascend in stream order",
        "latency_definition": "clock edges from the edge that accepts a segment's last beat to the edge that "
                              "registers its out_last beat: 2 x beats + LAT0 (+1 when the final pass-3 beat "
                              "overflows the partial output line)",
        "real_data": dict(real_meta, golden_selection_checks=checks),
        "configurations": configs,
        "mutations": muts,
        "verilator_lint": {"flags": list(LINT_FLAGS), "configurations": lint},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (RTL, TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--positions", type=int, default=SC.REAL_POSITIONS)
    parser.add_argument("--quick", action="store_true", help="one reduced configuration, no mutations")
    args = parser.parse_args()
    result = run(args.positions, args.quick)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
