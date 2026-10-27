import json,pathlib,subprocess,hashlib,gzip
W=pathlib.Path('/srv/opentallas-scratch2/claude/wt/codex-pv-pass2-0830');O=W/'results/codex_pv_wide_slice_1027';D=O/'input/pd';(D/'cores').mkdir(parents=True,exist_ok=True);SHA='64b502e407';base='physical/die_plan/qwen_kvsys';read=lambda p:subprocess.check_output(['git','show',f'{SHA}:{p}'],cwd=W)
b=read(base+'/die_plan.json');P=json.loads(b);assert 'ot_qwen_tp8_pv_join_t' not in P['clock']['mesh']['core_islands'];(O/'input/source_plan.json.gz').write_bytes(gzip.compress(b,mtime=0))
for t in P['partition_types'].values():t['hard_cores']=[h for h in t.get('hard_cores',[]) if h['module']=='ot_qwen_tp8_pv_join_t']
(D/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n')
for n in ['pv_join_pins_event27.json','pv_join_pins_fMX_event27.json','pv_join_pins_fR180_event27.json']:(D/'cores'/n).write_bytes(read(base+'/cores/'+n))
(O/'input/current_census.json').write_text(json.dumps(dict(modules={},source_commit=SHA,rule='PV-only projection: canonical plan.clock.mesh.core_islands has no PV join entry; all160 cells are resited outside joins,0pushdowns'),indent=1)+'\n')
(O/'input/mesh.json').write_bytes(read('results/codex_kv_event27/pv_clock_build/mesh.json'))
cmd=['python3',str(W/'tools/die_plan/kv_core_slice.py'),str(D),'--plan','die_plan.json','--census',str(O/'input/current_census.json'),'--mesh',str(O/'input/mesh.json'),'--out',str(O/'derived')];r=subprocess.run(cmd,cwd=W,capture_output=True,text=True);(O/'derive.log').write_text(r.stdout+r.stderr);print(r.returncode,r.stdout[-1200:],r.stderr[-500:])
