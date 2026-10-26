#!/usr/bin/env python3
"""Pack the EXISTING delay flops of an actual bound CB16 wrapper without adding RTL stages.

This is a physical preparation tool. A complete G2 gate additionally requires actual hard views and all
other mapped soft registers; missing views/fabric-register inventories are explicit blockers, never skeleton PASS.
"""
import argparse,copy,heapq,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import check,gen_phys,schema,taps

DLY=re.compile(r'\bot_dp_dly\s*#\(\s*\.W\((\d+)\),\s*\.D\((\d+)\)\s*\)\s+(\w+)\s*\((.*?)\);',re.S)
LEAF=re.compile(r'// as-built ([^\n]+)\n\s*(\w+)\s+(\w+)\s*\((.*?)\n\s*\);',re.S)
PIN=re.compile(r'\.(\w+)\(([^()]*)\)')
CELL_W,CELL_H=1.08,.27  # actual DFFHQNx1_ASAP7_75t_R 1x LEF, area .2916um2
PITCH_X=2.16            # 50% horizontal utilization; actual DPL must confirm the chosen mapped master
MARGIN=4.32
PIN_OVERRIDES={}


def physical_name(name):
    m=re.fullmatch(r'u_u_t_(\d)_(\d)',name)
    if m:return 'u_t'+m[1]+m[2]
    m=re.fullmatch(r'u_u_fab_u_x_(\d)_(\d)',name)
    if m:return 'u_xstn'+m[1]+m[2]
    return name


def core_pin(t,inst,pin,plan_dir):
    hc=next((c for c in t.get('hard_cores',[]) if c['inst']==inst),None)
    if not hc:return None
    pts=[];w,h=hc['outline_um'];ox,oy=hc['origin_um'];dx,dy=hc.get('track_offset_um',[0,0])
    rows=check.core_pins(hc,plan_dir)
    if hc.get('module') in PIN_OVERRIDES:
        rows=[(q['name'],q['layer'],q['x'],q['y']) for q in PIN_OVERRIDES[hc['module']]['pins']]
    for n,_l,x,y in rows:
        if n!=pin and not n.startswith(pin+'['):continue
        orient=hc.get('orient','R0')
        if orient in ('MY','R180'):x=w-x
        if orient in ('MX','R180'):y=h-y
        if orient not in ('R0','MY','MX','R180'):raise ValueError('unsupported actual core orientation '+orient)
        pts.append((ox+dx+x,oy+dy+y))
    return (sum(x for x,y in pts)/len(pts),sum(y for x,y in pts)/len(pts)) if pts else None


def inside(p,b):return b[0]<p[0]<b[2] and b[1]<p[1]<b[3]
def overlap(a,b,gap=0):return a[0]<b[2]+gap and a[2]>b[0]-gap and a[1]<b[3]+gap and a[3]>b[1]-gap

def boxes(t):
    return [(c['origin_um'][0],c['origin_um'][1],c['origin_um'][0]+c['outline_um'][0],c['origin_um'][1]+c['outline_um'][1]) for c in t.get('hard_cores',[])]

def segment_clear(a,b,blocks):
    # Exact axis-aligned intersection: a thin macro cannot disappear between samples.
    if a[0]!=b[0] and a[1]!=b[1]:raise ValueError('routing visibility edge must be rectilinear')
    for x0,y0,x1,y1 in blocks:
        if a[1]==b[1] and y0<a[1]<y1 and max(min(a[0],b[0]),x0)<min(max(a[0],b[0]),x1):return False
        if a[0]==b[0] and x0<a[0]<x1 and max(min(a[1],b[1]),y0)<min(max(a[1],b[1]),y1):return False
    return True


