#!/usr/bin/env python3
"""W11: quarter-per-stack ring layout -- writer, boundary migration, read-back.

Runs tb_w11_idx_ring_gate in Verilator (timed HBM models with backing
storage) in three configurations and writes results/rtl/w11_idx_ring_gate.json:

* ring_small: a small ring (C = 2,080 slots) so the stack rings WRAP many
  times: two users (0, 5) step from 0 to 8,223 keys each through the writer
  (257 boundary migrations each), read back at 1,040 / 4,127 / 6,200 / 7,777 /
  8,223 keys;
* full_shape: the spec ring (RSB 64, RTAIL 32: C = 65,568, 1,090 blocks per
  user per stack), 30-bit sector address, 10-bit user ID, the key region at the
  TOP of the 30-bit stack space for the model's 866 users; users 0, 481, 551
  and 865 prefilled to 262,080 keys (a 1M-context die slice), read back, then
  64 decode steps each (two migrations) to 262,144 and read back again;
* negative_no_migration: ring_small with the writer's migration disabled
  (scratch copy): must FAIL the read-back.

Every key, lane mask, last flag and refusal bit is checked; every HBM request
is checked against the active user's region by the bench's own 64-bit
arithmetic; the reader's sectors per scan are checked.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/w11_idx_ring_gate.json"
V = "rtl/hdc/v41x/"
SOURCES = [V + f for f in (
    "ot_hdc_v41x_idx_hbm.sv", "ot_hdc_v41x_idx_kstream.sv", "ot_hdc_v41x_idx_kstream_ring.sv",
    "ot_hdc_v41x_idx_quarter_join.sv", "ot_hdc_v41x_idx_ring_ranges.sv",
    "ot_hdc_v41x_idx_ring_kwr.sv")] + ["rtl/test/tb_w11_idx_ring_gate.sv"]
CPP = "rtl/test/w11_idx_ring_gate.cpp"
TOP = "tb_w11_idx_ring_gate"

MODEL_USERS = 866
SPEC = {"AW": 30, "HW": 23, "UW": 10, "RSB": 64, "RTAIL": 32}
UBLK_SPEC = 64 * 17 + 2
KB_TOP = (1 << 23) - MODEL_USERS * UBLK_SPEC      # key region ends at sector 2^30
RUNS = {
    "ring_small": {"NMAX": 8223, "CHK0": 1040, "CHK1": 4127, "CHK2": 6200, "CHK3": 7777},
    "full_shape": dict(SPEC, KB=KB_TOP, MEM_WORDS=1055017, NU=4, U0=0, U1=481, U2=551, U3=865,
                       PREFILL_N=262080, NMAX=262144, CHK0=262080, CHK1=0, CHK2=0, CHK3=0),
    "negative_no_migration": {"NMAX": 300, "CHK0": 65},
}
BENCH_DEFAULTS = {"AW": 28, "HW": 21, "UW": 10, "RSB": 2, "RTAIL": 32, "KB": 1000, "MEM_WORDS": 65521,
                  "NU": 2, "U0": 0, "U1": 5, "U2": 0, "U3": 0, "PREFILL_N": 0, "NMAX": 8223,
                  "CHK0": 65, "CHK1": 1040, "CHK2": 4127, "CHK3": 0, "WB": 128, "GA": 120, "CLK_PS": 967}

PASS = re.compile(r"W11_RING_PASS scans=(\d+) wrapped_stack_scans=(\d+) checked=(\d+) cycles=(\d+)")
WRITER = re.compile(r"W11_RING_WRITER keys=(\d+) migrations=(\d+) copied_sectors=(\d+)")
MON = re.compile(r"W11_RING_MON requests=(\d+) max_sector=(\d+)")
READ = re.compile(r"W11_RING_READ user=(\d+) n=(\d+) checked=(\d+) sectors=(\d+) wrap_n2=(\d+),(\d+),(\d+),(\d+) cycle=(\d+)")
STACK = re.compile(r"W11_RING_STACK s=(\d+) rd=(\d+) wr=(\d+) act=(\d+) conf=(\d+) ref=(\d+)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sources() -> dict[str, str]:
    return {p: sha(ROOT / p) for p in sorted({*SOURCES, CPP, "tools/w11_idx_ring_gate.py"})}


def ring_geometry(rsb: int, rtail: int) -> dict:
    c = rsb * 1024 + rtail
    ublk = rsb * 17 + (1 + (rtail + 63) // 64 if rtail else 0)
    return {"slots": c, "blocks_per_user_per_stack": ublk, "sectors_per_user_per_stack": ublk * 128,
            "bytes_per_user_per_stack": ublk * 4096}


def run(name: str, params: dict, work: Path) -> dict:
    src_root = ROOT
    if name == "negative_no_migration":
        src_root = work / "neg"
        for p in [*SOURCES, CPP]:
            (src_root / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / p, src_root / p)
        w = src_root / V / "ot_hdc_v41x_idx_ring_kwr.sv"
        text = w.read_text()
        old = "mig <= !c_op && c_count[4:0] == 0 && c_count >= 32;"
        assert text.count(old) == 1
        w.write_text(text.replace(old, "mig <= 1'b0;"))
    obj = work / f"obj_{name}"
    cmd = ["verilator", "--cc", "--exe", "--build", "-j", "4", "-Wno-fatal", "-Wno-WIDTH",
           "-Wno-UNOPTFLAT", "-Wno-WIDTHCONCAT", "--output-split", "20000", "--output-split-cfuncs",
           "10000", "--top-module", TOP, *[f"-G{k}={v}" for k, v in params.items()],
           "--Mdir", str(obj), *[str(src_root / s) for s in SOURCES], str(src_root / CPP)]
    t0 = time.perf_counter()
    b = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if b.returncode:
        raise RuntimeError(f"{name}: build failed\n{b.stdout[-2000:]}\n{b.stderr[-3000:]}")
    build_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    r = subprocess.run([str(obj / f"V{TOP}")], capture_output=True, text=True, timeout=14400)
    sim_s = time.perf_counter() - t0
    out = r.stdout + r.stderr
    m = PASS.search(out)
    row = {"name": name, "parameters": dict(BENCH_DEFAULTS, **params), "passed": bool(m and r.returncode == 0),
           "build_wall_seconds": round(build_s, 1), "simulation_wall_seconds": round(sim_s, 1)}
    cfg = row["parameters"]
    row["ring"] = ring_geometry(cfg["RSB"], cfg["RTAIL"])
    if not row["passed"]:
        row["failure"] = next((ln.strip() for ln in out.splitlines() if "Error" in ln), out[-400:])
        return row
    scans, wrapped, checked, cycles = map(int, m.groups())
    keys, migs, copied = map(int, WRITER.search(out).groups())
    reqs, max_sec = map(int, MON.search(out).groups())
    row.update({
        "scans": scans, "wrapped_stack_scans": wrapped, "checked_keys": checked, "cycles": cycles,
        "writer": {"keys": keys, "migrations": migs, "copied_sectors": copied},
        "hbm_requests_checked_in_region": reqs, "max_sector_address": max_sec,
        "max_sector_address_bits": max_sec.bit_length(),
        "reads": [{"user": int(g[0]), "n": int(g[1]), "checked": int(g[2]), "sectors": int(g[3]),
                   "wrap_keys_per_stack": [int(x) for x in g[4:8]]} for g in READ.findall(out)],
        "hbm_per_stack": [{"stack": int(g[0]), "reads": int(g[1]), "writes": int(g[2]),
                           "activates": int(g[3]), "row_conflicts": int(g[4]), "refreshes": int(g[5])}
                          for g in STACK.findall(out)],
    })
    return row


def main() -> None:
    pins = sources()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="w11-ring-") as td:
        with cf.ThreadPoolExecutor(3) as ex:
            rows = list(ex.map(lambda kv: run(kv[0], kv[1], Path(td)), RUNS.items()))
    assert sources() == pins, "a source changed while the gate ran"
    by = {r["name"]: r for r in rows}
    for r in rows:
        print(r["name"], "pass" if r["passed"] else "FAIL", r.get("cycles"), r.get("checked_keys"),
              r.get("failure", ""), flush=True)
    small, full, neg = by["ring_small"], by["full_shape"], by["negative_no_migration"]
    assert small["passed"] and full["passed"] and not neg["passed"]
    assert small["writer"]["migrations"] == 2 * (8223 // 32) and small["wrapped_stack_scans"] > 0
    assert full["max_sector_address"] < (1 << 30) and full["max_sector_address"] >= (1 << 29)
    assert {r["user"] for r in full["reads"]} == {0, 481, 551, 865}
    assert all(r["checked"] == r["n"] for r in small["reads"] + full["reads"])
    assert any(sum(r["wrap_keys_per_stack"]) for r in full["reads"])
    rec = {
        "schema": "opentallas.w11-idx-ring-gate.v1",
        "status": "pass",
        "git_head": head,
        "simulator": "Verilator " + subprocess.run(["verilator", "--version"], capture_output=True,
                                                   text=True).stdout.split()[1],
        "layout": {
            "placement": "stack q holds position quarter q (Qs = 8 floor(N/32)); key position p in ring slot "
                         "p mod C of the user's per-stack ring; ring = RSB super-blocks + one RTAIL-key tail "
                         "super-block; user region at block KB + user x UBLK on every stack; placement is a "
                         "function of (user, N) alone",
            "migration": "when N reaches a multiple of 32, positions [q Qs, q Qs + 8 q) move to stack q-1 "
                         "(q = 1..3; 48 keys, six 8-key groups); a key keeps its slot, so each group is 17 "
                         "sectors copied to the same addresses one stack down (from stack 3 or q+1 while "
                         "Qs < 24)",
            "spec": dict(SPEC, KB=KB_TOP, **ring_geometry(64, 32)),
            "why_tail": "the longest quarter of a 262,144-row die slice is 65,559 keys (N = 262,143: quarter 3 "
                        "= N - 3 Qs), so the ring needs 65,536 + 32 slots; a 32-key tail super-block costs "
                        "2 blocks (8 KB) per user per stack",
        },
        "cases": rows,
        "verdicts": {
            "ring_wrap_and_migration_exact": small["passed"],
            "full_shape_top_of_range_exact": full["passed"],
            "negative_control_detects_missing_migration": not neg["passed"],
        },
        "limitation": "Standalone gate: writer and readers own the HBM ports in alternate phases (no "
                      "concurrent writes during a scan); not integrated into ot_chip_v41x_die; behavioural "
                      "timed HBM with a modulo backing store (MEM_WORDS chosen so the four full-shape users' "
                      "regions do not alias; the address monitor checks full 30-bit addresses).",
        "sources_sha256": pins,
    }
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
