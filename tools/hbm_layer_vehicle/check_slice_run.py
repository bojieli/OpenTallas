#!/usr/bin/env python3
"""Check replay completeness for preserved slice binaries, without rebuilding.

The original TB could print SLICE_PASS before every domain's scheduled events
executed, and readmemh could truncate a replay larger than its compiled NEV.
Compare the actual counts and per-record commit checks to the *whole* hdr.mem,
independently of the binary's event depth. This validates a slice replay only;
it does not turn a partial slice into layer or token qualification.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


FAULT_OUTPUT_PORTS = {
    'fault', 'pc_fault', 'owner_fault_split', 'lg_fault', 's_fault',
    'schedule_fault', 'tgt_fault', 'share_fault', 'ring_fault', 'fault_cause', 'program_fault',
}


def fault_activity(replay, log, boundary=None, tb_source=None):
    """Reject activity only on actual declared fault outputs with zero observers.

    The generated observer is initialized to zero and samples after stream
    reset. A reported change therefore proves nonzero fault activity occurred;
    the lack of a report does not qualify a native programme or its arithmetic.
    """
    if boundary is None and tb_source is None:
        candidates = [replay, replay.parent, replay.parent.parent, Path.cwd()/'slice']
        for parent in candidates:
            if (parent/'boundary.json').is_file() and (parent/'tb_slice.sv').is_file():
                boundary, tb_source = parent/'boundary.json', parent/'tb_slice.sv'
                break
    errors = []
    if boundary is None or tb_source is None:
        return dict(source_bound=False, errors=['missing source-bound fault observer boundary/TB']), errors
    boundary, tb_source = Path(boundary), Path(tb_source)
    b = json.loads(boundary.read_text())
    source = tb_source.read_text()
    block = re.search(r'always @\(posedge ck0\) if \(rs0\) begin(.*?)if \(cnt\[0\] >= cycles\) begin',
                      source, re.S)
    outputs = []
    for k, port in enumerate(b['outputs']):
        driver_port = port['driver'].rsplit('.', 1)[-1]
        if driver_port not in FAULT_OUTPUT_PORTS:
            if 'fault' in driver_port.split('_'):
                errors.append('unclassified declared output fault semantics: '+port['name'])
            continue
        name = port['name']
        initial = f"reg [{port['width']-1}:0] po{k} = '0; integer f{k} = -1, l{k} = -1, n{k} = 0;"
        tracking = (f"if ({name} != po{k}) begin if (f{k} < 0) f{k} = cnt[0]; "
                    f"l{k} = cnt[0]; n{k} = n{k} + 1; po{k} = {name}; end")
        reporting = f'if (n{k} > 0) $display("SLICE_OUT {name} first=%0d last=%0d changes=%0d", f{k}, l{k}, n{k});'
        if initial not in source or block is None or tracking not in block[1] or reporting not in source:
            errors.append('unverified zero/reset-scoped fault observer: '+name)
        outputs.append(name)
    if not outputs:
        errors.append('boundary has no classified observable fault outputs')
    changes = []
    for name, first, last, count in re.findall(r'^SLICE_OUT (\S+) first=(\d+) last=(\d+) changes=(\d+)$', log, re.M):
        if name in outputs and int(count)>0:
            changes.append(dict(port=name, first=int(first), last=int(last), changes=int(count)))
            errors.append(f'declared fault output changed from zero: {name} ({count} changes)')
    return dict(source_bound=bool(outputs) and block is not None and
                not any(e.startswith(('unverified', 'unclassified')) for e in errors),
                boundary_sha256=hashlib.sha256(boundary.read_bytes()).hexdigest(),
                tb_source_sha256=hashlib.sha256(tb_source.read_bytes()).hexdigest(),
                declared_fault_outputs=outputs, observed_activity=changes,
                absence_claim='no stronger native/arithmetic proof from missing activity alone'), errors


def check_run(replay, run_log, scope="component_probe", boundary=None, tb_source=None):
    replay, run_log = Path(replay), Path(run_log)
    headers = [int(line.strip(), 16) for line in (replay / "hdr.mem").read_text().splitlines() if line.strip()]
    events = [h for h in headers if h >> 62 in (1, 2)]
    expected = Counter("drives" if h >> 62 == 1 else "checks" for h in events)
    commits = Counter(((((h >> 32) & 0xfff) - 1), h & 0xffffffff)
                      for h in events if h >> 62 == 2 and (h >> 32) & 0xfff)
    domains = {0: "stream_edges", 1: "serial_edges", 2: "hbm_edges"}
    last = {domains[d]: max([h & 0xffffffff for h in events if (h >> 60) & 3 == d] + [-1]) for d in domains}
    log = run_log.read_text()
    summaries = re.findall(r"^SLICE_SUMMARY (.+)$", log, re.M)
    summary = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", summaries[-1])} if summaries else {}
    actual_commits = Counter((int(r), int(c)) for r, c in re.findall(r"^SLICE_REC rec=(\d+) cyc=(\d+) COMMIT_OK$", log, re.M))
    errors = []
    fault_observation, fault_errors = fault_activity(replay, log, boundary, tb_source)
    errors.extend(fault_errors)
    if scope != "component_probe":
        errors.append("native layer/chain qualification refused: replay completeness only proves a component probe")
    if len(summaries) != 1:
        errors.append(f"expected one SLICE_SUMMARY, found {len(summaries)}")
    if len(re.findall(r"^SLICE_PASS$", log, re.M)) != 1 or re.search(r"^SLICE_(FAIL|CHECK_FAIL)\b", log, re.M):
        errors.append("missing unique SLICE_PASS or explicit failure")
    if not expected["checks"]:
        errors.append("replay has no checks (idle smoke is not exactness evidence)")
    for field in ("drives", "checks"):
        if summary.get(field) != expected[field]:
            errors.append(f"{field}: executed {summary.get(field)}, expected {expected[field]}")
    for field in ("fails", "rec_fail"):
        if summary.get(field) != 0:
            errors.append(f"{field}: {summary.get(field)}")
    for field, cycle in last.items():
        if summary.get(field, -1) < cycle:
            errors.append(f"{field}: stopped at {summary.get(field)}, last scheduled event {cycle}")
    if actual_commits != commits or summary.get("rec_commit_ok") != sum(commits.values()):
        errors.append("per-record commit checks differ from the complete replay schedule")
    index_path = replay / "index.json"
    index = {}
    if index_path.exists():
        index = json.loads(index_path.read_text())
        for field, n in (("events", len(events)), ("drives", expected["drives"]), ("checks", expected["checks"])):
            if index.get(field) != n:
                errors.append(f"replay index {field} differs from hdr.mem")
        if "vm_preload_words" in index:
            loaded = re.findall(r"^SLICE_VM_PRELOAD words=(\d+)$", log, re.M)
            if loaded != [str(index["vm_preload_words"])]:
                errors.append(f"VM preload words: executed {loaded}, expected {index['vm_preload_words']}")
        for inst, n in index.get("hbm_preload_sectors", {}).items():   # HBM image replays (sm_slice_lower)
            got = re.findall(rf"^HBM_MODEL_PRELOAD {re.escape(inst)} sectors=(\d+) ", log, re.M)
            if got != [str(n)]:
                errors.append(f"HBM preload {inst}: loaded {got}, expected {n}")
    return {"schema": "opentallas.hbm_slice_run_check.v1", "scope": "component_probe", "requested_scope": scope,
            "qualifies_native_layer": False, "qualifies_native_chain": False,
            "state_seed_provenance": index.get("state_seed_provenance", ["unspecified"]),
            "passed": not errors, "errors": errors, "expected": dict(expected),
            "last_scheduled_cycles": last, "summary": summary,
            "expected_record_checks": sum(commits.values()),
            "replay_hdr_sha256": hashlib.sha256((replay / "hdr.mem").read_bytes()).hexdigest(),
            "run_log_sha256": hashlib.sha256(run_log.read_bytes()).hexdigest(),
            "fault_observation": fault_observation}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay", type=Path, required=True)
    ap.add_argument("--run-log", type=Path, required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--boundary", type=Path, help="exact compiled boundary manifest (auto-discovered beside slice)")
    ap.add_argument("--tb-source", type=Path, help="exact compiled generated TB with zero/reset-scoped observers")
    ap.add_argument("--scope", choices=["component_probe", "native_layer", "native_chain"], default="component_probe")
    a = ap.parse_args()
    result = check_run(a.replay, a.run_log, scope=a.scope, boundary=a.boundary, tb_source=a.tb_source)
    payload = json.dumps(result, indent=2) + "\n"
    if a.out:
        a.out.write_text(payload)
    print(payload, end="")
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
