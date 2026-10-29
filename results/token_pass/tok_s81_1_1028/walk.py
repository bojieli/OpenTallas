import sys, json, collections, importlib.util
sys.path.insert(0,'tree/tools/s81_dv/tokfunc')
spec=importlib.util.spec_from_file_location('B','tree/tools/s81_dv/tokfunc/compose_tok_ds.py'); B=importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
C=B.C
for wl in ('ar','mtp'):
    dag=json.loads(C.DAGS[wl].read_text())
    crit=[n for n in dag['nodes'] if n.get('critical')]
    raw=sum(float(n['cycles']) for n in crit)
    print(wl,'tau',json.loads(C.BASE.read_text())['workloads'][wl].get('tau'),'DAG raw crit sum',round(raw,1),'totals',dag['totals']['cycles'])
    seq=[('none',dict(lanes=False,release=False,offchip=False)),('+lanes',dict(lanes=True,release=False,offchip=False)),
         ('+release',dict(lanes=True,release=True,offchip=False)),('+offchip(full)',dict(lanes=True,release=True,offchip=True))]
    prev=None
    for name,o in seq:
        o['regrade']=False
        r=B.compose(wl,o)
        ex=sum(e['cycles'] for e in r['extra'])
        fixed_nodes=r['fixed']-ex
        print(f"  {name:16s} T={r['T']:.1f} fixed={r['fixed']:.1f} solved={r['solved']:.1f} nodes={fixed_nodes:.1f} extra={ex:.1f}" + (f" dT={r['T']-prev:.1f}" if prev else ''))
        prev=r['T']
        if name=='none':
            # node override delta vs raw DAG, by class
            by=collections.Counter(); byk=collections.Counter()
            for n in dag['nodes']:
                if n.get('critical'):
                    by[n.get('cls')]+=r['cyc'][n['id']]-float(n['cycles'])
                    for x in r['comps'][n['id']]: byk[x['k']]+=x['c']
            print('   node delta vs DAG by cls',{k:round(v,1) for k,v in by.most_common()})
            ext=collections.Counter()
            for e in r['extra']:
                key=e['slot'].split('.',1)[-1] if e['slot'].startswith('L') else e['slot']
                ext[(e['kind'],key[:40])]+=e['cycles']
            for k,v in sorted(ext.items(),key=lambda kv:-abs(kv[1]))[:25]: print('   extra',k,round(v,1))
        if name=='+offchip(full)':
            print('   log',{k:(dict(v) if isinstance(v,collections.Counter) else v) for k,v in r['log'].items() if k not in('components','layers')})
