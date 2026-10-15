#!/usr/bin/env python3
"""Independently invert physical image addresses and compare exact source sectors.

This checks installation INPUT files; actual HBM command ACK/readback is a
separate required gate and is never asserted by this software verifier.
"""
import argparse,itertools,json
from pathlib import Path
from hbm_svc_packed136_image import sector_pc,digest
from w19_payload_loader import logical_records,compact_sectors

def inverse(s,d):
    row=s>>15;col=(s>>7)&31
    bank=((((s>>12)&7)^(row>>2))&7)*4+((s^row)&3)
    if not d['region_row_base']<=row<d['region_row_base']+d['region_row_count']:raise ValueError('row outside allocation')
    if sector_pc(s) not in d['pcs']:raise ValueError('unallocated physical PC')
    t=((row-d['region_row_base'])<<10)|((bank>>2)<<7)|(col<<2)|(bank&3)
    return t*4+d['pcs'].index(sector_pc(s))

def physical_words(path):
    with Path(path).open() as f:
        while True:
            address=f.readline()
            if not address:return
            data=f.readline()
            if not address.startswith('@') or len(data.strip())!=64:raise ValueError('truncated physical sector')
            yield int(address[1:],16),int(data,16).to_bytes(32,'little')

def check(directory,physical_path=None):
    directory=Path(directory);r=json.loads((directory/'receipt.json').read_text());d=r['descriptor']
    if digest(directory/'records.hex')!=r['records_file_sha256']:raise ValueError('source record hash mismatch')
    count=0
    for actual,expected in itertools.zip_longest(physical_words(physical_path or directory/'physical.hex'),compact_sectors(logical_records(directory/'records.hex'),r['records'])):
        if actual is None or expected is None:raise ValueError('missing/extra physical sector')
        s,data=actual
        if inverse(s,d)!=d['packed_sector_offset']+count:raise ValueError('wrong physical address or order')
        if data!=expected:raise ValueError('source payload/readback mismatch')
        count+=1
    if count!=r['sectors']:raise ValueError('sector count')
    return dict(sectors=count,source_payload_and_inverse_address_pass=True,actual_HBM_ACK=False,actual_HBM_readback=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');p.add_argument('--physical');a=p.parse_args();print(json.dumps(check(a.directory,a.physical)))
