"""Bind the actual pair image to an explicit ROM64 profile and native epoch test."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys

def prepare(root, selected_alias, out):
    sys.path.insert(0,str(root/'tools/mem_compiler'))
    import kv_dcal_profile as P
    image=root/'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_qc_pair.svh'
    profile=P.extract_sv(image.read_text())
    sys.path.insert(0,str(Path(__file__).parent))
    from epoch_calendar import bind_image_profile
    bind_image_profile(profile,profile)
    out.mkdir(parents=True,exist_ok=False)
    for name,data in [('profile',profile),('stale',dict(profile,ADM_LEN=1100,FIRST_OFS=1176))]:
        rec=P.personalise(data,out/name,instance=name)
        shutil.copy2(out/name/rec['viamap'],out/(name+'.viamap.hex'))
    # This is a missing-content/stale-duration control, not a claim that the
    # physical R8 composition selected the stale payload.
    try:
        stale=json.loads((out/'stale/stale.profile.json').read_text())
        bind_image_profile(profile,stale)
    except ValueError:
        (out/'stale_bind_control.txt').write_text('CAUGHT image/profile mismatch: ADM_LEN1100!=1270 FIRST1176!=1346\n')
    else:raise ValueError('stale profile unexpectedly accepted')
    rtl=root/'rtl/qwen_sys/d2d_static_20261015'
    gold=(rtl/'qkd_d2d_cal_seq_bc4.sv').read_text()
    gold=gold.replace('module qkd_d2d_cal_seq_pin_bc4 #(', 'module bc4_literal_qc_pair #(',1)
    gold=gold.replace('`include "d2d_cal_image_mu.svh"','`include "qc_pair.svh"')
    (out/'gold.sv').write_text(gold)
    shutil.copy2(image,out/'qc_pair.svh')
    shutil.copy2(selected_alias,out/'selected_bc4_rom64.sv')
    for f in [rtl/'ot_qwen_d2d_cal_seq_bc4.sv',rtl/'ot_qwen_d2d_cal_seq_rom64_core.sv',
              root/'physical/asap7_memory_macros_v2/ot_rom_64x32_m2/ot_rom_64x32_m2.v']:
        shutil.copy2(f,out/f.name)
    shutil.copy2(Path(__file__).with_name('tb.sv'),out/'tb.sv')
    tx=int(image.read_text().split("D2D_CAL_K_TX_IMG = 1024'h")[1].split(';')[0],16)
    rx=int(image.read_text().split("D2D_CAL_K_RX_IMG = 1024'h")[1].split(';')[0],16)
    boot=[n for i in range(32) for n in [(tx>>(32*i))&0xffffffff,(rx>>(32*i))&0xffffffff]]
    boot += [profile['TX_SEG2'],profile['RX_SEG2']]
    (out/'boot.hex').write_text(''.join('%08x\n'%v for v in boot))
    (out/'defs.svh').write_text(''.join('`define '+k+' '+str(profile[k])+'\n' for k in ['TX_SEG1','RX_SEG1','TX_SEG2','RX_SEG2']))
    (out/'run.sh').write_text("""#!/bin/bash
set -euo pipefail
ulimit -c 0
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$(dirname "$0")"
verilator --binary --timing -Wno-fatal -j 4 --top-module tb --Mdir obj tb.sv gold.sv selected_bc4_rom64.sv ot_qwen_d2d_cal_seq_bc4.sv ot_qwen_d2d_cal_seq_rom64_core.sv ot_rom_64x32_m2.v > build.log 2>&1
./obj/Vtb > run.log 2>&1
grep -q BC4_EPOCH_PASS run.log
tail -8 run.log
""")
    inputs=dict(selected_image=str(image),image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                selected_r8_alias=str(selected_alias),profile=profile,clock_ps=833,
                epochs=3,profile_only_no_physical_or_POR_change=True,
                source_static_contract='All66 boot words, runtime BASE remap, halt/recovery/reload; actual native ROM and selected BC4',
                limitations='No HOST authorization arithmetic or full D2D datapath simulated; RF input boundary projection only')
    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--source-root',type=Path,required=True);a.add_argument('--selected-alias',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    p=a.parse_args();prepare(p.source_root,p.selected_alias,p.out)
