#!/usr/bin/env python3
"""One source-bound capture home. Rectangle reservation, not physical admission."""
import argparse,gzip,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_home_20261002'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inputs():
    rows=json.loads((BASE/'inputs/origins.json').read_text());d={}
    for row in rows:
        p=BASE/'inputs'/row['copy'];raw=p.read_bytes()
        if digest(p)!=row['copy_sha256']:raise ValueError('Pinned input changed '+p.name)
        if not row['source_was_gzip'] and hashlib.sha256(gzip.decompress(raw)).hexdigest()!=row['source_sha256']:raise ValueError('Snapshot differs')
        text=gzip.decompress(raw).decode();key=row['copy'].removesuffix('.gz')
        d[key]=json.loads(text) if key.endswith('.json') else text
    return d,rows

def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def snap_up(v,grid):return math.ceil(v/grid)*grid
def snap_down(v,grid):return math.floor(v/grid)*grid

def current_fields(old,frames):
    if len(old)!=2048 or {v['local_pair'] for v in old}!=set(range(2048)):raise ValueError('Full compiled inventory')
    sizes={'q_pair':frames['q_priced_outline_um'],'BF16_column_pair':frames['BF_priced_outline_um']}
    x=y=4320;rowheight=0;out=[]
    for item in old:
        w,h=[round(z*1000) for z in sizes[item['source_class']]]
        if x+w+4320>33000000:x=4320;y+=rowheight+8640;rowheight=0
        out.append(dict(item,bbox_DBU=[x,y,x+w,y+h]));x+=w+8640;rowheight=max(rowheight,h)
    return out

