"""Exact actual mapped macro/read-FF constraints on a disabled geometry proposal.

The fold LEF is an OLD reference, so this is conditional planning geometry,
never a current-view/source qualification. No netlist/flow mutation.
"""
import collections,gzip,json,re,sys
from pathlib import Path
B=Path(__file__).resolve().parent
g=json.load(gzip.open(sys.argv[1]));r=json.load(open(sys.argv[2]));ld=Path(sys.argv[3]);out=Path(sys.argv[4]);out.mkdir(exist_ok=True)
policy=json.load(open(sys.argv[5])) if len(sys.argv)>5 else None
hs={h['inst']:h for h in r['macros']};lib={}
for f in ld.glob('*.lef'):
    text=f.read_text();mod=re.search(r'\nMACRO (\S+)',text)[1];wh=list(map(float,re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text).groups()));ps={}
    for m in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n',text,re.S):
        if m[1]in ['VDD','VSS']:continue
        rects=re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',m[2]);assert len(rects)==1,m[1]
        a,b,c,d=map(float,rects[0]);ps[m[1]]=[(a+c)/2,(b+d)/2]
    lib[mod]=(wh,ps)
def pin(i,p,b):
    n=g['macro_nodes'][str(i)];h=hs[n['name']];wh,ps=lib[n['type']];key=p if len(n['connections'][p])==1 and p in ps else f'{p}[{b}]';x,y=ps[key];w,z=wh;ori=h.get('orient','R0')
    if policy and n['type']=='ot_coll_fold_slice'and key in policy['proposed_local_pin_centers_um']:
        x,y=policy['proposed_local_pin_centers_um'][key]
    if policy and n['type']=='ot_coll_fold_slice'and p=='src'and 'src_linear' in policy:
        x=policy['src_linear']['x_um'];y=policy['src_linear']['first_y_um']+b*policy['src_linear']['pitch_um']
    if ori in ['MY','R180']:x=w-x
    if ori in ['MX','R180']:y=z-y
    if ori=='R90':x,y=z-y,x
    if ori=='R270':x,y=y,w-x
    return [round(x+h['origin_um'][0],6),round(y+h['origin_um'][1],6)]
def ep(i,p,b):return dict(node=i,instance=g['macro_nodes'][str(i)]['name'],port=p,bit=b,xy_um=pin(i,p,b))
def man(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
terms=g['terms'];constraints=collections.defaultdict(dict);direct=[];unqualified_clock_reset=[]
def add(ff,e):constraints[str(ff)][(e['node'],e['port'],e['bit'])]=e
for row in g['macro_to_first_capture']:
    for tid in row['sources']:
        t=terms[tid]
        if t[0]=='MACRO':add(row['capture_ff'],ep(t[1],t[2],t[3]))
for row in g['macro_input_sources']:
    if row['port']in ['clk','rst_n','VDD','VSS']:
        unqualified_clock_reset.append(dict(macro=row['macro'],port=row['port'],bit=row['bit']));continue
    dst=ep(row['macro'],row['port'],row['bit'])
    for tid in row['sources']:
        t=terms[tid]
        if t[0]=='FF':add(t[1],dst)
        if t[0]=='MACRO':
            src=ep(t[1],t[2],t[3]);d=man(src['xy_um'],dst['xy_um']);direct.append(dict(source=src,destination=dst,distance_um=round(d,6),pass_405=d<=405+1e-7))
failed=[];feasible=0;constraints_count=0
for ff,es in constraints.items():
    es=list(es.values());constraints_count+=len(es)
    us=[e['xy_um'][0]+e['xy_um'][1]for e in es];vs=[e['xy_um'][0]-e['xy_um'][1]for e in es]
    u=[max(us)-405,min(us)+405];v=[max(vs)-405,min(vs)+405]
    if u[0]>u[1]+1e-7 or v[0]>v[1]+1e-7:
        axis=us if max(us)-min(us)>=max(vs)-min(vs)else vs;ai=axis.index(min(axis));bi=axis.index(max(axis))
        failed.append(dict(ff=ff,name=g['ff_nodes'][ff]['name'],macro_endpoint_count=len(es),u_interval=u,v_interval=v,witness=[es[ai],es[bi]],minimum_oneFF_radius_um=round(max(max(us)-min(us),max(vs)-min(vs))/2,6)))
    else:feasible+=1
dc=collections.Counter((x['source']['instance'],x['destination']['instance'])for x in direct if not x['pass_405'])
fc=collections.Counter(re.sub(r'\[[^]]*\]','[]',x['name']).split('$_')[0]for x in failed)
summary=dict(status='ACTUAL_SOURCE_JOIN_CONDITIONAL_GEOMETRY_NOT_RELEASED',actual_macro_count=len(g['macro_nodes']),actual_standard_FF_count=g['standard_FF_count'],direct_macro_bit_edges=len(direct),failed_direct_macro_bit_edges=sum(not x['pass_405']for x in direct),max_direct_macro_distance_um=max(x['distance_um']for x in direct),FFs_with_macro_constraints=len(constraints),macro_endpoint_constraints=constraints_count,unconstrained_diamond_feasible_FFs=feasible,empty_macro_diamond_FFs=len(failed),unqualified_clock_reset_pin_rows=len(unqualified_clock_reset),failed_direct_macro_pairs=[dict(source=a,destination=b,bit_edges=n)for(a,b),n in dc.most_common()],failed_FF_families=fc.most_common(),scope='Actual mapped source dependencies joined to actual selectedSRAM/referenceoldfoldpins with explicit orientation. No new FF/edge. Empty diamonds prove this placement cannot host those existingFFs within405 of every immediate macro endpoint. Nonempty diamonds do not prove macro-free cellsites, FF-to-FF/control reach, current-view identity, clocks/reset/PG, source equivalence or release.')
(out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
if policy:
    summary['new_view_pin_policy']=policy
    summary['scope']+=' FOLD PIN POLICY IS A PLANNED NEW-VIEW OVERRIDE, NOT ACTUAL QUALIFIED PINS. All eight use one same proposed view; old rectangle is footprint only.'
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(out/'MACRO_READER_CONSTRAINTS.json.gz','wt')as f:json.dump(dict(summary=summary,direct_macro_edges=direct,empty_diamonds=failed,FF_macro_constraints={k:list(v.values())for k,v in constraints.items()},unqualified_clock_reset=unqualified_clock_reset),f,separators=(',',':'))
print(json.dumps({k:v for k,v in summary.items()if k not in ['failed_direct_macro_pairs','failed_FF_families','scope']}));print('FFFAIL',fc.most_common(8));print('DIRECTFAIL',dc.most_common(5))
