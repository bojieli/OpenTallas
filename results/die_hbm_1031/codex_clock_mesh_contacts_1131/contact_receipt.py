from pathlib import Path
import sys,re,json,collections
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-mesh-core-union-1131/tools/die_plan');import die_sta as D
r=Path(__file__).resolve().parent;o=r/'mesh_contact_fixed_r3';nets,stats=D.spef_split(o/'route.spef');n=nets['mesh_contact'];adj=collections.defaultdict(set)
for a,b,res in n.res:adj[a].add(b);adj[b].add(a)
seen={'mesh_contact'};todo=['mesh_contact']
for a in todo:
 for b in adj[a]:
  if b not in seen:seen.add(b);todo.append(b)
required=['mesh_contact','M0_11:Y','M0_12:Y'];missing=[p for p in required if p not in seen];assert not missing,missing
log=(o/'route.log').read_text();drc=int(re.findall(r'Number of violations = (\d+)',log)[-1]);assert drc==0
d=(o/'route.def').read_text();clock_def=re.search(r'(?ms)^\s*- ck_mesh\b.*?;',d)[0];vias={v:len(re.findall(r'\b'+v+r'\b',clock_def)) for v in ['VIA12','VIA23','VIA34','VIA45','VIA56','VIA67','VIA78','VIA89']};assert all(vias.values()),vias
receipt=dict(verdict='LOCAL_PHYSICAL_MESH_CONTACT_PASS',scope='Two actual BUFx24 Y pins through actual M1-to-M9 via stairs to full retained local mesh conductor; one same ck_mesh net. Not whole-mesh/native-core/current-tap timing closure.',drc=drc,regular_mesh_wire=True,clock_special_shapes_removed=True,resistor_connected_terminals=required,resistor_edges=len(n.res),Rsum_ohm=sum(z[2]for z in n.res),Csum_ff=sum(z[2]for z in n.caps)*1000,physical_via_inventory=vias,implementation='Existing clock_routed.routed_tcl -> explicit_clock_mesh.routed_mesh_tcl; all grid conductor/vias encoded as regular FIXED dbWire. No net alias or invented clock node.',resistance_basis='Shared CR.rcx_tcl opt under probe0.04 width credit; values qualify this connectivity probe, not whole mesh timing.',failures=[dict(attempt='v1 narrow/wide',cause='setSpecial takes no arguments; failure before P&R',handled='queried installed OpenDB API; clearSpecial used'),dict(attempt='v2 narrow/wide',cause='Clock remained un-routed (regularwire NULL); test input ports clipped PG VDD by6nm narrow/106nm wide',handled='PG-gap on-track test ports; clear every M.Y special flag; actual route guard retained'),dict(attempt='v3 DRT-contact',cause='Even net+ITerm clearSpecial retained clock SWire and GRT/DRT skipped ck_mesh, regularwire NULL despite DRC0',handled='shared FIXED regular mesh encoder replaces all clock SWires and connects native pins')],G4='BLOCKED actual full mesh under hard-core union + native child clock landings +14/6/ROOT current local taps +START/reset/storage +real views')
(r/'mesh_contact_receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
