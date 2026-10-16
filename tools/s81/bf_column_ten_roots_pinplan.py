#!/usr/bin/env python3
"""Literal S-DIE ten-root column candidate, with two independently routed faces."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SEED = 'ae042eb26'
BASE = 'physical/ref_tile_specs/s81_bf_native_1015/column_c10_pins/pin_request.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--face', choices=['E', 'W'], required=True)
    args = parser.parse_args()
    import sys
    sys.path.insert(0, str(ROOT/'tools/s81'))
    from bf_direct_pins import groups
    raw = subprocess.check_output(['git', 'show', f'{SEED}:{BASE}'], cwd=ROOT)
    old = json.loads(raw)
    front_path = ROOT/'physical/ref_tile_specs/s81_bf_native_1015/front_five_roots/pin_request.json'
    front = json.loads(front_path.read_text())['pins']
    pinmap = groups(column=True)
    pins = {}
    for port, names in pinmap.items():
        for i, name in enumerate(names):
            p = dict(old['pins'][name])
            if port == 'ci':
                fp = front[f'c0[{i}]']
                assert fp['y'] == front[f'c1[{i}]']['y'] == p['y']
                assert fp['source_pin'][3:] == name
                p.update(face=args.face, x=450.144 if args.face == 'E' else 0.0)
            # Yosys scalarizes single-bit vectors; pin placement must use the
            # actual physical scalar port name rather than a synthetic [0].
            n = f'{port}[{i}]' if len(names) > 1 else port
            p.update(source_pin=name, w=.192 if p['layer'] == 'M4' else .024,
                     h=.024 if p['layer'] == 'M4' else .192)
            pins[n] = p
    for i in range(9):
        pins[f'leaf_ck[{i}]'] = dict(face='N', layer='M5', x=round(43.212+43.2*i, 6),
                                      y=198.72, w=.024, h=.192, source_pin=f'leaf_clk[{i}]')
    if args.face=='W':
        for pin in pins.values():
            if pin['face'] in 'NS':pin['x']=round(450.144-pin['x'],6)
    assert len(pins) == 851
    for n, p in pins.items():
        for m, q in pins.items():
            if n >= m or (p['face'], p['layer']) != (q['face'], q['layer']):
                continue
            axis = 'x' if p['face'] in 'NS' else 'y'
            assert abs(p[axis]-q[axis]) >= .096-1e-6, (n, m)
    source = ['rtl/dsrom_sys/s81_die_bind/dsfd_bf_col_roots.sv',
              'rtl/v41rom/ot_v41_bf_col_roots.sv', 'rtl/v41rom/ot_v41_bf16_lanes3_roots.sv',
              'rtl/v41rom/ot_v41_bf_lane4.sv', 'rtl/v41rom/ot_v41_bf_reduce.sv',
              'rtl/v41rom/ot_v41_bf_fp4_leaves.sv', 'rtl/v41rom/ot_v41_bf_segment_leaf.sv']
    if args.face=='W':source[0]='rtl/dsrom_sys/s81_die_bind/dsfd_bf_col_roots_w.sv'
    record = dict(schema='opentallas.s81.bf_column_ten_root.v1',
                  status='GRANTED_INDEPENDENT_CANDIDATE_NOT_PHYSICALLY_QUALIFIED',
                  top='dsfd_bf_col_roots_w' if args.face=='W' else 'dsfd_bf_col_roots', outline_um=[450.144, 198.72], face=args.face,
                  orientation='R0; W requires its own actual view, no mirrored view inheritance',
                  source_sha256={n:digest(ROOT/n) for n in source},
                  seed_proposal=dict(commit=SEED,path=BASE,sha256=hashlib.sha256(raw).hexdigest()),
                  front_request_sha256=digest(front_path), pins=pins,
                  changes=dict(ci_seam_bits=776, seam_y_mismatches=0, reset_face='S',
                               south_outputs=64, south_output_pitch_um=1.152,
                               added_north_clock_pins=9, total_clock_roots=10,
                               payload_cycles_added=0, relocated_input_edges=1,
                               RTL_register_bits_added=50),
                  grant=dict(owner='S-DIE',record='2026-10-16 direct message to BF views helper',
                             scope='Independent candidate within existing outline; no adoption into848parents',
                             conditions=['exact ci776 front order/stretch', 'no added N clock/S pin collisions',
                                         'actual per-root R/phi-R and full parent die clock ABI',
                                         'source-bound exact+mutant, TT setup/FF hold/DRC0 and native gates',
                                         'current all-incident field/N-output/clock/PG proof before adoption']),
                  geometric_cut=dict(seam=776/(194.16/.048),south=64/(72.576/.048),limit=.60,
                                     scope='Track arithmetic only; actual obstruction/PG/access/congestion still required'),
                  physical_qualification=False)
    out=ROOT/f'physical/ref_tile_specs/s81_bf_native_1015/column_ten_roots_{args.face.lower()}'
    out.mkdir(parents=True,exist_ok=True)
    (out/'pin_request.json').write_text(json.dumps(record,indent=2)+'\n')
    lines=['# Literal independent ten-root column candidate, no inherited physical view.']
    for n,p in pins.items():
        lines.append(f"place_pin -pin_name {{{n}}} -layer {p['layer']} -location {{{p['x']} {p['y']}}} -pin_size {{{p['w']} {p['h']}}} -force_to_die_boundary")
    (out/'pins.tcl').write_text('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(13,6))
    ax.add_patch(Rectangle((0,0),450.144,198.72,fill=False))
    # Literal macro kit homes; all other space is available to the ten real
    # clock cones. This is a geometry request, not a placement density image.
    mx=43.2 if args.face=='E' else 280.8
    orient='R0' if args.face=='E' else 'MY'
    for i,y in enumerate([25.92,112.32]):
        ax.add_patch(Rectangle((mx,y),125.304,62.952,color='lightgray'))
        ax.text(mx+62.652,y+31.476,f'actual ROM{i}\n4096 x274\n{orient} aligned-v2',ha='center',va='center')
    for n,p in pins.items():
        if n=='ck' or n.startswith('leaf_ck['):
            ax.scatter(p['x'],p['y'],c='red',s=18)
            ax.annotate(n,(p['x'],p['y']),xytext=(p['x'],p['y']+6),ha='center',fontsize=7)
        elif n=='rs':
            ax.scatter(p['x'],p['y'],c='red',s=18);ax.text(p['x'],8,'reset',ha='center',fontsize=8)
        else:
            ax.scatter(p['x'],p['y'],c='tab:blue' if n.startswith('ci[') else 'tab:green',s=2)
    ax.text(310 if args.face=='E' else 145,103,'Ten real same-PLL clock roots\nflat actual source; no hard-child substitutes\nphysical placement/CTS/native proof PENDING',ha='center',va='center')
    ax.set(xlim=(-8,460),ylim=(-12,222),xlabel='um',ylabel='um',
           title=f'Independent R0 {args.face}-facing BF column request: 851 literal signal/clock pins\n450.144 x198.72; zero payload cycles; source {record["source_sha256"][source[1]][:12]}')
    ax.set_aspect('equal');fig.tight_layout();fig.savefig(out/'connected_pin_plan.png',dpi=140);plt.close(fig)
    print(json.dumps(dict(face=args.face,pins=len(pins),source_sha256=record['source_sha256'])))


if __name__ == '__main__':
    main()
