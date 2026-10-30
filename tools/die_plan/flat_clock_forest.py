"""Explicit native flat-clock forests; absent per-type pointer changes nothing.

The packet owns every real sequential clock pin and every declared clock root.
No CTS leaf is inferred to be a planned driver. The source never creates a port,
changes a data/reset connection or chooses a clock delay after measurement.
"""
import json
import hashlib
import math
import re
import shutil
from collections import Counter
from pathlib import Path
import core_infra as CI
from die_sta import PERIOD_PS
def tq(value):
    """A Tcl quoted word; preserve literal synthesized identifiers."""
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('[', '\\[').replace(']', '\\]') + '"'


PRIMARY = re.compile(r'clk(?:_t[0-9]+)?\Z')
ENV = {'BUFx8_ASAP7_75t_R','BUFx10_ASAP7_75t_R','BUFx12_ASAP7_75t_R',
       'BUFx12f_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx24_ASAP7_75t_R'}


def check_forwarded_roles(t, roots):
    inputs={p['name'] for p in t.get('clock',{}).get('landing_contract',{}).get('pins',[]) if p.get('kind')=='clock' and p.get('dir')=='in'}
    edges={p['port']:p for p in t.get('clock',{}).get('edge_clocks',[])}
    for root in roots:
        if PRIMARY.fullmatch(root):continue
        name=re.sub(r'\[0\]$','',root);edge=edges.get(name)
        if name not in inputs or edge is None or edge.get('period_mult',1)!=1 or edge.get('source_latency_ps') is not None:
            raise ValueError('flat clock forest: nonprimary root is not a declared833ps source-forwarded landing clock')


def finite(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)


