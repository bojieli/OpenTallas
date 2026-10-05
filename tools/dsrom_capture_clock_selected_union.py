#!/usr/bin/env python3
"""Select one clock bank and source-price raw wire/fanout correction proposal."""
import argparse,gzip,hashlib,json,math,re
from pathlib import Path
import dsrom_capture_home_r49 as H
import dsrom_capture_identity_slot_join as I
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_clock_selected_union_20261002'
def inputs():
    out={}
    for r in json.loads((BASE/'inputs/origins.json').read_text()):
        raw=(BASE/'inputs'/r['copy']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('Arch origin drift')
        plain=gzip.decompress(raw) if r['copy'].endswith('.gz') else raw
        out[r['copy']]=([json.loads(x) for x in plain.splitlines()] if '.jsonl' in r['copy'] else json.loads(plain) if '.json' in r['copy'] else plain.decode())
    return out

def correction(nets,rc):
    # One explicit conservative budget split, not a parameter sweep.
    # Half of old5.76fF reserved for contacts/stubs/coupling, not assigned0.
    metal_budget=2.88;Cmax=max(rc.values());relay_reach=metal_budget/Cmax
    hd,_=H.H.inputs();facts=hd['capture.json'];limits={c:facts['fanout_loads'][c]['bounded_BUF_leaf_clock_load_fF'] for c in ('SS','FF')};bufcaps={c:facts['source_cell_facts']['BUFx4_ASAP7_75t_R'][c]['pins']['A']['cap_fF'] for c in ('SS','FF')}
    rows=[];graph={};bad=0
    for net in nets:
        source=net['source']['instance'];sx,sy=net['source']['point_DBU'];k=len(net['sinks']);edges=[]
        if k<1 or k>8:raise ValueError('source fanout must remain bounded8')
        first_total_wire=min(5.76,*(limits[c]-k*bufcaps[c] for c in ('SS','FF')))
        if first_total_wire<=0:raise ValueError('No positive driver wire envelope')
        first_metal_budget=first_total_wire/2
        starC=0
        for sink in net['sinks']:
            x,y=sink['point_DBU'];L=(abs(x-sx)+abs(y-sy))/1000
            C=abs(x-sx)/1000*rc['M8']+abs(y-sy)/1000*rc['M9'];starC+=C
            first_budget_reach=first_metal_budget/(k*Cmax)
            added=max(0,math.ceil(max(0,L-first_budget_reach)/relay_reach))
            edges.append((sink['instance'],added));rows.append(dict(net=net['name'],source=source,destination=sink['instance'],sink_pin=sink['pin'],source_fanout=k,first_driver_total_wire_budget_fF=first_total_wire,first_driver_reserved_contact_stub_C_fF=first_total_wire/2,first_driver_worst_pin_load_fF={c:k*bufcaps[c] for c in ('SS','FF')},first_driver_pins_plus_wire_envelope_within_source_leaf_load=True,endpoint_L1_um=L,proposed_route_order='M8 horizontal then M9 vertical; legal pin/via escape absent',unbuffered_star_branch_metal_C_fF=C,first_branch_reach_um=first_budget_reach,relay_reach_um=relay_reach,proposed_relay_BUF=added,actual_legal_sites_and_signal_routes=None))
        graph[source]=edges
        bad+=net['source_wire_allowance_5p76_fF_exceeded_in_this_route_family']
    children={v for ee in graph.values() for v,n in ee if v in graph};roots=set(graph)-children
    if len(roots)!=1:raise ValueError('raw source single root per shard')
    padcounts={};visiting=set();cache={}
    def depth(node):
        if node not in graph:return 0
        if node in cache:return cache[node]
        if node in visiting:raise ValueError('clock cycle')
        visiting.add(node);lengths=[n+1+depth(child) for child,n in graph[node]];target=max(lengths)
        padcounts[node]=sum(target-z for z in lengths);visiting.remove(node);cache[node]=target;return target
    D=depth(next(iter(roots)))
    return dict(source_clock_nets=len(nets),source_lower_bound_5p76_violations=bad,wire_contact_budget_fF=5.76,proposed_metal_budget_fF=metal_budget,remaining_contacts_stubs_coupling_budget_fF=2.88,contact_capacitance_proven=False,
      additional_relay_BUF=sum(r['proposed_relay_BUF'] for r in rows),additional_equal_cell_depth_pad_BUF=sum(padcounts.values()),equalized_logical_cell_depth=D,equal_cell_depth_is_not_skew_or_slew_closure=True,
      source_root=next(iter(roots)),branches=rows,clock_edges_and_sites_not_physical=True,signal_escape_RC_extra_must_fit_reserved_budget=True)

def clock_site_inventory(existing,raw_box,seats,requested,shard,rails):
    # Reserve named allowed sites in EXISTING empty raw rows. This does not
    # bind correction nets to stations or qualify the segment route envelope.
    occupied={raw_box[1]+j*540+270:[] for j in range(seats)}
    for c in existing:
        b=c['bbox_DBU']
        for y in (b[1]-b[1]%270,b[1]):
            if y in occupied and b[1]<y+270 and b[3]>y and b[0]<raw_box[2] and b[2]>raw_box[0]:
                occupied[y].append((max(raw_box[0],b[0]),min(raw_box[2],b[2])))
    out=[];free_total=0
    for y,intervals in occupied.items():
        intervals=sorted(set(intervals));merged=[]
        for a,b in intervals:
            if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
            else:merged.append((a,b))
        cursor=raw_box[0];gaps=[]
        for a,b in merged:
            if a>cursor:gaps.append((cursor,a))
            cursor=max(cursor,b)
        if cursor<raw_box[2]:gaps.append((cursor,raw_box[2]))
        for a,b in gaps:
            x=math.ceil(a/54)*54
            while x+378<=b:
                free_total+=1
                if len(out)<requested:
                    out.append(dict(proposed_site_ID=f's{shard}.clock_correction_inventory.{len(out)}',master='BUFx4_ASAP7_75t_R',bbox_DBU=[x,y,x+378,y+270],orientation='MX',actual_instance_net_assignment=None))
                x+=378
    if len(out)!=requested:raise ValueError('Raw empty-row correction site deficit')
    hd,_=H.H.inputs();master=hd['cell_LEF.json']['BUFx4_ASAP7_75t_R'];supply={n:H.pinpoint(master,n)[1] for n in ('VDD','VSS')};rail_index={}
    for rail in rails:
        r=rail['bbox_DBU'];rail_index[(rail['net'],(r[1]+r[3])/2)]=r
    for item in out:
        x,y=item['bbox_DBU'][:2]
        for n,r in supply.items():
            a=[x+r[0],y+270-r[3],x+r[2],y+270-r[1]];rr=rail_index.get((n,(a[1]+a[3])/2))
            if rr is None or not (rr[0]<=a[0] and rr[1]<=a[1] and rr[2]>=a[2] and rr[3]>=a[3]):raise ValueError('Correction MX PG pin not covered')
    return dict(physical_shard=shard,proposed_sites=out,requested_sites=requested,source_disjoint_free_sites=free_total,remaining_free_sites=free_total-requested,
      source_existing_cell_rectangles_excluded=True,literal_new_VDD_VSS_in_same_net_M1_rail_union=True,external_PG_upfeeds_vias_current_unqualified=True,correction_nets_not_assigned_to_these_sites=True,
      new_buffer_MX_supply_phase='VDD bottom/VSS top, existing d4 M1 rails including final toprail',
      source_root_R0_read_and_feedback_rows_unchanged=True,actual_minmax_RC_legality_slew_clock_skew_not_proven=True)

def build():
    d=inputs();arch=d['model.json'];bank=arch['selector_additional_core_clock_bank'];rc={m:float(re.search(r'set_layer_rc -layer '+m+r' -resistance [^ ]+ -capacitance ([^\n]+)',d['setRC.tcl'])[1]) for m in ('M8','M9')}
    if len(d['selector_core_clock_cells.jsonl.gz'])!=70406:raise ValueError('clock bank count')
    cases=[correction(d[f'shard{s}_clock_nets.jsonl.gz'],rc) for s in (0,1)]
    if sum(x['source_lower_bound_5p76_violations'] for x in cases)!=756:raise ValueError('Arch violation census')
    site_inventories=[]
    for shard,case in enumerate(cases):
        raw=arch['physical_shards'][str(shard)];site_inventories.append(clock_site_inventory(d[f'shard{shard}_cells.jsonl.gz'],raw['raw_slot_bbox_DBU'],raw['seats'],case['additional_relay_BUF']+case['additional_equal_cell_depth_pad_BUF'],shard,raw['PG_M1_literal_rails']))
    minimum_extra=arch['minimum_extra_clock_buffers_vs_whole_owner_floor']
    if minimum_extra!=627:raise ValueError('raw clock census drift')
    proposals=sum(x['additional_relay_BUF']+x['additional_equal_cell_depth_pad_BUF'] for x in cases)
    body_per_BUF=.10206;positive_reserve=(minimum_extra+proposals)*body_per_BUF*2/1e6
    h=H.build();identity=I.build();common_demand=identity['common_total_required_with_identity_mm2']+positive_reserve;common_deficit=max(0,common_demand-h['area']['reduced_common_reserved_mm2']);selectordelta=bank['complete_reservation_including_current_core_rectangle_headroom_mm2']-(1.68242+.62337924324)
    return dict(schema='DS_CLOCK_SINGLE_SELECTED_BANK_RAW_CORRECTION_1',candidate=h['candidate'],selected_selector_clock_construction=dict(source_commit='d4a3deb550aa71afec39e0549adb0e0a7f4c2894',named_bank_bbox_DBU=bank['named_site_bank_bbox_DBU'],core_clock70406=70406,transport_clock48007_not_readded=True,reserved_bank_mm2=bank['legal_site_reservation_mm2'],spare_sites=bank['unused_legal_sites'],complete_selector_reserved_with_core_rectangle_headroom_mm2=bank['complete_reservation_including_current_core_rectangle_headroom_mm2'],source_cells_hash=bank['cell_artifact_sha256']),
      prior51ae_annex_preserved_unselected=True,prior51ae_annex_charge_mm2=0,one_clock_bank_charged=True,
      restricted_route_family_RC_fF_per_um=rc,per_shard_raw_clock_correction_proposals=cases,raw_empty_row_correction_site_inventories=site_inventories,
      raw_only_clock_count6521_exceeds_previous_fullowner5894=True,minimum_additional_raw_clock_BUF627=627,
      positive_new_relay_and_pad_BUF=proposals,raw_clock_50pct_additional_reserve_mm2=positive_reserve,
      correction_cells_not_in_feedback_bit_pitch=True,correction_inventory_home_selected_existing_raw_empty_rows=True,actual_net_to_station_routes_unselected=True,
      capture_island_remaining_lower_screen_after_clock_and_identity_before_tokens_VM_routes_mm2=identity['island_remaining_before_replication_tokens_VM_routes_mm2']-positive_reserve,
      common_if_all_new_clock_correction_and_identity_colocated_demand_mm2=common_demand,common_if_all_correction_colocated_deficit_mm2=common_deficit,
      common_deficit_not_whole_island_or_architecture_impossibility=True,
      publication_credit_policy='retain source debt until exclusive VM512 causalvisibility plus positive captured reversecredit/CDC; returnedcredit post-edge not sameedge source reuse',
      new_publicationseat_RAM_or_free_downstreamcapacity_assumed=False,
      frozen_global_identity_bits=169,user_identity_bits=32,route_shard_separate=True,request_bits=187,reply_bits=240,
      old_fff6_header_user16_not_full_identity_proof=True,wire_packet_adapter_packing_and_width_reprice_pending=True,
      conditional_II1_source_credit_inequality='C >= ceil(reply_latency + ordered_VM_visibility_latency + positive_credit_return_CDC_latency) + 1; actual providers/origins absent, C unselected',
      typed_direct_HQ_INV_HQ_forward_BUF_lowerbound=3,typed_samecell_feedback_BUF_lowerbound=2,forward_repair_cell_counts_not_bound_until_stations_selected=True,
      whole_selector_replacement_screen_mm2=h['area']['whole_reticle_screen_unchanged_mm2']+selectordelta,
      raw_clock_reserve_not_added_again_to_reticle_if_contained_in_existing_island=True,
      minimum_required_new_clock_strip_or_enclosure_growth_if_common_sites_fail_mm2=None,
      parent_clock_phase_reset_release_control_sink_union=None,actual_typed_forward_hold=False,legal_PG_vias_pin_escape=False,SSFF=False,
      actual_consumer_deadline=None,physical_fit=False,contextual_PR_admitted=False,no_capture_edge_or_clock_relaxation=True,new_jobs=[])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);m=build()
    for s,case in enumerate(m['per_shard_raw_clock_correction_proposals']):
        raw=(json.dumps(case.pop('branches'),sort_keys=True,separators=(',',':'))+'\n').encode();blob=gzip.compress(raw,mtime=0);name=f'shard{s}_clock_branches.json.gz';(a.out.parent/name).write_bytes(blob);case['branch_file']=name;case['branch_sha256']=hashlib.sha256(blob).hexdigest()

    for s,inventory in enumerate(m['raw_empty_row_correction_site_inventories']):
        raw=(json.dumps(inventory.pop('proposed_sites'),sort_keys=True,separators=(',',':'))+'\n').encode();blob=gzip.compress(raw,mtime=0);name=f'shard{s}_correction_sites.json.gz';(a.out.parent/name).write_bytes(blob);inventory['site_file']=name;inventory['site_sha256']=hashlib.sha256(blob).hexdigest()
    a.out.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
