#!/usr/bin/env python3
"""W11: the quarter-per-stack ring key layout inside the adopted V4.1 die top.

ot_chip_v41x_die with IDX_RING = 1 (opt-in): the core's key writer records go
through ot_hdc_v41x_idx_ring_port (decode steps + boundary migration, K-port
arbitration) and the pooled indexer scans with four ot_hdc_v41x_idx_kstream_ring
streams and ot_hdc_v41x_idx_quarter_join.  One reduced DeepSeek-V4.1 decode
step through the die (bench rtl/test/tb_chip_v41x_die_ring.sv, the die smoke's
checks: every logit, the whole vector memory, the whole KV cache against the
ISA model, token against the golden), on two images:

* pos7:  the adopted smoke's step (position 7): every region holds < 32 keys, so
         all keys sit on stack 3 (quarters 0-2 empty);
* ctx64: --context 64, the step at position 63 where the index top-k selects:
         ratio-1 regions go 63 -> 64 keys (a migration: 48 keys move a stack down)
         and are scanned from all four stacks.

Each image runs twice: RING = 1 and RING = 0 (the adopted replicated path, the
reference on the same image).  Writes results/rtl/w11_die_idx_ring_gate.json.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_chip_v41x_die_smoke as ds  # noqa: E402

core = ds.core
OUT = ROOT / "results/rtl/w11_die_idx_ring_gate.json"
TB = ROOT / "rtl/test/tb_chip_v41x_die_ring.sv"
HARNESS = ROOT / "rtl/test/chip_v41x_die_ring_harness.cpp"
RING_RTL = [ROOT / f"rtl/hdc/v41x/{n}.sv" for n in (
    "ot_hdc_v41x_idx_kstream_ring", "ot_hdc_v41x_idx_ring_ranges", "ot_hdc_v41x_idx_ring_kwr",
    "ot_hdc_v41x_idx_ring_port", "ot_hdc_v41x_idx_quarter_join")]
IMAGES = {"pos7": ("--hbm",), "ctx64": ("--hbm", "--context", "64")}
IDXRING = re.compile(r"IDXRING regions=(\d+) preloaded_keys=(\d+) max_region_keys=(\d+) migrations=(\d+) "
                     r"copied_sectors=(\d+)")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def src_list(build: bool) -> list[Path]:
    out = ds.sources("dpi", build=build)
    return out + [p for p in RING_RTL if p not in out]


def build(obj: Path, ring: int) -> Path:
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [ds.VERILATOR, "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-IMPORTSTAR", "-Wno-MODDUP", "-Wno-TIMESCALEMOD", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT",
           "--top-module", "tb_chip_v41x_die_ring", f"-GRING={ring}", "-Mdir", str(obj), f"-I{core.SVH.parent}",
           str(core.VLT), *map(str, src_list(True)), str(TB), str(HARNESS), "-CFLAGS", "-O1", "-j", "8"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"verilator build failed (RING={ring}):\n{r.stdout[-3000:]}\n{r.stderr[-4000:]}")
    return obj / "Vtb_chip_v41x_die_ring"


def used_sources(obj: Path) -> list[Path]:
    """Every source file Verilator read for this build (its dependency file)."""
    dep = next(obj.glob("*__ver.d")).read_text().replace("\\\n", " ")
    files = [Path(f) for f in dep.split(":", 1)[1].split() if f.endswith((".sv", ".v", ".svh", ".vlt", ".cpp"))]
    return sorted({f.resolve() for f in files if str(f.resolve()).startswith(str(ROOT))}, key=str)


def run(exe: Path, img: Path, ring: int) -> dict:
    args = (img / "run.args").read_text().split()
    t0 = time.perf_counter()
    sim = subprocess.run([str(exe), f"+DIR={img}", *args, "+QRATE=32"], capture_output=True, text=True,
                         timeout=6 * 3600, cwd=ROOT)
    wall = time.perf_counter() - t0
    log = sim.stdout + sim.stderr
    m, wr = core.SINGLE.search(log), core.IDXHBMWR.search(log)
    if m is None or wr is None:
        return {"status": "fail", "simulation_exit": sim.returncode, "tail": log[-3000:]}
    names = ("input_token", "position", "next_token", "isa_next_token", "cycles", "fault", "logit_mismatches",
             "vm_mismatches", "kv_mismatches")
    step = dict(zip(names, map(int, m.groups())))
    writer = dict(zip(("records", "sector_writes", "fifo_highwater", "read_stall_cycles", "writer_stall_cycles",
                       "refresh_events", "refpb_mode"), map(int, wr.groups())))
    cnt = core.counters(log)
    die = re.search(r"DIE fault=([01]+)", log)
    rec = {"step": step, "index_key_hbm_writer": writer, "unit_counters": cnt,
           "die_fault_bits": die.group(1) if die else None, "simulation_exit": sim.returncode,
           "simulation_wall_seconds": round(wall, 1),
           "simulation_log_sha256": hashlib.sha256(log.encode()).hexdigest(), "simulation_tail": log[-1800:]}
    ok = (sim.returncode == 0 and "PASS" in log and step["next_token"] == step["isa_next_token"] and
          step["fault"] == 0 and step["logit_mismatches"] == step["vm_mismatches"] == step["kv_mismatches"] == 0
          and die is not None and int(die.group(1), 2) == 0 and cnt.get("idx", {}).get("ops", 0) > 0
          and writer["records"] == cnt.get("idx_kwr", {}).get("ops", -1))
    if ring:
        g = IDXRING.search(log)
        ok = ok and g is not None
        if g:
            rec["ring"] = dict(zip(("regions", "preloaded_keys", "max_region_keys", "migrations", "copied_sectors"),
                                   map(int, g.groups())))
            ok = ok and rec["ring"]["copied_sectors"] == 102 * rec["ring"]["migrations"]
    rec["status"] = "pass" if ok else "fail"
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/claude-1000/w11s/rd/die_gate"))
    ap.add_argument("--reuse-images", action="store_true")
    ap.add_argument("--reuse-executables", action="store_true",
                    help="use <scratch>/obj_ring{0,1} as built from this tree (every source it read must predate it)")
    a = ap.parse_args()
    ds.setup("dpi")
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    pins = {ds.rel(p): sha(p) for p in sorted(set(src_list(True)), key=str) +
            [core.SVH, core.VLT, TB, HARNESS, Path(__file__), ROOT / "tools/rtl_chip_v41x_die_smoke.py",
             ROOT / "tools/rtl_hdc_v41x_decode_campaign.py", ROOT / "tools/hdc_program_v41.py",
             ROOT / "tools/hdc_images_v41x.py"]}
    imgs = {k: a.scratch / f"img_{k}" for k in IMAGES}
    with cf.ThreadPoolExecutor(4) as ex:
        futs = {}
        if not a.reuse_images:
            futs.update({ex.submit(core.images, imgs[k], *v): k for k, v in IMAGES.items()})
        exes = {r: ex.submit(lambda rr: (a.scratch / f"obj_ring{rr}" / "Vtb_chip_v41x_die_ring")
                             if a.reuse_executables else build(a.scratch / f"obj_ring{rr}", rr), r) for r in (0, 1)}
        for f in futs:
            f.result()
        exes = {r: f.result() for r, f in exes.items()}
    used = sorted({p for r in (0, 1) for p in used_sources(a.scratch / f"obj_ring{r}")}, key=str)
    for r in (0, 1):
        built = exes[r].stat().st_mtime
        stale = [ds.rel(p) for p in used_sources(a.scratch / f"obj_ring{r}") if p.stat().st_mtime > built]
        assert not stale, f"sources newer than the RING={r} executable: {stale}"
    pins.update({ds.rel(p): sha(p) for p in used})
    jobs = [(k, r) for k in IMAGES for r in (1, 0)]
    with cf.ThreadPoolExecutor(4) as ex:
        res = dict(zip(jobs, ex.map(lambda kr: run(exes[kr[1]], imgs[kr[0]], kr[1]), jobs)))
    assert {ds.rel(p): sha(p) for p in sorted(set(src_list(True)), key=str)} == \
        {k: v for k, v in pins.items() if k in {ds.rel(p) for p in src_list(True)}}, "sources changed during the run"
    cases = []
    for k in IMAGES:
        r1, r0 = res[(k, 1)], res[(k, 0)]
        same = (r1.get("status") == "pass" and r0.get("status") == "pass" and
                r1["step"]["next_token"] == r0["step"]["next_token"])
        cases.append({"image": k, "image_args": list(IMAGES[k]),
                      "image_sha256": {n: sha(imgs[k] / n) for n in sorted(os.listdir(imgs[k]))
                                       if n.endswith((".hex", ".json", ".args"))},
                      "ring": r1, "replicated_reference": r0, "token_identical": same,
                      "cycle_delta_ring_minus_replicated": (r1["step"]["cycles"] - r0["step"]["cycles"]) if same else None})
        print(k, r1.get("status"), r0.get("status"), r1.get("step"), r1.get("ring"), flush=True)
    ok = all(c["ring"]["status"] == "pass" and c["replicated_reference"]["status"] == "pass" and c["token_identical"]
             for c in cases)
    ctx = next(c for c in cases if c["image"] == "ctx64")
    ok = ok and ctx["ring"]["ring"]["migrations"] > 0
    rec = {
        "schema": "opentallas.w11-die-idx-ring-gate.v1",
        "status": "pass" if ok else "fail",
        "git_head": head,
        "simulator": ds.tool_version(ds.VERILATOR),
        "configuration": {"die": "ot_chip_v41x_die", "IDX_RING": 1, "IDX_RING_RSB": 1, "IDX_RING_RTAIL": 0,
                          "X_IDX": 2, "units": list(core.X_UNITS), "W_HBM": 1, "KV_HBM": 1, "fp": "dpi",
                          "ring_port_read_fence": 1},
        "cases": cases,
        "claim_boundary": ("Reduced V4.1 single decode step through the die top with the ring key layout: key "
                           "writes from the core's writer placed by ot_hdc_v41x_idx_ring_port (decode step + "
                           "migration), scanned by the pooled adapter's ring readers and join, scored and selected; "
                           "bit-exact against the ISA model and token-identical to the replicated path on the same "
                           "image. Regions are one-super-block rings (C = 1,024), named by the core's writer as "
                           "(region base block, position) (ot_hdc_v41x_idx_pool_kwr RING = 1). The preloaded (golden-prefilled) keys are placed by the bench in ring layout. "
                           "The ring port holds reads while its writer is busy (READ_FENCE = 1, the legacy rule)."),
        "limits": ["one-super-block rings (C = 1,024) and one user (IDX_RING_MU = 0) in this gate; full ring "
                   "capacity (C = 65,568) and two interleaved users are results/rtl/w11_die_idx_ring_mu_gate.json, "
                   "ring slots past 1,024 and the wrap results/rtl/w11_idx_ring_naming.json"],
        "sources_sha256": pins,
    }
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(rec["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
