#!/usr/bin/env python3
"""Does a HIERARCHICAL descriptor distributor keep a WIDE array busy, correctly?

THE QUESTION, AND WHY IT IS NOT ALREADY ANSWERED
------------------------------------------------
``tools/audit_control_path_throughput.py`` reports nine (capability) verdicts of
SHORT and the fan-out each one needs: 34 for the 16-unit capabilities, 68 for
``rom_qwen3``, 1,076 for ``rom_deepseek_v4`` and ``rom_deepseek_v41_wafer``. Its
whole ``utilisation_with_fanout`` column is valid only GIVEN that one descriptor
is expanded in hardware across every compute unit -- and the only routed fan-out
record in the repository is ``ot_probe_cluster_disp`` at UNITS=16. The 48.2 %
sustained-utilisation figure behind every sustained-throughput claim is likewise
a ONE-UNIT measurement multiplied onto 16-, 32- and 512-unit chips.

``rtl/proto/ot_cluster_dispatcher.sv``'s own header says what the flat structure
costs: "34x to 1,075x too slow for the arrays this project actually proposes".

So this campaign measures the replacement at the widths that matter, with the
real compute units, and it refuses to report a throughput number from a run that
did not also prove the results correct.

WHAT IS MEASURED, BY WHOM
-------------------------
Every configuration is simulated by the pinned Verilator 5.050 -- the same
simulator ``tools/rtl_gemm_operand_reuse_campaign.py`` uses -- on
``rtl/test/tb_dispatch_tree_throughput.sv`` with a REAL ``ot_compute_unit`` at
every leaf, each with its own pair of ``fakeram_256x128`` weight macros.

  functional   every accumulator in every unit must be bit-identical to
               ``testdata/rtl/a3_mac_tile/expected.hex``, the vectors
               ``ot_mac_tile`` was qualified against. LEAVES x 16 results.
  sub-range    every leaf's ``cu_tile`` must equal the descriptor's grid origin
               plus that leaf's index. A broadcast that handed every unit the
               same work would pass the functional check and be useless for a
               real GEMM, so this is checked separately and at width.
  utilisation  summed busy cycles over all units / (LEAVES x elapsed cycles),
               with the control plane modelled at its MEASURED rate: one
               descriptor every 567 datapath cycles (116.4 sequencer cycles at
               the place-and-routed 265 MHz, seen from the place-and-routed
               1,290 MHz of ot_compute_unit).

A configuration whose functional or sub-range check fails is recorded with its
utilisation REFUSED, because a distributor that keeps units busy with the wrong
operands is worthless and reporting its duty cycle would be a lie.

WHAT IS NOT MEASURED HERE
-------------------------
Frequency and area. Those come from ``tools/run_abi3_physical.py`` post-route
records on ``ot_probe_dispatch_tree``; a cycle count says nothing about whether
the structure closes timing, and pre-layout timing says nothing about whether it
routes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
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
    "rtl/proto/ot_dispatch_tree.sv",
    "rtl/proto/ot_cluster_dispatcher.sv",
    "rtl/test/tb_dispatch_tree_throughput.sv",
)
VECTORS = ("testdata/rtl/a3_mac_tile/act.hex",
           "testdata/rtl/a3_mac_tile/wgt.hex",
           "testdata/rtl/a3_mac_tile/expected.hex")
TOP = "tb_dispatch_tree_throughput"

#: WIDTHTRUNC and WIDTHEXPAND are waived by NAME, not with -Wno-fatal: the
#: shipped ot_compute_unit indexes a 256-entry activation file with a 9-bit
#: counter and the bench assigns 32-bit localparams to sized regs.  Waiving the
#: classes by name keeps every OTHER warning fatal, which is what caught a real
#: SELRANGE fault in ot_mac_lane_packed once.
WAIVED = ("WIDTHTRUNC", "WIDTHEXPAND", "DECLFILENAME", "UNUSEDSIGNAL",
          "PINCONNECTEMPTY", "PROCASSINIT")

UTIL_RE = re.compile(
    r"UTIL units=(\d+) leaves=(\d+) group=(\d+) radix=(\d+) flat=(\d+) "
    r"skew=(\d+) K=(\d+) passes=(\d+) interval=(\d+) descs=(\d+) "
    r"passes_launched=(\d+) completions=(\d+) cycles=(\d+) util=([\d.]+) "
    r"starved=([\d.]+) rootstall=([\d.]+) timeout=(\d+) grants=(\d+) "
    r"decoupled=(\d+) banks=(\d+)")

#: The audit's own required_fanout column, so the widths this campaign runs are
#: the widths the capabilities ask for and not a round number of my choosing.
REQUIRED_WIDTHS = {
    16: "compute units in hbm_sram_cluster_32, hbm_sram_cluster_32_speculative, "
        "hbm_sram_single_chip, rom_deepseek_v41_array_64, "
        "rom_deepseek_v4_array_32 and rom_deepseek_v4_pro_array_32; their "
        "required_fanout rate factor is 34",
    32: "compute units in rom_qwen3; its required_fanout rate factor is 68",
    34: "the literal required_fanout of the six 16-unit capabilities, measured "
        "as a width as well so the rate factor is covered either way it is read",
    68: "the literal required_fanout of rom_qwen3",
    512: "compute units in rom_deepseek_v4 and rom_deepseek_v41_wafer; their "
         "required_fanout rate factor is 1,076",
    1076: "the literal required_fanout of rom_deepseek_v4 and "
          "rom_deepseek_v41_wafer",
    1088: "68 leaves x GROUP 16: the smallest GROUP=16 tree that exceeds the "
          "1,076 required_fanout, so one routed record covers every capability",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def git_state() -> dict[str, Any]:
    def run(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD") or None,
            "branch": run("rev-parse", "--abbrev-ref", "HEAD") or None,
            "worktree_dirty": bool(run("status", "--porcelain"))}


def verilator_version() -> str:
    out = subprocess.run([str(VERILATOR), "--version"], capture_output=True,
                         text=True, check=True).stdout
    return out.split()[1]


def build(workdir: Path, leaves: int, radix: int, credits: int,
          jobs: int, flat: int = 0, skew: int = 0, group: int = 1,
          decoupled: int = 0, banks: int = 1) -> Path:
    tag = (f"l{leaves}_g{group}_r{radix}_c{credits}_f{flat}_s{skew}"
           f"_d{decoupled}_b{banks}")
    obj = workdir / f"obj_{tag}"
    exe = obj / f"sim_{tag}"
    if exe.exists():
        return exe
    cmd = [str(VERILATOR), "--binary", "--timing", "-O2",
           "-DOT_A3_FAKERAM_BEHAVIOURAL",
           *[f"-Wno-{w}" for w in WAIVED],
           "--top-module", TOP,
           f"-GLEAVES={leaves}", f"-GRADIX={radix}", f"-GCREDITS={credits}",
           f"-GFLAT={flat}", f"-GSKEW={skew}", f"-GGROUP={group}",
           f"-GREFILL_DECOUPLED={decoupled}", f"-GWGT_BANKS={banks}",
           "-o", exe.name, "--Mdir", str(obj), "-j", str(jobs),
           *[str(ROOT / s) for s in SOURCES]]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"verilator failed for {tag}:\n{r.stdout}\n{r.stderr}")
    return exe


def run_one(exe: Path, ndesc: int, units: int, flat: int) -> dict[str, Any]:
    units_seen = units
    r = subprocess.run([str(exe), f"+ndesc={ndesc}"], cwd=ROOT,
                       capture_output=True, text=True)
    lines = r.stdout.splitlines()
    func = next((l for l in lines if l.startswith(("PASS functional",
                                                   "FAIL functional"))), "")
    rows = []
    for line in lines:
        m = UTIL_RE.match(line.strip())
        if not m:
            continue
        g = m.groups()
        rows.append({
            "kernel_depth_k": int(g[6]),
            "passes_per_descriptor": int(g[7]),
            "control_interval_datapath_cycles": int(g[8]),
            "descriptors_retired": int(g[9]),
            "passes_launched": int(g[10]),
            "unit_completions": int(g[11]),
            "elapsed_cycles": int(g[12]),
            "array_utilisation_percent": float(g[13]),
            "root_idle_queue_empty_percent": float(g[14]),
            "root_stalled_for_credit_percent": float(g[15]),
            "hit_cycle_limit": bool(int(g[16])),
            #: utilisation counts a STALLED unit as busy, because it is holding
            #: its accumulators and burning a cycle. Under a skewed refill that
            #: makes it an occupancy figure; this is the work figure.
            "pass_rate_per_unit_cycles": (int(g[12]) / int(g[10])
                                          if int(g[10]) else None),
            #: WEIGHT COLUMNS FETCHED over the refill port, summed over units.
            #: The reuse factor the fill frontier is supposed to buy is
            #: measurable as the ratio of this between the two flow-control
            #: modes at the same passes-per-descriptor: a lockstep unit fetches
            #: one column per column CONSUMED, a decoupled one fetches one per
            #: column RESIDENT.
            "refill_grants": int(g[17]),
            "refill_grants_per_unit_pass_column": (
                int(g[17]) / (int(units_seen) * int(g[10]) * int(g[6]))
                if (int(g[10]) and units_seen) else None),
            "refill_decoupled": int(g[18]),
            "weight_banks": int(g[19]),
        })
    #: WORK CONSERVATION, checked and not assumed: a token must reach EVERY unit
    #: exactly once, so the root's unit-completion total has to be UNITS times the
    #: number of tokens it launched, and the descriptors it retires has to be the
    #: number sent.  A tree that dropped a replica on a busy child, or delivered
    #: one twice, fails this even when every result is still bit-exact -- because
    #: each pass re-walks the same K and overwrites the accumulator.
    conserved = None
    if not flat:
        conserved = all(row["unit_completions"] == units * row["passes_launched"]
                        and row["descriptors_retired"] == ndesc for row in rows)
        for row in rows:
            row["work_conserved"] = (row["unit_completions"]
                                     == units * row["passes_launched"])
            row["expected_unit_completions"] = units * row["passes_launched"]
    return {"functional_line": func,
            "functional_pass": func.startswith("PASS"),
            "work_conserved_all_cases": conserved,
            "utilisation": rows,
            "finished": any(l.startswith("DONE") for l in lines),
            "stdout_tail": lines[-3:] if r.returncode else lines}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--leaves", type=int, action="append", default=None,
                    help="fan-out width to measure, repeatable "
                         "(default: the audit's own required_fanout widths)")
    ap.add_argument("--radix", type=int, action="append", default=None,
                    help="tree radix, repeatable (default 16)")
    ap.add_argument("--credits", type=int, default=2)
    ap.add_argument("--group", type=int, action="append", default=None,
                    help="compute units per leaf. 1 is one leaf per unit; 16 is "
                         "the width ot_cluster_dispatcher is already routed at, "
                         "so UNITS = LEAVES * GROUP")
    ap.add_argument("--structure", action="append", default=None,
                    choices=("tree", "flat"),
                    help="tree (ot_dispatch_tree) or flat (ot_cluster_dispatcher), "
                         "repeatable; default tree only")
    ap.add_argument("--skew", action="append", type=int, default=None,
                    choices=(0, 1, 2, 3, 4),
                    help="0: identical units; 1: per-unit refill duty so units "
                         "finish at different times; 2: one unit in sixteen at a "
                         "50%% duty; 3: one in sixteen at 25%%; 4: EVERY unit at "
                         "50%%. Repeatable; default 0")
    ap.add_argument("--decoupled", action="append", type=int, default=None,
                    choices=(0, 1),
                    help="ot_compute_unit REFILL_DECOUPLED: 0 is the lockstep "
                         "handshake the published stall table and the 54.13%% "
                         "skew-2 utilisation were measured on, 1 is the fill "
                         "frontier. Repeatable; default 0")
    ap.add_argument("--banks", action="append", type=int, default=None,
                    help="ot_compute_unit WGT_BANKS: 1 single buffer (the fill "
                         "and the walk share one macro port), 2 double buffer at "
                         "one extra macro pair. Repeatable; default 1")
    ap.add_argument("--ndesc", type=int, default=12,
                    help="descriptors per utilisation case")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    if not VERILATOR.exists():
        raise SystemExit(f"pinned Verilator {PINNED_VERILATOR_VERSION} not at {VERILATOR}")
    version = verilator_version()
    if version != PINNED_VERILATOR_VERSION:
        raise SystemExit(f"Verilator {version} is not the pinned "
                         f"{PINNED_VERILATOR_VERSION}")

    leaves = args.leaves or [16, 34, 68, 1076]
    radices = args.radix or [16]
    args.workdir.mkdir(parents=True, exist_ok=True)

    structures = args.structure or ["tree"]
    skews = args.skew if args.skew is not None else [0]
    groups = args.group or [1]
    #: (REFILL_DECOUPLED, WGT_BANKS) pairs.  Zipped rather than crossed when the
    #: caller gives the same number of each, because 1/1 and 1/2 are different
    #: designs and 0/2 is a build nobody needs.
    decs = args.decoupled if args.decoupled is not None else [0]
    bnks = args.banks if args.banks is not None else [1]
    if len(bnks) == 1:
        modes = [(d, bnks[0]) for d in decs]
    elif len(decs) == 1:
        modes = [(decs[0], b) for b in bnks]
    elif len(decs) == len(bnks):
        modes = list(zip(decs, bnks))
    else:
        raise SystemExit("--decoupled and --banks must be equal in number, or "
                         "one of them given once")

    records = []
    for structure in structures:
      for (decoupled, banks) in modes:
        for skew in skews:
          for radix in radices:
           for gsz in groups:
            for n in leaves:
                flat = 1 if structure == "flat" else 0
                if flat and decoupled:
                    #: ot_cluster_dispatcher has no per-pass output, so its units
                    #: cannot be told which pass brings a new tile.  Refused
                    #: rather than measured with a flag that means nothing.
                    print("  skip flat + decoupled: the flat dispatcher cannot "
                          "supply wgt_reload", flush=True)
                    continue
                exe = build(args.workdir, n, radix, args.credits, args.jobs,
                            flat=flat, skew=skew, group=gsz,
                            decoupled=decoupled, banks=banks)
                res = run_one(exe, args.ndesc, n * gsz, flat)
                rec = {
                    "refill_decoupled": decoupled,
                    "weight_banks": banks,
                    "leaves": n,
                    "group": gsz,
                    "compute_units": n * gsz,
                    "radix": radix if not flat else None,
                    "structure": structure,
                    "distributor_module": ("ot_dispatch_tree" if not flat
                                           else "ot_cluster_dispatcher"),
                    "refill_skew": skew,
                    "credits": args.credits,
                    "why_this_width": REQUIRED_WIDTHS.get(
                        n * gsz, "not one of the audit's required widths"),
                    "tree_depth_levels": _depth(n, radix) if not flat else 1,
                    "interior_nodes": _nodes(n, radix) if not flat else 0,
                    **res,
                }
                #: a utilisation number from a run whose results were wrong is
                #: not a result, so it is refused rather than reported.
                if rec.get("work_conserved_all_cases") is False:
                    rec["utilisation_refused"] = (
                        "work conservation failed: the root's unit-completion "
                        "total is not UNITS times the tokens it launched, so some "
                        "unit did not receive every descriptor exactly once")
                if not rec["functional_pass"]:
                    rec["utilisation_refused"] = (
                        "functional or sub-range check did not pass; a duty "
                        "cycle measured on wrong results is not evidence")
                records.append(rec)
                best = max((r["array_utilisation_percent"]
                            for r in res["utilisation"]), default=0.0)
                print(f"  {structure:<4} d={decoupled} b={banks} "
                      f"skew={skew} units={n*gsz:>5} "
                      f"leaves={n:>5} group={gsz:>3} "
                      f"radix={str(rec['radix']):>4} "
                      f"depth={rec['tree_depth_levels']} "
                      f"nodes={rec['interior_nodes']:>4} "
                      f"functional={'PASS' if rec['functional_pass'] else 'FAIL'} "
                      f"conserved={rec.get('work_conserved_all_cases')} "
                      f"best_util={best:5.2f}%", flush=True)

    body = {
        "schema": "opentallas.rtl.dispatch_tree_campaign.v1",
        "question": ("Does a hierarchical descriptor distributor hold array "
                     "utilisation at the fan-out widths "
                     "tools/audit_control_path_throughput.py requires, with "
                     "results bit-identical to the reference at every width?"),
        "git": git_state(),
        "simulator": {"name": "verilator", "version": version,
                      "path": str(VERILATOR), "sha256": sha256_file(VERILATOR)},
        "sources": [{"path": s, "sha256": sha256_file(ROOT / s),
                     "size_bytes": (ROOT / s).stat().st_size} for s in SOURCES],
        "vectors": [{"path": v, "sha256": sha256_file(ROOT / v)} for v in VECTORS],
        "control_model": {
            "interval_datapath_cycles": 567,
            "basis": ("116.4 control cycles per engine command measured by G1e "
                      "(results/rtl/abi3_g1e_control_end_to_end.json) at the "
                      "place-and-routed 265 MHz of ot_a3_microsequencer, seen "
                      "from the place-and-routed 1,290 MHz of ot_compute_unit"),
        },
        "records": records,
        "refusals": [
            "refill-write-is-charged-only-in-the-decoupled-mode: under "
            "REFILL_DECOUPLED=0 a granted refill writes NOTHING -- the weight "
            "image is preloaded through the host port and refill_valid is a pure "
            "token, so the baseline stall numbers charge for waiting but not for "
            "storing. Under REFILL_DECOUPLED=1 the grant carries the column and "
            "writes the macro, which costs a port slot whenever the fill and the "
            "walk are in the same bank. The two modes are therefore NOT equal "
            "fidelity on the write side, and the decoupled mode is the stricter "
            "of the two.",
            "flat-cannot-be-decoupled: ot_cluster_dispatcher has no per-pass "
            "output, so it cannot tell a unit which pass brings a new weight "
            "tile. Flat rows are measured at REFILL_DECOUPLED=0 only; a flat "
            "row with the flag tied high would charge a tile fetch per pass and "
            "would not be comparable to the tree.",
            "activation-delivery-not-modelled: the fill frontier covers the "
            "WEIGHT path. Activations are written through a bench port with no "
            "rate limit at all, so nothing here says what an activation-starved "
            "array would do.",
            "utilisation-requires-correctness: a configuration whose functional, "
            "sub-range or work-conservation check fails has its utilisation "
            "refused, not reported.",
            "no-frequency-claim: this campaign measures cycles. Whether the "
            "structure closes at the 1,290 MHz the cycle counts are quoted "
            "against is a place-and-route question, answered by "
            "tools/run_abi3_physical.py on ot_probe_dispatch_tree and by nothing "
            "here.",
            "output-stationary-only: every unit walks the same K and the same "
            "scale and differs only by its sub-range index. A descriptor whose "
            "extent had to be split unequally across units is out of scope for "
            "this distributor and for this measurement.",
            "one-descriptor-stream: the control plane is modelled as a periodic "
            "source at its measured rate. A real sequencer's descriptor stream "
            "is bursty and interleaved with other engines' commands, which this "
            "does not model.",
            "tensor-engine-only: LEAVES here are tensor compute units. Vector, "
            "attention and reduction engines also consume descriptors and are "
            "not distributed by this tree in this measurement.",
        ],
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        print(f"wrote {args.output}")
    ok = all(r["functional_pass"] and r.get("work_conserved_all_cases") is not False
             for r in records)
    return 0 if ok else 1


def _depth(leaves: int, radix: int) -> int:
    d, reach = 1, radix
    while reach < leaves:
        reach *= radix
        d += 1
    return d


def _nodes(leaves: int, radix: int) -> int:
    d = _depth(leaves, radix)
    total = 0
    for l in range(d):
        span = radix ** (d - l)
        total += -(-leaves // span)
    return total


if __name__ == "__main__":
    raise SystemExit(main())
