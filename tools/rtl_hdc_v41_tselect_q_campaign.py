#!/usr/bin/env python3
"""RTL campaign for the quartered V4.1 threshold SELECT (rtl/hdc/v41/ot_hdc_tselect_q.sv).

Q x W-lane ot_hdc_tselect datapaths share one threshold: a segment is split into
Q contiguous position ranges, each streamed on its own port, and quarter q emits
its part of the selection; the concatenation in quarter order must be the
golden's selection (tools/hdc_golden_v41.py `topk_lowest_index`, value
descending, ties to the lower index, -0 == +0) in position order.  Stimulus is
the single-unit campaign's (tools/rtl_hdc_v41_tselect_campaign.py): tie-heavy
random segments, raw BF16 patterns, runtime k from 0 to past K, dense and
sparse ascending positions, random lane masks, full-memory segments, and the
real reduced DeepSeek-V4.1 indexer and candidate-block selections -- split at
random points into Q quarters (empty quarters included, ties straddling the
split points), so the cross-quarter tie quota is exercised.  Also the two-level
decomposition (G = Q dies, each die's range selected by the RTL in Q quarters,
then the RTL merge with one die per quarter) and a mutation check with an
unmutated control.  Writes results/rtl/hdc_v41_tselect_q_campaign.json.
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
import hdc_golden_v41 as G  # noqa: E402,F401
import rtl_hdc_v41_select_campaign as SC  # noqa: E402
import rtl_hdc_v41_tselect_campaign as T  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_tselect_q_campaign.json"
RTL = ROOT / "rtl/hdc/v41/ot_hdc_tselect_q.sv"
HELPERS = ROOT / "rtl/hdc/v41/ot_hdc_tselect.sv"
TB = ROOT / "rtl/test/tb_hdc_tselect_q.sv"
HARNESS = ROOT / "rtl/test/hdc_tselect_q_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/rtl_hdc_v41_select_campaign.py",
         ROOT / "tools/rtl_hdc_v41_tselect_campaign.py", Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED")
LINE = re.compile(r"TSELECTQ Q=(\d+) W=(\d+) VW=(\d+) IW=(\d+) K=(\d+) segments=(\d+) beats=(\d+) elements=(\d+) "
                  r"outputs=(\d+) out_beats=(\d+) errors=(\d+) lat0_min=(-?\d+) lat0_max=(-?\d+) cycles=(\d+)")


def lat0(w):
    """ot_hdc_tselect's LAT0 + 2: each walk's drain has one more edge (the registered leaf sums)."""
    return T.lat0(w) + 2


# name, Q, W, IW, K, AW, random segments, real sets, two-level trials
CONFIGS = [
    ("index_topk_shipped_q4_w16", 4, 16, 16, 512, 10, 160, ("index", "index_all"), 12),
    ("index_topk_reduced_q4_w4", 4, 4, 16, 16, 10, 1500, ("index",), 40),
    ("candidate_blocks_reduced_q4_w4", 4, 4, 12, 64, 8, 600, ("candidate",), 0),
    ("k7_q2_w8_edge", 2, 8, 10, 7, 8, 1500, (), 40),
    ("single_quarter_q1_w8", 1, 8, 16, 16, 10, 800, ("index",), 0),
]
MUTATION_CONFIG = ("mutation_q4_w4", 4, 4, 16, 16, 8, 400, (), 8)
MUTATIONS = [
    ("tie quota ignores ties in earlier quarters", "rem <= (trest > epq) ? trest - epq : {QW{1'b0}};", "rem <= trest;"),
    ("earlier-quarter tie count includes the quarter itself", "eqpre[CW*i +: CW] = eacc;",
     "eqpre[CW*i +: CW] = eacc + {{QB{1'b0}}, hbq[(i*NB)*CWQ + CWQ*lsel +: CWQ]};"),
    ("passes stop at quarter 0's lines", "if (nlast_v[AW*i +: AW] > mx) mx", "if (i == 0) mx"),
    ("tie to the higher index", "c2_pre[(LW+1)*ll +: LW+1]} < rem", "c2_pre[(LW+1)*ll +: LW+1]} <= rem"),
    ("strict threshold compare dropped", "assign c1_gt_d[gl] = lv && (k > tkey);",
     "assign c1_gt_d[gl] = lv && (k >= tkey);"),
    ("-0 not canonicalised to +0", "fkey = (v[VW-2:0] == 0) ?", "fkey = (v[VW-1:0] == 0) ?"),
    ("pass-2 histogram ignores the boundary bucket", "k[VW-1 -: RB] == bsel);", "1'b1);"),
    ("tie remainder not carried across beats", "else if (c2_v) rem <=", "else if (1'b0) rem <="),
    ("empty lanes counted in the histogram", "e  = hs_ing ? s0_lv[gl] :", "e  = hs_ing ? 1'b1 :"),
    ("rotate ignores the running fill", "if (cp_v) frun <= cp_l ?", "if (1'b0) frun <= cp_l ?"),
    ("tree walk starts two edges early", "localparam integer DRAIN = 5 + RB - 1;",
     "localparam integer DRAIN = 5 + RB - 3;"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_points(rng, n, Q):
    """Q contiguous ranges of 0..n: random cut points (empty ranges allowed) or an even split."""
    if Q == 1:
        return [0, n]
    if rng.random() < 0.5:
        cuts = sorted(int(c) for c in rng.integers(0, n + 1, Q - 1))
    else:
        cuts = [(n * j) // Q for j in range(1, Q)]
    return [0] + cuts + [n]


def seg_record_q(rng, vals, pos, k, K, W, Q, dense=False, cuts=None):
    """(per-quarter beats, k, per-quarter expected) of one segment split into Q contiguous ranges."""
    vals = np.asarray(vals, np.float64)
    pos = np.asarray(pos)
    b = T.bits16(vals)
    sel = T.expected(vals, min(k, K))
    cuts = cuts or split_points(rng, len(vals), Q)
    beats, exps = [], []
    for q in range(Q):
        lo, hi = cuts[q], cuts[q + 1]
        beats.append(T.to_beats(rng, vals[lo:hi], pos[lo:hi], W, dense))
        exps.append([(int(pos[i]), int(b[i]), bool(vals[i] == -np.inf)) for i in sel if lo <= i < hi])
    return beats, k, exps


def write_vectors(segs, W, Q, d: Path, tag):
    pfx = d / tag
    stats = dict(elements=0, expected_outputs=0, beats=0)
    h = hashlib.sha256()
    for q in range(Q):
        li, le = [], []
        for beats, k, exps in segs:
            bq = beats[q]
            for bi, lanes in enumerate(bq):
                lv = sum(1 << j for j, e in enumerate(lanes) if e is not None)
                fields = " ".join(f"{e[0]:x} {e[1]:x}" if e else "0 0" for e in lanes)
                li.append(f"{int(bi == len(bq) - 1)} {k} {lv:x} {fields}\n")
                stats["elements"] += sum(e is not None for e in lanes)
            stats["beats"] += len(bq)
            le.append(f"S {len(exps[q])} {len(bq)}\n")
            le += [f"{p:x} {vb:x} {int(ni)}\n" for p, vb, ni in exps[q]]
            stats["expected_outputs"] += len(exps[q])
        Path(f"{pfx}.in{q}").write_text("".join(li))
        Path(f"{pfx}.exp{q}").write_text("".join(le))
        h.update(Path(f"{pfx}.in{q}").read_bytes() + Path(f"{pfx}.exp{q}").read_bytes())
    stats["vectors_sha256"] = h.hexdigest()
    return pfx, stats


def parse(out):
    m = LINE.search(out)
    if not m:
        return {"pass": False, "log": out[-2000:]}
    (q, w, vw, iw, k, segs, beats, el, outs, obeats, err, lmin, lmax, cyc) = map(int, m.groups())
    return {"segments": segs, "beats": beats, "elements": el, "outputs": outs, "out_beats": obeats,
            "errors": err, "lat0_min": lmin, "lat0_max": lmax, "cycles": cyc, "pass": "PASS" in out and err == 0}


def build(obj: Path, rtl: Path, Q, W, iw, K, AW):
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "--top-module", "tb_hdc_tselect_q",
                    f"-GQ={Q}", f"-GW={W}", f"-GIW={iw}", f"-GK={K}", f"-GAW={AW}", "-Mdir", str(obj), str(rtl),
                    str(HELPERS), str(TB), str(HARNESS), "-CFLAGS", "-O1"], check=True, capture_output=True)
    return obj / "Vtb_hdc_tselect_q"


def simulate(binary, pfx, bub=0, gap=0, seed=1, out=False):
    args = [str(binary), f"+PFX={pfx}", f"+BUBBLE={bub}", f"+GAP={gap}", f"+SEED={seed}"] + (["+OUT=1"] if out else [])
    return parse(subprocess.run(args, capture_output=True, text=True).stdout)


def read_out(pfx, Q):
    """Per segment, the concatenation of the Q quarters' outputs."""
    per_q = [T.read_out(Path(f"{pfx}.out{q}")) for q in range(Q)]
    return [[e for q in range(Q) for e in per_q[q][s]] for s in range(len(per_q[0]))]


