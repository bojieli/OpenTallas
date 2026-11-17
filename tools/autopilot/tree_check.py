"""Durable source-tree checks shared by separate autopilot oneshot processes.

A completed check is keyed by exact die, tree, manifest, hosts and checker bytes.
Workers run in independent user units; no verification lifetime depends on a daemon
thread in the calling tick. Each attempt keeps its own spec and log.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp." + str(os.getpid()))
    tmp.write_text(json.dumps(obj, sort_keys=True, indent=1) + "\n")
    os.replace(tmp, path)


def identity(die, tree, want, hosts, checker):
    return dict(die=die, tree=tree, manifest_hash=want, hosts=sorted(set(hosts)),
                checker_sha256=hashlib.sha256(Path(checker).read_bytes()).hexdigest())


def location(root, ident):
    key = hashlib.sha256(json.dumps(ident, sort_keys=True).encode()).hexdigest()
    return Path(root) / key


def active(unit):
    if not unit:
        return False
    try:
        r = subprocess.run(["systemctl", "--user", "show", "-p", "ActiveState", "--value", unit],
                           capture_output=True, text=True, timeout=15)
        return r.returncode == 0 and r.stdout.strip() in ("active", "activating", "reloading", "deactivating")
    except (OSError, subprocess.SubprocessError):
        return False


def read(root, ident, active_fn=active):
    path = location(root, ident) / "result.json"
    try:
        d = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if d.get("identity") != ident:
        return None
    if d.get("running") and not active_fn(d.get("unit")):
        d["running"] = False
    return d


def launch(root, ident, checker, main_sha, links_only=False, launcher=None):
    folder = location(root, ident)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "launch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        old = read(root, ident) or {}
        if old.get("running") or (old.get("state") == "ok" and old.get("full_ok") and not links_only):
            return old
        stamp = str(time.time_ns())
        unit = "ot-treecheck-" + folder.name[:20] + "-" + stamp[-10:]
        checker_bytes = Path(checker).read_bytes()
        if hashlib.sha256(checker_bytes).hexdigest() != ident["checker_sha256"]:
            raise ValueError("checker changed while preparing its immutable snapshot")
        pinned = folder / ("src_manifest-" + ident["checker_sha256"] + ".py")
        helper_bytes = Path(__file__).read_bytes()
        helper_sha = hashlib.sha256(helper_bytes).hexdigest()
        worker = folder / ("worker-" + helper_sha + ".py")
        for target, payload in ((pinned, checker_bytes), (worker, helper_bytes)):
            if not target.exists() or target.read_bytes() != payload:
                temp = target.with_name(target.name + ".tmp." + str(os.getpid()))
                temp.write_bytes(payload)
                os.replace(temp, target)
        spec = dict(identity=ident, result=str(folder / "result.json"), checker=str(pinned),
                    main_sha=main_sha, links_only=links_only, attempt=stamp, unit=unit,
                    log=str(folder / (stamp + ".log")))
        specfile = folder / (stamp + ".json")
        atomic_json(specfile, spec)
        pending = dict(old, identity=ident, running=True, unit=unit, attempt=stamp, t=time.time())
        pending.setdefault("state", "cheap")
        atomic_json(folder / "result.json", pending)
        argv = ["systemd-run", "--user", "--quiet", "--collect", "--unit=" + unit,
                "--property=Type=exec", "--property=StandardOutput=append:" + spec["log"],
                "--property=StandardError=append:" + spec["log"],
                sys.executable, "-I", str(worker), "--worker", str(specfile)]
        run = launcher or (lambda args: subprocess.run(args, capture_output=True, text=True, timeout=30))
        try:
            r = run(argv)
            if r.returncode and not active(unit):
                pending.update(state="bad", running=False, why=(r.stderr or r.stdout or "")[-300:])
                atomic_json(folder / "result.json", pending)
        except (OSError, subprocess.SubprocessError) as exc:
            pending.update(state="bad", running=False, why=str(exc)[-300:])
            atomic_json(folder / "result.json", pending)
        return pending


def worker(specfile):
    spec = json.loads(Path(specfile).read_text())
    ident = spec["identity"]
    prior_path = Path(spec["result"])
    try:
        prior = json.loads(prior_path.read_text())
    except (OSError, ValueError):
        prior = {}
    details, rc = [], 0
    for host in ident["hosts"]:
        base = [sys.executable, "-I", spec["checker"], "hosts", ident["tree"], "--hosts", host]
        if spec["links_only"]:
            p = subprocess.run(base + ["--links-only"], capture_output=True, text=True)
            details.append(dict(host=host, basis="links", rc=p.returncode, output=(p.stdout + p.stderr)[-3000:]))
        else:
            # Publication already completed a content hash on many hosts. Reuse
            # that exact successful receipt only while its inventory/signature,
            # immutable modes and unshared inodes still match.
            p = subprocess.run(base + ["--expect", ident["manifest_hash"], "--cached-receipts"],
                               capture_output=True, text=True)
            basis = "published-verification-receipt"
            if p.returncode:
                details.append(dict(host=host, basis="cache-miss", rc=p.returncode,
                                    output=(p.stdout + p.stderr)[-1000:]))
                p = subprocess.run(base + ["--expect", ident["manifest_hash"]],
                                   capture_output=True, text=True)
                basis = "full-verification"
            details.append(dict(host=host, basis=basis, rc=p.returncode, output=(p.stdout + p.stderr)[-3000:]))
        rc |= bool(p.returncode)
    now = time.time()
    result = dict(prior, identity=ident, running=False, unit=spec["unit"], attempt=spec["attempt"],
                  t=now, state="bad" if rc else "ok", details=details)
    if not rc:
        result.pop("why", None)  # failed attempt evidence remains in its immutable *.result.json
        result["links_t"] = now
        if not spec["links_only"]:
            result.update(full_ok=True, verified_t=now, main_sha=spec.get("main_sha", ""))
    else:
        result["why"] = " | ".join(d["output"][-250:] for d in details if d["rc"])[-800:]
    # A stale worker may preserve its own evidence, never replace a newer result.
    evidence = prior_path.parent / (spec["attempt"] + ".result.json")
    atomic_json(evidence, result)
    try:
        current = json.loads(prior_path.read_text())
    except (OSError, ValueError):
        current = {}
    if current.get("attempt") == spec["attempt"]:
        atomic_json(prior_path, result)
    print(json.dumps(dict(identity=ident, state=result["state"], full_ok=result.get("full_ok", False),
                          attempt=spec["attempt"])), flush=True)
    return 1 if rc else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", required=True)
    raise SystemExit(worker(ap.parse_args().worker))