def validate(t, packet):
    if packet.get('schema')!='opentallas.flat_clock_forest.v1':
        raise ValueError('flat clock forest: schema')
    if packet.get('module')!=t['module'] or packet.get('outline_um')!=t['outline_um']:
        raise ValueError('flat clock forest: stale module/outline')
    if packet.get('build_allowed') is not True or not packet.get('geometry_review'):
        raise ValueError('flat clock forest: unqualified/unreviewed packet')
    if not packet.get('wire_rc') or not all(finite(packet['wire_rc'].get(k)) and packet['wire_rc'][k]>0 for k in ('r_kohm_um','c_ff_um')):
        raise ValueError('flat clock forest: native per-class wire RC required')
    if not finite(packet.get('input_slew_ps')) or packet['input_slew_ps']<80:
        raise ValueError('flat clock forest: explicit80ps input-slew model required')
    if packet.get('install_stage')!='post_place_pre_cts':
        raise ValueError('flat clock forest: exact post-place cohort only')
    if t.get('hard_cores') or t.get('master_slice') or t.get('reg_spine') or t.get('clock',{}).get('branch_buffers'):
        raise ValueError('flat clock forest: incompatible macro/other clock owner')
    roots=packet['roots']; cells=packet['cells'];seen=set();sinks={};parents={};counts=Counter()
    if not roots or not cells:raise ValueError('flat clock forest: empty ownership')
    for root,r in roots.items():
        if r['kind']!=('primary' if PRIMARY.fullmatch(root) else 'forwarded'):
            raise ValueError('flat clock forest: root role')
        if len(r['xy_um'])!=2 or not all(finite(x) for x in r['xy_um']):
            raise ValueError('flat clock forest: root coordinate')
    for c in cells:
        name=c['name'];root=c['root'];p=c['placement']
        if not re.fullmatch(r'ot_flat_clk_[A-Za-z0-9_]+',name) or name in seen or root not in roots or c['master'] not in ENV:
            raise ValueError('flat clock forest: cell identity/master/root')
        seen.add(name);parents[name]=c['parent']
        if c['parent']==name or (c['parent']!='port:'+root and c['parent'] not in seen):
            raise ValueError('flat clock forest: parent order/cycle')
        if c['parent'] in seen and next(q['root'] for q in cells if q['name']==c['parent'])!=root:
            raise ValueError('flat clock forest: cross-root driver')
        for key in ('origin_um','centre_um','size_um'):
            if len(p[key])!=2 or not all(finite(x) for x in p[key]):raise ValueError('flat clock forest: placement')
        x,y=p['origin_um'];w,h=p['size_um']
        if min(x,y)<0 or min(w,h)<=0 or x+w>t['outline_um'][0] or y+h>t['outline_um'][1]:
            raise ValueError('flat clock forest: footprint outside outline')
        if any(abs(p['centre_um'][a]-p['origin_um'][a]-p['size_um'][a]/2)>1e-6 for a in (0,1)):
            raise ValueError('flat clock forest: inconsistent footprint centre')
        if p['orient'] not in ('R0','R180','MX','MY'):raise ValueError('flat clock forest: row orientation')
        for s in c.get('sinks',[]):
            if s['name'] in sinks or s.get('clock_pin')!='CLK' or not s.get('master'):
                raise ValueError('flat clock forest: duplicate/untyped sink')
            if s['source_root'] not in roots or len(s['xy_um'])!=2 or not all(finite(x) for x in s['xy_um']):
                raise ValueError('flat clock forest: stale native root/geometry')
            if roots[root]['kind']=='forwarded' and s['source_root']!=root:
                raise ValueError('flat clock forest: forwarded root stealing')
            if roots[root]['kind']=='primary' and not PRIMARY.fullmatch(s['source_root']):
                raise ValueError('flat clock forest: primary root stealing')
            if sum(abs(a-b) for a,b in zip(p['centre_um'],s['xy_um']))>220:
                raise ValueError('flat clock forest: planned driver-to-sink reach exceeds220um')
            sinks[s['name']]=(root,s);counts[root]+=1
    if not sinks:raise ValueError('flat clock forest: no native FF inventory')
    used_parents={c['parent'] for c in cells}
    if any(not c.get('sinks') and c['name'] not in used_parents for c in cells):
        raise ValueError('flat clock forest: unused planned driver')
    for i,c in enumerate(cells):
        x,y=c['placement']['origin_um'];w,h=c['placement']['size_um']
        for other in cells[:i]:
            a,b=other['placement']['origin_um'];u,v=other['placement']['size_um']
            if x<a+u-1e-8 and a<x+w-1e-8 and y<b+v-1e-8 and b<y+h-1e-8:
                raise ValueError('flat clock forest: planned cell overlap')
    for root,r in roots.items():
        if r['node'] not in seen or parents[r['node']]!='port:'+root:
            raise ValueError('flat clock forest: missing root node')
        if sum(c['parent']=='port:'+root for c in cells)!=1:
            raise ValueError('flat clock forest: one declared driver per input root')
        if r['kind']=='primary' and not 0<counts[root]<=1500:
            raise ValueError('flat clock forest: primary sink load outside1..1500')
        names={n for n,(sr,_) in sinks.items() if sr==root}
        for corner in ('TT','FF'):
            q=r['qualification'][corner];arr=q['sink_latency_ps']
            if set(arr)!=names or not all(finite(x) for x in arr.values()):
                raise ValueError('flat clock forest: incomplete per-corner sink model')
            cases=q.get('calibrated_sink_latency_ps',{})
            if set(cases)!= {'late','early'} or any(set(v)!=names or not all(finite(x) for x in v.values()) for v in cases.values()):
                raise ValueError('flat clock forest: consistent per-master calibration states required')
            window=max(max(v.values())-min(v.values()) for v in cases.values())
            if not finite(q['slew_max_ps']) or q['slew_max_ps']>80 or window>20:
                raise ValueError('flat clock forest: TT/FF calibrated window or slew FAIL')
    if any(r['kind']=='forwarded' for r in roots.values()) and not re.fullmatch(r'[0-9a-f]{64}',packet.get('native_sdc_sha256') or ''):
        raise ValueError('flat clock forest: frozen native forwarded-clock SDC required')
    check_forwarded_roles(t,roots)
    if set(packet.get('clock_periods',{}))!=set(roots) or any(abs(v-PERIOD_PS)>1e-9 for v in packet['clock_periods'].values()):
        raise ValueError('flat clock forest: actual833ps root clock contract required')
    for corner in ('TT','FF'):
        for category in ('primary','same_forwarded'):
            q=packet['related_pair_model'][corner][category]
            if not finite(q['max_ps']) or q['max_ps']>80 or q['over80']!=0:
                raise ValueError('flat clock forest: related-pair clock model FAIL')
    if any(v.get('forwarded_landing_window',{}).get('pairs',0) for v in packet['related_pair_model'].values()):
        policy=packet.get('landing_clock_contract',{})
        if policy.get('kind')!='canonical_landed_forwarded_default' or policy.get('window_ps')!=PERIOD_PS/2:
            raise ValueError('flat clock forest: explicit existing landed clock-damage contract required')
        if any(v.get('forwarded_landing_window',{}).get('max_ps',0)>policy['window_ps'] for v in packet['related_pair_model'].values()):
            raise ValueError('flat clock forest: forwarded landing clock-damage window FAIL')
    if not packet.get('model_source') or packet.get('measured_timing_used') is not False:
        raise ValueError('flat clock forest: plan model source required')
    return sinks


