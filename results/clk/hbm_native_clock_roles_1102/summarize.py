from pathlib import Path
import collections,csv,json
r=Path(__file__).resolve().parent;profiles=json.load(open(r/'profiles.json'))['profiles'];progress=json.load(open(r/'progress.json'));summary=[]
for i,p in enumerate(profiles):
 rowsfile=r/str(i)/'roots.tsv'
 if not rowsfile.exists():
  summary.append(dict(view=p['view'],status='NO_ACTUAL_SYNTH_ODB',declared_clock_inputs=len(p['clock_pins']),role_qualified=False));continue
 rows=list(csv.DictReader(open(rowsfile),delimiter='\t'));entry=next(e for e in progress if e['view']==p['view']);rootrows=[x for x in rows if x['kind']=='ROOT'];loads=[x for x in rows if x['kind']=='ITERM'];assert set(x['root']for x in rootrows)==set(p['clock_pins'])
 assert all(x['iotype']=='INPUT'for x in rootrows+loads)
 assert all(x['sigtype']=='CLOCK'for x in loads)
 ff=[x for x in loads if x['master'].startswith('DFF')and x['pin']=='CLK'];macro=[x for x in loads if x['mastertype']=='BLOCK'];assert len(ff)+len(macro)==len(loads)
 counts=dict(collections.Counter(x['net']for x in ff));native=dict(top_module=p['master'],source_odb_sha256=entry['source_odb_sha256'],clock_root_ports=[dict(port=x['root'],net=x['net'],dir=x['iotype'])for x in rootrows],ff_count=len(ff),ff_clock_net_counts=counts,ff_clock_pins=[dict(inst=x['instance'],pin=x['pin'],net=x['net'],master=x['master'])for x in ff],macro_clock_pins=[dict(inst=x['instance'],master=x['master'],pin=x['pin'],net=x['net'])for x in macro])
 (r/str(i)/'native_clock_census.json').write_text(json.dumps(native,indent=2)+'\n')
 roots=[]
 for x in rootrows:
  items=[y for y in loads if y['root']==x['root']];roots.append(dict(port=x['root'],native_net=x['net'],ff_clock_pins=sum(y in ff for y in items),macro_clock_pins=sum(y in macro for y in items),unused=not items))
 summary.append(dict(view=p['view'],status='ACTUAL_SYNTH_ODB_DIRECT_ROOT_ROLES',source_odb=entry['source_odb'],source_odb_sha256=entry['source_odb_sha256'],roots=roots,ff_clock_pins=len(ff),macro_clock_pins=len(macro),role_qualified=True,source_profile_only=True))
(r/'result.json').write_text(json.dumps(dict(scope='exact native saved synth ODB direct root roles; no source adoption or physical timing',profiles=summary,qualified_profiles=2,unqualified_profiles=7,declared_body_join='32 bodies/448 formal clock inputs remains declared-profile scope; no automatic cross-profile role transfer',holds=['Current parent native pin/instance/source event coherent adoption','16 VMS planned4SRAM versus actual3 mismatch','Hardened LEF/typed TT+FF/PG/route/phase/reset/START joins','Seven GEN-only profiles lack saved native synth ODB']),indent=2)+'\n')
print([(x['view'],x.get('ff_clock_pins'),x.get('macro_clock_pins'))for x in summary if x['role_qualified']])
