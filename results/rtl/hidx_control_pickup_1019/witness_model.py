import collections,gzip,json,pathlib,math
r=pathlib.Path(__file__).resolve().parent
x=json.load(gzip.open(r/'transparent_diagnostic.json.gz','rt'));m=json.loads((r/'census/ot_hbm_idx_topk_link_static_p/mapped.json').read_text())['modules'][x['top']]
names=collections.defaultdict(list)
for name,n in m['netnames'].items():
 for b in n['bits']:
  if isinstance(b,int) and len(names[b])<8:names[b].append(name)
roots=[z for z in x['drivers'] if not z['transparent'] and z['loads']>32 and not z['driver'].startswith('literal:')]
rows=[]
for z in roots:
 rows.append({k:z[k] for k in ('driver','net','role','loads','endpoint_roles','sink_classes')}|{'netnames':names[z['net']],'minimum_32load_owners':math.ceil(z['loads']/32)})
rows.sort(key=lambda z:z['loads'],reverse=True)
o={'diagnostic_only':True,'strict_native_verdict':'REFUSED unsupported bus','source_commit':'5af00a1ab','mapped_sha256':x['provenance']['mapped_sha256'],'nontransparent_violations':len(rows),'violations_by_role':dict(collections.Counter(z['role'] for z in rows)),'worst_nontransparent':rows[:40],'all_nontransparent_violations':rows,'input_boundary_unregistered_data_count':sum(not z['registered_data_endpoints_only'] and bool(z['endpoint_roles'].get('data',0)) for z in x['input_registration'])}
(r/'control_ownership_model.json').write_text(json.dumps(o,indent=2)+'\n')
print(json.dumps({k:v for k,v in o.items() if k!='all_nontransparent_violations'},indent=2))