def manhattan(points,blocks):
    """Shortest obstacle-free rectilinear route, not a diagonal through a macro wall."""
    out=[tuple(points[0])]
    # Permit the real 0.096um pin inset at the very edge, but no through-core routing.
    wireblocks=[(x0+.2,y0+.2,x1-.2,y1-.2) for x0,y0,x1,y1 in blocks]
    for end in points[1:]:
        start=out[-1];end=tuple(end)
        xs=sorted(set([start[0],end[0]]+[v for b in blocks for v in (b[0]-2,b[2]+2)]))
        ys=sorted(set([start[1],end[1]]+[v for b in blocks for v in (b[1]-2,b[3]+2)]))
        legal={(i,j) for i,x in enumerate(xs) for j,y in enumerate(ys) if not any(inside((x,y),b) for b in wireblocks)}
        begin=(xs.index(start[0]),ys.index(start[1]));finish=(xs.index(end[0]),ys.index(end[1]))
        if begin not in legal or finish not in legal:raise ValueError(f'endpoint inside a hard core: {start} -> {end}')
        heap=[(0,begin)];distance={begin:0};pred={}
        while heap:
            d,n=heapq.heappop(heap)
            if d!=distance[n]:continue
            if n==finish:break
            i,j=n
            for nxt in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                if nxt not in legal:continue
                aa=(xs[i],ys[j]);bb=(xs[nxt[0]],ys[nxt[1]])
                if not segment_clear(aa,bb,wireblocks):continue
                nd=d+abs(aa[0]-bb[0])+abs(aa[1]-bb[1])
                if nd<distance.get(nxt,1e99):distance[nxt]=nd;pred[nxt]=n;heapq.heappush(heap,(nd,nxt))
        if finish not in distance:raise ValueError(f'no core-free route: {start} -> {end}')
        path=[];cur=finish
        while cur!=begin:path.append((xs[cur[0]],ys[cur[1]]));cur=pred[cur]
        out.extend(reversed(path))
    return [p for i,p in enumerate(out) if not i or p!=out[i-1]]


def fabric_homes(t,ls,plan_dir):
    homes={}
    for leaf in ls:
        if not leaf['module'].startswith('qfd_c_xstn'):continue
        inst=physical_name(leaf['inst']);suffix=inst[len('u_xstn'):];core='u_t'+suffix
        pin=core_pin(t,core,'tap',plan_dir);hc=next((h for h in t.get('hard_cores',[]) if h['inst']==core),None)
        if pin is None or hc is None:continue
        x,y=pin;x0,y0=hc['origin_um'];w,h=hc['outline_um'];faces=[(abs(x-x0),'W'),(abs(x-x0-w),'E'),(abs(y-y0),'S'),(abs(y-y0-h),'N')];face=min(faces)[1]
        x += -30 if face=='W' else 30 if face=='E' else 0
        y += -30 if face=='S' else 30 if face=='N' else 0
        homes[leaf['inst']]=dict(inst=leaf['inst'],module=leaf['module'],center_um=[x,y],box_um=[x-20,y-20,x+20,y+20],tap_core=core,reason='actual source fabric beside its actual core tap; 40x40 soft region, not a macro/view')
    return homes


def at(points,frac):
    dist=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:])];need=sum(dist)*frac
    for a,b,d in zip(points,points[1:],dist):
        if need<=d:return (a[0]+(b[0]-a[0])*need/d,a[1]+(b[1]-a[1])*need/d) if d else a
        need-=d
    return points[-1]


def bank_shape(bits,face):
    cols=min(bits,36 if face in ('N','S') else 2)
    return cols,cols*PITCH_X,math.ceil(bits/cols)*CELL_H


def pack(target,bits,face,outline,blocks,used):
    cols,bw,bh=bank_shape(bits,face);w,h=outline
    cx,cy=target
    # Deterministic grid search, always preserving a real placement envelope and core halos.
    for radius in range(0,401,4):
        offsets=[(0,0)] if not radius else [(sx*radius,sy*j) for j in range(-radius,radius+1,4) for sx,sy in ((1,1),(-1,1),(1,-1),(-1,-1))]+[(sx*j,sy*radius) for j in range(-radius,radius+1,4) for sx,sy in ((1,1),(-1,1),(1,-1),(-1,-1))]
        for dx,dy in offsets:
            x=round((cx+dx-bw/2-MARGIN)/.054)*.054+MARGIN;y=round((cy+dy-bh/2-MARGIN)/CELL_H)*CELL_H+MARGIN
            b=(x,y,x+bw,y+bh)
            if x<MARGIN or y<MARGIN or b[2]>w-MARGIN or b[3]>h-MARGIN:continue
            if any(overlap(b,z,2.0) for z in blocks) or any(overlap(b,z,1.08) for z in used):continue
            used.append(b)
            return dict(box_um=list(b),columns=cols,bits=bits,cell_size_um=[CELL_W,CELL_H],pitch_um=[PITCH_X,CELL_H],target_um=list(target),movement_um=abs(x+bw/2-cx)+abs(y+bh/2-cy))
    raise ValueError(f'no legal {bits}-FF bank near {target}')