def hierarchy(rng, binary, Q, W, iw, K, trials, s: Path, tag):
    """G = Q dies: each die's contiguous range selected by the RTL (in Q quarters), then the RTL merge
    of the G die lists (one die per quarter); must equal the golden top-k of the whole array."""
    locs, arrays = [], []
    for t in range(trials):
        per = int(rng.integers(max(1, K // 2), min((1 << iw) // Q, 32 * K) + 1))
        n = Q * per
        vals = SC.random_values(rng, n, T.VW)
        if rng.random() < 0.3:
            vals = np.asarray(rng.choice([1.0, 0.5, -0.0, 0.0, 2.0], n), np.float64)
        arrays.append(vals)
        for d in range(Q):
            sl = slice(d * per, (d + 1) * per)
            locs.append(seg_record_q(rng, vals[sl], np.arange(n)[sl], K, K, W, Q))
    pfx1, st1 = write_vectors(locs, W, Q, s, f"{tag}_local")
    r1 = simulate(binary, pfx1, out=True)
    got = read_out(pfx1, Q) if r1.get("pass") else []
    merges = []
    for t, vals in enumerate(arrays):
        dies = got[t * Q:(t + 1) * Q] if got else [[] for _ in range(Q)]
        cat = [e for d in dies for e in d]
        cuts = [0]
        for d in dies:
            cuts.append(cuts[-1] + len(d))
        cvals = np.array([SC.from_bits(np.array([vb]), T.VW)[0] for _, vb, _ in cat]) if cat else np.zeros(0)
        cpos = np.array([p for p, _, _ in cat], np.int64)
        b = T.bits16(vals)
        full = T.expected(vals, K)
        rec = seg_record_q(rng, cvals, cpos, K, K, W, Q, cuts=cuts)
        # the merge's expected output is the golden top-k of the WHOLE array, split by die
        per = len(vals) // Q
        exps = [[(int(p), int(b[p]), bool(vals[p] == -np.inf)) for p in full if d * per <= p < (d + 1) * per]
                for d in range(Q)]
        merges.append((rec[0], K, exps))
    pfx2, st2 = write_vectors(merges, W, Q, s, f"{tag}_merge")
    r2 = simulate(binary, pfx2, bub=20, gap=10, seed=3)
    return {"trials": trials, "local_segments": len(locs), "local": dict(st1, **r1), "merge": dict(st2, **r2),
            "pass": bool(r1.get("pass") and r2.get("pass") and len(got) == len(locs))}


def config_segments(ci, Q, W, iw, K, AW, nseg, real, sets):
    rng = np.random.default_rng(6000 + ci)
    segs = []
    for _ in range(nseg):
        vals, pos, k = T.random_segment(rng, W, iw, K, AW)
        segs.append(seg_record_q(rng, vals, pos, k, K, W, Q))
    counts = {}
    for kind in real:
        src = sets["index" if kind == "index_all" else kind]
        for vals, labels, k in src:
            segs.append(seg_record_q(rng, vals, np.asarray(labels), K if kind == "index_all" else k, K, W, Q,
                                     dense=True))
        counts[kind] = len(src)
    n = min((1 << AW) * W * Q, 1 << iw)
    segs.append(seg_record_q(rng, np.full(n, 1.0), np.arange(n), K, K, W, Q, dense=True,
                             cuts=[(n * j) // Q for j in range(Q + 1)]))
    segs.append(seg_record_q(rng, SC.random_values(rng, n, T.VW), np.arange(n), K, K, W, Q, dense=True,
                             cuts=[(n * j) // Q for j in range(Q + 1)]))
    perm = np.random.default_rng(7000 + ci).permutation(len(segs))
    return [segs[i] for i in perm], counts, nseg + 2


def run_config(ci, cfg, sets, s: Path, rtl=RTL, icarus=False, modes=None):
    name, Q, W, iw, K, AW, nseg, real, htrials = cfg
    segs, counts, n_rand = config_segments(ci, Q, W, iw, K, AW, nseg, real, sets)
    pfx, st = write_vectors(segs, W, Q, s, name)
    binary = build(s / f"obj_{name}", rtl, Q, W, iw, K, AW)
    runs = {}
    for mode, bub, gap, seed in modes or (("back_to_back", 0, 0, 1), ("bubbles_and_gaps", 30, 20, 7)):
        rec = simulate(binary, pfx, bub, gap, seed)
        rec.update({"simulator": "verilator", "bubble_percent": bub, "gap_percent": gap, "seed": seed})
        rec["pass"] = bool(rec["pass"] and rec.get("segments") == len(segs) and
                           rec.get("outputs") == st["expected_outputs"] and rec.get("elements") == st["elements"] and
                           rec.get("lat0_min", -1) >= lat0(W) and rec.get("lat0_max", 999) <= lat0(W) + 1)
        runs[mode] = rec
    if icarus:
        vvp = s / f"{name}.vvp"
        subprocess.run(["iverilog", "-g2012", f"-Ptb_hdc_tselect_q.Q={Q}", f"-Ptb_hdc_tselect_q.W={W}",
                        f"-Ptb_hdc_tselect_q.IW={iw}", f"-Ptb_hdc_tselect_q.K={K}", f"-Ptb_hdc_tselect_q.AW={AW}",
                        "-o", str(vvp), str(TB), str(rtl), str(HELPERS)], check=True, capture_output=True)
        out = subprocess.run(["vvp", "-n", str(vvp), f"+PFX={pfx}", "+BUBBLE=30", "+GAP=20", "+SEED=7"],
                             capture_output=True, text=True).stdout
        rec = parse(out)
        rec.update({"simulator": "icarus", "bubble_percent": 30, "gap_percent": 20, "seed": 7})
        rec["pass"] = bool(rec["pass"] and rec.get("segments") == len(segs) and
                           rec.get("outputs") == st["expected_outputs"])
        runs["icarus_bubbles_and_gaps"] = rec
    hier = hierarchy(np.random.default_rng(8000 + ci), binary, Q, W, iw, K, htrials, s, name) if htrials else None
    ok = all(r["pass"] for r in runs.values()) and (hier is None or hier["pass"])
    return {"name": name, "quarters": Q, "lanes_per_quarter": W, "lanes": Q * W, "value_width": T.VW,
            "index_width": iw, "K": K, "line_address_width": AW,
            "latency_cycles": f"2 x (longest quarter's beats) + {lat0(W)} (+1 on a final-line overflow)",
            "lat0": lat0(W), "random_segments": n_rand, "real_segments": counts, **st, "runs": runs,
            "two_level": hier, "pass": ok}


def mutations(s: Path, sets):
    out = []
    src = RTL.read_text()
    cdir = s / "mut_control"
    cdir.mkdir()
    ctrl = run_config(90, MUTATION_CONFIG, sets, cdir, modes=(("back_to_back", 0, 0, 1),))
    out.append({"mutation": "none (control)", "caught": not ctrl["pass"], "control": True,
                "detail": {k: v.get("errors") for k, v in ctrl["runs"].items()}})
    print("mutation control", "pass" if ctrl["pass"] else "FAIL", flush=True)
    for i, (what, a, b) in enumerate(MUTATIONS):
        mdir = s / f"mut{i}"
        mdir.mkdir()
        m = mdir / "ot_hdc_tselect_q.sv"
        m.write_text(src.replace(a, b))
        try:
            rec = run_config(90, MUTATION_CONFIG, sets, mdir, rtl=m, modes=(("back_to_back", 0, 0, 1),))
            caught = not rec["pass"]
            detail = {k: v.get("errors") for k, v in rec["runs"].items()}
            if rec["two_level"]:
                detail["two_level_pass"] = rec["two_level"]["pass"]
        except subprocess.CalledProcessError as e:
            caught, detail = True, {"build_failed": e.stderr[-300:] if e.stderr else ""}
        out.append({"mutation": what, "caught": caught, "detail": detail})
        print("mutation", what, "caught" if caught else "MISSED", flush=True)
    return out


def run(positions, quick=False) -> dict:
    src = RTL.read_text()
    for what, a, _ in MUTATIONS:
        assert src.count(a) == 1, (what, src.count(a))
    sets, checks, real_meta = SC.real_sets(positions)
    configs, ok, lint = [], True, {}
    for name, Q, W, iw, K, AW, *_ in CONFIGS:
        r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, f"-GQ={Q}", f"-GW={W}", f"-GIW={iw}", f"-GK={K}",
                            f"-GAW={AW}", "--top-module", "ot_hdc_tselect_q", str(RTL), str(HELPERS)],
                           capture_output=True, text=True)
        lint[name] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:10]}
        ok &= r.returncode == 0
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        for ci, cfg in enumerate(CONFIGS[1:2] if quick else CONFIGS):
            rec = run_config(ci, cfg, sets, s, icarus=(cfg[0] == "k7_q2_w8_edge"))
            ok &= rec["pass"]
            configs.append(rec)
            print(cfg[0], "pass" if rec["pass"] else "FAIL",
                  {m: (r.get("errors"), r.get("lat0_min"), r.get("lat0_max")) for m, r in rec["runs"].items()},
                  "two-level", None if rec["two_level"] is None else rec["two_level"]["pass"], flush=True)
        muts = [] if quick else mutations(s, sets)
        ok &= all(m["caught"] != bool(m.get("control")) for m in muts)
    status = "pass" if ok and all(checks[k] > 0 for k in checks) else "fail"
    return {
        "schema": "opentallas.hdc-v41-tselect-q-campaign.v1",
        "status": status,
        "claim_boundary": "functional cycle-level RTL simulation of the quartered threshold SELECT alone (one "
                          "behavioural line memory per quarter) against tools/hdc_golden_v41.py topk_lowest_index; "
                          "clock rate and area are in results/physical_abi3/asap7/hdc/v41/ot_hdc_tselect_q4_w16/.",
        "semantics": "k largest values, ties to the lower index, -0 == +0, emitted in ascending position order as "
                     "the concatenation of the Q quarters' outputs; each quarter a contiguous position range",
        "latency_definition": "edges from the edge accepting the segment's final last beat (over all quarters) to "
                              "the edge registering the last quarter's out_last: 2 x (longest quarter's beats) + "
                              "LAT0 (+1 on a final-line overflow)",
        "real_data": dict(real_meta, golden_selection_checks=checks),
        "configurations": configs,
        "mutations": muts,
        "verilator_lint": {"flags": list(LINT_FLAGS), "configurations": lint},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (RTL, HELPERS, TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--positions", type=int, default=SC.REAL_POSITIONS)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    result = run(args.positions, args.quick)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
