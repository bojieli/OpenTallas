#!/usr/bin/env python3
"""Preserve all 768 logical tiles while proposing 46 physical field columns.

Two whole 4x4 arithmetic cohorts move to separate rooms; two other cohorts
fold into the remaining 2x16 physical sites. This is an exact identity map,
not evidence that the new hardware/relay/clock rooms fit or close.
"""
import argparse
import json
from pathlib import Path
from qwen_split.compute_spine import ref_tile_id


def build():
    entries=[]
    for c in range(48):
        for r in range(16):
            block=(c//4)*4+r//4
            if c<44:
                location=dict(kind='main_field',column=c,row=r)
            elif block in (45,46):
                location=dict(kind='rehome_cohort',cohort=block,
                              column=c-44,row=r%4,x_um=None,y_um=None)
            else:
                location=dict(kind='main_field',column=44+(c-44)%2,
                              row=(0 if block==44 else 8)+(r%4)+4*((c-44)//2))
            entries.append(dict(instance=f't_{c}_{r}',logical_column=c,
                logical_row=r,tile_id=ref_tile_id(c,r),arithmetic_block=block,
                dvm_head=f'h_{c}',location=location,
                station_identity=f's_{c}_{r}',
                source_function='same ROM/output rows, DVM chunk, tree host and arithmetic order'))
    assert len(entries)==768 and len({e['tile_id']for e in entries})==768
    main=[e for e in entries if e['location']['kind']=='main_field']
    rehome=[e for e in entries if e['location']['kind']=='rehome_cohort']
    assert len(main)==736 and len(rehome)==32
    assert len({(e['location']['column'],e['location']['row'])for e in main})==736
    assert {e['tile_id']for e in rehome}==set(range(720,752))
    return dict(schema='opentallas.qwen.logical-field-cohort-remap.v1',
        qualified=False,scope='complete logical identity preservation; ordinal physical-site proposal only',
        logical_tiles=768,main_physical_sites=736,rehome_tiles=32,
        retained_logical_columns=48,retained_DVM_heads=48,
        moved_arithmetic_blocks=[45,46],folded_arithmetic_blocks=[44,47],
        relays_and_clock_entries='all preserved identities; locations/ages unassigned',
        required_geometry=['two real sixteen-tile rooms plus stations and logical DVM paths',
            'actual 481.68-wide tile admission and all source-equivalent pin/clock plans',
            'all rectangle/halo/pin/cut/routed timing and fixed-calendar costs',
            'reticle fit with complete SU/IO/native59/embedding hardware'],entries=entries)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(build(),indent=2)+'\n')
