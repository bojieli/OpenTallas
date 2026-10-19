"""Bounded MODEL ONLY; preserve contacts, explicitly join native-phase leads."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE / 'source'
old = json.loads((S/'model.json').read_text())
inp = json.loads((S/'input.json').read_text())
spec = importlib.util.spec_from_file_location('checker', S/'reference_checker.py')
checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)

def area(boxes):
    xs = sorted({r[k] for r in boxes for k in (0,2)})
    total = 0
    for x0,x1 in zip(xs,xs[1:]):
        intervals = sorted((r[1],r[3]) for r in boxes if r[0]<=x0 and r[2]>=x1)
        end = None
        for lo,hi in intervals:
            total += (x1-x0)*max(0,hi-max(lo,end if end is not None else lo))
            end = max(hi,end if end is not None else hi)
    return total

def overlap(a,b):
    return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])

def gaps(a,b):
    return [max(a[k]-b[k+2],b[k]-a[k+2],0) for k in (0,1)]

def build():
    m = copy.deepcopy(old)
    m['name'] += '_NATIVE_PHASE_VARIANT_MODEL'
    joins=[]
    for p in m['paths']:
        x,y=p['preserved_anchor_nm']; pad=[x-12,y-12,x+12,y+12]
        for s in p['shapes']:
            r=s['rect_nm']
            if s['layer']=='M4':
                r[1]-=9; r[3]-=9
                if s['role']!='horizontal_zero_jog':
                    col=p['vias'][0]['center_nm'][0]
                    for k in (0,2):
                        if abs(r[k]-col)==23:r[k]-=12
            else:r[:]=[r[0]-12,r[1]-9,r[2]-12,r[3]-9]
        for v in p['vias']:
            v['center_nm']=[v['center_nm'][0]-12,v['center_nm'][1]-9]
            for key in ('cut_rect_nm','m4_rect_nm','m5_rect_nm'):
                r=v[key];v[key]=[r[0]-12,r[1]-9,r[2]-12,r[3]-9]
        lead=next(s['rect_nm'] for s in p['shapes'] if s['layer']=='M4')
        contact=[max(pad[0],lead[0]),max(pad[1],lead[1]),min(pad[2],lead[2]),min(pad[3],lead[3])]
        assert contact[2]-contact[0]==24 and contact[3]-contact[1]==15
        p['shapes'].append(dict(layer='M4',rect_nm=pad,net=p['pin'],role='UNCHANGED_original_contact'))
        joins.append(dict(pin=p['pin'],original_contact_nm=pad,overlap_nm=contact,
                          added_local_tail_area_nm2=216,local_union_height_nm=33,
                          notch_step_nm=9,native_join_drc=None))
        p['terminal_nm'][1]-=9
        p['centerline_points_nm']=[[x,y],[x,y-9]]+[[q[0]-(12 if j in (1,2) else 0),q[1]-9] for j,q in enumerate(p['centerline_points_nm'])]
        lengths={l:area([s['rect_nm'] for s in p['shapes'] if s['layer']==l])/24/1000 for l in ('M4','M5')}
        p['layer_metal_length_um']=lengths
        p['cap_ff']=sum(lengths[l]*inp['rules']['rc'][l]['c_ff_per_um'] for l in lengths)
        p['resistance_kohm']=sum(lengths[l]*inp['rules']['rc'][l]['r_kohm_per_um'] for l in lengths)+p['via_count']*inp['rules']['via_r_kohm']
    m['explicit_contact_joins']=joins
    return m

def check(m):
    errors=[]; shaped=[]; vias=[]; grid=0; min_gap={l:10**9 for l in ('M4','M5','V4')}
    for p in m['paths']:
        assert p['preserved_anchor_nm']==next(q['preserved_anchor_nm'] for q in old['paths'] if q['pin']==p['pin'])
        own=p['shapes']; reached={len(own)-1}; changed=True
        edges={k:set() for k in range(len(own))}
        for j,a in enumerate(own):
            for k,b in enumerate(own):
                if a['layer']==b['layer'] and overlap(a['rect_nm'],b['rect_nm']):edges[j].add(k)
        for v in p['vias']:
            endpoints=[]
            for l,key in [('M4','m4_rect_nm'),('M5','m5_rect_nm')]:
                found=[k for k,s in enumerate(own) if s['layer']==l and checker.contains(s['rect_nm'],v[key])]
                if not found:errors.append(['VIA_ENCLOSURE',p['pin'],l])
                endpoints.extend(found)
            for j in endpoints:edges[j].update(endpoints)
            if v['center_nm'][0]%48 or (v['center_nm'][1]-3)%48:errors.append(['VIA_GRID',p['pin']])
            vias.append(v)
        while changed:
            enlarged=reached|set().union(*(edges[k] for k in reached));changed=enlarged!=reached;reached=enlarged
        if len(reached)!=len(own):errors.append(['CONTACT_DISCONNECTED',p['pin']])
        for s in own:
            r=s['rect_nm'];l=s['layer']
            if s['role']!='UNCHANGED_original_contact':
                ax=1 if l=='M4' else 0;phase=3 if l=='M4' else 0
                if ((r[ax]+r[ax+2])//2-phase)%48:errors.append(['LONG_LEAD_GRID',p['pin'],s])
                grid+=1
            if not(0<=r[0]<r[2]<=m['outline_nm'][0] and 0<=r[1]<r[3]<=m['outline_nm'][1]):errors.append(['OUTLINE',p['pin']])
            if min(r[2]-r[0],r[3]-r[1])!=24:errors.append(['RECT_WIDTH',p['pin']])
            for o in m['preserved_obstruction_rectangles']:
                if o['layer']==l and overlap(r,o['rect_nm']):errors.append(['CORE_OBS',p['pin']])
            for pg in m['pg_rectangles']:
                if pg['layer']==l and max(gaps(r,pg['rect_nm']))<72:errors.append(['PG_SPACING',p['pin']])
            shaped.append(s)
        for l in ('M4','M5'):
            ss=[s['rect_nm'] for s in own if s['layer']==l]
            # Connected patches on each layer; small retained pads join long leads.
            unseen=set(range(len(ss)))
            while unseen:
                group={unseen.pop()}; change=True
                while change:
                    add={j for j in unseen if any(overlap(ss[j],ss[k]) for k in group)}
                    change=bool(add);group|=add;unseen-=add
                if area([ss[k] for k in group])<2000:errors.append(['CONNECTED_MINAREA',p['pin'],l])
    for j,a in enumerate(shaped):
        for b in shaped[j+1:]:
            if a['layer']!=b['layer'] or a['net']==b['net']:continue
            g=max(gaps(a['rect_nm'],b['rect_nm']));l=a['layer'];min_gap[l]=min(min_gap[l],g)
            if g<48:errors.append(['CROSS_NET_SCALAR48',a['net'],b['net'],g])
    for j,a in enumerate(vias):
        for b in vias[j+1:]:
            if a['net']==b['net']:continue
            g=max(gaps(a['cut_rect_nm'],b['cut_rect_nm']));min_gap['V4']=min(min_gap['V4'],g)
            if g<34:errors.append(['CUT_SPACING34',a['net'],b['net'],g])
    assert m['pg_rectangles']==old['pg_rectangles']
    return dict(errors=errors,connected_paths=len(m['paths']),on_grid_lead_rectangles=grid,unchanged_contact_rectangles=206,
                vias=len(vias),minimum_cross_net_axis_gaps_nm=min_gap,terminal=checker.audit(m),
                local_union_native_DRC='HOLD: 33nm local union, 9nm notch; no native union-width/notch/step applicability proof')

def costs(m):
    result={}
    clocks=[p for p in m['paths'] if p['kind']=='clock']; others=[p for p in m['paths'] if p['kind']!='clock']
    for corner,cal in inp['calibration']['corners'].items():
        b=inp['timing'][corner]['base'];driver=max(cal['inv4_r_kohm'],b['out_r_kohm'])
        def delay(p,load):return p['resistance_kohm']*(p['cap_ff']+load)+driver*p['cap_ff']
        total=sum(p['cap_ff'] for p in m['paths']); clkcap=sum(b['clk_cap_ff']+p['cap_ff'] for p in clocks)
        result[corner]=dict(clock_lead_delay_upper_ps=max(delay(p,b['clk_cap_ff']) for p in clocks),
            input_lead_delay_upper_ps=max(delay(p,b['pin_cap_ff']) for p in others if p['kind']!='data_out'),
            output_lead_delay_upper_ps_by_load_ff={str(load):max(delay(p,load) for p in others if p['kind']=='data_out') for load in (.72,2.88,11.52,23.04,46.08)},
            clock_pin_cap_ff_by_pin={p['pin']:b['clk_cap_ff']+p['cap_ff'] for p in clocks},
            simultaneous_read_write_plus_clock_access_energy_fj=b['read_energy_fj']+b['write_energy_fj']+total*b['voltage']**2,
            complete_boundary_clock_driver_energy_fj=clkcap*b['voltage']**2,
            hybrid_clock_cap_ff=26*clkcap,hybrid_full_activity_energy_pj=26*(b['read_energy_fj']+b['write_energy_fj']+total*b['voltage']**2)/1000)
    return result

def pg_witnesses(m):
    records=[]
    for pg in m['pg_rectangles']:
        r=pg['rect_nm'];x=round((r[0]+r[2])/96)*48;y=round(((r[1]+r[3])/2-3)/48)*48+3
        lower=[x-23,y-12,x+23,y+12];upper=[x-12,y-42,x+12,y+42]
        records.append(dict(net=pg['net'],unchanged_rectangle_nm=r,nominal_R0_via_center_nm=[x,y],
            m4_enclosure_nm=lower,m5_minarea_landing_nm=upper,
            enclosure_inside_actual_pg=checker.contains(r,lower),
            landing_clear_of_M5_OBS=not any(o['layer']=='M5' and overlap(upper,o['rect_nm']) for o in m['proposed_obstruction_rectangles']),
            own_pin_OBS_exception=None,actual_route_and_binding=None,
            cost_included=False))
    return records

def main():
    m=build();r=check(m);assert not r['errors'],r['errors'][:5]
    assert r['terminal']['status']=='PASS',r['terminal']['errors'][:5]
    m['timing']=costs(m);m['native_qualification']=None
    m['hypothetical_PG_access']=pg_witnesses(m)
    assert all(p['enclosure_inside_actual_pg'] and p['landing_clear_of_M5_OBS'] for p in m['hypothetical_PG_access'])
    m['proof']=dict(r,native_PRL_thin_spacing_nm=24)
    # Causal geometric faults target electrical joins, grids, spacing, and OBS.
    mutants={}
    for name in ('disconnect_contact','wrong_M4_phase','wrong_M5_phase','blocked_terminal'):
        q=copy.deepcopy(m)
        if name=='disconnect_contact':q['paths'][1]['shapes'][-1]['rect_nm'][1]+=40;q['paths'][1]['shapes'][-1]['rect_nm'][3]+=40
        elif name=='wrong_M4_phase':q['paths'][1]['shapes'][0]['rect_nm'][1]+=1;q['paths'][1]['shapes'][0]['rect_nm'][3]+=1
        elif name=='wrong_M5_phase':q['paths'][1]['vias'][0]['center_nm'][0]+=1
        else:next(o for o in q['proposed_obstruction_rectangles'] if o['layer']=='M4')['rect_nm'][0]=0
        rr=check(q);mutants[name]=dict(errors=rr['errors'],terminal=rr['terminal']['status'])
        assert rr['errors'] or rr['terminal']['status']=='FAIL',name
    sources={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(S.iterdir()) if p.is_file()}
    sources['model.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    comparison=dict(status='MODEL_ONLY_HOLD',original_commit='693ac5af4',terminal_review_commit='7814bb23a',
       source_sha256=sources,original_cost=old['timing'],variant_cost=m['timing'],
       unchanged_outline_nm=m['outline_nm'],unchanged_26_bank_area_um2=26*m['macro_area_um2'],
       unchanged_pg_rectangles=44,mutants=mutants,
       native_R0_transform_scenario=dict(master_origin_nm=[0,0],core_offset_unchanged_nm=m['core_offset_nm'],
           bank_origin_pitch_nm=[86400,43200],bank_origin_pitch_mod48_nm=[0,0],
           M4_horizontal_track_phase_nm=3,M5_vertical_track_phase_nm=0,
           mirror_X_residual_M5_nm=m['outline_nm'][0]%48,
           mirror_Y_residual_M4_nm=(m['outline_nm'][1]-3)%48,
           actual_master_orientation_and_parent_tracks=None),
       rule_applicability='Tech offset/pitch supplies nominal R0 parent-track scenario only. No master ORIGIN/orientation, parent TRACKS or native RIGHTWAYONGRIDONLY interpreter receipt establishes applicability to original internal metal. Original 614 phase discrepancies remain analytical HOLD, not manufactured DRC failures.',
       native_join='206 exact original pads retained. 15nm same-layer overlap establishes abstract connectivity only; local 33nm union/9nm notch, EOL, corner, widthtable and native pin access remain HOLD.',
       pg='44 original rectangles retained; no PG added/priced. Same-net M4 PIN/OBS exception not established from supplied tech. Candidate VIA45 fit is insufficient to prove accessibility/binding. PG HOLD.',
       cost_scope='Exact rectangle-union area/24nm conservative passive RC surrogate, with original pad union counted once. Via fringe/coupling/extracted RC unavailable. No CQ minimum, silicon timing, macro internals, PG route or parent cost qualification.')
    (HERE/'variant.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
    (HERE/'comparison.json').write_text(json.dumps(comparison,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(status=comparison['status'],checks=r,TT=m['timing']['tt'],mutants={k:len(v['errors']) or v['terminal'] for k,v in mutants.items()})))

if __name__=='__main__':main()
