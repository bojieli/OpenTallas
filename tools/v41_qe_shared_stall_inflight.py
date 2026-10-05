#!/usr/bin/env python3
"""In-flight sweep of the shared-HBM QE weight supply (companion to tools/v41_qe_shared_stall_gate.py).

Same bench (rtl/test/tb_v41_qe_shared_stall.sv), same vectors (released L0 wq_a rank-0 rows, seeded BF16
activation, hdc_golden_v41.linear_q expected), WEIGHT_STALL = 1, 1,024-word window.  Sweeps the opt-in
in-flight knobs, whose defaults are the qualified geometry:
  LA       ot_hdc_qstream request look-ahead (words)            default 8
  W_ND     ot_chip_v41x_weight_pc_adapter burst descriptors      default 8
  W_DEPTH  adapter return sectors reserved per pseudo-channel   default 16
  W_ROOM   free sectors a pseudo-channel must show as w_room    default 16 (= DEPTH: room only when empty)
each with no K traffic and with saturating one-sector K reads on all 32 pseudo-channels.  Every output word
is compared bit for bit.  The bench also attributes every request cycle (V41QELIM): issued, adapter
back-pressure (and no free descriptor), look-ahead blocked by the 1,024-word window, or blocked because no
look-ahead word has room on all its pseudo-channels (pc_room).

    python3 tools/v41_qe_shared_stall_inflight.py [--jobs 12]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_qe_shared_stall_gate as S  # noqa: E402

OUT = ROOT / "results/rtl/v41_qe_shared_stall_inflight.json"
PRIOR = ROOT / "results/rtl/v41_qe_shared_stall.json"
WORDS, WORD_BYTES = 3840, 544
# (LA, W_ND, W_DEPTH, W_ROOM)
GRID = [(la, nd, 16, 16) for nd in (8, 16, 32, 64) for la in (8, 32, 128)]
GRID += [(la, nd, depth, 4) for depth in (64, 256) for nd in (8, 32, 64) for la in (8, 32, 128)]
GRID += [(128, 64, 1024, 4), (128, 128, 256, 4), (128, 128, 1024, 4), (128, 256, 1024, 4), (256, 256, 1024, 4)]
KCASES = (("noK", 0), ("Ksat", 1))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(d: Path, g) -> Path:
    la, nd, depth, room = g
    obj = d / f"obj_la{la}_nd{nd}_d{depth}_r{room}"
    cmd = [S.VERILATOR, "--binary", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-TIMESCALEMOD",
           "-Wno-UNOPTFLAT", "--top-module", "tb_v41_qe_shared_stall", "-GSTALL=1", "-GLWIN=10", f"-GLA={la}",
           f"-GW_ND={nd}", f"-GW_DEPTH={depth}", f"-GW_ROOM={room}", "-Mdir", str(obj),
           *map(str, S.RTL + [S.TB]), "-j", "2"]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=7200)
    if r.returncode:
        raise RuntimeError(f"build {g} failed: " + r.stderr[-2000:])
    return obj / "Vtb_v41_qe_shared_stall"


def one(d: Path, g):
    exe = build(d, g)
    out = []
    for kname, kper in KCASES:
        p = subprocess.run([str(exe), f"+KPER={kper}", "+KCRED=8", "+LEAD=1", "+RATE=0"], cwd=d,
                           capture_output=True, text=True, timeout=7200)
        m = S.LINE.search(p.stdout)
        rec = dict(la=g[0], w_nd=g[1], w_depth=g[2], w_room=g[3], k=kname, k_period=kper,
                   status=m.group(1) if m else "no_report", returncode=p.returncode)
        if m:
            rec.update({k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", m.group(2))})
        for tag, key in (("V41QELIM", "limiter"), ("V41QEHBM", "hbm")):
            mm = re.search(tag + r" (.*)", p.stdout)
            if mm:
                rec[key] = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", mm.group(1))}
        fl = re.search(r"FAULT (.*)", p.stdout)
        if fl:
            rec["fault"] = fl.group(1)
        if rec["status"] == "pass":
            rec["bytes_per_cycle_row_phase"] = round(WORDS * WORD_BYTES / rec["rows_cycles"], 2)
            rec["bytes_per_cycle_token"] = round(WORDS * WORD_BYTES / rec["end"], 2)
            lim = rec.get("limiter", {})
            if lim.get("req_cycles"):
                rec["mean_inflight_words"] = round(lim["inflight_sum"] / lim["req_cycles"], 2)
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--workdir", type=Path)
    ap.add_argument("--jobs", type=int, default=12)
    a = ap.parse_args()
    tmp = None if a.workdir else tempfile.TemporaryDirectory(prefix="v41_qe_inflight_")
    d = a.workdir or Path(tmp.name)
    d.mkdir(parents=True, exist_ok=True)
    src = S.vectors(d)
    rows = []
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        for res in ex.map(lambda g: one(d, g), GRID):
            rows += res
            for r in res:
                print(json.dumps({k: r.get(k) for k in ("la", "w_nd", "w_depth", "w_room", "k", "status", "errors",
                                                        "end", "starve", "bytes_per_cycle_row_phase")}), flush=True)
    prior = json.loads(PRIOR.read_text())
    base = {c["k_period"]: c for c in prior["cases"] if c["stall"] and c["window_words"] == 1024}
    default = {r["k_period"]: r for r in rows if (r["la"], r["w_nd"], r["w_depth"], r["w_room"]) == (8, 8, 16, 16)}
    regression = {str(k): dict(prior_end=base[k]["end"], sweep_end=default[k]["end"],
                               identical=base[k]["end"] == default[k]["end"] and base[k]["starve"] == default[k]["starve"])
                  for k in (0, 1)}
    exact = all(r["status"] == "pass" and r["errors"] == 0 for r in rows)
    best = max((r for r in rows if r["status"] == "pass"), key=lambda r: r["bytes_per_cycle_row_phase"])
    record = {
        "schema": "opentallas.rtl.v41_qe_shared_stall_inflight.v1",
        "status": "pass" if exact and all(v["identical"] for v in regression.values()) else "fail",
        "claim": ("In-flight sweep of the actual QE + qstream + shared one-stack HBM model on the real L0 wq_a "
                  "descriptor; synthetic activation and K traffic; one stack, no core, no physical timing."),
        "knobs": {"LA": "qstream look-ahead words", "W_ND": "adapter descriptors", "W_DEPTH": "adapter return "
                  "sectors per PC", "W_ROOM": "free sectors per PC advertised to the qstream as room"},
        "demand_bytes_per_cycle": WORD_BYTES,
        "default_regression_vs_prior_record": regression,
        "best": {k: best[k] for k in ("la", "w_nd", "w_depth", "w_room", "k", "end", "starve",
                                       "bytes_per_cycle_row_phase")},
        "vectors": src,
        "cases": rows,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in S.RTL + [S.TB, Path(__file__).resolve(),
                          ROOT / "tools/v41_qe_shared_stall_gate.py", ROOT / "tools/hdc_golden_v41.py",
                          ROOT / "tools/hdc_golden.py"]},
    }
    out = a.output
    if out.exists() and json.loads(out.read_text()).get("status") == "fail" and record["status"] == "pass":
        out = out.with_name(out.stem + "_rerun.json")
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"], json.dumps(record["best"]), json.dumps(regression))
    if tmp:
        tmp.cleanup()
    sys.exit(0 if record["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
