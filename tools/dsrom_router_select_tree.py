#!/usr/bin/env python3
"""DS-ROM recovery lever "router": the parallel router top-6 (rtl/hdc/v41/ot_hdc_select_tree.sv) on the 1M token.

    python3 tools/dsrom_router_select_tree.py sim --gold <dir of ctx1048576_LXX.{npz,json}> --work <dir> --out <json>
    python3 tools/dsrom_router_select_tree.py lever --sim <json> --screen <screen.json> --out <lever json>

sim: Verilator (and Icarus, 4-state) runs of ot_hdc_select_tree (K 6, FP32, IW 9, W 64 lanes, NB 8 beats) on
  * the golden's biased router scores (scores + bias, FP32) of EVERY layer of the 1M token (position 1,048,575):
    384 scores = 6 beats of 64 lanes in expert-id order; the expected selection is topk_lowest_index of the
    golden (tools/hdc_golden_v41.py) and must equal the golden's recorded experts of that layer;
    one single-segment run per layer (its first-accept -> result edges are the cycle record) and one run of all
    layers back to back;
  * random tie-heavy segments (the select campaign's value alphabets: +-0, +-inf, subnormals, all-equal, raw
    bit patterns), 1..512 elements over 1..8 beats with random lane masks and unique random indices,
    in ascending-index (ORDER 1) and rank (ORDER 0) form, back to back and with random bubbles.
lever: writes the opentallas.dsrom-recovery.lever.v1 record that tools/dsrom_1m_allmeasured.py applies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402
import rtl_hdc_v41_select_campaign as SC  # noqa: E402

RTL = ROOT / "rtl/hdc/v41/ot_hdc_select_tree.sv"
TB = ROOT / "rtl/test/tb_hdc_select_tree.sv"
HARNESS = ROOT / "rtl/test/hdc_select_tree_harness.cpp"
CTX = 1048576
K, VW, IW, W, NB = 6, 32, 9, 64, 8
FAST_HZ = 1.2e9
LINE = re.compile(r"SELTREE K=(\d+) VW=(\d+) IW=(\d+) W=(\d+) NB=(\d+) ORDER=(\d+) segments=(\d+) beats=(\d+) "
                  r"results=(\d+) errors=(\d+) lat_min=(-?\d+) lat_max=(-?\d+) lat_expect=(\d+) span0=(-?\d+) "
                  r"cycles=(\d+)")
KEYS = ("K", "VW", "IW", "W", "NB", "ORDER", "segments", "beats", "results", "errors", "lat_min", "lat_max",
        "lat_expect", "span0", "cycles")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_head():
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or None


def parse(out: str):
    m = LINE.search(out)
    if not m:
        return {"pass": False, "raw": out[-2000:]}
    r = {k: int(v) for k, v in zip(KEYS, m.groups())}
    r["pass"] = "PASS" in out[m.end():]
    return r


def write_vectors(segs, order, path_in: Path, path_exp: Path):
    """segs: (vals float64, labels, placement [(beat, lane)] per element, beats).  The expected selection is the
    golden's topk_lowest_index over the array indexed by label (ties to the lower label)."""
    li, le = [], []
    for vals, labels, place, beats in segs:
        bits = SC.fbits(vals, VW)
        grid = {(b, l): (int(x), int(lab)) for (b, l), x, lab in zip(place, bits, labels)}
        for b in range(beats):
            li.append(f"B {int(b == beats - 1)}\n")
            for l in range(W):
                x, lab = grid.get((b, l), (0, 0))
                li.append(f"{x:x} {lab:x} {int((b, l) in grid)}\n")
        exp = SC.expected(vals, labels, K, order)
        le.append(f"S {len(exp)}\n")
        le += [f"{i:x} {int(n)}\n" for i, n in exp]
    path_in.write_text("".join(li))
    path_exp.write_text("".join(le))
    return hashlib.sha256(path_in.read_bytes() + path_exp.read_bytes()).hexdigest()


