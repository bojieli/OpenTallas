#!/usr/bin/env python3
"""Select the actual four-stack service + mandatory near baseline; source only."""
import argparse,hashlib,json
from pathlib import Path
import qwen_rom_combined_nearbaseline_sources as base
ROOT=Path(__file__).resolve().parents[1]

def selected(output,*,hbm_layers=36):
    output=Path(output)
    rec=base.selected(output,hbm_layers=hbm_layers)
    c=ROOT/'rtl/qwen_sys/combined'
    pin=json.loads((c/'stream4_tagged_source_pin.json').read_text())
    for p,h in pin['sources'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:
            raise ValueError('actual Claude STREAM4 source changed: '+p)
    omit={'ot_qwen_rom_combined_nearbaseline_die.sv','ot_qwen_nearhbm_realmem_service.sv','ot_qwen_rt_kv_fill_service.sv'}
    die=[Path(p) for p in rec['die'] if Path(p).name not in omit]
    die += [c/'ot_qwen_rom_combined_stream4_die.sv',c/'ot_qwen_combined_stream4_rows.sv',
            ROOT/'rtl/hdc/kv/ot_qwen_rt_kv_stream4_service.sv',ROOT/'rtl/hdc/kv/ot_qwen_kv_land_merge.sv']
    rec['die']=list(map(str,dict.fromkeys(die)))
    rec['top']='ot_qwen_rom_combined_stream4_die'
    rec['parameters'].update(HBM_STREAM4=1,NSTK=4,WBW=4)
    rec['hbm_top']='ot_qwen_hbm_stream4_tagged'
    rec['hbm_parameters']=dict(NSTK=4,NPC=128,MEM_WORDS=hbm_layers*131072,TAGW=9,TTAGW=13,CORE_FS=833333,CTL_FS=1024000)
    rec['hbm']=[str(ROOT/p) for p in pin['sources'] if Path(p).name not in {'ot_qwen_rt_kv_stream4_service.sv','ot_qwen_rt_kv_stream4_mp_service.sv','ot_qwen_kv_land_merge.sv'}]
    rec['hbm']=[p for p in rec['hbm'] if Path(p).name!='ot_qwen_hbm_stream4_ack.sv']
    rec['hbm']=list(dict.fromkeys(rec['hbm']))
    rec['optional_candidates']['stream_controller']=True
    rec['mandatory_baseline']['stream4_source']=pin['main_commit']
    rec['source_sha256']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in dict.fromkeys(rec['die']+rec['tile']+rec['collective']+rec['hbm'])}
    rec['runtime_contract']='Initialize all models before preload (157); existing P8191 descriptor3 inputs; bind STREAM4 mem and tagged near-row reads to SAME logical backing store; preserve actual controller timing/CDC; pulse rm_kv_free only after O+AR at MLP; drain wb_busy_o plus row_drained_o before readback/reuse; core done alone is insufficient.'
    rec['clocks'].update(STREAM4='core-domain ports, model CORE_FS833333/CTL_FS1024000 with actual controller crossings; tagged near-row transport retains independent hclk')
    rec['runtime_wiring']=str(ROOT/'tools/runtime/qwen_combined/stream4_memory_binding.hpp')
    rec['scope']='source integration only; standalone P8191 bandwidth is not combined full-token gain or physical closure'
    (output/'sources.json').write_text(json.dumps(rec,indent=2)+'\n')
    (output/'die_sources.f').write_text('\n'.join(rec['die'])+'\n')
    (output/'hbm_sources.f').write_text('\n'.join(rec['hbm'])+'\n')
    return rec
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--hbm-layers',type=int,default=36);a=p.parse_args()
    rec=selected(a.output,hbm_layers=a.hbm_layers);print(json.dumps({'top':rec['top'],'source_book':str(a.output/'sources.json')}))
