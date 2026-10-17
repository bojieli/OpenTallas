#!/usr/bin/env python3
"""Variant B: 3 VM slices, one per b2 port PAIR (band), centred in the centre column between the W and E port tiles
of that band; rows interleaved row = band mod 3; SU / seq_su / native59 / xs_tap / tt_ctlm central.  rb_{2b}, rb_{2b+1}
-> slice b.  SU operand window (<= 5 rows) takes <= 2 rows per slice: sq 3 x (3 x 1024); SU write <= 2 rows per slice
(2 x 548) + 150 descriptors + 57 rd = 1303 per slice.  Row-serial service ports at full width per slice (x3)."""
import json, sys
from pathlib import Path
H = Path(__file__).resolve().parent
VM, SU = 'sp_vector_memory', 'sp_su64_sfu'
W_, H_ = 2600.0, 2240.0   # 5.82 mm2 = 15.78 / 3 + ~10 %
base, tag = sys.argv[1], sys.argv[2]
g = json.load(open(base)); I = {i['n']: i for i in g['insts']}
occ = [i for n, i in I.items() if n != VM]
def free(x, y):
    return y >= 21.6 and all(min(x + W_, o['x'] + o['w']) - max(x, o['x']) <= 0 or min(y + H_, o['y'] + o['h']) - max(y, o['y']) <= 0 for o in occ)
xl = I['sp_port_tiles_0']['x'] + I['sp_port_tiles_0']['w']; xr = I['sp_port_tiles_0_f1']['x']
x = (xl + xr) / 2 - W_ / 2
io = I['io_collective']
ys = [io['y'] + io['h'] + 21.6, I['sp_halfres_2']['y'] - 300.0, I['sp_port_tiles_2']['y']]
S = []
for b, y0 in enumerate(ys):
    for d in range(400):
        c = [yy for yy in (y0 + d * 21.6, y0 - d * 21.6) if free(x, yy)]
        if c: break
    s = dict(n=f'vm_s{b}', m='qfd_vm_slice_model', x=round(x, 3), y=round(c[0], 3), w=W_, h=H_); occ.append(s); S.append(s)
names = [s['n'] for s in S]
insts = [i for i in g['insts'] if i['n'] != VM] + S
buses = []; k = 0
for bb in g['buses']:
    name, cl, w, eps = bb
    if VM not in eps: buses.append(bb); continue
    if cl in ('clock_trunk', 'reset'):
        ne = []
        for e in eps:
            if e == VM: ne.append(names[k % 3]); k += 1
            else: ne.append(e)
        buses.append([name, cl, w, ne]); continue
    src, sinks = eps[0], eps[1:]
    if name.startswith('b2_rb_'):
        j = int(name.rsplit('_', 1)[1]); buses.append([name, cl, w, [src, names[j // 2]]]); continue
    if name == 'ng_vm_sq_2048':
        for j in range(3): buses.append([f'{name}_s{j}', cl, 2048, [names[j], SU]])
        continue
    if name == 'ng_vm_sq_0':
        for j in range(3): buses.append([f'{name}_s{j}', cl, 1024, [names[j], SU, 'seq_su']])
        continue
    if name == 'ng_su_va_0':
        for j in range(3): buses.append([f'{name}_s{j}', cl, 1303, [SU, names[j]]])
        continue
    if src == VM:
        for j in range(3): buses.append([f'{name}_s{j}', cl, w, [names[j]] + sinks])
    else:
        buses.append([name, cl, w, [src] + [x_ for e in sinks for x_ in (names if e == VM else [e])]])
json.dump(dict(insts=insts, buses=buses), open(H / 'm' / f'{tag}_B.json', 'w'))
print(tag, [(s['n'], s['x'], s['y']) for s in S])
