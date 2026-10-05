#!/usr/bin/env python3
"""RTL campaign for the V4.1 candidate-block SELECT at shipped scale
(rtl/hdc/v41/ot_hdc_tselect_cand.sv: a block-max front end on ot_hdc_tselect).

Every expected output comes from tools/hdc_golden_v41.py: the block scores and
the keep mask are `Model.candidate_blocks` (block max over 8 positions, the
newest block pinned to +inf, padding -inf, top-K blocks by `topk_lowest_index`,
kept when the block max is above -inf), called on the golden's own code.  The
unit emits the selected blocks in ascending block order with the block max and
a -inf flag; the expected stream is the golden's selection in block order, and
{selected and not -inf} must equal the golden keep mask on every segment.

* shipped configuration (64 score lanes, 64 tselect lanes, K = 2048, 17-bit
  block index, 2^11 lines = 1,048,576 positions): random score arrays with
  MANY ties (small alphabets with +/-0, +/-inf and subnormals, all-equal,
  coarse normals, raw BF16 patterns, NaN excluded), lengths from one position
  to the full 1M context, and real reduced DeepSeek-V4.1 index scores scaled
  up (every indexer's BF16 score array from the golden decode, concatenated in
  random order until the shipped length is reached, so the value distribution
  and its ties are the model's);
* the multi-die form: a context split into G contiguous block-aligned ranges,
  each range's local top-K on the RTL (only the die holding the newest position
  pins), the G outputs concatenated in range order and selected again on the
  RTL ot_hdc_tselect (tools/rtl_hdc_v41_tselect_campaign.py's bench), which
  must equal the golden's candidate blocks of the whole context;
* reduced configuration (8 lanes, K = 64) on the real reduced layer-20 scores
  (the golden's own candidate mask at the reduced shapes), a 16-lane and an
  odd-K edge configuration;
* shipped-context latency: one segment at 8K, 200K and 1M positions;
* a mutation check (each mutant of the front end must fail; the unmutated RTL
  must pass the same configuration).

Verilator 4.038 back to back and with random bubbles and idle gaps; one
configuration also under Icarus.  Writes results/rtl/hdc_v41_cand_campaign.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pickle
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41_select_campaign as SC  # noqa: E402
import rtl_hdc_v41_tselect_campaign as TC  # noqa: E402

OUT = ROOT / "results/rtl/hdc_v41_cand_campaign.json"
RTL = ROOT / "rtl/hdc/v41/ot_hdc_tselect_cand.sv"
TSEL = ROOT / "rtl/hdc/v41/ot_hdc_tselect.sv"
TB = ROOT / "rtl/test/tb_hdc_tselect_cand.sv"
HARNESS = ROOT / "rtl/test/hdc_tselect_cand_harness.cpp"
TOOLS = [ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/rtl_hdc_v41_select_campaign.py",
         ROOT / "tools/rtl_hdc_v41_tselect_campaign.py", Path(__file__)]
LINT_FLAGS = ("-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED")
LINE = re.compile(r"TSELCAND P=(\d+) W=(\d+) VW=(\d+) IW=(\d+) K=(\d+) segments=(\d+) beats=(\d+) elements=(\d+) "
                  r"outputs=(\d+) out_beats=(\d+) errors=(\d+) lat0_min=(-?\d+) lat0_max=(-?\d+) cycles=(\d+)")
SEGLAT = re.compile(r"SEGLAT (\d+) (\d+) (\d+)")
CB = 8                               # candidate_block_size
FRONT = 4                            # front-end edges: 3 block-max stages + the line register
SHIPPED = json.loads((ROOT / "configs/models/candidates/deepseek-v4.1-flash.json").read_text())
OPC = SHIPPED["metadata"]["operator_config"]
MAX_CONTEXT = SHIPPED["max_context_tokens"]
LAT_CONTEXTS = (8192, 200000, MAX_CONTEXT)

# name, P, WB, IW, K, AW, random segments, real kinds, multi-die trials, long segments
CONFIGS = [
    ("candidate_shipped_p64_wb64", 64, 64, 17, OPC["candidate_topk_blocks"], 11, 120, ("index_scaled",), 6, 3),
    ("candidate_wb16_k300", 64, 16, 14, 300, 10, 200, ("index_scaled",), 0, 0),
    ("candidate_reduced_p8_k64", 8, 8, 12, 64, 8, 800, ("candidate_scores",), 0, 0),
    ("k7_p16_wb8_edge", 16, 8, 10, 7, 8, 1200, (), 0, 0),
]
MUTATION_CONFIG = ("mutation_p16_wb8", 16, 8, 12, 24, 8, 400, (), 0, 0)
MUTATIONS = [
    ("pin ignores in_pin", "assign bp_d[gb] = in_last && in_pin && in_lv[8*gb];",
     "assign bp_d[gb] = in_last && in_lv[8*gb];"),
    ("pin takes a block that is not the newest", "&& !in_lv[8*gb + 8];", ";"),
    ("empty lanes enter the block max as +0", "fkey(in_val[16*gl +: 16]) : KEY_NINF;", "fkey(in_val[16*gl +: 16]) : 16'h8000;"),
    ("block index not advanced across beats", "if (acc) bcnt <= base_now + NBW;", "if (acc) bcnt <= base_now;"),
    ("packer keeps stale lanes of the previous line", "else if (fresh) line_lv[gl] <= 1'b0;", "else if (1'b0) line_lv[gl] <= 1'b0;"),
    ("key inverse keeps the sign flip", "wire [15:0] v = k[15] ? {1'b0, k[14:0]} : ~k;", "wire [15:0] v = k[15] ? k : ~k;"),
    ("block max takes the lower half only", "assign m2_d[32*gb +: 32] = {kmax(l2, l3), kmax(l0, l1)};",
     "assign m2_d[32*gb +: 32] = {kmax(l0, l1), kmax(l0, l1)};"),
    ("stall does not hold the front end", "wire             adv = !(line_v && !t_ready);", "wire             adv = 1'b1;"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bits16(v):
    return (np.asarray(v, np.float32).view(np.uint32) >> 16).astype(np.int64)


# -- golden ------------------------------------------------------------------------------
def golden_keep(s, k):
    """The golden's own candidate_blocks on an array of index scores (per block)."""
    stub = SimpleNamespace(cand_b=CB, cand_k=k)
    n = len(s)
    return G.Model.candidate_blocks(stub, np.asarray(s, np.float64), n)[::CB]


