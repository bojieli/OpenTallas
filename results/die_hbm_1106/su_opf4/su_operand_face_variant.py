#!/usr/bin/env python3
"""Emit a distinct SU lane1 candidate budgeting the outer operand face loop.

Original signed sources are copied byte-for-byte. New module names opt into a
separate variant: index response stays native; operand response gains two edges.
Physical requalification is required. No existing signed view is modified.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

OLD = 'ot_hbm_su_pg_lane1_core'
NEW = 'ot_hbm_su_pg_lane1_opf4_core'
LANE = 'ot_hbm_su_static_lane'
PIN = 'ot_hbm_su_static_lane_pinreg'
NEW_LANE = LANE+'__op_extra2'
NEW_PIN = PIN+'__op_extra2'

def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one source anchor: {old}')
    return text.replace(old,new)

def extend_stage(text, name, extra):
    start=text.index('generate if (FETCH_EXTRA_EDGES > 0) begin:'+name)
    end=text.index('end endgenerate',start)+len('end endgenerate')
    return text[:start]+text[start:end].replace('FETCH_EXTRA_EDGES',f'(FETCH_EXTRA_EDGES + {extra})')+text[end:]

def generate(source, out, operand_extra=2, index_extra=0):
    if source.resolve()==out.resolve():
        raise ValueError('Variant output must differ from immutable signed source')
    out.mkdir(parents=True,exist_ok=True)
    hashes={}
    for p in sorted(source.glob('*.sv')):
        shutil.copyfile(p,out/p.name)
        hashes[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    for suffix in ['.sv','__wrap.sv','__fshell.sv']:
        p=source/(OLD+suffix)
        text=p.read_text().replace(OLD,NEW)
        if suffix=='.sv':
            if '.FETCH_EXTRA_EDGES(2)' not in text:
                raise ValueError('Expected the sealed outer index response of two edges')
            text=replace_once(text,PIN+' #(',NEW_PIN+' #(')
        (out/(NEW+suffix)).write_text(text)
    lane=replace_once((source/(LANE+'.sv')).read_text(),'module '+LANE+' #(','module '+NEW_LANE+' #(')
    lane=extend_stage(lane,'g_fetch_edge',operand_extra)
    if index_extra:
        lane=extend_stage(lane,'g_index_edge',index_extra)
    (out/(NEW_LANE+'.sv')).write_text(lane)
    pin=replace_once((source/(PIN+'.sv')).read_text(),'module '+PIN+' #(','module '+NEW_PIN+' #(')
    pin=replace_once(pin,LANE+' #(',NEW_LANE+' #(')
    (out/(NEW_PIN+'.sv')).write_text(pin)
    receipt={'status':'MUTANT_DO_NOT_ROUTE' if (operand_extra,index_extra)!=(2,0) else 'FUNCTION_AND_PHYSICAL_QUALIFICATION_PENDING',
       'master':NEW,'source':str(source),'source_sha256':hashes,
       'MLAT':5,'ALAT':3,'outer_index_response_edges':2+index_extra,'outer_operand_response_edges':2+operand_extra,
       'arithmetic_index_response_edges':4+index_extra,'arithmetic_operand_response_edges':4+operand_extra,
       'retained_input_output_faces':[1,1], 'extra_raw_flop_bits':operand_extra*26+index_extra*137,
       'physical_view':'NONE; original SIGNED view remains unchanged'}
    (out/'operand_variant.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--signed-rtl',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--mutant',choices=['operand','index'])
    a=p.parse_args()
    generate(a.signed_rtl,a.out,0 if a.mutant=='operand' else 2,2 if a.mutant=='index' else 0)
    print(NEW)

if __name__=='__main__':main()