def leafs(txt):
    return [dict(path=m[1],module=m[2],inst=m[3],ports=dict(PIN.findall(m[4]))) for m in LEAF.finditer(txt)]

def wire(expr):
    m=re.fullmatch(r'\s*(\w+)(?:\[.*\])?\s*',expr)
    return m[1] if m else None


def endpoints(txt,name,expr,out,ls,t,plan_dir,homes):
    a=wire(expr);b=wire(out);source=[];target=[]
    for leaf in ls:
        inst=physical_name(leaf['inst'])
        for pn,con in leaf['ports'].items():
            p=core_pin(t,inst,pn,plan_dir)
            if p is None and leaf['inst'] in homes:p=tuple(homes[leaf['inst']]['center_um'])
            if p is None:continue
            if a and re.search(r'\b'+re.escape(a)+r'\b',con):source.append(p)
            if b and re.search(r'\b'+re.escape(b)+r'\b',con):target.append(p)
    if len(set(source))==1 and len(set(target))==1:return [source[0],target[0]]
    return None


def interface_routes(raw,tn,t,ls,homes,plan_dir,txt):
    """Physical lower bounds; source/capture pad redistribution must keep the full lane calendar exact."""
    P=schema.Plan(raw);pins=gen_phys.type_pins(P,tn);by={}
    for name,bit,_layer,x,y,_face in pins:by.setdefault(name,[]).append((x,y))
    declared={e['conn'][4:]:len(e.get('regs_um',[])) for e in t.get('internal_stations',[]) if e.get('conn','').startswith('bus:')};result=[]
    actual={m[3][len('u_lpad_'):]:int(m[2]) for m in DLY.finditer(txt) if m[3].startswith('u_lpad_')}
    for b in t.get('buses',[]):
        if b['name'] not in by or '.' not in b.get('leaf',''):continue
        inst,pin=b['leaf'].rsplit('.',1);end=core_pin(t,inst,pin,plan_dir);soft=None
        if end is None:
            soft=next((q for key,q in homes.items() if physical_name(key)==inst),None)
            if soft:end=soft['center_um']
        if end is None:continue
        row=by[b['name']];face=(sum(x for x,y in row)/len(row),sum(y for x,y in row)/len(row))
        try:
            path=manhattan([face,end],boxes(t));length=sum(abs(a[0]-c[0])+abs(a[1]-c[1]) for a,c in zip(path,path[1:]));minimum=max(0,math.ceil(length/405)-1)
            budget=declared.get(b['name'],0);have=actual.get(b['name'],0) if b['dir']=='in' else 0
            result.append(dict(bus=b['name'],direction=b['dir'],leaf=b['leaf'],centroid_route_um=length,minimum_stations_lower_bound=minimum,declared_stations=budget,actual_input_pad_depth=have,
                additional_plan_cycles_lower_bound=max(0,minimum-budget),existing_pad_capacity_shortfall=max(0,minimum-have),
                interpretation='data/epoch relay distribution must be re-bound and re-priced; no source-stage insertion performed',face_um=list(face),leaf_um=list(end),path_um=path,minimum_station_targets_um=[list(at(path if b['dir']=='in' else list(reversed(path)),(i+1)/(minimum+1))) for i in range(minimum)]))
        except ValueError as e:result.append(dict(bus=b['name'],error=str(e)))
    return result


