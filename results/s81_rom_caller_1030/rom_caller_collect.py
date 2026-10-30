from pathlib import Path
import json,re,hashlib
r=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030/iqf_current_bind');P=json.load(open(r/'src/physical/die_plan/s81/plan_iqf_reset_1030.json'));records=[]
for tn,t in P['partition_types'].items():
 if not any(x in tn for x in ['col_h9_r1','col_h9_r2','col_h10_r0_p4']):continue
 p=r/'out/rtl'/(t['module']+'.sv')
 if not p.exists():continue
 s=p.read_text();rows=[]
 for m in re.finditer(r'ot_v41_rom_elem_q_qxpq_w10_gb\s*#\((.*?)\)\s+(\w+)\s*\(',s,re.S):
  params=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[1]));decl=[]
  for k,v in params.items():
   if v.startswith('P_'):decl += [l.strip() for l in s.splitlines() if re.search(r'\b'+re.escape(v)+r'\b\s*=',l)]
  before=s[:m.start()].splitlines()[-1].strip();rows.append(dict(instance=m[2],source_comment=before,params=params,bound_param_declarations=decl,header=m[0]))
 records.append(dict(plan_type=tn,bound_path=str(p),bound_sha256=hashlib.sha256(s.encode()).hexdigest(),partition_instances=[x.get('id',x.get('name')) for x in P['partitions'] if x['type']==tn],ROM_callers=rows))
o=r/'rom_caller_actual.json';o.write_text(json.dumps(dict(schema='opentallas.rom.actual_caller_params.v1',source='current successful IQF reset-only bind; frozen native event3 source',records=records,note='Actual emitted parent caller values, not defaults; source-only no physical/nativeROM-cohort transfer credit.'),indent=1)+'\n')
print('types',len(records),'callers',sum(len(x['ROM_callers']) for x in records),'CGR',sorted({z['params'].get('CGR') for x in records for z in x['ROM_callers']}))
for x in records:print(x['plan_type'],len(x['ROM_callers']),x['ROM_callers'][0]['params'] if x['ROM_callers'] else {})