def block_scores(s, pin):
    n = len(s)
    nb = -(-n // CB)
    bs = np.concatenate([np.asarray(s, np.float64), np.full(nb * CB - n, -np.inf)]).reshape(nb, CB).max(axis=1)
    if pin:
        bs[(n - 1) // CB] = np.inf
    return bs


def expected_blocks(s, k, K, base, pin):
    """Selected blocks in block order: [(block index, canonical value bits, ninf)]."""
    bs = block_scores(s, pin)
    sel = sorted(int(i) for i in G.topk_lowest_index(bs, min(min(k, K), len(bs))))
    vb = bits16(bs)
    vb = np.where(bs == 0, 0, vb)                  # a zero maximum leaves as +0
    return [(base + i, int(vb[i]), bool(bs[i] == -np.inf)) for i in sel], bs


# -- stimulus ------------------------------------------------------------------------------
def scaled_scores(rng, arrays, n):
    """Real reduced index-score arrays concatenated in random order up to n positions."""
    out, have = [], 0
    while have < n:
        a = arrays[int(rng.integers(len(arrays)))]
        out.append(a)
        have += len(a)
    return np.concatenate(out)[:n]


def random_length(rng, P, K, cap):
    r = rng.random()
    n = int(1 if r < 0.03 else rng.integers(1, 8 * K + 1) if r < 0.4 else
            rng.integers(8 * K - 16, 8 * K + 17) if r < 0.5 else rng.integers(1, 64 * P + 1) if r < 0.75 else
            rng.integers(1, cap + 1))
    return max(1, min(n, cap))


def to_beats(vals, P):
    b = bits16(vals)
    beats = []
    for i in range(0, len(b), P):
        chunk = b[i:i + P]
        beats.append((len(chunk), list(map(int, chunk)) + [0] * (P - len(chunk))))
    return beats


def seg_record(vals, k, K, P, WB, base=0, pin=True, check_golden=True):
    exp, _ = expected_blocks(vals, k, K, base, pin)
    if check_golden and pin:
        keep = golden_keep(vals, min(k, K))
        got = np.zeros(len(keep), bool)
        for i, _, ninf in exp:
            got[i - base] = not ninf
        assert (got == keep).all(), "expected stream disagrees with the golden candidate_blocks"
    beats = to_beats(vals, P)
    lines = -(-len(beats) // (WB // (P // CB)))
    return dict(beats=beats, k=k, base=base, pin=pin, exp=exp, lines=lines, n=len(vals))


def write_vectors(segs, P, d: Path, tag):
    fin, fexp = d / f"{tag}.in", d / f"{tag}.exp"
    n_el = n_out = n_beats = 0
    with fin.open("w") as fi, fexp.open("w") as fe:
        for sg in segs:
            nb = len(sg["beats"])
            for bi, (cnt, vals) in enumerate(sg["beats"]):
                lv = (1 << cnt) - 1
                base = sg["base"] if bi == 0 else 0
                fi.write(f"{int(bi == nb - 1)} {int(sg['pin'])} {sg['k']} {base:x} {lv:x} "
                         + " ".join(f"{v:x}" for v in vals) + "\n")
                n_el += cnt
            n_beats += nb
            fe.write(f"S {len(sg['exp'])} {sg['lines']}\n")
            fe.writelines(f"{p:x} {vb:x} {int(ni)}\n" for p, vb, ni in sg["exp"])
            n_out += len(sg["exp"])
    h = hashlib.sha256(fin.read_bytes() + fexp.read_bytes()).hexdigest()
    return fin, fexp, dict(elements=n_el, expected_outputs=n_out, beats=n_beats, vectors_sha256=h)


def parse(out):
    m = LINE.search(out)
    if not m:
        return {"pass": False, "log": out[-2000:]}
    (p, w, vw, iw, k, segs, beats, el, outs, obeats, err, lmin, lmax, cyc) = map(int, m.groups())
    rec = {"segments": segs, "beats": beats, "elements": el, "outputs": outs, "out_beats": obeats,
           "errors": err, "lat0_min": lmin, "lat0_max": lmax, "cycles": cyc, "pass": "PASS" in out and err == 0}
    lats = [tuple(map(int, x)) for x in SEGLAT.findall(out)]
    if lats:
        rec["segment_latency"] = lats
    return rec


def build(obj: Path, rtl: Path, P, WB, iw, K, AW):
    subprocess.run(["verilator", "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "--top-module", "tb_hdc_tselect_cand",
                    f"-GP={P}", f"-GW={WB}", f"-GIW={iw}", f"-GK={K}", f"-GAW={AW}", "-Mdir", str(obj), str(rtl),
                    str(TSEL), str(TB), str(HARNESS), "-CFLAGS", "-O1"], check=True, capture_output=True)
    return obj / "Vtb_hdc_tselect_cand"


def simulate(binary, fin, fexp, bub=0, gap=0, seed=1, out=None, latlog=False):
    args = [str(binary), f"+IN={fin}", f"+EXP={fexp}", f"+BUBBLE={bub}", f"+GAP={gap}", f"+SEED={seed}"]
    if out:
        args.append(f"+OUT={out}")
    if latlog:
        args.append("+LATLOG=1")
    return parse(subprocess.run(args, capture_output=True, text=True).stdout)


def lat0(WB):
    return FRONT + TC.lat0(WB)


def real_arrays(sets):
    idx = [np.asarray(v, np.float64) for v, _, _ in sets["index"]]
    return [a for a in idx if len(a) >= 1]


def config_segments(ci, cfg, sets):
    name, P, WB, iw, K, AW, nseg, real, _, nlong = cfg
    rng = np.random.default_rng(7000 + ci)
    cap = min((1 << AW) * WB * CB, (1 << iw) * CB)
    kmax = (1 << int(np.ceil(np.log2(K + 1)))) - 1
    segs, counts = [], {}
    for _ in range(nseg):
        n = random_length(rng, P, K, cap)
        k = K if rng.random() < 0.6 else int(rng.integers(0, kmax + 1))
        vals = SC.random_values(rng, n, 16)
        pin = rng.random() < 0.8
        base = 0 if pin or rng.random() < 0.5 else int(rng.integers(0, (1 << iw) - (-(-n // CB)) + 1))
        segs.append(seg_record(vals, k, K, P, WB, base, pin))
    arrays = real_arrays(sets)
    for kind in real:
        if kind == "index_scaled":
            lens = [int(rng.integers(1, cap + 1)) for _ in range(20)] + [8 * K, 8 * K + 1, 8 * K - 7]
            for n in lens:
                n = min(n, cap)
                segs.append(seg_record(scaled_scores(rng, arrays, n), K, K, P, WB))
            counts[kind] = len(lens)
        elif kind == "candidate_scores":
            # the reduced model's layer-20 index scores, whose golden keep mask the select campaign checked
            src = sets["cand_scores"]
            for s in src:
                segs.append(seg_record(np.asarray(s, np.float64), K, K, P, WB))
            counts[kind] = len(src)
    for n in [cap, cap - 1][:nlong] + [8 * 200000 // 8][:max(0, nlong - 2)]:   # full memory and 200K
        segs.append(seg_record(scaled_scores(rng, arrays, n) if arrays else SC.random_values(rng, n, 16),
                               K, K, P, WB))
    segs.append(seg_record(np.full(min(cap, 64 * K), 1.0), K, K, P, WB))       # all ties
    perm = np.random.default_rng(8000 + ci).permutation(len(segs))
    return [segs[i] for i in perm], counts


def run_config(ci, cfg, sets, s: Path, rtl=RTL, icarus=False, modes=None):
    name, P, WB, iw, K, AW, nseg, real, mtrials, nlong = cfg
    segs, counts = config_segments(ci, cfg, sets)
    fin, fexp, st = write_vectors(segs, P, s, name)
    binary = build(s / f"obj_{name}", rtl, P, WB, iw, K, AW)
    runs = {}
    for mode, bub, gap, seed in modes or (("back_to_back", 0, 0, 1), ("bubbles_and_gaps", 30, 20, 7)):
        rec = simulate(binary, fin, fexp, bub, gap, seed)
        rec.update({"simulator": "verilator", "bubble_percent": bub, "gap_percent": gap, "seed": seed})
        rec["pass"] = bool(rec["pass"] and rec.get("segments") == len(segs) and rec.get("outputs") ==
                           st["expected_outputs"] and rec.get("elements") == st["elements"] and
                           rec.get("lat0_min", -1) == lat0(WB))
        # lat0_max is not bounded here: a segment whose last beat enters the front end while the tselect is
        # still selecting the previous segment waits in the line register (queueing, not latency); the
        # isolated-segment bound is checked exactly in latency_at_shipped_context
        runs[mode] = rec
    if icarus:
        vvp = s / f"{name}.vvp"
        subprocess.run(["iverilog", "-g2012", f"-Ptb_hdc_tselect_cand.P={P}", f"-Ptb_hdc_tselect_cand.W={WB}",
                        f"-Ptb_hdc_tselect_cand.IW={iw}", f"-Ptb_hdc_tselect_cand.K={K}",
                        f"-Ptb_hdc_tselect_cand.AW={AW}", "-o", str(vvp), str(TB), str(rtl), str(TSEL)],
                       check=True, capture_output=True)
        out = subprocess.run(["vvp", "-n", str(vvp), f"+IN={fin}", f"+EXP={fexp}", "+BUBBLE=30", "+GAP=20",
                              "+SEED=7"], capture_output=True, text=True).stdout
        rec = parse(out)
        rec.update({"simulator": "icarus", "bubble_percent": 30, "gap_percent": 20, "seed": 7})
        rec["pass"] = bool(rec["pass"] and rec.get("segments") == len(segs) and
                           rec.get("outputs") == st["expected_outputs"])
        runs["icarus_bubbles_and_gaps"] = rec
    multi = multi_die(np.random.default_rng(9000 + ci), binary, sets, P, WB, iw, K, AW, mtrials, s, name) \
        if mtrials else None
    ok = all(r["pass"] for r in runs.values()) and (multi is None or multi["pass"])
    return {"name": name, "score_lanes": P, "tselect_lanes": WB, "block_index_width": iw, "K": K,
            "line_address_width": AW, "max_positions": min((1 << AW) * WB * CB, (1 << iw) * CB),
            "latency_cycles": f"{FRONT} + 2 x lines + {TC.lat0(WB)} (+1), lines = ceil(input beats / {WB // (P // CB)})",
            "lat0": lat0(WB), "real_segments": counts, "segments": len(segs), **st, "runs": runs,
            "multi_die": multi, "pass": ok}


# -- multi-die: local candidate select on G contiguous ranges, then the RTL tselect merge ----------------
def read_out(path: Path):
    return TC.read_out(path)


def multi_die(rng, binary, sets, P, WB, iw, K, AW, trials, s: Path, tag):
    arrays = real_arrays(sets)
    locs, whole = [], []
    for t in range(trials):
        g = int(rng.choice([2, 4, 8]))
        per_blocks = int(rng.integers(max(1, K // 4), min((1 << AW) * WB, (1 << iw) // g) + 1))
        per = per_blocks * CB
        n = g * per - int(rng.integers(0, CB * 3))          # the newest die may end mid-block
        vals = scaled_scores(rng, arrays, n) if rng.random() < 0.6 else SC.random_values(rng, n, 16)
        whole.append((vals, g))
        for d in range(g):
            sl = vals[d * per:(d + 1) * per]
            locs.append(seg_record(sl, K, K, P, WB, base=d * per_blocks, pin=(d == g - 1), check_golden=False))
    fin, fexp, st1 = write_vectors(locs, P, s, f"{tag}_local")
    r1 = simulate(binary, fin, fexp, out=s / f"{tag}_local.out")
    got = read_out(s / f"{tag}_local.out") if r1.get("pass") else []
    # the merge level: plain ot_hdc_tselect over the concatenated local outputs (ascending block order)
    tsb = TC.build(s / f"obj_{tag}_merge", TSEL, WB, iw, K, 12)
    merges, i, golden_ok = [], 0, True
    for vals, g in whole:
        cat = [e for d in range(g) for e in got[i + d]] if got else []
        i += g
        exp, bs = expected_blocks(vals, K, K, 0, True)
        keep = golden_keep(vals, K)
        golden_ok &= [p for p, _, ni in exp if not ni] == [int(x) for x in np.nonzero(keep)[0]]
        cvals = SC.from_bits(np.array([vb for _, vb, _ in cat], np.int64), 16) if cat else np.zeros(0)
        cpos = np.array([p for p, _, _ in cat], np.int64)
        merges.append((TC.to_beats(rng, cvals, cpos, WB, False), K, exp))
    fin2, fexp2, st2 = TC.write_vectors(merges, WB, K, s, f"{tag}_merge")
    r2 = TC.simulate(tsb, fin2, fexp2, bub=20, gap=10, seed=3)
    return {"trials": trials, "local_segments": len(locs), "local": dict(st1, **r1), "merge": dict(st2, **r2),
            "merge_unit": f"ot_hdc_tselect W={WB} IW={iw} K={K} AW=12",
            "golden_keep_mask_agrees": bool(golden_ok),
            "pass": bool(r1.get("pass") and r2.get("pass") and len(got) == len(locs) and golden_ok)}


# -- shipped-context latency -----------------------------------------------------------------------------
def latency_runs(sets, s: Path, clock_hz=None):
    name, P, WB, iw, K, AW, *_ = CONFIGS[0]
    rng = np.random.default_rng(11)
    arrays = real_arrays(sets)
    segs = [seg_record(scaled_scores(rng, arrays, n), K, K, P, WB) for n in LAT_CONTEXTS]
    fin, fexp, st = write_vectors(segs, P, s, "latency")
    binary = build(s / "obj_latency", RTL, P, WB, iw, K, AW)
    rec = simulate(binary, fin, fexp, latlog=True)
    rows = []
    for (seg, beats, lat), n, sg in zip(rec.get("segment_latency", []), LAT_CONTEXTS, segs):
        blocks = -(-n // CB)
        row = {"context": n, "blocks": blocks, "input_beats": beats, "tselect_lines": sg["lines"],
               "cycles_after_last_beat": lat, "formula": FRONT + 2 * sg["lines"] + TC.lat0(WB),
               "cycles_from_first_beat": lat + beats - 1}
        rows.append(row)
    return {"configuration": name, "pass": rec.get("pass", False), "errors": rec.get("errors"), **st,
            "rows": rows}


def real_sets_cached(positions, cache):
    if cache and Path(cache).exists():
        return pickle.loads(Path(cache).read_bytes())
    sets, checks, meta = SC.real_sets(positions)
    # the reduced layer-20 index scores (the arrays whose block maxima are sets["candidate"])
    prompt, gen = G.prompt_and_expected()
    sets = dict(sets)
    sets["cand_scores"] = []
    model = G.Model()
    state = model.new_state()
    seq = list(prompt) + list(gen)
    for p in range(positions):
        tr = {}
        logits = model.decode_token(seq[p], p, state, trace=tr)
        if p + 1 >= len(seq):
            seq.append(int(np.argmax(logits)))
        if f"L{model.cand_src}.index_scores" in tr:
            sets["cand_scores"].append(np.asarray(tr[f"L{model.cand_src}.index_scores"], np.float64))
    out = (sets, checks, meta)
    if cache:
        Path(cache).write_bytes(pickle.dumps(out))
    return out


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
        assert src.count(a) == 1, (what, src.count(a))
        mdir = s / f"mut{i}"
        mdir.mkdir()
        m = mdir / "ot_hdc_tselect_cand.sv"
        m.write_text(src.replace(a, b))
        mode = ("bubbles_and_gaps", 30, 20, 7) if "stall" in what else ("back_to_back", 0, 0, 1)
        try:
            rec = run_config(90, MUTATION_CONFIG, sets, mdir, rtl=m, modes=(mode,))
            caught = not rec["pass"]
            detail = {k: v.get("errors") for k, v in rec["runs"].items()}
        except subprocess.CalledProcessError as e:
            caught, detail = True, {"build_failed": e.stderr[-300:] if e.stderr else ""}
        out.append({"mutation": what, "caught": caught, "detail": detail})
        print("mutation", what, "caught" if caught else "MISSED", flush=True)
    return out


def run(positions, quick=False, cache=None) -> dict:
    src = RTL.read_text()
    for what, a, _ in MUTATIONS:
        assert src.count(a) == 1, (what, src.count(a))
    sets, checks, real_meta = real_sets_cached(positions, cache)
    ok = True
    lint = {}
    for name, P, WB, iw, K, AW, *_ in CONFIGS:
        r = subprocess.run(["verilator", "--lint-only", *LINT_FLAGS, f"-GP={P}", f"-GWB={WB}", f"-GIW={iw}",
                            f"-GK={K}", f"-GAW={AW}", "--top-module", "ot_hdc_tselect_cand", str(RTL), str(TSEL)],
                           capture_output=True, text=True)
        lint[name] = {"returncode": r.returncode, "messages": r.stderr.strip().splitlines()[:10]}
        ok &= r.returncode == 0
    configs = []
    with tempfile.TemporaryDirectory() as scratch:
        s = Path(scratch)
        for ci, cfg in enumerate(CONFIGS[2:3] if quick else CONFIGS):
            rec = run_config(ci, cfg, sets, s, icarus=(cfg[0].startswith("k7")))
            ok &= rec["pass"]
            configs.append(rec)
            print(cfg[0], "pass" if rec["pass"] else "FAIL",
                  {m: (r.get("errors"), r.get("lat0_min"), r.get("lat0_max")) for m, r in rec["runs"].items()},
                  "multi-die", None if rec["multi_die"] is None else rec["multi_die"]["pass"], flush=True)
        lat = None if quick else latency_runs(sets, s)
        if lat:
            ok &= lat["pass"] and all(r["cycles_after_last_beat"] in (r["formula"], r["formula"] + 1)
                                      for r in lat["rows"])
            print("latency", lat["rows"], flush=True)
        muts = [] if quick else mutations(s, sets)
        ok &= all(m["caught"] != bool(m.get("control")) for m in muts)
    status = "pass" if ok and checks.get("candidate", 0) > 0 and len(sets["cand_scores"]) > 0 else "fail"
    return {
        "schema": "opentallas.hdc-v41-cand-campaign.v1",
        "status": status,
        "claim_boundary": "functional cycle-level RTL simulation of the candidate-block select (behavioural line "
                          "memory in the bench) against tools/hdc_golden_v41.py Model.candidate_blocks; clock rate "
                          "and area are in results/physical_abi3/asap7/hdc/v41/ot_hdc_tselect_cand/.",
        "semantics": "block max over 8 positions, newest block pinned to +inf, top-K blocks by value with ties to "
                     "the lower block index, kept when the block max is above -inf; emitted in ascending block "
                     "order with the block max (a zero maximum as +0) and a -inf flag",
        "shipped_shape": {"candidate_block_size": OPC["candidate_block_size"],
                          "candidate_topk_blocks": OPC["candidate_topk_blocks"],
                          "candidate_source_layer_id": OPC["candidate_source_layer_id"],
                          "max_context_tokens": MAX_CONTEXT},
        "latency_definition": "clock edges from the edge that accepts a segment's last input beat to the edge that "
                              f"registers its out_last beat: {FRONT} + 2 x lines + LAT0(WB) (+1 when the final "
                              "pass-3 beat overflows the partial output line); the input stream itself is one beat of "
                              "P positions per cycle",
        "real_data": dict(real_meta, golden_selection_checks=checks,
                          reduced_layer20_score_arrays=len(sets["cand_scores"])),
        "configurations": configs,
        "latency_at_shipped_context": lat,
        "mutations": muts,
        "verilator_lint": {"flags": list(LINT_FLAGS), "configurations": lint},
        "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in (RTL, TSEL, TB, HARNESS, *TOOLS)},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--positions", type=int, default=SC.REAL_POSITIONS)
    parser.add_argument("--quick", action="store_true", help="one reduced configuration, no mutations")
    parser.add_argument("--real-cache", help="pickle of the golden decode's selection inputs (reused if present)")
    args = parser.parse_args()
    result = run(args.positions, args.quick, args.real_cache)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"])
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