def emit(t, packet):
    sinks=validate(t,packet);roots=packet['roots'];cells=packet['cells']
    owner={s['name']:c['name'] for c in cells for s in c.get('sinks',[])}
    lines=['# Explicit planned forest, native inventory only; no port/data/reset edits.',
           'source /work/native_pg_binding.tcl','source /work/core_infra_impl.tcl',
           'source /work/flat_clock_forest_guard.tcl','set ::ot_flat_roots {}','set ::ot_flat_sinks {}','set ::ot_flat_cells {}']
    for root,r in roots.items():
        lines.append('dict set ::ot_flat_roots '+tq(root)+' [list '+tq(r['kind'])+' '+tq(r['node'])+' '+' '.join(map(str,r['xy_um']))+']')
    for name,(root,s) in sinks.items():
        lines.append('dict set ::ot_flat_sinks '+tq(name)+' [list '+' '.join(tq(x) for x in [root,s['source_root'],s['master'],s['clock_pin'],*s['xy_um'],owner[name]])+']')
    for c in cells:
        p=c['placement']
        lines.append('dict set ::ot_flat_cells '+tq(c['name'])+' [list '+' '.join(tq(x) for x in [c['master'],c['parent'],c['root'],*p['origin_um'],*p['centre_um'],p['orient'],*p['size_um']])+']')
    lines+=['ot_flat_native_guard','ot_ci_begin','ot_flat_input_nets',
            'if {[file exists /work/landing_exports.tcl]} {source /work/landing_exports.tcl}']
    for root in roots:lines.append('ot_ci_tree_begin '+tq(root))
    for c in cells:
        p=c['placement'];x,y=p['centre_um'];w,h=t['outline_um']
        lines.append(f'ot_ci_cell {tq(c["name"])} {tq(c["master"])} {x:.9f} {y:.9f} {{0 0 {w:.9f} {h:.9f}}}')
        lines.append('ot_ci_origin_assert '+tq(c['name'])+' '+' '.join(map(str,p['origin_um']))+' '+p['orient'])
    for c in cells:lines.append('ot_ci_tree_node '+tq(c['name'])+' '+tq(c['parent']))
    for c in cells:
        for s in c.get('sinks',[]):lines.append('ot_ci_tree_sink '+tq(c['name'])+' '+tq(s['name']+'/'+s['clock_pin']))
    lines+=['ot_ci_tree_finish','ot_ci_finish','ot_flat_graph_guard']
    return '\n'.join(lines)+'\n'


