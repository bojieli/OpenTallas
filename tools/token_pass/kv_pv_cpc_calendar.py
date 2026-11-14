#!/usr/bin/env python3
"""Join actual landed PV trunk cuts and selected PVFIN output pin cycles.

v2 separates transport before PVFIN from source cycles after its arithmetic.
Only a coherent final bind can emit a bound input contract; --prototype keeps
the exact unresolved bind/context limitations visible and never qualifies it.
"""
import argparse,csv,gzip,hashlib,importlib.util,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PORTS={'out_valid','out_beat','out_epoch','out_data','fault'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 return json.load(gzip.open(p))if str(p).endswith('.gz')else json.loads(Path(p).read_text())
def checked_calendar(c):
 if c.get('first_input_age_cycles_added')!=0 or c.get('arithmetic_cycles_added')!=0:
  raise ValueError('PV calendar must preserve input and arithmetic ages')
 schema=c.get('schema')
 if schema=='opentallas.kv.pv_landed_calendar.v1':
  trunk,pin=c.get('result_cycles_added'),0
 elif schema=='opentallas.kv.pv_landed_calendar.v2':
  trunk,pin=c.get('result_trunk_cycles_added'),c.get('result_pin_cycles_added')
  if type(trunk)is not int or type(pin)is not int or c.get('result_cycles_added')!=trunk+pin:
   raise ValueError('PV v2 component total mismatch')
  components=c.get('source_pin_components')
  if pin!=2 or not isinstance(components,list)or len(components)!=1:
   raise ValueError('unsupported or duplicated PV source pin component')
  x=components[0]
  if x.get('id')!='pvfin-output-pin'or x.get('inst')!='pvfin'or x.get('module')!='qkd_pv_fin_s2x8_pin_i1'or x.get('cycles')!=pin or set(x.get('ports',[]))!=PORTS:
   raise ValueError('PV source pin component contract mismatch')
  for key in ('source_sha256','tsv_sha256','proof_sha256'):
   if not re.fullmatch('[0-9a-f]{64}',x.get(key,'')):raise ValueError('missing PV source identity')
 else:raise ValueError('unknown PV result calendar schema')
 if any(type(x)is not int or x<0 for x in (trunk,pin)):
  raise ValueError('PV result cycles must be nonnegative integers')
 return trunk,pin
def selected_pin_component(pl,ab,repo,proof_root):
 proof_file=proof_root/'results/kv-pvfin-1/pin_stage_1113/impact.json'
 proof=read(proof_file);master=proof['master'];wrapper=proof['asbuilt_fixed_i1_wrapper']
 if proof['total_additional_cycles_vs_original']!=2 or proof['params']!={'ADD_LAT':7,'MUL_LAT':6,'SKEW':1,'MUT':0,'IN_STAGE':1}:
  raise ValueError('unsupported PVFIN source latency/parameter proof')
 selections=[x for x in ab.get('substitute_inst',[])if x.get('inst')=='pvfin']
 if len(selections)!=1 or selections[0].get('module')!=wrapper:raise ValueError('PVFIN selected source mismatch')
 active=[pl['partition_types'][p['type']]for p in pl['partitions']]
 content=[x for t in active for x in t.get('contents',[])if x.get('inst')=='pvfin']
 if len(content)!=1 or content[0].get('module')!=wrapper:raise ValueError('plan PVFIN wrapper mismatch')
 rules=[x for x in ab.get('core_pin_cycles',[])if x.get('inst')=='pvfin']
 if len(rules)!=1 or rules[0].get('module')!=wrapper:raise ValueError('missing/duplicate PVFIN CPC rule')
 rule=rules[0];tsv=Path(rule['tsv']);tsv=tsv if tsv.is_absolute()else repo/tsv
 added={}
 with tsv.open(newline='')as f:
  for row in csv.DictReader(f,delimiter='\t'):
   if row['core']!=rule['core']:continue
   if row['dir']!='out':raise ValueError('PVFIN CPC must describe output pins only')
   for port in row['port_or_bus'].split(','):
    port=port.strip()
    if port in added:raise ValueError('duplicate PVFIN CPC port')
    added[port]=int(row['added_cycles'])
 if set(added)!=PORTS or set(added.values())!={2}:raise ValueError('PVFIN output CPC contract mismatch')
 source_files=list(dict.fromkeys(Path(p)if Path(p).is_absolute()else repo/p for p in ab['files']if Path(p).name==master+'.sv'))
 if len(source_files)!=1:raise ValueError('selected PVFIN source file is ambiguous')
 selected=source_files[0];canonical=proof_root/'rtl/qwen_sys/split_20261014'/selected.name
 if sha(selected)!=sha(canonical):raise ValueError('selected PVFIN source differs from canonical D5 proof source')
 component=dict(id='pvfin-output-pin',inst='pvfin',module=wrapper,cycles=2,ports=sorted(PORTS),
                tsv=str(tsv),tsv_sha256=sha(tsv),source=str(selected),source_sha256=sha(selected),proof=str(proof_file),proof_sha256=sha(proof_file))
 return component
def derive(plan,asbuilt,bind,repo=ROOT,proof_root=ROOT,prototype=False,base_calendar=None,trunk_calendar=None):
 plan,asbuilt,bind,repo,proof_root=map(lambda p:Path(p).resolve(),(plan,asbuilt,bind,repo,proof_root))
 ab=read(asbuilt);pl=read(plan);br=read(bind/'bind_report.json')
 errors=br.get('errors',[])
 if br.get('n_errors')!=len(errors):raise ValueError('incomplete bind error report')
 allowed='PARAM_REGEN kv_pv_col_regen.py: pair image pair_image_txdp.json is stale for this bind:'
 unresolved=[e for e in errors if not e.startswith(allowed)]
 prov=read(bind/'provenance_bind.json')['provenance']
 mismatch=[]
 for key,p in [('plan',plan),('manifest',asbuilt)]:
  q=Path(prov[key]);q=q if q.is_absolute()else repo/q
  if not q.is_file()or sha(q)!=sha(p):mismatch.append(key)
 if not prototype and (unresolved or mismatch):
  raise ValueError('final calendar requires coherent matching bind; errors='+str(unresolved[:3])+' context='+str(mismatch))
 component=selected_pin_component(pl,ab,repo,proof_root)
 if base_calendar is not None:
  prior=read(base_calendar);checked_calendar(prior)
  if prior['schema'].endswith('.v2')or prior.get('source_pin_components'):
   raise ValueError('PVFIN CPC already present: refusing double count')
 bg_file=bind/'bus_groups.json'
 if not bg_file.exists():bg_file=bind/'bus_groups.json.gz'
 bg=read(bg_file)
 # Native trunk producer uses bound_stages; programme prep consumes landed
 # stages. Normalize a private copy to the actual landed data ages.
 for g in bg['landing']:
  for m in g['members']:m['bound_stages']=m['landed_stages']
 producer=repo/'tools/qwen_kv_die/pv_landed_calendar.py'
 spec=importlib.util.spec_from_file_location('native_pv_landed_calendar',producer);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 if trunk_calendar is None:
  trunk=mod.derive(bg)
 else:
  trunk=read(trunk_calendar);_,already_pin=checked_calendar(trunk)
  if already_pin or trunk.get('source_pin_components'):raise ValueError('trunk input already includes source pin cycles')
  ti=trunk.get('input_identity')or{}
  if ti.get('bus_groups_sha256')!=sha(bg_file)or not re.fullmatch('[0-9a-f]{64}',ti.get('producer_sha256','')):
   mismatch.append('trunk_calendar')
   if not prototype:raise ValueError('final trunk calendar must identify the exact coherent bind and producer')
 trunk_extra,_=checked_calendar(trunk)
 if base_calendar is not None:
  old=read(base_calendar);checked_calendar(old)
  if old.get('pairs')!=trunk['pairs']or old.get('result_cycles_added')!=trunk_extra:
   raise ValueError('base trunk calendar is stale for actual landed bind')
 out=dict(trunk,schema='opentallas.kv.pv_landed_calendar.v2',
          kind='PROTOTYPE_NOT_BOUND'if prototype else'BOUND_INPUT_CONTRACT_RUNTIME_PENDING',
          result_cycles_added=trunk_extra+2,result_trunk_cycles_added=trunk_extra,result_pin_cycles_added=2,
          source_pin_components=[component],
          input_identity=dict(plan=str(plan),plan_sha256=sha(plan),asbuilt=str(asbuilt),asbuilt_sha256=sha(asbuilt),
                              bind=str(bind),bus_groups_sha256=sha(bg_file),
                              trunk_producer_sha256=(trunk.get('input_identity')or{}).get('producer_sha256')if trunk_calendar else sha(producer),
                              trunk_calendar=str(trunk_calendar)if trunk_calendar else None,
                              trunk_calendar_sha256=sha(trunk_calendar)if trunk_calendar else None),
          unresolved_bind_errors=unresolved,bind_context_mismatch=mismatch,
          native_programme_qualified=False,physical_qualified=False,
          consumption='Trunk cycles shift published P0/P1 only; pin cycles add to bound fin path and generated F_DLY only. Both preserve arithmetic and first-input ages.')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ('plan','asbuilt','bind','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--repo-root',type=Path,default=ROOT);p.add_argument('--proof-root',type=Path,default=ROOT)
 p.add_argument('--prototype',action='store_true');p.add_argument('--base-calendar',type=Path);p.add_argument('--trunk-calendar',type=Path)
 a=p.parse_args();r=derive(a.plan,a.asbuilt,a.bind,a.repo_root,a.proof_root,a.prototype,a.base_calendar,a.trunk_calendar)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:r[k]for k in ('kind','result_cycles_added','result_trunk_cycles_added','result_pin_cycles_added','bind_context_mismatch')},sort_keys=True))
