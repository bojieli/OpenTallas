#!/usr/bin/env python3
"""Source-pinned packed136 image on four explicitly allocated real HBM PCs.

The allocation is an input, never guessed from ordinal address bits. All images
retain the PHY's full sector30 address and XOR pseudo-channel mapping. No
weights or scales are invented, reordered within a record, or quantized here.
"""
import argparse
import hashlib
import json
from pathlib import Path
from w19_payload_loader import compact_sectors, logical_records

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def sector_pc(s):
    return ((s>>2)^(s>>7)^(s>>12))&31


def mapped_sector(pc,bank,row,col):
    """Exactly rtl/hbm_accel/service/ot_hbm_kport_map.sv."""
    if not(0<=pc<32 and 0<=bank<32 and 0<=row<32768 and 0<=col<32):
        raise ValueError('actual PHY coordinate bounds')
    bhi=((bank>>2)^(row>>2))&7
    blo=(bank^row)&3
    hi5=((row&3)<<3)|bhi
    s=(row<<15)|(bhi<<12)|(col<<7)|((pc^col^hi5)<<2)|blo
    if sector_pc(s)!=pc:raise AssertionError('actual XOR PC mismatch')
    return s


def validate_allocation(a,payloads):
    if a.get('schema')!='opentallas.hbm-packed136-allocation.v1':
        raise ValueError('explicit packed136 allocation schema required')
    if not a.get('provenance') or not a.get('allocation_id'):
        raise ValueError('source-owned region reservation/provenance required')
    pcs=a.get('pcs')
    if not isinstance(pcs,list) or len(pcs)!=4 or len(set(pcs))!=4 or any(type(x)!=int or not 0<=x<32 for x in pcs):
        raise ValueError('four distinct actual physical PC IDs required')
    for k in ('stack','row_base','row_count','stack_bytes'):
        if type(a.get(k))!=int:raise ValueError('integer allocation field '+k)
    if not 0<=a['stack']<4 or not 0<a['stack_bytes']<=1<<35:
        raise ValueError('stack capacity or identity')
    if payloads<1:raise ValueError('positive payload count')
    sectors=((payloads*136+127)//128)*4
    rows=(sectors+4095)//4096
    if a['row_base']<0 or a['row_count']<rows or a['row_base']+a['row_count']>32768:
        raise ValueError('reserved actual row extent insufficient')
    return sectors


def sector_address(ordinal,a):
    lane=ordinal&3;t=ordinal>>2
    bank=((t>>7)&7)<<2|(t&3)
    col=(t>>2)&31;row=a['row_base']+(t>>10)
    s=mapped_sector(a['pcs'][lane],bank,row,col)
    if (s+1)*32>a['stack_bytes']:raise ValueError('allocated sector outside actual stack capacity')
    return s


def install(source,expected_sha256,payloads,allocation,output):
    source=Path(source);output=Path(output)
    if digest(source)!=expected_sha256:raise ValueError('logical record source SHA mismatch')
    a=json.loads(Path(allocation).read_text());sectors=validate_allocation(a,payloads)
    output.mkdir(parents=True,exist_ok=False)
    seen=set();logical_hash=hashlib.sha256();image_hash=hashlib.sha256()
    paths=[output/'physical.hex',output/'ordinal.jsonl',output/'receipt.json']
    try:
        with paths[0].open('x') as image,paths[1].open('x') as index:
            count=0
            for ordinal,data in enumerate(compact_sectors(logical_records(source),payloads)):
                s=sector_address(ordinal,a)
                if s in seen:raise ValueError('physical allocation alias')
                seen.add(s);logical_hash.update(data)
                line=f'@{s:08x}\n{int.from_bytes(data,"little"):064x}\n'
                image.write(line);image_hash.update(line.encode())
                index.write(json.dumps(dict(ordinal=ordinal,stack=a['stack'],pc=sector_pc(s),sector=s,
                    global_sector=(a['stack']<<30)|s,byte_address=(a['stack']<<35)|(s<<5)))+'\n')
                count+=1
        if count!=sectors:raise AssertionError('exact final line padding count')
        if digest(source)!=expected_sha256:raise ValueError('logical source changed during install')
        record=dict(schema='opentallas.hbm-packed136-installed-image.v1',enabled_default=False,
            allocation=a,allocation_sha256=digest(allocation),logical_source_sha256=expected_sha256,
            payloads=payloads,useful_bytes=payloads*136,physical_bytes=sectors*32,sectors=sectors,
            final_padding_bytes=sectors*32-payloads*136,packed_byte_stream_sha256=logical_hash.hexdigest(),
            physical_hex_sha256=image_hash.hexdigest(),ordinal_manifest_sha256=digest(paths[1]),
            layout='logical j -> allocated pcs[j%4]; perPC t=j//4; bank={t9:7,t1:0}; col=t6:2; row=row_base+(t>>10)',
            native_address_unit='full sector30; global sector32 includes stack2',
            source_dependencies={p:digest(ROOT/p) for p in ['tools/w19_payload_loader.py','tools/hbm_svc_packed136_image.py','rtl/hbm_accel/service/ot_hbm_kport_map.sv','rtl/hbm_accel/ingest/ot_hbm_loader_kport_address.sv']},
            qualified=False,remaining=['Allocation reservation must join current actual global checkpoint manifest',
                'Hardware loader actual installation/ACK and production native83 SM programme not proved',
                'Actual four-PC producer, cold/steady calendar and immutable136B price not proved'])
        paths[2].write_text(json.dumps(record,indent=2)+'\n')
        return record
    except BaseException:
        for p in paths:
            if p.exists():p.unlink()
        output.rmdir()
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--enable-packed136',action='store_true')
    p.add_argument('--source',required=True);p.add_argument('--source-sha256',required=True)
    p.add_argument('--payloads',required=True,type=int);p.add_argument('--allocation',required=True);p.add_argument('--out',required=True)
    args=p.parse_args()
    if not args.enable_packed136:p.error('structural format mode defaults off; --enable-packed136 required')
    print(json.dumps(install(args.source,args.source_sha256,args.payloads,args.allocation,args.out),indent=2))
