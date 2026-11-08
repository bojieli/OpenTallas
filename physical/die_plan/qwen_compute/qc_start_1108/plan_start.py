"""QC START transport class event (QC-TYPES-7s 11-08): Codex START4 (qc_start_1106/plan_start.py) generalised to any
type list.  Same knobs: landing_reader_start (R relays origin -> every input ring), landing_writer_start (W relays to far
FSTART face flops) and landing_local_resets (same-depth local raw-reset copies for origin + FSTART flops); hops <= 405 um,
boot +R+W cycles only, 0 steady data cycles.  Changes vs 1106: NAMES from argv; the bound RTL of a type whose module is
shared is read from <rawdir>/<module>__<type>.sv when present (strict bind naming), else <rawdir>/<module>.sv.

usage: plan_start.py BASE_PLAN SIDECAR RAWDIR OUT_PLAN OUT_REPORT TYPE [TYPE ...]"""
import copy,hashlib,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'tools/die_plan'),str(ROOT/'tools/s81_head')]
import clock_landings as CL
import head_cland_stage_delta as H
NAMES=()

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def relay_graph(text):
    out={}
    for m in re.finditer(r'\bot_dp_r(?:relay|gate)(?:_nl)?\s+(\w+)\s*\(([^;]*?)\);([^\n]*)',text,re.S):
        ps=dict(re.findall(r'\.(clk|d|q)\(\s*(\w+)\s*\)',m[2]));d=re.search(r'\bdepth (\d+)\b',m[3])
        if 'q' in ps:out[ps['q']]=dict(instance=m[1],**ps,depth=int(d[1]) if d else None)
    def depth(net,seen=()):
        if net in seen:raise ValueError(('reset cycle',net))
        if net in out:
            z=out[net]
            if z['depth'] is None:z['depth']=depth(z['d'],seen+(net,))+1
            return z['depth']
        a=re.search(r'\bassign\s+'+re.escape(net)+r'\s*=\s*(\w+)\s*;',text)
        if a:return depth(a[1],seen+(net,))
        if net in ['rst_n','rst_root_n','arst_n']:return 0
        raise ValueError(('no literal reset depth',net))
    return out,depth

