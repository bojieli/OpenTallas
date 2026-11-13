"""Re-derive reset_start_raw_exports rows + landing pin source_instance from the solved reset tree.
Rule: an export's source = the raw-role start relay nearest (manhattan) the export pin; pin xy is unchanged.
Usage: rawfix.py REPO IN.json OUT.json [--report]"""
import json,sys,copy
sys.path.insert(0,sys.argv[1]+'/tools/die_plan')
import schema as S, reset_tree as RT
raw=json.load(open(sys.argv[2])); P=S.Plan(raw,sys.argv[2]); out=copy.deepcopy(raw)
def man(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])
for tn,t in sorted(P.types.items()):
    rows=[r for r in t.get('reset_start_raw_exports',[]) if not r.get('existing_port')]
    if not rows: continue
    tree=RT.for_type(P,tn); rel=[r for r in RT.start_relays(tree) if r.get('role') in ('raw','boot','bootstrap_transport')]
    byn={r['name']:r for r in rel}
    T=out['partition_types'][tn]; pins={p['name']:p for p in T['clock']['landing_contract']['pins']}
    for row in T['reset_start_raw_exports']:
        if row.get('existing_port'): continue
        pin=pins[row['port']]; cur=byn.get(row['instance'])
        ok=cur is not None and cur['q']==row['net'] and man(cur['xy'],row['xy_um'])<1e-6 and pin.get('source_instance')==row['instance'] and pin.get('source_copy_from_net',row['net'])==row['net']
        if ok: continue
        best=min(rel,key=lambda r:(man(r['xy'],pin['xy_um']),r['name']))
        d=man(best['xy'],pin['xy_um'])
        print(f"{tn}.{row['port']}: {row['instance']}/{pin.get('source_instance')} -> {best['name']} q={best['q']} xy={[round(v,2) for v in best['xy']]} pin={pin['xy_um']} dist={d:.1f}um")
        row.update(instance=best['name'],net=best['q'],xy_um=list(best['xy'])); pin['source_instance']=best['name']
        if 'source_copy_from_net' in pin: pin['source_copy_from_net']=best['q']
if len(sys.argv)>3 and sys.argv[3]!='--report': json.dump(out,open(sys.argv[3],'w'),indent=1)

# ---- pass 2: clock.landing_local_resets[].raw = nearest wavefront relay at (type release depth - 1) to the copy site xy_um
def lr_pass(out, path):
    P2=S.Plan(out,path)
    for tn,t in sorted(P2.types.items()):
        L=(t.get('clock') or {}).get('landing_local_resets') or []
        if not L: continue
        tree=RT.for_type(P2,tn); want=tree['depth']-1
        cand=[r for r in tree['relays'] if r['depth']==want]
        col='column' in (t.get('reset') or {})
        byq={r['q']:r for r in tree['relays']}
        T=out['partition_types'][tn]['clock']['landing_local_resets']
        old=OLD.get(tn,{}); oldq={r['q']:r for r in old.get('relays',[])}
        for e in T:
            o=oldq.get(e['raw'])
            if o and not col:   # physical identity: same xy and same depth offset from release
                od=old['depth']-o['depth']
                same=[r for r in tree['relays'] if man(r['xy'],o['xy'])<1e-3 and tree['depth']-r['depth']==od]
                if len(same)==1:
                    if same[0]['q']!=e['raw']: print(f"{tn}.lrst_{e['name']}: {e['raw']} -> {same[0]['q']} (same relay, renumbered)"); MAP[0]+=1
                    e['raw']=same[0]['q']; continue
                print(f"{tn}.lrst_{e['name']}: {e['raw']} NO_PHYSICAL_MATCH ({len(same)})"); MAP[1]+=1
            cur=byq.get(e['raw']); best=min(cand,key=lambda r:(man(r['xy'],e['xy_um']),r['name']))
            if cur and cur['depth']==want and (not col or man(cur['xy'],e['xy_um'])<=man(best['xy'],e['xy_um'])+1e-6): continue
            print(f"{tn}.lrst_{e['name']}: {e['raw']}(d{cur and cur['depth']},{cur and round(man(cur['xy'],e['xy_um']),1)}um) -> {best['q']}(d{want},{man(best['xy'],e['xy_um']):.1f}um)")
            e['raw']=best['q']
OLD=json.load(open(__import__('os').environ['OLD_RELAYS'])) if __import__('os').environ.get('OLD_RELAYS') else {}
MAP=[0,0]
lr_pass(out, sys.argv[2])
print('renumbered',MAP[0],'no_match',MAP[1])
if len(sys.argv)>3 and sys.argv[3]!='--report': json.dump(out,open(sys.argv[3],'w'),indent=1)
