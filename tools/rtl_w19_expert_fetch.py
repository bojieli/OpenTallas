#!/usr/bin/env python3
"""W19 B2: the V4.1 HBM comparator's routed-expert fetch path in RTL, measured against a timing-faithful DRAM model.

    python3 tools/rtl_w19_expert_fetch.py [--out results/rtl/w19_expert_fetch.json] [--work /tmp/claude-1000/w19/b2]

1. Router top-6 (rtl/gpu/ot_gpu_router_topk.sv, rtl/test/tb_gpu_router_topk.sv): the 40 layers' router vectors of the
   W17 1M reference token (bi = scores + bias, FP32; /home/ubuntu/w17work/ref/ctx1048576_seed20260930) and random
   vectors with ties and signed zeros, against hdc_golden_v41.topk_lowest_index (ids ascending).
2. Fetch (rtl/gpu/ot_gpu_expert_fetch.sv, rtl/test/tb_gpu_expert_fetch.sv): router values -> top-6 -> per-SM
   descriptors -> HBM (rtl/hdc/kv/ot_hdc_hbm_model.sv: one HBM3E stack, 32 pseudo-channels, 1.0 TB/s, all-bank
   refresh live) -> SMEM staging of the 8 SMs homed on the stack -> tensor core at one line a cycle, at 1.2 GHz.
   The die's TP-96 slice of an expert (w1, w3: 24 rows x 5,120 FP4 + UE8M0 scales; w2: 54 rows x 2,304, the larger
   rank) is spread over the die's 32 SMs by bytes (longest-processing-time rows); the stack's share is the 8 SMs
   s = 0, 4, .., 28.  Every released line is checked against the backing store.
Records cycle stamps from the first router value: top-6 out, first descriptor, first HBM request, first sector
landed, first line to a tensor core, the first expert's w1/w3 rows complete in every SM, the first expert complete,
all experts complete; and the stream rate against the stack's 1.0 TB/s.
"""
import argparse, datetime, hashlib, json, os, re, subprocess, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as V  # noqa: E402

