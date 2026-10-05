#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash, S81) per-user rate MEASURED at the target context: one decode token at position
1,048,575 (1M context), one representative layer per layer TYPE plus the head.

Owner rules (2026-10-03/04): simulate the minimum component that contains each mechanism, at full shape, at the
target position only; compose the token from measured components; list every term still modelled.

What runs in RTL here (Verilator 5.050, full shape, the 1M state of results/rtl/w17_v41_1m_reference_token.json,
seed 20260930, whose released-checkpoint golden shards live in --gold):

  reader   the index-key reader (W11 quarter-per-stack: one ot_hdc_v41x_idx_kstream_range per HBM3E stack into the
           timing-faithful ot_hdc_v41x_idx_hbm, 32 pseudo-channels a stack, joined by ot_hdc_v41x_idx_quarter_join)
           for every scanning layer type's per-rank key count at 1M, at the 1.2 GHz streaming clock (CLK_PS 833) and
           at the W11 spec clock (967 ps); every key of every beat checked; sectors, bytes, achieved TB/s vs the four
           stacks' peak, per-stack mean/max HBM read latency.
  select   the index top-512 streaming-filter select (ot_hdc_v41x_sel, Q 4 x W 16 = 64 scores/cycle) on the GOLDEN
           1M index scores of each scanning layer, rank by rank (each rank's quarter of the positions, its four stacks
           as the four select quarters), then the cross-die final select on the four ranks' local selections;
           bit-exact against tools/hdc_golden_v41.topk_lowest_index and equal to the golden layer's own selection.
  ckvvec   vectors for the selected-CKV gather + attention bench (tools/rtl_v41x_ckv_sel_attn_campaign.py) whose
           selection is the golden layer's REAL 1M selection (owner/stack distribution of the real token), rows in
           the golden's stored formats over 1,048,576 (ratio 1) / 524,288 (ratio 2) compressed rows.
  compose  per-layer-type table and the token composition (the S81 unified model graph with every measured
           context-dependent node replaced by its measurement, re-solved), AR and MTP at 1M.

Writes results/rtl/dsrom_1m_measured_20261004/ (records) ; bulk outputs go to --out on the compute host.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import third_party_tau as _TPT  # noqa: E402
REC = ROOT / "results/rtl/dsrom_1m_measured_20261004"
GOLD_DEFAULT = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
POS = 1048575
CTX = 1048576
TP = 4

# layer types (configs/models/candidates/deepseek-v4.1-flash.json attention_groups + reference-token kinds)
TYPES = {
    "swa":            dict(rep=0,  layers=[0], kind="sliding"),
    "engram_swa":     dict(rep=1,  layers=[1], kind="engram+sliding"),
    "csa2_full":      dict(rep=2,  layers=[2, 8, 14], kind="ratio2+compressor+indexer (L14 +engram)",
                           scan_keys=524288),
    "csa2_reuse":     dict(rep=3,  layers=[l for l in range(3, 20) if l not in (8, 14)], kind="ratio2"),
    "csa1_full":      dict(rep=20, layers=[20], kind="ratio1+compressor+indexer+candidates", scan_keys=1048576),
    "csa1_reuse":     dict(rep=21, layers=[l for l in range(21, 40) if l not in (24, 28, 32, 36)], kind="ratio1"),
    "csa1_reindex":   dict(rep=24, layers=[24, 28, 32, 36], kind="ratio1+indexer (16,384 candidate keys)",
                           scan_keys=16384),
}


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def gold_layer(gold: Path, L: int):
    z = np.load(gold / f"ctx1048576_L{L:02d}.npz")
    j = json.loads((gold / f"ctx1048576_L{L:02d}.json").read_text())
    return z, j


# ------------------------------------------------------------------------------------------------ reader
def reader_runs():
    """(name, N per rank, params).  Per-rank key counts at position 1,048,575 (TP4 rank = position quarter):
    ratio 1 (L20): 1,048,576 index keys incl. the token's own -> 262,144 a rank;
    ratio 2 (L2/L8/L14): 524,288 -> 131,072 a rank.  Two ring placements bound the head offsets."""
    runs = []
    for tag, n in (("csa1_full_L20", 262144), ("csa2_full_L2", 131072)):
        for clk in (833, 967):
            runs.append((f"{tag}_clk{clk}", n, dict(CLK_PS=clk, WB=128, GA=120)))
        runs.append((f"{tag}_clk833_placement2", n, dict(CLK_PS=833, WB=128, GA=120, BASE=123, BSTEP=777, OSTEP=8)))
    # window-row load of a one-stack (non-scan) die: 128 rows x 17 sectors = 2,176 sectors per stack, the same as a
    # 1,024-key quarter (2.125 sectors/key): each stack of the bench is one die's window load, contiguous rows
    runs.append(("window128_per_stack_clk833", 4096, dict(CLK_PS=833, WB=128, GA=120)))
    return runs