def plan(base,side,rawdir):
    p=copy.deepcopy(base);L=CL.Landings(base,side);reports={}
    for n in NAMES:
        t=p['partition_types'][n];c=t['clock'];mask=L.by_type[n];rings=mask['inputs'];pins=H.pins_of(t)
        bands={b:H.band_geom(c['landing_contract']['bands'][b]['rect_um']) for b in rings}
        rects=[v['rect_um'] for v in c['landing_contract']['bands'].values()]
        origin=[sum(b[0][i] for b in bands.values())/len(bands) for i in (0,1)]
        role=L.ca_type[n]['role'][0];inport='cland_rstart_in' if role=='relay' else 'cland_tstart_in';entry=pins[inport]
        dist=H.md(origin,entry)
        if dist>365:origin=[entry[i]+(origin[i]-entry[i])*365/dist for i in (0,1)]
        origin=H.rnd(H.snap_point(origin,rects,t['outline_um'],ext=11.15))
        assert H.md(origin,entry)+H.ORIGIN_EXT<=405,(n,'entry',origin,entry)
        sv=rawdir/(t['module']+'__'+n+'.sv')
        sv=sv if sv.exists() else rawdir/(t['module']+'.sv')
        text=sv.read_text();rr=H.rrl_from_rtl(sv);graph,depth=relay_graph(text)
        # QC-TYPES-7 11-08: a raw relay that drives a port (assign rst_o_N = rr_tK) is exported too; the QC wrappers do not
        # use HEAD rst_start_raw* names, so H.rrl_from_rtl misses them (strict bind: writer START raw drives an output port).
        rr=[(a,b,c,d,int(e or bool(re.search(r"\bassign\s+\w+\s*=\s*"+re.escape(a)+r"\s*;",text)))) for a,b,c,d,e in rr]
        origin_inst='u_cland_rstart_rx' if role=='relay' else 'u_cland_origin'
        m=re.search(r'\b'+origin_inst+r'\s*\(([^;]*?)\);',text,re.S);assert m,(n,origin_inst)
        old_reset=re.search(r'\.rst_raw_n\(\s*(\w+)\s*\)',m[1])[1];control_depth=depth(old_reset)
        R=max(H.stages_needed(origin,H.ORIGIN_EXT,*b) for b in bands.values())
        for attempt in range(6):
            reader={};okay=True
            for bus,geom in bands.items():
                pts=[H.rnd(H.snap_point(pt,rects,t['outline_um'])) for pt in H.chain(origin,H.ORIGIN_EXT,*geom,R)]
                seq=[(origin,H.ORIGIN_EXT)]+[(pt,0) for pt in pts]+[geom]
                if any(H.md(seq[j][0],seq[j+1][0])+seq[j][1]+seq[j+1][1]>405+1e-6 for j in range(len(seq)-1)):okay=False
                reader[bus]={'stages':[dict(xy_um=pt,raw_reset=H.nearest(rr,pt,allow_exported=False)[0]) for pt in pts]}
            if okay:break
            R+=1
        else:raise ValueError((n,'reader cannot clear occupied bands at bounded reach'))
        c['landing_reader_start']=dict(depth=R,origin_rect_um=[round(origin[0]-8.64,2),round(origin[1]-8.64,2),round(origin[0]+8.64,2),round(origin[1]+8.64,2)],branches=reader)
        outs=[b for b in mask['outputs'] if 'cland_fstart_out_'+b in pins];needs={b:H.stages_needed(origin,H.ORIGIN_EXT,pins['cland_fstart_out_'+b],0) for b in outs};W=max(needs.values(),default=0)
        # Existing writer branches must remain covered at their new uniform phase.
        far=sorted(set(b for b,x in needs.items() if x)|set(c.get('landing_writer_start',{}).get('branches',{})))
        reuse=role=='relay' and bool(t.get('landing_relay_start_copy'))
        if reuse and W:W+=1
        for attempt in range(6):
            wr={};okay=True
            for bus in far:
                physical=W-int(reuse)
                pts=[H.rnd(H.snap_point(pt,rects,t['outline_um'])) for pt in H.chain(origin,H.ORIGIN_EXT,pins['cland_fstart_out_'+bus],0,physical)]
                seq=[(origin,H.ORIGIN_EXT)]+[(pt,0) for pt in pts]+[(pins['cland_fstart_out_'+bus],0)]
                if any(H.md(seq[j][0],seq[j+1][0])+seq[j][1]+seq[j+1][1]>405+1e-6 for j in range(len(seq)-1)):okay=False
                wr[bus]={'stages':[dict(xy_um=pt,raw_reset=H.nearest(rr,pt,allow_exported=False)[0]) for pt in pts]}
            if okay:break
            W+=1
        else:raise ValueError((n,'writer cannot clear occupied bands at bounded reach'))
        if W:c['landing_writer_start']=dict(depth=W,branches=wr,**({'reuse_relay_origin':True} if reuse else {}))
        consumers={origin_inst:origin,**{'u_cland_fstart_'+b:tuple(pins['cland_fstart_out_'+b]) for b in outs}}
        # SAME old reset depth per actual emitted consumer, including relay origins.
        resets=[];reset_report=[]
        for inst,xy in sorted(consumers.items()):
            choices=sorted((z for z in rr if z[1]==control_depth-1 and not z[4]),key=lambda z:H.md(z[2:4],xy))
            for r in choices:
                rx=r[2:4];d=H.md(rx,xy)
                if d>740:continue
                want=xy if d<=296 else ((xy[0]+rx[0])/2,(xy[1]+rx[1])/2)
                cp=H.snap_point(want,rects,t['outline_um'])
                if H.md(cp,rx)<=370 and H.md(cp,xy)<=370:break
            else:raise ValueError((n,inst,'no legal same-depth local reset copy'))
            resets.append(dict(name='start_'+str(len(resets)),raw=r[0],xy_um=H.rnd(cp),consumers=[inst]));reset_report.append(dict(consumer=inst,old_reset=old_reset,depth=control_depth,raw=r[0],raw_depth=r[1],raw_hop_um=H.md(rx,cp),consumer_hop_um=H.md(cp,xy)))
        c['landing_local_resets']=resets
        hops=[]
        for b,br in reader.items():
            seq=[(origin,H.ORIGIN_EXT)]+[(v['xy_um'],0) for v in br['stages']]+[bands[b]]
            hops += [dict(kind='reader',bus=b,hop_um=H.md(seq[j][0],seq[j+1][0])+seq[j][1]+seq[j+1][1]) for j in range(len(seq)-1)]
        for b,br in wr.items():
            seq=[(origin,H.ORIGIN_EXT)]+[(v['xy_um'],0) for v in br['stages']]+[(pins['cland_fstart_out_'+b],0)]
            hops += [dict(kind='writer',bus=b,hop_um=H.md(seq[j][0],seq[j+1][0])+seq[j][1]+seq[j+1][1]) for j in range(len(seq)-1)]
        for v in hops:assert v['hop_um']<=405+1e-6,(n,v)
        reports[n]=dict(base_type_sha256=digest(base['partition_types'][n]),role=role,origin=origin,entry_port=inport,entry_hop_um=H.md(origin,entry),reader_depth=R,writer_depth=W,reuse_relay_origin=reuse,boot_extra_cycles=R+W,steady_data_cycles_added=0,control_reset_depth=control_depth,raw_relays=len(rr),reader_buses=list(rings),writer_buses=far,max_transport_hop_um=max(x['hop_um'] for x in hops),local_resets=reset_report,hops=hops)
    assert {k:v for k,v in p.items() if k!='partition_types'}=={k:v for k,v in base.items() if k!='partition_types'}
    assert all(p['partition_types'][n]==v for n,v in base['partition_types'].items() if n not in NAMES)
    return p,reports

if __name__=='__main__':
    a=sys.argv[1:]
    if len(a)<6:raise SystemExit(__doc__)
    NAMES=tuple(a[5:]);base=json.loads(Path(a[0]).read_text());side=json.loads(Path(a[1]).read_text())
    p,report=plan(base,side,Path(a[2]))
    Path(a[3]).write_text(json.dumps(p,separators=(', ',': '))+'\n');Path(a[4]).write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({n:{k:v for k,v in z.items() if k in ['reader_depth','writer_depth','boot_extra_cycles','max_transport_hop_um','entry_hop_um','control_reset_depth']} for n,z in report.items()}))
