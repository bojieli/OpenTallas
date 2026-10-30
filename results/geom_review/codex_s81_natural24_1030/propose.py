#!/usr/bin/env python3
"""Analytic natural-child placement; never writes a release plan or creates views."""
import argparse, hashlib, json, math, re, sys
from collections import defaultdict
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--plan',required=True)
    ap.add_argument('--out',required=True);a=ap.parse_args();repo=Path(a.repo);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(repo/'tools/die_plan'));import schema
    data=json.load(open(Path(__file__).with_name('native_children.json')));plan=json.load(open(a.plan))
    t=plan['partition_types']['ot_s81sl_kv_leaf__t1'];W,H=t['outline_um'];halo=5.4
    taps=[(W*(i+.5)/4,H*(j+.5)/4) for i in range(4) for j in range(4)]
    pinroot=repo/'physical/die_plan/s81';rows=data['core_rows'];by={x['source_interface']['physical_inst']:x for x in rows}
    def short(k):return k.removeprefix('u_bound.u_u_')
    fixed={'ve_u_s':(546.624,780.48),'ve_u_m':(721.728,780.48),
           'vn_u_a':(552.96,181.44),'vn_u_b':(552.96,488.16),
           'vsw':(930.816,769.536),'vs':(1168.704,776.736),
           'rxsf':(923.328,1005.12),'rxsb':(1074.624,1005.12)}
    pinsets={};pin_sources={}
    for k,v in by.items():
        p=pinroot/v['known_parent_placement']['pins_file'];pd=json.load(open(p));pinsets[k]={x['name']:x for x in pd['pins']}
        pin_sources[str(p.relative_to(repo))]=hashlib.sha256(p.read_bytes()).hexdigest()
    A=[]
    for k,v in by.items():
        s=short(k);old=v['known_parent_placement'];wh=old['outline_um']
        if s.startswith('vp_g_ln_'):
            i=int(re.search(r'ln_(\d+)',s).group(1));xy=([928.8,1054.08,1179.36,1304.64][i%4],[181.44,306.72,488.16,613.44][i//4])
        else:xy=fixed[s]
        A.append(dict(inst=k,module=v['source_interface']['module'],xy=list(xy),wh=wh,orient=old['orient'],kind='hard',params=v['source_interface']['actual_params']))
    macro_specs=[('u_bound.u_u_vp_u_b0',[169.368,29.16],552.96),('u_bound.u_u_vp_u_b1',[169.368,29.16],743.04),('u_bound.u_u_vq.g_xr.u_xm',[94.824,41.064],933.12)]
    def parent_macros(y):return [dict(inst=k,module='parent_SRAM',xy=[x,y],wh=wh,orient='R0',kind='parent SRAM') for k,wh,x in macro_specs]
    A+=parent_macros(34.56)
    B=[];mirror={'R0':'MX','MY':'R180'}
    for v in A[:24]:
        b=dict(v);b['xy']=[v['xy'][0],round(H-v['xy'][1]-v['wh'][1]+.024,6)];b['orient']=mirror[v['orient']];B.append(b)
    B+=parent_macros(1088.64)
    C=[]
    cp={'ve_u_s':(546.624,200.064),'ve_u_m':(721.728,200.064),'vn_u_b':(500.16,774.144),'vn_u_a':(867.36,900.096),'vs':(683.52,973.44),'vsw':(928.8,660.096),'rxsf':(930.816,25.92),'rxsb':(1082.112,25.92)}
    for v in A[:24]:
        z=dict(v);k=short(z['inst'])
        if k.startswith('vp_g_ln_'):
            i=int(re.search(r'ln_(\d+)',k).group(1))
            if i>=12:z['xy']=[[500.16,625.44,750.72,1194.048][i-12],613.44]
        else:z['xy']=list(cp[k])
        if k in ['vn_u_a','vn_u_b']:z['orient']='R0'
        C.append(z)
    C+=parent_macros(34.56)
    C[-3]['xy'][0]=500.16;C[-2]['xy'][0]=690.24;C[-1]['xy']=[500.16,80.064]
    def rect(v):x,y=v['xy'];w,h=v['wh'];return x,y,x+w,y+h
    def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-8 and min(a[3],b[3])>max(a[1],b[1])+1e-8
    def pin(v,name):
        p=pinsets[v['inst']][name];x,y=p['x'],p['y'];w,h=v['wh'];o=v['orient']
        if o in ('MY','R180'):x=w-x
        if o in ('MX','R180'):y=h-y
        return v['xy'][0]+x,v['xy'][1]+y
    def md(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
    buses={b['name']:b for b in t['buses']};layers={x['name']:x for x in plan['die'].get('layers',schema.ASAP7_LAYERS)}
    external={}
    for name,b in buses.items():
        q=dict(b,id=name,src={'part':'leaf'},dst={'part':'parent'});external[name]={i:(x,H) for i,ln,x in schema.pin_positions(q,layers)}
    reports={}
    for label,layout in [('A',A),('B',B),('C',C)]:
        M={short(v['inst']):v for v in layout if v['kind']=='hard'};bad=[];tap_hits=[]
        for i,v in enumerate(layout):
            rr=rect(v)
            if rr[0]<500 or rr[1]<17 or rr[2]>1430 or rr[3]>1152:bad.append(['target bounds',v['inst'],rr])
            for z in layout[i+1:]:
                if overlap(rr,rect(z)):bad.append(['body overlap',v['inst'],z['inst']])
            for k,(x,y) in enumerate(taps):
                if overlap(rr,(x-halo,y-halo,x+halo,y+halo)):tap_hits.append([v['inst'],k])
        critical=[]
        def conn(title,src,dst,ports):
            vals=[]
            for sp,dp,n in ports:
                for i in range(n):
                    sn=f'{sp}[{i}]' if n>1 else sp;dn=f'{dp}[{i}]' if n>1 else dp
                    if sn not in pinsets[src['inst']] or dn not in pinsets[dst['inst']]:continue
                    pa,pb=pin(src,sn),pin(dst,dn);vals.append((md(pa,pb),sn,dn,pa,pb))
            critical.append(dict(name=title,bits=len(vals),max_manhattan_um=round(max(x[0] for x in vals),3),over405=sum(x[0]>405 for x in vals),worst=max(vals),source='available unqualified template pins; point distance is a lower bound, not obstacle-routed timing'))
        conn('VE_m -> VE_s',M['ve_u_m'],M['ve_u_s'],[(p,p,128) for p in ['m_dd','m_hh','m_kk']]+[('m_pre','m_pre',1),('m_v','m_v',1)])
        conn('VN_a -> VN_b',M['vn_u_a'],M['vn_u_b'],[('c_s','c_s',31),('c_v','c_v',1)])
        conn('RXsf -> RXsb',M['rxsf'],M['rxsb'],[('o_mx','i_mx',32),('o_u','i_u',31),('o_u2','i_u2',31),('o_v','i_v',1)])
        external_reach=[]
        for key,port,bits,start,bus,direction in [('vn_u_a','rb_d',32,0,'leafdn_i0','in'),('vn_u_b','rb_d',32,0,'leafdn_i0','in'),('vs','g_d',32,561,'leafdn_i0','in'),('vs','e_d',96,3,'leafup_o0','out')]:
            v=M[key];vals=[]
            for i in range(bits):
                pp=pin(v,f'{port}[{i}]');ep=external[bus][start+i];vals.append((md(pp,ep),i,pp,ep))
            worst=max(vals);n=len([x for x in vals if x[0]>405]);lower=math.ceil(worst[0]/405)
            external_reach.append(dict(core=key,port=port,bus=bus,bits=bits,max_manhattan_um=round(worst[0],3),over405=n,minimum_segments_lower_bound=lower,minimum_extra_pipeline_cycles_lower_bound=max(0,lower-1),worst=worst,existing_RTL_path='direct boundary register -> core (or core -> boundary register), no new relay assumed'))
        clocks=[]
        for v in layout[:24]:
            names=[p for p in pinsets[v['inst']] if p in ['clk','ck']]
            pp=pin(v,names[0]) if names else (v['xy'][0]+v['wh'][0]/2,v['xy'][1]+v['wh'][1]/2)
            j=min(range(16),key=lambda j:md(pp,taps[j]));clocks.append(dict(inst=v['inst'],pin=names[0] if names else 'MISSING_EXACT_PIN',xy=pp,tap=j,feed_manhattan_um=round(md(pp,taps[j]),3)))
        area=sum(v['wh'][0]*v['wh'][1] for v in layout[:24]);ma=sum(v['wh'][0]*v['wh'][1] for v in layout[24:]);region=(1430-500)*(1152-17)
        # These are independently sized lower-bound cut budgets, not a whole-netlist cut PASS.
        tracks=.75*(1/.048+1/.064)
        cut=[dict(link='VE_m/VE_s',bits=386,available_face_span_um=345.6,tracks=round(345.6*tracks,3),ratio=round(386/(345.6*tracks),6)),dict(link='VN_a/VN_b',bits=32,available_face_span_um=356.4,tracks=round(356.4*tracks,3),ratio=round(32/(356.4*tracks),6)),dict(link='HCPL 16 inputs, aggregate',bits=16*257,minimum_clear_span_um_at_60pct=round(16*257/(tracks*.6),3),note='actual source256data+valid per lane; VP parent storage/soft registered glue must be placed; do not invent direct HCPL->VN wires')]
        report=dict(status='ANALYTIC_CANDIDATE_NOT_ADOPTED',layout=layout,geometry_body_findings=bad,clock_reset_keepout_10p8_hits=tap_hits,hard_count=24,hard_footprint_um2=area,parent_macro_um2=ma,target_region_um2=region,free_region_after_bodies_um2=region-area-ma,
                    parent_glue_cell_counts={'t1':94717,'t3':138117,'t4':123432,'t5':88282},max_average_parent_cell_area_at_60pct_um2=round(.6*(region-area-ma)/138117,3),
                    direct_internal_pin_links=critical,direct_N_boundary_links=external_reach,clock_feeds=clocks,max_clock_feed_um=max(x['feed_manhattan_um'] for x in clocks),cut_budget_estimates=cut,
                    qualified_clock_views=0,qualification='Footprints and pin tables are not signed/current ABI views; no RTL, plan, latency, pin or clock contract change adopted.')
        reports[label]=report;(out/f'variant_{label}.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'input_refs.json').write_text(json.dumps(dict(dataset_commit='8e3341c88ce',plan_sha256=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest(),pin_file_sha256=pin_sources,source_ABI_gap='inherited kv_bound has594data+epoch595; current plan has597data+epoch598, +3 k bits remain SOURCE/PLAN FAIL owned by S81'),indent=2)+'\n')
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,axs=plt.subplots(1,3,figsize=(25,9),dpi=150)
    colors={'ve':'#6baed6','vn':'#fd8d3c','vp':'#74c476','vsw':'#9e9ac8','vs':'#c7b9e2','rx':'#fdae6b'}
    for ax,(label,rep) in zip(axs,reports.items()):
        ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5));ax.add_patch(Rectangle((0,0),499.2,H,color='#e6e6e6',alpha=.8));ax.add_patch(Rectangle((0,1152),W,H-1152,color='#fff2b2',alpha=.7))
        for x,y in taps:ax.add_patch(Rectangle((x-halo,y-halo),2*halo,2*halo,fc='red'));ax.text(x+7,y,'tap',fontsize=4,color='red')
        for v in rep['layout']:
            k=short(v['inst']);c=next((c for p,c in colors.items() if k.startswith(p)),'#aaaaaa') if v['kind']=='hard' else '#bbbbbb';ax.add_patch(Rectangle(v['xy'],*v['wh'],fc=c,ec='black',lw=.6,alpha=.8));x,y=v['xy'];w,h=v['wh'];txt=re.sub(r'vp_g_ln_(\d+)_u_l',r'H\1',k).replace('_u_','_')
            ax.text(x+w/2,y+h/2,txt+'\n'+v['orient'],ha='center',va='center',fontsize=6)
        M={short(v['inst']):v for v in rep['layout'] if v['kind']=='hard'}
        for q in rep['direct_N_boundary_links']:
            _,bit,p,e=q['worst'];ax.plot([p[0],e[0]],[p[1],e[1]],color='crimson',lw=1,ls='--');ax.text((p[0]+e[0])/2,(p[1]+e[1])/2,f"{q['port']} {q['max_manhattan_um']:.0f}",fontsize=5,color='crimson')
        for q in rep['direct_internal_pin_links']:
            if q['name']=='VN_a -> VN_b':
                _,sp,dp,pa,pb=q['worst'];ax.plot([pa[0],pb[0]],[pa[1],pb[1]],color='darkorange',lw=1.2,ls=':')
        ax.set(xlim=(-20,W+20),ylim=(-20,H+35),aspect='equal',title=f"{label}:24 real child footprints,3 parent SRAMs\nBody/clock-site fit only; red=N-boundary lower bounds; orange=VN link")
    fig.suptitle('S81 KVleaf natural24 analytic proposals — no release-plan edit, no fabricated views, no P&R',fontsize=12);fig.tight_layout();fig.savefig(out/'variants.png')
    print(json.dumps({k:dict(body_errors=len(v['geometry_body_findings']),tap_hits=len(v['clock_reset_keepout_10p8_hits']),hard_area=v['hard_footprint_um2'],clock_feed_max=v['max_clock_feed_um'],direct_N_max=max(q['max_manhattan_um'] for q in v['direct_N_boundary_links']),internal=[(q['name'],q['max_manhattan_um'],q['over405']) for q in v['direct_internal_pin_links']]) for k,v in reports.items()},indent=2))
if __name__=='__main__':main()
