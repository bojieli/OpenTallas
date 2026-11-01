#!/usr/bin/env python3
"""Rewrite FP phase CFG return-row IDs from actual full-field ownership tables.

The old one-phase remapper encodes 48-bit rows. Full fields also store BF
programme descriptors in bits71:48, so this tool updates only the 16 row-tag
bit planes in the existing 72-bit via-map. Weight images, timing fields,
SENT words and BF phases stay byte-identical. Source output remains PARTIAL:
this supplies row identities, not producer dates or a whole-token calendar.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil

ROW_WORDS=tuple(range(8))+tuple(range(17,25))


def tag_plan(field,groups):
    maps={};unmapped=[]
    for phase in field['phases']:
        p=phase['phase']
        if type(p) is not int or not 0<=p<1024 or p in maps or p in unmapped:
            raise ValueError('actual source phase identity is invalid or repeated')
        if phase.get('fmt')=='bf16':
            unmapped.append(p);continue
        if phase['op']=='attn.a_proj':
            tags=phase.get('row_index')
            if tags is None:raise ValueError('a_proj needs actual rank-row ownership')
        else:
            group=groups[phase['op']][phase['gi']]
            selected=phase['sel']
            try:
                if any(type(i)is not int or not 0<=i<len(group['rows']) for i in selected):
                    raise ValueError('phase selection is outside the actual source group')
                original=[group['rows'][i] for i in selected]
                source_tags=group['rows'] if group.get('cap_tags') is None else group['cap_tags']
                tags=[source_tags[i] for i in selected]
            except (IndexError,TypeError):raise ValueError('phase rows are outside the actual source group') from None
            if original!=phase['row_index']:
                raise ValueError('actual group rows differ from the compiled phase ownership')
        if len(tags)!=phase['rows'] or len(set(tags))!=len(tags) or any(type(v)is not int or not 0<=v<16384 for v in tags):
            raise ValueError('phase needs unique native 14-bit capture row IDs')
        maps[p]=list(tags)
    return dict(schema='opentallas.s81.fp_phase_rank_tags.v1',frame=field['frame'],maps=maps,
                bf_unmapped_phases=unmapped,status='PARTIAL',production_enabled=False,added_cycles=0)


def word(physical,address):
    packed=physical[address//8];slot=address%8
    return sum(((packed>>(8*bit+slot))&1)<<bit for bit in range(72))


def set_tag(physical,address,tag):
    row,slot=divmod(address,8);before=physical[row]
    mask=sum(1<<(8*bit+slot) for bit in range(16))
    bits=sum(((tag>>bit)&1)<<(8*bit+slot) for bit in range(16))
    physical[row]=(before&~mask)|bits
    if (before^physical[row])&~mask:raise AssertionError('row rewrite changed another physical bit plane')


def check_preserved_planes(before,after):
    if len(before)!=len(after) or any((a^b)>>128 for a,b in zip(before,after)):
        raise AssertionError('non-row CFG data or BF descriptor spare planes changed')


def rewrite(field,groups,images,out,*,already_ranked=(),hardlink=False):
    images,out=Path(images),Path(out)
    if out.exists():raise ValueError('preserve prior image material; choose fresh output')
    plan=tag_plan(field,groups);frame=field['frame']
    if not re.fullmatch(r'[A-Za-z_]\w*',frame):raise ValueError('unsafe actual frame name')
    banks={};paths={};original={}
    for path in sorted(images.glob(frame+'_c*_[0-6].viamap.hex')):
        match=re.fullmatch(re.escape(frame)+r'_c(\d+)_([0-6])\.viamap\.hex',path.name)
        if not match:continue
        key=tuple(map(int,match.groups()));data=[int(v,16) for v in path.read_text().split()]
        if len(data)!=512 or any(not 0<=v<1<<576 for v in data):raise ValueError('invalid native CFG4096x72 via-map')
        paths[key]=path;banks[key]=list(data);original[key]=list(data)
    pairs=sorted({p for p,b in banks})
    if not pairs or any((p,b) not in banks for p in pairs for b in range(7)):
        raise ValueError('all seven actual CFG banks are required per frame pair')
    changed={p:0 for p in plan['maps']};checked={p:0 for p in plan['maps']}
    already=set(already_ranked)
    if not already<=plan['maps'].keys():raise ValueError('already-ranked phase is not a mapped FP source phase')
    for phase,tags in plan['maps'].items():
        for pair in pairs:
            for index in ROW_WORDS:
                address=4*phase+index//7;key=(pair,index%7)
                value=word(banks[key],address)
                if value==0 or value&0x8000:continue
                row=value&0xffff;checked[phase]+=1
                if phase in already:
                    if row not in tags:raise ValueError('already-ranked input differs from actual row ownership')
                    continue
                if row>=len(tags):raise ValueError('phase-local source CFG row is outside its actual ownership map')
                if tags[row]!=row:
                    set_tag(banks[key],address,tags[row]);changed[phase]+=1
    out.mkdir(parents=True)
    # Emit fresh CFG files; immutable other material can be linked cheaply.
    cfg_names={path.name for path in paths.values()}
    unchanged_files=0
    for path in images.iterdir():
        if not path.is_file() or path.name in cfg_names:continue
        if hardlink:os.link(path,out/path.name)
        else:shutil.copyfile(path,out/path.name)
        unchanged_files+=1
    for key,path in paths.items():
        (out/path.name).write_text(''.join(f'{v:0144x}\n' for v in banks[key]))
        check_preserved_planes(original[key],banks[key])
    plan.update(input_images=str(images.resolve()),already_ranked_phases=sorted(already),
                checked_cfg_words=checked,changed_cfg_words=changed,unchanged_non_cfg_files=unchanged_files,
                qualification='FP source row IDs only; BF row tags, capture lifetimes and source calendar remain unqualified')
    (out/'rank_tags.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--field',type=Path,required=True);p.add_argument('--groups',type=Path,required=True)
    p.add_argument('--images',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--already-ranked-phase',type=int,action='append',default=[])
    p.add_argument('--hardlink',action='store_true');a=p.parse_args()
    result=rewrite(json.loads(a.field.read_text()),json.loads(a.groups.read_text()),a.images,a.out,
                   already_ranked=a.already_ranked_phase,hardlink=a.hardlink)
    print('PARTIAL:',sum(result['changed_cfg_words'].values()),'native CFG row fields remapped;',
          len(result['bf_unmapped_phases']),'BF phases left explicit')


if __name__=='__main__':main()
