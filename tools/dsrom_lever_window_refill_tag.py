#!/usr/bin/env python3
"""Lever item 2: WINDOW_REFILL_CREDITS=8 refill-tag owner collision at epoch 512, and its default-off fix.

    python3 tools/dsrom_lever_window_refill_tag.py --scratch DIR \
        [--out results/rtl/dsrom_system_rtl_20261003/levers/window_refill_tag.json]

DUT: rtl/dsrom_sys/levers/ot_dsrom_window_kv_prefetch_lv.sv (successor of the pinned, unchanged
rtl/chip/ot_chip_v41x_window_kv_prefetch.sv; EPOCH_SAFE default 0).  Bench:
rtl/test/dsrom_sys/levers/tb_window_refill_tag.sv (five arms, one stimulus, real ot_chip_v41x_kv_rope_reqmux +
ot_chip_v41x_kv_reqmux owner path, bounded out-of-order memory).  Simulator: Icarus (iverilog -g2012); lint:
Verilator 5.050 --lint-only -Wall on the successor at both EPOCH_SAFE values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHIP = ROOT / "rtl/chip"
ORIG = [CHIP / f"ot_chip_v41x_{n}.sv" for n in ("window_kv_prefetch", "window_row_codec", "window_stage4",
                                                "kv_rope_reqmux", "kv_reqmux")]
SUCC = ROOT / "rtl/dsrom_sys/levers/ot_dsrom_window_kv_prefetch_lv.sv"
TB = ROOT / "rtl/test/dsrom_sys/levers/tb_window_refill_tag.sv"
VERILATOR = os.environ.get("OT_VERILATOR", os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
# pins of the originals as recorded by the epoch-contract record (byte-identity of pinned files)
PINNED = {"rtl/chip/ot_chip_v41x_window_kv_prefetch.sv": "5a0cf8fb49fd259a7ad48df1e8b8f0e48abf69b28116802a46438a4322a71062",
          "rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv": "2c1ff0a202a2f26c8bc7d46d498839e40a31ee1d1cfbd52d5c1869b8c523f94c",
          "rtl/chip/ot_chip_v41x_kv_reqmux.sv": "eef51eba3f64cc95b479fe6acc21f1b901296f6e980b27957af94492db8bc66c"}


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(cmd, cwd, log: Path):
    t0 = time.monotonic()
    p = subprocess.run(list(map(str, cmd)), cwd=cwd, capture_output=True, text=True)
    log.write_text(p.stdout + p.stderr)
    return p, round(time.monotonic() - t0, 2)


def fields(line: str) -> dict:
    return {k: (int(v, 16) if k.endswith("tag") else int(v)) for k, v in re.findall(r"(\w+)=([0-9a-fA-F]+)", line)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results/rtl/dsrom_system_rtl_20261003/levers/window_refill_tag.json")
    ap.add_argument("--refills", type=int, default=600)
    a = ap.parse_args()
    w = a.scratch.resolve()
    w.mkdir(parents=True, exist_ok=True)
    srcs = [*ORIG, SUCC, TB, Path(__file__).resolve()]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in srcs}
    checks, cmds = {}, {}
    checks["pinned_originals_byte_identical"] = all(pins[k] == v for k, v in PINNED.items())

    # lint of the successor at both settings
    lint = {}
    for es in (0, 1):
        for cred in (1, 8):
            cmd = [VERILATOR, "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "--top-module",
                   "ot_dsrom_window_kv_prefetch_lv", f"-GEPOCH_SAFE={es}", f"-GREFILL_CREDITS={cred}",
                   CHIP / "ot_chip_v41x_window_row_codec.sv", CHIP / "ot_chip_v41x_window_stage4.sv", SUCC]
            p, s = run(cmd, w, w / f"lint_es{es}_c{cred}.log")
            kinds = sorted(set(re.findall(r"%(?:Warning|Error)-(\w+)", p.stdout + p.stderr)))
            lint[f"EPOCH_SAFE={es},REFILL_CREDITS={cred}"] = dict(returncode=p.returncode, warning_kinds=kinds)
            cmds[f"lint_es{es}_c{cred}"] = " ".join(map(str, cmd))
    # the original under the same lint (reference: any warning the successor shows must be inherited)
    cmd = [VERILATOR, "--lint-only", "-Wall", "-Wno-DECLFILENAME", "-Wno-UNUSED", "--top-module",
           "ot_chip_v41x_window_kv_prefetch", "-GREFILL_CREDITS=8", *ORIG[:3]]
    p, s = run(cmd, w, w / "lint_orig_c8.log")
    lint["original,REFILL_CREDITS=8"] = dict(returncode=p.returncode,
                                             warning_kinds=sorted(set(re.findall(r"%(?:Warning|Error)-(\w+)", p.stdout + p.stderr))))
    cmds["lint_orig_c8"] = " ".join(map(str, cmd))
    checks["lint_successor_no_new_warning_kinds"] = all(
        set(v["warning_kinds"]) <= set(lint["original,REFILL_CREDITS=8"]["warning_kinds"]) for k, v in lint.items())

    exe = w / "tag.vvp"
    cmd = ["iverilog", "-g2012", "-s", "tb_window_refill_tag", f"-Ptb_window_refill_tag.N_REFILL={a.refills}",
           "-o", exe, *ORIG, SUCC, TB]
    p, s_build = run(cmd, w, w / "iverilog.log")
    if p.returncode:
        raise SystemExit((w / "iverilog.log").read_text()[-3000:])
    cmds["build"] = " ".join(map(str, cmd))
    runs = {}
    for name, extra in (("main", []), ("stale_at_wrap", ["+STALE_AT_WRAP"])):
        cmd = ["vvp", "-n", exe, *extra]
        p, s = run(cmd, w, w / f"{name}.log")
        runs[name] = dict(returncode=p.returncode, seconds=s, tail=(p.stdout + p.stderr).splitlines()[-6:])
        cmds[name] = " ".join(map(str, cmd))
    out = (w / "main.log").read_text()
    res = fields(next(l for l in out.splitlines() if l.startswith("RESULT")))
    cyc = fields(next(l for l in out.splitlines() if l.startswith("REFILL_CYCLES")))
    diff = next((l for l in out.splitlines() if l.startswith("AB_FIRST_DIFF")), None)
    stale = (w / "stale_at_wrap.log").read_text()
    n = a.refills
    checks.update({
        "hazard_original_credits8_stalls_at_epoch512": res["a_rows"] == 511 and res["a_mux_fault"] == 1
        and res["a_bad_tag"] == 0x4000 and res["a_pf_state_stuck"] == 1,
        "successor_credits8_all_refills_exact_no_fault": res["b_rows"] == n and res["b_fault"] == 0,
        "successor_epoch_wraps_511_to_0": res["b_wrap"] == 1,
        "successor_equals_original_every_cycle_before_epoch512": res["ab_first_diff_refill"] == 511,
        "successor_default_equals_original_every_cycle_credits8": res["ca_diffs"] == 0,
        "successor_default_equals_original_every_cycle_credits1": res["fe_diffs"] == 0,
        "credits1_reference_all_refills_exact": res["e_rows"] == n,
        "stale_epoch511_reply_after_wrap_rejected": "STALE_AT_WRAP_REJECTED" in stale,
    })
    status = "pass" if all(checks.values()) and runs["main"]["returncode"] == 0 else "fail"
    rec = dict(
        schema="opentallas.rtl.dsrom_lever_window_refill_tag.v1", status=status,
        lever="free-levers audit L3 (WINDOW_REFILL_CREDITS=8): refill tag owner collision at epoch >= 512",
        root_cause=("rtl/chip/ot_chip_v41x_window_kv_prefetch.sv:108 EPOCH_W = TAGW-5 = 11; :257/:335 the epoch "
                    "advances on every multi-credit refill and resets only on rst_n; :237 the FR_PIPE request tag is "
                    "TAGW'({refill_epoch, refill_next}). Tag bits 15:14 are owner bits: ot_chip_v41x_kv_rope_reqmux.sv:100,105 "
                    "admit a WINDOW request only with wt[15:14]==00 and otherwise raise the sticky bad_tag fault. Epoch 512 "
                    "(the 512th refill after reset) sets bit 14 = the CKV owner encoding: the request is blocked and the "
                    "prefetch hangs in FR_PIPE. Any truncation at the boundary would alias epoch e+512 into the CKV / RoPE "
                    "owner namespace."),
        fix=("ot_dsrom_window_kv_prefetch_lv EPOCH_SAFE=1 (default 0): EPOCH_W = TAGW-5-2 = 9; client tag "
             "{2'b00, epoch9, sector5}; the same 9-bit state is compared on return; epoch wraps 511 -> 0. Tag width is "
             "NOT widened: every owner boundary (16/15/16/17/16 bits, contract_r2.json owner_tag_path) stays unchanged, "
             "which is the only way to keep the client out of the owner bits without editing the muxes, KARB and "
             "backend. Reuse of an epoch value 512 refills later is safe because the epoch advances only from IDLE, "
             "after all 17 replies of the previous row were received (no older-epoch request outstanding); the bench "
             "shows a stale epoch-511 reply after the wrap is rejected. Area: 2 fewer epoch flops."),
        why_not_widen=("Widening TAGW at the prefetch does not help: the outer mux slices the client tag at 16 bits and "
                       "assigns bits 15:14 to owners, the inner mux bit 14, KARB bit 16. A wider epoch needs every owner "
                       "boundary widened (5 modules + idx_hbm), all pinned; the 9-bit wrap is the documented minimal "
                       "encoding (contract_r2.json proposed_minimal_encoding)."),
        refills=n, results=res, refill_cycles=cyc, first_divergence=diff,
        cycles_per_refill=dict(credits8=round(cyc["b_credits8_total"] / max(1, cyc["b_n"]), 2),
                               credits1=round(cyc["e_credits1_total"] / max(1, cyc["e_n"]), 2),
                               memory="bounded OOO, 8 slots, latency 2 + (7 i mod 13) cycles; not the HBM model"),
        checks=checks, lint=lint, runs=runs, commands=cmds, source_sha256=pins,
        claim_boundary=("Prefetch + real owner muxes + synthetic OOO memory; no die/KARB/idx_hbm composition, no "
                        "numeric attention, no token-rate or adoption claim. The window credits lever itself is not "
                        "adopted; this removes the epoch>=512 correctness blocker only."),
        scratch=str(w), recorded_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(status, json.dumps(checks, indent=1))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
