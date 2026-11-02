"""Reproduce disabled coupled candidate3 and necessary per-bus geometry price.

Input is the exact frozen candidate9 plan, not current main. This performs no
RTL emission, kit generation, synthesis, P&R, STA, or canonical adoption.
"""
import copy, gzip, json, math, re, sys
from pathlib import Path
B=Path(__file__).resolve().parent;ROOT=next(p for p in B.parents if (p/'tools/die_plan/schema.py').exists())
sys.path.insert(0,str(ROOT/'tools/die_plan'));import schema as S,gen_phys
old=json.loads(Path(sys.argv[1]).read_text());q=json.load(gzip.open(B/'candidate2/DISABLED_PARENT_PLAN_UNRELEASED.json.gz'))
q['partition_types']['coll_ft__cla4a25d77']=copy.deepcopy(old['partition_types']['coll_ft__cla4a25d77'])
for a in q['partitions']:
    if a['name']in ['coll_f1','coll_f2','coll_core','coll_ucie']:
        a['origin_um']=next(z['origin_um']for z in old['partitions']if z['name']==a['name'])
    if a['name']=='coll_f3':a['origin_um']=[777.6,9469.44]
t=q['partition_types']['coll_ftm'];t['outline_um']=[786.24,2021.76]
for a in t['ft_slots']:
    for k,f in [('in_window_um','in_face'),('out_window_um','out_face')]:
        if a[f]in'WE'and k in a:a[k]=[round(z+552.96,6)for z in a[k]]
P=S.Plan(q);pins={(bus,bit):(x,y)for bus,bit,ln,x,y,face in gen_phys.type_pins(P,'coll_ftm')}
src=(B/'frozen_FTm_actual.sv').read_text();rows=[]
for a in old['partition_types']['coll_ftm']['ft_slots']:
    n=a['name'];k=a['stations'];st=re.findall(r'ot_dp_st #\(\.W\((\d+)\)\) (u_ft_'+n+r'_o_\d+) .*',src);assert len(st)==k,(n,len(st),k)
    band=old['partition_types']['coll_ftm']['clock']['landing_contract']['bands'][n+'_i']['rect_um'][:]
    if a['in_face']=='N':band=[band[0],band[1]+552.96,band[2],band[3]+552.96]
    def distance(x,y):return max(band[0]-x,0,x-band[2])+max(band[1]-y,0,y-band[3])
    # Closest point in the WHOLE band is a conservative lower bound for a real
    # source flop. Giving lastFF150um pin reach makes this bound optimistic.
    ds=[max(0,distance(*pt)-150)for(bus,bit),pt in pins.items()if bus==n+'_o'];assert ds
    lb=max(ds);need=max(1,math.ceil(lb/405-1e-9));chosen=max(k,need)
    if a['in_face']in'NS'and a['out_face']in'NS':chosen=max(5,chosen)
    next(z for z in t['ft_slots']if z['name']==n)['stations']=chosen
    rows.append(dict(bus=n,direction=a['in_face']+'->'+a['out_face'],width=a['width'],actual_postring_FFs=k,actual_source_instances=[z[1]for z in st],translated_landing_band_um=band,outputFF_pin_budget_um=150,necessary_distance_um=round(lb,6),necessary_postring_hops=need,proposed_postring_FFs=chosen,proposed_mission_data_edge_delta=chosen-k,clock_cohort='local clk after fclk_in_'+n+'_i; source CAk/boot/clock/reset unqualified'))
c=B/'candidate3';c.mkdir(exist_ok=True)
with gzip.open(c/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz','wt')as f:json.dump(q,f,separators=(',',':'))
(c/'REPRODUCED_FTm_LOWERBOUNDS.json').write_text(json.dumps(dict(status='NECESSARY_GEOMETRY_ONLY_NOT_RELEASE_PRICE',source='frozen candidate9/D762',rows=rows,holds=['all clock/reset/START and paired source rederive','programme/model/ROOT perpath composition','actual registered pin/first/lastFF allbit proof','internalR90 plan support','other macro/reader source graphs']),indent=2)+'\n')
print(json.dumps({'slots':len(rows),'proposed_added_edges':{r['bus']:r['proposed_mission_data_edge_delta']for r in rows}}))
