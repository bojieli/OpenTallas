#!/usr/bin/env python3
"""Real RoPE coefficients through the shared KV and indexer K HBM path."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

from rtl_v41x_rope_hbm_cache import CONFIG, emit_fixture, cap

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[ROOT/p for p in (
    "rtl/chip/ot_chip_v41x_rope_hbm_cache.sv",
    "rtl/chip/ot_chip_v41x_rope_su_word.sv",
    "rtl/chip/ot_chip_v41x_kv_reqmux.sv",
    "rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv",
    "rtl/chip/ot_chip_v41x_hbm_karb.sv",
    "rtl/test/tb_chip_v41x_rope_shared_k.sv",
)]
OUT=ROOT/"results/rtl/v41x_rope_shared_k.json"


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main()->None:
    with tempfile.TemporaryDirectory(prefix="v41_rope_shared_k_") as td:
        temp=Path(td)
        fixture=emit_fixture(temp)
        obj=temp/"obj"
        verilator=str(Path.home()/".local/opentallas-tools/verilator-5.050/bin/verilator")
        cmd=[verilator,"--binary","--timing","-O0","-Wno-fatal","-Wno-TIMESCALEMOD",
             "--top-module","tb_chip_v41x_rope_shared_k","-Mdir",str(obj),
             *map(str,SOURCES),"-CFLAGS","-O0","-j","4"]
        start=time.monotonic()
        build=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,
                             timeout=300,preexec_fn=cap)
        if build.returncode:
            raise RuntimeError("build failed:\n"+build.stderr[-4000:])
        sim=subprocess.run([str(obj/"Vtb_chip_v41x_rope_shared_k"),f"+DIR={temp}"],
                           cwd=ROOT,capture_output=True,text=True,timeout=30,preexec_fn=cap)
        match=re.search(r"ROPE_SHARED_K_PASS sectors=(\d+) pairs=(\d+) su_reads=(\d+) rope_wait=(\d+) cycles=(\d+)",sim.stdout)
        if sim.returncode or not match or tuple(map(int,match.groups()[:3]))!=(8,32,64) or int(match.group(4))<1:
            raise RuntimeError("simulation failed:\n"+sim.stdout[-3000:]+sim.stderr[-2000:])
        record={
            "schema":"opentallas.rtl.v41x_rope_shared_k.v1",
            "status":"pass",
            "claim_scope":"Real 200K plain FP32 coefficients through four-stack RoPE cache, three-client KV/RoPE mux, K-versus-indexer arbiter, timed sector replies, and 64 SU cosine/sine operand reads. No full token or HBM PHY silicon timing claim.",
            "sectors_received":8,"coefficient_pairs":32,"su_operand_reads":64,
            "rope_wait_cycles":int(match.group(4)),
            "simulation_cycles":int(match.group(5)),
            "build_seconds":round(time.monotonic()-start,2),
            "fixture":fixture["plain200k"],
            "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in
                             [*SOURCES,CONFIG,ROOT/"tools/hdc_golden_v41.py",Path(__file__)]},
        }
    OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"pass","sectors":8,"rope_wait_cycles":record["rope_wait_cycles"]}))


if __name__=="__main__":
    main()
