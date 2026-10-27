#!/usr/bin/env python3
"""KV-P7-V38 10-23: G2 core-channel GRT probe for a partition type with hard cores (read-only diagnostic).

The g2.py partition FT probe models leaf blockages and face-pin ft stations only; it has no hard cores and no core
pins.  This probe checks the v3.7q core channels with OpenROAD GRT: the type outline + plan tracks (g2.py
make_tracks), every hard core as a placement blockage + M1..M5 obstruction (the closed-core LEF OBS form, e.g.
pv_join), and the bound partition netlist's boundary-crossing nets (g2_channels_v37q.endpoints: station chains
passed through, ft slots in->out) with one DFF per net end: at the core pin of that bit (just outside its face), at
the bit's slot in its face window, or at the glue leaf's centroid.  GRT on M2..M7 with layer adjustment ADJ (0.4:
GRT overflow 0 at 0.4 ~ bits / tracks <= 0.6 with the glue logic's own share).
usage: g2_coreprobe_v37q.py PLAN_DIR RTL_DIR type OUT_DIR [--adjust 0.4] [--mem 16] [--run]"""
import argparse
import json
import sys
from pathlib import Path

QD = Path(__file__).resolve().parent
sys.path.insert(0, str(QD))
sys.path.insert(0, str(QD.parents[2] / 'tools/die_plan'))
import g2_channels_v37q as GC   # noqa: E402
import g2                       # noqa: E402
import gen_phys                 # noqa: E402
import schema as S              # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('plan_dir'); ap.add_argument('rtl'); ap.add_argument('type'); ap.add_argument('out')
ap.add_argument('--adjust', type=float, default=0.4); ap.add_argument('--mem', type=int, default=16)
ap.add_argument('--run', action='store_true'); ap.add_argument('--iters', type=int, default=3)
a = ap.parse_args()
pd, out = Path(a.plan_dir), Path(a.out)
out.mkdir(parents=True, exist_ok=True)
raw = json.load(open(pd / 'die_plan.json'))
P = S.Plan(raw)
tn = a.type
t = raw['partition_types'][tn]
w, h = t['outline_um']
_e, _d, gpos, nets = GC.endpoints(P, raw, a.rtl, tn, pd)
m = gen_phys.CORE_MARGIN_UM
cells, wires, place = [], [], []
nn = 0
for pp, gls in nets:
    pts = []
    for q in list(pp) + [gpos[g_] for g_ in gls]:
        q = (round(min(max(q[0], m), w - m - 1.0), 1), round(min(max(q[1], m), h - m - 0.3), 1))
        if q not in pts:
            pts.append(q)
    if len(pts) < 2:
        continue
    n = f'n{nn}'
    nn += 1
    wires.append(n)
    for k, (x, y) in enumerate(pts):
        c = f'f{nn}_{k}'
        cells.append(f'  {g2.FLOP} {c} (.QN({n}));' if k == 0 else f'  {g2.FLOP} {c} (.D({n}));')
        place.append((c, x, y))
v = ['module coreprobe ();'] + [f'  wire {x};' for x in wires] + cells + ['endmodule']
(out / 'probe.v').write_text('\n'.join(v) + '\n')
(out / 'make_tracks.tcl').write_text(gen_phys.make_tracks_tcl(P))
top = P.type_top_layer(tn)
tcl = [f'read_lef {g2.TECH_LEF}', f'read_lef {g2.SC_LEF}', 'read_verilog /work/probe.v', 'link_design coreprobe',
       f'initialize_floorplan -die_area {{0 0 {w:g} {h:g}}} -core_area {{{m:g} {m:g} {w - m:g} {h - m:g}}} '
       '-site asap7sc7p5t', 'source /work/make_tracks.tcl']
for hc in t.get('hard_cores', []):
    dx, dy = hc.get('track_offset_um', [0, 0])
    x0, y0 = hc['origin_um'][0] + dx, hc['origin_um'][1] + dy
    x1, y1 = x0 + hc['outline_um'][0], y0 + hc['outline_um'][1]
    tcl.append(f'create_blockage -region {{{x0:g} {y0:g} {x1:g} {y1:g}}}')
    for L in g2.lrange('M1', 'M5'):
        tcl.append(f'create_obstruction -region {{{x0:g} {y0:g} {x1:g} {y1:g}}} -layer {L}')
for c, x, y in place:
    tcl.append(f'place_inst -name {c} -location {{{x:.3f} {y:.3f}}} -status PLACED')
tcl += ['detailed_placement -max_displacement {400 400}', 'check_placement -verbose']
tcl.append(g2.grt_tail(f'M2-{top}', [(L, a.adjust) for L in g2.lrange('M2', top)]).replace('-congestion_iterations 30', f'-congestion_iterations {a.iters}'))
tcl += ['puts OT_DONE']
(out / 'probe.tcl').write_text('\n'.join(tcl) + '\n')
(out / 'run.sh').write_text(g2.run_sh(a.mem, 8, 'g2core'))
(out / 'run.sh').chmod(0o755)
meta = dict(kind='g2-coreprobe-v37q', type=tn, outline_um=[w, h], nets=nn, flops=len(place),
            hard_cores=len(t.get('hard_cores', [])), adjust=a.adjust, congestion_iterations=a.iters, route_layers=f'M2-{top}', core_obs='M1-M5')
(out / 'probe.json').write_text(json.dumps(meta, indent=1) + '\n')
print(json.dumps(meta))
if a.run:
    print(json.dumps(g2.run_probe(out)))
