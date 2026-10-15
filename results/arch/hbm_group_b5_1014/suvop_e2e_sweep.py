import sys,json
sys.path.insert(0,'tools/throughput'); sys.path.insert(0,'tools')
import accepted_cost as A
out={}
for wl in ('ds','qwen'):
    run,count=A.hbm_schedule(wl)
    base=run()
    out[wl]={'base':base,'records':count.get('SU.VOP',0),'loss':{}}
    for r in (1.10,1.183,1.249,1.333,1.5,2.0,2.651,3.0,4.0,5.33):
        c=run('SU.VOP',r)
        out[wl]['loss'][r]=round(100*(1-base/c),3)
    print(wl,json.dumps(out[wl]),flush=True)
json.dump(out,open('/tmp/gb5/suvop_e2e.json','w'),indent=1)
