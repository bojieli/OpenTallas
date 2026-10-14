#!/usr/bin/env python3
"""Reproduce the actual assigned-pin screen with measured provisional bus arcs.

The retained old plan supplies unchanged dimensions/instance identities. The
two explicit successor substitutions use their real die-assigned pin files and
measured CTS tables. They remain provisional, never routed qualification.
"""
import json
from pathlib import Path
import native_comb_seams as S
ROOT=Path(__file__).resolve().parents[2]
RESULT=ROOT/'results/rtl/s81_suhc_20261013'


def main():
    plan=json.loads((RESULT/'native_comb_packing_request_1013.json').read_text())
    actual=json.loads((RESULT/'native_provisional_models/provisional_bus_timing.json').read_text())['models']
    models={};geoms={};substitutions={}
    for leaf in plan['instances']:
        if leaf['instance'] not in ('u_cf','u_pd.u_f5r1'):continue
        cell='ot_s81_hc_ccf' if leaf['instance']=='u_cf' else 'ot_s81_hc_pad_fv4fd5r1'
        models[leaf['cell']]=actual[cell]
        substitutions[leaf['instance']]={'reference_cell':leaf['cell'],'actual_successor_cell':cell,
                                        'status':'provisional placed CTS arcs, not routed view'}
        assigned=json.loads((ROOT/'physical/s81_die_pins/v18'/f'{cell}.json').read_text())
        geom=S.pins(leaf);ox,oy=leaf['origin_um'];w,h=leaf['outline_um']
        for bus,port in assigned['ports'].items():
            assert not port.get('uniform'), 'exact per-bit assignment required'
            for bit,(face,layer,offset,depth) in enumerate(port['per_bit']):
                name=bus if port['bits']==1 and bus in geom else f'{bus}[{bit}]'
                x,y={'N':(offset,h-depth/2),'S':(offset,depth/2),
                     'W':(depth/2,offset),'E':(w-depth/2,offset)}[face]
                geom[name]=(ox+x,oy+y)
        geoms[leaf['instance']]=geom
    rec=S.screen(plan,models,geoms)
    rec['status']='PROVISIONAL CTS DIAGNOSIS ONLY: actual successor assigned pins and placed CTS arcs; no routed qualification'
    rec['actual_master_substitutions']=substitutions
    rec['provisional_model_source']='native_provisional_models/provisional_bus_timing.json'
    out=RESULT/'native_comb_successor_provisional_seams_1013.json'
    out.write_text(json.dumps(rec,indent=2)+'\n')
    print(len(rec['seams']),'seams;',rec['fail_count'],'fail;',rec['missing_count'],'missing')


if __name__=='__main__':main()