def cmd_reader(a):
    only = set(a.only.split(",")) if a.only else None
    import w11_idx_reader_rate as W
    out = a.out.resolve()
    (out / "build").mkdir(parents=True, exist_ok=True)
    rows = []

    def one(r):
        name, n, params = r
        t0 = time.time()
        row = W.build_and_run((name, "quarter_stack", n, params, "dsrom_1m"), out / "build")
        row["wall_s"] = round(time.time() - t0, 1)
        clk = params["CLK_PS"]
        secs = row["cycles"] * clk * 1e-12
        row["bytes"] = row["sectors"] * 32
        row["seconds"] = secs
        row["achieved_TBps"] = row["bytes"] / secs / 1e12
        row["peak_TBps"] = 4 * 32 * 32 / 1024e-12 / 1e12          # 4 stacks x 32 PCs x 32 B / 1,024 ps
        row["fraction_of_peak"] = row["achieved_TBps"] / row["peak_TBps"]
        print(f"{name:34s} N={n} cycles={row['cycles']} sectors={row['sectors']} "
              f"{row['achieved_TBps']:.3f} TB/s = {100 * row['fraction_of_peak']:.1f}% peak", flush=True)
        return row

    with cf.ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(one, [r for r in reader_runs() if not only or r[0] in only]))
    srcs = {p: sha(ROOT / p) for p in sorted(set(W.QS_SOURCES + [W.QS_CPP, "tools/w11_idx_reader_rate.py",
                                                                    "tools/dsrom_1m_measure.py"]))}
    ver = subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip()
    rec = dict(schema="opentallas.dsrom-1m.reader.v1", simulator=ver, source_sha256=srcs, runs=rows,
               status="pass" if all(r["checked_keys"] == r["keys"] for r in rows) else "fail")
    (out / "reader.json").write_text(json.dumps(rec, indent=1) + "\n")


# ------------------------------------------------------------------------------------------------ select
def _segment(S, G, bits, pos, cuts, K, W):
    """rtl_hdc_v41x_sel_campaign.segment with explicit quarter cuts (stack sub-quarters of a rank)."""
    rng = np.random.default_rng(0)
    bits = np.asarray(bits, np.int64)
    pos = np.asarray(pos, np.int64)
    v = S.vals_of(bits)
    sel = sorted(int(i) for i in G.topk_lowest_index(v, min(K, K, len(bits))))
    beats, exps = [], []
    for q in range(len(cuts) - 1):
        lo, hi = cuts[q], cuts[q + 1]
        beats.append(S.to_beats(rng, bits[lo:hi], pos[lo:hi], W, True))
        exps.append([(int(pos[i]), int(bits[i]), int(bits[i] == S.NINF)) for i in sel if lo <= i < hi])
    return (beats, K, exps, {"n": len(bits)}), [int(pos[i]) for i in sel]


