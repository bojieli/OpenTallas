#!/usr/bin/env python3
"""QC-IMPORT-1 fresh native source target (step 1 of the native provider import).

Same recipe as Codex baseline26/landing_candidate/reframe_target119.py (target119_h800), with three changes:
  - plan = QC plan of record plan_qc_import1.json (h800 native + START provider/reset_source + form (a) tap growth);
  - abstracts regenerated with the COMBINED island windows (44,590 clock bodies + 48,259 provider bodies, actual body
    sizes, main die_trial.island_windows) and the native reset outputs (reset_infra=True);
  - route.v carries landing infra + native reset wavefront nets (route_netlist(landing_infra, reset_infra)).
The frozen trial26 clock (clock/) and the die PG capacity reservations (grt/obs.tcl) are copied unchanged.
Static target only: no route, timing, START phase or provider import qualification.
usage: fresh_target.py --plan P --base TARGET119_H800 --sites CLOCK_SITES PROVIDER_SITES --tools T --out OUT"""
import argparse, hashlib, json, shutil, sys
from collections import defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--plan', type=Path, required=True)
ap.add_argument('--base', type=Path, required=True)
ap.add_argument('--sites', type=Path, nargs='+', required=True)
ap.add_argument('--tools', type=Path, required=True)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
sys.path.insert(0, str(a.tools))
import schema as S, gen_phys as GP, die_trial as DT, landing_route as LR
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan = a.plan.resolve()
p = S.Plan(S.load(plan), plan)
a.out.mkdir(parents=True, exist_ok=False)
sites = DT.load_island_sites([str(s) for s in a.sites])
win, recs = DT.island_windows(p, sites)
blocked = [r['source'] for r in recs for h in r['parts'] if h['in_core']]
outside = [r['source'] for r in recs if not r['parts']]
if blocked or outside:
    raise SystemExit(f'HOLD: island in hard core {len(blocked)} / outside partitions {len(outside)}')
mods = DT.standin_module_names(p)
(a.out / 'abstracts').mkdir()
for tn in sorted(p.types):
    text, _ = DT.abstract_lef(p, tn, islands=win.get(tn), module_name=mods[tn], landing_infra=True, reset_infra=True)
    (a.out / 'abstracts' / f'{mods[tn]}.lef').write_text(text)
shutil.copytree(a.base / 'clock', a.out / 'clock')
shutil.copytree(a.base / 'grt', a.out / 'grt')
bits = {}
for tn in p.types:
    w = defaultdict(int)
    for bus, bit, *_ in GP.type_pins(p, tn):
        w[bus] = max(w[bus], bit + 1)
    bits[tn] = dict(w)
text, nft = DT.route_netlist(p, bits, landing_infra=True, reset_infra=True)
(a.out / 'grt/route.v').write_text(text)
lefs = sorted(x.name for x in (a.out / 'abstracts').glob('*.lef'))
ftf = sorted({t.get('ft_track_frac', .25) for t in p.types.values()})
ca = p.layer_budget.get('cut_avail', {'M8': .6, 'M9': .6})
adjust = [(ln, round(1 - ftf[0], 3)) for ln in ('M4', 'M5', 'M6', 'M7')] + \
         [(ln, round(1 - ca.get(ln, .6), 3)) for ln in ('M8', 'M9')]
(a.out / 'grt/grt.tcl').write_text(DT.grt_tcl(p, a.out / 'grt', .72, lefs, [], adjust))
shutil.copyfile(a.base / 'grt/obs.tcl', a.out / 'grt/obs.tcl')
network = LR.network(p)
(a.out / 'grt/landing_provisional_nets.txt').write_text(''.join(n + '\n' for n in network['provisional']))
kit = json.loads((a.base / 'kit.json').read_text())
kit.update(source_clock_plan_sha256=kit['plan_sha256'], plan=str(plan), plan_sha256=sha(plan),
           types=len(p.types), parts=len(p.parts), ports=len(p.ports), static_target_only=True,
           source_clock=str(a.base / 'clock'), source_clock_tree_sha256=sha(a.base / 'clock/tree.json'),
           island_sites={str(s): sha(s) for s in a.sites},
           island_windows=dict(types=len(win), windows=sum(map(len, win.values())), sites=len(sites)),
           reset_infra=True,
           qualification='QC-IMPORT-1 fresh native source target: NO route, timing, START phase or provider import '
                         'qualification; prewire graft + provider all-cell import still required',
           landing_infra=dict(edges=network['edges'], nets=len(network['wires']),
                              provisional=len(network['provisional'])))
(a.out / 'kit.json').write_text(json.dumps(kit, indent=1) + '\n')
print('QC_IMPORT1_FRESH_TARGET', len(p.types), 'types', len(p.parts), 'parts', kit['island_windows'],
      network['edges'], 'edges', len(network['provisional']), 'provisional', nft, 'ft')
