#!/usr/bin/env python3
"""Replay checkpoint QE FP8/paired-FP4 local qtile ROM banks through RTL."""
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

RECORD=ROOT/"results/rtl/v41x_qe_local_tile_bank_l0.json"
SHARD=ROOT/"results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
RTL=ROOT/"rtl/chip/ot_chip_v41x_qtile_pair_bank.sv"
TB=ROOT/"rtl/test/tb_chip_v41x_qtile_pair_bank.sv"
OUT=ROOT/"results/rtl/hdc_v41x_qtile_pair_bank.json"


def digest(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cap()->None:
    n=3*1024**3
    resource.setrlimit(resource.RLIMIT_AS,(n,n))


def make_expected(src:dict,source_dir:Path,name:str)->np.ndarray:
    codes,scales,fp4=Q.source_matrix(src,source_dir,name)
    nrows=320 if name=="wq_a" else 576
    if fp4:
        payload=codes.reshape(nrows,20,8,16)
        scale=scales.reshape(nrows,20,8)
        words=np.zeros((nrows,20,8,33),dtype=np.uint8)
        words[:,:,:,:16]=payload
    else:
        payload=codes.reshape(nrows,20,8,32)
        scale=np.repeat(scales,32,axis=0).reshape(nrows,20,8)
        words=np.zeros((nrows,20,8,33),dtype=np.uint8)
        words[:,:,:,:32]=payload
    words[:,:,:,32]=scale
    return words.reshape(nrows*20,8,33)


def write_hex(path:Path,arr:np.ndarray)->None:
    with path.open("w") as out:
        for row in arr:
            out.write(row.tobytes()[::-1].hex()+"\n")


def main()->None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-images",type=Path,required=True)
    ap.add_argument("--tile-images",type=Path,required=True)
    args=ap.parse_args()
    local=json.loads(RECORD.read_text())
    source=json.loads(SHARD.read_text())
    if local["macro_type"]!="ot_rom_8192x274_m8" or len(local["macros"])!=16:
        raise ValueError("unexpected local qtile bank manifest")
    with tempfile.TemporaryDirectory(prefix="v41_qtile_pair_") as td:
        work=Path(td)
        with (work/"banks.hex").open("w") as out:
            for m in local["macros"]:
                p=args.tile_images/m["image_file"]
                if digest(p)!=m["image_sha256"]: raise ValueError(f"stale macro image {p}")
                raw=np.frombuffer(p.read_bytes(),dtype=np.uint8).reshape(8192,35)
                for row in raw:
                    value=int.from_bytes(row.tobytes(),"little")
                    if value>>274: raise ValueError("nonzero macro image padding")
                    out.write(f"{value:069x}\n")
        for name,fmt in (("wq_a","fp8"),("exp110.w1","fp4")):
            write_hex(work/f"expected_{fmt}.hex",make_expected(source,args.source_images,name))
        sim=work/"sim.vvp"
        compile=subprocess.run(["iverilog","-g2012","-s","tb_chip_v41x_qtile_pair_bank",
                                "-o",str(sim),str(RTL),str(TB)],cwd=ROOT,
                               capture_output=True,text=True,timeout=60,preexec_fn=cap)
        if compile.returncode: raise RuntimeError("compile failed:\n"+compile.stderr[-2500:])
        run=subprocess.run(["vvp",str(sim),f"+DIR={work}"],cwd=ROOT,
                           capture_output=True,text=True,timeout=180,preexec_fn=cap)
        match=re.search(r"QTILE_PAIR_PASS lanes=(\d+) skew_lanes=(\d+) fp8_beats=6400 fp4_beats=11520",run.stdout)
        if run.returncode or not match or tuple(map(int,match.groups()))!=(143360,143360):
            raise RuntimeError("simulation failed:\n"+run.stdout[-2500:]+run.stderr[-500:])
    record={"schema":"opentallas.rtl.v41x_qtile_pair_bank.v1","status":"pass",
            "claim_scope":"One local qtile bank layout: 8 FP8 plus 8 paired-FP4 274-bit macros, 143360 checkpoint lane reads exact into 8x264 qtile operand in aligned and real qtile-skew schedules, with zero bank conflicts. No ptile hookup, complete die binpack, route or rate claim.",
            "fp8_beats":6400,"fp4_beats":11520,"lane_reads":143360,
            "skew_lane_reads":143360,
            "memory_cap_bytes":3*1024**3,
            "source_sha256":{str(p.relative_to(ROOT)):digest(p) for p in
                             (RECORD,SHARD,RTL,TB,Path(__file__),ROOT/"tools/v41_fullshape_qe_stream_image.py")}}
    OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print("PASS: 143,360 checkpoint local qtile lane reads exact")


if __name__=="__main__":main()
