#!/usr/bin/env python3
"""W11: the core's key writer names keys at full ring capacity (C = 65,568).

Runs rtl/test/tb_w11_idx_ring_naming.sv (Verilator): ot_hdc_v41x_idx_pool_kwr
(RING = 1: the record names (region base block, position), no 1,024-row limit)
-> ot_hdc_v41x_idx_ring_port (WIDE_REC = 1, READ_FENCE = 1, as the die tile
instantiates them) -> four timed HBM stack models, read back by the pooled
adapter's ring reader (ring ranges, four ot_hdc_v41x_idx_kstream_ring, the
quarter join).  Two users with 10-bit ids (1 and 865), regions KB + user x 1,090
blocks at full shape (30-bit sectors, RSB 64, RTAIL 32):
  user 1:   decode steps at positions 1,020 .. 1,059 (ring slots past 1,024);
  user 865: decode steps at positions 65,560 .. 65,599 (the quarter-3 ring wraps
            at 65,568; scans read two segments).
Steps alternate between the users; after every step both users are scanned in
full, every key checked.  Writes results/rtl/w11_idx_ring_naming.json (new;
never overwritten).
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERILATOR = os.environ.get("OT_VERILATOR", str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
OUT = ROOT / "results/rtl/w11_idx_ring_naming.json"
V = "rtl/hdc/v41x/"
SOURCES = [V + f for f in (
    "ot_hdc_v41x_idx_hbm.sv", "ot_hdc_v41x_idx_kstream.sv", "ot_hdc_v41x_idx_kstream_ring.sv",
    "ot_hdc_v41x_idx_quarter_join.sv", "ot_hdc_v41x_idx_ring_ranges.sv", "ot_hdc_v41x_idx_ring_kwr.sv",
    "ot_hdc_v41x_idx_ring_port.sv", "ot_hdc_v41x_idx_pool_kwr.sv")] + ["rtl/test/tb_w11_idx_ring_naming.sv"]
CPP = "rtl/test/w11_idx_ring_naming.cpp"
TOP = "tb_w11_idx_ring_naming"
PARAMS = {"AW": 30, "HW": 23, "RSB": 64, "RTAIL": 32, "KB": 7444668, "MEM_WORDS": 1055017, "UA": 1, "UB": 865,
          "NA0": 1020, "NA1": 1060, "NB0": 65560, "NB1": 65600, "WB": 128, "GA": 120, "CLK_PS": 967}
NAMING = re.compile(r"W11_NAMING users=(\d+),(\d+) counts=(\d+),(\d+) steps=(\d+) writer_keys=(\d+) records=(\d+) "
                    r"migrations=(\d+) copied_sectors=(\d+)")
SCANS = re.compile(r"W11_NAMING_SCANS scans=(\d+) keys_checked=(\d+) wrap_scans=(\d+) steps_slot_past_1024=(\d+) "
                   r"fifo_highwater=(\d+)")
PASS = re.compile(r"W11_NAMING_PASS cycles=(\d+)")


def sources() -> dict[str, str]:
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
            for p in sorted({*SOURCES, CPP, "tools/w11_idx_ring_naming.py"})}


def run(work: Path, extra: dict | None = None) -> dict:
    obj = work / ("obj" if not extra else "obj_" + "_".join(f"{k}{v}" for k, v in extra.items()))
    cmd = [VERILATOR, "--cc", "--exe", "--build", "-j", "8", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNOPTFLAT",
           "-Wno-WIDTHCONCAT", "--output-split", "20000", "--output-split-cfuncs", "10000", "--top-module", TOP,
           *[f"-G{k}={v}" for k, v in dict(PARAMS, **(extra or {})).items()], "--Mdir", str(obj),
           *[str(ROOT / s) for s in SOURCES], str(ROOT / CPP)]
    b = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if b.returncode:
        raise RuntimeError(f"build failed\n{b.stderr[-3000:]}")
    t0 = time.perf_counter()
    r = subprocess.run([str(obj / f"V{TOP}")], capture_output=True, text=True, timeout=4 * 3600)
    out = r.stdout + r.stderr
    m, sc, mp = NAMING.search(out), SCANS.search(out), PASS.search(out)
    if r.returncode or not (m and sc and mp):
        return {"passed": False, "exit": r.returncode, "tail": out[-3000:]}
    ua, ub, na, nb, steps, wkeys, recs, migs, copied = map(int, m.groups())
    scans, checked, wraps, past, hw = map(int, sc.groups())
    return {"passed": True, "users": [ua, ub], "final_counts": [na, nb], "steps": steps, "writer_keys": wkeys,
            "port_records": recs, "migrations": migs, "copied_sectors": copied, "scans": scans,
            "keys_checked": checked, "scans_of_a_wrapped_ring": wraps, "steps_at_slot_past_1024": past,
            "record_fifo_highwater": hw, "cycles": int(mp.group(1)),
            "simulation_wall_seconds": round(time.perf_counter() - t0, 1),
            "simulation_log_sha256": hashlib.sha256(out.encode()).hexdigest()}


def main() -> int:
    pins = sources()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="w11-naming-") as td:
        with cf.ThreadPoolExecutor(2) as ex:
            fres, fneg = ex.submit(run, Path(td)), ex.submit(run, Path(td), {"WIDE": 0})
            res, neg = fres.result(), fneg.result()
    assert sources() == pins, "sources changed during the run"
    p = PARAMS
    C = p["RSB"] * 1024 + p["RTAIL"]
    ok = res["passed"] and res["steps"] == (p["NA1"] - p["NA0"]) + (p["NB1"] - p["NB0"]) == res["writer_keys"] \
        == res["port_records"] and res["scans_of_a_wrapped_ring"] > 0 and res["steps_at_slot_past_1024"] > 0 \
        and res["migrations"] > 0 and res["final_counts"] == [p["NA1"], p["NB1"]] and not neg["passed"]
    rec = {
        "schema": "opentallas.w11-idx-ring-naming.v1",
        "status": "pass" if ok else "fail",
        "git_head": head,
        "simulator": "Verilator " + subprocess.run([VERILATOR, "--version"], capture_output=True,
                                                   text=True).stdout.split()[1],
        "parameters": p,
        "ring": {"slots_per_user_per_stack": C, "blocks_per_region": p["RSB"] * 17 + 1 + (p["RTAIL"] + 63) // 64,
                 "user_region_base_block": "KB + user x 1,090"},
        "result": res,
        "negative_control": {"change": "WIDE = 0: the port decodes the legacy record (region block = w_ssec / 128, "
                                       "row = {w_ssec mod 128, w_sslot} < 1,024)", "must_fail": True,
                             "passed": neg["passed"], "failure_tail": neg.get("tail", "")[-600:]},
        "checks": ("every record's (region base block, position) against the step's user and count; after every "
                   "step both users scanned in full (all four stacks, the quarter join), every key compared: "
                   "bench-placed keys with their generator, written keys with the writer's record"),
        "claim_boundary": ("The die's ring writer path (ot_hdc_v41x_idx_pool_kwr RING = 1 -> "
                           "ot_hdc_v41x_idx_ring_port WIDE_REC = 1) and the pooled adapter's ring reader arm, "
                           "instantiated as the die does, at full ring capacity with timed HBM models; the key "
                           "elements come from the bench (the SU store the core issues), not a decode step: the "
                           "reduced vehicle provisions 128 positions (hdc_isa_v41.POS_MAX), so no die token reaches "
                           "a slot past 1,024. The die-token evidence at full capacity is "
                           "results/rtl/w11_die_idx_ring_mu_gate.json."),
        "sources_sha256": pins,
    }
    if OUT.exists():
        raise SystemExit(f"{OUT} exists; records are never overwritten")
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(rec["status"], {k: res.get(k) for k in ("steps", "keys_checked", "scans_of_a_wrapped_ring", "cycles")})
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
