#!/usr/bin/env python3
"""Plan the compact BF column against both exact c10 front seams; no routed-view claim.

The one master is placed R0 on the left and MY on the right. Data pins must match
both front faces. Move reset off that seam and spread all south return/partial
pins. This is a slot-change request: unchanged RTL/outline and zero added cycles.
Run: python3 tools/s81/bf_column_c10_pinplan.py --out DIR
"""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEF = 'physical/s81_die_views/bf_compact199/ot_v41_bf_col/ot_v41_bf_col.lef'
RTL = 'rtl/v41rom/ot_v41_bf_col.sv'
REF = '5fce4c7b5607c476c206908187ebf6371fbb73ba'
FRONT = 'physical/ref_tile_specs/s81_bf_native_1015/static_pins_c10s/pin_request.json'


def source(path):
    return subprocess.check_output(['git', 'show', f'{REF}:{path}'], cwd=ROOT)


def plan():
    closed_commit='05a8d46eea3ed1b180ba21f2b4042d96dc49e2c8'
    runner_path='tools/s81/run_bf_hier_physical.py'
    runner=subprocess.check_output(['git','show',f'{closed_commit}:{runner_path}'],cwd=ROOT)
    assignment=next(n for n in ast.parse(runner).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='QP' for t in n.targets))
    params={k.arg:ast.literal_eval(k.value) for k in assignment.value.keywords}
    params.update(BXST=2,FXST=2,HDLY=0)
    raw = source(LEF)
    front_raw = source(FRONT)
    front = json.loads(front_raw)['pins']
    old = {}
    for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n', raw.decode(), re.S):
        if re.search(r'USE (POWER|GROUND)', m[2]):
            continue
        r = re.search(r'LAYER (\S+) ;\s+RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', m[2])
        assert r, m[1]
        ly = r[1]
        x0, y0, x1, y1 = map(float, r.groups()[1:])
        x, y = (x0+x1)/2, (y0+y1)/2
        face = 'E' if x > 449 else 'N' if y > 198 else 'S' if y < 1 else 'W'
        old[m[1]] = dict(layer=ly, x=round(x, 6), y=round(y, 6), face=face)
    assert len(old) == 842
    new = {n: dict(p) for n, p in old.items()}
    seam = {}
    for side in (0, 1):
        face = {p['source_pin'][3:]: p for n, p in front.items() if n.startswith(f'c{side}[')}
        assert len(face) == 776
        assert all(n in old for n in face)
        if side == 1:
            assert all(face[n]['y'] == seam[n]['y'] and face[n]['layer'] == seam[n]['layer'] for n in face)
        seam = face
    for n, p in seam.items():
        new[n] = dict(layer=p['layer'], x=450.144, y=p['y'], face='E')
    # Existing reset sat only .072 um from a stretched data-pin centre.
    new['rst_n_pin'] = dict(layer='M5', x=227.148, y=0.0, face='S')
    south = sorted((n for n, p in old.items() if p['face'] == 'S'), key=lambda n: old[n]['x'])
    assert len(south) == 64 and south[-1] == 'qy_bkf'
    for i, n in enumerate(south):
        # 1.152 um / pin vs legacy .096: same order, clear S return corridor.
        new[n] = dict(layer='M5', x=round(375.324 + i*1.152, 6), y=0.0, face='S')
    assert new['clk'] == old['clk']
    assert set(new) == set(old)
    for n,p in new.items():
        assert 0 <= p['x'] <= 450.144 and 0 <= p['y'] <= 198.72, n
    for n,p in new.items():
        for q,v in new.items():
            if n >= q or p['face'] != v['face'] or p['layer'] != v['layer']:
                continue
            k = 'x' if p['face'] in 'NS' else 'y'
            assert abs(p[k]-v[k]) >= .096-1e-6, (n,q)
    return dict(schema='opentallas.s81.bf_column_c10_pinplan.v1',
                status='REQUESTED_NOT_ROUTED_NOT_NATIVE_QUALIFIED',
                source_commit=REF, source_lef=LEF, source_lef_sha256=hashlib.sha256(raw).hexdigest(),
                source_rtl=RTL, source_rtl_sha256=hashlib.sha256(source(RTL)).hexdigest(),
                front_request=FRONT, front_request_sha256=hashlib.sha256(front_raw).hexdigest(),
                top='ot_v41_bf_col', outline_um=[450.144,198.72],
                placements=[dict(name='left', orient='R0', xy_um=[0,0]),
                            dict(name='front', orient='R0', xy_um=[451.332,0]),
                            dict(name='right', orient='MY', xy_um=[569.16,0])],
                pair_outline_um=[1019.304,198.72],
                closed_source_commit=closed_commit, parameter_runner=runner_path,
                parameter_runner_sha256=hashlib.sha256(runner).hexdigest(), parameters=params,
                parameters_scope='Historical exact column build QP + BXST2 FXST2 HDLY0; no borrowed timing or clock qualification',
                reroute_reason='slot_change: c10 connected seam pin stretch, reset off seam, south partial/return spread',
                changes=dict(seam_bits=776, matched_front_faces=2, seam_y_mismatches=0,
                             south_pins=64, south_pitch_um=1.152, reset='E to S x227.148',
                             clock='N x227.148 unchanged', cycles_added=0, area_added_um2=0),
                geometric_cut=dict(basis='one M4 track per bit, 0.048um pitch; excludes PG/obstruction derating and is not routed cut proof',
                                   seam_bits=776, seam_span_um=194.16, seam_track_fraction=round(776/(194.16/.048),6),
                                   south_bits=64, south_span_um=72.576, south_track_fraction=round(64/(72.576/.048),6),
                                   limit=.60),
                open_gates=['actual column CTS insertion/roots (historical 535ps/53493 sinks fails native)',
                            'actual column native launch/capture and TT/FF/DRC0',
                            'parent S partial/return/reset real routes and static schedule',
                            'front c10 post-ECO native audit'],
                pins=new)


