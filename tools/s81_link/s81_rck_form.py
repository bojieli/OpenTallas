#!/usr/bin/env python3
"""Build a private centred-RCK view and actual-consumer relay pose; never edit a live kit."""
import argparse,csv,hashlib,json,math,re,shutil
from pathlib import Path

PITCH=.048

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def snap(x,p):return round(x/p)*p

def centered_view(lef,tt,ff,bb,out):
    out=Path(out)
    if out.exists():raise ValueError('use a fresh view output directory')
    text=Path(lef).read_text();m=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text)
    w,h=map(float,m.groups())
    if w<5*h:raise ValueError('centred RCK form requires the retained EW macro')
    pins=list(re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1\s*$',text,re.M|re.S))
    clocks=[p for p in pins if p[1]=='pma_rck']
    if len(clocks)!=1 or 'USE CLOCK' not in clocks[0][2]:raise ValueError('one native pma_rck clock port required')
    block=clocks[0];rects=list(re.finditer(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',block[2]))
    if len(rects)!=1 or 'LAYER M5 ;' not in block[2]:raise ValueError('exact native single M5 clock rectangle required')
    r=rects[0];x0,y0,x1,y1=map(float,r.groups());width=x1-x0;phase=((x0+x1)/2)%PITCH
    data=[]
    for p in pins:
        if not p[1].startswith('pma_rx['):continue
        for b in re.finditer(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;',p[2]):
            a,b0,c,d=map(float,b.groups())
            if b0<y1 and d>y0:data.append((a,c))
    if len(data)!=544:raise ValueError('preserve all 544 native pad-side input rectangles')
    data.sort();choices=[]
    for a,b in zip(data,data[1:]):
        centre=snap(((a[1]+b[0])/2-phase),PITCH)+phase
        clearance=min(centre-width/2-a[1],b[0]-centre-width/2)
        if clearance>=.192:choices.append((abs(centre-w/2),-centre,centre,clearance))
    if not choices:raise ValueError('no legal centred clock gap')
    _,_,centre,clearance=min(choices)
    replacement=f'RECT {centre-width/2:.3f} {y0:.3f} {centre+width/2:.3f} {y1:.3f} ;'
    start=block.start(2)+r.start();end=block.start(2)+r.end();updated=text[:start]+replacement+text[end:]
    out.mkdir(parents=True)
    target=out/Path(lef).name;target.write_text(updated)
    for f in [tt,ff,bb]:shutil.copyfile(f,out/Path(f).name)
    # All PG/OBS/data ports and all actual timing/functional bytes stay exact.
    assert updated[:start]==text[:start] and updated[start+len(replacement):]==text[end:]
    rec=dict(schema='opentallas.s81_rck_view.v1',master='ot_s81_pma_rxm',footprint_um=[w,h],
             clock_layer='M5',old_clock_rect=[x0,y0,x1,y1],new_clock_rect=[centre-width/2,y0,centre+width/2,y1],
             clearance_um=clearance,pma_latency_cycles=4,timing_and_bb='byte-identical retained native views',
             inputs={str(f):sha(f) for f in [lef,tt,ff,bb]},outputs={f.name:sha(f) for f in out.iterdir() if f.is_file()})
    (out/'rck_view.json').write_text(json.dumps(rec,indent=1)+'\n');return rec


def boxes(macros,placement):
    result=[]
    for name,x,y,orient in re.findall(r'place_macro -macro_name \{([^}]+)\} -location \{([\d.]+) ([\d.]+)\} -orientation (\w+)',Path(placement).read_text()):
        if orient not in ('R0','MX','MY','R180'):raise ValueError('unqualified macro orientation '+orient)
        if name.endswith('u_prx'):master='ot_s81_pma_rxm'
        elif name.endswith('u_ptx'):master='ot_s81_pma_txm'
        elif name.endswith('u_chn'):master='ot_s81_kp4_dchn'
        elif name.endswith('u_dmem'):master='ot_sram_1r1w2c_64x546_m1'
        elif name.endswith('u_cmem'):master='ot_sram_1r1w_32x546_m1'
        else:raise ValueError('unknown retained macro '+name)
        s=(Path(macros)/(master+'.lef')).read_text();m=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',s);w,h=map(float,m.groups());x,y=float(x),float(y)
        obs=s.split('OBS',1)[1] if 'OBS' in s else ''
        if any(int(k)>5 for k in re.findall(r'LAYER M(\d+)',obs)):raise ValueError('M6/M7 relay overflight blocked by '+name)
        result.append(dict(instance=name,master=master,rect=[x,y,x+w,y+h],orientation=orient))
    if len(result)!=5:raise ValueError('retain all five native PHY/decoder/SRAM macros')
    return result


def relay_pose(capture,sinks,macros,placement):
    first=list(csv.DictReader(Path(capture).open(),delimiter='\t'));rows=list(csv.DictReader(Path(sinks).open(),delimiter='\t'))
    source={};dest={}
    for r in first:
        bit=int(re.search(r'\.q\[(\d+)\]',r['instance'].replace('\\',''))[1])
        if r['kind']!='ff' or int(r['origin_count'])!=1:raise ValueError('exact one-bit native capture map required')
        source[bit]=r
    for r in rows:
        n=r['instance'].replace('\\','')
        if '.u_syn.x0[' in n:dest[int(re.search(r'x0\[(\d+)\]',n)[1])]=r
    if set(source)!=set(range(544)) or set(dest)!=set(range(544)):raise ValueError('all544 exact native producer/consumer bits required')
    ms=boxes(macros,placement);rx=next(m for m in ms if m['master']=='ot_s81_pma_rxm');band=rx['rect'][1]-12.96
    obstacles=[(a-9.234,b-8.775,c+9.234,d+8.775) for m in ms for a,b,c,d in [m['rect']]]
    occupied={}
    def reserve(p,width=1.404):
        key=(int(p[0]/4),int(p[1]/2));occupied.setdefault(key,[]).append((p[0],p[1],width))
    def free(p):
        x,y=p
        if not (4.914<=x<=2880.846 and 4.455<=y<=1222.425):return False
        if any(a<x<c and b<y<d for a,b,c,d in obstacles):return False
        k=(int(x/4),int(y/2))
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for a,b,width in occupied.get((k[0]+dx,k[1]+dy),[]):
                    if abs(a-x)<(1.404+width)/2-1e-8 and abs(b-y)<.27-1e-8:return False
        return True
    def grid(p):return (round(snap(p[0]-.54,.054)+.54,6),round(snap(p[1]-.135,.27)+.135,6))
    def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
    def choices(ideal):
        out=[ideal]
        for rad in (2.16,4.32,8.64,17.28,34.56,69.12):
            out.extend((ideal[0]+dx*rad,ideal[1]+dy*rad) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)))
        for a,b,c,d in obstacles:
            out.extend(((a-.108,ideal[1]),(c+.108,ideal[1]),(ideal[0],b-.27),(ideal[0],d+.27)))
        return sorted(set(map(grid,out)),key=lambda p:dist(p,ideal))
    def route(start,goal):
        def walk(prev,left,path):
            if left==1:
                if dist(prev,goal)<=405+1e-6:return path+[goal]
                return None
            ideal=(prev[0]+(goal[0]-prev[0])/left,prev[1]+(goal[1]-prev[1])/left)
            for p in choices(ideal):
                if free(p) and dist(prev,p)<=405+1e-6 and dist(p,goal)<=405*(left-1)+1e-6:
                    result=walk(p,left-1,path+[p])
                    if result:return result
            return None
        if dist(start,goal)>1620:raise ValueError('four native405um hops cannot reach consumer')
        return walk(start,4,[])
    # Retain actual clocked-register occupancy; old data-face cells move to band.
    oldfaces={r['instance'] for r in first}
    for r in rows:
        if r['instance'] not in oldfaces and r['master'].startswith('DFF'):reserve((float(r['x_um']),float(r['y_um'])),float(r['area_um2'])/.27)
    fields=[]
    def field(bit,start,target,kind,producer,consumer):
        start=grid(start)
        if kind!='valid':
            if not free(start):raise ValueError('capture site blocked '+str(bit))
            reserve(start)
        result=None
        for goal in choices(target):
            if free(goal):
                result=route(start,goal)
                if result:break
        if not result:raise ValueError('no legal literal four-stage pose for field '+str(bit))
        for point in result:reserve(point)
        path=[start]+result;hops=[dist(a,b) for a,b in zip(path,path[1:])]
        fields.append(dict(bit=bit,kind=kind,producer=producer,consumer=consumer,capture_xy=list(start),stages=[list(p) for p in result],hops_um=hops))
    # Longest fields first preserve admission slack around the hard-macro wall.
    order=sorted(range(544),key=lambda k:abs(float(source[k]['origin_x_mean'])-float(dest[k]['x_um']))+abs(band-float(dest[k]['y_um'])),reverse=True)
    for k in order:
        r,t=source[k],dest[k]
        field(k,(float(r['origin_x_mean']),band+.135),(float(t['x_um'])+2.16,float(t['y_um'])),'payload',r['instance'],t['instance'])
    am=next(r for r in rows if '.u_syn.am_ok$' in r['instance']);pv=next(r for r in rows if '.u_syn.pv$' in r['instance']);facev=next(r for r in rows if '.u_face_p_v.q$' in r['instance'])
    for group in range(3):
        x=sum(float(source[k]['origin_x_mean']) for k in range(532+4*group,536+4*group))/4
        for b in range(3):
            i=3*group+b
            field(545+i,(x+(b-1)*2.16,band-8.64+.135),(float(am['x_um'])+(i-4)*2.16,float(am['y_um'])-4.32),'partial_count','PMA header bits '+str(list(range(532+4*group,536+4*group))),am['instance'])
    field(544,(float(facev['x_um']),float(facev['y_um'])),(float(pv['x_um'])+2.16,float(pv['y_um'])-2.16),'valid',facev['instance'],pv['instance'])
    fields.sort(key=lambda x:x['bit']);assert len(fields)==554 and {f['bit'] for f in fields}==set(range(554))
    return dict(schema='opentallas.s81_rck_relay_pose.v1',field_width=554,stages=4,max_hop_um=max(max(f['hops_um']) for f in fields),min_hop_um=min(min(f['hops_um']) for f in fields),
                source_inputs=dict(capture_sha256=sha(capture),sinks_sha256=sha(sinks)),macros=ms,fields=fields,
                routing='M6/M7 overflight; all actual child OBS<=M5; PG/macros unchanged',
                binding='resolve each logical registered field against fresh synthesis connectivity; merge aliases co-locate, never guess cell indices',
                reset_calendar='four edges; valid/reset aliases share logical depth and must be resolved from actual netlist',
                model=dict(added_recovered_PIN_cycles=4,period_ps=833,added_latency_ps=3332,words_per_recovered_edge=1,transport_reset_FF_upper_bound=2220,AM_FF=9,total_FF_upper_bound=2229,required_LOCKSAFE=1,minimum_HOLD_EDGES=64))



def native_plan(native,profile,out):
    """Compose one physical/source option into the full captured native context."""
    import sys
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
    import schema as S
    import landing_contract as LC
    native=Path(native).resolve();profile=Path(profile).resolve();out=Path(out)
    if out.exists():raise ValueError('do not overwrite an existing prepared plan')
    d=json.loads(native.read_text());t=d['partition_types']['serdes__t4']
    pose=json.loads((profile/'relay_pose.json').read_text())
    view=json.loads((profile/'rx_centered/rck_view.json').read_text())
    if t['outline_um']!=[2885.76,1226.88] or pose['field_width']!=554 or pose['stages']!=4:
        raise ValueError('this actual profile is qualified only for retained t4 geometry')
    candidates=[q for c in t['contents'] for q in c.get('physical_parts',[]) if q['physical_master']=='ot_s81_pma_rxm']
    if len(candidates)!=1:raise ValueError('one exact retained RX physical part required')
    rx=candidates[0]
    if rx['origin_um']!=[319.272,952.56] or rx.get('orient')!='MX':raise ValueError('retained native RX pose differs')
    lef=profile/'rx_centered/ot_s81_pma_rxm.lef'
    if sha(lef)!=view['outputs'][lef.name]:raise ValueError('prepared RX view differs')
    rx['lef']=str(lef);rx['lib']=str(profile/'rx_centered/ot_s81_pma_rxm_tt.lib')
    flags=t.setdefault('verilog_defines',[])
    for flag in ('OT_S81_KP4_AM_FACE3','OT_S81_RCK_RELAY4'):
        if flag not in flags:flags.append(flag)
    pins=t['clock']['pad_clock']['pins']
    if len(pins)!=1 or pins[0]['name']!='io_pma_rck' or pins[0]['period_ps']!=833:
        raise ValueError('exact native recovered-clock contract required')
    rect=view['new_clock_rect'];raw_x=rx['origin_um'][0]+(rect[0]+rect[2])/2
    P=S.Plan(d,str(native));xy=LC.on_track(P,pins[0]['layer'],raw_x,pins[0]['xy_um'][1])
    pins[0]['xy_um']=list(xy)
    out.write_text(json.dumps(d,separators=(',',':'))+'\n')
    receipt=dict(schema='opentallas.s81_rck_native_profile.v1',source_plan=str(native),source_sha256=sha(native),
                 prepared_plan=str(out.resolve()),prepared_sha256=sha(out),type='serdes__t4',defines=flags,
                 physical_view=str(lef),physical_view_sha256=sha(lef),RCK_anchor_um=list(xy),
                 model=pose['model'],native_topology='preserved full native plan; no reset/landing indices or edges changed',
                 geometry_review='results/geom_review/s81_rck_B4_1106/review.json',
                 state='PREPARED; fresh mapped connectivity and real clock construction required before route')
    out.with_suffix('.profile.json').write_text(json.dumps(receipt,indent=1)+'\n')
    return receipt


def main():
    a=argparse.ArgumentParser();a.add_argument('--capture',required=True);a.add_argument('--sinks',required=True);a.add_argument('--macros',required=True);a.add_argument('--placement',required=True);a.add_argument('--bb',required=True);a.add_argument('--out',required=True);a.add_argument('--native-plan');a.add_argument('--plan-out')
    q=a.parse_args();out=Path(q.out)
    if out.exists():raise ValueError('use a fresh profile output directory')
    pose=relay_pose(q.capture,q.sinks,q.macros,q.placement)
    out.mkdir(parents=True);(out/'relay_pose.json').write_text(json.dumps(pose,indent=1)+'\n')
    m=Path(q.macros);centered_view(m/'ot_s81_pma_rxm.lef',m/'ot_s81_pma_rxm_tt.lib',m/'ot_s81_pma_rxm_ff.lib',q.bb,out/'rx_centered')
    if q.native_plan:
        if not q.plan_out:raise ValueError('--native-plan requires --plan-out')
        native_plan(q.native_plan,out,q.plan_out)
    print(json.dumps(dict(fields=554,stages=4,max_hop_um=pose['max_hop_um'],min_hop_um=pose['min_hop_um'],model=pose['model']),indent=1))
if __name__=='__main__':main()
