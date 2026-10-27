import json,sys
p=json.load(open(sys.argv[1]))
bad=0;tot=0
for tn,t in p['partition_types'].items():
    hc={h['inst'] for h in t.get('hard_cores',[]) or []}
    for tap in t.get('clock',{}).get('taps',[]) or []:
        if tap.get('kind')!='core': continue
        tot+=1
        if 'core_group' in tap: continue
        nm=tap['name']
        if not any(nm==i or nm.startswith(i+'.') for i in hc):
            bad+=1; print('STALE',tn,nm)
    # cores lacking taps
    if t.get('clock',{}).get('core_taps')=='early':
        names=[x['name'] for x in t['clock'].get('taps',[]) if x.get('kind')=='core']
        miss=[i for i in hc if not any(n==i or n.startswith(i+'.') for n in names)]
        if miss: print('NOTAP',tn,len(miss),miss[:3])
print('core_taps',tot,'stale',bad)
