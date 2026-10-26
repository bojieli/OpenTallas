#!/usr/bin/env python3
"""Actual fixture-to-native tensor copy plan. No implicit SID relocation.

The complete 2^18-word VM image fits the real 1MiB logical SU store. Keep VM
word identity in local storage; no compressed descriptor or capacity fiction.
This first legal allocation serializes each record's stage/execute/drain phases.
Cycle qualification needs the real arithmetic calendar and inter-tile routes;
transport minima reported here are lower bounds, never service measurements.
"""
import argparse,hashlib,json,sys,gzip
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hbm_static'))
from su_program_inventory import decode


def addresses(raw):
    dispatch,unit,sut,desc=decode(raw)
    ni,no=dispatch['n'][0],desc['A'].m
    needed={'A'}
    if sut['m1'] in(1,4,6)or sut['ad']==3 or sut['e2']==1:needed.add('B')
    if sut['m2']==1 or sut['qm']or sut['ad']in(1,2)or sut['e1']in(1,2):needed.add('A'if sut['c_pair']else'C')
    if sut['qm']or sut['ad']==5:needed.add('D')
    if sut['a_ind']:raise ValueError('runtime lane gather needs its real index/read calendar')
    src,dst=set(),set()
    for name,md in desc.items():
        used=name in needed or(name=='O'and sut['dst'])or(name=='R'and sut['red'])
        if not used:continue
        if md.space!='VM':raise ValueError('nonVM tensor needs its actual native producer')
        if name=='R':
            n=1 if sut['red_whole']or sut['red_tree']else no
            words={md.base+i*(md.stride or 1)for i in range(n)}
        else:
            words={md.base+o*md.stride+((i>>1)if name in'BD'and sut['b_half']else i)*(0 if md.ibcast else(md.istride or 1))for o in range(no)for i in range(ni)}
            if name=='A'and sut['c_pair']:words|={a^1 for a in words}
        (dst if name in'OR'else src).update(words)
    if any(a<0 or a>=1<<18 for a in src|dst):raise ValueError('tensor exceeds real 2^18-word store')
    return src,dst


def native_sector(sector):
    return dict(SID=(sector>>13)&3,bank=sector&7,row=(sector>>3)&1023,sec16=sector)


def local_word(word):
    # The stored 4-frame geometry is exact, including quarter identity.
    return dict(frame=(word>>16)&3,quarter=(word>>14)&3,bank=word&127,
                row=((word>>16)<<7)|((word>>7)&127),word_in_macro=(word>>7)&7)


def masks(words):
    result={}
    for word in words:result[word>>3]=result.get(word>>3,0)|(1<<(word&7))
    return result


def plan(directory):
    manifest=json.loads((directory/'su_prod.json').read_text())
    coverage=json.loads((directory/'su_coverage.json').read_text())
    raw=[int(x,16)for x in(directory/'su_rec.mem').read_text().split()]
    records=[]
    for bits,rec in zip(raw,manifest['cases']):
        src,dst=addresses(bits);stage=masks(src);drain=masks(dst)
        histogram=[0]*32
        for s in stage:histogram[(((s>>13)&3)*8)+(s&7)]+=1
        # One port per bank per fixed slot. Different banks issue in parallel.
        slots=[[]for _ in range(max(histogram,default=0))]
        cursor=[0]*32
        for s in sorted(stage):
            native=native_sector(s);bank=native['SID']*8+native['bank'];cycle=cursor[bank];cursor[bank]+=1
            slots[cycle].append(dict(source_vm_sector=s,source_native=native,
                source_mask=stage[s],local_first_word=local_word(s*8)))
        records.append(dict(tag=rec['tag'],unit=rec['unit'],stage_words=len(src),drain_words=len(dst),
            stage_sector_slots=slots,stage_bank_counts=histogram,
            stage_minimum_edges=len(slots),drain_masks={str(k):v for k,v in sorted(drain.items())},
            drain_native={str(s):native_sector(s)for s in sorted(drain)},
            overlap_words=len(src&dst),local_identity=True,source_guard='all used source words staged before execution',
            drain_guard='only actual output words written; preexisting VM words outside mask preserved',
            transport='Cross-quarter source/local mismatch needs real static COLL route, not a changed source SID',
            priced_cycles=rec['priced']))
    return dict(status='actual canonical fixture allocation/copy plan, not executed whole SU',
        canonical_coverage=coverage,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in directory.iterdir()if p.is_file()},
        physical_store=dict(logical_bytes=1048576,physical_bytes=12582912,SRAMs=3072,banks=512,read_replicas=6),
        local_mapping='each word v keeps identity: frame=v[17:16],quarter=v[15:14],bank=v[6:0],row={v[17:16],v[13:7]}; sector emits words s*8+k where source_mask[k]',records=records,qualification=False,missing=['actual SRAM dispatch network','arithmetic calendar/full reduction/native stream joins','COLL cross-quarter staging routes','fullprogramme execution and immutable service measurement'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=plan(a.vectors);a.out.parent.mkdir(parents=True,exist_ok=True);payload=(json.dumps(result,separators=(',',':'))+'\n').encode(); a.out.write_bytes(gzip.compress(payload,mtime=0) if a.out.suffix=='.gz' else payload)
    print(json.dumps(dict(records=len(result['records']),stage_words=sum(r['stage_words']for r in result['records']),qualification=False)))
if __name__=='__main__':main()
