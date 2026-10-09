#!/usr/bin/env python3
"""Produce S81 descriptor geometry and explicit physical-region install records.

No capacity/default placement inference. Config must list four physical stacks,
two Engram homes, every mutable descriptor region, and usable capacities. This
is the ND1 (one die owns its rows), NS4 released host descriptor layout. Output
is candidate deployment material until the runtime reader consumes this ledger.
"""
import argparse
import hashlib
import json
from pathlib import Path
from kv_ingest_ref import desc, M_ROWS, M_IKEY


def align(n, a=128):
    return (n+a-1)//a*a


def produce(cfg):
    stacks = cfg['stacks']
    if len(stacks) != 4 or [s['id'] for s in stacks] != list(range(4)):
        raise ValueError('explicit physical stack IDs0..3 required')
    homes = cfg['engram_home_stack_ids']
    if len(homes) != 2 or len(set(homes)) != 2 or any(s not in range(4) for s in homes):
        raise ValueError('two distinct actual Engram home stack IDs required')
    stride = cfg['host_stack_stride_sectors']
    if not 0 < stride or 4*stride > (1<<30):
        raise ValueError('host windows must fit runtime class00')
    users = cfg['users']; pos = cfg['positions_per_user']; rope_pos = cfg['rope_positions']
    if not 0 < users or not 0 < pos <= (1<<24) or pos % 16 or not 0 < rope_pos:
        raise ValueError('ND1 capacity geometry requires nonzero users,16-aligned positions<=2^24')
    engram_count = cfg['engram_pc_local_atom_count']
    if not 0 < engram_count or engram_count % 4:
        raise ValueError('Engram local span must contain whole canonical four-atom groups')
    regions = [[] for _ in stacks]; descriptors = []
    names = [r['kind'] for r in cfg['mutable_regions']]
    if len(names) != len(set(names)) or not {'KEY','CKV','WINDOW'} <= set(names):
        raise ValueError('explicit KEY,CKV,WINDOW inventory required, no duplicates')
    for r in cfg['mutable_regions']:
        kind = r['kind']; base = r['global_base_sector']
        if base < 0 or base % 128:
            raise ValueError('mutable region bases must be explicit128-sector aligned')
        if kind == 'KEY':
            mode = M_IKEY; rb = 68; pitch = None; ring = 0
            per_user = ((pos//4+1023)//1024)*2176
            counts = [users*per_user]*4
        elif kind == 'CKV':
            mode = M_ROWS; rb = 288; pitch = 9; ring = 0
            per_user = align(pos//4,16)*pitch
            counts = [users*per_user]*4
        elif kind == 'WINDOW':
            mode = M_ROWS; rb = 528; pitch = 17; ring = cfg['window_ring_rows']
            sid = cfg['window_stack_id']
            if sid not in range(4) or not 0 < ring or ring & (ring-1):
                raise ValueError('explicit physical WINDOW home and power-of-two ring required')
            per_user = ring*pitch; counts = [0]*4; counts[sid] = users*per_user
        else:
            raise ValueError('unknown mutable region: no omitted allocator state allowed')
        for s,count in enumerate(counts):
            if count:
                regions[s].append(dict(kind=kind,base=base,end=base+count,sector_count=count,
                                       users=users,per_user_sectors=per_user,global_units='32B sectors'))
        # Same allocation and descriptor factory. Users have separate bases;
        # first-position is per-user, never64*context folded into24-bit n0.
        rows = ring if kind == 'WINDOW' else pos
        quantum = 16 if kind == 'KEY' else 64
        chunk_max = (65535*64//rb)//quantum*quantum
        for user in range(users):
            ubase = base+user*per_user
            if kind == 'WINDOW': ubase += cfg['window_stack_id']*stride
            for first in range(0,rows,chunk_max):
                n = min(rows-first,chunk_max); nb = (n*rb+63)//64
                word = desc(mode,fence=1,tag=(len(descriptors)&255),a0=ubase,
                            a1=0 if ring else stride,a2=0 if pitch is None else pitch,a3=ring,
                            n0=first,n1=0 if kind=='KEY' else rb,n2=n,n4=0,n5=0,n6=0 if ring else 2,nb=nb)
                if word >= (1<<256): raise ValueError('descriptor field overflow')
                descriptors.append(dict(kind=kind,user=user,first=first,count=n,
                                        payload_beats=nb,descriptor_hex=f'{word:064x}'))
    output_stacks=[]; pc_records=[]; stack_records=[]
    for s,cap in enumerate(stacks):
        usable=cap['usable_sectors']; physical=cap['physical_capacity_sectors']
        if not 0 < usable <= physical < (1<<30):
            raise ValueError('explicit usable capacity must fit actual configured physical capacity')
        reg=sorted(regions[s],key=lambda r:r['base'])
        if not reg: raise ValueError('unset mutable region inventory')
        for a,b in zip(reg,reg[1:]):
            if a['end'] > b['base']: raise ValueError('mutable regions overlap')
        reserved=align(max(r['end'] for r in reg))
        if reserved > stride: raise ValueError('mutable region exceeds host stack window')
        eng_base=reserved//32; eng_limit=eng_base+engram_count
        end=reserved+engram_count*32 if s in homes else reserved
        plain=align(end); span=align(2*rope_pos); yarn=plain+span; end=yarn+span
        if end > usable: raise ValueError('installed regions exceed physical usable capacity')
        output_stacks.append(dict(id=s,name=cap['name'],physical_capacity_sectors=physical,
            usable_sectors=usable,mutable_regions=reg,mutable_reserved_end=reserved,
            host_base=s*stride,host_limit=s*stride+reserved,engram_home=s in homes,
            plain_base=plain,yarn_base=yarn,rope_span=span,installed_end=end,
            remaining_sectors=usable-end))
        if s in homes:
            h=homes.index(s)
            stack_records.append(dict(stack_sel=h,usable=usable,rsv=reserved,plain=plain,yarn=yarn,span=span))
            for p in range(32):
                pc_records.append(dict(pc=h*32+p,base=eng_base,limit=eng_limit,physical_stack_id=s))
    return dict(schema='opentallas.s81-native-install.v1',ND=1,NS=4,
        source='same golden descriptor factory and installed allocation records',stacks=output_stacks,
        engram_home_stack_ids=homes,aperture_stack_writes=sorted(stack_records,key=lambda r:r['stack_sel']),
        aperture_pc_writes=sorted(pc_records,key=lambda r:r['pc']),commit_after_records=True,
        descriptors=descriptors,production_reader_binding_verified=False,adopted=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('config',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args(); raw=args.config.read_bytes();cfg=json.loads(raw);out=produce(cfg)
    out['config_sha256']=hashlib.sha256(raw).hexdigest()
    out['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__': main()
