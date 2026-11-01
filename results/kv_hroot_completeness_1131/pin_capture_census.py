import re,json
from pathlib import Path
import geom_rules as G
r=Path(__file__).resolve().parent;d=G.Design('/srv/opentallas-scratch/claude/wt/codex-kv-physical-1101/results/kv_hroot_reloc_1131_A4_actual.tsv');out=[]; lr=G.land_ring_captures(d,json.loads((r/"land_slots.json").read_text()),json.loads((r/"face_guard.json").read_text()))
for p in d.pins:
 if p['sig'] in ('POWER','GROUND','CLOCK') or G.CLOCK_PIN_RE.search(p['name']) or p['name'].startswith('strap_'):continue
 ni=d.pin_net.get(p['k']);found=set();seen=set();front=[ni] if ni is not None else []
 while front:
  n=front.pop()
  if n in seen:continue
  seen.add(n)
  refs=[d.nets[n][1]] if p['io']=='OUTPUT' else d.nets[n][2]
  for z in refs:
   if not z or z[0]!='i' or z[2]:continue
   i=z[1]
   if d.kind(i)=='S':found.add(i)
   elif d.kind(i)=='B':
    if p['io']=='OUTPUT':front.extend(n for n,ck in d.cell_in.get(i,[]) if not ck)
    else:front.extend(d.drives.get(i,[]))
  # Every directional first-register branch is retained, not a bus centroid.
 if p['name'] in lr['caps']:found=set(lr['caps'][p['name']])
 row=dict(typed_landing=p['name'] in lr['caps'],pin=p,endpoints=[dict(name=d.cells[i][6],xy=list(G.ctr(d.cells[i])),distance_um=abs(p['x']-G.ctr(d.cells[i])[0])+abs(p['y']-G.ctr(d.cells[i])[1])) for i in found]);out.append(row)
(r/'all_bit_first_capture_census.json').write_text(json.dumps(out,indent=2))
bad=[z for z in out if z['endpoints'] and (max if z['typed_landing'] else min)(e['distance_um'] for e in z['endpoints'])>150]
print('signal pins',len(out),'no pure firstFF',sum(not z['endpoints'] for z in out),'hardbad',len(bad));print(json.dumps(sorted(bad,key=lambda z:-(max if z['typed_landing'] else min)(e['distance_um'] for e in z['endpoints']))[:12],indent=1))
