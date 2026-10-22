import sys,json,pathlib,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]/'tools'))
import textbook_lint as T
p=pathlib.Path(sys.argv[1])
g,top=T.flatten(T.parse_verilog(p.read_text()),'ot_hbm_accel_smh_xs'); a=T.build(g,None); ck,clock_sinks=T.clock_nets(g,a)
allrows=[];strap=[]; cats={}
for x,d in a['driver'].items():
 if x<=3 or x in ck or (d[0]>=0 and a['kind'][d[0]] in ('buf','tie')):continue
 n,f,e=T.bufinv_fanout(g,a,x,ck);lab=T.net_label(g,a,x)
 row=dict(net=lab,loads=n,flops=f,example=str(e));allrows.append(row)
 cat=next((s for s in ('g_s1[','g_s2[','g_sm[','a1p[','a2p[') if s in lab),None)
 if cat: cats[cat]=max(cats.get(cat,0),n)
 if any(s in lab for s in ('g_s1[','g_s2[','g_sm[','a1p[','a2p[')):strap.append(row)
r=dict(category_max=cats,top=top,netlist_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),strap_roots=len(strap),max_strap_fanout=max(x['loads'] for x in strap),strap_top=sorted(strap,key=lambda x:x['loads'],reverse=True)[:24],all_signal_top=sorted(allrows,key=lambda x:x['loads'],reverse=True)[:24])
r['clock_roots']=[dict(source=list(k),**v) for k,v in clock_sinks.items()]
print(json.dumps(r,indent=2))


assert r['max_strap_fanout']<=32