def cmd_select(a):
    import hdc_golden_v41 as G
    import rtl_hdc_v41x_sel_campaign as S
    G.set_arith("chunk8") if hasattr(G, "set_arith") else None
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    Q, W, IW, K = 4, 16, 20, 512
    specs = a.layers.split(",")          # "24f": stream EVERY position (non-candidates as -inf, the as-built full scan)
    layers = sorted({int(x.rstrip("f")) for x in specs})
    results = {}
    for spec in specs:
        L, full = int(spec.rstrip("f")), spec.endswith("f")
        z, j = gold_layer(a.gold, L)
        s = z[f"L{L}.index_scores"]
        n_all = len(s)
        per = n_all // TP
        golden_sel = sorted(int(x) for x in j["ctx_out"]["sel"])
        segs, labels, local = [], [], []
        for r in range(TP):
            lo, hi = r * per, (r + 1) * per
            idx = np.arange(lo, hi)
            if not full:
                idx = idx[np.isfinite(s[lo:hi])]              # reindex: only the candidate keys are streamed
            bits = S.bf16_bits(s[idx])
            sub = [lo + (per * q) // 4 for q in range(5)]     # stack sub-quarter (quarter-per-stack placement)
            cuts = [int(np.searchsorted(idx, b)) for b in sub]
            seg, lsel = _segment(S, G, bits, idx, cuts, K, W)
            segs.append(seg)
            labels.append(f"L{L}{'_full' if full else ''}_rank{r}")
            local.append(lsel)
        aw = 8
        tag = f"L{L}" + ("_full" if full else "")
        cfg = S.run_config(f"{tag}_local", Q, W, IW, K, aw, segs, labels, out, runs=((0, 0, 1),))
        # cross-die final: rank r's local selection on quarter r
        cb = np.concatenate([S.bf16_bits(s[np.asarray(x)]) for x in local])
        cp = np.concatenate([np.asarray(x) for x in local])
        cuts = np.cumsum([0] + [len(x) for x in local]).tolist()
        segx, gsel = _segment(S, G, cb, cp, cuts, K, W)
        cfgx = S.run_config(f"{tag}_final", Q, W, IW, K, 6, [segx], [f"{tag}_final"], out, runs=((0, 0, 1),))
        res = dict(layer=L, full_stream=full, scores=n_all, streamed_per_rank=[sg[3]["n"] for sg in segs],
                   local=dict(pass_=cfg["pass"], runs=[{k: v for k, v in r.items() if k != "log"} for r in cfg["runs"]],
                              elements=cfg["elements"], beats=cfg["beats"]),
                   final=dict(pass_=cfgx["pass"], runs=[{k: v for k, v in r.items() if k != "log"} for r in cfgx["runs"]]),
                   global_selection_equals_golden_layer=(sorted(gsel) == golden_sel),
                   golden_selection_sha256=hashlib.sha256(json.dumps(golden_sel).encode()).hexdigest())
        results[tag] = res
        print(f"{tag}: local pass={cfg['pass']} final pass={cfgx['pass']} golden_equal={res['global_selection_equals_golden_layer']}",
              flush=True)
    srcs = {str(p.relative_to(ROOT)): sha(p) for p in S.RTL + [S.TB, S.HARNESS]}
    srcs.update({p: sha(ROOT / p) for p in ("tools/rtl_hdc_v41x_sel_campaign.py", "tools/hdc_golden_v41.py",
                                            "tools/dsrom_1m_measure.py")})
    gold_pins = {f"L{L}": dict(npz=sha(a.gold / f"ctx1048576_L{L:02d}.npz"), json=sha(a.gold / f"ctx1048576_L{L:02d}.json"))
                 for L in layers}
    ver = subprocess.run([S.VERILATOR, "--version"], capture_output=True, text=True).stdout.strip()
    rec = dict(schema="opentallas.dsrom-1m.select.v1", simulator=ver, source_sha256=srcs, golden_shards=gold_pins,
               layers=results, status="pass" if all(r["local"]["pass_"] and r["final"]["pass_"] and
                                                    r["global_selection_equals_golden_layer"] for r in results.values())
               else "fail")
    (out / "select.json").write_text(json.dumps(rec, indent=1) + "\n")


# ------------------------------------------------------------------------------------------------ ckv vectors
def cmd_ckvvec(a):
    import v41_ckv_sel_attn_vectors as CV
    CV.V.set_arith("chunk8")
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cases = []
    spec = [("L20_1m_real", 20, 1048576), ("L2_1m_real", 2, 524288), ("L24_1m_real", 24, 1048576)]
    for i, (name, L, n) in enumerate(spec):
        _, j = gold_layer(a.gold, L)
        real = sorted(int(x) for x in j["ctx_out"]["sel"])
        orig = CV.selection
        CV.selection = lambda rng, n_, kind, real=real: list(real)
        try:
            c = CV.make_case(out / name, name, 128, n, "golden_1m_selection", 20261004 + i)
        finally:
            CV.selection = orig
        c["layer"] = L
        c["golden_selection_sha256"] = hashlib.sha256(json.dumps(real).encode()).hexdigest()
        cases.append(c)
        print(name, c["T"], c["owned_rows_per_die"], len(c["owners_die_stack"]), c["quarter_counts"], flush=True)
    rec = dict(scope="Selected-CKV path vectors at the 1M token: the golden layer's real top-512 selection over the "
                     "compressed rows of position 1,048,575 (owner/stack distribution of the real token); rows and q/p "
                     "in the golden's stored formats (random BF16 latents: timing is data-independent, exactness is "
                     "checked on every score and p.v output).",
               parameters=dict(H=CV.H, D=CV.D, TD=CV.TD, NL=4, TROWS=640, TOPK=CV.TOPK),
               golden_sources={g: sha(ROOT / g) for g in CV.GOLDEN}, cases=cases)
    (out / "manifest.json").write_text(json.dumps(rec, indent=2) + "\n")


# ------------------------------------------------------------------------------------------------ compose
CLK = 1.2e9                       # streaming domain (index reader, scorer, select, CKV path, attention)
HOP_US = 0.4820175438596491       # per stage hop (S82 pricing: 23.2/57 us + 2 x 45 SerDes endpoint stages)
S81_EXTRA_HOPS = 81 - 58          # S81 = S58 graph + 23 stage hops (dsrom_c_recheck_20261004), indexer replicated
IDX_ARRAY = dict(latency=48, query_settle=24, ii=1.0, record="results/rtl/w11_idx_array.json")
ATTN_JOB = dict(window128_qk_last=54, mixed640_qk_last=182, tail_after_last_row=50,  # 50: v41x_ckv_sel_attn_wide full1m last_score - last_staged (engine on)
                record="results/rtl/w11_attn_ploader.json (pwords2_psup2)")
WAVEFRONT = dict(head_occ_us=12.37, l20_occ_us=11.62, overhead=0.00408, hop_us=0.48, positions=5,
                 record="results/rtl/dsrom_wavefront_verify_20261004/record.json")
DRAFT = dict(fused_us=105.55, as_built_us=144.44, l1l2_nv5_us=56.07, seed_commit_us=3.217, tau=_TPT.tau_ds_v41(5),  # adopted owner 6-class blend 4.159 (2026-10-05); published 3.8879 = sensitivity
             record="results/rtl/dsrom_dspark_step_slices_20261004/composition.json + "
                    "results/rtl/dsrom_fused_draft_head_20261004")
MODEL_AR = {"1048576": 405.486}


def s58_graph(ctx=CTX):
    """The unified model at the S81 baseline's S58 graph settings (tools/dsrom_return_storage_hbm.py run():
    m0 = 2,535.5 tok/s at 1M), re-timed by _cons_adjust; returns the P=1 graph and its time."""
    import copy
    import uarch_model as u
    cap = json.loads((ROOT / "results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json").read_text())
    rows = {r["stages"]: r for r in cap["all_stage_capacity_rows"]}
    saved = copy.deepcopy(u.PRESETS["proposal"])
    got = {}
    orig = u._cons_adjust

    def hook(g, P, *a, **k):
        T = orig(g, P, *a, **k)
        got.setdefault(P, (g, T))
        return T
    u._cons_adjust = hook
    try:
        u.PRESETS["proposal"]["bf16_stripe_macros"] = 2 * rows[58]["BF16_pairs_per_die"]
        u.PRESETS["proposal"]["idx_reader_Bpc"] = 3000
        with u._cons_ctx(ctx):
            p = u.cons_v41_rom(58, 8, 36, bf16="columns", clock_hz=u.PRODUCT_CLOCK_HZ,
                               field_concurrency=u.FIELD_CONCURRENCY,
                               added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT),
                               dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, "w18"), elem_stages=8,
                               ss_wire=True, serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM,
                               vmh=u.VMC_FUSED, hub_block=u.PRODUCT_HUB)
    finally:
        u._cons_adjust = orig
        u.PRESETS["proposal"].clear()
        u.PRESETS["proposal"].update(saved)
    g, T = got[1]
    return g, T, p


