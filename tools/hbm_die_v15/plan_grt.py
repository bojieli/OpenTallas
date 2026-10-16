#!/usr/bin/env python3
"""Die-level global route of a v15 floorplan candidate on block abstracts with its planned pins (H-DIE 2026-10-15).

    plan_grt.py --pins PINS.json --placement P.json --die W H --tech TECH.lef --out CASE_DIR [--k 16]

Same model as the historical HBM die GRT (tools/hbm_accel_die_fp.py case b, grt27): k-bit bundled nets on the k-scaled
ASAP7 track tech (TECH.lef from that case), every block a CLASS BLOCK macro with OBS M1..M5 (blocks are M5-capped; die
routes use M2..M9 over channels and M6..M9 over blocks), the same layer adjustments (M4/M5 0.5, M6/M7 0.05, M8/M9 0.2256
PG share), 12 congestion iterations.  One bundle pin per k bits of every planned link end (GLOBAL-FP pin plan: face,
offset, span), both ends of a link joined by the same bundle net.  The result is the die-level routability of the
PLAN (pins planned, bodies abstract): overflow must be 0 before real views are composed; it is not view timing.
Writes CASE_DIR/{tech.lef, elements.lef, die.v, run.tcl, manifest.json}; run with run_case.sh (ORFS asap7lock).
"""
import argparse, json, math, shutil
from collections import defaultdict
from pathlib import Path

LAYER = dict(N='M5', S='M5', E='M4', W='M4')
PITCH = dict(M4=0.768, M5=0.768)
DEPTH = 3.072


