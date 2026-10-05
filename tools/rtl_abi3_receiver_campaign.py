#!/usr/bin/env python3
"""Run and record the OR64 operand-receiver campaign on both simulators.

``rtl/abi3/ot_a3_operand_receiver.sv`` is the second of the two blocks
``results/rtl/abi3_boundary_chain.json`` established were MISSING from the
dependent chain of section 13 item 13: nothing in the design wrote a reduction
root into a consumer tile's activation FIFO or advanced its
``act_ready_kblocks``.  This campaign qualifies it the way every other block in
this programme is qualified -- two independently written checkers over one
deterministic top, on Icarus Verilog and Verilator, required to agree case for
case -- against a restatement of ot_a3_tile64's own activation packing rule and
of ``rtl/ot_fp32_rne_pkg.sv``'s binary32 -> BF16 round-to-nearest-even.

It does NOT measure a boundary.  The two-tile chain measurement is
``tools/rtl_abi3_boundary_chain_datapath_campaign.py``.  What it does measure is
the receiver's own operand-readiness delay -- the cycles from a slice's last
root to the cycle ``act_ready_kblocks`` names that slice -- which is reported,
never predicted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "opentallas.rtl.abi3_operand_receiver.v1"
CAMPAIGN = "rtl3_abi3_operand_receiver"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_operand_receiver.json"
MANIFEST = ROOT / "testdata/rtl/abi3_operand_receiver/manifest.json"

RTL_SOURCES = [
    "rtl/abi3/ot_a3_lane_pkg.sv",
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_operand_receiver.sv",
    "rtl/test/a3_receiver_top.sv",
]
BOUND_SOURCES = RTL_SOURCES + [
    "rtl/test/tb_a3_receiver.sv",
    "rtl/test/a3_receiver_harness.cpp",
    "tools/build_abi3_receiver_vectors.py",
    "tools/rtl_abi3_receiver_campaign.py",
]
VECTOR_FILES = ("or_root.hex", "or_case.hex", "or_expect.hex", "or_meta.hex")

CASE_RE = re.compile(
    r"^RCASE (?P<index>\d+) (?P<verdict>OK|DIVERGE) site=(?P<site>\d+) "
    r"words=(?P<words>\d+) slices=(?P<slices>\d+) roots=(?P<roots>\d+) "
    r"sat=(?P<sat>\d+) code=(?P<code>\d+) detail=(?P<detail>\d+) "
    r"tag=(?P<tag>\d+) ready=(?P<ready>\d+) delay=(?P<delay>\d+) "
    r"blocks=(?P<blocks>\d+) group=(?P<group>\d+) gap=(?P<gap>\d+) "
    r"inject=(?P<inject>\d+)$", re.MULTILINE)
CHECKS_RE = re.compile(r"^CHECKS: (\d+)$", re.MULTILINE)
MARKER_RE = re.compile(
    r"^PASS: ABI3 operand receiver cases=(?P<cases>\d+) "
    r"words=(?P<words>\d+) slices=(?P<slices>\d+)$", re.MULTILINE)

SITE_NAMES = {
    0: "none", 1: "error class", 2: "error detail", 3: "error tag",
    4: "activation words written", 5: "the block's own slice counter",
    6: "act_ready_kblocks", 7: "roots accepted", 8: "saturations counted",
    9: "the top timed out", 10: "done did not pulse exactly once",
    11: "the receiver is still busy", 12: "the activation scale port was driven",
    13: "an activation word (low half)", 14: "an activation word (high half)",
    15: "no readiness was stamped for a completed slice",
    16: "the case did not finish",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(body: Any) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True) + "\n"


def tool_identity(name: str, argv: list[str], pattern: str) -> dict[str, Any]:
    path = shutil.which(argv[0]) or argv[0]
    if not Path(path).exists():
        raise SystemExit(f"required tool is unavailable: {name} ({argv[0]})")
    out = subprocess.run(argv, capture_output=True, text=True, check=False)
    text = (out.stdout or "") + (out.stderr or "")
    match = re.search(pattern, text)
    return {"executable": path, "executable_sha256": sha256_file(Path(path)),
            "version": (match.group(0) if match else
                        text.splitlines()[0] if text else "")}


def git_identity() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        return subprocess.run(args, cwd=ROOT, capture_output=True,
                              text=True, check=False).stdout.strip()
    return {"commit": run(["git", "rev-parse", "HEAD"]),
            "worktree_dirty": bool(run(["git", "status", "--porcelain"]))}


def canonicalise(text: str, build: Path) -> str:
    return text.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>").replace(
        str(Path.home()), "<HOME>")


def parse(log: str) -> dict[str, Any]:
    cases = [{k: (m.group(k) if k == "verdict" else int(m.group(k)))
              for k in ("index", "verdict", "site", "words", "slices", "roots",
                        "sat", "code", "detail", "tag", "ready", "delay",
                        "blocks", "group", "gap", "inject")}
             for m in CASE_RE.finditer(log)]
    for case in cases:
        case["site_name"] = SITE_NAMES.get(case["site"], "unknown")
    marker = MARKER_RE.search(log)
    checks = CHECKS_RE.search(log)
    return {"cases": cases, "marker_present": marker is not None,
            "checks": int(checks.group(1)) if checks else None,
            "case_count": int(marker.group("cases")) if marker else None,
            "words": int(marker.group("words")) if marker else None,
            "slices": int(marker.group("slices")) if marker else None}


def run_stage(name: str, command: list[str], cwd: Path, build: Path,
              timeout: int) -> dict[str, Any]:
    out = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                         timeout=timeout)
    log = canonicalise((out.stdout or "") + (out.stderr or ""), build)
    return {"name": name, "command": canonicalise(" ".join(command), build),
            "returncode": out.returncode, "log": log}


def run_iverilog(build: Path) -> dict[str, Any]:
    vvp = build / "or.vvp"
    compile_cmd = ["iverilog", "-g2012", "-s", "tb_a3_receiver", "-o", str(vvp)]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/tb_a3_receiver.sv"))
    comp = run_stage("iverilog.compile", compile_cmd, build, build, 3600)
    if comp["returncode"] != 0:
        raise SystemExit("iverilog compile failed:\n" + comp["log"])
    run = run_stage("iverilog.run", ["vvp", str(vvp)], build, build, 7200)
    entry = parse(run["log"])
    entry.update({"name": "iverilog", "compile_command": comp["command"],
                  "run_command": run["command"], "run_returncode": run["returncode"],
                  "log_sha256": hashlib.sha256(run["log"].encode()).hexdigest(),
                  "run_log": run["log"],
                  "status": "pass" if run["returncode"] == 0 and entry["marker_present"]
                            else "fail"})
    return entry


def run_verilator(build: Path, verilator: str) -> dict[str, Any]:
    obj = build / "obj_or"
    compile_cmd = [verilator, "--cc", "--exe", "--build", "-Wall", "-Wno-fatal",
                   "-Wno-DECLFILENAME", "-O2", "--top-module", "ot_a3_receiver_top",
                   "--Mdir", str(obj), "-o", "Vor"]
    compile_cmd += [str(ROOT / s) for s in RTL_SOURCES]
    compile_cmd.append(str(ROOT / "rtl/test/a3_receiver_harness.cpp"))
    compile_cmd += ["-CFLAGS", "-std=c++17 -O2", "-j", "8"]
    comp = run_stage("verilator.compile", compile_cmd, build, build, 3600)
    if comp["returncode"] != 0:
        raise SystemExit("verilator build failed:\n" + comp["log"])
    run = run_stage("verilator.run", [str(obj / "Vor")], build, build, 7200)
    entry = parse(run["log"])
    entry.update({"name": "verilator", "compile_command": comp["command"],
                  "run_command": "<BUILD>/obj_or/Vor", "run_returncode": run["returncode"],
                  "log_sha256": hashlib.sha256(run["log"].encode()).hexdigest(),
                  "run_log": run["log"],
                  "status": "pass" if run["returncode"] == 0 and entry["marker_present"]
                            else "fail"})
    return entry


COMPARED = ("index", "verdict", "site", "words", "slices", "roots", "sat",
            "code", "detail", "tag", "ready", "delay")


def build_artifact(entries: list[dict[str, Any]],
                   manifest: dict[str, Any]) -> dict[str, Any]:
    projections = [[tuple(c[k] for k in COMPARED) for c in e["cases"]] for e in entries]
    agree = len({tuple(p) for p in projections}) == 1 and bool(projections[0])
    checks_agree = len({e["checks"] for e in entries}) == 1
    diverged = [c for e in entries for c in e["cases"] if c["verdict"] != "OK"]
    status = ("pass" if all(e["status"] == "pass" for e in entries) and agree
              and checks_agree and not diverged else "fail")
    by_name = {c["id"]: c for c in manifest["cases"]}
    faults = sorted({(by_name[c["index"]]["expect_error_detail"],
                      by_name[c["index"]]["expect_error_detail_name"])
                     for c in entries[0]["cases"]
                     if by_name[c["index"]]["expect_error_code"]})
    readiness = sorted({c["delay"] for c in entries[0]["cases"]
                        if by_name[c["index"]]["expect_slices"] > 0})
    return {
        "schema": SCHEMA,
        "campaign": CAMPAIGN,
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": [e["name"] for e in entries],
        "cross_simulator_agreement": {
            "simulators_observed_the_same_cases": agree,
            "check_counts_agree": checks_agree,
            "compared_fields": list(COMPARED),
        },
        "block": {
            "rtl": "rtl/abi3/ot_a3_operand_receiver.sv",
            "why_it_exists": (
                "results/rtl/abi3_boundary_chain.json established by elaboration "
                "that ot_a3_tile64's act_wr_en is an internal net and that "
                "nothing in the design wrote a reduction root into a consumer "
                "tile's activation FIFO.  This is that block"),
            "rounding": (
                "the output stage's single rounding of section 4.4, performed by "
                "ot_fp32_rne_pkg::fp32_to_bf16_rne -- the same function the lane's "
                "own output stage and ot_a3_vector_add use, not a second "
                "implementation of it"),
            "distinct_fault_modes": [{"detail": d, "name": n} for d, n in faults],
        },
        "readiness_delay": {
            "cycles": (readiness[0] if len(readiness) == 1 else None),
            "observed": readiness,
            "rule": (
                "the cycles from the root that completes a K-block slice to the "
                "cycle act_ready_kblocks names that slice: one to write the "
                "activation word into the FIFO and one for the tile to see the "
                "readiness, so the tile never reads a word before it has landed.  "
                "Measured, not predicted, and required to be the same on both "
                "simulators"),
            "invariant_over": (
                "g = 1, 2 and 4, one to three slices, a nonzero op_a_base, and "
                "three idle cycles between roots"),
        },
        "totals": {
            "cases": entries[0]["case_count"],
            "activation_words": entries[0]["words"],
            "slices_delivered": entries[0]["slices"],
            "checks_per_simulator": entries[0]["checks"],
        },
        "manifest": {k: v for k, v in manifest.items() if k != "cases"},
        "cases_declared": manifest["cases"],
        "divergences": diverged,
        "simulators": entries,
        "claim_boundary": {
            "establishes": [
                "that a binary32 root off the link becomes the consumer tile's "
                "activation word: rounded once to BF16 with round-to-nearest-even, "
                "packed g elements to a 64-bit word, written on the tile's own "
                "activation broadcast port at op_a_base + (b mod 2) x "
                "op_a_block_stride + w, and compared word for word",
                "that act_ready_kblocks advances exactly one slice at a time and "
                "only after the slice's last word has landed in the array, so the "
                "tile's S_WAIT gate cannot open on a word that is not there",
                "that the readiness delay does not depend on g, on the slice "
                "count, on the base, or on the rate the roots arrive at",
                "six distinct fail-closed modes, including a root that is not "
                "finite and a root out of ascending tag order",
                "that saturation in the narrowing is COUNTED and is not a fault, "
                "as it is in the lane's own output stage",
            ],
            "does_not_establish": {
                "any_boundary_latency": (
                    "the readiness delay is the receiver's own two cycles, not a "
                    "dependent boundary.  The two-tile chain measurement is a "
                    "separate campaign"),
                "scaled_activations": (
                    "a block-scaled activation is refused: the E8M0 activation "
                    "interleave is recorded as unwritten in ot_a3_tile64's own "
                    "header, and no quantising output stage exists to emit one"),
                "narrower_activation_formats": (
                    "fp32 -> FP8 or MXFP4 is a two-output quantisation, which "
                    "ot_a3_vector_convert also refuses; the receiver refuses it "
                    "rather than inventing one"),
                "the_link_itself": (
                    "the root is presented on a port.  What a traversal costs is "
                    "ot_a3_link_channel's, and results/rtl/a3_link_campaign.json "
                    "regresses it"),
                "physical_realisability": (
                    "simulation says nothing about area, timing or power; no "
                    "routed record of this block exists"),
            },
        },
        "source_sha256": {s: sha256_file(ROOT / s) for s in BOUND_SOURCES},
        "git": git_identity(),
        "tools": {
            "iverilog": tool_identity("iverilog", ["iverilog", "-V"],
                                      r"Icarus Verilog version [\d.]+"),
            "vvp": tool_identity("vvp", ["vvp", "-V"],
                                 r"Icarus Verilog runtime version [\d.]+"),
            "verilator": tool_identity(
                "verilator",
                [os.environ.get("VERILATOR", str(Path.home() /
                 ".local/opentallas-tools/verilator-5.050/bin/verilator")), "--version"],
                r"Verilator [\d.]+"),
            "cxx": tool_identity("g++", ["g++", "--version"], r"g\+\+ .*"),
            "python": {"executable": sys.executable, "version": sys.version.split()[0]},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260908)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 2

    verilator = os.environ.get(
        "VERILATOR",
        str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
    tmp = None
    if args.build_dir is None:
        tmp = tempfile.TemporaryDirectory()
        build = Path(tmp.name)
    else:
        build = args.build_dir
        build.mkdir(parents=True, exist_ok=True)

    from tools.build_abi3_receiver_vectors import build_cases, emit
    manifest = emit(build_cases(), build, args.seed)
    for name in VECTOR_FILES:
        if sha256_file(build / name) != manifest["image_sha256"][name]:
            raise SystemExit(f"image {name} does not match its own manifest digest")
    committed = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else None
    manifest["vector_manifest_matches_committed"] = bool(
        committed is not None and committed.get("image_sha256") == manifest["image_sha256"])

    entries = [run_iverilog(build), run_verilator(build, verilator)]
    body = build_artifact(entries, manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(body), encoding="utf-8")
    for entry in entries:
        print(f"{entry['name']}: {entry['status'].upper()} "
              f"cases={entry['case_count']} checks={entry['checks']} "
              f"words={entry['words']} slices={entry['slices']}")
    r = body["readiness_delay"]
    print(f"operand readiness: {r['cycles']} cycles, observed {r['observed']}")
    print(f"abi3 operand receiver campaign: {body['status'].upper()} -> {args.output}")
    if tmp is not None:
        tmp.cleanup()
    return 0 if body["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