def router_seg(v):
    n = len(v)
    return (v, np.arange(n), [(i // W, i % W) for i in range(n)], -(-n // W))


def random_segs(rng, nseg):
    segs = []
    for _ in range(nseg):
        r = rng.random()
        n = int(rng.integers(1, K + 3) if r < 0.25 else rng.integers(1, W * NB + 1) if r < 0.6 else
                rng.integers(300, W * NB + 1))
        beats = int(rng.integers(-(-n // W), NB + 1))
        slots = rng.choice(beats * W, n, replace=False)
        if rng.random() < 0.4:
            slots = np.sort(slots)
        place = [(int(s) // W, int(s) % W) for s in slots]
        vals = SC.random_values(rng, n, VW)
        labels = np.arange(n) if rng.random() < 0.4 else rng.choice(1 << IW, n, replace=False)
        segs.append((vals, labels, place, beats))
    return segs


def cmd_sim(a):
    gold, work, out = Path(a.gold), Path(a.work), Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    vl = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
    verilator = str(vl) if vl.exists() else "verilator"
    exes = {}
    for order in (1, 0):
        obj = work / f"obj_o{order}"
        if not (obj / "Vtb_hdc_select_tree").exists():
            subprocess.run([verilator, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "--top-module",
                            "tb_hdc_select_tree", f"-GK={K}", f"-GVW={VW}", f"-GIW={IW}", f"-GW={W}", f"-GNB={NB}",
                            f"-GORDER={order}", "-Mdir", str(obj), str(RTL), str(TB), str(HARNESS), "-CFLAGS", "-O1"],
                           check=True)
        exes[order] = obj / "Vtb_hdc_select_tree"
    ivl = work / "tb_icarus.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(ivl), "-s", "tb_hdc_select_tree", f"-Ptb_hdc_select_tree.K={K}",
                    f"-Ptb_hdc_select_tree.VW={VW}", f"-Ptb_hdc_select_tree.IW={IW}", f"-Ptb_hdc_select_tree.W={W}",
                    f"-Ptb_hdc_select_tree.NB={NB}", "-Ptb_hdc_select_tree.ORDER=1", str(RTL), str(TB)], check=True)

    def run(order, fin, fexp, bubble=0, seed=1, icarus=False):
        cmd = (["vvp", "-n", str(ivl)] if icarus else [str(exes[order])]) + \
              [f"+IN={fin}", f"+EXP={fexp}", f"+BUBBLE={bubble}", f"+SEED={seed}"]
        return parse(subprocess.run(cmd, capture_output=True, text=True).stdout)

    layers, all_segs = [], []
    for jf in sorted(gold.glob(f"ctx{CTX}_L[0-9][0-9].json")):
        L = int(jf.stem.split("_L")[1])
        js = json.loads(jf.read_text())
        z = np.load(gold / f"ctx{CTX}_L{L:02d}.npz")
        v = np.asarray(z[f"L{L}.router"], np.float32).astype(np.float64)
        ids = sorted(int(i) for i in V.topk_lowest_index(v, K))
        assert ids == js["experts"], (L, ids, js["experts"])
        seg = router_seg(v)
        all_segs.append(seg)
        tag = f"L{L:02d}"
        h = write_vectors([seg], 1, work / f"{tag}.in", work / f"{tag}.exp")
        r = run(1, work / f"{tag}.in", work / f"{tag}.exp")
        layers.append(dict(layer=f"L{L}", kind=js.get("kind"), golden_experts=js["experts"], scores=len(v),
                           beats=seg[3], vectors_sha256=h, npz_sha256=sha(gold / f"ctx{CTX}_L{L:02d}.npz"),
                           first_accept_to_result_cycles=r.get("span0"), latency=r.get("lat_max"),
                           errors=r.get("errors"), **{"pass": r.get("pass")}))
        print(tag, layers[-1], flush=True)
    runs = {}
    h = write_vectors(all_segs, 1, work / "all.in", work / "all.exp")
    runs["real_all_layers_back_to_back"] = dict(vectors_sha256=h, **run(1, work / "all.in", work / "all.exp"))
    runs["real_all_layers_bubbles30"] = dict(vectors_sha256=h, **run(1, work / "all.in", work / "all.exp", 30, 7))
    runs["real_all_layers_icarus"] = dict(vectors_sha256=h, **run(1, work / "all.in", work / "all.exp", icarus=True))
    write_vectors(all_segs, 0, work / "all_rank.in", work / "all_rank.exp")
    runs["real_all_layers_rank_order"] = dict(**run(0, work / "all_rank.in", work / "all_rank.exp"))
    rng = np.random.default_rng(20261004)
    rs = random_segs(rng, a.random)
    for order in (1, 0):
        h = write_vectors(rs, order, work / f"rnd_o{order}.in", work / f"rnd_o{order}.exp")
        runs[f"random_order{order}"] = dict(vectors_sha256=h, **run(order, work / f"rnd_o{order}.in",
                                                                     work / f"rnd_o{order}.exp"))
        runs[f"random_order{order}_bubbles30"] = dict(vectors_sha256=h, **run(order, work / f"rnd_o{order}.in",
                                                                               work / f"rnd_o{order}.exp", 30, 3))
    for k, r in runs.items():
        print(k, r, flush=True)
    cyc = sorted({x["first_accept_to_result_cycles"] for x in layers})
    ok = all(x["pass"] for x in layers) and all(r.get("pass") for r in runs.values())
    res = dict(schema="opentallas.dsrom-recovery.router-select-tree.v1", generated_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               source_commit=git_head(), status="pass" if ok else "fail",
               unit=dict(module="ot_hdc_select_tree", params=dict(K=K, VW=VW, IW=IW, W=W, NB=NB, ORDER=1),
                         clock_hz=FAST_HZ, clock_domain="streaming 1.2 GHz (as ot_hdc_select)",
                         input="384 biased router scores (FP32) as 6 beats of 64 lanes, expert-id order",
                         output="the 6 expert ids in ascending order, one beat"),
               measure="first beat accepted -> result registered (edges), = beats - 1 + LAT + 1, the as-built "
                       "record's first accept -> last output beat",
               cycles=cyc, us=[round(c / FAST_HZ * 1e6, 5) for c in cyc],
               simulator=subprocess.run([verilator, "--version"], capture_output=True, text=True).stdout.strip(),
               icarus=subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0],
               context=CTX, position=CTX - 1, layers=layers, runs=runs, random_segments=a.random,
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in
                              (RTL, TB, HARNESS, Path(__file__), ROOT / "tools/hdc_golden_v41.py",
                               ROOT / "tools/rtl_hdc_v41_select_campaign.py")})
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1) + "\n")
    print("SELTREE", res["status"], cyc)
    return 0 if ok else 1


def cmd_lever(a):
    sim = json.loads(Path(a.sim).read_text())
    scr = json.loads(Path(a.screen).read_text())
    asb = json.loads((ROOT / "results/rtl/dsrom_1m_allmeasured_20261004/su.json").read_text())["node_us"]
    cyc = max(sim["cycles"])
    us = cyc / FAST_HZ * 1e6
    old = asb["ffn.top6_order"]["us"]
    ss, ff = scr["ss_setup_wns_ps"], scr["ff_hold_wns_ps"]
    closes = ss is not None and ff is not None and ss >= 0 and ff >= 0
    exact = sim["status"] == "pass"
    src = (f"ot_hdc_select_tree (64 lanes x 6 beats, sort-8 leaves + top-8 merge trees + ascending-id sort) "
           f"{cyc} cycles at 1.2 GHz first score beat -> 6 ids, exact on all {len(sim['layers'])} layers' golden "
           f"1M router scores ({Path(a.sim).name})")
    rec = dict(schema="opentallas.dsrom-recovery.lever.v1", lever="router",
               verdict=a.verdict or ("ADOPT" if exact and closes else "REJECT"), exact=exact,
               ss_ff=dict(period_ps=scr["period_ps"], ss_setup_wns_ps=ss, ff_hold_wns_ps=ff, closes=closes,
                          cell_area_um2=scr.get("cell_area_um2"), ss_fmax_prelayout_hz=scr.get("ss_fmax_prelayout_hz"),
                          worst_start=scr.get("worst_start"), worst_end=scr.get("worst_end"),
                          basis=scr.get("basis"), record=a.screen_record or a.screen),
               nodes={"*.ffn.top6": dict(us=0.0, source="covered by ffn.top6_order (one ot_hdc_select_tree pass "
                                                        "selects and orders)", cls="measured"),
                      "*.ffn.top6_order": dict(us=round(us, 5), source=src, cls="measured")},
               measurement=dict(old=dict(unit="one ot_hdc_select (K 6, 1 score/cycle)", cycles=round(old * 1.2e3),
                                         us=old, record="results/rtl/dsrom_1m_allmeasured_20261004/su_runs/select.json"),
                                new=dict(unit="ot_hdc_select_tree K 6 W 64 NB 8 ORDER 1", cycles=cyc, us=round(us, 5),
                                         latency_after_last_beat=sim["layers"][0]["latency"], beats=6,
                                         record=a.sim_record or a.sim),
                                layers_exact=sum(x["pass"] for x in sim["layers"]), layers=len(sim["layers"]),
                                random_segments=sim["random_segments"],
                                saving_us_per_layer=round(old - us, 5)),
               default="opt-in: applied only in the recovery baseline; the as-built ot_hdc_select is unchanged")
    if a.note:
        rec["note"] = a.note
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("sim")
    s.add_argument("--gold", required=True)
    s.add_argument("--work", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--random", type=int, default=4000)
    s = sp.add_parser("lever")
    s.add_argument("--sim", required=True)
    s.add_argument("--screen", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--sim-record")
    s.add_argument("--screen-record")
    s.add_argument("--verdict")
    s.add_argument("--note")
    a = ap.parse_args(argv)
    return dict(sim=cmd_sim, lever=cmd_lever)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
