from pathlib import Path
import json,re,sys,collections
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-mesh-contacts-1101/tools/die_plan');import die_sta as D
r=Path(__file__).resolve().parent
results={}
for form in ['near','east']:
 o=r/f'slid_mesh_contact_{form}';nets,_=D.spef_split(o/'route.spef');n=nets['mesh_contact'];adj=collections.defaultdict(set)
 for a,b,v in n.res:adj[a].add(b);adj[b].add(a)
 seen={'mesh_contact'};todo=list(seen)
 for a in todo:
  for b in adj[a]:
   if b not in seen:seen.add(b);todo.append(b)
 required=['mesh_contact','M0_0:Y','M0_1:Y'];assert all(p in seen for p in required)
 log=(o/'route.log').read_text();counts=list(map(int,re.findall(r'Number of violations = (\d+)',log)));assert counts[-1]==0
 results[form]=dict(final_drc=counts[-1],iteration_counts=counts,resistor_connected_terminals=required,resistor_edges=len(n.res),Rsum_ohm=sum(z[2]for z in n.res),Csum_ff=sum(z[2]for z in n.caps)*1000)
receipt=dict(verdict='ACTUAL_DISPLACED_MESH_DRIVER_CONTACT_PASS',forms=results,scope='Actual current C11E union-sited M0_0/M0_1 driver Y to original mesh strap anchors via explicit M8/M9 PG-gap doglegs, shared regular FIXED encoder. Hard cores/PG preserved. No diagonal phantom conductor.',G4='BLOCKED nativeK/current station local taps/whole current feed+START+reset/storage/real views',release_qualified=False,initial_marker='Each variant had one M9 spacing marker at iter0; normal DRT repaired it by iter1 without any source/geometry/rule waiver.',resistance_basis='Shared probe RCX options retained; physical contact qualification, not whole analog mesh phase/signoff.')
(r/'slid_contact_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
