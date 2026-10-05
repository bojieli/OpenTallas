import sys,pathlib,subprocess,json,hashlib,time,os,struct,resource
root=pathlib.Path('/tmp/opentallas-field-source-gate-f06-20261003'); out=pathlib.Path(__file__).parent
snap=pathlib.Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277')
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
sys.path.insert(0,str(root/'tools'));import v41_field_rt_gate as g
assert subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)==''
source={str(p.relative_to(root)):sha(p) for p in g.SOURCES}
cmd=[sys.executable,str(root/'tools/v41_field_rt_gate.py'),'--snapshot',str(snap),'--workdir',str(out/'work'),'--jobs','1','--threads','1']
headroom={'meminfo':pathlib.Path('/proc/meminfo').read_text(),'loadavg':pathlib.Path('/proc/loadavg').read_text(),'disk_free':__import__('shutil').disk_usage(out).free}
rec={'schema':'opentallas.field_source_gate_independent_replay.v1','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'command':cmd,'source_sha256':source,'pid':os.getpid(),'headroom':headroom,'source_unmodified_before':True,'tool':{'path':g.VERILATOR,'sha256':sha(g.VERILATOR),'version':subprocess.check_output([g.VERILATOR,'--version'],text=True).strip()},'parameters':{'np':16,'regions':4,'nbf':4,'phw':4,'vaw':16,'jobs':1,'threads':1},'checkpoint_revision':snap.name,'index_sha256':sha(snap/'model.safetensors.index.json')}
(out/'start.json').write_text(json.dumps(rec,indent=2)+'\n');t=time.monotonic()
with (out/'gate.log').open('w') as log:
 p=subprocess.Popen(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT);rec['child_pid']=p.pid;(out/'start.json').write_text(json.dumps(rec,indent=2)+'\n');rc=p.wait()
rec.update(returncode=rc,wall_seconds=time.monotonic()-t,source_unmodified_after=source=={str(p.relative_to(root)):sha(p) for p in g.SOURCES},max_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
trace=(out/'work/verilate_flat.log').read_text() if (out/'work/verilate_flat.log').exists() else ''
rec['classification']='FRONTEND_MISSING_MODULE' if '%Error-MODMISSING' in trace and 'ot_hdc_cg' in trace else 'OTHER'
rec['functional_comparison_reached']=(out/'work/simulate.log').exists();rec['artifacts']={str(p.relative_to(out)):sha(p) for p in [out/'gate.log',out/'work/verilate_flat.log',out/'work/verilate_flat.rss',out/'work/ops.txt'] if p.exists()}
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({'classification':rec['classification'],'returncode':rc,'child_pid':p.pid,'wall_seconds':rec['wall_seconds']}))
