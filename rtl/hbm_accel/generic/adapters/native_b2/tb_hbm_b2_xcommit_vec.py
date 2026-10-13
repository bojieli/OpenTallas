#!/usr/bin/env python3
"""Stimulus / golden / verdict for tb_hbm_b2_xcommit (the x-store commit tracker gated with the real native SM).

Ops, lines, x fragments and the golden come from tools/dshbm_sm_pq_seq.py / tools/dshbm_matched_sm_seq.py (gen_op, same
seed, same compare as cmd_run): this script only chooses the op list and the production-shaped x-beat bursts.

  gen   --dir D            write seq.hex lines.hex x.hex xc.hex gold.json
  check --dir D --sel N    compare out.txt with the golden and the commit criteria; exit 0 only if everything holds
"""
import argparse, json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[5]
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
sys.path.insert(0, str(ROOT / "tools"))
NC, ACTIVE, XDEPTH, NW, D = 8, 8, 128, 10, 27
# (tag, fmt, K, R, load, burst beats (0 = one burst), gap between bursts, release delay, idle gap before, claim)
OPS = [("warm bf16 K5120 R1 (G10): 1040 beats, one burst, tiles asleep", "bf16", 5120, 1, 1, 0, 0, 0, 150, 0),
       ("fp8 K512 R1 (G1): one burst of 104", "fp8", 512, 1, 1, 0, 0, 0, 0, 0),
       ("fp4 K2304 R2 (G2): bursts of 26, gap 1", "fp4", 2304, 2, 1, 26, 1, 0, 0, 0),
       ("bf16 K512 R32 (G1): bursts of 13, gap 5, release 60 late", "bf16", 512, 32, 1, 13, 5, 60, 0, 0),
       ("fp8 K1280 R16 (G2): bursts of 26, gap 30, tiles asleep", "fp8", 1280, 16, 1, 26, 30, 0, 200, 0),
       ("fp8 K1280 R2 resident x (no load, claims committed)", "fp8", 1280, 2, 0, 0, 0, 0, 0, 1),
       ("bf16 K5120 R1 (G10): one burst of 1040, ring wrap onto stale x", "bf16", 5120, 1, 1, 0, 0, 0, 0, 0),
       ("fp8 K2304 R2 (G3): bursts of 104, gap 2, release 3 late", "fp8", 2304, 2, 1, 104, 2, 3, 0, 0),
       # priced shapes: the full x store (128 addresses x 13 beats = 1,664 beats) in the two production row bursts
       ("PRICE fp8 K16384 R1 (G16): 1,664 beats, row bursts of 26 (FP8), gap 1", "fp8", 16384, 1, 1, 26, 1, 0, 0, 0),
       ("PRICE bf16 K8192 R1 (G16): 1,664 beats, row bursts of 104 (BF16), gap 1", "bf16", 8192, 1, 1, 104, 1, 0, 0, 0),
       ("PRICE bf16 K8192 R1 (G16): 1,664 beats, one burst", "bf16", 8192, 1, 1, 0, 0, 0, 0, 0)]


