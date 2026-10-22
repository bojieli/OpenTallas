#!/usr/bin/env python3
"""Opt-in ATTN reset-forest successor; default pinreg.py output stays unchanged.

Duplicate the actual ASR state transition, never a BUF/INV alias. Partition the
native RESETN endpoints after collapsing transparent cells, preserving polarity.
No serial edge changes. A complete final census must independently validate it.
Usage: reset_partition.py <safe_pr.v> <safe_pr32.v> <report.json> [MUT]
MUT 1 inverts one actual reset endpoint (causal assertion/release negative).
"""
import collections, hashlib, json, math, re, sys

inp, outp, report = sys.argv[1:4]
mut = int(sys.argv[4]) if len(sys.argv)>4 else 0
src=open(inp).read()
assert hashlib.sha256(src.encode()).hexdigest()=='f78cea8af28b15937316ca31ea473a916fe1342d8bf91255bd3023c5dfd2fc5e', 'Exact original pin-registration candidate required'
cre=re.compile(r'^(\s*(?:\(\*[^*]*\*\)\s*)?)(\w+)\s+(c\w+)\s*\((.*)\);\s*$',re.M)
outs={'Y','QN','Q','H','L','CON','SN'}
cells={n:(m,dict((k,v.strip()) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',p))) for _,m,n,p in cre.findall(src)}
loads=collections.defaultdict(list)
for n,(m,ps) in cells.items():
    for p,v in ps.items():
        if p not in outs: loads[v].append((n,p))
def walk(net,polarity=0,seen=frozenset()):
    if net in seen:raise RuntimeError('transparent cycle')
    answer=[]
    for n,p in loads.get(net,[]):
        m,ps=cells[n]
        if m.startswith(('BUF','INV','HB')):
            ys=[v for k,v in ps.items() if k in outs]
            assert len(ys)==1
            answer+=walk(ys[0],polarity^m.startswith('INV'),seen|{net})
        elif p not in ('CLK','CK'): answer.append((n,p,int(polarity)))
    return answer
roots=[]
for n,(m,ps) in cells.items():
    if m.startswith(('BUF','INV','HB')):continue
    for p,v in ps.items():
        if p not in outs:continue
        ends=sorted(set(walk(v)))
        if len(ends)>32:
            assert m=='DFFASRHQNx1_ASAP7_75t_R' and p=='QN', (n,m,p)
            assert all(pin=='RESETN' for _,pin,_ in ends),n
            assert len({(c,pin) for c,pin,_ in ends})==len(ends),n
            roots.append((n,ends))
assert len(roots)==8, len(roots)
new=[];wires=[];edits={};records=[];mut_done=False
for n,ends in roots:
    m,ps=cells[n]; rr=dict(master=n,master_cell=m,original_pins=ps,endpoints=len(ends),clones=[])
    for group in range(1,math.ceil(len(ends)/32)):
        cn=f'cpr32_{n}_{group}'; q=f'npr32_{n}_{group}'
        cp=dict(ps);cp['QN']=q
        new.append('  (* keep = 1 *) '+m+' '+cn+' ('+', '.join('.'+k+'('+v+')' for k,v in cp.items())+');')
        wires.append(q); invq=q+'_inv'; invert_needed=False
        chunk=ends[group*32:(group+1)*32]
        for cell,pin,polarity in chunk:
            if mut and not mut_done:polarity^=1;mut_done=True
            invert_needed |= bool(polarity)
            edits[(cell,pin)]=invq if polarity else q
        if invert_needed:
            wires.append(invq)
            new.append(f'  (* keep = 1 *) INVx1_ASAP7_75t_R cpr32_inv_{n}_{group} (.A({q}), .Y({invq}));')
        rr['clones'].append(dict(name=cn,pins=cp,endpoints=chunk))
    records.append(rr)
def rewrite(match):
    pre,m,n,raw=match.groups()
    ps=cells[n][1]
    for p in list(ps):
        if (n,p) in edits:ps[p]=edits[n,p]
    return pre+m+' '+n+' ('+', '.join('.'+k+'('+v+')' for k,v in ps.items())+');'
dst=cre.sub(rewrite,src)
dst=dst.replace('module qkd_kvs_attn_safe_pr ', 'module qkd_kvs_attn_safe_pr32 ',1)
assert 'module qkd_kvs_attn_safe_pr32 ' in dst
dst=dst.replace('endmodule','\n'+'\n'.join('  wire '+n+';' for n in wires)+'\n'+'\n'.join(new)+'\nendmodule')
dst='// Opt-in same-edge native reset-forest successor; reset_partition.py MUT '+str(mut)+'\n'+dst
open(outp,'w').write(dst)
data=dict(schema='opentallas.attn_reset_partition.v1',input_sha256=hashlib.sha256(src.encode()).hexdigest(),output_sha256=hashlib.sha256(dst.encode()).hexdigest(),mut=mut,extra_ff=sum(len(r['clones']) for r in records),extra_inv=sum('INVx1' in x for x in new),serial_edge_delta=0,rewired_reset_pins=len(edits),roots=records)
assert data['extra_ff']==13
json.dump(data,open(report,'w'),indent=2)
print('ATTN_RESET32_MODEL',json.dumps({k:v for k,v in data.items() if k!='roots'}))
