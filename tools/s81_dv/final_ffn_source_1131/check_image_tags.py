#!/usr/bin/env python3
"""Read actual native CFG bank images and bind down source rows to their tags."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/s81_dv'))
from field_rank_images import word

def check(field,images,mutant=False):
    f=json.load(open(field));images=Path(images);cache={};count=0;phases=0
    for p in f['phases']:
        if p['op']!='ffn.down':continue
        assert p.get('kslot',1)==1
        assert p['plan']['single_frame_cap_score']==0
        phases+=1
        for q in p['placement']:
            for row in q['rows']:
                if row>=p['rows']:continue
                cfgword=17 if row%2 else 0;key=(q['pair'],cfgword%7)
                if key not in cache:cache[key]=[int(v,16) for v in (images/f'{f["frame"]}_c{key[0]}_{key[1]}.viamap.hex').read_text().split()]
                tag=word(cache[key],4*p['phase']+cfgword//7)&65535
                if mutant and count==0:tag^=1
                assert tag==p['row_index'][row],(p['phase'],q['pair'],row,tag,p['row_index'][row])
                count+=1
    assert count>0
    return dict(status='PASS_CAP_AWARE_FIELD_LITERAL_TAGS',frame=f['frame'],down_phases=phases,literal_tags=count,source_calendar_scope='single-frame logical FIN only',production_enabled=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--field',type=Path,required=True);p.add_argument('--images',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',action='store_true');a=p.parse_args()
    if a.out.exists():raise ValueError('preserve previous verdict')
    try:r=check(a.field,a.images,a.mutant)
    except Exception as e:a.out.write_text(json.dumps(dict(status='FAIL',error=str(e)),indent=2));raise
    a.out.write_text(json.dumps(r,indent=2));print(r['status'],r['literal_tags'])
