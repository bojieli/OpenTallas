#!/usr/bin/env python3
"""Price a disabled TT_C homes proposal against the existing clock ABI; does not rewire a kit."""
import argparse, importlib.util, json, re, collections, heapq
from pathlib import Path

def check(dump,homes,origin_homes,macro_delta,output,macro_ports,sdc,raw_homes=None):
    root=Path(__file__).resolve().parents[3]
    spec=importlib.util.spec_from_file_location('geom',root/'tools/autopilot/geom_rules.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    d=g.Design(dump);move={r['name']:r['xy'] for r in homes};mc={r['id']:(r['dx'],r['dy']) for r in macro_delta}
    main=[p for p in d.pins if p['io']=='INPUT' and re.fullmatch(r'clk(?:_t\d+)?(?:\[0\])?',p['name'])]
    if len(main)!=63:raise ValueError('Clock ABI must remain exactly63 existing main-clock ports')
    declared=re.findall(r'create_clock -name clk -period ([0-9.]+) \[get_ports \{([^}]+)\}\]',sdc.read_text())
    if len(declared)!=1 or set(declared[0][1].split())!={p['name'] for p in main}:raise ValueError('All63 ports must belong to the one actual named clk cohort')
    memo={}
    def clock_root(n):
        if n in memo:return memo[n]
        dr=d.nets[n][1]
        if not dr:r=None
        elif dr[0]=='p':r=d.pin_by_k[dr[1]]['name']
        elif d.kind(dr[1]) in ('B','K'):
            ns=d.cell_in.get(dr[1],[]);ck=[nn for nn,c in ns if c];rr=ck or [nn for nn,c in ns]
            r=clock_root(rr[0]) if len(rr)==1 else None
        else:r=None
        memo[n]=r;return r
    sinks=[];unknown=[];retained=[]
    physical_clocks=collections.defaultdict(list)
    for line in macro_ports.read_text().splitlines():
        a=line.split('\t')
        if a[0]!='PORT' or a[5]!='CLOCK':continue
        rect=[list(map(float,z.split(','))) for z in a[7].split(';')]
        box=[min(z[0] for z in rect),min(z[1] for z in rect),max(z[2] for z in rect),max(z[3] for z in rect)]
        physical_clocks[int(a[1]),int(a[6])].append((a[3],[(box[0]+box[2])/2,(box[1]+box[3])/2]))
    physical_used=collections.Counter()
    replaced=lambda n:any(n.startswith('u_bound.u_cland_origin/'+stage+'$') for stage in ['s1','s2','pd'])
    for i,c in d.cells.items():
        if c[0] not in ('S','M') or replaced(c[6]):continue
        xy=move.get(c[6],list(g.ctr(c)))
        if c[0]=='M':
            xy=list(d.extra.get('macro_clk_xy',{}).get(i,g.ctr(c)))
            if i in mc:xy=[xy[0]+mc[i][0],xy[1]+mc[i][1]]
        for nn,isclk in d.cell_in.get(i,[]):
            if not isclk:continue
            sinkname=c[6]
            if c[0]=='M':
                kk=(i,nn);q=physical_used[kk];physical_used[kk]+=1;pp=physical_clocks[kk]
                if q>=len(pp):unknown.append('Missing exact macro clock ITerm: '+c[6]);continue
                pn,xy=pp[q];xy=list(xy);sinkname+='::'+pn
                if i in mc:xy=[xy[0]+mc[i][0],xy[1]+mc[i][1]]
            r=clock_root(nn)
            if r is None:unknown.append(c[6]);continue
            if re.fullmatch(r'clk(?:_t\d+)?(?:\[0\])?',r):sinks.append(dict(name=sinkname,xy=xy,logical_root=r))
            else:
                retained.append(dict(name=sinkname,logical_root=r,xy=xy))
                if c[6] in move:unknown.append('Non-main clock sink moved without its own cohort: '+c[6])
    for h in origin_homes:
        sinks.append(dict(name=f'u_bound.u_cland_origin/g_on.g_region[{h["region"]}].{h["stage"]}',xy=h['xy'],logical_root='clk'))
    for h in (raw_homes if raw_homes is not None else [h for h in origin_homes if h['stage']=='s2']):
        sinks.append(dict(name=f'u_bound.g_tt_raw_regions.g_region[{h["region"]}].u_raw_copy/q',xy=h['xy'],logical_root='clk'))
    loads=collections.Counter();assign=[];bad=[]
    for sink in sinks:
        x,y=sink['xy'];tap=min(main,key=lambda p:abs(x-p['x'])+abs(y-p['y']));reach=abs(x-tap['x'])+abs(y-tap['y']);loads[tap['name']]+=1
        assign.append(dict(**sink,parent_tap=tap['name'],reach_um=round(reach,6)))
        if reach>200:bad.append(sink['name'])
    nearest_max=max(loads.values());nearest_loads=dict(loads);changes=0;queue=[]
    tap_by_name={p['name']:p for p in main}
    for j,a in enumerate(assign):
        if loads[a['parent_tap']]<=1200:continue
        x,y=a['xy']
        for tap in main:
            reach=abs(x-tap['x'])+abs(y-tap['y'])
            if tap['name']!=a['parent_tap'] and reach<=200:
                heapq.heappush(queue,(reach-a['reach_um'],j,tap['name'],reach))
    while queue and max(loads.values())>1200:
        _,j,target,reach=heapq.heappop(queue);a=assign[j];source=a['parent_tap']
        if 'nearest_parent_tap' in a or loads[source]<=1200 or loads[target]>=1200:continue
        a['nearest_parent_tap']=source;a['parent_tap']=target;a['reach_um']=round(reach,6);loads[source]-=1;loads[target]+=1;changes+=1
    summary=dict(schema='opentallas.tt_clock_association_prep.v1',status='PASS_MODEL_ONLY' if not unknown and not bad and max(loads.values())<=1200 else 'HELD',clock_ports=[p['name'] for p in main],port_count=63,policy='explicit capacity-aware same-cohort reassociation after the normal nearest split; source event must apply this metadata before CTS; no new tap count/strength/edge/waveform',clock_period_ps=float(declared[0][0]),reassociated_sinks=changes,nearest_load_max=nearest_max,nearest_loads=nearest_loads,native_clock_tree_applied=False,preserve_existing_cell_clock_edge_and_clock_polarity_path=True,no_clock_gate_or_inverter_bypass=True,native_name_join_required=True,added_main_clock_ff=13,main_sinks=len(sinks),nonmain_sinks_retained=len(retained),max_reach_um=max(a['reach_um'] for a in assign),max_sinks=max(loads.values()),loads=dict(loads),unknown=unknown,reach_fail=bad,over_capacity={k:v for k,v in loads.items() if v>1200},arrival_or_timing_credit=False,assignments=assign,retained_other_cohorts=retained)
    output.write_text(json.dumps(summary,separators=(',',':'))+'\n');return summary
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--dump',type=Path,required=True);ap.add_argument('--homes',type=Path,required=True);ap.add_argument('--origin-homes',type=Path,required=True);ap.add_argument('--macro-delta',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--macro-ports',type=Path,required=True);ap.add_argument('--sdc',type=Path,required=True);ap.add_argument('--raw-homes',type=Path);a=ap.parse_args()
    r=check(a.dump,json.loads(a.homes.read_text()),json.loads(a.origin_homes.read_text()),json.loads(a.macro_delta.read_text()),a.out,a.macro_ports,a.sdc,json.loads(a.raw_homes.read_text()) if a.raw_homes else None);print('TT_CLOCK_ASSOCIATION',r['status'],'main',r['main_sinks'],'reach',r['max_reach_um'],'load',r['max_sinks'],'unknown',len(r['unknown']))