def snap(v, p):
    return round(math.floor(v / p) * p + p / 2, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pins', required=True); ap.add_argument('--placement', required=True)
    ap.add_argument('--die', nargs=2, type=float, required=True); ap.add_argument('--tech', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--k', type=int, default=16)
    ap.add_argument('--obs-high', action='append', default=[], help='PREFIX:L1,L2 also blocks layers L1,L2 over every block whose name starts with PREFIX (e.g. sm_:M8,M9 = a cluster M8/M9 grant)')
    a = ap.parse_args()
    D = json.load(open(a.pins)); P = json.load(open(a.placement))
    W, H = a.die
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    shutil.copy(a.tech, out / 'tech.lef')
    blocks = D['blocks']
    # bundle pins per (block, link)
    pins = defaultdict(list)          # block -> [(pin name, layer, rect)]
    ends = defaultdict(dict)          # link -> {block: [pin names]}
    for b, v in blocks.items():
        w, h = P[b]['w'], P[b]['h']
        for f, fx in v['faces'].items():
            L = w if f in 'NS' else h
            lay = LAYER[f]; pt = 2 * PITCH[lay]
            used = set()
            for p in sorted(fx['pins'], key=lambda p: p['offset_um']):
                nb = max(1, math.ceil(p['bits'] / a.k))
                step = max(pt, p['span_um'] / nb)
                o = p['offset_um']
                names = []
                for i in range(nb):
                    pos = snap(min(max(o + step * i + step / 2, 1.0), L - 1.0), PITCH[lay])
                    while pos in used and pos < L - 1.0:
                        pos = round(pos + PITCH[lay], 3)
                    k0 = pos
                    while pos in used and pos > 1.0:          # wrapped: search downward
                        pos = round(pos - PITCH[lay], 3)
                    if pos in used:
                        raise SystemExit(f'face full: {b} {f} ({p["link"]})')
                    used.add(pos)
                    hw = 0.192
                    if f == 'N':
                        r = (pos - hw, h - DEPTH, pos + hw, h)
                    elif f == 'S':
                        r = (pos - hw, 0, pos + hw, DEPTH)
                    elif f == 'E':
                        r = (w - DEPTH, pos - hw, w, pos + hw)
                    else:
                        r = (0, pos - hw, DEPTH, pos + hw)
                    nm = f'p{len(pins[b])}'
                    pins[b].append((nm, lay, r))
                    names.append(nm)
                ends[p['link']][b] = names
    # LEF
    L = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    for b in blocks:
        w, h = P[b]['w'], P[b]['h']
        L += [f'MACRO M_{b}', '  CLASS BLOCK ;', f'  FOREIGN M_{b} 0 0 ;', f'  SIZE {w:.3f} BY {h:.3f} ;', '  SYMMETRY X Y ;']
        for nm, lay, r in pins[b]:
            L += [f'  PIN {nm}', '    DIRECTION INOUT ;', '    USE SIGNAL ;', '    PORT', f'      LAYER {lay} ;',
                  f'        RECT {r[0]:.3f} {r[1]:.3f} {r[2]:.3f} {r[3]:.3f} ;', '    END', f'  END {nm}']
        hi = [l for spec in a.obs_high for pre, ls in [spec.split(':')] if b.startswith(pre) for l in ls.split(',')]
        L += ['  OBS'] + [x for m in ('M1', 'M2', 'M3', 'M4', 'M5', *hi) for x in (f'    LAYER {m} ;', f'      RECT 0 0 {w:.3f} {h:.3f} ;')] + ['  END', f'END M_{b}']
    L.append('END LIBRARY')
    (out / 'elements.lef').write_text('\n'.join(L) + '\n')
    # netlist
    conn = defaultdict(list)
    nets, dangling = [], []
    for link, e in ends.items():
        if len(e) != 2:
            dangling.append(link); continue
        (b1, n1), (b2, n2) = e.items()
        for i in range(max(len(n1), len(n2))):
            net = f'n{len(nets)}'
            nets.append(net)
            conn[b1].append((n1[min(i, len(n1) - 1)], net)); conn[b2].append((n2[min(i, len(n2) - 1)], net))
    V = ['module hbm_plan_die ();'] + [f'  wire {n};' for n in nets]
    for b in blocks:
        cs = ', '.join(f'.{p}({n})' for p, n in conn[b])
        V.append(f'  M_{b} {b} ({cs});')
    V.append('endmodule')
    (out / 'die.v').write_text('\n'.join(V) + '\n')
    # tcl
    T = ['read_lef /work/tech.lef', 'read_lef /work/elements.lef', 'read_verilog /work/die.v', 'link_design hbm_plan_die',
         f'initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site bsite']
    for m, (o, p) in dict(M1=(0.144, 0.576), M2=(0.144, 0.617), M3=(0.144, 0.576), M4=(0.192, 0.768), M5=(0.192, 0.768),
                          M6=(0.256, 1.024), M7=(0.256, 1.024), M8=(1.856, 1.280), M9=(1.856, 1.280)).items():
        T.append(f'make_tracks {m} -x_offset {o} -x_pitch {p} -y_offset {o} -y_pitch {p}')
    for b in blocks:
        T.append(f'place_inst -name {b} -location {{{P[b]["x"]:.3f} {P[b]["y"]:.3f}}} -orientation R0 -status FIRM')
    for m, adj in (('M2', 1.0), ('M3', 1.0), ('M4', 0.5), ('M5', 0.5), ('M6', 0.05), ('M7', 0.05), ('M8', 0.2256), ('M9', 0.2256)):
        T.append(f'set_global_routing_layer_adjustment {m} {adj:.4f}')
    T += ['set_routing_layers -signal M2-M9', 'set t0 [clock seconds]',
          'global_route -verbose -allow_congestion -congestion_iterations 12 -congestion_report_file /work/grt_congestion.rpt',
          'puts "OT_TIME grt_s=[expr {[clock seconds]-$t0}]"',
          'report_wire_length -net * -global_route -file /work/wirelength.csv']
    (out / 'run.tcl').write_text('\n'.join(T) + '\n')
    man = dict(k=a.k, blocks=len(blocks), bundle_nets=len(nets), pins=sum(len(v) for v in pins.values()),
               dangling_links=dangling, die_um=[W, H], pins_file=a.pins, placement=a.placement)
    (out / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps(man)[:600])


if __name__ == '__main__':
    main()
