#!/usr/bin/env python3
"""Report current-wave cache/ownership gaps; propose only explicitly approved recoveries.

This command never changes jobs, caches, holds or retry lists. Its recovery TSV rows
can be reviewed and added to the existing kit_wave_pending.tsv mechanism. Private
jobs cannot be inferred from AP state: an approval must explicitly record that check.
"""
import argparse
import csv
import fnmatch
import json
from pathlib import Path
import re
import subprocess


TERMINAL = {"CANCELLED", "WITHDRAWN", "ARCHIVED", "REJECTED", "SIGNED", "SIGNED-UNVERSIONED",
            "TRIAL-SIGNED", "GRT-DONE", "CTS-DONE", "PASS", "FAIL", "CRASH"}


def terminal(status):
    return bool(status) and (status in TERMINAL or status.startswith("DONE-"))


def completed(job, settings, item):
    status = job.get("status", "")
    counted = settings.get("counted_items") or ()
    return status in {"SIGNED", "SIGNED-UNVERSIONED", "TRIAL-SIGNED", "GRT-DONE", "CTS-DONE", "PASS"} \
        or any(fnmatch.fnmatchcase(item or "", pattern) for pattern in counted)


def block_of(key, record):
    if record.get("block_sha"):
        return record["block_sha"]
    tail = key.rsplit("|", 1)[-1]
    return tail[1:] if re.fullmatch(r"b[0-9a-f]{12,64}", tail) else ""


def current_record(key, record, stages):
    block = block_of(key, record)
    return bool(block) and any(
        row.get("plan_current") == "yes" and row.get("die") == record.get("die")
        and row.get("item") == record.get("item") and row.get("block_sha")
        and block.startswith(row["block_sha"]) for row in stages)


def approval_for(approvals, die, item, attempt):
    return next((a for a in approvals if a.get("die") == die and a.get("item") == item
                 and a.get("attempt") == attempt), None)


def approved(approval, die, merged):
    return bool(approval and approval.get("live_checked") is True and approval.get("reason")
                and re.fullmatch(r"[0-9a-f]{7,40}", approval.get("sha", ""))
                and approval.get("scope") in ("hub", "src")
                and merged(approval["sha"], approval["scope"], die))


def report(wave, ap_state, config, stages, required_types=None, approvals=(), merged=lambda *a: False):
    items = wave.get("items", {})
    jobs = ap_state.get("jobs", {})
    live = {}
    for job_id, job in jobs.items():
        die, item = job.get("die"), job.get("type") or job.get("item")
        if die and item and not terminal(job.get("status")):
            live.setdefault((die, item), []).append(job_id)
    for key, record in items.items():
        if record.get("status") == "RUNNING" and not record.get("q_id"):
            live.setdefault((record.get("die"), record.get("item")), []).append("wave:" + key)

    caches, recoveries, updates, holds = [], [], [], []
    for key, record in items.items():
        job_id = record.get("q_id")
        job = jobs.get(job_id, {})
        if record.get("q_status") != "RUNNING" or not terminal(job.get("status")):
            continue
        die, item, attempt = record.get("die"), record.get("item"), record.get("attempt")
        current = current_record(key, record, stages)
        alternatives = live.get((die, item), [])
        approval = approval_for(approvals, die, item, attempt)
        done = completed(job, (config.get("dies") or {}).get(die, {}), item)
        can_recover = current and not done and not alternatives and approved(approval, die, merged)
        caches.append({"key": key, "die": die, "item": item, "attempt": attempt, "q_id": job_id,
                       "cached": "RUNNING", "actual": job["status"], "current": current,
                       "record_status": record.get("status"), "completed": done, "live_alternatives": alternatives,
                       "recovery_approved": bool(can_recover)})
        # A cache correction describes the exact terminal job; it is not a failed verdict rewrite.
        updates.append({"key": key, "expected_q_id": job_id, "expected_q_status": "RUNNING",
                        "q_status": job["status"]})
        if can_recover:
            reason = " ".join(approval["reason"].split())
            recoveries.append("\t".join((approval["sha"], approval["scope"], die,
                                         f"{item}@{attempt}", approval.get("lane", "OPERATOR"), reason)))

    for die, settings in (config.get("dies") or {}).items():
        for item, reason in (settings.get("hold_items") or {}).items():
            matching = [(k, v) for k, v in items.items() if v.get("die") == die
                        and fnmatch.fnmatchcase(v.get("item", ""), item)]
            latest = max(matching, key=lambda kv: kv[1].get("updated", 0), default=("", {}))[1]
            job = jobs.get(latest.get("q_id"), {})
            current = any(current_record(k, v, stages) for k, v in matching)
            # Absence from a stage cache does not prove a required type obsolete.
            required = any(fnmatch.fnmatchcase(name, item) for name in required_types.get(die, ())) \
                if required_types is not None else (True if current else None)
            approval = approval_for(approvals, die, item, latest.get("attempt"))
            alternatives = sorted({job for (job_die, name), values in live.items() if job_die == die
                                   and fnmatch.fnmatchcase(name, item) for job in values})
            done = any(completed(jobs.get(v.get("q_id"), {}), settings, v.get("item")) for _, v in matching)
            clear = required is True and not done and not alternatives and approval and approval.get("clear_hold") is True \
                and approved(approval, die, merged)
            holds.append({"die": die, "item": item, "required_type": required, "current_record": current,
                          "record_status": latest.get("status"), "job_status": job.get("status"),
                          "q_id": latest.get("q_id"), "attempt": latest.get("attempt"), "reason": reason,
                          "live_alternatives": alternatives, "completed": done, "clear_approved": bool(clear)})
    return {"summary": {"terminal_caches": len(caches),
                        "current_terminal_caches": sum(x["current"] for x in caches),
                        "required_type_holds": sum(x["required_type"] is True for x in holds),
                        "approved_recoveries": len(recoveries)},
            "terminal_caches": caches, "cache_updates": updates, "holds": holds,
            "recovery_rows": sorted(set(recoveries))}


def add_arguments(parser):
    parser.add_argument("--root", default=str(Path.home() / "coord/autopilot"))
    parser.add_argument("--required-types", "--required-items", dest="required_types",
                        help="JSON {die: [actual required plan type/core names]}; optional")
    parser.add_argument("--approved-fixes", help="JSON approvals with die,item,attempt,sha,scope,reason,live_checked")
    parser.add_argument("--repo", help="repository for actual source/hub ancestry checks; no recovery without it")
    parser.add_argument("--out", help="write a report; jobs/config/state remain untouched")


def command(args):
    root = Path(args.root)
    load = lambda name: json.loads((root / name).read_text())
    config = load("kit_wave.json")
    stages = list(csv.DictReader((root / "kit_wave_stages.tsv").open(), delimiter="\t"))
    required = json.loads(Path(args.required_types).read_text()) if args.required_types else None
    approvals = json.loads(Path(args.approved_fixes).read_text()) if args.approved_fixes else ()

    def merged(sha, scope, die):
        if not args.repo:
            return False
        tip = "origin/main" if scope == "hub" else (config.get("dies", {}).get(die) or {}).get("src_sha")
        return bool(tip) and subprocess.run(["git", "-C", args.repo, "merge-base", "--is-ancestor", sha, tip],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    result = report(load("kit_wave_state.json"), load("state.json"), config, stages, required, approvals, merged)
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text)
    else:
        print(text, end="")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return command(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
