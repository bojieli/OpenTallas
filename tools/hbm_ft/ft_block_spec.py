#!/usr/bin/env python3
"""FT-HBM per-block feedthrough spec (estimate from lane_census.py paths + coordinator insts.tsv).

For every instance of the masters matching --master, the lanes whose straight L path passes THROUGH it (enters one face,
leaves the opposite one) are mapped into the MASTER frame (orientation R0/MX/MY/R180 undone) and grouped by master
direction (NS/SN/WE/EW).  Per instance and per master direction: bits, lane count, crossing offsets.  The bundle proposal
puts each direction's ft bundle at the master centre line (MY/MX/R180 replicas then line up with themselves), pins on the
die/ft layers (M9 vertical for N-S, M8 horizontal for E-W), face width = bits * pitch / util (FT-PLAN face rule), and
in-block stages: registered in + out (pin-register rule) and a relay every <= HOP um between them; repeater sites <= REP um.
Only lanes whose straight route saves >= 1 stage at HOP over the current channel route are counted as 'gain' lanes.

    ft_block_spec.py paths.json insts.tsv --master ot_hbm_accel_smh_attn --hop 1000 --out spec.json
"""
import argparse, collections, json, math, re
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('paths'); ap.add_argument('insts')
ap.add_argument('--master', required=True, help='regex on master name')
ap.add_argument('--hop', type=float, default=1000.0)
ap.add_argument('--rep', type=float, default=450.0)
ap.add_argument('--pitch', type=float, default=0.08, help='M8/M9 track pitch um')
ap.add_argument('--util', type=float, default=0.5, help='face pin utilisation')
ap.add_argument('--gain-only', action='store_true', help='count only lanes whose straight route saves >= 1 stage')
ap.add_argument('--out', required=True)
a = ap.parse_args()
P = json.load(open(a.paths))
I = {}
for l in open(a.insts):
    f = l.rstrip('\n').split('\t'); I[f[0]] = dict(m=f[1], x=float(f[2]), y=float(f[3]), w=float(f[4]), h=float(f[5]), o=f[6])
FLIPX = {'MY': True, 'R180': True}; FLIPY = {'MX': True, 'R180': True}
def to_master(d, o):
    if d in ('NS', 'SN') and FLIPY.get(o): d = d[::-1]
    if d in ('WE', 'EW') and FLIPX.get(o): d = d[::-1]
    return d
inst = collections.defaultdict(lambda: collections.defaultdict(lambda: dict(bits=0, lanes=0, offs=[])))
masters = {}
for p in P:
    gain = p.get('r1000', p['s1000']) - p['s1000']
    if a.gain_only and gain <= 0: continue
    for n, v in p['cross'].items():
        b = I[n]
        if not re.search(a.master, b['m']) or not v['through']: continue
        md = to_master(v['through'], b['o'])
        A, B = p['a'], p['b']
        if p['L'] == 'HV': hx, vy = B[0], A[1]          # H segment at y=A.y, V segment at x=B.x
        else: hx, vy = A[0], B[1]
        off = (hx - b['x']) if md in ('NS', 'SN') else (vy - b['y'])
        if md in ('NS', 'SN') and FLIPX.get(b['o']): off = b['w'] - off
        if md in ('WE', 'EW') and FLIPY.get(b['o']): off = b['h'] - off
        e = inst[n][md]; e['bits'] += p['bits']; e['lanes'] += 1; e['offs'].append(round(off))
        masters[n] = b
out = dict(master_re=a.master, hop_um=a.hop, rep_um=a.rep, gain_only=a.gain_only, instances={}, bundles={})
need = collections.defaultdict(int)
for n, D in sorted(inst.items()):
    b = masters[n]
    out['instances'][n] = dict(master=b['m'], orient=b['o'], dirs={d: dict(bits=e['bits'], lanes=e['lanes'], off_min=min(e['offs']), off_max=max(e['offs'])) for d, e in D.items()})
    for d, e in D.items(): need[(b['m'].split('__pv')[0], d)] = max(need[(b['m'].split('__pv')[0], d)], e['bits'])
for (m, d), bits in sorted(need.items()):
    b = next(x for x in masters.values() if x['m'].split('__pv')[0] == m)
    L = b['h'] if d in ('NS', 'SN') else b['w']; F = b['w'] if d in ('NS', 'SN') else b['h']
    hops = max(1, math.ceil(L / a.hop))            # in-reg at entry face, out-reg at exit face, relays between
    face = bits * a.pitch / a.util
    out['bundles'][f'{m}:{d}'] = dict(max_inst_bits=bits, layer='M9' if d in ('NS', 'SN') else 'M8', length_um=L,
        face_um=round(face, 1), face_avail_um=F, face_ok=face <= 0.8 * F, centre_offset_um=round(F / 2, 3),
        in_block_regs=hops + 1, in_block_cycles=hops, repeater_sites=max(0, math.ceil(L / a.rep) - 1),
        flops=bits * (hops + 1), insts_using=sum(1 for n in inst if inst[n].get(d) and masters[n]['m'].split('__pv')[0] == m))
json.dump(out, open(a.out, 'w'), indent=1)
for k, v in out['bundles'].items(): print(k, v)
