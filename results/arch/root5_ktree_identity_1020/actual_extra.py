from pathlib import Path
import subprocess,json,hashlib,re,gzip
r=Path.cwd();old=Path('/srv/opentallas-scratch/claude/ref_gate/ot_qkh_ktree_lk_nc32c-20261020-031904/routes/gate/work/orfs');new=Path(str(old).replace('031904','041108'))
rep=json.loads((old/'native_census.json').read_text())
rel='results/asap7/opentallas_ot_qkh_ktree_lk_nc32c_asap7_ref_gate/base/1_2_yosys.v'
raws=[(x/rel).read_bytes() for x in (old,new)]
assert [hashlib.sha256(x).hexdigest() for x in raws]==['6d1d28a1d58ab5088166ffb25084c552ae7810b51ee401801a55fc3434fc7cea','c53dd281eba6a845dff175c6e88876013eb106c5cd3cb6c52053c449f88a2368']
libs=[x['path'] for x in rep['liberty']]
summary=[]
import threading
from concurrent.futures import ThreadPoolExecutor
lock=threading.Lock()
pool=ThreadPoolExecutor(max_workers=4)
futures=[]
def execute(label,raw,expect,side='cand',libpaths=None):
    net=r/(label+'.v');net.write_bytes(raw)
    out=r/(label+'.json')
    args=['python3',f'/audit/{side}/tools/ref_tile/native_census.py','--netlist','/audit/'+net.name,'--top',rep['top'],'--out','/audit/'+out.name]
    for lib in (libs if libpaths is None else libpaths):args+=['--liberty',lib]
    cmd=['docker','run','--rm','-v',str(r)+':/audit','openroad/orfs:latest']+args
    z=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    result=json.loads(out.read_text());admit=result.get('admission',{}).get('status')=='PASS_WITH_SCOPED_WAIVER'
    assert (z.returncode==0)==expect,(label,z.stdout,result)
    assert admit==expect,(label,result)
    if expect:
        assert result['status']=='FAIL' and result['max_dynamic_loads']==34 and len(result['violations'])==15 and not result['role_errors']
        assert result['netlist']['positive_buf_identity_sha256']=='24f05e9e4e08b9590b5ce8d6e1d2b00958c5fb0fea739cd7934f7da46b5dc228'
    row=dict(label=label,rc=z.returncode,raw_status=result['status'],max=result.get('max_dynamic_loads'),nodes=len(result.get('violations',[])),admission=result.get('admission'),role_errors=result.get('role_errors'),netlist=result.get('netlist'))
    summary.append(row);print(json.dumps(row),flush=True)
    with lock:
        (r/'actual_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
def run(*args,**kwargs):
    futures.append(pool.submit(execute,*args,**kwargs))
x=raws[1]
needle=b'  AND2x2_ASAP7_75t_R _3433_ ('
assert needle in x
run('nonbuf_function',x.replace(needle,b'  NAND2x2_ASAP7_75t_R _3433_ (',1),False)
for future in futures: future.result()
pool.shutdown()
print('ACTUAL_NONBUF_FUNCTION_NEGATIVE_PASS',flush=True)
