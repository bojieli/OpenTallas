#!/usr/bin/env python3
"""Report HBM replay evidence without promoting partial SU probes to token passes."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def report(out, mode, rev, contract, names):
    rows = {}
    for name in names:
        replay = json.loads((out / "rj" / f"{name}.json").read_text())
        log = out / "runs" / name / "run.log"
        text = log.read_text(errors="replace") if log.exists() else ""
        match = re.search(r"SLICE_SUMMARY drives=(\d+) checks=(\d+) fails=(\d+) rec_commit_ok=(\d+) rec_fail=(\d+) stream_edges=(\d+) serial_edges=(\d+)", text)
        values = dict(zip(("drives", "checks", "fails", "rec_commit_ok", "rec_fail", "stream_edges", "serial_edges"), map(int, match.groups()))) if match else {}
        passed = bool(re.search(r"^SLICE_PASS", text, re.M)) and bool(match) and values["fails"] == values["rec_fail"] == 0 and values["checks"] > 0
        rows[name] = dict(verdict="PASS" if passed else ("FAIL" if text else "NO_RUN"),
                          scope=replay.get("scope", "component_probe"),
                          qualifies_native_layer=replay.get("qualifies_native_layer", False),
                          qualifies_native_chain=replay.get("qualifies_native_chain", False),
                          replay_sha256=hashlib.sha256((out / "rj" / f"{name}.json").read_bytes()).hexdigest(),
                          priced_layer_cycles=replay.get("priced_layer_cycles"), events=len(replay["events"]), **values)
    manifests = {}
    for pattern in ("emit/**/manifest.json", "qemit/**/manifest.json"):
        for path in sorted(out.glob(pattern)):
            data = json.loads(path.read_text())
            manifests[str(path.relative_to(out))] = {k: data[k] for k in ("scope", "counts", "qualifies_native_layer", "qualifies_native_chain") if k in data}
    grade = "RTL-functional (source assembly)" if mode == "source" else "RTL-functional (GEN composition; source children)"
    result = dict(schema="opentallas.tok_func_hbm.v2", grade=grade, src_rev=rev,
                  contract=str(contract), contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),
                  replays=rows, emission=manifests, qualifies_full_token=False,
                  token_verdict="INCOMPLETE", replay_verdict="PASS" if rows and all(x["verdict"] == "PASS" for x in rows.values()) else "FAIL",
                  mapped_netlist_rerun="BLOCKED until frozen mapped hierarchy and simulation libraries are supplied; GEN top with source children is RTL evidence",
                  note="SW SU component probes only. format_open and unsupported operators prevent layer/chain/full-token qualification; priced cycles are schedule targets, not measured token cycles.")
    (out / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("source", "gen_rtl"), required=True)
    parser.add_argument("--rev", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("replays", nargs="+")
    args = parser.parse_args()
    result = report(args.out, args.mode, args.rev, args.contract, args.replays)
    print("REPORT", result["replay_verdict"], "token=INCOMPLETE", args.out / "report.json")
    return 0 if result["replay_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
