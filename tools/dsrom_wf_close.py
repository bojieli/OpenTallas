#!/usr/bin/env python3
"""DS-ROM wavefront package controller closure (ot_rom_pkg_ctrl_wfc, WAVE=1) at 1.2 GHz, in context.

  route   one instance through tools/run_abi3_physical.py (ORFS, CORNER=WC synthesis/repair, hold repair at
          WC+BC, 833 ps, 60 ps setup / 25 ps hold uncertainty, IO at 20 % of the period, ADDER_MAP_FILE off),
          without the driver's wall-clock ceilings; then per-corner signoff STA on 6_final.odb + RCX spef
          (SS RVT libs: setup; FF RVT libs: hold) with tools/qwen_async_seq_incontext_physical.py sta.
              python3 tools/dsrom_wf_close.py route --inst src|stg --run-dir D [--util 40]
  record  results/rtl/dsrom_wf_close_20261004/record.json from the route dirs, the equivalence logs and the
          screens.
              python3 tools/dsrom_wf_close.py record --dir D --out record.json

Instances (FULL_SHAPE die parameters, rtl/chip/ckvsel/ot_chip_v41x_die.sv): FLIT 512, NW 21, AW 30, VWA 15,
USER_W 10, MAXU 866, KVW 32768, WIN 6.  src = SOURCE 1 (embedding package: wavefront issue, verify, squash);
stg = SOURCE 0 (a stage package: HIDDEN rewind by up to WIN); RX/TX payload words of the L20 package (41 / 46).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = "rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv"
COMMON = dict(WAVE=1, WIN=6, FLIT=512, NW=21, AW=30, VWA=15, USER_W=10, MAXU=866, KVW=32768,
              SEND_HIDDEN=1, HID_DEST=1, FWD_TOKEN=1)
INST = {"src": dict(COMMON, SOURCE=1, XWORDS=41, RXWORDS=41),
        "stg": dict(COMMON, SOURCE=0, XWORDS=46, RXWORDS=41)}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cmd_route(a):
    out = a.run_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("OT_ORFS_NUM_CORES", "20")
    drv = module("wf_physical", ROOT / "tools/run_abi3_physical.py")
    drv.run = lambda cmd, *, cwd=None, timeout=None: subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    drv.flow_timeout_seconds = lambda: None
    drv.synth_timeout_seconds = lambda: None
    args = ["--view", "asap7", "--top", "ot_rom_pkg_ctrl_wfc", "--source", SRC,
            "--clock-period-ns", "0.833", "--clock-uncertainty-ns", "0.060", "--clock-uncertainty-hold-ns", "0.025",
            "--orfs-corner", "WC", "--hold-corners", "WC,BC", "--stages", "pnr", "--io-delay-fraction", "0.2",
            "--max-transition-ns", "library", "--max-fanout", "32", "--core-utilization", str(a.util),
            "--nickname-tag", a.inst, "--keep-workdir", str(out / "work"), "--output", str(out / "physical.json")]
    for k, v in INST[a.inst].items():
        args += ["--param", f"{k}={v}"]
    for kv in a.orfs_var:
        args += ["--orfs-var", kv]
    (out / "route_args.json").write_text(json.dumps(dict(args=args, source_sha256=sha(ROOT / SRC)), indent=1))
    rc = drv.main(args)
    nick = None
    for p in (out / "work").rglob("6_final.odb"):
        nick = p.parent.parent.name
        break
    sta = None
    if nick:
        r = subprocess.run([sys.executable, str(ROOT / "tools/qwen_async_seq_incontext_physical.py"), "sta",
                            "--workdir", str(out / "work"), "--nickname", nick, "--out", str(out / "sta.json")],
                           capture_output=True, text=True)
        (out / "sta.log").write_text(r.stdout + r.stderr)
        sta = r.returncode
    (out / "done.json").write_text(json.dumps(dict(route_rc=rc, nickname=nick, sta_rc=sta)) + "\n")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("route")
    r.add_argument("--inst", choices=sorted(INST), required=True)
    r.add_argument("--run-dir", type=Path, required=True)
    r.add_argument("--util", type=float, default=40)
    r.add_argument("--orfs-var", action="append", default=[])
    a = ap.parse_args()
    {"route": cmd_route}[a.cmd](a)


if __name__ == "__main__":
    main()
