#!/usr/bin/env python3
"""What does an unbacked weight refill cost the compute unit, before and after?

THE TABLE THIS REPLACES, AND WHY IT IS STILL HERE
-------------------------------------------------
``tools/audit_kernel_refill_regimes.py`` quotes four numbers measured by
``rtl/test/tb_kernel_rom_vs_hbm.sv`` on ``ot_compute_unit``::

    refill period 1    46 cycles     0 stall cycles
    refill period 2    78 cycles    31 stall cycles
    refill period 4   142 cycles    95 stall cycles
    refill period 8   266 cycles   219 stall cycles

Those were measured on the LOCKSTEP handshake: a weight column could only be
consumed on a cycle when ``refill_valid`` happened to be high, so the refill port
ran in step with the MAC tile. That is ``REFILL_DECOUPLED=0``, which this campaign
runs as its first column and which must still reproduce the four numbers exactly.
If it ever stops doing so, the baseline has moved and every comparison against it
is void -- so the check is in the record, not in a comment.

WHAT IS COMPARED, AND WHAT IS NOT EQUAL ABOUT IT
-----------------------------------------------
Three configurations of ONE RTL file, so nothing about the datapath, the vectors
or the expected results differs between columns:

  decoupled=0 banks=1   the lockstep baseline.  A granted refill writes NOTHING:
                        the weight image is preloaded through the host port and
                        ``refill_valid`` is a pure token.  The baseline therefore
                        charges for WAITING but not for STORING, which is the one
                        respect in which it is the weaker model of the three.
  decoupled=1 banks=1   the fill frontier on a single weight bank.  A grant
                        carries the column and writes the macro, and fetch and
                        compute serialise because there is only one bank.
  decoupled=1 banks=2   the double buffer: the next descriptor's tile lands in the
                        other bank while this one is walked.

``+nopreload=1`` runs the decoupled columns with the host image port UNUSED, so
every weight column the unit computes with must have arrived over the refill port.
Under ``banks=2`` the walk reads a bank the host never wrote, so a residency or
bank-select fault is a wrong accumulator rather than an unverifiable cycle count.
The campaign runs both and records that they agree.

PASSES ARE THE POINT
--------------------
``+passes=P`` runs P passes of one descriptor with ``wgt_reload`` asserted on the
first only.  Each pass re-walks the same resident columns, so the accumulator
after P passes must equal the accumulator after one -- and the REFILL GRANTS say
whether the hardware believed it.  A lockstep unit fetches P*K columns for P
passes; a decoupled one fetches K.  That divisor is the reuse factor
``tools/audit_kernel_refill_regimes.py`` refuses to state without a batch, and at
P=3 -- the descriptor coarseness at which all nine capabilities' control-path
verdicts clear -- it is measured here rather than assumed.

WHAT THIS DOES NOT MEASURE
--------------------------
Area, frequency and energy.  A cycle count says nothing about whether the second
bank closes timing or what it costs in silicon; that is
``tools/run_abi3_physical.py`` on ``ot_compute_unit`` with the same parameters, and
``tools/audit_operand_delivery_double_buffer.py`` composes the two.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = Path(os.environ.get("OPENTALLAS_TOOL_ROOT",
                                 Path.home() / ".local/opentallas-tools"))
VERILATOR = TOOLS_ROOT / "verilator-5.050/bin/verilator"
PINNED_VERILATOR_VERSION = "5.050"

SOURCES = (
    "rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv",
    "rtl/proto/ot_mac_lane.sv",
    "rtl/proto/ot_mac_tile.sv",
    "rtl/proto/ot_compute_unit.sv",
    "rtl/test/tb_kernel_rom_vs_hbm.sv",
)
VECTORS = {"act": "testdata/rtl/a3_mac_tile/act.hex",
           "wgt": "testdata/rtl/a3_mac_tile/wgt.hex",
           "exp": "testdata/rtl/a3_mac_tile/expected.hex"}
TOP = "tb_kernel_rom_vs_hbm"

#: the same single waived warning class tools/rtl_gemm_operand_reuse_campaign.py
#: waives, by name and not with -Wno-fatal: the unit indexes a 256-entry
#: activation file with a 9-bit counter and the bench assigns a 32-bit localparam
#: to a 9-bit reg.  Every other warning stays fatal.
WAIVED = ("WIDTHTRUNC",)

#: The published table this campaign must keep reproducing at decoupled=0,
#: banks=1, passes=1.  Source: tools/audit_kernel_refill_regimes.py MEASURED.
PUBLISHED_BASELINE = {1: (46, 0), 2: (78, 31), 4: (142, 95), 8: (266, 219)}

LINE_RE = re.compile(
    r"(PASS|FAIL) period=(\d+): .*?(\d+) cycles, (\d+) stall cycles, "
    r"passes=(\d+) grants=(\d+) prewindow=(\d+) decoupled=(\d+) banks=(\d+) "
    r"nopreload=(\d+)")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "branch": run("rev-parse", "--abbrev-ref", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def verilator_version() -> str:
    return subprocess.run([str(VERILATOR), "--version"], capture_output=True,
                          text=True, check=True).stdout.split()[1]


def build(workdir: Path, decoupled: int, banks: int, jobs: int) -> Path:
    obj = workdir / f"obj_d{decoupled}b{banks}"
    exe = obj / "sim"
    if exe.exists():
        return exe
    cmd = [str(VERILATOR), "--binary", "--timing",
           "-DOT_A3_FAKERAM_BEHAVIOURAL",
           *[f"-Wno-{w}" for w in WAIVED],
           "--top-module", TOP,
           f"-GREFILL_DECOUPLED={decoupled}", f"-GWGT_BANKS={banks}",
           "-o", exe.name, "--Mdir", str(obj), "-j", str(jobs),
           *[str(ROOT / s) for s in SOURCES]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"verilator failed d={decoupled} b={banks}:\n"
                         f"{r.stdout}\n{r.stderr}")
    return exe


def run_one(exe: Path, period: int, passes: int, nopreload: int,
            decoupled: int, banks: int) -> dict[str, Any]:
    args = [str(exe), *[f"+{k}={v}" for k, v in VECTORS.items()],
            f"+period={period}", f"+passes={passes}", f"+nopreload={nopreload}"]
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    line = next((l for l in r.stdout.splitlines()
                 if l.startswith(("PASS", "FAIL"))), "")
    m = LINE_RE.match(line)
    if not m:
        #: a run that produced no verdict, or a WRONG one.  Kept with its keys so
        #: it appears in every selection the checks make instead of vanishing.
        wrong = next((l for l in r.stdout.splitlines() if l.startswith("FAIL")), "")
        return {"refill_period": period, "passes": passes,
                "nopreload": bool(nopreload), "bit_exact": False,
                "refill_decoupled": decoupled, "weight_banks": banks,
                "refused": ("bench reported wrong accumulators" if wrong
                            else "bench printed no parseable verdict"),
                "bench_line": wrong or None,
                "stdout": r.stdout[-400:] if not wrong else None}
    g = m.groups()
    cycles, stalls, grants = int(g[2]), int(g[3]), int(g[5])
    return {
        "refill_period": period,
        "passes": passes,
        "nopreload": bool(nopreload),
        "bit_exact": g[0] == "PASS",
        "cycles": cycles,
        "stall_cycles": stalls,
        "refill_grants": grants,
        "prefetch_window_cycles": int(g[6]),
        "refill_decoupled": int(g[7]),
        "weight_banks": int(g[8]),
        #: columns fetched per column CONSUMED.  1.0 is no reuse at all.
        "grants_per_consumed_column": grants / (passes * 32),
        "bench_line": line,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--period", type=int, nargs="+", default=[1, 2, 4, 8, 16])
    ap.add_argument("--passes", type=int, nargs="+", default=[1, 2, 3, 8])
    ap.add_argument("--mode", action="append", default=None,
                    metavar="DECOUPLED:BANKS",
                    help="repeatable; default 0:1 (the published baseline), "
                         "1:1 (single buffer) and 1:2 (double buffer)")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    if not VERILATOR.exists():
        raise SystemExit(f"pinned Verilator not at {VERILATOR}")
    version = verilator_version()
    if version != PINNED_VERILATOR_VERSION:
        raise SystemExit(f"Verilator {version} is not the pinned "
                         f"{PINNED_VERILATOR_VERSION}")
    modes = [tuple(int(x) for x in m.split(":")) for m in (args.mode
                                                          or ["0:1", "1:1", "1:2"])]
    args.workdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for decoupled, banks in modes:
        exe = build(args.workdir, decoupled, banks, args.jobs)
        #: the lockstep mode has no refill data path -- the grant is a pure token
        #: and the weights come from the host port -- so +nopreload has nothing to
        #: compute with there and is run only to record that it FAILS, which is
        #: what tells the reader the baseline's operands were free.
        for nopre in (0, 1):
            for passes in args.passes:
                for period in args.period:
                    row = run_one(exe, period, passes, nopre, decoupled, banks)
                    row["mode"] = f"decoupled={decoupled} banks={banks}"
                    rows.append(row)
                    print(f"  d={decoupled} b={banks} nopreload={nopre} "
                          f"P={passes:<2} period={period:<3} "
                          f"{'PASS' if row.get('bit_exact') else 'FAIL'} "
                          f"cycles={row.get('cycles')} "
                          f"stalls={row.get('stall_cycles')} "
                          f"grants={row.get('refill_grants')}", flush=True)

    def pick(d: int, b: int, period: int, passes: int, nopre: int):
        return next((r for r in rows
                     if r["refill_decoupled"] == d and r["weight_banks"] == b
                     and r["refill_period"] == period and r["passes"] == passes
                     and r["nopreload"] == bool(nopre)), None)

    #: GATE 1 -- the published baseline, reproduced digit for digit.
    baseline_check = []
    for period, (cyc, stall) in PUBLISHED_BASELINE.items():
        r = pick(0, 1, period, 1, 0)
        baseline_check.append({
            "refill_period": period,
            "published_cycles": cyc, "published_stall_cycles": stall,
            "measured_cycles": (r or {}).get("cycles"),
            "measured_stall_cycles": (r or {}).get("stall_cycles"),
            "agrees": bool(r and r.get("cycles") == cyc
                           and r.get("stall_cycles") == stall),
        })
    baseline_ok = all(c["agrees"] for c in baseline_check)

    #: GATE 2 -- the decoupled modes deliver every column over the refill port,
    #: with the host image port unused, and get the same answer either way.
    delivery_check = []
    for decoupled, banks in modes:
        if not decoupled:
            continue
        for passes in args.passes:
            for period in args.period:
                a = pick(decoupled, banks, period, passes, 0)
                b = pick(decoupled, banks, period, passes, 1)
                delivery_check.append({
                    "mode": f"decoupled={decoupled} banks={banks}",
                    "refill_period": period, "passes": passes,
                    "preloaded_bit_exact": bool(a and a["bit_exact"]),
                    "refill_only_bit_exact": bool(b and b["bit_exact"]),
                    "cycles_agree": bool(a and b and a.get("cycles") == b.get("cycles")),
                })
    delivery_ok = all(d["refill_only_bit_exact"] for d in delivery_check)

    #: GATE 3 -- the control that proves gate 2 means something.  At
    #: REFILL_DECOUPLED=0 the refill port carries NO payload, so a run with the
    #: host image port skipped MUST produce wrong accumulators.  If it did not,
    #: the weights would be coming from somewhere this campaign does not control
    #: and the refill-only runs above would prove nothing.
    control = [{"refill_period": r["refill_period"], "passes": r["passes"],
                "bit_exact": r["bit_exact"]}
               for r in rows if r["refill_decoupled"] == 0 and r["nopreload"]]
    control_ok = bool(control) and not any(c["bit_exact"] for c in control)

    body = {
        "schema": "opentallas.rtl.refill_stall_campaign.v1",
        "question": ("What does an unbacked weight refill cost ot_compute_unit "
                     "under the lockstep handshake, under a fill frontier on one "
                     "weight bank, and under a double buffer -- on the same RTL, "
                     "the same vectors and the same expected results?"),
        "git": git_state(),
        "simulator": {"name": "verilator", "version": version,
                      "path": str(VERILATOR), "sha256": sha256_file(VERILATOR)},
        "sources": [{"path": s, "sha256": sha256_file(ROOT / s),
                     "size_bytes": (ROOT / s).stat().st_size} for s in SOURCES],
        "vectors": [{"path": v, "sha256": sha256_file(ROOT / v)}
                    for v in VECTORS.values()],
        "kernel_depth_k": 32,
        "lanes": 16,
        "modes": [{"refill_decoupled": d, "weight_banks": b} for d, b in modes],
        "rows": rows,
        "published_baseline_reproduced": {
            "checks": baseline_check,
            "all_agree": baseline_ok,
            "why_it_gates": ("the four numbers in "
                             "tools/audit_kernel_refill_regimes.py are the "
                             "baseline every operand-delivery claim is measured "
                             "against. A run in which they moved would mean the "
                             "comparison is against a different design, so this "
                             "is checked and not assumed."),
        },
        "refill_is_the_only_weight_source": {
            "checks": delivery_check,
            "all_decoupled_modes_bit_exact_without_the_host_port": delivery_ok,
            "why_it_matters": ("with WGT_BANKS=2 the walk reads a bank the host "
                              "image port never writes, so every one of the 16 "
                              "checked accumulators depends on the fill frontier "
                              "having delivered the right column into the right "
                              "bank. Residency is therefore checked by the "
                              "reference and not by a counter."),
        },
        "lockstep_refill_carries_no_payload": {
            "expectation": ("at REFILL_DECOUPLED=0 every one of these runs must "
                            "report WRONG accumulators: the refill grant is a pure "
                            "token with no data, so with the host image port "
                            "skipped the weight store is never written. These rows "
                            "are a CONTROL, not failures -- they are what makes the "
                            "refill-only runs of the decoupled modes evidence."),
            "runs": control,
            "all_wrong_as_expected": control_ok,
        },
        "refusals": [
            "baseline-refill-writes-nothing: at REFILL_DECOUPLED=0 a granted "
            "refill stores no column -- the image is preloaded and refill_valid is "
            "a pure token. The baseline charges for waiting and not for storing, "
            "so the two modes are not equal fidelity on the write side and the "
            "decoupled one is the stricter. Any row where the decoupled mode looks "
            "worse should be read against that.",
            "one-descriptor-one-tile: this bench runs ONE descriptor, so the "
            "double buffer has no NEXT tile to prefetch and its advantage here is "
            "reuse across passes plus whatever the pre-pass window delivers. The "
            "prefetch-across-descriptors term is measurable only in the array "
            "campaign, where descriptors keep arriving.",
            "k-is-32: the vectors ot_mac_tile was qualified against are K=32. The "
            "array campaign's descriptors are K=256, so cycle counts here are not "
            "comparable to it in absolute terms.",
            "activation-path-not-rate-limited: only the weight refill is starved. "
            "Activations are written through a bench port at full rate.",
            "no-frequency-or-area-claim: cycles only. Whether the second bank "
            "closes timing and what it costs is a place-and-route question.",
        ],
    }

    print("\npublished baseline reproduced:", baseline_ok)
    print("refill-only delivery bit-exact in every decoupled mode:", delivery_ok)
    print("lockstep refill carries no payload (control, all must be wrong):",
          control_ok)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        print(f"wrote {args.output}")
    ok = baseline_ok and delivery_ok and control_ok and all(
        r.get("bit_exact") for r in rows
        if not (r["refill_decoupled"] == 0 and r["nopreload"]))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
