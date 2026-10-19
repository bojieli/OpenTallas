#!/usr/bin/env python3
"""MODEL ONLY: separated analytical M4/M5 port leads; emits no macro views.

The caller supplies source-pinned boundary anchors, PG, original OBS and
calibration. Geometry uses integer nm. This is a bounded access architecture,
not a replacement for native DRC, parent escape or macro-array timing.
"""
import hashlib
import json
import math
import sys


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def rectangle(layer, box, net, role):
    assert box[2] > box[0] and box[3] > box[1], box
    return dict(layer=layer, rect_nm=box, net=net, role=role)


def distance(a, b):
    """Axis gap in nm; zero indicates overlap or touching on that axis."""
    return [max(a[i] - b[i+2], b[i] - a[i+2], 0) for i in (0, 1)]


def plan(data):
    # Real source pitch 96nm, target pitch192nm, width24nm, VIA45 source
    # enclosure M4 +/-23x12, M5 +/-12x23, cut +/-12x12. No abstract via box.
    rules=data['rules']
    assert rules['width_nm']==24 and rules['source_pitch_nm']==96
    assert rules['target_pitch_nm']==192 and rules['via_cut_spacing_nm']==34
    anchors=data['anchors']; n=max(sum(a['face']==f for a in anchors) for f in ('W','E'))
    # All vertical columns are 96nm apart; nearest column is228nm beyond
    # old edge. The outermost column is204nm from the new edge. This keeps
    # the original M4 pad/PG/OBS and reserves end-cap and cut spacing.
    channel=432+(n-1)*96
    assert channel%48==0
    old_w,old_h=data['old_outline_nm']
    width=old_w+2*channel
    height=data['target_height_nm']
    assert width%48==24 and height%48==24
    paths=[]; shapes=[]; vias=[]; counters={'W':0,'E':0}
    for a in anchors:
        face=a['face']; k=counters[face]; counters[face]+=1
        old_x,old_y=a['old_center_nm']
        assert old_y==780+k*96, (a,k)
        new_y=780+k*192
        core_x=old_x+channel
        new_x=12 if face=='W' else width-12
        t=228+(n-1-k)*96
        column=channel-t if face=='W' else channel+old_w+t
        assert column%48==12
        endpoints=[[core_x,old_y],[column,old_y],[column,new_y],[new_x,new_y]]
        net=a['pin']; own=[]; own_vias=[]
        if k==0:
            # Zero vertical travel: no coincident stacked cuts or tiny M5
            # sliver. One M4 wire joins inherited and outer contacts.
            own.append(rectangle('M4',[min(core_x,new_x)-12,old_y-12,
                                      max(core_x,new_x)+12,old_y+12],net,'horizontal_zero_jog'))
        else:
            for x0,x1,y,role in ((core_x,column,old_y,'source_horizontal'),
                                  (column,new_x,new_y,'terminal_horizontal')):
                left=min(x0,x1)-12;right=max(x0,x1)+12
                left=min(left,column-23);right=max(right,column+23)
                own.append(rectangle('M4',[left,y-12,right,y+12],net,role))
            own.append(rectangle('M5',[column-12,old_y-23,column+12,new_y+23],net,'vertical_column'))
            for y in (old_y,new_y):
                own_vias.append(dict(name='VIA45',net=net,center_nm=[column,y],
                    cut_rect_nm=[column-12,y-12,column+12,y+12],
                    m4_rect_nm=[column-23,y-12,column+23,y+12],
                    m5_rect_nm=[column-12,y-23,column+12,y+23]))
        layer_lengths={layer:sum((s['rect_nm'][2]-s['rect_nm'][0]) *
                                (s['rect_nm'][3]-s['rect_nm'][1])/24/1000
                                for s in own if s['layer']==layer) for layer in ('M4','M5')}
        # Area/width counts complete enclosure metal, not merely centerlines.
        cap=sum(layer_lengths[l]*rules['rc'][l]['c_ff_per_um'] for l in layer_lengths)
        resistance=sum(layer_lengths[l]*rules['rc'][l]['r_kohm_per_um'] for l in layer_lengths)
        resistance+=len(own_vias)*rules['via_r_kohm']
        paths.append(dict(pin=net,face=face,index=k,kind=a['kind'],
            preserved_anchor_nm=[core_x,old_y],terminal_nm=[new_x,new_y],
            centerline_points_nm=endpoints,layer_metal_length_um=layer_lengths,
            via_count=len(own_vias),cap_ff=cap,resistance_kohm=resistance,shapes=own,vias=own_vias))
        shapes.extend(own);vias.extend(own_vias)
    assert len(paths)==len(anchors)
    connected_paths=0
    for p in paths:
        own=p['shapes']
        edges={i:set() for i in range(len(own))}
        for i,a in enumerate(own):
            for j,b in enumerate(own):
                if i!=j and a['layer']==b['layer'] and overlap(a['rect_nm'],b['rect_nm']):
                    edges[i].add(j)
        for v in p['vias']:
            endpoints=[]
            for layer,key in (('M4','m4_rect_nm'),('M5','m5_rect_nm')):
                found=[i for i,s in enumerate(own) if s['layer']==layer and
                       all(s['rect_nm'][k]<=v[key][k] for k in (0,1)) and
                       all(s['rect_nm'][k]>=v[key][k] for k in (2,3))]
                assert found,(p['pin'],layer,v)
                endpoints.extend(found)
            for i in endpoints:edges[i].update(set(endpoints)-{i})
        reached={0}; pending=[0]
        while pending:
            for j in edges[pending.pop()]-reached:reached.add(j);pending.append(j)
        assert len(reached)==len(own),p['pin']
        for x,y in (p['preserved_anchor_nm'],p['terminal_nm']):
            pad=[x-12,y-12,x+12,y+12]
            assert any(s['layer']=='M4' and overlap(s['rect_nm'],pad) for s in own)
        connected_paths+=1
    pg=[dict(p,rect_nm=[p['rect_nm'][0]+channel,p['rect_nm'][1],
                       p['rect_nm'][2]+channel,p['rect_nm'][3]]) for p in data['pg']]
    old_obs=[dict(o,rect_nm=[o['rect_nm'][0]+channel,o['rect_nm'][1],
                            o['rect_nm'][2]+channel,o['rect_nm'][3]]) for o in data['obs']]
    errors=[]; min_gaps={'M4':10**9,'M5':10**9,'V4':10**9}
    # Analytical physical checks cover every lead rectangle and native via
    # enclosure. Same-net intentional intersections are retained.
    for i,s in enumerate(shapes):
        r=s['rect_nm']; layer=s['layer']
        if not(0<=r[0]<r[2]<=width and 0<=r[1]<r[3]<=height): errors.append(['outline',s])
        if (r[2]-r[0])*(r[3]-r[1])<rules['minimum_area_nm2']:errors.append(['minimum_area',s])
        for o in old_obs:
            if layer==o['layer'] and overlap(r,o['rect_nm']):errors.append(['old_OBS',s,o])
        for p in pg:
            if layer==p['layer']:
                gaps=distance(r,p['rect_nm'])
                # A wide0.096um PG rail requires72nm per native spacing table.
                if max(gaps)<72:errors.append(['PG_spacing',s,p,gaps])
        for q in shapes[i+1:]:
            if q['net']==s['net'] or q['layer']!=layer:continue
            gaps=distance(r,q['rect_nm']); g=max(gaps)
            min_gaps[layer]=min(min_gaps[layer],g)
            #40nm is stronger than ordinary24nm spacing and includes the
            #native EOL/corner scalar spacing here; full deck is still native.
            if g<40:errors.append(['cross_net_metal_spacing',s,q,gaps])
    for i,v in enumerate(vias):
        for q in vias[i+1:]:
            if v['net']==q['net']:continue
            gaps=distance(v['cut_rect_nm'],q['cut_rect_nm']); g=max(gaps)
            min_gaps['V4']=min(min_gaps['V4'],g)
            if g<rules['via_cut_spacing_nm']: errors.append(['cross_net_cut_spacing',v,q,gaps])
    # New parent-visible OBS adds reservations; it never removes original
    # obstructions. M5 channels are blocked from parent PG/signal use. Original
    # PG pins remain inside the original array box at their exact dimensions.
    proposed_obs=[dict(layer=l,rect_nm=[0,0,width,height]) for l in ('M1','M2','M3')]
    proposed_obs.append(dict(layer='M4',rect_nm=[72,0,width-72,height]))
    proposed_obs.extend([dict(layer='M5',rect_nm=[72,0,channel,height]),
                          dict(layer='M5',rect_nm=[channel+old_w,0,width-72,height])])
    clocks=[p for p in paths if p['kind']=='clock']; nonclocks=[p for p in paths if p['kind']!='clock']
    assert clocks
    timing={}
    for corner,cal in data['calibration']['corners'].items():
        b=data['timing'][corner]['base']
        driver=max(cal['inv4_r_kohm'],b['out_r_kohm'])
        def delay(p,load):
            # Rtotal*(Ctotal+load)+Rdriver*Ctotal upper-bounds every
            #positive-resistance RC-tree Elmore sum represented by this
            #platform wire/via model. No0.38 lumped shortcut or free load.
            return p['resistance_kohm']*(p['cap_ff']+load)+driver*p['cap_ff']
        clk=max(delay(p,b['clk_cap_ff']) for p in clocks)
        inp=max(delay(p,b['pin_cap_ff']) for p in nonclocks if p['kind']!='data_out')
        out_by_load={str(load):max(delay(p,load) for p in nonclocks if p['kind']=='data_out')
                     for load in (.72,2.88,11.52,23.04,46.08)}
        cap_sum=sum(p['cap_ff'] for p in nonclocks)
        timing[corner]=dict(clock_lead_delay_upper_ps=clk,input_lead_delay_upper_ps=inp,
            output_lead_delay_upper_ps_by_load_ff=out_by_load,
            max_cq_ps_by_load_ff={load:b['clk_to_q_ps']+b['out_r_kohm']*(float(load)-.72)+clk+d
                                  for load,d in out_by_load.items()},
            min_cq_ps_lower_bound=b['clk_to_q_ps'],added_min_cq_lower_bound_ps=0,
            setup_required_upper_ps=b['setup_ps']+clk+inp,
            hold_required_upper_ps=b['hold_ps']+clk,
            min_period_upper_ps=b['min_period_ps']+2*(clk+inp),
            min_pulse_upper_ps=b['min_pulse_ps']+2*clk,
            output_slew_intrinsic_upper_ps=b['out_slew_intrinsic_ps']+2*max(out_by_load.values()),
            max_output_r_kohm=b['out_r_kohm']+max(p['resistance_kohm'] for p in nonclocks if p['kind']=='data_out'),
            clock_pin_cap_ff_by_pin={p['pin']:b['clk_cap_ff']+p['cap_ff'] for p in clocks},
            nonclock_pin_cap_ff_by_pin={p['pin']:b['pin_cap_ff']+p['cap_ff'] for p in nonclocks},
            read_energy_fj=b['read_energy_fj']+cap_sum*b['voltage']**2,
            write_energy_fj=b['write_energy_fj']+cap_sum*b['voltage']**2,
            clock_access_energy_fj=sum(p['cap_ff'] for p in clocks)*b['voltage']**2,
            leakage_nw=b['leakage_nw'])
    return dict(schema='opentallas.analytical-port-access-channel.v1',
        status='MODEL_ONLY_PENDING_ROOT_REVIEW_NO_GENERATION',name=data['name'],
        old_outline_nm=[old_w,old_h],outline_nm=[width,height],core_offset_nm=[channel,0],
        side_channel_width_nm=channel,macro_area_um2=width*height/1e6,
        core_geometry=data['core_geometry'],paths=paths,pg_rectangles=pg,
        preserved_obstruction_rectangles=old_obs,proposed_obstruction_rectangles=proposed_obs,
        proof=dict(pin_count=len(paths),path_count=len(paths),via_count=len(vias),
            source_to_terminal_connected_paths=connected_paths,
            geometry_error_count=len(errors),errors=errors,minimum_cross_net_axis_gaps_nm=min_gaps,
            same_layer_spacing_scalar_checked_nm=40,wide_pg_spacing_checked_nm=72,
            technology_rule_deck_qualification=None,parent_external_escape_qualification=None,
            per_pin_clock_phase_qualification=None),
        timing=timing,source_provenance=data['source_provenance'],rules=rules,
        source_semantics_unchanged=data['source_semantics_unchanged'],
        cycle_change_proposed=0,native_qualification=None,parent_fit=None,
        characterized_load_range_ff=[.72,46.08],characterized_slew_range_ps=[5,320],
        hold_policy='Added FF minimum CQ is zero, not the maximum lead delay; FF input hold charges maximum clock lead. Native qualification remains open.',
        note='Via R from native setRC; via enclosure metal included in wire capacitance. No separate via-cut fringe C characterization, as in platform RC model.')


if __name__=='__main__':
    print(json.dumps(plan(json.loads(sys.argv[1])),sort_keys=True,indent=2))
