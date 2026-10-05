#!/usr/bin/env python3
"""Check finite candidate banks. Input JSON: cycles of physical requests.
No stalls are inserted; conflicts disqualify unchanged-cycle composition.
Schema each row: cycle, code_addr(null/int), scale_reads[{group,addr}],
vm_reads[{group,addr(element)}], vm_writes[{group,addr(word),mask}].
"""
import argparse,json,csv,gzip
from collections import defaultdict

def check(rows, vm_depth=1024):
    problems=[]; counts=defaultdict(int)
    previous=-1
    for row in rows:
        cycle=row['cycle']
        if cycle<=previous: raise ValueError('cycles must increase')
        previous=cycle
        code=row.get('code_addr')
        if code is not None:
            counts['code_reads']+=2
            if not 0<=code<8192: problems.append([cycle,'code_depth',code])
        seen=set()
        for read in row.get('scale_reads',[]):
            g,a=read['group'],read['addr']
            if not 0<=g<4 or not 0<=a<8192: problems.append([cycle,'scale_range',g,a])
            if g in seen: problems.append([cycle,'scale_port',g])
            seen.add(g);counts['scale_reads']+=1
        reads=defaultdict(set);writes=defaultdict(list)
        for r in row.get('vm_reads',[]):
            a=r['addr'];w=a//16
            if a<0 or w//4>=vm_depth: problems.append([cycle,'vm_read_depth',a])
            reads[w%4].add(w//4);counts['vm_scalar_reads']+=1
        for r in row.get('vm_writes',[]):
            a=r['addr']
            if a<0 or a//4>=vm_depth: problems.append([cycle,'vm_write_depth',a])
            if r.get('mask',65535): writes[a%4].append(a//4);counts['vm_word_writes']+=1
        for bank,addrs in reads.items():
            if len(addrs)>1: problems.append([cycle,'vm_read_port',bank,sorted(addrs)])
        for bank,addrs in writes.items():
            if len(addrs)>1: problems.append([cycle,'vm_write_port',bank,addrs])
            if set(addrs)&reads.get(bank,set()): problems.append([cycle,'vm_read_during_write_unqualified',bank])
    return {'status':'candidate_conflict' if problems else 'trace_subset_ports_fit_not_physical_pass',
            'cycles_examined':len(rows),'counts':dict(counts),'problems':problems,
            'claim':'Only supplied trace and proposed four single-read/single-write word banks; not RTL/arithmetic/physical verification.'}

def load_csv(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt') as f: raw=list(csv.DictReader(f))
    grouped={}
    for r in raw:
        if int(r['edge'])==0: continue
        key=(r['case'],r['cycle'])
        x=grouped.setdefault(key,dict(cycle=len(grouped),code_addr=None,scale_reads=[],vm_reads=[],vm_writes=[]))
        def n(k): return int(r[k],0)
        if n('wrom_re'): x['code_addr']=n('wrom_addr')
        if n('scale_re'): x['scale_reads'].append(dict(group=n('group'),addr=n('scale_addr')))
        if n('x_re'): x['vm_reads'].append(dict(group=n('group'),addr=n('x_addr')))
        if n('o_we'): x['vm_writes'].append(dict(group=n('group'),addr=n('o_addr'),mask=n('o_mask')))
    return list(grouped.values())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trace');p.add_argument('--output');a=p.parse_args()
    r=check(load_csv(a.trace) if '.csv' in a.trace else json.load(open(a.trace)));s=json.dumps(r,indent=2)+'\n'
    if a.output:open(a.output,'w').write(s)
    else:print(s,end='')
