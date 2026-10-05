#!/usr/bin/env python3
"""Exact three-client shared-K request and tagged-response gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[ROOT/p for p in ("rtl/chip/ot_chip_v41x_kv_reqmux.sv",
                           "rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv",
                           "rtl/test/tb_chip_v41x_kv_rope_reqmux.sv")]
OUT=ROOT/"results/rtl/v41x_kv_rope_reqmux.json"


def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cap()->None:
    n=4*1024**3
    resource.setrlimit(resource.RLIMIT_AS,(n,n))


def main()->None:
    with tempfile.TemporaryDirectory(prefix="v41_kv_rope_mux_") as td:
        temp=Path(td)
        verilator=str(Path.home()/".local/opentallas-tools/verilator-5.050/bin/verilator")
        cmd=[verilator,"--binary","--timing","-Wno-fatal","-Wno-TIMESCALEMOD",
             "--top-module","tb_chip_v41x_kv_rope_reqmux","-Mdir",str(temp/"obj"),
             *map(str,SOURCES),"-j","4"]
        build=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,
                             timeout=120,preexec_fn=cap)
        if build.returncode:
            raise RuntimeError("build failed:\n"+build.stderr[-3000:])
        sim=subprocess.run([str(temp/"obj/Vtb_chip_v41x_kv_rope_reqmux")],cwd=ROOT,
                           capture_output=True,text=True,timeout=30,preexec_fn=cap)
        match=re.search(r"KV_ROPE_MUX_PASS grants=(\d+) rope_grants=(\d+) wait=(\d+)",sim.stdout)
        if sim.returncode or not match or tuple(map(int,match.groups()))!=(3,1,2):
            raise RuntimeError("simulation failed:\n"+sim.stdout[-2000:]+sim.stderr[-1000:])
    rec={"schema":"opentallas.rtl.v41x_kv_rope_reqmux.v1","status":"pass",
         "claim_scope":"One-stack three-client contention and response-owner demultiplexing through the shared K request channel; other stacks replicate this arbitration. No PHY timing or full die token claim.",
         "grants":3,"rope_grants":1,"rope_wait_cycles":2,
         "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in [*SOURCES,Path(__file__)]}}
    OUT.write_text(json.dumps(rec,indent=2)+"\n")
    print(json.dumps({"status":"pass","grants":3,"rope_wait_cycles":2}))


if __name__=="__main__":
    main()