def layer_times(g):
    fin = g.solve(True)
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    tot = {}
    for n in g.path(sink):
        L = n.split(".")[0]
        tot[L] = tot.get(L, 0.0) + sum(g.contrib[n].values())
    return fin[sink], tot


SRC_OF = {**{L: 2 for L in range(2, 20)}, **{L: 20 for L in range(20, 24)}, **{L: 24 for L in range(24, 40)}}
REINDEX = (24, 28, 32, 36)


def _ckv_cycles(ckv):
    ck = {}
    for res in ckv["results"]:
        L = int(res["case"].split("_")[0][1:])
        c, f = res["cycles"], res["fields"]["CKVSEL"]
        end = c["last_score"] if c.get("last_score", -1) >= 0 else c["last_row_staged"] + ATTN_JOB["tail_after_last_row"]
        span = c["all_rows_arrived"] - c["last_id"]
        ck[L] = dict(cycles=end - c["last_id"], last_id=c["last_id"], end=end, last_pv=c["last_pv"],
                     engine=c.get("last_score", -1) >= 0, pass_=res["pass_"], lat=f["lat"],
                     hbm_sectors=f["hbm_reads"], hbm_bytes=32 * f["hbm_reads"],
                     owned_rows_per_die=res["owned_rows_per_die"],
                     fetch_span_cycles=span,
                     achieved_TBps_4dies=round(32 * f["hbm_reads"] / (span / CLK) / 1e12, 4))
    return ck


