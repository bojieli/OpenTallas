#!/usr/bin/env python3
"""W11 streaming-domain exactness gates: the as-built campaign tools, pointed at the latency-parameterised _l units.

The FPL/FML/QL units live in their own files (tools/w11_stream_latgen.py), so the as-built campaign tools and benches
stay as on main; this driver swaps their RTL / bench constants for the streaming copies and passes the latencies:

  idx   tools/rtl_hdc_v41x_idx_campaign.py shape bench (mixed classes + bubbles/back-pressure, back-to-back scan;
        reduced shape adds the vehicle) on ot_hdc_v41x_idx_engine_l           --shape reduced|shipped [--quick]
  arr   tools/rtl_w11_idx_array.py small-N gates (NS=4/NK=1, NS=2/NK=4) on ot_hdc_v41x_idx_array_l
  attn  tools/rtl_hdc_v41x_attn_campaign.py tile benches and engines on ot_hdc_v41x_attn_tile_l / ot_hdc_v41x_attn_l,
        including the p.v / q.k bubble count against the stationary-bank count (NBANKP)

Each writes <out>.json with its verdict, the latencies and the sha256 of every source it built.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
V = ROOT / "rtl/hdc/v41x"
T = ROOT / "rtl/test"
FPLIB = [ROOT / "rtl/hdc/ot_hdc_fp32_add_lat.sv", ROOT / "rtl/hdc/ot_hdc_prefix.sv"]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pins(paths):
    return {str(Path(p).resolve().relative_to(ROOT)): sha(Path(p)) for p in paths}


# -- indexer engine --------------------------------------------------------------------------------------------
def gate_idx(a, lat):
    import rtl_hdc_v41x_idx_campaign as C
    rtl = [V / "ot_hdc_v41x_idx_lat.sv", V / "ot_hdc_v41x_idx_arith_lat.sv", *C.RTL, *FPLIB]
    tb, vlt = T / "tb_hdc_v41x_idx_lat.sv", T / "tb_hdc_v41x_idx_lat.vlt"

    def build(work: Path, nk, ih, nb, fd, jobs=16):
        obj = work / "obj_nk{}_ih{}_nb{}_fd{}_l{FPL}_{FML}_{QL}".format(nk, ih, nb, fd, **lat)
        exe = obj / "Vtb_hdc_v41x_idx"
        stamp = hashlib.sha256(b"".join(p.read_bytes() for p in rtl + [vlt, tb, C.HARNESS])).hexdigest()
        if exe.exists() and (obj / "stamp").exists() and (obj / "stamp").read_text() == stamp:
            return exe
        cmd = ["verilator", "--cc", "--exe", "--build", "-O3", "--x-assign", "fast", "--x-initial", "fast",
               "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-DECLFILENAME", "-Wno-UNOPTFLAT",
               "--top-module", "tb_hdc_v41x_idx", f"-GNK={nk}", f"-GIH={ih}", f"-GNB={nb}", f"-GFD={fd}",
               *[f"-G{k}={v}" for k, v in lat.items()],
               "-CFLAGS", "-DVTOP=Vtb_hdc_v41x_idx -O1", "-j", str(jobs), "--Mdir", str(obj),
               str(vlt), str(tb)] + [str(p) for p in rtl] + [str(C.HARNESS)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        (obj / "stamp").write_text(stamp)
        return exe

    C.build = build
    rng = np.random.default_rng(20260926)
    ih, nb = {"shipped": (32, 4), "reduced": (32, 1)}[a.shape]
    per_class = 2 if a.quick else 12
    nkeys = (lambda: int(rng.integers(1, 40))) if a.quick else (lambda: int(rng.integers(1, 400)))
    toks = [C.finish(C.rand_token(rng, ih, nb, nkeys(), c)) for c in C.CLASSES for _ in range(per_class)]
    if a.shape == "reduced":
        toks += C.vehicle_tokens(8 if a.quick else 40)
    r = C.shape_bench(Path(a.work), a.shape, ih, nb, 8, 64, toks, 512 if a.quick else 16384, rng)
    m, b = r["mixed"], r["back_to_back"]
    exact = m["errors"] == 0 and m["checked"] == m["keys"] and b["errors"] == 0 and b["checked"] == b["keys"] \
        and m["faults_expected_and_raised"] == m["expected_faults"]
    thr = b["keys_per_cycle"] >= 0.99 * 8 * (1 - 1.0 / max(1, b["beats"]))
    return dict(gate="idx", shape=a.shape, quick=a.quick, bench=r, bit_exact=exact, throughput_ok=thr,
                keys_per_cycle=b["keys_per_cycle"], first_score_latency=b["lat_min"],
                status="pass" if exact and thr else "fail",
                sources=pins(rtl + [tb, vlt, C.HARNESS, ROOT / "tools/hdc_golden_v41.py",
                                    ROOT / "tools/rtl_hdc_v41x_idx_campaign.py"]))


# -- indexer scoring array (small N) -----------------------------------------------------------------------------
def gate_arr(a, lat):
    import rtl_w11_idx_array as A
    A.RTL = ["rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv",
             "rtl/hdc/v41x/ot_hdc_v41x_idx.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv", "rtl/hdc/ot_hdc_fastfp.sv",
             "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv"]
    A.TB, A.VLT = "rtl/test/tb_hdc_v41x_idx_array_lat.sv", "rtl/test/tb_hdc_v41x_idx_array_lat.vlt"
    A.SOURCES = A.RTL + [A.TB, A.VLT, A.HARNESS, "tools/rtl_w11_idx_array.py", "tools/rtl_hdc_v41x_idx_campaign.py",
                         "tools/hdc_golden_v41.py", "tools/w11_stream_gates.py"]
    def build(work, ns, nk, jobs=8):
        tag = "".join(c for c in A.verilator_version().split()[1] if c.isdigit() or c == ".")
        obj = work / "obj_lat{FPL}_{FML}_{QL}".format(**lat) / f"ns{ns}_nk{nk}_v{tag}"
        exe = obj / "Vtb_hdc_v41x_idx_array"
        stamp = hashlib.sha256(b"".join((ROOT / p).read_bytes() for p in A.RTL + [A.TB, A.VLT, A.HARNESS])).hexdigest()
        if exe.exists() and (obj / "stamp").exists() and (obj / "stamp").read_text() == stamp:
            return exe, None
        obj.mkdir(parents=True, exist_ok=True)
        cmd = [A.VERILATOR, "--cc", "--exe", "--build", "-O3", "--x-assign", "fast", "--x-initial", "fast",
               "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-DECLFILENAME", "-Wno-UNOPTFLAT",
               "--top-module", "tb_hdc_v41x_idx_array", f"-GNS={ns}", f"-GNK={nk}",
               *[f"-G{x}={v}" for x, v in lat.items()],
               "-CFLAGS", "-DVTOP=Vtb_hdc_v41x_idx_array -O1", "-j", str(jobs), "--Mdir", str(obj),
               str(ROOT / A.VLT), str(ROOT / A.TB)] + [str(ROOT / p) for p in A.RTL] + [str(ROOT / A.HARNESS)]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stdout[-3000:] + r.stderr[-3000:])
        (obj / "stamp").write_text(stamp)
        return exe, time.time() - t0
    A.build = build
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    A.OUT = Path(a.out).with_suffix(".array.json")
    if not (work / "meta.json").exists():
        A.phase_prepare(work, False, True)
    A.phase_sim(work, 4)
    A.phase_record(work)
    rec = json.loads(A.OUT.read_text())
    ok = rec.get("status") == "pass" or rec.get("verdict", {}).get("small_n_exact") or rec.get("ok_small")
    small = rec.get("element", {})
    return dict(gate="arr", array_record=str(A.OUT), status="pass" if ok else "fail", bit_exact=bool(ok),
                element=small, sources=pins([ROOT / p for p in A.SOURCES]))


# -- attention tile and engine -----------------------------------------------------------------------------------
def gate_attn(a, lat):
    import rtl_hdc_v41x_attn_campaign as C
    fpl, fml = lat["FPL"], lat["FML"]
    C.RTL_TILE, C.RTL_ENG = V / "ot_hdc_v41x_attn_tile_lat.sv", V / "ot_hdc_v41x_attn_lat.sv"
    C.TB_TILE, C.TB_ENG = T / "tb_hdc_v41x_attn_tile_lat.sv", T / "tb_hdc_v41x_attn_lat.sv"
    base = [V / "ot_hdc_v41x_attn_tile.sv", V / "ot_hdc_v41x_attn.sv", *C.LIB, *FPLIB]
    C.lib = lambda f=3: list(base)
    out = Path(a.work)
    res = {}
    for (H, TD, nb, seed) in [(4, 16, 40, 7), (16, 32, 120, 3)]:
        r = C.run_tile(out, H=H, TD=TD, nbeats=nb, seed=seed, fpl=fpl, fml=fml)
        res[f"tile_h{H}_td{TD}"] = {k: r[k] for k in ("status", "beats", "checked", "errors",
                                                      "faults_expected_and_raised", "first_ov")}
        print(res[f"tile_h{H}_td{TD}"], flush=True)
    engines = []
    rng = np.random.default_rng(9)
    small = [C.random_job(rng, 4, 64, T_, min(T_, 40)) for T_ in (72, 1, 33)]
    rng = np.random.default_rng(5)
    dpt8 = [C.random_job(rng, 16, 64, T_, min(T_, 128)) for T_ in (256, 97)]
    for name, cfg, jobs, extra in [
            ("small", dict(H=4, D=64, TD=16, NL=1, TROWS=72), small, {}),
            ("dpt8_pw2", dict(H=16, D=64, TD=32, NL=4, TROWS=256), dpt8, {"PWORDS": 2})] + \
            [(f"dpt8_pw2_b{nbk}", dict(H=16, D=64, TD=32, NL=4, TROWS=256), dpt8, {"PWORDS": 2, "NBANKP": nbk})
             for nbk in a.banks]:
        ex = dict(extra, FPL=fpl, FML=fml, SC_CRED=128, PV_CRED=128)
        r = C.run_engine(out, f"{name}_l{fpl}_{fml}", cfg, jobs, extra=ex)
        e = dict(name=name, config=cfg, extra=ex, bit_exact=r["bit_exact"], latency=r["latency"],
                 per_job=[{k: j[k] for k in ("T", "qk_beats", "qk_beat_bubbles", "pv_beats", "pv_beat_bubbles")}
                          for j in r["per_job"]])
        print(json.dumps(e), flush=True)
        engines.append(e)
    ok = all(v["status"] == "pass" for v in res.values()) and all(e["bit_exact"] for e in engines)
    return dict(gate="attn", tiles=res, engines=engines, bit_exact=ok, status="pass" if ok else "fail",
                sources=pins([C.RTL_TILE, C.RTL_ENG, C.TB_TILE, C.TB_ENG, *base, V / "ot_hdc_v41x_attn_staging.sv",
                              ROOT / "tools/rtl_hdc_v41x_attn_campaign.py", ROOT / "tools/hdc_golden_v41.py"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gate", choices=("idx", "arr", "attn"))
    ap.add_argument("--lat", required=True, help="FPL,FML,QL (attention: FPL,FML)")
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shape", default="reduced", choices=("reduced", "shipped"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--banks", type=lambda s: [int(x) for x in s.split(",") if x], default=[])
    a = ap.parse_args()
    lat = dict(zip(("FPL", "FML", "QL"), map(int, a.lat.split(","))))
    if a.gate == "attn":
        lat.pop("QL", None)
    Path(a.work).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rec = dict(gate_idx=gate_idx, gate_arr=gate_arr, gate_attn=gate_attn)["gate_" + a.gate](a, lat)
    rec.update(tool="tools/w11_stream_gates.py " + " ".join(sys.argv[1:]), latencies=lat,
               wall_s=round(time.time() - t0, 1),
               git_head=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                       text=True).stdout.strip())
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)) + "\n")
    print("status", rec["status"])


if __name__ == "__main__":
    main()