def install(P, tn, kd):
    t=P.types[tn];pointer=t.get('flat_clock_forest_file')
    if not pointer:return False
    if t.get('clock',{}).get('landing_export_form','tie')!='tie':
        raise ValueError('flat clock forest: non-tie export drivers need explicit native load modeling')
    import gen_phys
    path=Path(pointer)
    if not path.is_absolute():path=Path(P.path).parent/path
    packet=json.loads(path.read_text());body=emit(t,packet)
    declared={name for name,x,y in gen_phys.clock_pins(P,tn) if PRIMARY.fullmatch(name)}
    declared.update(e['port'] for e in t.get('clock',{}).get('edge_clocks',[]))
    if {re.sub(r'\[0\]$','',n) for n in packet['roots']}!=declared:
        raise ValueError('flat clock forest: declared input roots incomplete/extra')
    kd=Path(kd);base=Path(__file__).parent
    if any(r['kind']=='forwarded' for r in packet['roots'].values()):
        if not t.get('clock',{}).get('landing_contract') or hashlib.sha256((kd/'constraint.sdc').read_bytes()).hexdigest()!=packet['native_sdc_sha256']:
            raise ValueError('flat clock forest: native forwarded timing contract changed/missing')
    rc=(kd/'setRC_rcx.tcl').read_text()
    match=re.search(r'^set_wire_rc -clock -resistance (\S+) -capacitance (\S+)',rc,re.M)
    if not match or any(abs(float(v)-packet['wire_rc'][k])>1e-10 for v,k in zip(match.groups(),('r_kohm_um','c_ff_um'))):
        raise ValueError('flat clock forest: model RC differs from native kit clock RC')
    if (kd/'cts_post.tcl').read_text()!=(base/'cts_post.tcl').read_text():
        raise ValueError('flat clock forest: unknown POST_CTS owner')
    (kd/'flat_clock_forest.json').write_text(json.dumps(packet,indent=1)+'\n')
    (kd/'flat_clock_forest_apply.tcl').write_text(body)
    shutil.copyfile(base/'flat_clock_forest_guard.tcl',kd/'flat_clock_forest_guard.tcl')
    shutil.copyfile(base/'core_infra.tcl',kd/'core_infra_impl.tcl')
    shutil.copyfile(base.parents[1]/'physical/common_flow/native_pg_binding.tcl',kd/'native_pg_binding.tcl')
    # Replace only the known nearest-tap method: this packet explicitly owns all
    # native clock roots. Landing output clocks are exported from actual final
    # station clock nets after the complete forest is installed.
    (kd/'clock_taps.tcl').write_text('# Explicit flat forest owns the complete clock-root inventory; applied after reset checks.\n')
    with (kd/'pre_cts.tcl').open('a') as f:
        f.write('\nuplevel #0 {source /work/flat_clock_forest_apply.tcl}\n')
        f.write('set ::ot_ci_cts_plan_open 0\nsource /work/core_infra_cts.tcl\n')
    shutil.copyfile(base/'core_infra_cts.tcl',kd/'core_infra_cts.tcl')
    (kd/'cts_post.tcl').write_text('''if {[info exists ::env(OT_RESET_PAIR_FIXED)] && $::env(OT_RESET_PAIR_FIXED) eq "1"} {
  source /work/reset_pair_place.tcl
  ot_reset_pair_verify_hops [ord::get_db_block] 405
}
uplevel #0 {ot_flat_graph_guard}
source /work/pg_connect.tcl
ot_pg_connect_all flat_forest_post
ot_pg_require_bound flat_forest_post
''')
    return True