def _apply(g, reader, sel, ck, variant, gather=None):
    """Replace every context-dependent node of the graph by its measurement.  variant 'as_built': the four
    re-index layers score all 1,048,576 keys (what the native program and the golden do: score, then mask to the
    16,384 candidates); 'candidate_gather': they read only the candidate blocks (an UNBUILT lever: its index read
    stays modelled, its select is the measured candidate stream); 'mask_drop': full measured scan, but the masked
    (-inf) keys are dropped before the select (UNBUILT lane compaction; select = the measured candidate stream)."""
    rd = {r["name"]: r for r in reader["runs"]}

    def worst(tag):
        return max((r for n, r in rd.items() if n.startswith(tag) and "clk833" in n), key=lambda r: r["cycles"])
    scan_reader = {2: worst("csa2_full_L2"), 8: worst("csa2_full_L2"), 14: worst("csa2_full_L2"),
                   20: worst("csa1_full_L20")}
    if variant in ("as_built", "mask_drop"):
        scan_reader.update({L: worst("csa1_full_L20") for L in REINDEX})
    def reindex_tag(L):
        """as_built: the full masked stream; the levers: their MEASURED select stream when
        tools/dsrom_reindex_candidates.py records are given (L24 / L28 measured, L32 / L36 take the
        worse of the two), else the candidate-only stream of the 1M record (projection)."""
        suffix = {"mask_drop": "_mdrop", "candidate_gather": "_gather"}.get(variant)
        if variant == "as_built":
            return "L24_full"
        own = [f"L{x}{suffix}" for x in (24, 28) if f"L{x}{suffix}" in sel]
        if not own:
            return "L24"
        if f"L{L}{suffix}" in sel:
            return f"L{L}{suffix}"
        cost = lambda t: max(sg["last"] - sg["first"] + 1 + sg["tail"] for sg in sel[t]["local"]["runs"][0]["per_segment"])
        return max(own, key=cost)
    seltag = {2: "L2", 8: "L8", 14: "L14", 20: "L20", **{L: reindex_tag(L) for L in REINDEX}}
    sel_local, sel_final = {}, {}
    for L, key in seltag.items():
        r = sel[key]
        segs = r["local"]["runs"][0]["per_segment"]
        sel_local[L] = max(sg["last"] - sg["first"] + 1 + sg["tail"] for sg in segs)
        fs = r["final"]["runs"][0]["per_segment"][0]
        sel_final[L] = fs["last"] - fs["first"] + 1 + fs["tail"]
    patches, modelled = [], []

    def put(name, cycles, src):
        nd = g.nodes[name]
        old = dict(issue=nd["issue"], depth=nd["depth"], ctrl=nd["ctrl"])
        nd.update(issue=cycles / CLK, depth=0.0, ctrl=0.0, stream=False)
        nd.pop("wire_in", None)
        nd.pop("wire_out", None)
        patches.append(dict(node=name, model_us=round((old["issue"] + old["depth"] + old["ctrl"]) * 1e6, 4),
                            measured_us=round(cycles / CLK * 1e6, 4), measured_cycles=int(cycles), source=src))
    for L in range(40):
        pre = f"L{L}.attn."
        if pre + "idx.score" in g.nodes:
            if L in scan_reader:
                r = scan_reader[L]
                put(pre + "idx.score", r["cycles"] + IDX_ARRAY["query_settle"] + IDX_ARRAY["latency"],
                    f"reader {r['name']} ({r['keys']} keys/rank, {r['sectors']} sectors/rank) + idx array settle/latency")
            elif gather is not None and L in REINDEX:
                w = gather["worst_rank"]
                put(pre + "idx.score", w["cycles"] + IDX_ARRAY["query_settle"] + IDX_ARRAY["latency"],
                    f"candidate-block gather {w['name']} (real 1M candidate lists, {w['sectors']} sectors/rank, "
                    f"{w['achieved_TBps']} TB/s) + idx array settle/latency")
            else:
                modelled.append(dict(node=pre + "idx.score", us=round(sum(g.contrib[pre + "idx.score"].values()) * 1e6, 4),
                                     why="candidate-block gather reader is not built (unbuilt lever)"))
            put(pre + "idx.topk_local", sel_local[L], f"select {seltag[L]} golden 1M scores: ingest + tail, worst rank")
            put(pre + "idx.topk_final", sel_final[L], f"cross-die final select {seltag[L]} (4 x 512 real local selections)")
        if L >= 2:
            c = ck[SRC_OF[L]]
            if pre + "gather" in g.nodes:
                put(pre + "gather", c["cycles"], f"CKV path L{SRC_OF[L]} real 1M selection: last ID -> last q.k score")
                put(pre + "rows_allgather", 0, "inside the measured CKV path (all-gather links)")
            else:
                put(pre + "rows_allgather", c["cycles"],
                    f"re-use layer: CKV path on source L{SRC_OF[L]}'s real 1M selection, last ID -> last q.k score")
            put(pre + "scores", 0, "inside the measured CKV path (q.k overlaps staging)")
        else:
            put(pre + "scores", ATTN_JOB["window128_qk_last"], "attention engine q.k, T=128 staged rows (exact)")
    return patches, modelled, scan_reader, sel_local, sel_final


WINDOW_TYPES = ("window_only", "scan", "reindex", "reuse")


def _window_type(L):
    if L in (0, 1):
        return "window_only"
    if L in (2, 8, 14, 20):
        return "scan"
    if L in REINDEX:
        return "reindex"
    return "reuse"


def _apply_window(g, win, kind):
    """S81-bound WINDOW terms (tools/dsrom_s81_window_la.py record, results/rtl/dsrom_s81_window_bind_20261004):
    per layer two measured nodes are inserted ahead of the layer's attention scores, in the S81 die's order --
      own_row_write  the token's own packed row, 16 blocks through the as-built writer on the K channel, after
                     kv_rope_qdq (measured with the layer type's concurrent index traffic);
      window_load    the 128-row job, started at the attention issue (after the own row, q_rope and, in an
                     indexed layer, the final select): start -> rows staged (CKV layers, whose measured CKV path
                     streams the staged rows) or start -> rows delivered (window-only layers, whose patched
                     scores node is the q.k over staged rows);
    kind 'la' = the bound full-bandwidth load, 'asbuilt_c8' = the S81 selection's as-built refill (credits 8)."""
    terms = win["composition_terms"][kind]
    patches, new = [], {}
    for name, nd in g.nodes.items():
        if name.endswith(".attn.scores"):
            L = int(name.split(".")[0][1:])
            pre = f"L{L}.attn."
            t = terms[_window_type(L)]
            wr = dict(name=pre + "own_row_write", deps=[pre + "kv_rope_qdq"], layer=nd["layer"],
                      issue=t["own_row_write_cycles"] / CLK, issue_cat="kv_sweep", depth=0.0, depth_cat="kv_sweep",
                      ctrl=0.0, stream=False, kind="op", sweep=None, desc="S81 own-row write (measured)")
            deps = [pre + "own_row_write", pre + "q_rope"] + ([pre + "idx.topk_final"] if pre + "idx.topk_final" in g.nodes else [])
            ld = dict(name=pre + "window_load", deps=deps, layer=nd["layer"], issue=t["window_cycles"] / CLK,
                      issue_cat="kv_sweep", depth=0.0, depth_cat="kv_sweep", ctrl=0.0, stream=False, kind="op",
                      sweep=None, desc=f"S81 WINDOW job ({kind}, measured)")
            new[wr["name"]], new[ld["name"]] = wr, ld
            nd = dict(nd, deps=nd["deps"] + [pre + "window_load"])
            for n in (wr, ld):
                patches.append(dict(node=n["name"], model_us=0.0, measured_us=round(n["issue"] * 1e6, 4),
                                    measured_cycles=int(round(n["issue"] * CLK)), source=f"{t['source']} ({kind})"))
        new[name] = nd
    g.nodes = new
    return patches


