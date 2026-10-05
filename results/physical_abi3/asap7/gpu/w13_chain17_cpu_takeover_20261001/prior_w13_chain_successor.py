#!/usr/bin/env python3
"""W13-only successor: wait for pinned column jobs, qualify, commit, harden.

Run from an immutable bundle beside w13_column_corner_gate.py and config.json.
Never resumes the parked predecessor or removes remote work directories.
"""
import argparse
import concurrent.futures
import datetime
import fcntl
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import time

if __package__ in (None, ""):
    from w13_column_corner_gate import CHIP, check, digest
else:
    from tools.w13_column_corner_gate import CHIP, check, digest


def identity(pid):
    try:
        text = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        return {"pid": pid, "start_ticks": text[19], "state": text[0]}
    except FileNotFoundError:
        return None


def running(handle):
    current = identity(handle["pid"])
    return current is not None and current["start_ticks"] == handle["start_ticks"] and current["state"] != "Z"


def parked(config):
    for handle in config["predecessor"]:
        current = identity(handle["pid"])
        if current is None or current["start_ticks"] != handle["start_ticks"] or current["state"] not in ("T", "t"):
            raise RuntimeError("predecessor no longer parked at pinned identity")


def event(config, name, **details):
    line = json.dumps({"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "event": name, **details}, sort_keys=True)
    with Path(config["events"]).open("a") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def qualify(root, block, expected_sources):
    result = check(root, block, expected_sources)
    path = root / CHIP / "blocks" / f"{block}.json"
    if not path.is_file():
        result["issues"].append("missing_block_record")
    else:
        record = json.loads(path.read_text())
        result["block_record_sha256"] = digest(path)
        if record.get("block") != block or record.get("clock_period_ns") != 0.833 or record.get("closed_against_budget") is not True:
            result["issues"].append("block_boundary_or_clock_not_closed")
        metrics = record.get("metrics", {})
        for metric in ("drc_errors", "antenna_violating_nets", "max_cap_violations", "max_fanout_violations", "max_slew_violations"):
            if metrics.get(metric) != 0:
                result["issues"].append("block:" + metric)
        if metrics.get("flow_errors") != {}:
            result["issues"].append("block:flow_errors")
        corners_path = root / CHIP / "corners" / f"{block}.json"
        if corners_path.is_file() and record.get("sources") != json.loads(corners_path.read_text()).get("sources"):
            result["issues"].append("block_corner_source_identity_mismatch")
        for view in ("lef", "liberty"):
            artifact = record.get("abstract", {}).get(view, {})
            target = root / artifact.get("path", "missing")
            if not target.is_file() or digest(target) != artifact.get("sha256"):
                result["issues"].append("block_abstract_pin_mismatch:" + view)
    result["passed"] = not result["issues"]
    return result


def audits(branch, destination=None):
    return [qualify(Path(destination or c["root"]), c["block"], c["sources"]) for c in branch["columns"]]


def copy_block(root, dest, block):
    paths = [CHIP / kind / f"{block}.json" for kind in ("blocks", "boundary", "corners")]
    paths.extend(p.relative_to(root) for p in (root / CHIP / "abstracts" / block).iterdir() if p.is_file())
    for relative in paths:
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    return [str(path) for path in paths]


def run_branch(config, branch):
    name = branch["name"]
    event(config, "waiting", branch=name, handles=branch["handles"])
    while any(running(h) for h in branch["handles"]):
        parked(config)
        time.sleep(10)
    parked(config)
    rows = audits(branch)
    event(config, "column_gate", branch=name, audits=rows)
    if not all(r["passed"] for r in rows):
        event(config, "blocked", branch=name, reason="column qualification failed; no SM launch")
        return False
    dest = Path(branch["destination"])
    if dest.exists():
        raise RuntimeError(f"refusing to reuse destination {dest}")
    subprocess.run(["git", "-C", config["repository"], "worktree", "add", "--detach", str(dest), config["base"]], check=True)
    files = []
    for column in branch["columns"]:
        root, block = Path(column["root"]), column["block"]
        files.extend(copy_block(root, dest, block))
    receipt_tool = Path(config['receipt_tool'])
    if digest(receipt_tool) != config['bundle_pins'][str(receipt_tool)]:
        raise RuntimeError('receipt tool changed')
    for tool in (receipt_tool, Path(config['gate_tool'])):
        target = dest / 'tools' / tool.name
        shutil.copyfile(tool, target)
        files.append(str(target.relative_to(dest)))
    copied = audits(branch, dest)
    if copied != rows:
        raise RuntimeError("copied column evidence differs from qualified source")
    audit = CHIP / "w13_chain16" / f"{name}_columns.json"
    (dest / audit).parent.mkdir(parents=True, exist_ok=True)
    (dest / audit).write_text(json.dumps({"columns": copied, "config_sha256": config["config_sha256"]}, indent=2) + "\n")
    files.append(str(audit))
    subprocess.run(["git", "add", "--", *files], cwd=dest, check=True)
    subprocess.run(["git", "commit", "-m", f"W13b chain16: qualified {name} column evidence before SM hardening"], cwd=dest, check=True)
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=dest):
        raise RuntimeError("SM launch worktree is not clean")
    parked(config)
    if not all(r["passed"] for r in audits(branch, dest)):
        raise RuntimeError("final destination gate failed")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dest, text=True).strip()
    # Price from the pinned destination's actual block definition, never the old 55 GiB floor.
    peak = float(subprocess.check_output(['python3', '-c',
        'from tools.chip_assembly.floorplans import BLOCKS; print(BLOCKS[' + repr(branch['sm']) + '].peak_gb)'], cwd=dest, text=True))
    minimum = math.ceil(max(peak, branch['minimum_gib']))
    if minimum < 60 or peak != branch['validated_peak_gib']:
        raise RuntimeError('SM modeled peak differs from validated admission contract')
    work = branch["remote_work"]
    commands = ["export LD_LIBRARY_PATH=/home/ubuntu/.local/w13lib", f"test ! -e {shlex.quote(work)}", f"mkdir -p {shlex.quote(work)}"]
    admission_dir = 'results/physical_abi3/asap7/chip/w13_chain16'
    commands.append(shlex.join(['mkdir', '-p', admission_dir]))
    commands.append(shlex.join(['python3', 'tools/w13_floorplan_receipt.py', '--admission-only',
        '--local-memory', '--lease-floor-gib', str(minimum), '--output', admission_dir + '/' + branch['sm'] + '_admission.json']))
    for phase in ("synth", "pnr", "corners"):
        args = ["python3", "tools/chip_assembly/harden.py", "--block", branch["sm"], "--work", work, "--phase", phase]
        if phase == "pnr":
            args.extend(["--budget", branch["budget"]])
        commands.append(shlex.join(args))
    env = {**os.environ, "OT_CHIP_PERIOD_NS": "0.833", "OT_REMOTE_NATIVE": "1", "OT_GATE_EXCLUDE": config["exclude"], "OT_GATE_MIN_GB": str(minimum)}
    event(config, "launch_sm", branch=name, commit=head, destination=str(dest), remote_work=work, minimum_gib=minimum, validated_peak_gib=peak)
    with Path(branch["log"]).open("x") as log:
        job = subprocess.Popen([config["remote_gate"], "bash", "-c", " && ".join(commands)], cwd=dest, env=env, stdout=log, stderr=subprocess.STDOUT)
        event(config, "sm_handle", branch=name, handle=identity(job.pid))
        rc = job.wait()
    event(config, "sm_finished", branch=name, rc=rc)
    sm = qualify(dest, branch["sm"], branch["sm_sources"])
    event(config, "sm_qualification", branch=name, audit=sm)
    # Retain returned verdicts, including failures, by explicit path.
    returned = subprocess.check_output(["git", "ls-files", "-m", "-o", "--exclude-standard", "--", "results"], cwd=dest, text=True).splitlines()
    if returned:
        subprocess.run(["git", "add", "--", *returned], cwd=dest, check=True)
        subprocess.run(["git", "commit", "-m", f"W13b chain16: {name} SM returned evidence rc={rc}, qualified={sm['passed']}"], cwd=dest, check=True)
    return rc == 0 and sm["passed"]