def build():
    import numpy as np
    import dshbm_matched_sm_seq as MS
    import hdc_golden as G
    import hdc_golden_v41 as V2
    V2.set_arith("chunk8")
    rng = np.random.default_rng(20261013)
    fw = (NC * MS.XC + 2048 + 3) // 4
    seq, lines, xw, xc, gold, meta = [], [], [], [], [], []
    resident, rbase, ptr = None, 0, 0
    for tag, fmt, K, R, load, bl, gap, rel, idle, claim in OPS:
        if load:
            g = MS.gen_op("v41_" + fmt, R, K, NC, rng)
            resident = g
            rbase, ptr = ptr, (ptr + g["Gn"] * g["c"]) % XDEPTH
        else:
            g = MS.gen_op("v41_" + fmt, R, K, NC, rng, X=resident["X"])
            assert g["Gn"] == resident["Gn"]
        seq += [R, g["c"], g["Gn"], g["fmt"], len(g["lines"]), 1, load, g["Gn"] * g["c"], 1, rbase]
        lines += [f"{w:0272x}" for w in g["lines"]]
        if load:
            assert all(w >> (NC * MS.XC) == 0 for w in g["xw"])
            xw += [f"{w:0{fw}x}" for w in g["xw"]]
        xc += [bl, gap, rel, idle, claim]
        gold.append([[int(G.bits(g["gold"][n][r])) for r in range(R)] for n in range(ACTIVE)])
        meta.append(dict(tag=tag, fmt=fmt, K=K, rows=R, load=load, groups=g["Gn"], x_addresses=g["Gn"] * g["c"],
                         x_base=rbase, beats=13 * g["Gn"] * g["c"] if load else 0, burst=bl, gap=gap, release_delay=rel,
                         idle_gap=idle, claim=claim, lines=len(g["lines"])))
    return seq, lines, xw, xc, gold, meta


def cmd_gen(a):
    d = Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    seq, lines, xw, xc, gold, meta = build()
    (d / "seq.hex").write_text("\n".join(f"{v:08x}" for v in seq) + "\n")
    (d / "lines.hex").write_text("\n".join(lines) + "\n")
    (d / "x.hex").write_text("\n".join(xw) + "\n")
    (d / "xc.hex").write_text("\n".join(f"{v:08x}" for v in xc) + "\n")
    (d / "gold.json").write_text(json.dumps(dict(gold=gold, ops=meta)) + "\n")
    print("NOPS", len(meta))


