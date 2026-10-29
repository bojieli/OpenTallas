import sys, json, collections, importlib.util
spec=importlib.util.spec_from_file_location('B','tree/tools/s81_dv/tokfunc/compose_tok_ds.py'); B=importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
C=B.C
wl=sys.argv[1]
dag=json.loads(C.DAGS[wl].read_text())
r=B.compose(wl,dict(lanes=False,release=False,offchip=False,regrade=False))
by=collections.defaultdict(lambda:[0,0.0,0.0,set()])
for n in dag['nodes']:
    if n.get('critical'):
        k=(n.get('cls'),n.get('op'))
        b=by[k]; b[0]+=1; b[1]+=float(n['cycles']); b[2]+=r['cyc'][n['id']]
        for x in r['comps'][n['id']]: b[3].add(str(x['src'])[:70])
rows=sorted(by.items(),key=lambda kv:-abs(kv[1][2]-kv[1][1]))
for k,(c,o,nw,s) in rows[:30]:
    print(f"{str(k):45s} n={c:3d} dag={o:10.1f} B={nw:10.1f} d={nw-o:+10.1f}  {sorted(s)[:2]}")
# solved path vs crit
print('fixed',r['fixed'],'solved',r['solved'])
ps=set(r['path']); cs=set(r['crit'])
print('path-only nodes', sum(r['cyc'][i] for i in ps-cs), 'crit-only', sum(r['cyc'][i] for i in cs-ps))
