"""Read back scoped native term contacts; no distributed PG/IR claim."""
import odb,json,collections
D=odb.dbDatabase.create();odb.read_db(D,'native_pg/connected.odb');B=D.getChip().getBlock();P=json.load(open('native_pg/selected_plan.json'));wanted=collections.defaultdict(set)
for c in P['contacts']:wanted[c['net']].add(tuple(c['xy_dbu']))
seen=collections.defaultdict(set)
for n in B.getNets():
 if n.getName() not in wanted:continue
 for sw in n.getSWires():
  for sb in sw.getWires():
   if not sb.isVia():continue
   v=sb.getTechVia()
   if v and v.getName()=='VIA78' and tuple(sb.getViaXY()) in wanted[n.getName()]:seen[n.getName()].add(tuple(sb.getViaXY()))
bad=[]
for c in P['contacts']:
 i=B.findInst(c['inst']);it=i.findITerm(c['pin']);net=it.getNet()
 if not net or net.getName()!=c['net'] or tuple(c['xy_dbu']) not in seen[c['net']]:bad.append([c['inst'],c['pin'],c['net'],c['xy_dbu']])
r=dict(verdict='PASS' if not bad else 'FAIL',scope='SCOPED_NATIVE_TERM_CONNECTIVITY_ONLY; original198fragment misses retained; no IR/fullgrid/clockphase qualification',terms=len(P['contacts']),actual_native_contacts=sum(len(x) for x in seen.values()),bad=bad)
json.dump(r,open('native_pg/contact_readback.json','w'),indent=1);print(json.dumps(r));assert not bad