def floorplan(config):
    parked(config)
    dest = Path(config["floorplan_destination"])
    if dest.exists():
        raise RuntimeError("refusing to reuse floorplan destination")
    subprocess.run(["git", "-C", config["repository"], "worktree", "add", "--detach", str(dest), config["base"]], check=True)
    files = []
    for branch in config["branches"]:
        source = Path(branch["destination"])
        for block in [c["block"] for c in branch["columns"]] + [branch["sm"]]:
            files.extend(copy_block(source, dest, block))
        if not all(r["passed"] for r in audits(branch, dest)) or not qualify(dest, branch["sm"], branch["sm_sources"])["passed"]:
            raise RuntimeError("copied floorplan evidence did not qualify")
    subprocess.run(["git", "add", "--", *files], cwd=dest, check=True)
    subprocess.run(["git", "commit", "-m", "W13b chain16: qualified SM records for die floorplans"], cwd=dest, check=True)
    from w13_floorplan_receipt import receipt
    event(config, "floorplan_start", destination=str(dest))
    with Path(config["floorplan_log"]).open("x") as log:
        rc = subprocess.run(["python3", "tools/hbm_gpu_floorplan.py"], cwd=dest, stdout=log, stderr=subprocess.STDOUT).returncode
    companion = receipt(dest, dest / 'results/floorplan/hbm_gpu')
    companion_path = dest / 'results/floorplan/hbm_gpu/actual_sm_companion_receipt.json'
    companion_path.write_text(json.dumps(companion, indent=2) + '\n')
    event(config, 'floorplan_companion', passed=companion['passed'], path=str(companion_path), sha256=digest(companion_path))
    returned = subprocess.check_output(["git", "ls-files", "-m", "-o", "--exclude-standard", "--", "results/floorplan/hbm_gpu"], cwd=dest, text=True).splitlines()
    if returned:
        subprocess.run(["git", "add", "--", *returned], cwd=dest, check=True)
        subprocess.run(["git", "commit", "-m", f"W13b chain16: floorplan evidence rc={rc}"], cwd=dest, check=True)
    event(config, "floorplan_finished", rc=rc, companion_passed=companion['passed'])
    if rc != 0 or not companion['passed']:
        raise RuntimeError('floorplan or actual SM LEF companion gate failed; evidence preserved')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    config["config_sha256"] = digest(args.config)
    for path, pin in config["bundle_pins"].items():
        if digest(Path(path)) != pin:
            raise RuntimeError("bundle pin mismatch:" + path)
    with Path(config["lock"]).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        parked(config)
        event(config, "successor_start", handle=identity(os.getpid()), config_sha256=config["config_sha256"])
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_branch, config, branch) for branch in config["branches"]]
            passed = [future.result() for future in futures]
        if all(passed):
            floorplan(config)
        event(config, "successor_finished", branches_passed=passed, floorplan="completed" if all(passed) else "blocked by SM qualification")


if __name__ == "__main__":
    main()
