#!/usr/bin/env python3
"""Select the actual owner VPOS/KVmp/near source join; emits only, never builds."""
import argparse
import hashlib
import json
from pathlib import Path
import qwen_rom_combined_nearbaseline_sources as predecessor
import qwen_rom_verify_core_emit_w12 as vpos
import qwen_rom_rt_core_emit_w12 as core

ROOT=Path(__file__).resolve().parents[1]
TOP='ot_qwen_rom_combined_dspark_die'


def selected(output):
    output=Path(output)
    rec=predecessor.selected(output,hbm_layers=36)
    generated=output/'gen/ot_qwen_rom_core.sv'
    generated.write_text(vpos.emit(core.CORE.read_text()))
    omit={'ot_qwen_rom_combined_nearbaseline_die.sv','ot_qwen_tp_seq_combined.sv',
          'ot_qwen_nearhbm_realmem_service.sv'}
    die=[Path(p) for p in rec['die'] if Path(p).name not in omit]
    combined=ROOT/'rtl/qwen_sys/combined'
    die += [combined/name for name in [TOP+'.sv','ot_qwen_tp_seq_combined_vp.sv',
             'ot_qwen_combined_nearhbm_mp_service.sv','ot_qwen_combined_dspark_accept.sv']]
    die += [ROOT/'rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv',ROOT/'rtl/hdc/ot_hdc_accept.sv']
    die=list(dict.fromkeys(die))
    for p in die:
        if not p.is_file():raise FileNotFoundError(p)
    rec['die']=list(map(str,die));rec['top']=TOP
    rec['parameters'].update(DSPARK=1,ACCEPT_COMMIT=0,VPMAX=4,VWA=16,
                             NPROG=1024,NDESC=64,VM_ELEMS=1048576)
    rec['optional_candidates']['DSpark']=True
    rec['scope']='Opt-in owner VPOS/KVmp/near integration component; no full-token or timing qualification'
    rec['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in dict.fromkeys(die+list(map(Path,rec['tile']))+list(map(Path,rec['collective'])))}
    (output/'sources.json').write_text(json.dumps(rec,indent=2)+'\n')
    (output/'die_sources.f').write_text('\n'.join(map(str,die))+'\n')
    return rec


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=selected(a.output);print(json.dumps({'top':r['top'],'parameters':r['parameters']}))
