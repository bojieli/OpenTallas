#!/usr/bin/env python3
"""Passive W13 terminal intake: archive returned column evidence, never dispatch.

Waits for exact producer wrapper identities to finish (including remote copyback).
Commits only new archive paths in the configured stream worktree. Qualification
and all scientific launches remain exclusively with the authoritative chain.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

CHIP = Path("results/physical_abi3/asap7/chip")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        return {"pid": pid, "start_ticks": fields[19], "state": fields[0]}
    except FileNotFoundError:
        return None


def handle_live(handle):
    current = identity(handle["pid"])
    return current is not None and current["start_ticks"] == handle["start_ticks"] and current["state"] != "Z"


def archive(job, destination, config_pin):
    root, block = Path(job["root"]), job["block"]
    destination.mkdir(parents=True, exist_ok=False)
    paths = [CHIP / kind / f"{block}.json" for kind in ("blocks", "boundary", "corners")]
    paths += [p.relative_to(root) for p in (root / CHIP / "abstracts" / block).glob("*") if p.is_file()]
    copied = []
    for relative in paths:
        source = root / relative
        if not source.is_file():
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        pin = digest(target)
        copied.append({"path": str(relative), "sha256": pin,
                       "changed_since_attachment": pin != job["initial_artifact_sha256"].get(str(relative))})
    log = Path(job["wrapper_log"])
    if log.is_file():
        shutil.copyfile(log, destination / "wrapper.log")
    sources = {s: digest(root / s) if (root / s).is_file() else None for s in job["source_sha256"]}
    corner = destination / CHIP / "corners" / f"{block}.json"
    corners = json.loads(corner.read_text()) if corner.is_file() else None
    corner_changed = any(p["path"] == str(corner.relative_to(destination)) and p["changed_since_attachment"] for p in copied)
    record = {"schema": "opentallas.w13.column_terminal_intake.v1",
              "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "block": block, "producer_handle": job["handle"], "producer_source_commit": job["source_commit"],
              "config_sha256": config_pin, "artifacts": copied, "source_sha256": sources,
              "source_pin_mismatches": [s for s, pin in sources.items() if pin != job["source_sha256"][s]],
              "fresh_corner_record": corner_changed,
              "producer_claimed_closed_signoff": corners.get("closed_signoff") if corners else None,
              "wrapper_log_sha256": digest(destination / "wrapper.log") if log.is_file() else None,
              "qualification": "not performed by collector; authoritative chain must qualify all corners, boundaries, sources and resources before dispatch",
              "status": "returned_corner_evidence" if corner_changed else "producer_ended_without_new_corner_record"}
    (destination / "intake.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    pin = digest(args.config)
    if digest(Path(__file__)) != config["tool_sha256"]:
        raise RuntimeError("intake tool pin mismatch")
    with Path(config["lock"]).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        pending = list(config["jobs"])
        while pending:
            for job in pending[:]:
                if handle_live(job["handle"]):
                    continue
                dest = Path(config["output"]) / job["block"]
                result = archive(job, dest, pin)
                stream = Path(config["stream_worktree"])
                if subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=stream):
                    raise RuntimeError("archive retained; refusing commit while another change is staged")
                files = [str(p.relative_to(stream)) for p in dest.rglob("*") if p.is_file()]
                subprocess.run(["git", "add", "--", *files], cwd=stream, check=True)
                subprocess.run(["git", "commit", "-m", f"W13b: archive {job['block']} terminal intake ({result['status']})"], cwd=stream, check=True)
                with Path(config["events"]).open("a") as events:
                    events.write(json.dumps({"block": job["block"], "archive": str(dest), "status": result["status"]}) + "\n")
                pending.remove(job)
            if pending:
                time.sleep(10)


if __name__ == "__main__":
    main()
