from pathlib import Path
import json,subprocess
B=Path('results/arch/s81_halfclock_reexport_inputs_1020');I=Path('/home/ubuntu/wt/codex-s81-mu6-realctrl-1020/results/arch/s81_mu6_realctrl_1020/native_family_inventory');allrows=json.loads((I/'routed_asset_inventory.json').read_text());found={x['master']:x for h in allrows if h['host']=='ot-agidock128' for x in h['found']}
spec={m:dict(asset=row,abstract=json.loads((I/m/'abstract.json').read_text())) for m,row in found.items()}
script='''from pathlib import Path
import json,hashlib,re
spec=SPEC
out=[]
for master,r in spec.items():
 a=r['abstract']; files={}
 for path in r['asset']['finals']:
  if not path.endswith(('.odb','.v','.spef','.sdc')):continue
  files[path]=None
 for v in a['verdict']['files'].values():files[v['host']]=v['sha256']
 files[a['verdict']['json']]=a['verdict']['sha256']
 files[a['interface_sdc']['path']]=a['interface_sdc']['sha256']
 rows=[]
 for name,expected in files.items():
  p=Path(name);entry=dict(path=name,expected_sha256=expected,exists=p.exists())
  if p.is_file():
   data=p.read_bytes();entry.update(size=len(data),sha256=hashlib.sha256(data).hexdigest(),historical_hash_match=(hashlib.sha256(data).hexdigest()==expected) if expected else None)
   if p.suffix in ['.sdc','.json']:entry['text']=data.decode(errors='replace')
   if p.suffix=='.v':
    text=data.decode();entry['routed_v']=text;entry['kept_inverter_instances']=[dict(cell=m[1],instance=m[2],connections=m[3]) for m in re.finditer(r'(\\w+)\\s+(\\S*ot_dvrly_ckinv\\S*)\\s*\\((.*?)\\);',text,re.S)]
  rows.append(entry)
 out.append(dict(master=master,orfs_dir=r['asset']['path'],files=rows,old_native_OT_WS={k:v['ws'] for k,v in a['corners'].items()},old_verdict_expect=a['verdict']['expect_ps'],old_sdc_sequence=a['sdc_sequence'],old_interface_sdc=a['interface_sdc']))
print(json.dumps(out))
'''.replace('SPEC',repr(spec))
r=subprocess.run(['ssh','-o','BatchMode=yes','ot-agidock128','python3','-'],input=script,text=True,capture_output=True,timeout=40)
(B/'collection_stderr.txt').write_text(r.stderr);assert r.returncode==0,r.stderr
out=json.loads(r.stdout);(B/'six_actual_inputs.json').write_text(json.dumps(out,indent=2));(B/'historical_abstracts.json').write_text(json.dumps(spec,indent=2));
print(json.dumps([dict(master=x['master'],files=len(x['files']),missing=[f['path'] for f in x['files'] if not f['exists']],historical_mismatch=[f['path'] for f in x['files'] if f.get('historical_hash_match') is False],inverter=sum(len(f.get('kept_inverter_instances',[])) for f in x['files'])) for x in out],indent=2))