def freeze_candidate(candidate, module, placements, library_dir, geometry_review, type_spec=None):
    """Recompute both corners at exact legal sites, then compile the packet.

    `placements` comes from the plan's actual technology/obstacle legalization;
    no build-time search or measured clock delay is an input. The native guard
    independently rechecks every frozen site against the recovery checkpoint.
    """
    import copy
    import flat_clock_plan as MODEL
    if not finite(candidate.get('input_slew_ps')) or candidate['input_slew_ps']<80:
        raise ValueError('flat clock forest: stale/optimistic root input-slew model')
    if candidate.get('wire_rc',{}).get('r_kohm_um')!=MODEL.R or candidate.get('wire_rc',{}).get('c_ff_um')!=MODEL.C:
        raise ValueError('flat clock forest: candidate must use native clock class RC')
    inv,pairs=MODEL.actual_relations(candidate)
    if any(r.get('other_loads') for r in inv['roots'].values()):
        raise ValueError('flat clock forest: nonsequential native root loads require explicit ownership/modeling')
    if candidate['inventory'].get('endpoint_overlay'):
        raise ValueError('flat clock forest: proposed endpoint overlay is not a complete legal successor census')
    nodes=copy.deepcopy(candidate['nodes']);roots=candidate['root_nodes']
    check_forwarded_roles(type_spec or {},roots)
    MODEL.validate_topology(inv,nodes,roots,candidate['groups'])
    if set(placements)!={n['name'] for n in nodes}:
        raise ValueError('flat clock forest: incomplete legal driver placement')
    for n in nodes:
        p=placements[n['name']]
        if p['master']!=n['master']:raise ValueError('flat clock forest: legalization changed model master')
        if sum(abs(p['centre_um'][i]-n['xy'][i]) for i in (0,1))>2.000001:
            raise ValueError('flat clock forest: driver displacement exceeds2um; revise the plan')
        n['xy']=p['centre_um']
    metrics=MODEL.model(inv,nodes,roots,library_dir,candidate['input_slew_ps'])
    bounds=MODEL.related_pair_bounds(inv,nodes,candidate['groups'],metrics,pairs)
    for corner in bounds:
        for category in ('primary','same_forwarded'):
            bounds[corner].setdefault(category,dict(pairs=0,max_ps=0,over80=0,worst=[]))
    if any('unqualified_cross_forwarded' in m for m in bounds.values()):
        raise ValueError('flat clock forest: undeclared cross-forwarded relation')
    port_xy={p['name']:p['xy'] for p in inv['ports'].values()}
    source_root={q:r for r,record in inv['roots'].items() for q in record['sinks']}
    root_records={};cells=[]
    for root,index in roots.items():
        qualification={corner:dict(slew_max_ps=m['max_slew_ps'],sink_latency_ps={q:m['sink_arrival_ps'][q] for q in candidate['groups'][root]},calibrated_sink_latency_ps={case:{q:v[q] for q in candidate['groups'][root]} for case,v in m['calibrated_sink_latency_ps'].items()}) for corner,m in metrics.items()}
        root_records[root]=dict(kind='primary' if PRIMARY.fullmatch(root) else 'forwarded',node=nodes[index]['name'],xy_um=port_xy[root],qualification=qualification)
        def visit(i,parent):
            n=nodes[i];ss=[]
            for q in n['sinks']:
                c=inv['cells'][q]
                ss.append(dict(name=c['name'],master=c['master'],clock_pin='CLK',xy_um=c['xy'],source_root=source_root[q]))
            # Model and source packets use actual instance names, never transient ODB ids.
            for corner in qualification:
                a=qualification[corner]['sink_latency_ps']
                for q in n['sinks']:
                    a[inv['cells'][q]['name']]=a.pop(q)
                    for values in qualification[corner]['calibrated_sink_latency_ps'].values():values[inv['cells'][q]['name']]=values.pop(q)
            cells.append(dict(name=n['name'],parent=parent,root=root,master=n['master'],placement=placements[n['name']],sinks=ss))
            for kid in n['children']:visit(kid,n['name'])
        visit(index,'port:'+root)
    outline=[inv['outline'][2]-inv['outline'][0],inv['outline'][3]-inv['outline'][1]]
    packet=dict(schema='opentallas.flat_clock_forest.v1',module=module,outline_um=outline,
        roots=root_records,cells=cells,clock_periods={r:inv.get('clock_periods',{}).get(r) for r in roots},related_pair_model=bounds,build_allowed=True,input_slew_ps=candidate['input_slew_ps'],wire_rc=candidate['wire_rc'],
        install_stage='post_place_pre_cts',geometry_review=geometry_review,measured_timing_used=False,
        geometry_sha256=inv['geometry_sha256'],native_sdc_sha256=candidate.get('native_sdc_sha256'),model_source='native legal geometry + TT/FF RVT NLDM; per-master spice_cell/g021; actual planned-cell CPPR; one CORE-PDN shared droop region',
        band_policy='info: existing12.3a design target; actual TT/FF timing/signoff mandatory',
        landing_policy='existing declared forwarded landing window; no clock/SDC exception added',
        landing_clock_contract=dict(kind='canonical_landed_forwarded_default',window_ps=PERIOD_PS/2,source='die_sta_related.py time_class landed / default period/2; DATA-only SDC budget is separate'))
    validate(type_spec or dict(module=module,outline_um=outline),packet)
    return packet


