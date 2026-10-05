#!/usr/bin/env python3
"""Checkpoint-exact bounded ME HBM bank service for two L0 wo_a prefixes.

This exercises the eight skewed weight-bank ports at ML=2. It does not run
the arithmetic core or claim full 65,536-address operation throughput.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/"rtl/hdc/hbm/ot_hdc_v41x_me_bank_hbm_service.sv"
TB=ROOT/"rtl/test/tb_hdc_v41x_me_bank_hbm_service.sv"
MANIFEST_COMMIT="5bae99aa"
MANIFEST_PATH="results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json"
PASS=re.compile(r"ME_HBM_PASS bank_reads=(\d+) fp32_values=(\d+) requests=(\d+) "
                r"responses=(\d+) first_ready=(\d+) service_cycles=(\d+) max_credit=(\d+)")
WORDS=1024


def sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def sha(path:Path)->str:
    return sha_bytes(path.read_bytes())


def call(cmd:list[str],cwd:Path)->str:
    p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=300)
    if p.returncode:
        raise RuntimeError(f"{cmd[0]} failed:\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    return p.stdout


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--image",type=Path,default=Path("/tmp/v41_fullshape_rank0_rom_images/wo_a.me.bin"))
    ap.add_argument("--scratch",type=Path,default=Path("/tmp/v41-me-hbm-service"))
    ap.add_argument("--output",type=Path,default=ROOT/"results/rtl/hdc_v41x_me_bank_hbm_service.json")
    args=ap.parse_args()
    manifest_bytes=subprocess.run(["git","show",f"{MANIFEST_COMMIT}:{MANIFEST_PATH}"],
                                  cwd=ROOT,check=True,capture_output=True).stdout
    manifest=json.loads(manifest_bytes)
    mat=manifest["matrices"]["wo_a"]
    blob=args.image.read_bytes()
    assert mat["base_word"]==7680 and mat["word_count"]==131072
    assert mat["output_image_sha256"]==sha_bytes(blob) and len(blob)==131072*256
    ops={}
    for op,offset,base,hbase in (("wo_a_0",0,7680,0x100000),
                                  ("wo_a_1",65536,73216,0x200000)):
        d=args.scratch/op
        d.mkdir(parents=True,exist_ok=True)
        sector_words=[]
        for c in range(8):
            for w in range(WORDS):
                row=blob[(offset+w)*256:(offset+w+1)*256]
                sector=b"".join(row[(8*u+c)*4:(8*u+c+1)*4] for u in range(8))
                sector_words.append(sector)
        # Independent inverse of the HBM bank transpose: every checkpoint
        # FP32 bank value at q=8*u+c must survive with no code/scale change.
        for w in range(WORDS):
            row=blob[(offset+w)*256:(offset+w+1)*256]
            for c in range(8):
                sector=sector_words[c*WORDS+w]
                for u in range(8):
                    assert sector[u*4:(u+1)*4]==row[(8*u+c)*4:(8*u+c+1)*4]
        fixture=b"".join(sector_words)
        sector_hex=d/"sectors.hex"
        sector_hex.write_text("\n".join(f"{int.from_bytes(s,'little'):064x}"
                                        for s in sector_words)+"\n")
        exe=d/"tb.vvp"
        call(["iverilog","-g2012","-s","tb_hdc_v41x_me_bank_hbm_service",
              f"-Ptb_hdc_v41x_me_bank_hbm_service.ROM_BASE={base}",
              f"-Ptb_hdc_v41x_me_bank_hbm_service.HBM_BASE={hbase}",
              "-o",str(exe),str(RTL),str(TB)],ROOT)
        log=call(["vvp",str(exe)],d)
        m=PASS.search(log)
        if not m:
            raise RuntimeError(f"{op} has no PASS:\n{log[-3000:]}")
        reads,values,requests,responses,lead,cycles,credit=map(int,m.groups())
        if (reads,values,requests,responses)!=(8192,65536,8192,8192) or credit>64:
            raise RuntimeError(f"{op} failed coverage: {m.group(0)}")
        ops[op]={"rom_base_word":base,"hbm_base_sector":hbase,
                 "weight_bank_sector_bytes":32,"bank_count":8,
                 "word_addresses_per_bank":WORDS,"source_word_start":offset,
                 "sector_image_sha256":sha_bytes(fixture),
                 "sector_hex_sha256":sha(sector_hex),
                 "bank_reads_exact":reads,"fp32_values_exact":values,
                 "requests":requests,"responses":responses,
                 "ready_after_cycles":lead,"service_cycles":cycles,
                 "max_inflight_plus_resident_per_bank":credit,
                 "log_sha256":sha_bytes(log.encode())}
    # An invalid response tag must latch the response-protocol fault before
    # any bank read can consume data from the malformed sector.
    fault_dir=args.scratch/"fault"
    fault_dir.mkdir(parents=True,exist_ok=True)
    (fault_dir/"sectors.hex").write_bytes((args.scratch/"wo_a_0"/"sectors.hex").read_bytes())
    fault_exe=fault_dir/"tb.vvp"
    call(["iverilog","-g2012","-s","tb_hdc_v41x_me_bank_hbm_service",
          "-Ptb_hdc_v41x_me_bank_hbm_service.BAD_RESPONSE=1",
          "-o",str(fault_exe),str(RTL),str(TB)],ROOT)
    fault_log=call(["vvp",str(fault_exe)],fault_dir)
    if "ME_HBM_FAULT_PASS reason=2" not in fault_log:
        raise RuntimeError(f"malformed response failed to fault:\n{fault_log[-3000:]}")
    record={
        "schema":"opentallas.rtl.hdc_v41x_me_bank_hbm_service.v1",
        "status":"pass",
        "claim_boundary":"First 1,024 bank addresses of each of the two real full-shape L0 wo_a ME operations, at the adopted eight independently skewed 256-bit bank ports and ML=2. Exact source FP32 values, finite 64-sector ring per bank, 8-10-cycle behavioural HBM response. No full 65,536-address op, arithmetic output, shared HBM contention, die hookup, P&R or chip throughput claim.",
        "source_layout_commit":MANIFEST_COMMIT,
        "source_layout_manifest_sha256":sha_bytes(manifest_bytes),
        "source_weight_image_sha256":sha_bytes(blob),
        "source_weight_image_bytes":len(blob),
        "source_sha256":{str(p.relative_to(ROOT)):sha(p) for p in (RTL,TB,Path(__file__).resolve())},
        "families_remaining":{
            "qe":"16-lane current-core packed FP8/FP4 stream and ROM bridge owned by weight-layout agent; full comparator HBM stream integration open",
            "he_hcp":"reduced HCP weight HBM gate exists; full-shape independent-bank service and die hookup open",
            "crom":"stream constants remain ROM-served in adopted tile; HBM comparator source open",
            "wrom_embedding_vector":"embedding/vector BF16 weight source remains ROM-served; HBM comparator source open",
            "engram":"Engram table remains ROM-served; HBM comparator source open"
        },
        "operations":ops,
        "malformed_response_tag":{"status":"faulted_before_consumption",
                                  "fault_why":2,
                                  "log_sha256":sha_bytes(fault_log.encode())},
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps({k:(v["bank_reads_exact"],v["service_cycles"]) for k,v in ops.items()}))


if __name__=="__main__":
    main()