def build():
    d,receipts=inputs();c=d['capture.json'];frames=d['frames.json'];old=d['field.json']
    if c['control_bits']['total']!=1483 or c['physical_variant']!='exact576 FF seats; no640padding selected':raise ValueError('Wrong capture successor')
    fields=current_fields(old,frames)
    dy=max(r['bbox_DBU'][3] for r in fields)-max(r['bbox_DBU'][3] for r in old)
    boxes=[]
    for name,rows in [('field',fields),('cfg',d['cfg.json']),('bands',d['bands.json']),('services',d['services.json'])]:
        for item in rows:
            b=item['bbox_DBU']
            if name in ('cfg','bands'):b=[v+(dy if k%2 else 0) for k,v in enumerate(b)]
            boxes.append(dict(kind=name,name=item.get('name',str(item.get('local_pair'))),bbox_DBU=b))
    # Retained full selector moved out of old STORE; no deletion/reuse credit.
    selector_core_area=1.68242
    selector_h=snap_up(selector_core_area*1e12/2125440,270)
    selector=[1000000,8953200+dy,3125440,8953200+dy+selector_h];boxes.append(dict(kind='selector',name='full_selector_retained_projection',bbox_DBU=selector))
    hub=next(x['bbox_DBU'] for x in boxes if x['name']=='HUB_VM')
    collective=next(x['bbox_DBU'] for x in boxes if x['name']=='HUB_COLLECTIVE')
    tech=d['tech.lef'];m4=re.search(r'LAYER M4\b(.*?)END M4',tech,re.S)
    if not m4 or not re.search(r'DIRECTION\s+HORIZONTAL',m4[1]):raise ValueError('M4 directional identity')
    track=re.search(r'make_tracks M4[^\n]*-y_offset ([\d.]+)[^\n]*-y_pitch ([\d.]+)',d['tracks.txt'])
    offset,pitch=map(float,track.groups());lanes=64*69;halo=4320
    gross_y_um=lanes*pitch/.5
    height=snap_up(gross_y_um*1000+2*halo,270);width=324000
    x=snap_up(hub[0],54);top=snap_down(collective[1]-halo,270);home=[x,top-height,x+width,top]
    collisions=[v['name'] for v in boxes if overlap(home,v['bbox_DBU'])]
    if collisions:raise ValueError('Capture home intersects retained inventory '+str(collisions))
    if not (0<=home[0]<home[2]<=33000000 and 0<=home[1]<home[3]<=26000000):raise ValueError('Reticle')
    lo=(home[1]+halo)/1000;hi=(home[3]-halo)/1000
    tracks=max(0,math.floor((hi-offset)/pitch)-math.ceil((lo-offset)/pitch)+1)
    reserved_tracks=math.floor(tracks*.5)
    if reserved_tracks<lanes:raise ValueError('No-ready cut underreserved')
    rawslots=[];banks=[]
    for t in c['raw_record_slot_templates']:
        shard=t['shard'];w=round(t['width_um']*1000);h=round(t['height_um']*1000)
        b=[home[0]+halo,home[1]+halo,home[0]+halo+w,home[1]+halo+h]
        rawslots.append(dict(shard=shard,bbox_DBU=b,seats=t['seats'],record_bits=t['seats']*69,physical_home_selected_for_model=True,placed_on_distinct_shard_die=True))
        yy=b[1]
        for root in range(64):
            depth=6 if shard==0 and root<32 else 4;bh=depth*540
            banks.append(dict(shard=shard,local_root=root,global_root=64*shard+root,seats=depth,bbox_DBU=[b[0],yy,b[2],yy+bh],write_ports=1,no_ready=True));yy+=bh
        if yy!=b[3]:raise ValueError('Record bank template conservation')
    # Literal local source PG geometry, not borrowed from q PDN. Occupied
    # rows R0 and empty-row select INV MX have the same supply at abutment.
    lef=d['cell_LEF.json'];masters=['DFFHQNx1_ASAP7_75t_R','INVx1_ASAP7_75t_R','NAND2x1_ASAP7_75t_R']
    widths={}
    for master in masters:
        widths[master]=round(float(re.search(r'SIZE\s+([\d.]+)\s+BY',lef[master])[1])*1000)
        for supply,expected in [('VSS',(-9,9)),('VDD',(261,279))]:
            pin=re.search(r'PIN '+supply+r'\b(.*?)END '+supply,lef[master],re.S)
            rect=re.search(r'RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',pin[1])
            if tuple(round(float(rect[k])*1000) for k in (2,4))!=expected:raise ValueError('Raw PG rail phase')
    bitpitch=widths[masters[0]]+widths[masters[1]]+3*widths[masters[2]]
    if 69*bitpitch!=152766:raise ValueError('Raw template packing')
    rawPG=[]
    for slot in rawslots:
        first=slot['bbox_DBU'];last_y=first[1]+(slot['seats']-1)*540
        rawPG.append(dict(shard=slot['shard'],rows=slot['seats'],row_pitch_DBU=540,
            record_bit_pitch_DBU=bitpitch,record_fixed_row_orientation='R0',
            word_select_INV_orientation='MX',word_select_INV_origin_offset_DBU=[0,270],
            VSS_first_rail_bbox_DBU=[first[0],first[1]-9,first[2],first[1]+9],
            VDD_first_rail_bbox_DBU=[first[0],first[1]+261,first[2],first[1]+279],
            last_VDD_rail_top_DBU=last_y+279,MX_select_abuts_matching_supplies=True,
            rail_count=2*slot['seats'],rail_width_DBU=18,
            M2_upfeed_via_pitch_and_full_OBS_access=None))
    common=[home[0]+halo+152766+halo,home[1]+halo,home[2]-halo,home[3]-halo]
    common_area=(common[2]-common[0])*(common[3]-common[1])/1e12
    rawarea=sum(t['allocated_um2'] for t in c['raw_record_slot_templates'])/1e6
    common_required=c['subtotal_core_reservation_at50pct_mm2']-rawarea
    if common_area<common_required or any(overlap(common,s['bbox_DBU']) for s in rawslots):raise ValueError('Common circuit allocation')
    area=width*height/1e12;inside=(width-2*halo)*(height-2*halo)/1e12
    prior=d['budget.json'];oldcap=prior['composed_whole_area']['capture_whole_owner_proxy_mm2']
    screen=prior['composed_whole_area']['no_containment_whole_owner_on_one_die_screen_mm2']-oldcap+area
    sourcepins=c['source_cell_facts'];buf=sourcepins['BUFx4_ASAP7_75t_R']
    clock={corner:dict(c['fanout_loads'][corner],parent_BUF_A_pin_fF=buf[corner]['pins']['A']['cap_fF'],upstream_available_budget_fF=None) for corner in ('SS','FF')}
    # Region reach is a geometry fact; HUB_VM centre is not a port pin.
    centre=[(home[0]+home[2])/2,(home[1]+home[3])/2];hcentre=[(hub[0]+hub[2])/2,(hub[1]+hub[3])/2]
    vm_projection_um=sum(abs(a-b) for a,b in zip(centre,hcentre))/1000
    return dict(schema='DS_CAPTURE_HOME_1',candidate='DS4096-TP4-S58-PAR2-NP2048',source_receipts=receipts,
        capture_origin='e5629aefd71c1d0032178cf36544bc060bc05bdb',model_selected_home_DBU=home,DBU_per_um=1000,
        per_shard_raw_slots=rawslots,root_banks=banks,raw_M1_PG_overlay=rawPG,
        local_raw_M1_rail_polarity_proved=True,parent_PG_and_via_connection_qualified=False,common_circuit_reserved_bbox_DBU=common,
        common_circuit_home_shard=None,common_physical_576way_tree_must_not_span_dies_combinationally=True,
        same_envelope_reserved_per_shard_die=True,common_replication_not_selected_or_free=True,
        per_die_enclosure_mm2=area,per_die_outer_PG_ring_reservation_mm2=area-inside,
        full_owner_body_reservation_mm2=c['subtotal_core_reservation_at50pct_mm2'],
        common_logic_required_mm2=common_required,common_reserved_mm2=common_area,
        density_is_reservation_not_actual_placement=True,VM_bridge_state_logic_route_excluded=True,
        retained_selector_core_bbox_DBU=selector,selector_core_1p68242_reserved_once=True,
        distributed226_station_sites_not_available=True,known_rectangle_clearance_not_station_route_clearance=True,
        retained_field_pairs=len(fields),retained_weight_macros=8192,retained_cfg_macros=len(d['cfg.json']),
        corrected_q_BF_frames=frames,field_end_delta_DBU=dy,
        known_rectangle_collision_count=len(collisions),no_retained_instance_or_capacity_removed=True,
        inherited418_service_debit_containment_credit_mm2=0,
        arrival_cut=dict(layer='M4',direction='HORIZONTAL',cut_edge='west/east vertical edge',
            lanes=lanes,y_pitch_um=pitch,y_offset_um=offset,halfpool_fraction=.5,
            minimum_gross_edge_um=gross_y_um,enclosure_height_um=height/1000,
            gross_track_sites=tracks,halfpool_reserved_track_sites=reserved_tracks,
            actual_available_tracks_after_OBS_PG_clock_pin_via_union=None,actual_root_pin_coordinates=None),
        clock_reset=dict(source_FO8_trees=c['fanout8_tree'],source_pin_loads=clock,
            clock_reset_buffers_already_in_body_price=True,no_prior32way_tree_recharge=True,
            skew_ceiling_ps=25,slew_ceiling_ps=320,SS_uncertainty_ps=60,FF_uncertainty_ps=25,
            actual_buffer_sites_and_wire_cap=None,reset_release_recovery_removal_closed=False,
            SETN_TIEHI_cells=c['SETN_TIEHI_cells'],SETN_ties_already_in_body=True,upstream_root_source_phase=None),
        timing=dict(scalar_tree_NAND_levels=20,scalar_tree_mux_levels=10,
            one_edge_scalar_read_admitted=False,added_read_edges=None,root_delivery_added_edges=None,
            VM_region_centre_L1_projection_um=vm_projection_um,projection_is_not_pin_or_legal_route=True,
            VM_bridge_visible_latency_edges=None,actual_wholeprogram_deadline=None,
            token_delta_formula='exposed root delivery + read pipeline + formatter/home visibility + finite transport/lease waits; all missing terms unknown, not0'),
        whole_area=dict(predecessor_screen_mm2=prior['composed_whole_area']['no_containment_whole_owner_on_one_die_screen_mm2'],
            replaced_old_capture_proxy_mm2=oldcap,new_capture_enclosure_mm2=area,
            no_containment_screen_mm2=screen,remaining_to858_mm2=858-screen,
            VM_bridge_global_clock_PG_wire_remaining_mm2=None,actual_necessary_deficit_mm2=None,
            WAKE_enable_BF_selector_station_recharged=False,selector_station_cycles_per_call=226,
            selector_service_cycles_per_call=142,diecount_and_NP_unchanged=True),
        model_geometry_home_reserved=True,physical_fit_proven=False,physical_build_admitted=False,
        per_block_next_gate={'rawbank':'Arch per-shard actual M1 rail/tie/clock/reset/pin-via and feedback hold routing in reserved box',
            'read_mux_control':'Nash bind local64-bank drain and common home/finite merge ownership; Arch characterize source20NAND cone before pipeline choice',
            'full_parent':'Actual root and VM bridge routes/deadlines plus selected clock/reset PG union; no fulltoken prerequisite imposed on independent cone characterization'},
        timeout1024_FAIL_preserved=True,timeout4096_selected=False,ROM_ECC=False,new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
