#!/usr/bin/env python3
"""Prepare a self-contained production-profile miter for ot-run --stage."""
from pathlib import Path
import argparse
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
import kv_dcal_profile as P

def prepare(source: Path, out: Path):
    out.mkdir(parents=True,exist_ok=True)
    d=ROOT/'rtl/qwen_sys/d2d_static_20261015'
    text=source.read_text()
    import re
    m=re.search(r'`include\s+"([^"]+)"',text)
    profile_source=source.parent/m.group(1) if m else source
    if m:
        shutil.copy(profile_source,out/m.group(1))
    profile=P.extract_sv(profile_source.read_text())
    p=P.personalise(profile,out/'profile',instance='profile')
    shutil.copy(out/'profile'/p['viamap'],out/'profile.viamap.hex')
    mutant=json.loads(json.dumps(profile));mutant['START'][1]^=1
    mp=P.personalise(mutant,out/'mutant',instance='mutant')
    shutil.copy(out/'mutant'/mp['viamap'],out/'mutant.viamap.hex')
    shutil.copy(source,out/'gold.sv')
    files=[d/'ot_qwen_d2d_cal_seq_bc4.sv',d/'ot_qwen_d2d_cal_seq_rom64_core.sv',
           d/'qkd_d2d_cal_seq_rom64.sv',ROOT/'physical/asap7_memory_macros_v2/ot_rom_64x32_m2/ot_rom_64x32_m2.v',
           Path(__file__).with_name('tb.sv')]
    for f in files:shutil.copy(f,out/f.name)
    (out/'profile_defs.svh').write_text(f"`define TX_SEG2 32'd{profile['TX_SEG2']}\n`define RX_SEG2 32'd{profile['RX_SEG2']}\n")
    tb=(out/'tb.sv').read_text();(out/'tb.sv').write_text('`include "profile_defs.svh"\n'+tb)
    run='''#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
cd "$(dirname "$0")"
verilator --binary --timing -Wno-fatal --top-module tb -j 8 -I. --Mdir obj \\
  tb.sv gold.sv ot_qwen_d2d_cal_seq_bc4.sv ot_qwen_d2d_cal_seq_rom64_core.sv \\
  qkd_d2d_cal_seq_rom64.sv ot_rom_64x32_m2.v > build.log 2>&1
./obj/Vtb > sim.log 2>&1
tail -5 sim.log
'''
    (out/'run.sh').write_text(run)
    import subprocess,hashlib
    rec={'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
         'gold_source':str(source),'gold_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
         'profile':profile,'latency_delta_production_cycles':0,'latency_delta_boot_cycles':0,
         'profile_initial_reads_inside_existing_66_init_edges':8,
         'mutant':'START[1] bit0 toggled, content via map only'}
    (out/'inputs.json').write_text(json.dumps(rec,indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('source',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();prepare(a.source,a.out)