def legalize_drivers(candidate, technology, max_displacement_um=2.):
    """Nearest actual row/site with ALL post-place occupants immutable.

    Geometry only. No virtual clocks, fake ports or cell movement is used to
    obtain a clock site. An occupied neighborhood fails before a physical job.
    """
    import bisect
    import core_infra_plan as PL
    u=technology['dbu'];core=technology['core'];rows=technology['rows'];by_y={}
    for row in rows:by_y.setdefault(row['rect'][1],[]).append(row)
    ys=sorted(by_y);obstacles={y:[] for y in ys};maximum_h=max(v[1] for v in technology['masters'].values())
    for obstacle in technology['obstacles']:
        x0,y0,x1,y1=obstacle['rect']
        for y in ys[bisect.bisect_right(ys,y0-maximum_h):bisect.bisect_left(ys,y1)]:
            obstacles[y].append((x0,y0,x1,y1))
    result={};moves=[];limit=max_displacement_um*u
    for n in candidate['nodes']:
        if n['master'] not in technology['masters']:raise ValueError('missing actual driver LEF footprint')
        w,h=technology['masters'][n['master']];cx,cy=[v*u for v in n['xy']];best=None
        for y in ys[bisect.bisect_left(ys,cy-limit-h/2):bisect.bisect_right(ys,cy+limit-h/2)]:
            vertical=abs(y+h/2-cy);remaining=limit-vertical
            for row in by_y[y]:
                x0,y0,x1,y1=row['rect'];sw=row['site']
                if y<core[1] or y+h>min(y1,core[3]):continue
                low=max(x0,core[0],cx-w/2-remaining);high=min(x1-w,core[2]-w,cx-w/2+remaining)
                lo=math.ceil((low-x0)/sw);hi=math.floor((high-x0)/sw)
                if hi<lo:continue
                free=[(lo,hi)]
                for a,b,c,d in obstacles[y]:
                    if y>=d or y+h<=b:continue
                    free=PL._subtract(free,math.floor((a-w-x0)/sw)+1,math.ceil((c-x0)/sw)-1)
                    if not free:break
                desired=(cx-w/2-x0)/sw
                for a,b in free:
                    for ix in {max(a,min(b,math.floor(desired))),max(a,min(b,math.ceil(desired)))}:
                        x=x0+ix*sw;distance=abs(x+w/2-cx)+vertical
                        key=(distance,vertical,y,x,row['orient'])
                        if best is None or key<best[0]:best=(key,x,y,row['orient'])
        if best is None:raise ValueError(f'no empty legal clock site within{max_displacement_um}um of {n["name"]}; revise the placement plan')
        key,x,y,orient=best
        result[n['name']]=dict(master=n['master'],origin_um=[x/u,y/u],centre_um=[(x+w/2)/u,(y+h/2)/u],size_um=[w/u,h/u],orient=orient)
        for yy in ys[bisect.bisect_right(ys,y-maximum_h):bisect.bisect_left(ys,y+h)]:obstacles[yy].append((x,y,x+w,y+h))
        moves.append(key[0]/u)
    return result,dict(cells=len(result),max_displacement_um=max(moves,default=0),overlaps=0,basis='native rows/masters; all placed instances and hard blockages immutable')


def plan_empty_driver_sites(candidate, technology, library_dir, *, search_radius_um):
    """Revise planned clock centres before build, then reprice the whole forest.

    The search never moves an existing cell. This is a new candidate, not a
    relaxation of freeze_candidate's2um final quantization bound. It remains
    unqualified until exact geometry/electrical review and freeze succeed.
    """
    import copy
    import flat_clock_plan as MODEL
    if not finite(search_radius_um) or search_radius_um<=0:
        raise ValueError('explicit finite planned-site search radius required')
    out=copy.deepcopy(candidate);inv,pairs=MODEL.actual_relations(out)
    MODEL.validate_topology(inv,out['nodes'],out['root_nodes'],out['groups'])
    places,report=legalize_drivers(out,technology,search_radius_um)
    moves=[]
    for n in out['nodes']:
        old=n['xy'];new=places[n['name']]['centre_um']
        moves.append(dict(name=n['name'],from_um=old,to_um=new,manhattan_um=sum(abs(a-b) for a,b in zip(old,new))))
        n['xy']=new
    out['model']=MODEL.model(inv,out['nodes'],out['root_nodes'],library_dir,out['input_slew_ps'])
    out['related_pair_model']=MODEL.related_pair_bounds(inv,out['nodes'],out['groups'],out['model'],pairs)
    out['planned_site_revision']=dict(report,search_radius_um=search_radius_um,moves=moves)
    out['build_allowed']=False;out['verdict']='UNQUALIFIED_REVISED_PLANNED_SITES_REVIEW_REQUIRED'
    return out,places
