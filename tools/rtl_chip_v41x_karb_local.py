#!/usr/bin/env python3
"""Source-pinned transaction-equivalence gate of the local K arbitration partition.

ot_chip_v41x_hbm_karb_local (docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md) against the
monolithic ot_chip_v41x_hbm_karb: both drive their own refresh-aware HBM model
(ot_hdc_v41x_idx_hbm, preloaded identically) from the same traces
(rtl/test/tb_chip_v41x_karb_local_equiv.sv).  Per scenario the gate requires

  * every K response beat, grouped by tag and sorted by beat, identical in both arms and
    equal to a sequential golden (K in acceptance order; masked writes);
  * every B response beat, grouped by (PC, tag), identical and equal to the golden;
  * the final memory image identical and equal to the golden;
and it records cycles to drain, first-K acceptance -> first-K response latency in
each arm, and the added cycles.

    python3 tools/rtl_chip_v41x_karb_local.py            # writes the record
    python3 tools/rtl_chip_v41x_karb_local.py --quick    # two scenarios, no record
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import json
import random
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    "rtl/chip/ot_chip_v41x_hbm_karb_pipe.sv",
    "rtl/chip/ot_chip_v41x_karb_proot.sv",
    "rtl/chip/ot_chip_v41x_karb_pregion.sv",
    "rtl/chip/ot_chip_v41x_karb_pslice.sv",
    "rtl/chip/ot_chip_v41x_karb_pipe.sv",
    "rtl/chip/ot_chip_v41x_hbm_karb_local.sv",
    "rtl/chip/ot_chip_v41x_karb_stack_ep.sv",
    "rtl/chip/ot_chip_v41x_karb_region.sv",
    "rtl/chip/ot_chip_v41x_karb_region_kq.sv",
    "rtl/chip/ot_chip_v41x_karb_slice.sv",
    "rtl/chip/ot_chip_v41x_karb_q2.sv",
    "rtl/chip/ot_chip_v41x_karb_q2r.sv",
    "rtl/chip/ot_chip_v41x_keep_dff.sv",
    "rtl/chip/ot_chip_v41x_karb_qn.sv",
    "rtl/chip/ot_chip_v41x_karb_qh.sv",
    "rtl/chip/ot_chip_v41x_hbm_karb.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
    "rtl/test/tb_chip_v41x_karb_local_equiv.sv",
    "tools/rtl_chip_v41x_karb_local.py",
    "rtl/test/tb_chip_v41x_kv_prefetch.sv",
    "rtl/test/tb_chip_v41x_karb_local_hash.sv",
    "rtl/chip/ot_chip_v41x_kv_prefetch.sv",
    "rtl/chip/ot_chip_v41x_hbm3e_phy.sv",
    "rtl/hdc/kv/ot_hdc_hbm_model.sv",
)
KARB_RTL = ["rtl/chip/ot_chip_v41x_hbm_karb_pipe.sv", "rtl/chip/ot_chip_v41x_karb_proot.sv",
            "rtl/chip/ot_chip_v41x_karb_pregion.sv", "rtl/chip/ot_chip_v41x_karb_pslice.sv",
            "rtl/chip/ot_chip_v41x_karb_pipe.sv", "rtl/chip/ot_chip_v41x_hbm_karb_local.sv", "rtl/chip/ot_chip_v41x_karb_stack_ep.sv",
            "rtl/chip/ot_chip_v41x_karb_region.sv", "rtl/chip/ot_chip_v41x_karb_region_kq.sv",
            "rtl/chip/ot_chip_v41x_karb_slice.sv", "rtl/chip/ot_chip_v41x_karb_q2.sv",
            "rtl/chip/ot_chip_v41x_karb_q2r.sv", "rtl/chip/ot_chip_v41x_keep_dff.sv",
            "rtl/chip/ot_chip_v41x_karb_qn.sv", "rtl/chip/ot_chip_v41x_karb_qh.sv", "rtl/chip/ot_chip_v41x_hbm_karb.sv"]
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools"))
VERILATOR = os.environ.get("OT_VERILATOR", str(TOOLS_ROOT / "verilator-5.050/bin/verilator"))
OUTPUT = ROOT / "results/rtl/chip_v41x_karb_local_equiv.json"
NPC, AW, MEMW, NK, NB = 32, 28, 1 << 14, 512, 64
M32 = 0xFFFFFFFF


def pc_of(s: int) -> int:
    return ((s >> 2) ^ (s >> 7) ^ (s >> 12)) & (NPC - 1)


def wd(seed: int) -> int:
    x, v = seed & M32, 0
    for j in range(8):
        x = (x * 1664525 + 1013904223) & M32
        v |= x << (32 * j)
    return v


def apply_write(mem: list[int], a: int, data: int, strb: int) -> None:
    mask = 0
    for b in range(32):
        if strb >> b & 1:
            mask |= 0xFF << (8 * b)
    mem[a] = (mem[a] & ~mask) | (data & mask)


def entry(we, ln, addr, tag, strb, seed) -> str:
    v = (we << 112) | (ln << 108) | (addr << 80) | (tag << 64) | (strb << 32) | seed
    return f"{v:029x}"


def rand_read(rng, lo, hi, pc=None):
    while True:
        a = rng.randrange(lo, hi)
        ln = rng.randint(1, 4 - a % 4)
        if pc is None or pc_of(a) == pc:
            return a, ln


def scenario(name: str, seed: int, nk: int, nb: int, kwf: float, bwf: float, reuse: float,
             k_only_reads=False):
    rng = random.Random(seed)
    init = [rng.getrandbits(256) for _ in range(MEMW)]
    mem = list(init)
    half = MEMW // 2
    k, kexp, recent = [], {}, []
    for t in range(nk):
        if not k_only_reads and rng.random() < kwf:
            a = rng.randrange(half, MEMW)
            strb, ds = rng.getrandbits(32) | 1, rng.getrandbits(32)
            k.append(entry(1, 1, a, t, strb, ds))
            apply_write(mem, a, wd(ds), strb)
            recent.append(a)
        else:
            if recent and rng.random() < reuse:
                a = rng.choice(recent[-16:]); ln = rng.randint(1, 4 - a % 4)
            else:
                a, ln = rand_read(rng, half, MEMW)
            k.append(entry(0, ln, a, t, 0, 0))
            kexp[t] = [mem[a + i] for i in range(ln)]
    b, bexp = [], {}
    for p in range(NPC):
        rows, precent = [], []
        for t in range(nb):
            if rng.random() < bwf:
                a, _ = rand_read(rng, 0, half, p)
                strb, ds = rng.getrandbits(32) | 1, rng.getrandbits(32)
                rows.append(entry(1, 1, a, t, strb, ds))
                apply_write(mem, a, wd(ds), strb)
                precent.append(a)
            else:
                if precent and rng.random() < reuse:
                    a = rng.choice(precent); ln = rng.randint(1, 4 - a % 4)
                else:
                    a, ln = rand_read(rng, 0, half, p)
                rows.append(entry(0, ln, a, t, 0, 0))
                bexp[(p, t)] = [mem[a + i] for i in range(ln)]
        b.append(rows)
    return {"name": name, "seed": seed, "k": k, "b": b, "init": init, "kexp": kexp, "bexp": bexp,
            "mem": mem}


def write_trace(sc, d: Path) -> None:
    (d / "k.hex").write_text("\n".join(sc["k"]) + "\n")
    lines = []
    for p in range(NPC):
        rows = sc["b"][p]
        for i in range(NB):
            lines.append(f"@{p * NB + i:x} {rows[i]}" if i < len(rows) else "")
    (d / "b.hex").write_text("\n".join(x for x in lines if x) + "\n")
    (d / "init.hex").write_text("\n".join(f"{v:064x}" for v in sc["init"]) + "\n")


def parse(log: Path):
    k, b, mem, meta = defaultdict(list), defaultdict(list), {}, {}
    for line in log.read_text().splitlines():
        f = line.split()
        if f[0] == "K":
            k[int(f[1], 16)].append((int(f[2], 16), int(f[3], 16)))
        elif f[0] == "B":
            b[(int(f[1]), int(f[2], 16))].append((int(f[3], 16), int(f[4], 16)))
        elif f[0] == "M":
            mem[int(f[1])] = int(f[2], 16)
        else:
            for i in range(0, len(f), 2):
                meta[f[i]] = int(f[i + 1])
    # beats of one read may return out of beat order (the model's per-burst scheduler); the
    # consumers address staging by tag and beat, so compare per tag sorted by beat
    return ({t: sorted(v) for t, v in k.items()}, {t: sorted(v) for t, v in b.items()}, mem, meta)


def check_arm(sc, k, b, mem):
    errs = []
    for t, want in sc["kexp"].items():
        got = k.get(t, [])
        if [x[0] for x in got] != list(range(len(want))) or [x[1] for x in got] != want:
            errs.append(f"K tag {t}")
    if set(k) - set(sc["kexp"]):
        errs.append("unexpected K tags")
    for key, want in sc["bexp"].items():
        got = b.get(key, [])
        if [x[0] for x in got] != list(range(len(want))) or [x[1] for x in got] != want:
            errs.append(f"B {key}")
    if set(b) - set(sc["bexp"]):
        errs.append("unexpected B tags")
    if [mem.get(i) for i in range(MEMW)] != sc["mem"]:
        errs.append("memory image")
    return errs


def build(tmp: Path, fence: int) -> Path:
    exe = tmp / f"tb{fence}.vvp"
    srcs = [str(ROOT / s) for s in (*KARB_RTL, "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
                                     "rtl/test/tb_chip_v41x_karb_local_equiv.sv")]
    subprocess.run(["iverilog", "-g2012", "-s", "tb_chip_v41x_karb_local_equiv",
                    f"-Ptb_chip_v41x_karb_local_equiv.FENCE={fence}", "-o", str(exe), *srcs],
                   check=True, capture_output=True, text=True)
    return exe


def run_one(exe: Path, sc, work: Path, krdy: int, brdy: int):
    work.mkdir(parents=True, exist_ok=True)
    write_trace(sc, work)
    t0 = time.time()
    out = subprocess.run(["vvp", "-n", str(exe), f"+trace={work}", f"+log={work}/log",
                          f"+seed={sc['seed']}", f"+krdy={krdy}", f"+brdy={brdy}"],
                         capture_output=True, text=True, cwd=work)
    arms = {}
    for arm in ("mono", "local", "pipe"):
        k, b, mem, meta = parse(work / f"log.{arm}")
        arms[arm] = {"k": k, "b": b, "mem": mem, "meta": meta, "errs": check_arm(sc, k, b, mem)}
    same = all(arms["mono"][x] == arms[a][x] for a in ("local", "pipe") for x in ("k", "b", "mem"))
    ok = "DONE" in out.stdout and same and not any(arms[a]["errs"] for a in arms)
    m, l, pp = arms["mono"]["meta"], arms["local"]["meta"], arms["pipe"]["meta"]
    return {
        "scenario": sc["name"], "seed": sc["seed"], "k_requests": len(sc["k"]),
        "k_read_beats": sum(len(v) for v in sc["kexp"].values()),
        "k_writes": sum(1 for e in sc["k"] if int(e, 16) >> 112),
        "b_requests": sum(len(r) for r in sc["b"]),
        "k_rsp_ready_percent": krdy, "b_rsp_ready_percent": brdy,
        "stdout_tail": out.stdout.strip().splitlines()[-1:] if out.stdout else [],
        "mono_errors": arms["mono"]["errs"][:5], "local_errors": arms["local"]["errs"][:5],
        "pipe_errors": arms["pipe"]["errs"][:5], "arms_identical": same,
        "cycles_mono": m.get("CYCLES"), "cycles_local": l.get("CYCLES"), "cycles_pipe": pp.get("CYCLES"),
        "first_k_latency_pipe": (pp["FIRST_K_RSP"] - pp["FIRST_K_ACC"]) if "FIRST_K_RSP" in pp else None,
        "first_k_latency_mono": (m["FIRST_K_RSP"] - m["FIRST_K_ACC"]) if "FIRST_K_RSP" in m else None,
        "first_k_latency_local": (l["FIRST_K_RSP"] - l["FIRST_K_ACC"]) if "FIRST_K_RSP" in l else None,
        "k_wr_done_events": {"mono": m.get("KWD_EVENTS"), "local": l.get("KWD_EVENTS"), "pipe": pp.get("KWD_EVENTS")},
        "k_grants": {"mono": m.get("KGRANTS"), "local": l.get("KGRANTS"), "pipe": pp.get("KGRANTS")},
        "b_grants": {"mono": m.get("BGRANTS"), "local": l.get("BGRANTS"), "pipe": pp.get("BGRANTS")},
        "sim_seconds": round(time.time() - t0, 1), "pass": ok,
    }


def scenarios(quick: bool):
    s = [
        ("k_single_read_idle", dict(seed=11, nk=1, nb=0, kwf=0, bwf=0, reuse=0, k_only_reads=True), 100, 100),
        ("k_read_stream", dict(seed=12, nk=512, nb=0, kwf=0, bwf=0, reuse=0, k_only_reads=True), 100, 100),
        ("kv_prefetch_like_write_then_read", None, 100, 100),
        ("mixed_raw_full_ready", dict(seed=14, nk=512, nb=64, kwf=0.3, bwf=0.3, reuse=0.6), 100, 100),
        ("mixed_raw_backpressure", dict(seed=15, nk=512, nb=64, kwf=0.3, bwf=0.3, reuse=0.6), 40, 50),
        ("contended_b_heavy", dict(seed=16, nk=512, nb=64, kwf=0.1, bwf=0.5, reuse=0.3), 70, 30),
        ("k_write_heavy", dict(seed=17, nk=512, nb=32, kwf=0.7, bwf=0.2, reuse=0.8), 90, 90),
    ] + [(f"mixed_random_{sd}", dict(seed=sd, nk=512, nb=64, kwf=0.25, bwf=0.25, reuse=0.5), 30 + sd % 70,
          20 + (sd * 7) % 80) for sd in range(100, 112)]
    s += [(f"k_idle_region_{g}", {}, 100, 100) for g in range(NPC // 4)]
    return s[:2] + s[3:4] + [x for x in s if x[0] == "k_idle_region_0"] if quick else s


def idle_region(g: int):
    """One K read into an idle system, to a PC of region g (pc_of(addr) >> 2 == g)."""
    sc = scenario(f"k_idle_region_{g}", 900 + g, 0, 0, 0, 0, 0)
    rng = random.Random(900 + g)
    while True:
        a = rng.randrange(MEMW // 2, MEMW - 4) & ~3
        if pc_of(a) >> 2 == g:
            break
    sc["k"] = [entry(0, 1, a, 0, 0, 0)]
    sc["kexp"] = {0: [sc["mem"][a]]}
    return sc


def kv_like(seed: int):
    """Writes of a set of sectors, then reads of them (the prefetch issues reads after its writes)."""
    sc = scenario("kv_prefetch_like_write_then_read", seed, 0, 32, 0, 0.2, 0.0)
    rng = random.Random(seed + 1000)
    mem = list(sc["mem"])
    addrs = [rng.randrange(MEMW // 2, MEMW) for _ in range(192)]
    k, kexp = [], {}
    for t, a in enumerate(addrs):
        strb, ds = rng.getrandbits(32) | 1, rng.getrandbits(32)
        k.append(entry(1, 1, a, t, strb, ds)); apply_write(mem, a, wd(ds), strb)
    for t in range(len(addrs), 512):
        a = rng.choice(addrs); a4 = a - a % 4; ln = 4
        k.append(entry(0, ln, a4, t, 0, 0)); kexp[t] = [mem[a4 + i] for i in range(ln)]
    sc.update(k=k, kexp=kexp, mem=mem)
    return sc


def kv_bench(tmp: Path, local: int, fence: int) -> dict:
    """The adopted KV-prefetch bench (real ot_chip_v41x_kv_prefetch: gate, read-after-write, max descriptor,
    user slice, eviction, generation wrap with held responses, shared K ports under indexer traffic, region and
    whole-KV-region golden) with the monolithic (local = 0) or the local arbiter."""
    obj = tmp / f"kvobj_l{local}_f{fence}"
    obj.mkdir(parents=True, exist_ok=True)
    srcs = [ROOT / p for p in ("rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv", "rtl/hdc/kv/ot_hdc_hbm_model.sv",
                               "rtl/chip/ot_chip_v41x_hbm3e_phy.sv", "rtl/chip/ot_chip_v41x_kv_prefetch.sv",
                               *KARB_RTL, "rtl/test/tb_chip_v41x_kv_prefetch.sv")]
    srcs = list(dict.fromkeys(srcs))
    cmd = [VERILATOR, "--binary", "--timing", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-TIMESCALEMOD",
           "-Wno-BLKSEQ", "-Wno-MULTIDRIVEN", "--top-module", "tb_chip_v41x_kv_prefetch", "-Mdir", str(obj),
           f"-GKARB_LOCAL={local}", f"-GKARB_FENCE={fence}", *map(str, srcs), "-j", "4"]
    b = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if b.returncode:
        return {"pass": False, "build_tail": (b.stdout + b.stderr)[-2000:]}
    t0 = time.time()
    r = subprocess.run([str(obj / "Vtb_chip_v41x_kv_prefetch")], capture_output=True, text=True, cwd=ROOT,
                       timeout=4 * 3600)
    log = r.stdout + r.stderr
    keep = [ln for ln in log.splitlines() if re.match(r"(KVPF|KEYS|REGION|PASS|FAIL|TIMEOUT|KVBAD|WRAPBAD|HBMBAD)", ln)]
    cyc = re.search(r"cycles?[= ](\d+)", log)
    return {"arbiter": ("monolithic", "local", "pipelined local")[local], "k_rd_fence": fence if local else None,
            "pass": "PASS" in keep and r.returncode == 0, "summary": keep, "sim_seconds": round(time.time() - t0, 1),
            "log_sha256": hashlib.sha256(log.encode()).hexdigest()}


def hash_check(tmp: Path) -> dict:
    """Exhaustive K steering at AW = 30: all 2^17 values of sector bits [18:2] (random bits above), one request
    per cycle; each reaches the PC the monolithic arbiter picks, with its payload, and ingress never stalls."""
    exe = tmp / "hash.vvp"
    subprocess.run(["iverilog", "-g2012", "-s", "tb_chip_v41x_karb_local_hash", "-o", str(exe),
                    str(ROOT / "rtl/test/tb_chip_v41x_karb_local_hash.sv"), *(str(ROOT / s) for s in KARB_RTL)],
                   check=True, capture_output=True, text=True)
    out = subprocess.run(["vvp", "-n", str(exe)], capture_output=True, text=True).stdout
    line = next((ln for ln in out.splitlines() if ln.startswith("KARB_HASH")), "")
    return {"summary": line, "pass": "PASS" in out.splitlines()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--output", type=Path, default=OUTPUT)
    ap.add_argument("--keep", type=Path)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--no-kv", action="store_true")
    a = ap.parse_args()
    runs = []
    with tempfile.TemporaryDirectory(prefix="karbl_", dir="/tmp") as t:
        tmp = Path(a.keep) if a.keep else Path(t)
        tmp.mkdir(parents=True, exist_ok=True)
        from concurrent.futures import ThreadPoolExecutor
        jobs = []
        for fence in ((1,) if a.quick else (1, 0)):
            exe = build(tmp, fence)
            for name, kw, krdy, brdy in scenarios(a.quick):
                jobs.append((fence, exe, name, kw, krdy, brdy))

        def one(j):
            fence, exe, name, kw, krdy, brdy = j
            if name.startswith("k_idle_region_"):
                sc = idle_region(int(name.rsplit("_", 1)[1]))
            else:
                sc = kv_like(13) if kw is None else scenario(name, **kw)
            r = run_one(exe, sc, tmp / f"f{fence}_{name}", krdy, brdy)
            r["k_rd_fence"] = fence
            print(json.dumps({k: r[k] for k in ("scenario", "k_rd_fence", "pass", "cycles_mono", "cycles_local",
                                                 "cycles_pipe", "first_k_latency_mono", "first_k_latency_local",
                                                 "first_k_latency_pipe", "mono_errors", "local_errors",
                                                 "pipe_errors")}), flush=True)
            return r
        with ThreadPoolExecutor(max_workers=a.jobs) as ex:
            kvf = [] if a.quick or a.no_kv else [ex.submit(kv_bench, tmp, l, f) for l, f in ((0, 1), (1, 1), (1, 0), (2, 1), (2, 0))]
            hf = None if a.quick else ex.submit(hash_check, tmp)
            runs = list(ex.map(one, jobs))
            kv = [f.result() for f in kvf]
            hc = hf.result() if hf else None
        for r in kv:
            print(json.dumps(r), flush=True)
    ok = all(r["pass"] for r in runs) and all(r["pass"] for r in kv) and (hc is None or hc["pass"])
    rec = {
        "record": "V4.1 local K arbitration partition: transaction equivalence against the monolithic arbiter",
        "proposal": "docs/V41_KARB_LOCAL_PARTITION_PROPOSAL.md (Codex 796726ad, main 2bdb0c4a)",
        "sources": {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES},
        "simulator": subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0],
        "shape": {"NPC": NPC, "AW": AW, "TAGW": 16, "DW": 256, "model_mem_sectors": MEMW,
                  "regions": NPC // 4, "local_pcs_per_region": 4},
        "equivalence_basis": "transaction equivalence: each K tag's beats and each (PC, B tag)'s beats identical in "
                             "both arms and equal to a sequential golden (K in acceptance order, B per PC in order, "
                             "masked writes); final memory image identical and golden. B and K address disjoint "
                             "regions, as index keys and KV do on the die. Cross-PC K response order may differ.",
        "runs": runs, "kv_prefetch_bench": kv, "hash_steering_exhaustive": hc, "pass": ok,
        "added_uncontended_k_round_trip_cycles": sorted({r["first_k_latency_local"] - r["first_k_latency_mono"]
                                                         for r in runs if r["scenario"] == "k_single_read_idle"}),
        "pipe_added_uncontended_k_round_trip_cycles_by_region": {
            r["scenario"].rsplit("_", 1)[1]: r["first_k_latency_pipe"] - r["first_k_latency_mono"]
            for r in runs if r["scenario"].startswith("k_idle_region_") and r["k_rd_fence"] == 1},
    }
    if not a.quick:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
