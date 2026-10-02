#!/usr/bin/env python3
"""Complete-element reservation on the existing PAR2 4320DBU halo basis.

No source modification, synthesis or physical-tool invocation. Coordinates are
an explicit candidate allocation, not an extracted routed abstract.
"""
import json
import math
import hashlib
from pathlib import Path
from dsrom_noECC_physical_transition import union_area, intersection

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_complete_element_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n):return json.loads((BASE/'inputs'/n).read_text())
def snap(n):return math.ceil(n/2160)*2160
def translated(r,x,y):return [r[0]+x,r[1]+y,r[2]+x,r[3]+y]
def shapes(macro,x,y):
    for p in macro['pins']:
        for r in p['rectangles']:
            yield dict(kind='PG' if p['use'] in ('POWER','GROUND') else 'signal_pin',pin=p['name'],layer=r['layer'],bbox_DBU=translated([round(v*1000) for v in r['rect_um']],x,y))
    for r in macro['OBS']:
        yield dict(kind='OBS',layer=r['layer'],bbox_DBU=translated([round(v*1000) for v in r['rect_um']],x,y))
def tracks(grid,layer,axis,limit):
    g=next(g for g in grid['grids'] if g['layer']==layer)
    return sorted({start+i*pitch for start,count,pitch in g[axis] for i in range(min(count,max(0,(limit-start)//pitch+1))) if 0<=start+i*pitch<limit})
def build():
    receipts=load('receipt.json')
    for r in receipts:
        if sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('source pin changed '+r['copy'])
    manifest=json.loads((BASE/'physical_source_manifest.json').read_text())
    for r in manifest['files']:
        if sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('physical source copy changed '+r['copy'])
    env=load('envelope.json');grid=load('grid.json');local=load('macro_model.json');source=load('source_model.json');unified=load('unified_noECC.json')
    if unified['candidate']!=local['candidate']:raise ValueError('independent candidate forbidden')
    macro=local['macro'];halo=4320;mw,mh=round(macro['width_um']*1000),round(macro['height_um']*1000)
    result={}
    for name,c in env['classes'].items():
        width=round(c['outline_um'][0]*1000);height=snap(max(round(c['outline_um'][1]*1000),2*mh+4*halo))
        previous_PAR2_height=height
        inherited=c['adjacent_compute_control_wires_margin_reservation_um2']
        increment=source['area']['wake_proxy_um2_per_pair']*2
        if name=='BF16_column_pair':increment+=source['area']['mandatory_RNE_proxy_um2_per_BF_pair']*2
        cut=2*mw+6*halo
        capture_area=4*halo*mh/1e6
        # Deterministic reservation repair, not a count/parameter sweep: retain
        # the complete inherited nonmacro allowance and source repair proxy.
        required_height=(inherited+increment-capture_area)*1e6/(width-cut)
        height=snap(max(height,required_height))
        instances=[];physical=[]
        for mb in range(2):
            for bank in range(2):
                x=halo+mb*(mw+3*halo);y=halo+bank*(mh+2*halo)
                inst=f'u_e.g_mac[{mb}].g_pp.u_rom{bank}'
                body=[x,y,x+mw,y+mh];exclusion=[x-halo,y-halo,x+mw+halo,y+mh+halo]
                instances.append(dict(instance=inst,MB=mb,bank=bank,bbox_DBU=body,placement_halo_DBU=exclusion,orientation='R0',physical_payload_bits=274))
                physical.extend(dict(instance=inst,**s) for s in shapes(macro,x,y))
        # R0 macros face right. Capture strips lie outside placement halos;
        # their capture+enable netlist still needs exact mapped placement.
        capture=[dict(instance=i['instance'],bbox_DBU=[i['bbox_DBU'][2]+halo,i['bbox_DBU'][1],i['bbox_DBU'][2]+2*halo,i['bbox_DBU'][3]],register_bits=274,source_clock='leaf_clk[0]',real_cell_mapping_pending=True) for i in instances]
        region=[cut,0,width,height]
        region_area=(width-cut)*height/1e6
        capture_area=sum((r['bbox_DBU'][2]-r['bbox_DBU'][0])*(r['bbox_DBU'][3]-r['bbox_DBU'][1])/1e6 for r in capture)
        # M2 followpin locations are row-dependent. This conservative explicit
        # source-template shadow uses all possible270DBU row boundaries,
        # rather than treating uninstantiated PG as absent or a50% fraction.
        pdn=[]
        for y in range(0,height,270):pdn.append(dict(layer='M2',kind='followpin_shadow',bbox_DBU=[0,max(0,y-9),width,min(height,y+9)]))
        for layer,direction,w,spacing,pitch,offset in [('M5','V',120,72,2700,300),('M6','H',288,96,5400,513),('M7','V',288,96,10800,1000)]:
            for origin in range(offset,width if direction=='V' else height,pitch):
                for n in (0,w+spacing):
                    center=origin+n
                    rect=[center-w//2,0,center+w//2,height] if direction=='V' else [0,center-w//2,width,center+w//2]
                    if rect[0]>=0 and rect[1]>=0 and rect[2]<=width and rect[3]<=height:pdn.append(dict(layer=layer,kind='source_stripe_template',bbox_DBU=rect))
        capacities=[]
        for layer in ('M2','M4','M6'):
            ys=tracks(grid,layer,'Y',height)
            excluded=[s['bbox_DBU'] for s in physical+pdn if s['layer']==layer and s['bbox_DBU'][0]<=cut<=s['bbox_DBU'][2]]
            blocked={y for y in ys if any(r[1]<=y<=r[3] for r in excluded)}
            capacities.append(dict(layer=layer,crossing_x_DBU=cut,grid_tracks=len(ys),source_OBS_PG_template_blocked=len(blocked),remaining_before_vias_clock_spacing=len(ys)-len(blocked)))
        budget=sum(c['remaining_before_vias_clock_spacing'] for c in capacities if c['layer'] in ('M2','M4'))
        clock_topology={}
        for corner,p in local['complete_NB2_PP1_pair']['existing_capture_and4macro_clock_pins'].items():
            cap_load=1096*p['DFF_CLK_fF']
            limit=p['ICG_GCLK_max_cap_fF']
            clock_topology[corner]=dict(capture_leaf0_pin_load_lowerbound_fF=cap_load,
                capture_leaf0_min_load_groups_before_wires_control=math.ceil(cap_load/limit),
                ROM_leaves_4_5_6_7_each_pin_load_fF=p['ROM_CLK_fF'],
                distinct_capture_plus4ROM_load_groups_lowerbound=math.ceil(cap_load/limit)+4,
                leaves1_2_3_compute_chain_tree_loads_not_in_capture_bound=True,
                groups_are_electrical_partition_bounds_not_inserted_buffers=True)
        result[name]=dict(outline_DBU=[0,0,width,height],previous_catalog_outline_um=c['outline_um'],
            previous_PAR2_reserved_height_DBU=previous_PAR2_height,
            deterministic_height_repair_formula='ceil2160(max(previous_PAR2height,(inherited_nonmacro+RNE_WAKE_proxy-capture_strip_area)/(width-complete_macro_halo_capture_block_width)))',
            added_area_over_existing_PAR2_reservation_um2=width*(height-previous_PAR2_height)/1e6,
            reservation_area_um2=width*height/1e6,existing_PAR2_halo_basis=True,new_parent_area_debit_not_automatically_added=True,
            macro_instances=instances,translated_macro_pin_OBS_PG=physical,source_PDN_template_rectangles=pdn,
            macro_body_union_um2=union_area([i['bbox_DBU'] for i in instances])/1e6,
            halo_union_um2=union_area([i['placement_halo_DBU'] for i in instances])/1e6,
            capture_regions=capture,compute_control_clock_region_DBU=region,
            area_reservation=dict(inherited_compute_control_wires_margin_um2=inherited,
                proposed_remaining_cell_region_plus_capture_strips_um2=region_area+capture_area,
                conservative_RNE_WAKE_increment_at50pct_um2=increment,
                remaining_after_inherited_and_increment_um2=region_area+capture_area-inherited-increment,
                increment_embedding_not_claimed=True,complete_cell_area_mapping_required=True),
            ports=c['source_port_contract'],MACs=c['arithmetic'],
            crossing_capacity=capacities,required_source_catalog_tracks=c['local_signal_tracks_needed'],
            M2_M4_margin_before_actual_vias_clock_spacing=budget-c['local_signal_tracks_needed'],
            track_count_scope='Conservative template screen at namedcut; not routedcapacity. M6 excluded from budget because power/parent routing ownership is not granted.',
            local_ICG_groups=8,source_clock_load_lower_bound=local['complete_NB2_PP1_pair']['existing_capture_and4macro_clock_pins'],
            actual_WAKE1_clock_branch_topology=clock_topology,
            complete_leaf_clock_load_not_only_capture=True,
            gates=['Actual mapped leaf0..7 FF/ICG counts and CLKpin union including RNE stage4, chains, segmenttree, outputvalid/control',
                'Capture strips real DFF+holdmux/enable instance widths, site/grid/pin escape with VIA45 legality',
                'Actual M1/M2 followpin rows, PG via centers/enclosures and local CTS/clock exclusion union',
                'Parent actual port positions/load/slew and translated neighbour channels; source-correct fullscope SS/FF'],
            no_complete_hard_abstract_claim=True)
    return dict(schema='opentallas.dsrom.noECC.complete-element-reservation.v1',candidate=unified['candidate'],inputs=receipts,generator_sha256=sha(Path(__file__)),
        physical_source_manifest_sha256=sha(BASE/'physical_source_manifest.json'),
        physical_sources_count=len(manifest['files']),
        boundary_constraints_source='Parent must supply real driving cells/arrival/slew/output loads and root/leaf clock relationship; no zero-I/O or virtual-clock-only admission.',
        unified_model_commit='636db46842fb25bce441e241b17e6151975271cf',
        unified_screen_mm2=unified['full_topk_slot']['same_candidate_screen_with_topk_state_only_mm2'],
        selector_replacement=dict(single_owner='Epicurus/Maxwell',old_store_already_inherited=True,state_only_delta_mm2=.0617719608,
            staged_unoptimized_core_proxy_mm2=1.50883850628,full_proxy_extra_over_already_priced_state_mm2=1.50883850628-.3693656376,
            full_proxy_not_selected_or_added_without_shared_instance_union=True,controller_displacement_record='c3afef62a',
            no_independent_count_or_variant_selection=True),
        source_parameters=source['geometry'],optins=source['selected_opt_ins'],
        numerical_source_terminal=load('numerical_terminal.json')['status'],numerical_scope='Bounded actual q/BF with sharedRNE/WAKE1, not full-domain or physicaltiming proof',
        elements=result,
        capture_constraints=dict(period_ps=833.3333333333334,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
            accepted_issue_edge=0,capture_postNBA_edge=2,consume_preedge=3,added_ECC_cycles=0,
            two_cycle_setup_only_macro_read_to_selected_cap0_cap1=True,hold_remains_launch_edge=True,
            source_sdc_is_broad_and_must_be_endpoint_narrowed=True,
            forbid_multicycle_to_arithmetic_or_valid_metadata=True,
            constrain_macro_addr_CE_setup_hold_and_clock_minpulse=True,
            capture_to_lane_is_one_cycle_with_real_hold_enable_mux_and_shared_clock_skew=True,
            actual_source_clock_edges='Macro bank clocks leaves4+2MB/5+2MB -> capturegclk=leaf0 -> laneleaf1. Preserve generated/gated edge relation; actual crossleaf skew and enable/minpulse required.',
            root_to_WAKED_and_WAKEQ_to_ICGENA_setup_hold_required=True,
            no_false_path_to_payload_or_clockgate_control=True,
            source_LAT8_RNE_stages_unchanged=True),
        actual_parent_parameter_join=dict(standalone_PHW=source['geometry']['PHW'],product_PHW=10,
            configuration_wrapper_not_inside_element_frame=True,configuration_ROM_ECC_required=False,
            descriptor_validity_address_bounds_identity_and_mutable_control_protection_remain=True,
            old_Maxwell_weight_only_scope_superseded_by_explicit_user_clarification=True,
            no_configuration_ECC_area_macro_credit_until_source_instance_union=True,
            parent_accepted_phase_address_and_CFG_delivery_owned_by_parent_Nash=True),
        physical_G0=dict(admitted=False,scope='Complete local reservation with constructive sourcegeometry; positive area/track screen is not full load/via/clock admission',
            next_independent_gate='Map the complete reviewed element source, preserve all real ROM ports and arithmetic/control, extract cell/CLKpin union into this reservation; no placeholder cones or new engine RTL',
            PnR_launch_requires='Reviewed mapped completecell union and endpoint-specific constraints plus actual pin/via/PG/clock reservations in the shared noECC parent map'),
        new_jobs=0,original_sources_untouched=True)

if __name__=='__main__':
    data=(json.dumps(build(),indent=2,sort_keys=True)+'\n').encode();out=BASE/'model.json'
    if out.exists() and out.read_bytes()!=data:raise ValueError('preserve prior verdict; use successor')
    out.write_bytes(data);print(sha(out))