def cmd_compose(a):
    import copy
    reader = json.loads(Path(a.reader).read_text())
    sel = {}
    for f in a.select:
        sel.update(json.loads(Path(f).read_text())["layers"])
    runs = [json.loads(Path(f).read_text()) for f in a.ckv]
    gather = json.loads(Path(a.gather).read_text()) if a.gather else None
    measured_levers = bool(a.reindex_select)
    if a.reindex_select:
        rs = json.loads(Path(a.reindex_select).read_text())
        assert rs["status"] == "pass"
        for tag, r in rs["layers"].items():
            sel[f"{tag}_mdrop"] = dict(local=dict(runs=r["drop_dense"]["runs"]), final=r["final"])
            sel[f"{tag}_gather"] = dict(local=dict(runs=r["gather"]["runs"]), final=r["final"])
    if gather is not None:
        assert gather["status"] == "pass"
    win = json.loads(Path(a.window).read_text()) if a.window else None
    if win is not None:
        assert win["status"] == "pass"
    g0, T0, _ = s58_graph()
    assert abs(1 / T0 - 2535.5) < 0.1, T0
    t_model, lt_model = layer_times(g0)
    ar_model = t_model * 1e6 + S81_EXTRA_HOPS * HOP_US
    model_l20_idx = sum(g0.nodes[n]["issue"] for n in g0.nodes if n.startswith("L20.attn.idx")) * 1e6
    out = dict(schema="opentallas.dsrom-1m.composition.v2", context=CTX, position=POS,
               model=dict(AR_us=round(ar_model, 3), AR_tok_s=round(1e6 / ar_model, 1)), variants={})
    for run in runs:
        ck = _ckv_cycles(run)
        lat = run["results"][0]["fields"]["CKVSEL"]["lat"]
        for variant in ("as_built", "mask_drop", "candidate_gather"):
            g = copy.deepcopy(g0)
            patches, modelled, scan_reader, sl, sf = _apply(g, reader, sel, ck, variant, gather)
            t, lt = layer_times(g)
            ar = t * 1e6 + S81_EXTRA_HOPS * HOP_US
            idx_us = lambda L: sum(p["measured_us"] for p in patches if p["node"].startswith(f"L{L}.attn.idx"))
            l20_occ = WAVEFRONT["l20_occ_us"] - model_l20_idx + idx_us(20)
            re_occ = WAVEFRONT["l20_occ_us"] - model_l20_idx + idx_us(24)   # same stage work, its own index terms
            occ = max(WAVEFRONT["head_occ_us"], l20_occ, re_occ)
            ii = occ * (1 + WAVEFRONT["overhead"]) + WAVEFRONT["hop_us"]
            verify = ar + WAVEFRONT["positions"] * ii
            mtp = {k: round(DRAFT["tau"] * 1e6 / (verify + DRAFT[k] + DRAFT["seed_commit_us"]), 1)
                   for k in ("fused_us", "as_built_us", "l1l2_nv5_us")}
            types = {}
            for tname, v in TYPES.items():
                L = f"L{v['rep']}"
                types[tname] = dict(representative=v["rep"], count=len(v["layers"]), kind=v["kind"],
                                    model_us=round(lt_model[L] * 1e6, 3), measured_composed_us=round(lt[L] * 1e6, 3))
            types["head"] = dict(model_us=round(lt_model["head"] * 1e6, 3), measured_composed_us=round(lt["head"] * 1e6, 3))
            out["variants"][f"{variant}.lat{lat}"] = dict(
                AR_us=round(ar, 3), AR_tok_s=round(1e6 / ar, 1), II_us=round(ii, 3), verify_us=round(verify, 3),
                stage_occupancy_us=dict(head=WAVEFRONT["head_occ_us"], L20=round(l20_occ, 3), reindex=round(re_occ, 3)),
                MTP_tok_s=mtp, per_layer_type=types, patches=patches, still_modelled_context_terms=modelled,
                sel_local_cycles=sl, sel_final_cycles=sf, ckv=ck,
                scan_reader={L: dict(name=r["name"], cycles=r["cycles"], sectors=r["sectors"], bytes=r["bytes"],
                                     TBps=round(r["achieved_TBps"], 3), fraction_of_peak=round(r["fraction_of_peak"], 4))
                             for L, r in scan_reader.items()})
            print(variant, lat, json.dumps(dict(AR_us=round(ar, 3), AR=round(1e6 / ar, 1), II=round(ii, 3), MTP=mtp)),
                  flush=True)
        if win is not None:
            # the adopted re-index variant with the S81-bound window (and the gather read through the S81 wmux),
            # and the same with the S81 selection's as-built window refill, for reference
            base = out["variants"][f"candidate_gather.lat{lat}"]
            for kind in ("la", "asbuilt_c8"):
                g = copy.deepcopy(g0)
                gs = win["kgather_s81"] if kind == "la" else gather
                patches, modelled, scan_reader, sl, sf = _apply(g, reader, sel, ck, "candidate_gather", gs)
                patches += _apply_window(g, win, kind)
                t, lt = layer_times(g)
                ar = t * 1e6 + S81_EXTRA_HOPS * HOP_US
                idx_us = lambda L: sum(p["measured_us"] for p in patches if p["node"].startswith(f"L{L}.attn.idx"))
                dl = lambda L: (lt[f"L{L}"] - layer_times_cache[f"L{L}"]) * 1e6
                g_ref = copy.deepcopy(g0)
                _apply(g_ref, reader, sel, ck, "candidate_gather", gs)
                _, layer_times_cache = layer_times(g_ref)
                l20_occ = WAVEFRONT["l20_occ_us"] - model_l20_idx + idx_us(20) + max(0.0, dl(20))
                re_occ = WAVEFRONT["l20_occ_us"] - model_l20_idx + idx_us(24) + max(0.0, dl(24))
                occ = max(WAVEFRONT["head_occ_us"], l20_occ, re_occ)
                ii = occ * (1 + WAVEFRONT["overhead"]) + WAVEFRONT["hop_us"]
                verify = ar + WAVEFRONT["positions"] * ii
                mtp = {k: round(DRAFT["tau"] * 1e6 / (verify + DRAFT[k] + DRAFT["seed_commit_us"]), 1)
                       for k in ("fused_us", "as_built_us", "l1l2_nv5_us")}
                types = {}
                for tname, v in TYPES.items():
                    L = f"L{v['rep']}"
                    types[tname] = dict(representative=v["rep"], count=len(v["layers"]), kind=v["kind"],
                                        model_us=round(lt_model[L] * 1e6, 3), measured_composed_us=round(lt[L] * 1e6, 3))
                types["head"] = dict(model_us=round(lt_model["head"] * 1e6, 3), measured_composed_us=round(lt["head"] * 1e6, 3))
                out["variants"][f"candidate_gather.lat{lat}.s81_window_{kind}"] = dict(
                    AR_us=round(ar, 3), AR_tok_s=round(1e6 / ar, 1), II_us=round(ii, 3), verify_us=round(verify, 3),
                    stage_occupancy_us=dict(head=WAVEFRONT["head_occ_us"], L20=round(l20_occ, 3), reindex=round(re_occ, 3)),
                    MTP_tok_s=mtp, per_layer_type=types, patches=patches, still_modelled_context_terms=modelled,
                    delta_vs_candidate_gather_AR_us=round(ar - base["AR_us"], 3),
                    window_record=a.window, gather_read=gs.get("worst_rank", {}).get("name"))
                print("candidate_gather", lat, "s81_window", kind, json.dumps(dict(AR_us=round(ar, 3), AR=round(1e6 / ar, 1),
                      II=round(ii, 3), MTP=mtp)), flush=True)
    out["constants"] = dict(clock_hz=CLK, hop_us=HOP_US, extra_hops=S81_EXTRA_HOPS, idx_array=IDX_ARRAY, attn=ATTN_JOB,
                            wavefront=WAVEFRONT, draft=DRAFT)
    rd = {r["name"]: r for r in reader["runs"]}
    ck = _ckv_cycles(runs[-1])
    scan = lambda n: dict(keys_per_rank=rd[n]["keys"], bytes_per_rank=rd[n]["bytes"], bytes_4_ranks=4 * rd[n]["bytes"],
                          seconds=rd[n]["seconds"], achieved_TBps_per_rank=round(rd[n]["achieved_TBps"], 3),
                          peak_TBps_per_rank=rd[n]["peak_TBps"], fraction_of_peak=round(rd[n]["fraction_of_peak"], 4))
    l2, l20, w = scan("csa2_full_L2_clk833"), scan("csa1_full_L20_clk833"), scan("window128_per_stack_clk833")
    ckb = {L: ck[L]["hbm_bytes"] for L in ck}
    n_gather = {2: 18, 20: 4, 24: 16}           # layers whose CKV rows come from each source's selection
    out["hbm_per_token"] = dict(
        scope="KV/index HBM bytes of ONE decode token at position 1,048,575 (TP4: 4 ranks x 4 HBM3E stacks); "
              "Engram tables are in mask ROM on the DS-ROM (0 HBM bytes); weights in ROM (0 HBM bytes)",
        index_scan=dict(ratio2_L2_L8_L14=l2, ratio1_L20=l20,
                        ratio1_reindex_L24_L28_L32_L36_as_built="same read as L20 (the native index unit scores all keys, then masks)"),
        index_scan_bytes_as_built=3 * l2["bytes_4_ranks"] + 5 * l20["bytes_4_ranks"],
        ckv_selected_gather=dict(bytes_per_layer={f"L{L}_selection": b for L, b in ckb.items()},
                                 layers=n_gather, total_bytes=sum(n_gather[L] * ckb[L] for L in ckb),
                                 achieved_TBps_4_ranks={f"L{L}": ck[L]["achieved_TBps_4dies"] for L in ck},
                                 note="512 scattered rows: latency bound, not bandwidth bound"),
        window_rows=dict(per_stack=w, note="128-row window load, latency bound (first beat at ~110 cycles)"),
        engram_bytes=0)
    v = out["variants"]
    out["headline"] = dict(
        basis="as_built.lat259: every context-dependent term measured in full-shape RTL at position 1,048,575 "
              "(index read on timed HBM, select on the golden 1M scores, CKV gather + q.k on the golden 1M "
              "selections, CKV HBM latency 259 cycles, conservative over the reader's measured 87-88 ns mean)",
        AR_tok_s=v["as_built.lat259"]["AR_tok_s"], MTP_fused_tok_s=v["as_built.lat259"]["MTP_tok_s"]["fused_us"],
        model_AR_tok_s=out["model"]["AR_tok_s"],
        **{("levers_measured" if measured_levers else "levers_unbuilt"):
           {k: dict(AR_tok_s=v[k + ".lat259"]["AR_tok_s"], MTP_fused_tok_s=v[k + ".lat259"]["MTP_tok_s"]["fused_us"],
                    II_us=v[k + ".lat259"]["II_us"], reindex_occupancy_us=v[k + ".lat259"]["stage_occupancy_us"]["reindex"])
            for k in ("mask_drop", "candidate_gather")}},
        **({"s81_window": {k: dict(AR_tok_s=v[f"candidate_gather.lat259.s81_window_{k}"]["AR_tok_s"],
                                   MTP_fused_tok_s=v[f"candidate_gather.lat259.s81_window_{k}"]["MTP_tok_s"]["fused_us"],
                                   AR_us=v[f"candidate_gather.lat259.s81_window_{k}"]["AR_us"],
                                   II_us=v[f"candidate_gather.lat259.s81_window_{k}"]["II_us"])
                               for k in ("la", "asbuilt_c8")}} if win is not None else {}),
        interim="L20 (global-KV scan layer) is this tool's component measurement; Codex's S81 minimum run owns L20 at 1M "
                "and replaces it when it lands",
        still_modelled=["context-independent nodes of every layer (weights in ROM: projections, MoE, norms, softmax/p.v "
                        "at T = 640, hc/Sinkhorn) from the S81 unified graph", "L20 candidate-block select (cand.*)",
                        "stage hop 0.482 us (RTL endpoint + technology channel delay, no PHY)",
                        "head 13.63 us in the AR path (wavefront II uses the measured reduced-shape head 12.37 us)",
                        *([] if gather is not None else ["candidate_gather variant: candidate-block index read (unbuilt)"]),
                        *([] if measured_levers else ["mask_drop variant: lane compaction ahead of the select (unbuilt)"]),
                        "L1+L2 NV5 draft (56.07 us): SS pre-layout screen fails, not closed"])
    out["reader_runs"] = reader["runs"]
    Path(a.out).write_text(json.dumps(out, indent=1, default=str) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("reader")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--jobs", type=int, default=6)
    r.add_argument("--only", default="")
    s = sub.add_parser("select")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    s.add_argument("--layers", default="20,2,8,14,24")
    c = sub.add_parser("ckvvec")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    m = sub.add_parser("compose")
    m.add_argument("--reader", required=True)
    m.add_argument("--select", nargs="+", required=True)
    m.add_argument("--ckv", nargs="+", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--gather", default="", help="tools/dsrom_reindex_candidates.py gather.json (measured gather read)")
    m.add_argument("--reindex-select", default="", help="tools/dsrom_reindex_candidates.py select.json")
    m.add_argument("--window", default="", help="tools/dsrom_s81_window_la.py window_load.json (S81-bound WINDOW terms)")
    a = ap.parse_args()
    dict(reader=cmd_reader, select=cmd_select, ckvvec=cmd_ckvvec, compose=cmd_compose)[a.cmd](a)


if __name__ == "__main__":
    main()
