import subprocess,pathlib,json,hashlib,sys
r=pathlib.Path(__file__).resolve().parent; o=r.parent/'r17_minimum';o.mkdir(exist_ok=True)
m=json.loads((r/'source_manifest.json').read_text())
for p,h in m['files'].items(): assert hashlib.sha256((r/p).read_bytes()).hexdigest()==h,p
cases=[('pair_pos',['bash','tools/qwen_kv_die/attn_rv_1019/rv_pair_bench.sh',str(o/'pair_pos'),'0','0 1 2 3 4 5 6 7 8 9 10','RS=1','SD=213'],0,'KVS_RVPAIR_ALL PASS'),('reset_pos',['bash','tools/qwen_kv_die/attn_rv_1019/cal_rst_bench.sh',str(o/'reset_pos'),'0'],0,'CALRST_ALL PASS'),('reset_mut8',['bash','tools/qwen_kv_die/attn_rv_1019/cal_rst_bench.sh',str(o/'reset_mut8'),'8'],1,'CALRST_ALL FAIL'),('pair_mut2',['bash','tools/qwen_kv_die/attn_rv_1019/rv_pair_bench.sh',str(o/'pair_mut2'),'2','0 1 2 3 4 5 6 7 8 9 10','RS=1','SD=213'],1,'KVS_RVPAIR_ALL FAIL')]
import os
env=dict(os.environ,RVB='r17'); results=[]
for name,cmd,rc,mark in cases:
 with (o/(name+'.log')).open('w') as f: p=subprocess.run(cmd,cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT)
 text=(o/(name+'.log')).read_text(); good=p.returncode==rc and mark in text and 'FAIL build' not in text
 results.append({'name':name,'rc':p.returncode,'expected':rc,'runtime_marker':mark,'ok':good}); print(results[-1],flush=True)
(o/'record.json').write_text(json.dumps({'identity':m,'cases':results},indent=2)+'\n')
sys.exit(0 if all(c['ok'] for c in results) else 1)