def clock_inventory(raw,tn,txt,banks):
    original=schema.Plan(raw);current=len(schema.tap_grid(original,tn));dedicated=len(schema.core_taps(original,tn))
    rows=[[(b['box_um'][0]+b['box_um'][2])/2,(b['box_um'][1]+b['box_um'][3])/2,b['bits']] for b in banks]
    relay=[];missing=[]
    for name,rest in re.findall(r'\bot_dp_r(?:relay|gate)\s+(\w+)\s*\(([^\n]+)',txt):
        m=re.search(r'@\s*\(([0-9.]+),\s*([0-9.]+)\)',rest)
        if m:relay.append([float(m[1]),float(m[2]),1])
        else:missing.append(name)
    candidate=copy.deepcopy(raw);t=candidate['partition_types'][tn];ck=t.setdefault('clock',{});ck.update(tap_mode='density',tap_max_sinks=1000,tap_target_sinks=800,tap_radius_um=160,sink_sites_um=rows+relay)
    # Current CB plans do not mark internal stations per-bit; avoid counting any future per-bit stage twice.
    for e in t.get('internal_stations',[]):e.pop('bit_route',None)
    P=schema.Plan(candidate);taps._CACHE.clear()
    try:
        density=taps.density_taps(P,tn);density_report=dict(ports=[dict(port=n,x=x,y=y,planned_sinks=k,max_center_distance_um=r) for n,x,y,k,r in density],entries=len(density),max_sinks=max(q[3] for q in density),max_center_distance_um=max(q[4] for q in density))
    except ValueError as e:density_report=dict(error=str(e),entries=None)
    return dict(scope='PARTIAL actual delay-bank FF + expected face/FT + located reset/START cells; other mapped soft registers still required',current_emitted_grid_entries=current,current_dedicated_core_clock_entries=dedicated,actual_delay_ff=sum(b['bits'] for b in banks),located_reset_start_ff=len(relay),unlocated_reset_start_cells=missing,
        expected_face_ft_sinks=len(taps.planned_sinks(original,tn)),candidate_partial_density=density_report,full_clock_verdict='BLOCKED until actual fabric/control mapped FFs and real hard-core clock contracts are present')


def tcl_for(banks):
    """FIRM only existing mapped registers. Missing/merged state fails the hook instead of inventing cells."""
    if any(b.get('member_instances') for b in banks):
        return '# Actual W1 landing pads require the mapped FF alias hook, not source-width guesses.\nerror {Use cb16_mapped_sites.py place_actual_mapped.tcl for grouped W1 landing pads}\n'
    out=['# SOURCE inventory preparation: reconcile optimized bits against cb16_mapped_inventory before use.',
         '# Existing delay-register placement only: NO RTL insertion and NO changed stage count.',
         'set qc_pad_found 0; set qc_pad_missing {}; set qc_pad_ambiguous {}; array set qc_pad_seen {}',
         'set qc_pad_block [ord::get_db_block]; set qc_pad_dbu [$qc_pad_block getDbUnitsPerMicron]',
         'array set qc_pad_bank {}']
    for bank in banks:
        x0,y0,_,_=bank['box_um'];out.append(f"set qc_pad_bank({bank['instance']},{bank['stage']}) {{{x0:.6f} {y0:.6f} {bank['columns']} {bank['bits']}}}")
    out += [r'''foreach qc_i [$qc_pad_block getInsts] {
  if {![string match "*DFF*" [[$qc_i getMaster] getName]]} continue
  foreach qc_it [$qc_i getITerms] {
    if {[$qc_it getIoType] ne "OUTPUT"} continue
    set qc_n [$qc_it getNet]; if {$qc_n eq "NULL"} continue
    set qc_nm [string map {\\ {}} [$qc_n getName]]
    if {![regexp {([A-Za-z0-9_]+)[./]r\[([0-9]+)\]\[([0-9]+)\]} $qc_nm -> qc_inst qc_stage qc_bit]} continue
    set qc_bank "$qc_inst,$qc_stage"; set qc_key "$qc_bank,$qc_bit"
    if {![info exists qc_pad_bank($qc_bank)]} continue
    if {[info exists qc_pad_seen($qc_key)]} { lappend qc_pad_ambiguous $qc_key; continue }
    lassign $qc_pad_bank($qc_bank) qc_x0 qc_y0 qc_cols qc_bits
    if {$qc_bit >= $qc_bits} {error "delay bit exceeds actual declared width: $qc_key"}
    set qc_pad_seen($qc_key) [$qc_i getName]
    set qc_x [expr {$qc_x0+($qc_bit%$qc_cols)*2.16}]
    set qc_y [expr {$qc_y0+($qc_bit/$qc_cols)*0.27}]
    set qc_got [ff_put_near $qc_i [expr {round($qc_x*$qc_pad_dbu)}] [expr {round($qc_y*$qc_pad_dbu)}]]
    if {$qc_got eq ""} { lappend qc_pad_missing $qc_key; continue }
    incr qc_pad_found
  }
}
set qc_pad_expected 0
foreach qc_bank [array names qc_pad_bank] {
  set qc_bits [lindex $qc_pad_bank($qc_bank) 3]; incr qc_pad_expected $qc_bits
  for {set qc_bit 0} {$qc_bit<$qc_bits} {incr qc_bit} {
    set qc_key "$qc_bank,$qc_bit"; if {![info exists qc_pad_seen($qc_key)]} {lappend qc_pad_missing $qc_key}
  }
}
puts "QC_ACTUAL_PAD_SITES $qc_pad_found EXPECTED $qc_pad_expected MISSING [llength $qc_pad_missing] AMBIGUOUS [llength $qc_pad_ambiguous]"
if {[llength $qc_pad_missing] || [llength $qc_pad_ambiguous]} {error "actual CB16 pad FF site mapping failed: missing=[lrange $qc_pad_missing 0 9] ambiguous=[lrange $qc_pad_ambiguous 0 9]"}
''']
    return '\n'.join(out)+'\n'


