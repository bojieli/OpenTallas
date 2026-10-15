#!/usr/bin/env python3
"""Actual canonical lane demand at the real F2 SRAM geometry.

Counts the existing narrow leaf's service demand and the physical macro-line
coalescing opportunity separately. Wide-line hardware does not yet exist.
No instruction price, throughput threshold or geometry is changed here.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
from su_arith_generate import FIELDS
from su_arith_lower import lower


def unpack(raw):
    d={};shift=0
    for name,width in reversed(FIELDS):
        d[name]=(raw>>shift)&((1<<width)-1);shift+=width
    return d


def cell(address):
    assert 0<=address<1<<18,('outside_actual_local_store',address)
    return (((address>>14)&3)*128+(address&127),
            ((address>>16)<<7)|((address>>7)&127))


def metrics(addresses):
    rows=defaultdict(set);lines=defaultdict(set)
    for a in addresses:
        bank,row=cell(a);rows[bank].add(row);lines[bank].add(row>>3)
    return dict(unique_words=len(set(addresses)),banks=len(rows),
                max_distinct_word_rows_per_bank=max(map(len,rows.values()),default=0),
                max_distinct_macro_lines_per_bank=max(map(len,lines.values()),default=0))


def demand(programme,sut):
    need={'A'}
    if sut['m1']in(1,4,6)or sut['ad']==3 or sut['e2']==1:need.add('B')
    if sut['m2']==1 or sut['qm']or sut['ad']in(1,2)or sut['e1']in(1,2):need.add('C')
    if sut['qm']or sut['ad']==5:need.add('D')
    vectors=[]
    for images in programme:
        requests={n:[]for n in 'ABCDO'}
        for image in images:
            ctl=unpack(image);slot=1<<ctl['ls']
            for lane in range(128):
                if ctl['o_v']+(lane>>ctl['ls'])>=ctl['no']or ctl['i_v']+(lane&(slot-1))>=ctl['ni']:continue
                addresses=[]
                for s,role in enumerate('ABCDO'):
                    base=(ctl['vb']>>(s*24))&0xffffff
                    off=sum((ctl['ld_c']>>(24*(s*10+k)))&0xffffff for k in range(7)if lane>>k&1)
                    addresses.append((base+off)&0xffffff)
                if ctl['cpair']:addresses[2]=addresses[0]^1
                for role,a in zip('ABCDO',addresses):
                    if role in need or(role=='O'and ctl['dst']==1):requests[role].append(a)
        vectors.append({n:metrics(v)for n,v in requests.items()if v})
    return vectors


def main():
    source=Path(sys.argv[1]);out=Path(sys.argv[2]);records=[]
    for folder in ('coverage_ds','coverage_qwen'):
        path=source/folder
        meta=json.loads((path/'su_prod.json').read_text())
        raw=[int(v,16)for v in (path/'su_rec.mem').read_text().split()]
        assert len(raw)==len(meta['cases'])
        for i,value in enumerate(raw):
            summary,programme=lower(value)
            if not summary['supported']:continue
            vectors=demand(programme,summary['sut'])
            narrow=max((m['max_distinct_word_rows_per_bank']for v in vectors for m in v.values()),default=0)
            wide=max((m['max_distinct_macro_lines_per_bank']for v in vectors for m in v.values()),default=0)
            records.append(dict(design=folder,record=i,tag=meta['cases'][i]['tag'],
                words=summary['words'],groups=len(vectors),
                max_narrow_service_beats=narrow,max_wide_macroline_beats=wide,vectors=vectors))
    root=Path(__file__).resolve().parents[2]
    files=['rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv',
           'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
    report=dict(qualified=False,narrow_interface_implemented=True,wide_interface_implemented=False,
        model_only='Actual address demand; wide-line alternative requires RTL, root/wire/latency and native proof',
        geometry=dict(physical_banks=512,read_replicas_per_bank=6,macro_bits=256,selected_leaf_word_bits=32,
                      logical_word_bits=32,words_per_macro_read=8),
        source_sha256={f:hashlib.sha256((root/f).read_bytes()).hexdigest()for f in files},records=records)
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(records=len(records),narrow_conflicted=sum(r['max_narrow_service_beats']>1 for r in records),
        wide_multiline=sum(r['max_wide_macroline_beats']>1 for r in records))))


if __name__=='__main__':main()
