#!/usr/bin/env python3
"""QE3-SLICE2B 10-21: kept same-edge copies of TAP flops whose Q is replicated into many hw output bits.
w13c/w13cb census: u_tap.u_114..u_118 each feed 12 hw bits (sign/field replication) -> 12 x D landing slots
= 48 (D=4) / 96 (D=8) loads. Each such flop gets kept duplicates (same C, same D net, same module) so every
copy drives <= PER hw bits (PER=3 -> <=24 loads at D=8). Same edge, same function; idempotent.
usage: s8_tap_hw_copies.py <qfd_dv_s8_tap_bounded.sv> [PER]"""
import re,sys
from pathlib import Path
from collections import defaultdict
p=Path(sys.argv[1]);PER=int(sys.argv[2]) if len(sys.argv)>2 else 3
t=p.read_text()
if '_hwc' in t: print('already applied');sys.exit(0)
m=re.search(r'assign hw = \{([^}]*)\};',t)
nets=[x.strip() for x in m.group(1).split(',')]          # MSB first
pos=defaultdict(list)
for i,n in enumerate(nets): pos[n].append(i)
add_wires=[];add_insts=[];done=[]
for n,ix in pos.items():
    if len(ix)<=PER: continue
    dm=re.search(r'^(\(\* keep=1, keep_hierarchy="yes" \*\) qfd_s8tap_bmath_dff_p #\(\.ID\(\d+\)\) )(u_\d+)\(\.C\((\w+)\),\.D\((\w+)\),\.Q\('+re.escape(n)+r'\)\);$',t,re.M)
    assert dm,f'{n}: driver is not a plain kept dff_p'
    groups=[ix[k:k+PER] for k in range(0,len(ix),PER)]
    for g,grp in enumerate(groups[1:],1):
        c=f'{n}_hwc{g}'
        add_wires.append(c)
        add_insts.append(f'{dm[1]}{dm[2]}_hwc{g}(.C({dm[3]}),.D({dm[4]}),.Q({c}));')
        for i in grp: nets[i]=c
    done.append((n,dm[2],len(ix),len(groups)))
assert done,'no replicated hw flop found'
t=t[:m.start()]+'wire '+', '.join(add_wires)+';\n'+'assign hw = {'+','.join(nets)+'};'+t[m.end():]
t=t.replace('\nendmodule','\n// QE3-SLICE2B kept hw copies (same C/D, same edge)\n'+'\n'.join(add_insts)+'\nendmodule',1)
p.write_text(t)
for d in done: print('net %s driver %s: %d hw bits -> %d kept copies'%d)
