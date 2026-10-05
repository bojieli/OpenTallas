#!/usr/bin/env python3
"""Checkpoint-exact FP8/FP4 compact ROM word to QE operand gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import sys
import tempfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import v41_fullshape_qe_stream_image as Q  # noqa: E402

MANIFEST=ROOT/"results/rtl/hdc_v41x_fullshape_qe_stream_200k_l0_rank0.json"
SHARD=ROOT/"results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
RTL=ROOT/"rtl/hdc/v41x/ot_hdc_v41x_qrom_compact_word.sv"
TB=ROOT/"rtl/test/tb_hdc_v41x_qrom_compact_word.sv"
OUT=ROOT/"results/rtl/hdc_v41x_qrom_compact_word.json"
CASES=("wq_a","exp110.w1")


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cap()->None:
    limit=3*1024**3
    resource.setrlimit(resource.RLIMIT_AS,(limit,limit))


def hex_words(path:Path,array:np.ndarray)->None:
    with path.open("w") as out:
        for row in array.reshape(array.shape[0],-1):
            out.write(row.tobytes()[::-1].hex()+"\n")


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-images",type=Path,required=True)
    ap.add_argument("--packed-images",type=Path,required=True)
    args=ap.parse_args()
    manifest=json.loads(MANIFEST.read_text())
    source=json.loads(SHARD.read_text())
    fixtures={}
    with tempfile.TemporaryDirectory(prefix="v41_qrom_compact_") as td:
        temp=Path(td)
        for name in CASES:
            item=manifest["matrices"][name]
            packed=args.packed_images/item["image_file"]
            if not packed.is_file() or sha(packed)!=item["image_sha256"]:
                raise ValueError(f"physical packed QE image is stale: {name}")
            codes,scales,fp4=Q.source_matrix(source,args.source_images,name)
            logical,physical,geom=Q.pack_stream(codes,scales,fp4)
            if (len(physical),sha(packed),hashlib.sha256(logical.tobytes()).hexdigest()) != (
                item["word_count"],item["image_sha256"],item["logical_stream_sha256"]):
                raise ValueError(f"logical QE image is stale: {name}")
            if physical.tobytes()!=packed.read_bytes():
                raise ValueError(f"packed QE source differs from checkpoint: {name}")
            prefix="fp4" if fp4 else "fp8"
            hex_words(temp/f"{prefix}_physical.hex",physical)
            hex_words(temp/f"{prefix}_logical.hex",logical)
            fixtures[name]={"physical_sha256":item["image_sha256"],
                            "logical_sha256":item["logical_stream_sha256"],
                            "words":geom["word_count"],"bytes_per_physical_word":physical.shape[1]*physical.shape[2]}
        verilator=str(Path.home()/".local/opentallas-tools/verilator-5.050/bin/verilator")
        obj=temp/"obj"
        cmd=[verilator,"--binary","--timing","-Wno-fatal","-Wno-TIMESCALEMOD",
             "--top-module","tb_hdc_v41x_qrom_compact_word","-Mdir",str(obj),
             str(RTL),str(TB),"-j","4"]
        build=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=180,preexec_fn=cap)
        if build.returncode:
            raise RuntimeError("build failed:\n"+build.stderr[-3000:])
        sim=subprocess.run([str(obj/"Vtb_hdc_v41x_qrom_compact_word"),f"+DIR={temp}"],
                           cwd=ROOT,capture_output=True,text=True,timeout=60,preexec_fn=cap)
        match=re.search(r"QROM_COMPACT_PASS words=(\d+) fp8=(\d+) fp4=(\d+)",sim.stdout)
        if sim.returncode or not match or tuple(map(int,match.groups()))!=(10240,3840,6400):
            raise RuntimeError("simulation failed:\n"+sim.stdout[-2000:]+sim.stderr[-1000:])
    record={"schema":"opentallas.rtl.v41x_qrom_compact_word.v1","status":"pass",
            "claim_scope":"Checkpoint-exact 16-lane FP8 and compact-FP4 ROM word decode into QE's logical 16x272 operand for wq_a and expert110.w1. No 274-bit tile bank-address integration, complete die capacity, timing, or token verdict.",
            "words_checked":10240,"memory_cap_bytes":3*1024**3,"fixtures":fixtures,
            "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in
                             (MANIFEST,SHARD,RTL,TB,ROOT/"tools/v41_fullshape_qe_stream_image.py",Path(__file__))}}
    OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print("PASS: 3,840 FP8 and 6,400 FP4 checkpoint ROM words exact")


if __name__=="__main__":
    main()