def figure(rec, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,8))
    a=axes[0]
    for n,v in rec['pins'].items():
        if v['face']=='E':a.scatter(450.144,v['y'],s=2,c='blue')
        elif n=='clk':a.scatter(v['x'],198.72,s=30,c='red');a.text(v['x'],187,'clk N unchanged',ha='center')
        elif n=='rst_n_pin':a.scatter(v['x'],0,s=30,c='red');a.text(v['x'],8,'reset S',ha='center')
        elif v['face']=='S':a.scatter(v['x'],0,s=3,c='green')
    a.plot([0,450.144,450.144,0,0],[0,0,198.72,198.72,0],c='black')
    a.set_aspect('equal')
    a.set(xlim=(-10,460),ylim=(-10,210),xlabel='um',ylabel='um',title='One master, left R0 / right MY; all 842 functional pins')
    a=axes[1]
    front=json.loads(source(FRONT))['pins']
    for n,v in front.items():
        if n.startswith('c0['):
            cp=rec['pins'][v['source_pin'][3:]]
            a.plot([0,1],[cp['y'],v['y']],c='blue',lw=.3,alpha=.3)
    a.set(xticks=[0,1],xticklabels=['column E','front W/E'],ylim=(0,199),ylabel='y (um)',title='776 straight same-track connections on both seams')
    fig.suptitle('PROPOSED, NOT ROUTED: coherent BF c10 column pin plan\nE data matches c10; S payload 12x wider pitch; reset off seam; clock N kept')
    fig.tight_layout();fig.savefig(output,dpi=130);plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--figure',action='store_true')
    a=ap.parse_args()
    rec=plan();a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'pin_request.json').write_text(json.dumps(rec,indent=2)+'\n')
    t=['# Source-pinned proposed column c10 pin plan; NOT a routed view.']
    for n,p in sorted(rec['pins'].items()):
        size='.192 .024' if p['layer']=='M4' else '.024 .192'
        x=p['x'];y=p['y']
        if n=='clk':y=198.72
        t.append(f'place_pin -pin_name {{{n}}} -layer {p["layer"]} -location {{{x} {y}}} -pin_size {{{size}}} -force_to_die_boundary')
    (a.out/'pins.tcl').write_text('\n'.join(t)+'\n')
    if a.figure:
        figure(rec,a.out/'connected_plan.png')
    print(json.dumps(rec['changes']))


if __name__=='__main__':main()