REF = Path(os.environ.get("W19_REF", "/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
SRC_T = ["rtl/gpu/ot_gpu_router_topk.sv", "rtl/test/tb_gpu_router_topk.sv"]
SRC_F = ["rtl/gpu/ot_gpu_router_topk.sv", "rtl/gpu/ot_gpu_expert_fetch.sv", "rtl/hdc/kv/ot_hdc_hbm_model.sv",
         "rtl/test/tb_gpu_expert_fetch.sv"]
CLK_PS = 833
NSM_DIE, NSM, TP = 32, 8, 96
STACK_BPS = 1.0e12
AUDIT = dict(central_us=0.5, low_us=0.25, high_us=1.0, expert_chunk_efficiency=0.797,
             source="results/uarch/hbm_feasibility_audit.json fetch_latency_us, dram_proxy B_expert")


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def layout():
    """The die's rows of one expert over its 32 SMs (by bytes), and the stack's 8 SMs' runs in 128-B lines."""
    w2_rows = max(b - a for a, b in ((r * 5120 // TP, (r + 1) * 5120 // TP) for r in range(TP)))
    rows = [("w13", 5120 // 2 + 5120 // 32)] * 48 + [("w2", 2304 // 2 + 2304 // 32)] * w2_rows
    sm = [dict(w13=0, w2=0) for _ in range(NSM_DIE)]
    for kind, b in rows:                                   # rows in order: w1, w3, then w2; each to the lightest SM
        j = min(range(NSM_DIE), key=lambda s: (sm[s]["w13"] + sm[s]["w2"], s))
        sm[j][kind] += b
    die_bytes = sum(s["w13"] + s["w2"] for s in sm)
    mine = list(range(0, NSM_DIE, NSM_DIE // NSM))
    lines = [-(-(sm[j]["w13"] + sm[j]["w2"]) // 128) for j in mine]
    w13 = [-(-sm[j]["w13"] // 128) for j in mine]
    off = [sum(lines[:i]) for i in range(NSM)]
    return dict(w2_rows=w2_rows, die_bytes_per_expert=die_bytes, sm_bytes=[sm[j] for j in mine], stack_sms=mine,
                lines=lines, w13_lines=w13, off=off, exp_lines=sum(lines), base=0)


def build(src, top, work, params, name):
    exe = work / f"{name}.vvp"
    subprocess.run(["iverilog", "-g2012", "-o", str(exe), "-s", top] + [f"-P{top}.{k}={v}" for k, v in params.items()]
                   + [str(ROOT / s) for s in src], check=True)
    return exe


def run(exe, cwd):
    out = subprocess.run(["vvp", "-n", str(exe)], capture_output=True, text=True, cwd=cwd).stdout
    return out


def topk_check(work):
    vecs, want, names = [], [], []
    for L in range(40):
        z = np.load(REF / f"ctx1048576_L{L:02d}.npz")
        vecs.append(z[f"L{L}.router"].astype(np.float32))
        want.append(json.loads((REF / f"ctx1048576_L{L:02d}.json").read_text())["experts"])
        names.append(f"L{L}")
    rng = np.random.default_rng(20260930)
    pool = np.array([0.0, -0.0, 1.5, -1.5, 2.0, 1e-30, -1e-30, 3.25, -np.inf, np.inf], dtype=np.float32)
    for t in range(200):
        if t % 3 == 0:
            v = rng.choice(pool, 384)
        elif t % 3 == 1:
            v = rng.standard_normal(384).astype(np.float32)
        else:                                             # few distinct values: many ties at the cut
            v = rng.choice(rng.standard_normal(5).astype(np.float32), 384)
        vecs.append(v)
        want.append(sorted(int(i) for i in V.topk_lowest_index(v, 6)))
        names.append(f"random{t}")
    (work / "rt.hex").write_text("\n".join("%08x" % x for v in vecs for x in v.view(np.uint32)) + "\n")
    exe = build(SRC_T, "tb_gpu_router_topk", work, dict(NV=len(vecs)), "topk")
    out = run(exe, work)
    got = [list(map(int, l.split()[3:])) for l in out.splitlines() if l.startswith("TOPK ") and "TIMEOUT" not in l]
    lat = sorted({int(l.split()[2][4:]) for l in out.splitlines() if l.startswith("TOPK ")})
    bad = [n for n, g, w in zip(names, got, want) if g != w]
    ok = len(got) == len(want) and not bad
    return dict(vectors=len(vecs), real_router_vectors=40, random_vectors=200, exact=len(got) - len(bad),
                mismatches=bad[:10], verdict="pass" if ok else "fail",
                latency_last_beat_to_ids_cycles=lat, beats_per_vector=384 // 16,
                note="bench latency counts from the cycle the last beat is presented; +24 beats of 16 values")


def fetch_case(work, lay, name, mode, ids=None, rv=None, start=6000, bg_ppm=0, noc_ps=5000, extra=None):
    d = work / name
    d.mkdir(exist_ok=True)
    cfg = [lay["base"], lay["exp_lines"]] + lay["off"] + lay["lines"] + lay["w13_lines"]
    (d / "cfg.hex").write_text("\n".join("%x" % x for x in cfg) + "\n")
    (d / "ids.hex").write_text("\n".join("%x" % x for x in (ids or [0])) + "\n")
    rvv = rv if rv is not None else np.zeros(384, dtype=np.float32)
    (d / "rv.hex").write_text("\n".join("%08x" % x for x in rvv.view(np.uint32)) + "\n")
    params = dict(MODE=mode, NIDS=len(ids or [0]), START=start, BG_PPM=bg_ppm, CLK_PS=CLK_PS,
                  REQ_PS=10000 + noc_ps, RSP_PS=10000 + noc_ps, **(extra or {}))
    exe = build(SRC_F, "tb_gpu_expert_fetch", d, params, "f")
    out = run(exe, d)
    line = [l for l in out.splitlines() if l.startswith("FETCH")][-1]
    if "TIMEOUT" in line:
        return dict(case=name, verdict="fail", timeout=True)
    r = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", line)}
    r["ids"] = list(map(int, line.split(" ids")[1].split()))
    t0 = r["t0"]
    rel = {k: r[k] - t0 for k in ("topk", "desc", "req", "sect", "line", "w13_first_min", "w13_first_all",
                                   "exp1_all", "done") if r[k] >= 0}
    ns = {k: round(v * CLK_PS / 1000, 1) for k, v in rel.items()}
    nbytes = r["lines"] * 128
    stream_cyc = r["done"] - r["req"]
    gbps = nbytes / (stream_cyc * CLK_PS * 1e-12) / 1e9
    exp_lines = lay["exp_lines"] * r["nids"]
    res = dict(case=name, mode="router" if mode == 0 else "ids", params=params, ids=r["ids"],
               cycles_from_first_router_value=rel, ns_from_first_router_value=ns,
               first_byte_latency_cycles=r["sect"] - r["req"],
               first_byte_latency_ns=round((r["sect"] - r["req"]) * CLK_PS / 1000, 1),
               first_line_to_tensor_core_ns=round((r["line"] - r["req"]) * CLK_PS / 1000, 1),
               stack_bytes=nbytes, stream_GBps=round(gbps, 1), stack_efficiency=round(gbps * 1e9 / STACK_BPS, 3),
               max_read_latency_ns=round(r["rd_lat_max_ps"] / 1000, 1), refreshes_pc0=r["refreshes"],
               background_requests=r["bg_issued"], lines_checked=r["lines"], bad_sectors=r["bad"],
               integrity="pass" if r["bad"] == 0 and r["lines"] == exp_lines else "fail")
    res["verdict"] = res["integrity"]
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--work", default="/tmp/claude-1000/w19/b2")
    a = ap.parse_args(argv)
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    topk = topk_check(work)
    print("topk", topk["verdict"], topk["exact"], "/", topk["vectors"], topk["latency_last_beat_to_ids_cycles"])
    lay = layout()
    real = {}
    for L in (0, 1, 20, 39):
        z = np.load(REF / f"ctx1048576_L{L:02d}.npz")
        real[L] = (z[f"L{L}.router"].astype(np.float32),
                   json.loads((REF / f"ctx1048576_L{L:02d}.json").read_text())["experts"])
    rng = np.random.default_rng(346)
    union = sorted(int(i) for i in rng.choice(384, 35, replace=False))
    POST = dict(REFI_PS=10 ** 9)                           # refresh postponed over the fetch window
    jobs = [(f"ar_L{L}", dict(mode=0, rv=real[L][0]), L) for L in (0, 1, 20, 39)]
    jobs += [(f"ar_L0_start{st}", dict(mode=0, rv=real[0][0], start=st), 0) for st in (6050, 6100)]
    jobs += [("ar_L0_refresh_postponed", dict(mode=0, rv=real[0][0], extra=POST), 0),
             ("ar_L0_noc0ns", dict(mode=0, rv=real[0][0], noc_ps=0), 0),
             ("ar_L0_noc15ns", dict(mode=0, rv=real[0][0], noc_ps=15000), 0),
             ("ar_L0_noc15ns_refresh_postponed", dict(mode=0, rv=real[0][0], noc_ps=15000, extra=POST), 0),
             ("ar_L0_bg80", dict(mode=0, rv=real[0][0], bg_ppm=800000), 0),
             ("ar_L0_bg80_refresh_postponed", dict(mode=0, rv=real[0][0], bg_ppm=800000, extra=POST), 0),
             ("mtp_union35", dict(mode=1, ids=union), None),
             ("mtp_union35_refresh_postponed", dict(mode=1, ids=union, extra=POST), None),
             ("mtp_union35_bg80", dict(mode=1, ids=union, bg_ppm=800000), None)]

    def one(job):
        name, kw, L = job
        kw = dict(kw)
        mode = kw.pop("mode")
        c = fetch_case(work, lay, name, mode, **kw)
        if L is not None:
            c["golden_experts"] = real[L][1]
            c["router_exact"] = c["ids"] == real[L][1]
            c["verdict"] = "pass" if c["verdict"] == "pass" and c["router_exact"] else "fail"
        return c
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(4) as ex:
        cases = list(ex.map(one, jobs))
    for c in cases:
        print(c["case"], c["verdict"], c["ns_from_first_router_value"], "first byte", c["first_byte_latency_ns"],
              "GB/s", c["stream_GBps"])
    by = {c["case"]: c for c in cases}
    central = by["ar_L0"]
    ok = topk["verdict"] == "pass" and all(c["verdict"] == "pass" for c in cases)

    def exposed(c):                                         # top-6 out -> first expert's w1/w3 in every SM
        n = c["ns_from_first_router_value"]
        return round(n["w13_first_all"] - n.get("topk", 0.0), 1)
    rec = dict(schema="opentallas.rtl.w19_expert_fetch.v1", tool="tools/rtl_w19_expert_fetch.py", stream="W19 B2",
               status="pass" if ok else "fail",
               claim_boundary="RTL simulation (Icarus) of the router top-6 selector and the expert fetch path against "
                              "a behavioural, timing-faithful HBM3E model (one stack, 32 pseudo-channels); controller "
                              "and PHY latencies are the model's assumed defaults plus an assumed on-die NoC term. No "
                              "synthesis, P&R or timing closure.",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               simulator=subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0],
               clock_hz=1e12 / CLK_PS / 1e3 * 1e3, clk_ps=CLK_PS,
               hbm_model=dict(module="ot_hdc_hbm_model", npc=32, stack_bandwidth_Bps=STACK_BPS,
                              req_ps="10,000 controller/PHY (model default, assumed) + NoC",
                              rsp_ps="10,000 PHY/controller (model default, assumed) + NoC",
                              noc_ps_central=5000, refresh="all-bank REFab, tREFI 3.9 us, tRFC 350 ns, staggered; "
                              "requests start after the first interval", timings="model defaults (Ramulator2 HBM3)"),
               layout=lay, router_topk=topk, cases=cases,
               audit_comparison=dict(
                   audit=AUDIT,
                   metric="exposed wait after the router: top-6 out -> the first expert's w1/w3 rows landed in "
                          "every SM of the stack (the first expert matvec can start; later experts stream under "
                          "it). The model prices 0.5 us a MoE layer (0.25 / 1.0 bounds).",
                   exposed_ns={c["case"]: exposed(c) for c in cases if c["mode"] == "router"},
                   exposed_ns_refresh_live_ar=[exposed(by[k]) for k in ("ar_L0", "ar_L1", "ar_L20", "ar_L39",
                                                                         "ar_L0_start6050", "ar_L0_start6100")],
                   exposed_ns_refresh_postponed_ar=exposed(by["ar_L0_refresh_postponed"]),
                   first_byte_after_request_ns=central["first_byte_latency_ns"],
                   router_to_all_six_ns=central["ns_from_first_router_value"]["done"],
                   stream_efficiency=dict(ar_refresh_live=central["stack_efficiency"],
                                          ar_refresh_postponed=by["ar_L0_refresh_postponed"]["stack_efficiency"],
                                          mtp_refresh_live=by["mtp_union35"]["stack_efficiency"],
                                          mtp_refresh_postponed=by["mtp_union35_refresh_postponed"]["stack_efficiency"],
                                          audit_dramsim_expert_chunks=0.797)),
               source_sha256={s: sha(s) for s in sorted(set(SRC_T + SRC_F + ["tools/rtl_w19_expert_fetch.py",
                                                                           "tools/hdc_golden_v41.py"]))})
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
        print("wrote", a.out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
