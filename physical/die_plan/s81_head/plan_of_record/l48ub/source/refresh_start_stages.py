import json,re,sys,copy
sys.path.insert(0,'tools/die_plan'); sys.path.insert(0,'tools/s81_head')
import schema as S, reset_tree as R
U,O,V=sys.argv[1:4]
plan=S.Plan(S.load(U+'/source_plan.json'),U+'/source_plan.json')
off=json.load(open(O+'/offsets.json')); st=json.load(open(O+'/start_stages_v3.json')); sv=open(V+'/start_stages.sv').read()
cache={}
def relays(tn):
    if tn not in cache:
        t=R.for_type(plan,tn); raw=R.start_relays(t) if t.get('start') else t['relays']
        cache[tn]=(t,{r['name']:r for r in raw})
    return cache[tn]
rows={tn:{r['port']:r for r in t.get('reset_start_raw_exports',[])} for tn,t in plan.types.items()}
def src(pn,port):
    tn=plan.parts[pn]['type']; r=rows[tn][port]; t,rl=relays(tn); q=rl[r['instance']]
    return dict(part=pn,type=tn,instance=r['instance'],net=r['net'],xy_um=list(plan.to_die(pn,q['xy'])),local_xy_um=list(q['xy']),
      raw_release=off['parts'][pn]['release']-R.release_clocks(t)+R.entry_stages(t)+q['depth'],port=port)
dist=lambda a,b:sum(abs(x-y) for x,y in zip(a,b))
name=lambda c:re.sub(r'\W','_','wrst_'+c['part']+'__'+c['port'])
new=copy.deepcopy(st); used={(v['part'],v['port']) for v in st['reset_ports'].values()}
pool=[src(p,k) for p,k in sorted(used)]
ports={}; rebind=[]; changed=0
for s in new['stages']:
    old=s['reset_source']; c=src(old['part'],old['port']); d=dist(s['clock_pin_xy_um'],c['xy_um'])
    if c['instance']!=old['instance'] or c['local_xy_um']!=old['local_xy_um']: changed+=1
    if d>405:
        b=min(pool,key=lambda q:(dist(s['clock_pin_xy_um'],q['xy_um']),q['part'],q['port']))
        nd=dist(s['clock_pin_xy_um'],b['xy_um'])
        pat=r'(\.clk\('+re.escape(s['clock_port'])+r'\), \.rst_raw_n\()'+re.escape(s['reset_port'])+r'(\))'
        sv,n=re.subn(pat,lambda m:m[1]+name(b)+m[2],sv); assert n==1,s['id']
        rebind.append(dict(stage=s['id'],old=s['reset_port'],old_hop=round(d,2),new=name(b),new_hop=round(nd,2),new_instance=b['instance'],raw_release=b['raw_release'],old_release=c['raw_release']))
        c,d=b,nd; s['reset_port']=name(b)
    s['reset_source']=dict(c); s['reset_hop_um']=round(d,4); ports[name(c)]=dict(c)
new['reset_ports']=ports
rootid=next(s['id'] for s in new['stages'] if s['root']); r0=next(s for s in new['stages'] if s['id']==rootid)['reset_source']['raw_release']
span=max(s['reset_source']['raw_release']-r0 for s in new['stages'])
hops=[s['reset_hop_um'] for s in new['stages']]
assert span+4<=new['root_settle'],span
new['root_settle_guard']['raw_relative_span']=span
new['reset_refresh']=dict(by='DIE-HEAD-62 11-04',plan='l48ua f64ad52c1726',scope='reset_source metadata re-read from plan rows; '+str(len(rebind))+' rebind; stage tree, clock ports and geometry unchanged from src25q/head_src_v3',qualification=st['reset_qualification'])
json.dump(new,open(O+'/start_stages.json','w'),indent=1); open(O+'/start_stages.sv','w').write(sv)
gone=sorted(set(st['reset_ports'])-set(ports)); add=sorted(set(ports)-set(st['reset_ports']))
print(json.dumps(dict(changed_sources=changed,rebind=rebind,max_hop=max(hops),over=sum(h>405 for h in hops),span=span,settle=new['root_settle'],ports=len(ports),ports_gone=gone,ports_added=add)))
