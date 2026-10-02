#!/usr/bin/env python3
"""R49 widened raw banks, common box, PG/pin overlay; no new stage cuts."""
import argparse,copy,gzip,hashlib,json,re
from pathlib import Path
import dsrom_capture_home as H
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_home_r49_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inputs():
    rows=json.loads((BASE/'inputs/origins.json').read_text());out={}
    for r in rows:
        p=BASE/'inputs'/r['copy'];raw=gzip.decompress(p.read_bytes())
        if sha(p)!=r['copy_sha256'] or hashlib.sha256(raw).hexdigest()!=r['source_sha256']:raise ValueError('Frozen input drift')
        if sha(ROOT/r['source'])!=r['source_sha256']:raise ValueError('Current source drift')
        out[r['copy'].removesuffix('.gz')]=json.loads(raw)
    return out,rows

def pinpoint(body,pin):
    block=re.search(r'PIN '+pin+r'\b(.*?)END '+pin,body,re.S)
    if not block:raise ValueError('Source pin missing')
    rects=[[round(float(z)*1000) for z in x] for x in re.findall(r'RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',block[1])]
    b=max(rects,key=lambda v:(v[2]-v[0])*(v[3]-v[1]))
    return [(b[0]+b[2])/2,(b[1]+b[3])/2],b

