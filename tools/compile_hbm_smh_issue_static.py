#!/usr/bin/env python3
"""Offline issue-control compiler for production SUB4/LBS2/LSB16/NC8/IL8.

Input JSON: ops[{rows,K|groups,c=8,fmt,gs=true,x_base=0,launch_cycle,
base_tag=0}], requests[{cycle,addr,tag}], optional packet_lines[1088-bit hex].
launch_cycle denotes an issue_pq launch edge, phase cycle%8, reset phase zero.
The enclosing compiler owns dependencies, x-load and retirement capacity. There
are no dynamic ready/credit/retire gates. Requests are explicit reservations;
physical sector/PC metadata passes through reservations, without guessing memory
latency. Commands are available at programme start+4; S1 hop is start+6. These
transport offsets are reported separately from the issue_pq reference calendar.
INT8 must wait for composition of its separately owned static adapter.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PINNED = ['rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv',
          'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv',
          'tools/dshbm_matched_sm_seq.py', 'tools/uarch_model.py']
FMT = {'bf16': 0, 'fp8': 1, 'fp4': 2}
IL, XD, RMAX, SLAT, DBF = 8, 128, 4096, 7, 11


def normalize(raw):
    o = dict(raw)
    o['fmt'] = FMT.get(o['fmt'], o['fmt'])
    if o['fmt'] not in (0, 1, 2):
        raise ValueError('fmt3/INT8 has no integrated static issue compiler')
    if 'groups' not in o:
        k = int(o['K'])
        width = (512, 1024, 2048)[o['fmt']]
        if k <= 0:
            raise ValueError('K must be positive')
        o['groups'] = (k + width - 1) // width
    for k, v in dict(c=8, gs=True, x_base=0, base_tag=0).items():
        o.setdefault(k, v)
    if type(o['gs']) is not bool:
        raise ValueError('gs must be boolean')
    for k in ('rows', 'c', 'groups', 'fmt', 'x_base', 'base_tag', 'launch_cycle'):
        if type(o[k]) is not int:
            raise ValueError(f'{k} must be integer')
    if not (1 <= o['rows'] <= RMAX and o['c'] == 8 and 1 <= o['groups'] <= 16):
        raise ValueError('requires production R1..4096, c8, G1..16')
    if not (o['c']*o['groups'] <= XD and 0 <= o['x_base'] < XD and o['launch_cycle'] >= 1 and 0 <= o['base_tag'] < 1024):
        raise ValueError('invalid x footprint, launch or base_tag')
    return o


def issue_slots(raw):
    """Closed-form wave/t/slot traversal, including padded advances."""
    o = normalize(raw)
    r, g, c = o['rows'], o['groups'], o['c']
    cy = ((o['launch_cycle'] + 2 + IL - 1) // IL) * IL
    waves = (r*g+IL-1)//IL if o['gs'] else (r+IL-1)//IL
    for wave in range(waves):
        for group_step in range(1 if o['gs'] else g):
            for t in range(c):
                for si in range(IL):
                    item = wave*IL+si
                    row, group = divmod(item, g) if o['gs'] else (item, group_step)
                    yield dict(cycle=cy,row=row,group=group,t=t,si=si,
                               real=item < (r*g if o['gs'] else r),
                               first=t == 0,last=t == c-1,glast=group == g-1,
                               slot=row%IL,xa=(group*c+t+o['x_base'])%XD)
                    cy += 1


def control(s):
    return (int(s['real'])<<25 | int(s['first'])<<24 | int(s['last'])<<23 |
            (s['row'] & 4095)<<11 | int(s['glast'])<<10 | s['slot']<<7 | s['xa'])


def compile_manifest(manifest):
    commands, slots, ops, identities = {}, [], [], []
    previous = None
    for oi, raw in enumerate(manifest['ops']):
        o = normalize(raw)
        ss = list(issue_slots(o))
        if previous:
            p, end = previous
            pd = DBF*(p['fmt']==0)+SLAT*(p['groups']-1).bit_length()
            nd = DBF*(o['fmt']==0)+SLAT*(o['groups']-1).bit_length()
            need = max(0, DBF*((p['fmt']==0)-(o['fmt']==0)), pd-nd)
            # since resets at end edge; launch sees since > need.
            if o['launch_cycle'] < end+need+2:
                raise ValueError(f'op {oi}: launch violates hazard need={need}, previous_end={end}')
        launch = o['launch_cycle']
        if launch in commands:
            raise ValueError('format/issue collision')
        commands[launch] = 1<<28 | o['fmt']<<26
        line = 0
        for s in ss:
            cy = s['cycle']
            if cy in commands:
                raise ValueError('operation overlap')
            word = control(s)
            if s['real']:
                tag = (o['base_tag']+line)%1024
                word |= 1<<29 | tag<<30
                identities.append(dict(op=oi,line=line,cycle=cy,tag=tag))
                line += 1
            commands[cy] = word
            slots.append(dict(op=oi,**s))
        ops.append(dict(**o, first_issue=ss[0]['cycle'],last_advance=ss[-1]['cycle'],
                        last_real_issue=max(s['cycle'] for s in ss if s['real']),
                        real_lines=line,padded_advances=len(ss)-line))
        previous = o, ss[-1]['cycle']
    for q in manifest.get('requests', []):
        cy, addr, tag = q['cycle'], q['addr'], q['tag']
        if not (type(cy) is int and cy >= 0 and 0 <= addr < 2**32 and 0 <= tag < 1024):
            raise ValueError('invalid request reservation')
        if commands.get(cy,0)>>82:
            raise ValueError('two requests on one cycle')
        commands[cy] = commands.get(cy,0) | (1<<42 | addr<<10 | tag)<<40
    packets = []
    lines = manifest.get('packet_lines')
    if lines is not None:
        if len(lines) != len(identities):
            raise ValueError('packet_lines must contain exactly real nonpadding lines')
        for meta, text in zip(identities, lines):
            data = int(text,16)
            if not 0 <= data < 2**1088:
                raise ValueError('packet exceeds 1088 bits')
            packets.append(1<<1098 | meta['tag']<<1088 | data)
    return dict(schema='opentallas.hbm_smh.issue_static.v1',
                shape=dict(SUB=4,LBS=2,LSB=16,NC=8,IL=8,RMAX=4096,XD=128,LEV=4),
                programme_output_offset=4, feed_s1_hop_offset=6,
                sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in PINNED},
                ops=ops, slots=slots, packet_identities=identities,
                reservations=manifest.get('reservations',[]),
                qualification='issue-control only; no full-SM throughput claim',
                commands=[commands.get(cy,0) for cy in range(max(commands,default=0)+1)],
                packets=packets)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    a = ap.parse_args()
    result = compile_manifest(json.loads(a.manifest.read_text()))
    a.out.mkdir(parents=True,exist_ok=True)
    commands, packets = result.pop('commands'), result.pop('packets')
    (a.out/'programme83.hex').write_text(''.join(f'{w:021x}\n' for w in commands))
    if packets:
        (a.out/'packet1099.hex').write_text(''.join(f'{w:0275x}\n' for w in packets))
    result['cycles'] = len(commands)
    result['programme_sha256'] = hashlib.sha256((a.out/'programme83.hex').read_bytes()).hexdigest()
    (a.out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__ == '__main__':
    main()
