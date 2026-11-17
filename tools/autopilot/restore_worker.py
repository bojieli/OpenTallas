#!/usr/bin/env python3
"""restore_worker (FLEET-OPS-R, COORD 11-17): runs on rtx-pro (localhost) from cron, COPY ONLY.  Reads the hub's RESTORE-NEEDED queue over ssh, pushes each hash-checked file from
~/signed-export-1114 to the named fleet host, appends a done row on the hub.  No key leaves rtx-pro, nothing signed is mirrored on the fleet beyond the one requested file.
usage: restore_worker.py [--hub hub] [--export ~/signed-export-1114] [--dry]"""
import argparse, json, os, shlex, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import export_restore as E

QUEUE = ".local/state/restore_needed.jsonl"
DONE = ".local/state/restore_done.jsonl"


def ssh_read(hub, rel):
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=20", hub, f"cat ~/{rel} 2>/dev/null"], capture_output=True, text=True, timeout=120)
    return [json.loads(x) for x in r.stdout.splitlines() if x.strip().startswith("{")]


def push(host, src, dst):
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=20", host]
    if src is None:
        if subprocess.run(ssh + [f"mkdir -p {shlex.quote(dst)}"], capture_output=True).returncode:
            raise OSError("mkdir failed")
        return
    if subprocess.run(ssh + [f"mkdir -p {shlex.quote(os.path.dirname(dst))}"], capture_output=True).returncode:
        raise OSError("mkdir failed")
    r = subprocess.run(["rsync", "-a", "--ignore-existing", "-e", "ssh -o BatchMode=yes -o ControlPath=none", src, f"{host}:{dst}"], capture_output=True)
    if r.returncode:
        raise OSError("rsync failed")
    h = subprocess.run(ssh + [f"sha256sum {shlex.quote(dst)}"], capture_output=True, text=True).stdout.split()
    if not h or h[0] != E.sha256_file(src):
        raise OSError("sha256 mismatch after the copy")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hub", default="hub"); ap.add_argument("--export", default=os.path.expanduser("~/signed-export-1114")); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    q, d = ssh_read(a.hub, QUEUE), ssh_read(a.hub, DONE)
    todo = E.pending(q, d)
    print(f"queue {len(q)} pending {len(todo)}")
    if not todo or a.dry:
        return 0
    done = E.work(q, d, E.load_index(a.export), a.export, push)
    if done:
        text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in done)
        subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none", a.hub, f"mkdir -p ~/.local/state && cat >> ~/{DONE}"], input=text, text=True, timeout=120)
    for r in done:
        print(r["status"], r["host"], r["path"][-70:], r.get("why", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
