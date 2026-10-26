from pathlib import Path
import ast,subprocess,os,json,hashlib
B=Path.cwd();r=json.loads((B/'receipt.json').read_text());(B/'initial_causal_expectation_failure.json').write_text(json.dumps(r,indent=2)+'\n')
node=ast.parse((B/'run_pair.py').read_text());causal=next(x.value.value for x in node.body if isinstance(x,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='causal'for t in x.targets))
causal=causal.replace("yes('all selected nonGRP static bindings emitter',lambda:all(bs['qkd_kvs_'+k]['file']==S.RTL_FILE for k in ['ctl','attn','emb','pc','pc_h']))", """overrides={S.FACE_LAND_TILES[t]['master']:S.face_land_rtl(t) for t in S.FACE_LAND_SEL}
 yes('non-face-landed static bindings emitter',lambda:all(bs['qkd_kvs_'+k]['file']==S.RTL_FILE for k in ['ctl','attn','emb','pc','pc_h'] if 'qkd_kvs_'+k not in overrides))
 yes('exact face-land wrappers preserved',lambda:all(bs[m]['file']==f and bs[m]['module']==m+'_fl' for m,f in overrides.items() if m in bs))""")
old=B.parent/'codex-k-die-1340/paired_main14c';env=dict(os.environ,PYTHONPATH=str(old/'runtime902')+':'+str(B/'final/tools'),PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
causals={}
for flag in ['0','1']:
 ce={k:v for k,v in env.items()if not k.startswith('OT_KV_')}
 if flag=='1':
  ep=subprocess.check_output(['bash','-c','set -a;source "$1";env -0','bash',str(B.parent/'codex-kdie-main92-captured/successor/kv_flags.env')])
  ce.update({k.decode():v.decode()for pair in ep.split(b'\0')if pair for k,v in [pair.split(b'=',1)]if k.startswith(b'OT_KV_')})
 ce['SELECTED']=flag;p=subprocess.run(['/usr/bin/python3','-c',causal],cwd=B/'final',env=ce,capture_output=True,text=True);causals[flag]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
for v,hs in r['source_sha256'].items():
 for n,h in hs.items():assert hashlib.sha256((B/v/'tools/qwen_kv_die'/n).read_bytes()).hexdigest()==h
r['causals']=causals;r['prior_harness_failure']='all nonGRP emitter assertion wrongly included selected real face-land overrides; exact wrappers now required preserved; source unchanged and fullpair NEW0 retained'
r['verdict']='PASS_NEW0'if not r['new_failure_occurrences']and all(x['returncode']==0 for x in causals.values())else'FAIL'
(B/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(causals,indent=2),flush=True);print(r['verdict'],flush=True);raise SystemExit(0 if r['verdict']=='PASS_NEW0'else 1)
