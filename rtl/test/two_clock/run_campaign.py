#!/usr/bin/env python3
"""Dual-clock Verilator campaign of ot_ratio_cdc_fifo: build, run every direction x mode x seed, record.

    python3 rtl/test/two_clock/run_campaign.py --workdir SCRATCH --output R.json [--words N] [--seeds K] [--jobs J]

Modes (rtl/test/two_clock/tb_ratio_cdc_fifo.cpp): sparse (one word in flight, latency per phase), saturate
(throughput), random (60%/60% stalls both sides), backpressure (long reader stall bursts, bursty writer),
reset (random 1-5 cycle resets of either side in flight with 70%/70% stalls).  The mutation set re-builds the RTL
with one protocol rule removed and requires the scoreboard to FAIL (the bench can see the faults it claims to).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RTL = ROOT / "rtl/common/ot_ratio_cdc_fifo.sv"
TB = ROOT / "rtl/test/two_clock/tb_ratio_cdc_fifo.cpp"
BUILD = ROOT / "rtl/test/two_clock/build_tb.sh"
RES = re.compile(r"RESULT (.*) errors=(\d+) (PASS|FAIL)")
MUTANTS = {   # name: [(old, new), ...] -- each must make the reset or ordering checks fail
    "no_reader_peer_gate": [("assign r_live = (r_st == S_RUN) && (w_st_r != S_DOWN);", "assign r_live = (r_st == S_RUN);")],
    "no_wrst_accept_gate": [("assign w_rdy  = wrst_n && w_live", "assign w_rdy  = w_live")],
    "no_hold_no_seen_rule": [("if (w_cnt != '0) w_cnt <= w_cnt - 1'b1;", "if (1'b0) w_cnt <= w_cnt - 1'b1;"),
                             ("else if (w_ok || r_st_w != S_RUN) w_st <= S_WAIT;", "else w_st <= S_WAIT;"),
                             ("if (r_cnt != '0) r_cnt <= r_cnt - 1'b1;", "if (1'b0) r_cnt <= r_cnt - 1'b1;"),
                             ("else if (r_ok || w_st_r != S_RUN) r_st <= S_WAIT;", "else r_st <= S_WAIT;")],
    "no_hold_keep_seen_rule": [("if (w_cnt != '0) w_cnt <= w_cnt - 1'b1;", "if (1'b0) w_cnt <= w_cnt - 1'b1;"),
                               ("if (r_cnt != '0) r_cnt <= r_cnt - 1'b1;", "if (1'b0) r_cnt <= r_cnt - 1'b1;")],
    "wrong_slot_read": [("assign r_d    = sh[rp[AW-1:0]];", "assign r_d    = sh[rp[AW-1:0]+1'b1];")],
    "wait_ignores_peer": [("if (w_st_r != S_DOWN) r_st <= S_RUN;", "r_st <= S_RUN;")],
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(out: Path, depth: int, rtl: Path | None = None) -> Path:
    env = None
    if rtl is not None:
        import os
        env = dict(os.environ, RTL=str(rtl))
    subprocess.run(["bash", str(BUILD), str(out), "64", str(depth), "2"], check=True, env=env,
                   capture_output=True, text=True)
    return out / "tb"


def run(exe: Path, **kw) -> dict:
    argv = [str(exe)] + [f"+{k}={v}" for k, v in kw.items()]
    p = subprocess.run(argv, capture_output=True, text=True)
    m = RES.search(p.stdout)
    rec = dict(argv=argv[1:], returncode=p.returncode, verdict=m.group(3) if m else "NO_RESULT",
               errors=int(m.group(2)) if m else None, stdout_tail=p.stdout[-1500:])
    if m:
        for tok in m.group(1).split():
            k, _, v = tok.partition("=")
            rec[k] = v
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--words", type=int, default=2_000_000)
    ap.add_argument("--seeds", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args(argv)
    a.workdir.mkdir(parents=True, exist_ok=True)
    exes = {d: build(a.workdir / f"obj_d{d}", d) for d in (2, 4, 8)}
    tasks = []
    for d, exe in exes.items():
        for direction in ("f2s", "s2f"):
            for mode in ("sparse", "saturate", "random", "backpressure", "reset"):
                seeds = range(1, a.seeds + 1) if d == 4 else range(1, 2)
                for s in seeds:
                    tasks.append((f"DEPTH{d}", exe, dict(dir=direction, mode=mode, words=a.words, seed=s, phase=s % 4)))
    mut_tasks = []
    for name, edits in MUTANTS.items():
        src = RTL.read_text()
        for old, new in edits:
            assert old in src, (name, old)
            src = src.replace(old, new, 1)
        mp = a.workdir / f"mut_{name}.sv"
        mp.write_text(src)
        exe = build(a.workdir / f"obj_mut_{name}", 4, mp)
        for direction in ("f2s", "s2f"):
            for s in (5, 6, 7):
                mut_tasks.append((name, exe, dict(dir=direction, mode="reset", words=50000, seed=s)))
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = list(ex.map(lambda t: (t[0], run(t[1], **t[2])), tasks))
        mres = list(ex.map(lambda t: (t[0], run(t[1], **t[2])), mut_tasks))
    runs = [dict(config=c, **r) for c, r in res]
    mutants = {}
    for c, r in mres:
        mutants.setdefault(c, []).append(dict(argv=r["argv"], verdict=r["verdict"], errors=r["errors"]))
    mut_ok = {k: any(x["verdict"] == "FAIL" for x in v) for k, v in mutants.items()}
    rec = dict(schema="opentallas.two_clock_crossing_bench.v1",
               simulator=subprocess.run(["verilator", "--version"], capture_output=True, text=True).stdout.strip(),
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (RTL, TB, BUILD, Path(__file__))},
               words_per_run=a.words, runs=runs, mutants=mutants, mutant_detected=mut_ok,
               all_runs_pass=all(r["verdict"] == "PASS" for r in runs),
               all_mutants_detected=all(mut_ok.values()),
               total_words=sum(int(r.get("accepted", 0)) for r in runs))
    summ = {}
    for r in runs:
        key = f'{r["config"]} {r.get("dir")} {r.get("mode")}'
        s = summ.setdefault(key, dict(runs=0, pass_=0, words=0, flushed=0, resets=0))
        s["runs"] += 1; s["pass_"] += r["verdict"] == "PASS"; s["words"] += int(r.get("accepted", 0))
        s["flushed"] += int(r.get("flushed", 0)); s["resets"] += int(r.get("resets_w", 0)) + int(r.get("resets_r", 0))
        for k in ("lat_ps", "lat_dst_cycles", "lat_ticks", "words_per_ns"):
            if k in r:
                s.setdefault(k, []).append(r[k])
    rec["summary"] = summ
    rec["verdict"] = "PASS" if rec["all_runs_pass"] and rec["all_mutants_detected"] else "FAIL"
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["verdict"], "runs", len(runs), "words", rec["total_words"], "mutants", mut_ok)


if __name__ == "__main__":
    main()
