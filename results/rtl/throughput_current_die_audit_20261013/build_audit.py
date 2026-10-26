import json,pathlib,re,subprocess,hashlib,collections,datetime
repo=pathlib.Path(__file__).resolve().parents[3]
rows=[r for r in json.load(open(repo/'results/rtl/throughput_current_die_audit_20261013/registry_snapshot.json'))['rows'] if r.get('die_used') and r['category'].startswith('closed') and r['target'] in ['Qwen ROM','DeepSeek ROM','HBM accelerator']]
budget=json.load(open(repo/'results/arch/throughput_budget_20261010/budget.json'));out=[]
def git(*args):
 p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True);return p.stdout.strip() if p.returncode==0 else None
names={n for r in rows for n in [r['element'],*r.get('variants',[])]}
pat='^\\s*module\\s+('+'|'.join(re.escape(n)for n in names)+')\\b'
s=subprocess.run(['rg','-l',pat,'rtl','physical','--glob','*.sv','--glob','*.v'],cwd=repo,text=True,capture_output=True).stdout.splitlines()
mods=collections.defaultdict(list)
for f in s:
 text=(repo/f).read_text(errors='replace')
 for m in re.finditer(pat,text,re.M):mods[m[1]].append(f)
for r in rows:
 name=r['element']; aliases=[name,*r.get('variants',[])]; modulepaths=sorted({f for n in aliases for f in mods[n]}); b=budget.get('elements',{}).get(name); j=pathlib.Path.home()/'.local/state/closure_loop/jobs'/(r['best']['job']+'.json');d=json.loads(j.read_text()) if j.exists() else {};commit=d.get('commit_full') or r['best']['source_commit']
 item={'element':name,'target':r['target'],'closed_job':r['best']['job'],'routed_commit':commit,'registry_status':(b or {}).get('status','NO_BUDGET_ROW'),'registry_ratio':(b or {}).get('ratio'),'source_module_candidates':modulepaths,'production_records':[],'bench_checks':{k:{'expect':v.get('expect'),'rc':v.get('rc'),'ok':v.get('ok'),'tail':v.get('tail','')} for k,v in d.get('benches',{}).items()},'job_source':d.get('spec',{}).get('source')}
 refs=[]
 for op in (b or {}).get('ops',[]):
  refs.extend(re.findall(r'results/[A-Za-z0-9_./-]+\.json',op.get('src','')))
 for ref in sorted(set(refs)):
  p=repo/ref;record={'path':ref,'exists':p.exists()}
  if p.exists():
   rd=json.loads(p.read_text());record['record_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();pin=rd.get('source_commit') or rd.get('source',{}).get('commit') if isinstance(rd.get('source',{}),dict) else rd.get('source_commit');record['source_pin_field']=pin
   pins=re.findall(r'\b[0-9a-f]{9,40}\b',str(pin));record['source_pin_candidates']=pins;comparisons=[]
   for f in modulepaths:
    # Closure source overlays are intentional snapshots; compare their module blob when present.
    overlay=re.findall(r'physical/ref_tile/[A-Za-z0-9_./-]+/src',json.dumps(d.get('spec',{})))
    rf=f
    for ov in overlay:
     if git('rev-parse',commit+':'+ov+'/'+f):rf=ov+'/'+f;break
    for pcommit in pins:
     a=git('rev-parse',commit+':'+rf);bb=git('rev-parse',pcommit+':'+f)
     comparisons.append({'module':f,'routed_path':rf,'bench_commit':pcommit,'routed_blob':a,'bench_blob':bb,'same_module_bytes':bool(a and bb and a==bb)})
   record['module_blob_comparison']=comparisons
   record['evidence_status']='SAME_MODULE_BYTES' if any(x['same_module_bytes']for x in comparisons) else 'MODULE_VERSION_DIFFERS' if comparisons and any(x['routed_blob'] and x['bench_blob']for x in comparisons) else 'SOURCE_EQUIVALENCE_UNPROVEN'
  item['production_records'].append(record)
 if not b:item['audit_status']='UNRESOLVED_NO_PUBLISHED_SPECIFICATION'
 elif not refs:item['audit_status']='REGISTRY_RULE_WITHOUT_DIRECT_PRODUCTION_RECORD'
 else:item['audit_status']='PRODUCTION_SOURCE_EQUIVALENCE_REQUIRES_REVIEW' if any(x.get('evidence_status')!='SAME_MODULE_BYTES'for x in item['production_records']) else 'DIRECT_RECORD_MODULE_BYTES_MATCH'
 contract={'Qwen ROM':'qwen_rom','DeepSeek ROM':'s81','HBM accelerator':'r25gq'}[r['target']]
 cd=json.loads((repo/('results/arch/hier_contract_1011/'+contract+'.json')).read_text()); matches=[{'name':s.get('name'),'cell':s.get('cell'),'parent':s.get('parent'),'kind':s.get('kind')}for s in cd['slots']if s.get('kind')!='die' and s.get('cell')in aliases]
 item['current_main_contract']={'path':'results/arch/hier_contract_1011/'+contract+'.json','version':cd['version'],'matching_slots':matches,'membership_status':'DIRECT_SLOT_CELL_OR_VARIANT_MATCH' if matches else 'REQUIRES_DESCENDANT_OR_LIVE_DIE_MANIFEST_PROOF'}
 # Current job benches explicitly run full KV production exactness + the poisoning mutant.
 kv=d.get('benches',{}).get('bench_hubt_layer_exact',{});neg=d.get('benches',{}).get('bench_hubt_layer_pbmut',{})
 if kv.get('ok') and neg.get('ok'):
  try:
   kd=json.loads(kv['tail'].strip());cyc=max(kd['step'][x]for x in ['8192_normal','8192_peaky','8191_mixed']);item['current_job_production_evidence']={'cycles':cyc,'immutable_published_price':1816,'price_source':'results/rtl/tput_map_1011/qwen_kv_die/record.json price.cycles','ratio':cyc/1816,'exact_all':kd['exact_all'],'mutant_fails':neg['rc']!=0,'source':'same routed job spec source + identical snapshot overlay in bench stages','scope':'KV composed layer ctx8192; component minimum gate already executed by closure job'}
  except (KeyError,ValueError):pass
 out.append(item)
doc={'schema':'opentallas.current_die_throughput_audit.v1','generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'main_snapshot':git('rev-parse','HEAD'),'registry_snapshot_t':json.load(open(repo/'results/rtl/throughput_current_die_audit_20261013/registry_snapshot.json'))['t'],'scope':'Current API die_used=true, category closed*, three target designs only. API die_used flags may themselves be stale; this is an explicit filter, not proof of contract membership. No new pricing or specification fabricated. Same module bytes alone do not prove dependency equivalence.','published_budget_sha256':hashlib.sha256((repo/'results/arch/throughput_budget_20261010/budget.json').read_bytes()).hexdigest(),'summary':dict(collections.Counter(x['audit_status']for x in out)),'rows':out}
p=repo/'results/rtl/throughput_current_die_audit_20261013/audit.json';p.write_text(json.dumps(doc,indent=2)+'\n');print(len(out),doc['summary']);print('current production job records',[x['element']for x in out if x.get('current_job_production_evidence')]);print('source differences',[(x['element'],r['path'])for x in out for r in x['production_records']if r.get('evidence_status')=='MODULE_VERSION_DIFFERS'])
