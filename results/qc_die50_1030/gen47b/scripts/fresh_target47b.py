#!/usr/bin/env python3
"""DIE-QC-50/gen47b fresh plan_qc49 native target = DIE-QC-49 emit_native_target_v2 (target49) + the COMBINED
island windows (gen47 clock bodies + gen47 provider bodies) cut into every partition abstract (main
die_trial.abstract_lef islands=, 12.2a1 type-union; hard-core OBS kept). route.v regenerated (must equal target49);
grt.tcl/obs.tcl/tracks.tcl copied unchanged from target49 (same abstract file names).
usage: fresh_target47b.py --tools T --plan P --windows combined_island_windows.json --reference REF49 --out OUT"""
from pathlib import Path
from collections import defaultdict
import argparse, json, sys, shutil, re, hashlib
p = argparse.ArgumentParser()
for k in ('tools', 'plan', 'windows', 'reference', 'out'): p.add_argument('--' + k, required=True)
a = p.parse_args(); sys.path.insert(0, a.tools)
import schema as S, die_trial as D, gen_phys as G
sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
path = Path(a.plan); P = S.Plan(S.load(path), path); out = Path(a.out)
(out / 'abstracts').mkdir(parents=True, exist_ok=False); (out / 'grt').mkdir()
win = {t: [tuple(r) for r in rr] for t, rr in json.load(open(a.windows))['windows'].items()}
smod = D.standin_module_names(P); bits = {}; stats = {}
for tn, t in sorted(P.types.items()):
    text, st = D.abstract_lef(P, tn, islands=win.get(tn), module_name=smod[tn], landing_infra=True, reset_infra=True)
    (out / 'abstracts' / (smod[tn] + '.lef')).write_text(text); stats[tn] = st
    b = defaultdict(int)
    for bus, bit, *_ in G.type_pins(P, tn): b[bus] = max(b[bus], bit + 1)
    bits[tn] = dict(b)
text, ft = D.route_netlist(P, bits, landing_infra=True, reset_infra=True); (out / 'grt/route.v').write_text(text)
ref = Path(a.reference)
for name in ['grt.tcl', 'obs.tcl', 'tracks.tcl']: shutil.copy2(ref / 'grt' / name, out / 'grt' / name)
same_route = sha(out / 'grt/route.v') == sha(ref / 'grt/route.v')
missing = [n for n in re.findall(r'read_lef /work/abstracts/(\S+)', (out / 'grt/grt.tcl').read_text()) if not (out / 'abstracts' / n).exists()]
if missing: raise SystemExit('HOLD abstracts missing for grt.tcl: %s' % missing[:5])
receipt = dict(schema='opentallas.native_target_infra.v1', plan=str(path), plan_sha256=sha(path), windows=a.windows,
               windows_sha256=sha(a.windows), island_types=len(win), island_windows=sum(map(len, win.values())),
               abstracts_with_islands=sum(1 for s in stats.values() if s.get('island_windows')),
               route_v_equals_target49=same_route, types=len(stats), parts=len(P.parts), landing_infra=True,
               reset_infra=True, route=False, physical_timing=False,
               source='main die_trial.abstract_lef(islands=combined)/route_netlist; target49 grt.tcl/obs.tcl/tracks.tcl')
(out / 'emit_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n'); print(json.dumps(receipt))
