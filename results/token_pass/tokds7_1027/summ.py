import json,sys,glob,os,collections
out={}
for d in sys.argv[1:]:
    for p in sorted(glob.glob(d+'/prog_*_su')):
        L=os.path.basename(p)[5:-3]; key=os.path.basename(d)+':'+L
        try: low=json.load(open(p+'/lowering.json'))
        except Exception as e: out[key]={'error':str(e)}; continue
        ops=low.get('ops') or low.get('lowering') or low
        if isinstance(ops,dict) and 'ops' in ops: ops=ops['ops']
        st=collections.Counter(); gaps=[]
        items = ops.items() if isinstance(ops,dict) else [(o.get('op') or o.get('id'),o) for o in ops]
        for k,o in items:
            if not isinstance(o,dict): continue
            s=o.get('status'); st[s]+=1
            if s=='GAP': gaps.append(o.get('op',k))
        r={'counts':dict(st),'gaps':gaps}
        try:
            s=json.load(open(p+'/schedule.json')); r['price']=s.get('price'); r['crit_ops']=sum(1 for o in s['ops'] if o.get('critical'))
        except Exception as e: r['sched_err']=str(e)[:100]
        out[key]=r
print(json.dumps(out,indent=1))
