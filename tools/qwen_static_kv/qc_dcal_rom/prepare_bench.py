#!/usr/bin/env python3
"""Prepare actual QC calendar INIT component with all output lockstep + wrong via mask."""
from pathlib import Path
import argparse,json,re,shutil,sys,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
import qc_dcal_profile as P

def prepare(source:Path,prefix:str,out:Path):
    source=source.resolve();source.relative_to(ROOT)
    out.mkdir(parents=True,exist_ok=True);text=source.read_text();profile=P.extract_sv(text,prefix)
    if len(profile['TX'])!=32:raise ValueError('actual QC component profile is NE32')
    p=P.personalise(profile,out/'profile',instance='profile')
    shutil.copy(out/'profile'/p['viamap'],out/'profile.viamap.hex')
    mutant=json.loads(json.dumps(profile));mutant['TX'][0]^=1
    m=P.personalise(mutant,out/'mutant',instance='mutant')
    shutil.copy(out/'mutant'/m['viamap'],out/'mutant.viamap.hex')
    def seg(port):
        v=re.search(r'\b'+re.escape(prefix+'_'+port+'_SEG1')+r"\s*=\s*32'([hd])([0-9a-f]+)",text,re.I)
        if not v:raise ValueError('missing segment value')
        return int(v.group(2),16 if v.group(1).lower()=='h' else 10)
    pack=lambda xs:sum(x<<(32*i) for i,x in enumerate(xs))
    (out/'profile_params.svh').write_text(f"localparam[1023:0] IMAGE_TX=1024'h{pack(profile['TX']):0256x};\nlocalparam[1023:0] IMAGE_RX=1024'h{pack(profile['RX']):0256x};\nlocalparam[31:0] SEG_TX=32'd{seg('TX')}, SEG_RX=32'd{seg('RX')};\n")
    d=ROOT/'rtl/qwen_sys/d2d_static_20261015'
    for file in [d/'ot_qwen_d2d_cal_seq.sv',d/'ot_qwen_d2d_cal_seq_image64.sv',ROOT/f'physical/asap7_memory_macros_v2/{P.NAME}/{P.NAME}.v',Path(__file__).with_name('tb.sv')]:
        shutil.copy(file,out/file.name)
    (out/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
cd "$(dirname "$0")"
verilator --binary --timing -Wno-fatal --top-module tb -j 8 -I. --Mdir obj \\
  tb.sv ot_qwen_d2d_cal_seq.sv ot_qwen_d2d_cal_seq_image64.sv ot_rom_64x64_m2.v > build.log 2>&1
./obj/Vtb > sim.log 2>&1
tail -5 sim.log
''')
    record={'source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'source':str(source.relative_to(ROOT)),
      'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'prefix':prefix,'profile':profile,
      'positive':'actual INIT+admission sequencer NL1 AUTO0 as instantiated by ot_qwen_d2d_ovl_seq',
      'mutant':'TX image entry0 bit0 toggled in via mask','production_edge_delta':0,'init_edge_delta':0}
    (out/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('source',type=Path);a.add_argument('prefix');a.add_argument('out',type=Path)
    q=a.parse_args();prepare(q.source,q.prefix,q.out)
