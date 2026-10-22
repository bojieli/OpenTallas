#!/usr/bin/env python3
"""Report HBM replay evidence without promoting partial SU probes to token passes."""
import argparse
import hashlib
import json
import re
from pathlib import Path


LAYER_RE = re.compile(r"^(ds_l\d+|qw_(?:l0|chain)_r\d+)")


def rungs(rows):
    """Per-layer / chain / token rungs.  A layer qualifies only when every part passes AND every part's emission
    qualifies the native layer (no format_open / unsupported records); measured cycles are the sum of the parts'
    executed stream edges (parts are independent finite-calendar replays, so the sum is the replayed span, not a
    priced layer time)."""
    layers = {}
    for name, row in rows.items():
        m = LAYER_RE.match(name)
        key = m.group(1) if m else name
        layers.setdefault(key, []).append((name, row))
    out = {}
    for key, parts in sorted(layers.items()):
        verdicts = [r["verdict"] for _, r in parts]
        all_pass = all(v == "PASS" for v in verdicts)
        native = all(r.get("qualifies_native_layer") for _, r in parts)
        out[key] = dict(parts=[n for n, _ in parts], pass_parts=sum(v == "PASS" for v in verdicts),
                        fail_parts=[n for n, r in parts if r["verdict"] != "PASS"],
                        stream_cycles=sum(r.get("stream_edges", 0) for _, r in parts),
                        serial_cycles=sum(r.get("serial_edges", 0) for _, r in parts),
                        checks=sum(r.get("checks", 0) for _, r in parts),
                        rung=("LAYER_PASS" if all_pass and native else
                              "PARTS_PASS_LAYER_INCOMPLETE" if all_pass else "PART_FAIL"))
    chain = "INCOMPLETE" if not any(r.get("qualifies_native_chain") for r in rows.values()) else (
        "PASS" if all(r["verdict"] == "PASS" for r in rows.values() if r.get("qualifies_native_chain")) else "FAIL")
    return out, chain


def report(out, mode, rev, contract, names, binary=None, binary_sha256=None):
    rows = {}
    for name in names:
        replay = json.loads((out / "rj" / f"{name}.json").read_text())
        log = out / "runs" / name / "run.log"
        text = log.read_text(errors="replace") if log.exists() else ""
        match = re.search(r"SLICE_SUMMARY drives=(\d+) checks=(\d+) fails=(\d+) rec_commit_ok=(\d+) rec_fail=(\d+) stream_edges=(\d+) serial_edges=(\d+)", text)
        values = dict(zip(("drives", "checks", "fails", "rec_commit_ok", "rec_fail", "stream_edges", "serial_edges"), map(int, match.groups()))) if match else {}
        hbm = re.search(r"hbm_edges=(\d+)", text)
        if hbm:
            values["hbm_edges"] = int(hbm.group(1))
        acc_path = out / "runs" / name / "acceptance.json"
        acc = json.loads(acc_path.read_text()) if acc_path.exists() else None
        if acc is not None:
            values["acceptance_passed"] = acc.get("passed")
            values["acceptance_errors"] = acc.get("errors", [])[:8]
        fail_recs = sorted({int(r) for r in re.findall(r"^SLICE_REC rec=(\d+) cyc=\d+ FAIL", text, re.M)})
        if fail_recs:
            values["failing_records"] = fail_recs
            values["first_check_fail"] = (re.search(r"^SLICE_CHECK_FAIL.*$", text, re.M) or [None])[0]
        passed = bool(re.search(r"^SLICE_PASS", text, re.M)) and bool(match) and values["fails"] == values["rec_fail"] == 0 and values["checks"] > 0 \
            and (acc is None or acc.get("passed") is True)
        rows[name] = dict(verdict="PASS" if passed else ("FAIL" if text else "NO_RUN"),
                          scope=replay.get("scope", "component_probe"),
                          qualifies_native_layer=replay.get("qualifies_native_layer", False),
                          qualifies_native_chain=replay.get("qualifies_native_chain", False),
                          replay_sha256=hashlib.sha256((out / "rj" / f"{name}.json").read_bytes()).hexdigest(),
                          priced_layer_cycles=replay.get("priced_layer_cycles"), events=replay["events"] if isinstance(replay["events"], int) else len(replay["events"]), **values)
    manifests = {}
    for pattern in ("emit/**/manifest.json", "qemit/**/manifest.json", "pay/*_parts.json"):
        for path in sorted(out.glob(pattern)):
            data = json.loads(path.read_text())
            manifests[str(path.relative_to(out))] = {k: data[k] for k in ("scope", "counts", "qualifies_native_layer", "qualifies_native_chain", "shared_calendar_epochs", "emitted_fraction") if k in data}
    layers, chain = rungs(rows)
    grade = "RTL-functional (source assembly)" if mode == "source" else "RTL-functional (GEN composition; source children)"
    result = dict(schema="opentallas.tok_func_hbm.v2", grade=grade, src_rev=rev,
                  contract=str(contract), contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),
                  binary=binary, binary_sha256=binary_sha256,
                  replays=rows, layers=layers, chain_verdict=chain, emission=manifests, qualifies_full_token=False,
                  token_verdict="INCOMPLETE", replay_verdict="PASS" if rows and all(x["verdict"] == "PASS" for x in rows.values()) else "FAIL",
                  mapped_netlist_rerun="BLOCKED until frozen mapped hierarchy and simulation libraries are supplied; GEN top with source children is RTL evidence",
                  note="SW SU and HC/COLL component probes only; payloads retain explicit fixture/far-end provenance and do not connect produced data across units. format_open and unsupported operators prevent layer/chain/full-token qualification; priced cycles are schedule targets, not measured token cycles.")
    (out / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mode", choices=("source", "gen_rtl"), required=True)
    parser.add_argument("--rev", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--binary")
    parser.add_argument("--binary-sha256")
    parser.add_argument("replays", nargs="+")
    args = parser.parse_args()
    result = report(args.out, args.mode, args.rev, args.contract, args.replays, args.binary, args.binary_sha256)
    for key, lay in result["layers"].items():
        print("LAYER", key, lay["rung"], f"{lay['pass_parts']}/{len(lay['parts'])} parts", f"stream_cycles={lay['stream_cycles']}", "fail=" + ",".join(lay["fail_parts"]))
    print("REPORT", result["replay_verdict"], "token=INCOMPLETE", args.out / "report.json")
    return 0 if result["replay_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
