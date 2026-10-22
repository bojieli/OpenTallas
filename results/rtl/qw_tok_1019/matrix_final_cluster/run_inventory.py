"""Four isolated exact-binary replay workers after the measured full-GU pilot."""
import concurrent.futures, json, pathlib, subprocess, sys, time
R=pathlib.Path('/srv/opentallas-scratch/claude/refill-1225/QWLAYER')
W=R/'matrix_final_cluster_1019_v2'
driver=R/'matrix_final_cluster_driver_1019_v3/replay.py'
cases=[dict(nu=n,layer=l,mode=m,mutant='positive') for n in (1,4) for l in (0,1) for m in ('qkv','gu') if (n,l,m)!=(1,0,'gu')]
cases += [dict(nu=n,layer=0,mode='gu',mutant=m) for n in (1,4) for m in ('sbase1','kc2','nearshift','predrain')]
cases += [dict(nu=n,layer=1,mode='qkv',mutant='scale_before_tree') for n in (1,4)]
def run(c):
    name=f"nu{c['nu']}_L{c['layer']}_{c['mode']}_{c['mutant']}"
    p=W/(name+'.runner.log'); start=time.time()
    with p.open('x') as out:
        rc=subprocess.run([sys.executable,str(driver),'run','--nu',str(c['nu']),'--layer',str(c['layer']),'--mode',c['mode'],'--mutant',c['mutant']],stdout=out,stderr=subprocess.STDOUT).returncode
    print('INVENTORY_CASE',name,'rc',rc,flush=True)
    return dict(**c,rc=rc,wall_seconds=time.time()-start)
if __name__=='__main__':
    assert not (W/'inventory_results.json').exists()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,cases))
    (W/'inventory_results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('INVENTORY_TERMINAL',len(rows),'classification pending',flush=True)
