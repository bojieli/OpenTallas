#!/usr/bin/env python3
"""Lint, build and run the per-die memory system ot_gpu_memsys (xbar + L2 slices + HBM partitions) and write
results/rtl/hbm_system_rtl_20261003/memsys.json (schema opentallas.gpu_sys.memsys.v1).

    python3 tools/gpu_sys/run_memsys.py [--ntx 20000] [--seeds 1] [--out ...] [--build-dir DIR]

Steps: (1) verilator --lint-only -Wall of every new module at ENABLE=0 and 1 (partition and memsys also USE_W2=1);
only UNUSED* warnings are tolerated (the ENABLE=0 branch leaves inputs unused), anything else (IMPLICIT, UNDRIVEN,
MULTIDRIVEN, WIDTH, comb loops) fails.  Third-party reused sources are waived by rtl/gpu_sys/ot_gpu_memsys_lint.vlt.
(2) random initial memory -> per-partition $readmemh images via tools/gpu_sys/mem_image.py (the placement rule under
test) and a die-global golden.  (3) Verilator --binary --timing bench rtl/test/gpu_sys/tb_gpu_memsys.sv for USE_W2=0
and USE_W2=1.  Exits nonzero on any FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import mem_image  # noqa: E402

VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
VLT = ROOT / "rtl/gpu_sys/ot_gpu_memsys_lint.vlt"
NEW = {
    "ot_gpu_xbar": ROOT / "rtl/gpu_sys/ot_gpu_xbar.sv",
    "ot_gpu_l2_slice": ROOT / "rtl/gpu_sys/ot_gpu_l2_slice.sv",
    "ot_gpu_hbm_partition": ROOT / "rtl/gpu_sys/ot_gpu_hbm_partition.sv",
    "ot_gpu_memsys": ROOT / "rtl/gpu_sys/ot_gpu_memsys.sv",
}
MODEL = ROOT / "rtl/hdc/kv/ot_hdc_hbm_model.sv"
W2 = ROOT / "rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv"
W2_TB = ROOT / "rtl/test/w2_nc6_completion_20261003/tb.sv"
BENCH = ROOT / "rtl/test/gpu_sys/tb_gpu_memsys.sv"
RTL = [*NEW.values(), MODEL, W2]
TOOLS = [HERE / "mem_image.py", Path(__file__).resolve()]
DEFAULT_OUT = ROOT / "results/rtl/hbm_system_rtl_20261003/memsys.json"
SCHEMA = "opentallas.gpu_sys.memsys.v1"
P = dict(NC=4, NS=2, NPC=2, MEM_WORDS=16384, OSD=64, WIN=4096, BWN=8192, LATN=64, CLK_PS=1000, L2_BYTES=32768)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def lint(top: str, enable: int, use_w2: int | None) -> dict:
    g = [f"-GENABLE={enable}"] + ([f"-GUSE_W2={use_w2}"] if use_w2 is not None else [])
    cmd = [str(VERILATOR), "--lint-only", "-Wall", "--top-module", top, *g, str(VLT), *map(str, RTL)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    msgs = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith("%")]
    warns = [ln for ln in msgs if ln.startswith("%Warning-")]
    errors = [ln for ln in msgs if ln.startswith("%Error") and "Exiting due to" not in ln]
    waived = [ln for ln in warns if re.match(r"%Warning-UNUSED", ln)]
    bad = [ln for ln in warns if ln not in waived] + errors
    return {"top": top, "enable": enable, "use_w2": use_w2, "pass": not bad,
            "waived_unused": [w.split(": ", 1)[-1] for w in waived], "violations": bad}


# Mutants: each must be killed (bench FAIL) to show the checks bite.  (file key, exact old text, new text)
MUTANTS = {
    "l2_no_same_sector_hazard": ("ot_gpu_l2_slice", "if (e_miss[i] && e_sec[i] == n_sec) n_haz = 1'b1;",
                                 "if (1 == 0) n_haz = 1'b1;"),
    "l2_no_update_on_write_hit": ("ot_gpu_l2_slice", "c_dat[{n_idx, n_sub}] <= n_merged;", ""),
    "partition_rmw_merge_inverted": ("ot_gpu_hbm_partition",
                                     "merged[b*8 +: 8] = rmw_wstrb[b] ? rmw_wdata[b*8 +: 8]",
                                     "merged[b*8 +: 8] = !rmw_wstrb[b] ? rmw_wdata[b*8 +: 8]"),
}


def build(bdir: Path, use_w2: int, ntx: int, mutant: str | None = None) -> Path:
    obj = bdir / (f"obj_w2_{use_w2}" if mutant is None else f"obj_mut_{mutant}")
    rtl = list(RTL)
    if mutant is not None:
        key, old, new = MUTANTS[mutant]
        src = NEW[key].read_text()
        if src.count(old) != 1:
            raise SystemExit(f"mutant {mutant}: anchor not found exactly once")
        mp = bdir / f"mut_{mutant}" / NEW[key].name
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text(src.replace(old, new))
        rtl = [mp if p == NEW[key] else p for p in rtl]
    g = [f"-GUSE_W2={use_w2}", f"-GNTX={ntx}"] + [f"-G{k}={P[k]}" for k in
                                                  ("NC", "NS", "NPC", "MEM_WORDS", "OSD", "WIN", "BWN", "LATN")]
    cmd = [str(VERILATOR), "--binary", "--timing", "-j", "2", "-Wno-fatal", "-Wno-WIDTH", "--top-module",
           "tb_gpu_memsys", "-Mdir", str(obj), *g, str(BENCH), *map(str, rtl)]
    r = subprocess.run(cmd, cwd=bdir, capture_output=True, text=True, env={**os.environ, "MAKEFLAGS": "-j2"})
    (bdir / f"build_{obj.name}.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"verilator build failed, see {bdir / f'build_{obj.name}.log'}")
    return obj / "Vtb_gpu_memsys"


def run(exe: Path, bdir: Path, seed: int, prefix: Path, golden: Path) -> dict:
    t = time.time()
    r = subprocess.run([str(exe), f"+golden={golden}", f"+gpu_sys_mem_prefix={prefix}", f"+verilator+seed+{seed}",
                        f"+seed={seed}"], cwd=bdir, capture_output=True, text=True)
    out = r.stdout + r.stderr
    (bdir / f"{exe.parent.name}_seed{seed}.log").write_text(out)
    res = {}
    for ln in out.splitlines():
        m = re.match(r"RESULT (\S+) (\S+)", ln)
        if m:
            v = m.group(2)
            res[m.group(1)] = float(v) if "." in v else int(v)
    res["pass"] = ("PASS tb_gpu_memsys" in out) and r.returncode == 0 and res.get("errors", 1) == 0
    res["error_lines"] = [ln for ln in out.splitlines() if ln.startswith("ERROR")][:20]
    res["wall_s"] = round(time.time() - t, 2)
    return res


def derive(r: dict) -> dict:
    ns = P["NS"]
    d = {}
    if r.get("bw1_cycles"):
        d["seq_read_1client_sectors_per_cycle_total"] = r["bw1_sectors"] / r["bw1_cycles"]
        d["seq_read_1client_sectors_per_cycle_per_partition"] = r["bw1_sectors"] / r["bw1_cycles"] / ns
    if r.get("bwN_cycles"):
        d["seq_read_allclients_sectors_per_cycle_total"] = r["bwN_sectors"] / r["bwN_cycles"]
        d["seq_read_allclients_sectors_per_cycle_per_partition"] = r["bwN_sectors"] / r["bwN_cycles"] / ns
        d["seq_read_allclients_GBps_per_partition_at_clk_mem"] = \
            r["bwN_sectors"] * 32 / (r["bwN_cycles"] * P["CLK_PS"] * 1e-12) / 1e9 / ns
    return {k: round(v, 4) for k, v in d.items()}


W2_VERDICT_FIXED = {
    "component": str(W2.relative_to(ROOT)),
    "contract_bench": str(W2_TB.relative_to(ROOT)),
    "fits": True,
    "placement": "inside ot_gpu_hbm_partition between the front end (W2 client 0; clients 1..5 tied idle) and the "
                 "model adapter (W2 provider), instantiated unmodified with OPT_EXACT=1 behind USE_W2 (default 0)",
    "adaptation": [
        "geometry is locked by $fatal (NC6/MAX_OUT16/CTAGW32/GENW4/SIDW3/PTAGW35/AW34): the partition keeps the "
        "default parameters, zero-extends its 27-LNS-bit sector address to AW 34 and its (TW+1)-bit front-end tag "
        "to CTAGW 32; the model runs with TAGW 35 so the provider tag {client, tag} round-trips unchanged",
        "generation is tied to 0: the memory-system tags (L2 completion-queue indices) are reused only after their "
        "response, which is the W2 duplicate-free condition with a constant generation",
        "W2 has no byte strobes, so the exact read-modify-write of partial writes stays in front of it; W2 only "
        "sees whole-sector reads and writes",
        "the HBM model has no write response: the adapter's acceptance-time write ack (the point at which the "
        "write is ordered before every later read of its sector) is W2's provider write-done",
        "admission_stop=0, rearm_v=0, provider_fenced=reset_fenced=1 (no runtime rearm/fence use); W2 resets "
        "asynchronously on the shared clk_mem reset (SYNCASYNCNET waived)",
    ],
    "cost": "W2 holds one request (holder register) and one read response stage: at most one request per two "
            "cycles and one read response per two cycles per partition, and MAX_OUT=16 outstanding per client: see "
            "the use_w2=1 bandwidth/latency figures against use_w2=0",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--build-dir", type=Path, default=None)
    ap.add_argument("--ntx", type=int, default=20000)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1])
    ap.add_argument("--skip-lint", action="store_true")
    ap.add_argument("--skip-mutants", action="store_true")
    a = ap.parse_args()

    ok = True
    errs = mem_image.self_check()
    print(f"{'FAIL' if errs else 'PASS'} mem_image self-check {errs or ''}")
    ok &= not errs

    lints = []
    if not a.skip_lint:
        for top in NEW:
            for en in (0, 1):
                for w in ((0, 1) if top in ("ot_gpu_hbm_partition", "ot_gpu_memsys") else (None,)):
                    L = lint(top, en, w)
                    lints.append(L)
                    print(f"{'PASS' if L['pass'] else 'FAIL'} lint {top} ENABLE={en} USE_W2={w} {L['violations'] or ''}")
                    ok &= L["pass"]

    bdir = a.build_dir or Path(tempfile.mkdtemp(prefix="gpu_memsys_"))
    bdir.mkdir(parents=True, exist_ok=True)
    gs = P["WIN"] + P["BWN"] + P["LATN"]
    sims = []
    for use_w2 in (0, 1):
        exe = build(bdir, use_w2, a.ntx)
        for seed in a.seeds:
            rng = np.random.default_rng(1000 + seed)
            data = rng.integers(0, 256, gs * 32, dtype=np.uint8)
            files = mem_image.write_images({0: data}, P["NS"], P["MEM_WORDS"], bdir / f"img_s{seed}", "mem")
            golden = mem_image.write_die_sectors({0: data}, gs, bdir / f"golden_s{seed}.hex")
            r = run(exe, bdir, seed, bdir / f"img_s{seed}" / "mem", Path(golden))
            r.update(derive(r))
            r.update(use_w2=use_w2, seed=seed, image_files=[Path(f).name for f in files])
            sims.append(r)
            print(f"{'PASS' if r['pass'] else 'FAIL'} sim USE_W2={use_w2} seed={seed} "
                  f"requests={r.get('total_requests')} errors={r.get('errors')} "
                  f"bw/partition={r.get('seq_read_allclients_sectors_per_cycle_per_partition')} "
                  f"miss={r.get('lat_read_miss_cycles')} {r['error_lines'][:3]}")
            ok &= r["pass"] and r.get("random_requests", 0) >= min(a.ntx, 20000)

    mutants = []
    if not a.skip_mutants:
        seed = a.seeds[0]
        for name in MUTANTS:
            exe = build(bdir, 0, a.ntx, name)
            r = run(exe, bdir, seed, bdir / f"img_s{seed}" / "mem", bdir / f"golden_s{seed}.hex")
            m = {"mutant": name, "killed": not r["pass"], "errors": r.get("errors"),
                 "first_errors": r["error_lines"][:3]}
            mutants.append(m)
            print(f"{'PASS' if m['killed'] else 'FAIL'} mutant {name} killed={m['killed']} errors={m['errors']}")
            ok &= m["killed"]

    w2 = dict(W2_VERDICT_FIXED)
    w2_runs = [s for s in sims if s["use_w2"] == 1]
    w2["functional_pass"] = bool(w2_runs) and all(s["pass"] for s in w2_runs)

    def pick(s):
        return {k: s.get(k) for k in ("seq_read_1client_sectors_per_cycle_per_partition",
                                      "seq_read_allclients_sectors_per_cycle_per_partition",
                                      "lat_read_miss_cycles", "lat_read_hit_cycles",
                                      "lat_write_full_miss_ack_cycles", "lat_write_partial_miss_ack_cycles",
                                      "random_cycles")}
    base = [s for s in sims if s["use_w2"] == 0]
    if base and w2_runs:
        w2["measured"] = {"use_w2_0": pick(base[0]), "use_w2_1": pick(w2_runs[0])}
    w2["verdict"] = ("PASS: fits unmodified and is exact in the memory-system bench; default stays USE_W2=0 "
                     "(it costs bandwidth/latency, see measured)") if w2["functional_pass"] else "FAIL"

    rec = {
        "schema": SCHEMA,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": "PASS" if ok else "FAIL",
        "simulator": subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip(),
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in [*RTL, VLT, BENCH, W2_TB, *TOOLS]},
        "parameters": P,
        "interfaces": {
            "mreq": "req_v/req_rdy/req_we/req_addr[31:0] byte (sector aligned)/req_wdata[255:0]/req_wstrb[31:0]/"
                    "req_tag; rsp_v/rsp_rdy/rsp_tag/rsp_we/rsp_data[255:0]",
            "ot_gpu_memsys": "#(ENABLE=0, NC=4, NS=2, NPC=2, MEM_WORDS=16384, CLK_PS=1000, L2_BYTES=32768, OSD=64, "
                             "USE_W2=0, DIE_IDX=-1, IMAGE_PREFIX=\"\") (clk, rst_n, req_v[NC], req_rdy[NC], req_we[NC], "
                             "req_addr[NC*32], req_wdata[NC*256], req_wstrb[NC*32], req_tag[NC*16], rsp_v[NC], "
                             "rsp_rdy[NC], rsp_tag[NC*16], rsp_we[NC], rsp_data[NC*256], fault); client c at [c*W +: W]",
            "ot_gpu_xbar": "#(ENABLE, NC, NS, TW=16) slice tag = {client, tag} (TW+log2 NC bits)",
            "ot_gpu_l2_slice": "#(ENABLE, NS, TW, L2_BYTES, OSD) up MREQ (TW) + down MREQ (log2 OSD tag) + stat_* + fault",
            "ot_gpu_hbm_partition": "#(ENABLE, NS, TW, NPC, MEM_WORDS, CLK_PS, USE_W2, PART_IDX, DIE_IDX, IMAGE_PREFIX) "
                                    "MREQ + fault",
        },
        "design": {
            "xbar": "combinational routing, slice = addr[7 +: log2 NS], round-robin per slice (requests) and per "
                    "client (responses), full valid/ready",
            "l2_slice": "sectored direct-mapped (128 B lines, 4 x 32 B sectors, tag per line, valid per sector), "
                        "write-through, update on write hit (whole merged sector written through), no allocate on "
                        "write miss, read miss fills one sector; in order, NON-blocking: up to OSD outstanding misses/"
                        "writes in an in-order completion queue; stalls only on a same-sector outstanding read miss "
                        "or a same-line fill this cycle; responses retire in acceptance order (head-of-line)",
            "partition": "slice bits removed, sector = local>>5; reads and full writes pass at one per cycle; "
                         "partial writes by an exact read-modify-write that blocks the partition front end until "
                         "the merged write is accepted; write ack at model acceptance (ordered before any later "
                         "same-sector read by the model's same-sector rule); NPC response ports merged round-robin",
        },
        "memory_image": {
            "array": "<memsys>.g_on.g_s[s].u_part.g_on.u_model.mem  (reg [255:0] mem [0:MEM_WORDS-1])",
            "mapping": "X -> slice (X>>7)&(NS-1); local {X[31:7+log2 NS], X[6:0]}; sector local>>5; word "
                       "sector % MEM_WORDS (helper refuses sector >= MEM_WORDS); byte lane X[4:0] = bits [8*lane +: 8]",
            "helper": "tools/gpu_sys/mem_image.py write_images(mem_map, ns, mem_words, out_dir, prefix='mem', die=None) "
                      "-> ['<out_dir>/<prefix>_p0.hex', ...] (die=d: '<prefix>_d<d>_p<s>.hex'; zero-filled, one per "
                      "partition); mem_map = {die-global byte address: bytes | uint8 ndarray}",
            "loading": "+gpu_sys_mem_prefix=<out_dir>/<prefix> plusarg, else parameter IMAGE_PREFIX; each partition "
                       "zeroes its array then $readmemh(\"<prefix>_p<slice>.hex\") (DIE_IDX=-1) or "
                       "\"<prefix>_d<DIE_IDX>_p<slice>.hex\" (DIE_IDX>=0)",
            "verilog_snippet": mem_image.VERILOG_SNIPPET,
        },
        "lint": lints,
        "simulations": sims,
        "mutants": mutants,
        "w2": w2,
        "limits": [
            "responses leave each slice in acceptance order (head-of-line blocking behind an older miss)",
            "a partial write that misses L2 serialises its partition for one read latency (exact RMW)",
            "one request per cycle per slice and per partition; the model's NPC pseudo-channels can take ~NPC/1.024 "
            "sectors per ns",
            "sequential-read bandwidth with NC streams is bound by the model's DRAM row/bank behaviour, not by "
            "the slice's outstanding limit: OSD=128 measured 0.546 sectors/cycle/partition against 0.616 at OSD=64 "
            "(same bench, seed 1), so OSD stays 64",
            "one client alone issues at most one request per cycle across all slices (0.5 sectors/cycle/partition "
            "ceiling at NS=2)",
            "behavioural model only (timing-faithful DRAM, not synthesisable); no ECC on the HBM path modelled",
        ],
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{rec['verdict']} memsys -> {a.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
