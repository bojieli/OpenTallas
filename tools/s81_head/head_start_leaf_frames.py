#!/usr/bin/env python3
"""HEAD physical-partition START count frames; physical clock regions unchanged."""
import argparse,copy,json
from pathlib import Path


def leaf_ocv(ocv,mapping):
    out=copy.deepcopy(ocv);seen=set()
    for key,corner in out['corners'].items():
        for row in corner.get('all',[]):
            s=row.get('src_part',row['src']);d=row.get('dst_part',row['dst'])
            if s not in mapping or d not in mapping:
                raise ValueError(f'{key}: unknown physical partition {s}->{d}')
            if (row['src'],row['dst'])!=(mapping[s],mapping[d]):
                raise ValueError(f'{key}: stale region mapping {s}->{d}')
            row.update(src=s,dst=d,src_part=s,dst_part=d);seen.update((s,d))
    if seen!=set(mapping):
        raise ValueError(f'partition START leaves lack crossing coverage: {sorted(set(mapping)-seen)}')
    out['start_frame_scope']={'frames':len(mapping),'physical_clock_regions':len(set(mapping.values())),
        'frame_clock_regions':dict(sorted(mapping.items())),
        'data_delta':'none: same external crossing rows; same-region links remain unlanded',
        'start_offsets':'unqualified pending local reset and full physical START route'}
    return out


def annotate(bind,table,mapping):
    """Project only region consistency check into physical clock frame; all count arithmetic remains per-part."""
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
    import count_align_bind as C
    b=copy.deepcopy(bind)
    actual={q:v['region'] for q,v in b['parts'].items() if not v['region'].startswith('st:')}
    if actual!={q:q for q in mapping}:raise ValueError('every physical part must have its own START frame')
    for c in b['ports'].values():
        c['src']=mapping[c['src_part']];c['dst']=mapping[c['dst_part']]
    t=C.annotate_table(table,b,strap_form=True)
    t['count_aligned']['frame_clock_regions']=dict(sorted(mapping.items()))
    return t


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('ocv');a.add_argument('--regions',required=True);a.add_argument('--out',required=True);a=a.parse_args()
    mapping=json.load(open(a.regions))['part_region'];out=leaf_ocv(json.load(open(a.ocv)),mapping)
    Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out['start_frame_scope']))
if __name__=='__main__':main()
