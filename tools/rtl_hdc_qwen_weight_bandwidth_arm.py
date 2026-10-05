#!/usr/bin/env python3
"""Run one compiled reduced Qwen weight arm from a pinned image directory."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--steps", type=int, default=2)
    ap.add_argument("--wrate", type=int, required=True)
    ap.add_argument("--log", type=Path, required=True)
    args = ap.parse_args()
    command = [str(args.exe.resolve()), f"+DIR={args.images.resolve()}",
               "+SYSTEM_MULTI", "+NPROMPT=16", "+NGEN=3",
               f"+STOPSTEP={args.steps}",
               *(args.images / "hbm.args").read_text().split(),
               f"+WRATE={args.wrate}"]
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("w") as stream:
        try:
            rc = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=3600, check=False).returncode
        except subprocess.TimeoutExpired:
            rc = 124
    meta = {"command": command, "returncode": rc, "binary_sha256": sha(args.exe),
            "image_sha256": {p.name: sha(p) for p in args.images.iterdir() if p.is_file()},
            "log_sha256": sha(args.log)}
    args.log.with_suffix(args.log.suffix + ".json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    print(args.log, "pass" if rc == 0 else "fail", flush=True)
    return 0 if rc == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
