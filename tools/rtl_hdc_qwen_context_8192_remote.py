#!/usr/bin/env python3
"""Stage and durably run the pinned Qwen 8K binary/image on a remote VM."""
import argparse
import json
import shlex
import subprocess
import time
from pathlib import Path

import rtl_hdc_qwen_context_8192 as GATE


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def remote_sha(host, paths):
    command = "sha256sum " + " ".join(shlex.quote(str(p)) for p in paths)
    lines = run(["ssh", "-o", "BatchMode=yes", host, command]).splitlines()
    if len(lines) != len(paths):
        raise RuntimeError("remote sha256sum did not return one digest per file")
    entries = [line.split(maxsplit=1) for line in lines]
    if any(len(entry) != 2 or len(entry[0]) != 64 for entry in entries):
        raise RuntimeError("malformed remote sha256sum output")
    return {Path(path.lstrip("*")).name: digest for digest, path in entries}


def wait_for_image(work, timeout):
    prepared = work / "prepared_image.json"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if prepared.is_file():
            try:
                rec = json.loads(prepared.read_text())
            except json.JSONDecodeError:
                time.sleep(5)
                continue
            if rec.get("status") != "prepared" or rec.get("phase") != "image":
                raise RuntimeError("image preparation did not pass")
            return rec
        failed = work / "prepared_result.json"
        if failed.is_file():
            try:
                rec = json.loads(failed.read_text())
            except json.JSONDecodeError:
                rec = {}
            if rec.get("status") == "fail":
                raise RuntimeError(f"image preparation failed: {rec.get('error')}")
        time.sleep(30)
    raise TimeoutError("image preparation did not finish")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workdir", type=Path, default=Path("/tmp/qwen_context_8192"))
    ap.add_argument("--host", default="ot-pve2")
    ap.add_argument("--remote-dir", default="/tmp/qwen_context_8192")
    ap.add_argument("--wait-seconds", type=int, default=43200)
    ap.add_argument("--session", default="qwen_ctx8192")
    args = ap.parse_args()
    work = args.workdir.resolve()
    prepared = wait_for_image(work, args.wait_seconds)
    if prepared["configuration"]["context_positions"] != 8192:
        raise RuntimeError("prepared image is not context 8192")
    for name, digest in prepared["source_sha256"].items():
        if GATE.sha(GATE.ROOT / name) != digest:
            raise RuntimeError(f"source pin differs: {name}")
    model = GATE.ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
    if GATE.sha(model) != prepared["model_sha256"]:
        raise RuntimeError("model pin differs")
    for name, digest in prepared["image_sha256"].items():
        if GATE.sha(work / "img" / name) != digest:
            raise RuntimeError(f"image pin differs: {name}")
    binary = work / "obj_ctx8192_w16384_lead32768_qd16_room4/Vtb_hdc_core"
    binary_digest = GATE.sha(binary)
    images = sorted(prepared["image_sha256"])
    run(["ssh", "-o", "BatchMode=yes", args.host, "mkdir -p " + shlex.quote(args.remote_dir + "/img")])
    run(["rsync", "-a", str(binary), f"{args.host}:{args.remote_dir}/Vtb_hdc_core"])
    run(["rsync", "-a", str(work / "img") + "/", f"{args.host}:{args.remote_dir}/img/"])
    remote_paths = [args.remote_dir + "/Vtb_hdc_core", *(args.remote_dir + "/img/" + name for name in images)]
    digests = remote_sha(args.host, remote_paths)
    if digests.pop("Vtb_hdc_core") != binary_digest:
        raise RuntimeError("remote binary differs")
    if digests != prepared["image_sha256"]:
        raise RuntimeError("remote image differs")
    manifest = {"host": args.host, "directory": args.remote_dir,
                "binary_sha256": binary_digest, "image_sha256": digests,
                "run_args": (work / "img/run.args").read_text().strip()}
    (work / "remote_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("remote binary/image hashes verified", flush=True)
    has_session = subprocess.run(["ssh", "-o", "BatchMode=yes", args.host,
                                  "tmux has-session -t " + shlex.quote(args.session)],
                                 capture_output=True)
    if has_session.returncode == 0:
        raise RuntimeError("remote session already exists")
    inner = ("cd " + shlex.quote(args.remote_dir) + " && ./Vtb_hdc_core " +
             "+DIR=" + shlex.quote(args.remote_dir + "/img") + " " +
             " ".join(shlex.quote(arg) for arg in manifest["run_args"].split()) +
             " > remote_stdout.log 2> remote_stderr.log; " +
             "rc=$?; printf '%s\\n' \"$rc\" > remote_exitcode")
    run(["ssh", "-o", "BatchMode=yes", args.host,
         "tmux new-session -d -s " + shlex.quote(args.session) + " " + shlex.quote(inner)])
    print("remote tmux session launched:", args.session, flush=True)
    deadline = time.monotonic() + args.wait_seconds
    while time.monotonic() < deadline:
        probe = subprocess.run(["ssh", "-o", "BatchMode=yes", args.host,
                                "test -f " + shlex.quote(args.remote_dir + "/remote_exitcode")],
                               capture_output=True)
        if probe.returncode == 0:
            break
        time.sleep(60)
    else:
        raise TimeoutError("remote RTL run did not finish")
    for name in ("remote_stdout.log", "remote_stderr.log", "remote_exitcode"):
        run(["rsync", "-a", f"{args.host}:{args.remote_dir}/{name}", str(work / name)])
    print("remote run complete; collecting", flush=True)
    collector = GATE.ROOT / "tools/rtl_hdc_qwen_context_8192_collect.py"
    return subprocess.run(["python3", str(collector), "--workdir", str(work),
                           "--remote-host", args.host, "--remote-dir", args.remote_dir,
                           "--output", str(work / "result.json")], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
