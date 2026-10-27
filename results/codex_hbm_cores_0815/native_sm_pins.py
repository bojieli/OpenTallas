#!/usr/bin/env python3
"""Native SM four-master candidate interfaces, sized before any physical kit.

Input is the exact native capacity census, output is a pin MODEL, not a frozen
plan. One native bus stays on one face. BDC/TCL use MY orientation where their
operand partner is east; TCT N sum/lf pins align with two TCL S outputs whose
origins are 0 and 108um. Clock-entry macro clearance and parent station reach
remain composing-plan obligations. No source logic or pipeline edge changes.
"""
import bisect
import collections
import hashlib
import json
from pathlib import Path
import sys

DIMS = {'hnx_xs3': [561.6,289.44], 'ot_hbm_accel_smh_bdc': [112.32,142.56],
        'ot_hbm_accel_smh_tcl': [86.4,120.96], 'ot_hbm_accel_smh_tct': [194.4,71.28]}


def face(mod, name, direction):
    if mod == 'hnx_xs3':
        if name.startswith('o_') and (name.endswith('_w') or name == 'o_iv_fw'): return 'W'
        if name.startswith('o_') and name.endswith('_e'): return 'E'
        if name == 'rl1' or name.startswith('o_'): return 'N'
        return 'S'
    if mod.endswith('_bdc'):
        return 'W' if name == 'i_w' else ('E' if direction == 'output' else ('N' if name == 'rst_a' else 'S'))
    if mod.endswith('_tcl'):
        return 'S' if direction == 'output' else ('N' if name == 'rst_a' else 'W')
    return 'S' if direction == 'output' else ('E' if name == 'rst_a' else 'N')


def snap(v): return round(.024 + .048*round((v-.024)/.048), 6)


def build(capacity, out):
    out = Path(out); out.mkdir(parents=True,exist_ok=True)
    profiles = json.loads(Path(capacity).read_text())['profiles']
    report = dict(scope='PIN MODEL ONLY: compose native parent macros, soft stations and PG/clock before P&R',
                  source_capacity_sha256=hashlib.sha256(Path(capacity).read_bytes()).hexdigest(),
                  source_rtl_commit='4d6f5439dc', added_cycles=0, models=[])
    tables = {}
    for mod, (w,h) in DIMS.items():
        groups = collections.defaultdict(list)
        pins = [dict(name='clk',layer='M5',x=snap(w/2),y=round(h/2,6))]
        for port in profiles[mod]['port_buses']:
            n, width = port['name'], port['width']
            if n == 'clk': continue
            f = face(mod,n,port['direction'])
            groups[f].extend(n if width == 1 else f'{n}[{i}]' for i in range(width))
        for f, names in groups.items():
            length = h if f in 'EW' else w
            lo = round((8.64-.024)/.048); hi = round((length-8.64-.024)/.048)
            for i,n in enumerate(names):
                c = round(.024 + .048*round(lo+(hi-lo)*(i+.5)/len(names)),6)
                pins.append(dict(name=n, layer='M4' if f in 'EW' else 'M5',
                    x=.019 if f=='W' else (round(w-.019,6) if f=='E' else c),
                    y=.019 if f=='S' else (round(h-.019,6) if f=='N' else c)))
        tables[mod] = pins
    # Align both complete native TCL result bundles to the TCT N seam by bit.
    # Its two leaf inputs are sum_i={s1,s0}, lf_a=lf0, lf_b=lf1.
    tcl = {p['name']:p for p in tables['ot_hbm_accel_smh_tcl']}
    for p in tables['ot_hbm_accel_smh_tct']:
        n = p['name']
        if n.startswith('sum_i['):
            bit = int(n.split('[')[1][:-1]); p['x'] = round(tcl[f'sum_o[{bit%256}]']['x'] + 108*(bit//256),6)
        elif n in ('lf_a','lf_b'):
            p['x'] = round(tcl['lfault']['x'] + (108 if n=='lf_b' else 0),6)
        elif n in ('i_v','i_last') or n.startswith('i_tag['):
            bit = 0 if n=='i_v' else (1 if n=='i_last' else 2+int(n.split('[')[1][:-1]))
            p['x'] = snap(88.56+bit*.96)
    for mod,(w,h) in DIMS.items():
        pins = tables[mod]; groups=collections.defaultdict(list)
        expected={p['name'] if p['width']==1 else f"{p['name']}[{i}]"
                  for p in profiles[mod]['port_buses'] for i in range(p['width'])}
        assert expected == {p['name'] for p in pins} and len(pins)==len(expected)
        for p in pins:
            if p['name']=='clk':continue
            f=min([(p['x'],'W'),(w-p['x'],'E'),(p['y'],'S'),(h-p['y'],'N')])[1]
            c=p['y'] if f in 'EW' else p['x'];assert abs(c-snap(c))<1e-5
            groups[f].append(c)
        stats={}
        for f,cs in groups.items():
            cs.sort();assert len(set(cs))==len(cs)
            peak=max(bisect.bisect_right(cs,c+10)-i for i,c in enumerate(cs))/10
            assert peak<=6,(mod,f,peak)
            stats[f]=dict(pins=len(cs),peak_per_um_10um=peak)
        rel=mod+'.json';data=json.dumps(pins,indent=1)+'\n';(out/rel).write_text(data)
        report['models'].append(dict(module=mod,outline_um=[w,h],pins_file=rel,pins=len(pins),
            pins_sha256=hashlib.sha256(data.encode()).hexdigest(),faces=stats,
            native_std_cells=profiles[mod]['std_cells'],clock_entry_um=[snap(w/2),h/2],
            qualification='PIN_MODEL_ONLY'))
    (out/'models.json').write_text(json.dumps(report,indent=1)+'\n')
    print('native source pin sets exact; four models peak <=6/um; 514 TCL/TCT abutting data pins aligned')


if __name__=='__main__':build(sys.argv[1],sys.argv[2])