def build(raw,tn,txt,plan_dir):
    t=raw['partition_types'][tn];ls=leafs(txt);homes=fabric_homes(t,ls,plan_dir);used=[q['box_um'] for q in homes.values()];bs=boxes(t);banks=[];unplaced=[];chains=[]
    stations={e['conn'][4:]:e for e in t.get('internal_stations',[]) if e.get('conn','').startswith('bus:')}
    buses={b['name']:b for b in t.get('buses',[])}
    # Fresh landing alignment emits payload-only W1 u_pd instances. Group actual equal-depth bits
    # into physical banks; member mapping preserves each real instance and never invents epoch FF.
    matches=list(DLY.finditer(txt));pd_groups={}
    for m in matches:
        if int(m[1])!=1 or not m[3].startswith('u_pd'):continue
        con=dict(PIN.findall(m[4]));src=wire(con.get('d',''));bus=src[:-2] if src and src.endswith('_q') else None
        if bus not in buses:continue
        pd_groups.setdefault((bus,int(m[2])),[]).append(m)
    grouped={m[3] for members in pd_groups.values() for m in members};items=[]
    for m in matches:
        if m[3] not in grouped:items.append((int(m[1]),int(m[2]),m[3],dict(PIN.findall(m[4])),None))
    for (bus,depth),members in pd_groups.items():
        items.append((len(members),depth,'actual_pd_'+bus+'_d'+str(depth),dict(bus=bus),[m[3] for m in members]))
    for W,D,name,con,members in items:
        face='W';pts=None;basis=''
        if members:
            bn=con['bus'];bus=buses[bn];leaf,port=bus['leaf'].rsplit('.',1);end=core_pin(t,leaf,port,plan_dir)
            if end is None:
                home=next((q for key,q in homes.items() if physical_name(key)==leaf),None)
                if home:end=home['center_um']
            if end is not None:
                # Existing lane padding already transports this bus to its leaf. Extra alignment
                # state is local to that leaf; each real W1 delay is represented exactly once.
                pts=[end,end];face=bus.get('face','W');basis='actual payload-only W1 landing pads beside sink; no inferred epoch'
        if name.startswith('u_lpad_'):
            bn=name[len('u_lpad_'):];e=stations.get(bn);b=buses.get(bn)
            if e:
                end=e['to_um'];leaf,port=b['leaf'].rsplit('.',1);end=core_pin(t,leaf,port,plan_dir) or end
                pts=[e['from_um'],end];face=b.get('face','W');basis='actual-delay + actual core endpoint (candidate pin override when selected)'
            elif b:
                leaf,port=b['leaf'].rsplit('.',1);end=core_pin(t,leaf,port,plan_dir)
                if end is None:
                    home=next((q for key,q in homes.items() if physical_name(key)==leaf),None)
                    if home:end=home['center_um']
                pins=[(x,y) for n,bit,layer,x,y,f in gen_phys.type_pins(schema.Plan(raw),tn) if n==bn]
                if end is not None and pins:
                    start=(sum(x for x,y in pins)/len(pins),sum(y for x,y in pins)/len(pins));pts=[start,end];face=b.get('face','W');basis='actual whole-port phase delay + actual fabric soft region'
        if pts is None:
            pts=endpoints(txt,name,con.get('d',''),con.get('q',''),ls,t,plan_dir,homes);basis='actual-delay + actual hard-core port centroids'
        if pts is None:
            unplaced.append(dict(instance=name,W=W,D=D,ff=W*D,reason='no exact source/capture placement anchor'));continue
        try:route=manhattan(pts,bs)
        except ValueError as e:unplaced.append(dict(instance=name,W=W,D=D,ff=W*D,reason=str(e),endpoints=pts));continue
        start=len(banks)
        for stage in range(D):
            target=at(route,(stage+1)/(D+1));bank=pack(target,W,face,t['outline_um'],bs,used);bank.update(instance=name,stage=stage,depth=D,basis=basis);
            if members:bank['member_instances']=members
            banks.append(bank)
        here=banks[start:];centers=[(sum(z['box_um'][::2])/2,sum(z['box_um'][1::2])/2) for z in here]
        hops=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip([route[0]]+centers,centers+[route[-1]])]
        route_length=sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(route,route[1:]));minimum=max(0,math.ceil(route_length/405)-1)
        chains.append(dict(instance=name,width=W,depth=D,registers=W*D,centre_max_hop_um=max(hops),shortest_route_um=route_length,minimum_stages_at405=minimum,additional_stages_lower_bound=max(0,minimum-D),basis=basis))
    hard_missing=[dict(inst=c['inst'],module=c.get('module'),missing=[k for k in ('lef','lib') if not c.get(k)]) for c in t.get('hard_cores',[]) if not c.get('lef') or not c.get('lib')]
    routes=interface_routes(raw,tn,t,ls,homes,plan_dir,txt)
    other_soft=[dict(inst=l['inst'],module=l['module']) for l in ls if not physical_name(l['inst']).startswith('u_t')]
    # Full inventory must eventually come from mapped cells, not inferred core sink counts.
    report=dict(type=tn,scope='ACTUAL_DELAY_BANK_PREPARATION_ONLY',banks=len(banks),placed_delay_ff=sum(b['bits'] for b in banks),unplaced_delay_ff=sum(z['ff'] for z in unplaced),unplaced=unplaced,chains=chains,hard_view_blockers=hard_missing,other_soft_modules_need_mapped_inventory=other_soft,fabric_homes=list(homes.values()),interface_routes=routes,clock_inventory=clock_inventory(raw,tn,txt,banks),
        cells_area_um2=sum(b['bits'] for b in banks)*CELL_W*CELL_H,new_pipeline_cycles=0,
        release_capacity_verdict='BLOCKED' if hard_missing or unplaced or other_soft else 'NOT_RUN',
        g2='NOT_RUN: actual hard-view ABI and full mapped soft-register inventory required; no skeleton substitute')
    return banks,report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--bound',type=Path,required=True);p.add_argument('--types');p.add_argument('--pin-overrides',type=Path);p.add_argument('--out',type=Path,required=True);q=p.parse_args();q.out.mkdir(parents=True,exist_ok=False)
    if q.pin_overrides:
        global PIN_OVERRIDES
        PIN_OVERRIDES=json.loads(q.pin_overrides.read_text())
    raw=json.loads(q.plan.read_text());report=json.loads((q.bound/'bind_report.json').read_text());types=q.types.split(',') if q.types else [k for k in raw['partition_types'] if k.startswith(('cbf_','cbn_','cbx_'))];out=[]
    for tn in types:
        if tn not in report['types']:raise ValueError(f'actual bound type missing: {tn}')
        module=report['types'][tn]['module'];txt=(q.bound/'rtl'/f'{module}.sv').read_text();banks,r=build(raw,tn,txt,q.plan.parent);d=q.out/tn;d.mkdir();(d/'banks.json').write_text(json.dumps(banks,indent=1)+'\n');(d/'report.json').write_text(json.dumps(r,indent=1)+'\n');(d/'place_actual_pads.tcl').write_text(tcl_for(banks));out.append(r)
    (q.out/'summary.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps([dict(type=r['type'],placed_delay_ff=r['placed_delay_ff'],unplaced_delay_ff=r['unplaced_delay_ff'],hard_view_blockers=len(r['hard_view_blockers'])) for r in out]))
if __name__=='__main__':main()
