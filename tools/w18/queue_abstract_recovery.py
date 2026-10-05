#!/usr/bin/env python3
"""Queue read-only recovery after an existing route AND its old continuation exit.

Uses the existing remote_gate resource leases, restricted to the checkpoint's
host. Never launches synthesis/P&R, moves the checkpoint, or changes its source.
The tool worktree must already exist at the same clean pin on both machines.
"""
import argparse
import importlib.util
import json
import os
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from recover_abstract import sha


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", required=True)
    ap.add_argument("--route-log", type=Path, required=True)
    ap.add_argument("--after-pid", type=int, required=True)
    ap.add_argument("--tool-worktree", type=Path, required=True)
    ap.add_argument("--expected-tool-commit", required=True)
    ap.add_argument("--orfs-dir", required=True)
    ap.add_argument("--route-record", required=True)
    ap.add_argument("--source-root", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--macro", action="append", required=True)
    ap.add_argument("--output-dir", required=True, help="new worker output directory")
    ap.add_argument("--queue-dir", type=Path, required=True, help="new local progress directory")
    ap.add_argument("--timeout-seconds", type=int, default=86400)
    a = ap.parse_args()
    root = a.tool_worktree.resolve()
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True).strip()
    if head != a.expected_tool_commit or dirty:
        ap.error("queue must run from the clean pinned tool worktree")
    a.queue_dir.mkdir(parents=True, exist_ok=False)
    progress = dict(pid=os.getpid(), host=a.host, tool_commit=head, tool_sha256=sha(__file__),
                    route_log=str(a.route_log), after_pid=a.after_pid, adopted=False,
                    started_at=datetime.now(timezone.utc).isoformat())
    def state(value):
        progress["state"] = value
        p = a.queue_dir / "live.json"
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(progress, indent=2) + "\n")
        tmp.replace(p)
    state("WAITING_EXISTING_ROUTE_AND_CONTINUATION")
    start = time.monotonic()
    while True:
        if time.monotonic() - start > a.timeout_seconds:
            state("TIMEOUT_NO_RELAUNCH")
            return 1
        terminal = a.route_log.is_file() and any(x.startswith("EXIT ") for x in a.route_log.read_text().splitlines())
        if terminal and not Path(f"/proc/{a.after_pid}").exists():
            break
        time.sleep(30)
    gate_path = Path("/tmp/claude-1000/remote_gate.py")
    spec = importlib.util.spec_from_file_location("gate", gate_path)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    progress["resource_gate_sha256"] = sha(gate_path)
    os.environ["OT_GATE_EXCLUDE"] = ",".join(h for h in gate.load_pool() if h != a.host)
    state("WAITING_HOST_8GB_LEASE")
    host, leases = gate.acquire(8, str(root))
    try:
        if host != a.host:
            raise RuntimeError("resource gate selected a different checkpoint host")
        q = shlex.quote
        # Verify the worker tool snapshot too; never reset or clean a live source.
        check = f"test $(git -C {q(str(root))} rev-parse HEAD) = {q(head)} && test -z \"$(git -C {q(str(root))} status --porcelain)\""
        cmd = ["python3", str(root / "tools/w18/recover_abstract.py"), "--extract",
               "--orfs-dir", a.orfs_dir, "--route-record", a.route_record,
               "--source-root", a.source_root, "--name", a.name, "--output-dir", a.output_dir]
        for m in a.macro:
            cmd.extend(["--macro", m])
        state("RECOVERING_READ_ONLY")
        with (a.queue_dir / "worker.log").open("w") as log:
            result = gate.ssh(host, check + " && " + shlex.join(cmd), stdout=log, stderr=subprocess.STDOUT)
        progress["returncode"] = result.returncode
        fetch = gate.ssh(host, "cat " + q(a.output_dir + "/recovery.json"), capture_output=True, text=True)
        if fetch.returncode == 0:
            (a.queue_dir / "recovery.json").write_text(fetch.stdout)
        state("DONE_DIAGNOSTIC_ONLY" if result.returncode == 0 else "BLOCKED_OR_FAILED_NO_RETRY")
        return result.returncode
    finally:
        for lease in leases:
            lease.close()


if __name__ == "__main__":
    raise SystemExit(main())