def build():
    d,receipts=inputs();old=d['prior_home.json'];r=d['shard.json']
    if H.build()!=old:raise ValueError('Predecessor replay differs')
    if (r['context_bits'],r['request_bits'],r['reply_bits'])!=(170,187,240) or not r['no_combinational_read_tree_across_dies']:raise ValueError('Wrong R49 ABI')
    hd,_=H.inputs();lef=hd['cell_LEF.json'];c=hd['capture.json']
    ff='DFFHQNx1_ASAP7_75t_R';inv='INVx1_ASAP7_75t_R';nand='NAND2x1_ASAP7_75t_R';buf='BUFx4_ASAP7_75t_R'
    if r['feedback']['total_BUFs']!=2*(39744+1483):raise ValueError('Baseline feedback role union')
    widths={master:round(float(re.search(r'SIZE ([\d.]+) BY',lef[master])[1])*1000) for master in (ff,inv,nand,buf)}
    # Existing five cells retained; two positive buffers placed in feedback
    # only after existing cells, no consumption of the empty routing row.
    bitcells=[('storage',ff),('restore',inv),('forward_NAND',nand),('feedback_NAND',nand),('final_NAND',nand),('feedback_BUF0',buf),('feedback_BUF1',buf)]
    offsets={};x=0
    for name,master in bitcells:offsets[name]=(master,x);x+=widths[master]
    wordwidth=69*x
    if wordwidth!=204930:raise ValueError('Widened source footprint')
    for supply,wanted in [('VSS',(-9,9)),('VDD',(261,279))]:
        block=re.search(r'PIN '+supply+r'\b(.*?)END '+supply,lef[buf],re.S)
        rect=re.search(r'RECT ([\d.-]+) ([\d.-]+) ([\d.-]+) ([\d.-]+)',block[1])
        if tuple(round(float(rect[k])*1000) for k in (2,4))!=wanted:raise ValueError('BUF PG phase differs')
    raw=[];banks=[];pg=[]
    for prior,s in zip(old['per_shard_raw_slots'],r['shards']):
        shard=prior['shard'];b=prior['bbox_DBU'];box=[b[0],b[1],b[0]+wordwidth,b[3]]
        seats=prior['seats'];area=wordwidth*(b[3]-b[1])/1e6
        # The R49 source-derived area is independently recomputed here.
        expected=35411.904 if shard==0 else 28329.5232
        if abs(area-expected)>1e-7:raise ValueError('Raw source area mismatch')
        raw.append(dict(shard=shard,bbox_DBU=box,seats=seats,record_bits=seats*69,raw_reserved_um2=area,
            actual_physical_shard_die=shard,baseline_feedback_BUFs=seats*69*2))
        for bank in old['root_banks']:
            if bank['shard']!=shard:continue
            bb=bank['bbox_DBU'];banks.append(dict(bank,bbox_DBU=[bb[0],bb[1],bb[0]+wordwidth,bb[3]]))
        prev=copy.deepcopy(old['raw_M1_PG_overlay'][shard]);prev.update(record_bit_pitch_DBU=x,
            VSS_first_rail_bbox_DBU=[box[0],box[1]-9,box[2],box[1]+9],
            VDD_first_rail_bbox_DBU=[box[0],box[1]+261,box[2],box[1]+279],
            feedback_BUF_orientation='R0',feedback_BUFs_per_bit=2,
            M1_rail_length_um=(2*seats*wordwidth)/1000,
            existing_word_select_INV_in_MX_empty_row_unchanged=True)
        pg.append(prev)
    home=old['model_selected_home_DBU'];oldcommon=old['common_circuit_reserved_bbox_DBU'];halo=4320
    common=[raw[0]['bbox_DBU'][2]+halo,oldcommon[1],oldcommon[2],oldcommon[3]]
    if any(H.overlap(common,s['bbox_DBU']) for s in raw):raise ValueError('Widened raw overlaps common')
    if sum(bank['seats'] for bank in banks)!=576:raise ValueError('Record capacity changed')
    body=r['feedback']['total_body_um2'];repair=2*body/1e6
    fullcell=old['full_owner_body_reservation_mm2']+repair
    rawarea=sum(v['raw_reserved_um2'] for v in raw)/1e6
    common_required=fullcell-rawarea
    common_area=(common[2]-common[0])*(common[3]-common[1])/1e12
    if common_area<common_required:raise ValueError('Reduced common circuit underreserved')
    inside=old['per_die_enclosure_mm2']-old['per_die_outer_PG_ring_reservation_mm2']
    if inside<fullcell:raise ValueError('Capture enclosure deficit')
    # Concrete literal pin coordinates for each repeated bit, NOT a legal
    # routed feedback circuit or a min/max timing certificate.
    links=[('storage','QN','restore','A'),('restore','Y','feedback_BUF0','A'),
        ('feedback_BUF0','Y','feedback_BUF1','A'),('feedback_BUF1','Y','feedback_NAND','A'),
        ('feedback_NAND','Y','final_NAND','B'),('final_NAND','Y','storage','D')]
    routes=[]
    for src,sp,dst,dp in links:
        sm,sx=offsets[src];dm,dx=offsets[dst]
        a,ar=pinpoint(lef[sm],sp);b,br=pinpoint(lef[dm],dp);a=[a[0]+sx,a[1]];b=[b[0]+dx,b[1]]
        routes.append(dict(source_role=src,source_pin=sp,dest_role=dst,dest_pin=dp,
            source_point_local_DBU=a,dest_point_local_DBU=b,
            L1_projection_um=sum(abs(v-w) for v,w in zip(a,b))/1000,
            actual_escape_layer_vias_OBS_and_wire_RC=None))
    return dict(schema='DS_CAPTURE_HOME_R49_RECONCILIATION_1',candidate=old['candidate'],source_receipts=receipts,
        predecessor_source_and_records_unchanged=True,canonical_island_home_DBU=home,
        per_shard_raw_homes=raw,root_banks=banks,raw_M1_PG_overlay=pg,
        prior_common_bbox_DBU=oldcommon,corrected_common_bbox_DBU=common,
        eliminated_prior_overlap_um=(raw[0]['bbox_DBU'][2]-oldcommon[0])/1000,
        common_shift_um=(common[0]-oldcommon[0])/1000,
        actual_raw_common_gap_um=(common[0]-raw[0]['bbox_DBU'][2])/1000,
        common_circuit_home_shard=None,control_locality_and_merge_provider_selected=False,
        no_combinational576way_crossdie_mux=True,no_global_field_ready=True,
        logical_phase_lease_count=1,source_verified_matrices=r['verified_source_matrices'],
        total_exact_seats=576,compiled_weight_macros_per_die=8192,compiled_CFG_macros_per_die=14336,
        actual_raw_bit_cell_roles=[dict(role=n,master=m,x_offset_DBU=o) for n,(m,o) in offsets.items()],
        raw_bit_pitch_DBU=x,raw_word_width_DBU=wordwidth,
        proposed_feedback_only_pin_routes_per_bit=routes,
        feedback_route_projection_not_routed_or_closed=True,
        forward_payload_does_not_traverse_feedback_BUFs=True,
        shared_restore_output_forward_fanout_load_change_requires_characterization=True,
        source_feedback_prototype_sha256=r['feedback']['typed_feedback_prototype_source_sha256'],
        source_typed_feedback_hold_closed=False,forward_hold_closed=False,
        ABI=dict(context_bits=r['context_bits'],request_bits=r['request_bits'],reply_bits=r['reply_bits'],
            physical_shard_bit_is_separate=True,token_capacity_C=None,
            extra_physical_shard_context_bits_per_token=1,total_new_token_FF_bits=None,
            req_reply_corridor_required_bits=427,request_ACK_credit_bits=None),
        clock_reset=dict(predecessor_FO8_tree=old['clock_reset'],baseline_FFbits_unchanged=41227,
            baseline_clock_RESETN_SETN_pin_loads_unchanged=True,
            feedback_combinational_BUFs_do_not_add_clock_or_reset_pins=True,
            added_new_token_selector_FF_CLK_and_reset_loads=None,
            all_feedback_BUF_VDD_VSS_feeds_required=True,
            raw_R0_MX_rail_phase_same=True,old73_element_clock_buffers_not_borrowed=True,
            parent_route_buffer_sites_wire_load_input_budget_and_reset_release=None),
        domains=dict(source_actual_clock='single clk',target_stream_GHz=1.2,target_serial_SU_GHz=.9,
            selected_CDC=None,consumer_clock_ps=r['offdie_service']['consumer_clock_ps'],
            consumer_physical_pin_home=None),
        area=dict(old_full_owner_cells_mm2=old['full_owner_body_reservation_mm2'],
            feedback_BUF_body_um2=body,feedback_50pct_reserve_mm2=repair,
            full_owner_cells_with_feedback_mm2=fullcell,
            total_widened_raw_reserve_mm2=rawarea,common_required_mm2=common_required,
            reduced_common_reserved_mm2=common_area,
            old_island_mm2=old['per_die_enclosure_mm2'],island_change_mm2=0,
            retained_PG_perimeter_mm2=old['per_die_outer_PG_ring_reservation_mm2'],
            interior_left_before_new_tokens_VM_forward_hold_routes_mm2=inside-fullcell,
            whole_reticle_screen_unchanged_mm2=old['whole_area']['no_containment_screen_mm2'],
            no_extra_feedback_cost_on_top_of_containing_enclosure=True,
            no_inherited_service_or_return_containment_credit=True,
            actual_necessary_reticle_deficit_mm2=None),
        arrival_cut=old['arrival_cut'],actual_tracks_after_pg_and_pin_union=None,
        timing=dict(rejected_cut_e899_unchanged=True,new_register_cuts_selected=False,
            actual_clock_qualified=False,accepted_consumer_deadline=None,actual_route_latency_cycles=None,
            local_region_to_VM_projection_um=old['timing']['VM_region_centre_L1_projection_um'],
            projection_not_legal_route_bound=True,first_last_accepted_edges=None),
        reticle_33by26_S58_NP2048_unchanged=True,
        geometry_raw_common_overlap_free=True,physical_fit_proven=False,physical_build_admitted=False,new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
