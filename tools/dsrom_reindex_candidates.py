#!/usr/bin/env python3
"""DS-ROM (DeepSeek-V4.1-Flash) re-index layers (L24, L28, L32, L36) at 1M: the two candidate-only
fixes, built and measured in full-shape RTL at position 1,048,575 on the 1M reference token's golden
data (results/rtl/w17_v41_1m_reference_token.json, seed 20260930, shards in --gold).

As built (results/rtl/dsrom_1m_measured_20261004) the re-index unit scores all 1,048,576 keys, writes -inf
outside the 16,384 candidate positions (the golden's `where(cand, s, -inf)`), and the top-512 select
on that mostly -inf stream overflows and replays twice: 12,359 select cycles, the slowest stage.

  (1) mask-drop  rtl/hdc/v41x/ot_hdc_v41x_sel_mdrop.sv (MDROP=1, default 0): masked keys are dropped
      in front of ot_hdc_v41x_sel (lane valid = valid & keep; empty beats not forwarded).
  (2) gather     rtl/hdc/v41x/ot_hdc_v41x_idx_kgather.sv: reads ONLY the candidate blocks' keys
      (8 keys = 4 code columns + 1 scale sector = 17 sectors a block) from HBM, from the candidate
      list the candidate-source layer (L20) already produces; replaces the full-range scan for
      these layers (opt-in).

Subcommands (heavy ones run on the compute host under admit.sh):
  gather   the gather unit, four timed HBM3E stacks a rank (ot_hdc_v41x_idx_hbm), on the REAL 1M
           candidate lists of every rank, two placements, plus functional edge cases; every key of
           every beat checked, 17 sectors a block.
  select   on the golden 1M L24 / L28 index scores, rank by rank (quarter = stack):
             mdrop      the drop stage + select on the FULL scored stream (masked lanes carry
                        adversarial large values: they would be selected if not dropped), MDROP=1;
             mdrop_off  the same bench at MDROP=0 (default-off = as built) on rank 0 of L24;
             drop_dense the select on the post-drop beats back to back (the tool convention of
                        tools/dsrom_1m_measure.py: select ingest + tail);
             gather     the select on the gather unit's output order (16 candidate keys a beat);
             final      the cross-die select on the four ranks' local selections;
           bit-exact against tools/hdc_golden_v41.topk_lowest_index on the golden MASKED scores, and
           the final equals the golden layer's own selection (value desc, ties to the lower index).
  screen   collect SS-setup / FF-hold pre-layout screens (tools/dsrom_reindex_screen.py) of the
           changed logic at 1.2 GHz.
Records: results/rtl/dsrom_reindex_candidates_20261004/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/rtl/dsrom_reindex_candidates_20261004"
GOLD_DEFAULT = Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930")
CTX, POS, TP, STACKS = 1048576, 1048575, 4, 4
PER_RANK = CTX // TP
PER_STACK = PER_RANK // STACKS
NINF = 0xFF80

KG_SRC = ["rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_kgather.sv",
          "rtl/test/tb_hdc_v41x_idx_kgather.sv", "rtl/test/hdc_v41x_idx_kgather.cpp"]
MD_SRC = ["rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv", "rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv",
          "rtl/hdc/v41x/ot_hdc_v41x_sel.sv", "rtl/hdc/v41x/ot_hdc_v41x_sel_mdrop.sv",
          "rtl/test/tb_hdc_v41x_sel_mdrop.sv", "rtl/test/hdc_v41x_sel_mdrop_harness.cpp"]
PLACEMENTS = {"p1": dict(BASE=0, BSTEP=1000, OSTEP=136), "p2": dict(BASE=123, BSTEP=777, OSTEP=8)}
CLK_PS = 833
BURST_PS = 1024
PEAK_SECTORS_PER_CYCLE_RANK = STACKS * 32 * CLK_PS / BURST_PS      # 4 stacks x 32 PCs, 32 B / 1,024 ps
PEAK_TBPS_RANK = STACKS * 32 * 32 / (BURST_PS * 1e-12) / 1e12
HBM = dict(tFAW_ns=15.0, acts_per_tFAW=4, tRRD_S_ns=2.5, burst_ns=1.024, pcs=32)


def sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verilator():
    import rtl_hdc_v41x_sel_campaign as S
    return S.VERILATOR


def cand_blocks(gold: Path):
    c = np.load(gold / "ctx1048576_cand.npz")["cand"]
    b = c.reshape(-1, 8)
    assert not (b.any(1) & ~b.all(1)).any(), "candidate blocks are whole 8-position blocks"
    return c, np.nonzero(b.any(1))[0]


def rank_lists(blk, r):
    out = []
    for q in range(STACKS):
        lo = (r * PER_RANK + q * PER_STACK) // 8
        out.append([int(x - lo) for x in blk if lo <= x < lo + PER_STACK // 8])
    return out


# ------------------------------------------------------------------------------------------------ gather
KGS = re.compile(r"KGSTACK s=(\d+) blocks=(\d+) sectors=(\d+) first=(-?\d+) last=(-?\d+)")
KGH = re.compile(r"KGHBM s=(\d+) rd=(\d+) act=(\d+) hit=(\d+) conf=(\d+) ref=(\d+) bp=(\d+) lat_sum_ps=(\d+) "
                 r"lat_max_ps=(\d+) pc_rd_min=(\d+) pc_rd_max=(\d+)")
KGP = re.compile(r"KGATHER_PASS blocks=([\d,]+) sectors=(\d+) last=(-?\d+)")


def kg_build(obj: Path, params: dict):
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [verilator(), "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
           "--top-module", "tb_hdc_v41x_idx_kgather", *[f"-G{k}={v}" for k, v in params.items()],
           "--Mdir", str(obj), *[str(ROOT / s) for s in KG_SRC]]
    subprocess.run(cmd, check=True, capture_output=True, cwd=ROOT)
    return obj / "Vtb_hdc_v41x_idx_kgather"


def kg_run(binary: Path, pfx: Path, lists):
    for q, l in enumerate(lists):
        assert l == sorted(set(l)) and len(l) <= 2048
        Path(f"{pfx}.s{q}").write_text(f"{len(l)}\n" + "".join(f"{x:x}\n" for x in l))
    t0 = time.time()
    r = subprocess.run([str(binary), f"+PFX={pfx}"], capture_output=True, text=True)
    m = KGP.search(r.stdout)
    if r.returncode or not m:
        return dict(pass_=False, log=(r.stdout + r.stderr)[-3000:])
    stacks = []
    for sm, hm in zip(KGS.finditer(r.stdout), KGH.finditer(r.stdout)):
        s, nb, sec, first, last = map(int, sm.groups())
        _, rd, act, hit, conf, ref, bp, ls, lm, rmin, rmax = map(int, hm.groups())
        stacks.append(dict(stack=s, blocks=nb, sectors=sec, first_out=first, last_out=last, hbm_reads=rd,
                           activates=act, row_hits=hit, row_conflicts=conf, request_backpressure_pc_cycles=bp,
                           mean_read_latency_ns=round(ls / rd / 1000, 1) if rd else None,
                           max_read_latency_ns=round(lm / 1000, 1), reads_per_pc_min=rmin, reads_per_pc_max=rmax))
    sectors, last = int(m.group(2)), int(m.group(3))
    first = min((s["first_out"] for s in stacks if s["first_out"] >= 0), default=-1)
    secs = last * CLK_PS * 1e-12
    row = dict(pass_=True, blocks=[int(x) for x in m.group(1).split(",")], sectors=sectors, bytes=32 * sectors,
               cycles=last, first_out=first, seconds=secs, wall_s=round(time.time() - t0, 1), stacks=stacks)
    if last > 0:
        row["achieved_TBps"] = round(32 * sectors / secs / 1e12, 4)
        row["fraction_of_peak"] = round(sectors / last / PEAK_SECTORS_PER_CYCLE_RANK, 4)
        if last > first >= 0:
            row["fraction_of_peak_first_to_last_beat"] = round(sectors / (last - first) / PEAK_SECTORS_PER_CYCLE_RANK, 4)
        acts = sum(s["activates"] for s in stacks)
        rd = sum(s["hbm_reads"] for s in stacks)
        row["activates_per_sector"] = round(acts / rd, 3)
        # tFAW bound of an ACT-per-sector stream: 4 ACTs per 15 ns per pseudo-channel
        row["tFAW_bound_fraction_of_peak"] = round(
            (HBM["acts_per_tFAW"] / HBM["tFAW_ns"]) / (1 / HBM["burst_ns"]) / (acts / rd), 4)
    return row


def functional_cases(rng):
    """Edge cases (local block indices of a 65,536-key stack: 0 .. 8,191)."""
    cases = {}
    cases["edges"] = [sorted(set(list(range(0, 16)) + [126, 127, 128, 129, 1023, 1024, 8190, 8191])), [], [4000],
                      sorted(int(x) for x in rng.choice(8192, 300, replace=False))]
    cases["full_list_2048"] = [sorted(int(x) for x in rng.choice(8192, 2048, replace=False)), [7], [], [8191]]
    cases["dense_run_2048"] = [list(range(3000, 5048)), list(range(0, 8192, 4)), [0], list(range(8192 - 64, 8192))]
    for i in range(3):
        cases[f"random{i}"] = [sorted(int(x) for x in rng.choice(8192, int(rng.integers(0, 600)), replace=False))
                               for _ in range(STACKS)]
    return cases


def cmd_gather(a):
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    _, blk = cand_blocks(a.gold)
    rng = np.random.default_rng(20261004)
    funcs = functional_cases(rng)
    bins = {p: kg_build(out / f"obj_kg_{p}", dict(PLACEMENTS[p], CLK_PS=CLK_PS)) for p in PLACEMENTS}
    runs = {}
    for p, b in bins.items():
        for r in range(TP):
            name = f"real_rank{r}_{p}"
            runs[name] = kg_run(b, out / name, rank_lists(blk, r))
            runs[name].update(kind="real", rank=r, placement=p)
            print(name, json.dumps({k: runs[name].get(k) for k in ("pass_", "blocks", "cycles", "achieved_TBps",
                                                                  "fraction_of_peak")}), flush=True)
        for fname, lists in funcs.items():
            name = f"func_{fname}_{p}"
            runs[name] = kg_run(b, out / name, lists)
            runs[name].update(kind="functional", placement=p)
            print(name, runs[name].get("pass_"), runs[name].get("cycles"), flush=True)
    real = [v for v in runs.values() if v["kind"] == "real"]
    worst = max(real, key=lambda v: v.get("cycles", 1 << 30))
    full = json.loads((ROOT / "results/rtl/dsrom_1m_measured_20261004/reader.json").read_text())
    fs = {r["name"]: r for r in full["runs"]}["csa1_full_L20_clk833"]
    srcs = {p: sha(ROOT / p) for p in KG_SRC + ["tools/dsrom_reindex_candidates.py"]}
    ver = subprocess.run([verilator(), "--version"], capture_output=True, text=True).stdout.strip()
    rec = dict(schema="opentallas.dsrom-reindex.gather.v1", simulator=ver, source_sha256=srcs,
               golden_candidates=dict(npz=sha(a.gold / "ctx1048576_cand.npz"), blocks=int(len(blk)),
                                      keys=int(8 * len(blk))),
               clock_ps=CLK_PS, peak_TBps_rank=PEAK_TBPS_RANK,
               worst_rank=dict(name=[k for k, v in runs.items() if v is worst][0], cycles=worst["cycles"],
                               sectors=worst["sectors"], bytes=worst["bytes"], achieved_TBps=worst["achieved_TBps"],
                               fraction_of_peak=worst["fraction_of_peak"]),
               full_scan_as_built=dict(name=fs["name"], cycles=fs["cycles"], sectors=fs["sectors"], bytes=fs["sectors"] * 32,
                                       fraction_of_peak=round(fs["sectors"] / fs["cycles"] / PEAK_SECTORS_PER_CYCLE_RANK, 4)),
               runs=runs, status="pass" if all(v.get("pass_") for v in runs.values()) else "fail")
    (out / "gather.json").write_text(json.dumps(rec, indent=1) + "\n")
    print("gather", rec["status"], json.dumps(rec["worst_rank"]), flush=True)


# ------------------------------------------------------------------------------------------------ select
def bf16_bits(x):
    import rtl_hdc_v41x_sel_campaign as S
    return S.bf16_bits(x)


def expect(bits_masked, pos, cuts, K):
    """Per quarter [(pos, bits, ninf)] of topk_lowest_index on the golden MASKED values of one rank."""
    import hdc_golden_v41 as G
    import rtl_hdc_v41x_sel_campaign as S
    v = S.vals_of(bits_masked)
    sel = sorted(int(i) for i in G.topk_lowest_index(v, min(K, len(v))))
    exps = []
    for q in range(len(cuts) - 1):
        lo, hi = cuts[q], cuts[q + 1]
        exps.append([(int(pos[i]), int(bits_masked[i]), int(bits_masked[i] == NINF)) for i in sel if lo <= i < hi])
    return exps, [int(pos[i]) for i in sel]


def write_mdrop_vectors(segs, d: Path, tag, W=16):
    """segs: per segment (per quarter beats [(lv, keep, [(bits, pos)] * W)], k, exps)."""
    pfx = d / tag
    h = hashlib.sha256()
    for q in range(STACKS):
        li, le = [], []
        for beats, k, exps in segs:
            bq = beats[q]
            for bi, (lv, keep, lanes) in enumerate(bq):
                li.append(f"{int(bi == len(bq) - 1)} {k} {lv:x} {keep:x} " +
                          " ".join(f"{b:x} {p:x}" for b, p in lanes) + "\n")
            le.append(f"S {len(exps[q])} {len(bq)}\n")
            le += [f"{p:x} {vb:x} {ni}\n" for p, vb, ni in exps[q]]
        Path(f"{pfx}.in{q}").write_text("".join(li))
        Path(f"{pfx}.exp{q}").write_text("".join(le))
        h.update(Path(f"{pfx}.in{q}").read_bytes() + Path(f"{pfx}.exp{q}").read_bytes())
    return pfx, h.hexdigest()


def md_build(obj: Path, mdrop: int, K=512, AW=8):
    obj.mkdir(parents=True, exist_ok=True)
    subprocess.run([verilator(), "--cc", "--exe", "--build", "-j", "8", "-O2", "-Wno-fatal", "--top-module",
                    "tb_hdc_v41x_sel_mdrop", "-GQ=4", "-GW=16", "-GIW=20", f"-GK={K}", f"-GAW={AW}", "-GMAXB=8192",
                    f"-GMDROP={mdrop}", "-Mdir", str(obj), *[str(ROOT / s) for s in MD_SRC], "-CFLAGS", "-O1"],
                   check=True, capture_output=True, cwd=ROOT)
    return obj / "Vtb_hdc_v41x_sel_mdrop"


def md_run(binary, pfx, labels):
    import rtl_hdc_v41x_sel_campaign as S
    r = subprocess.run([str(binary), f"+PFX={pfx}"], capture_output=True, text=True)
    res = S.parse(r.stdout)
    m = re.search(r"SHORT=(\d+) MDROP=(\d+)", r.stdout)
    res["short"] = int(m.group(1)) if m else None
    res["pass"] = res["pass"] and res["short"] == 0
    for ps, lab in zip(res.get("per_segment", []), labels):
        ps["family"] = lab
    return res


def seg_cost(run, convention=True):
    """Worst segment: ingest span + tail (tool convention) or tail after the last scored key."""
    segs = run["per_segment"]
    if convention:
        return max(sg["last"] - sg["first"] + 1 + sg["tail"] for sg in segs)
    return max(sg["tail"] for sg in segs)


def cmd_select(a):
    import rtl_hdc_v41x_sel_campaign as S
    import hdc_golden_v41 as G
    G.set_arith("chunk8") if hasattr(G, "set_arith") else None
    import dsrom_1m_measure as M
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    W, IW, K = 16, 20, 512
    cand, _ = cand_blocks(a.gold)
    rng = np.random.default_rng(20261004)
    bins = {}
    results = {}
    for L in [int(x) for x in a.layers.split(",")]:
        z, j = M.gold_layer(a.gold, L)
        s = z[f"L{L}.index_scores"]
        assert len(s) == CTX and (np.isfinite(s) == cand).all(), "re-index mask = the L20 candidate blocks"
        golden_sel = sorted(int(x) for x in j["ctx_out"]["sel"])
        fin = s[np.isfinite(s)]
        adv = int(bf16_bits(np.array([float(fin.max()) * 2 + 1.0]))[0])     # beats every real score
        md_segs, dense_segs, gat_segs, locals_, labels = [], [], [], [], []
        for r in range(TP):
            lo = r * PER_RANK
            pos = np.arange(lo, lo + PER_RANK)
            keep = cand[lo:lo + PER_RANK]
            bits_m = np.where(keep, bf16_bits(np.where(keep, s[lo:lo + PER_RANK], 0.0)), NINF).astype(np.int64)
            cuts = [q * PER_STACK for q in range(STACKS + 1)]
            exps, lsel = expect(bits_m, pos, cuts, K)
            locals_.append(lsel)
            # drop-stage input: every position, keep mask, adversarial values in masked lanes
            beats_md, beats_dense, beats_g = [], [], []
            for q in range(STACKS):
                bq, bd = [], []
                for g0 in range(cuts[q], cuts[q + 1], W):
                    kp = keep[g0:g0 + W]
                    lanes = [(int(bits_m[i]) if kp[i - g0] else adv, int(pos[i])) for i in range(g0, g0 + W)]
                    km = int(sum(1 << t for t in range(W) if kp[t]))
                    bq.append(((1 << W) - 1, km, lanes))
                    if km:
                        bd.append([(int(bits_m[i]), int(pos[i])) if kp[i - g0] else None for i in range(g0, g0 + W)])
                if not bd:
                    bd.append([None] * W)
                beats_md.append(bq)
                beats_dense.append(bd)
                idx = np.nonzero(keep[cuts[q]:cuts[q + 1]])[0] + cuts[q]
                beats_g.append(S.to_beats(rng, bits_m[idx], pos[idx], W, True))     # 2 blocks = 16 keys a beat
            md_segs.append((beats_md, K, exps))
            dense_segs.append((beats_dense, K, exps, {"n": int(keep.sum())}))
            gat_segs.append((beats_g, K, exps, {"n": int(keep.sum())}))
            labels.append(f"L{L}_rank{r}")
        res = dict(layer=L, candidates_per_rank=[int(cand[r * PER_RANK:(r + 1) * PER_RANK].sum()) for r in range(TP)],
                   masked_lane_value_bits=hex(adv))
        # (1) drop stage + select on the full stream, MDROP=1
        if 1 not in bins:
            bins[1] = md_build(out / "obj_md1", 1)
        pfx, vsha = write_mdrop_vectors(md_segs, out, f"L{L}_mdrop")
        r1 = md_run(bins[1], pfx, labels)
        res["mdrop"] = dict(pass_=r1["pass"], vectors_sha256=vsha, short=r1["short"], errors=r1.get("errors"),
                            per_segment=r1.get("per_segment"), ovf_segments=r1.get("ovf_segments"),
                            post_stream_cycles=seg_cost(r1, False) if r1["pass"] else None)
        # (1b) default-off check: the same bench at MDROP=0 (masked lanes forwarded as -inf) on rank 0
        if L == 24 and not a.skip_off:
            if 0 not in bins:
                bins[0] = md_build(out / "obj_md0", 0)
            pfx0, vsha0 = write_mdrop_vectors(md_segs[:1], out, f"L{L}_mdrop_off")
            r0 = md_run(bins[0], pfx0, labels[:1])
            res["mdrop_off_rank0"] = dict(pass_=r0["pass"], vectors_sha256=vsha0, per_segment=r0.get("per_segment"),
                                          ovf_segments=r0.get("ovf_segments"))
        # (2) post-drop beats back to back, (3) gather order, then the cross-die final
        for tag, segs in (("drop_dense", dense_segs), ("gather", gat_segs)):
            cfg = S.run_config(f"L{L}_{tag}", STACKS, W, IW, K, 8, segs, labels, out, runs=((0, 0, 1),))
            res[tag] = dict(pass_=cfg["pass"], beats=cfg["beats"], elements=cfg["elements"],
                            runs=[{k: v for k, v in rr.items() if k != "log"} for rr in cfg["runs"]],
                            cost_cycles_convention=seg_cost(cfg["runs"][0]) if cfg["pass"] else None)
        cb = np.concatenate([np.where(cand[np.asarray(x)], bf16_bits(s[np.asarray(x)]), NINF) for x in locals_])
        cp = np.concatenate([np.asarray(x) for x in locals_])
        cuts = np.cumsum([0] + [len(x) for x in locals_]).tolist()
        segx, gsel = M._segment(S, G, cb, cp, cuts, K, W)
        cfgx = S.run_config(f"L{L}_final", STACKS, W, IW, K, 6, [segx], [f"L{L}_final"], out, runs=((0, 0, 1),))
        res["final"] = dict(pass_=cfgx["pass"], runs=[{k: v for k, v in rr.items() if k != "log"} for rr in cfgx["runs"]])
        res["global_selection_equals_golden_layer"] = sorted(gsel) == golden_sel
        res["golden_selection_sha256"] = hashlib.sha256(json.dumps(golden_sel).encode()).hexdigest()
        res["pass_"] = (res["mdrop"]["pass_"] and res["drop_dense"]["pass_"] and res["gather"]["pass_"]
                        and res["final"]["pass_"] and res["global_selection_equals_golden_layer"]
                        and res.get("mdrop_off_rank0", {"pass_": True})["pass_"])
        results[f"L{L}"] = res
        print(f"L{L}", json.dumps({k: (v.get("pass_") if isinstance(v, dict) else v) for k, v in res.items()}), flush=True)
        print(f"L{L} mdrop post-stream {res['mdrop']['post_stream_cycles']} dense {res['drop_dense']['cost_cycles_convention']} "
              f"gather {res['gather']['cost_cycles_convention']}", flush=True)
    srcs = {p: sha(ROOT / p) for p in MD_SRC + [str(S.TB.relative_to(ROOT)), str(S.HARNESS.relative_to(ROOT)),
                                                 "tools/rtl_hdc_v41x_sel_campaign.py", "tools/hdc_golden_v41.py",
                                                 "tools/dsrom_1m_measure.py", "tools/dsrom_reindex_candidates.py"]}
    pins = {f"L{L}": dict(npz=sha(a.gold / f"ctx1048576_L{L:02d}.npz"), json=sha(a.gold / f"ctx1048576_L{L:02d}.json"))
            for L in [int(x) for x in a.layers.split(",")]}
    pins["cand"] = sha(a.gold / "ctx1048576_cand.npz")
    ver = subprocess.run([verilator(), "--version"], capture_output=True, text=True).stdout.strip()
    rec = dict(schema="opentallas.dsrom-reindex.select.v1", simulator=ver, source_sha256=srcs, golden_shards=pins,
               layers=results, status="pass" if all(r["pass_"] for r in results.values()) else "fail")
    (out / "select.json").write_text(json.dumps(rec, indent=1) + "\n")


def cmd_screen(a):
    rows = {}
    for w in a.work:
        w = Path(w)
        rows[w.name] = json.loads((w / "screen.json").read_text())
    srcs = {p: sha(ROOT / p) for p in ("rtl/hdc/v41x/ot_hdc_v41x_idx_kgather.sv", "rtl/hdc/v41x/ot_hdc_v41x_sel_mdrop.sv",
                                        "tools/dsrom_reindex_screen.py")}
    ok = all(r["ss_setup_wns_ps"] is not None and r["ss_setup_wns_ps"] >= 0 and r["ff_hold_wns_ps"] is not None
             and r["ff_hold_wns_ps"] >= 0 for r in rows.values())
    rec = dict(schema="opentallas.dsrom-reindex.screen.v1", period_ps=833.0, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
               basis="pre-layout: ORFS yosys/abc at CORNER=WC (ADDER_MAP_FILE off), OpenSTA ASAP7 RVT SS (setup) and FF "
                     "(hold) libs, ideal clock, inputs/outputs false-pathed; SRAM banks (list, reorder data) outside the "
                     "screened control as in ot_hdc_v41x_idx_kctl",
               source_sha256=srcs, runs=rows, status="pass" if ok else "fail")
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: (v["ss_setup_wns_ps"], v["ff_hold_wns_ps"]) for k, v in rows.items()}), rec["status"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gather")
    g.add_argument("--out", type=Path, required=True)
    g.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    s = sub.add_parser("select")
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--gold", type=Path, default=GOLD_DEFAULT)
    s.add_argument("--layers", default="24,28")
    s.add_argument("--skip-off", action="store_true")
    c = sub.add_parser("screen")
    c.add_argument("--work", nargs="+", required=True)
    c.add_argument("--out", required=True)
    a = ap.parse_args()
    dict(gather=cmd_gather, select=cmd_select, screen=cmd_screen)[a.cmd](a)


if __name__ == "__main__":
    main()