def cmd_check(a):
    d = Path(a.dir)
    j = json.loads((d / "gold.json").read_text())
    gold, ops = j["gold"], j["ops"]
    res, meta, xcop, sram, xs, timeout, total = {}, {}, {}, [], None, None, None
    for line in (d / "out.txt").read_text().splitlines():
        t = line.split()
        if line.startswith("# op"):
            meta[int(t[2])] = {t[k]: int(t[k + 1]) for k in range(3, len(t) - 1, 2)}
        elif line.startswith("# xc op"):
            xcop[int(t[3])] = {t[k]: int(t[k + 1]) for k in range(4, len(t) - 1, 2)}
        elif line.startswith("# sram"):
            sram.append({t[k]: int(t[k + 1]) for k in range(3, len(t) - 1, 2)})
        elif line.startswith("# xcsum"):
            xs = {t[k]: int(t[k + 1]) for k in range(2, len(t) - 1, 2)}
        elif line.startswith("# total_cycles"):
            total = int(t[-1])
        elif line.startswith("#"):
            timeout = line[2:]
        else:
            res.setdefault(int(t[0]), {})[int(t[1])] = t[2]
    rows, bad_ops, fails = [], 0, []
    for i, o in enumerate(ops):
        got, mism = res.get(i, {}), 0
        for r in range(o["rows"]):
            h = got.get(r)
            if h is None:
                mism += ACTIVE
                continue
            v = int(h, 16)
            mism += sum(1 for n in range(ACTIVE) if ((v >> (32 * n)) & 0xFFFFFFFF) != gold[i][n][r])
        m, x = meta.get(i, {}), xcop.get(i, {})
        exact = mism == 0 and len(got) == o["rows"] and m.get("fault", 1) == 0 and m.get("consumed") == m.get("lines") \
            and m.get("results") == o["rows"]
        bad_ops += 0 if exact else 1
        row = dict(op=i, **o, golden_mismatches=mism, results=len(got), exact=exact, rtl=m, commit=x)
        if x and o["load"]:
            row["commit_latency_edges"] = x["wr_last"] - x["e0_last"]            # last SRAM write edge after the last beat
            row["start_after_last_beat_edges"] = x["t_start"] - x["e0_last"]
            row["start_after_last_ack_edges"] = x["t_start"] - x["e_ack"]
            row["start_after_release_edges"] = x["t_start"] - x["e_rel"]
            row["first_read_after_start_edges"] = x["rd_first"] - x["t_start"]
            row["load_edges_first_tap_to_last_ack"] = x["e_ack"] - x["e_tap0"] + 1
            row["drain_added_ratio"] = round(row["start_after_last_ack_edges"] / row["load_edges_first_tap_to_last_ack"], 6)
            row["x_bound"] = o["release_delay"] == 0
        rows.append(row)
    if timeout:
        fails.append("timeout: " + timeout)
    if bad_ops:
        fails.append(f"golden: {bad_ops} op(s) not exact")
    if xs is None:
        fails.append("no summary line")
    else:
        for k in ("rb_bad", "stale", "write_while_drained", "write_gated", "beat_while_drained", "trk_fault", "sink_fault",
                  "sm_fault", "cal_nonuniform"):
            if xs[k]:
                fails.append(f"{k} = {xs[k]}")
        if xs["cal_lat_max"] != D:
            fails.append(f"measured commit depth {xs['cal_lat_max']} != D {D}")
        if xs["sink_acks"] != xs["beats"]:
            fails.append("sink ACK count != beats sampled")
    for r in rows:
        if r["load"] and r.get("commit"):
            if r["commit_latency_edges"] != D:
                fails.append(f"op {r['op']}: stream commit latency {r['commit_latency_edges']} != D")
            if a.sel == 0 and r["x_bound"] and r["start_after_last_beat_edges"] != D + 1:
                fails.append(f"op {r['op']}: start {r['start_after_last_beat_edges']} edges after the last beat, not D + 1")
            if a.sel == 0 and not r["x_bound"] and r["start_after_release_edges"] != 2:
                fails.append(f"op {r['op']}: start {r['start_after_release_edges']} edges after the release, not 2")
    # per branch (hop, tile row): calibrated write latency, first read after start, read-after-write slack
    br = {}
    for s in sram:
        hop = (4 - s["c"]) if s["c"] < 4 else (s["c"] - 3)
        k = f"hop{hop}_tilerow{s['p']}"
        b = br.setdefault(k, dict(write_latency_edges=set(), first_read_after_start_min=1 << 30, read_after_write_slack_min=1 << 30, macros=0))
        b["macros"] += 1
        b["write_latency_edges"].add(s["lat_max"])
        b["first_read_after_start_min"] = min(b["first_read_after_start_min"], s["rmin"])
        b["read_after_write_slack_min"] = min(b["read_after_write_slack_min"], s["smin"])
    for b in br.values():
        b["write_latency_edges"] = sorted(b["write_latency_edges"])
    out = dict(schema="opentallas.hbm_b2.xcommit_gate.v1", sel_mut=a.sel, D=D, status="pass" if not fails else "fail",
               fails=fails, mismatching_ops=bad_ops, total_cycles=total, summary=xs, branches=dict(sorted(br.items())),
               ops=rows)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(out["status"].upper(), "sel", a.sel, "; ".join(fails))
    for r in rows:
        print(f"  op {r['op']} exact {r['exact']} rb_bad {r['commit'].get('rb_bad')} start-last_beat {r.get('start_after_last_beat_edges')} "
              f"start-last_ack {r.get('start_after_last_ack_edges')} load {r.get('load_edges_first_tap_to_last_ack')} ratio {r.get('drain_added_ratio')} "
              f"commit {r.get('commit_latency_edges')} slack_min {r['commit'].get('slack_min')} | {r['tag']}")
    return 0 if not fails else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("gen", "check"))
    ap.add_argument("--dir", required=True)
    ap.add_argument("--sel", type=int, default=0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.step == "gen":
        cmd_gen(a)
    else:
        a.out = a.out or str(Path(a.dir) / "result.json")
        sys.exit(cmd_check(a))
