"""Explicit byte-identical source-pin successor; historical contract unchanged.

Publication comparisons use original immutable payloads. Path portability is an
explicit reviewed provenance change, never changed arithmetic/source bytes.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from h4_c0_ds_whole_reference import sha,load,payload


def successor(original,expected_sha,source_map,out):
    original=Path(original).resolve();out=Path(out)
    if sha(original)!=expected_sha:raise ValueError('reviewed historical contract SHA')
    c=load(original);pins=c['reference_source_sha256'];mapping=dict(source_map)
    if set(mapping)-set(pins):raise ValueError('source remap must name exact historical pin')
    newpins={};translations=[]
    for old,digest in pins.items():
        new=str(Path(mapping.get(old,old)).resolve())
        if sha(new)!=digest:raise ValueError('source remap bytes differ from historical pin: '+old)
        if new in newpins and newpins[new]!=digest:raise ValueError('source remap collision')
        newpins[new]=digest
        translations.append(dict(original_path=old,successor_path=new,sha256=digest))
    rows=[];identities=set()
    for row in c['expectations']:
        key=(row['PC'],row['version'],row['rank'],row.get('generation',1),row['field'])
        if key in identities:raise ValueError('duplicate historical reference identity')
        identities.add(key)
        p=(original.parent/row['path']).resolve();a=np.load(p,allow_pickle=False)
        if sha(p)!=row['file_sha256'] or payload(a)!=row['payload_sha256'] or list(a.shape)!=row['shape'] or a.dtype.str!=row['dtype']:
            raise ValueError('immutable historical comparison payload')
        rows.append(dict(row,path=str(p)))
    newpins[str(original)]=expected_sha;newpins[str(Path(__file__).resolve())]=sha(__file__)
    result=dict(c,reference_source_sha256=newpins,expectations=rows,
        reference_contract_successor=dict(original_path=str(original),original_sha256=expected_sha,
            source_path_translations=translations,payload_identity_changes=0,arithmetic_changes=0,
            original_contract_rewritten=False,comparison_only=True,successor_tool_sha256=sha(__file__)))
    with out.open('x') as f:f.write(json.dumps(result,sort_keys=True,indent=2)+'\n')
    if sha(original)!=expected_sha:raise ValueError('historical contract changed during successor creation')
    return dict(status='PASS_EXPLICIT_SOURCE_PIN_SUCCESSOR',fields=len(rows),original_sha256=expected_sha,successor_sha256=sha(out))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--expected-sha',required=True)
    p.add_argument('--source-map',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(successor(a.original,a.expected_sha,load(a.source_map),a.out),sort_keys=True))
