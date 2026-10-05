#!/usr/bin/env python3
"""Source-bound coefficient bank/staging/credit scenarios, not hardware timing.

Enumerates actual encoded emit lanes. Arithmetic/order is unchanged; proposed
compiled fill packets carry exact destination masks and source selectors.
No checkpoint payload, image producer, RTL or evaluation is changed.
"""
import argparse,ast,gzip,hashlib,json,math,subprocess,types
from collections import defaultdict,Counter
from decimal import Decimal as D
from pathlib import Path

PIN='4080bb5fd'
PREFIX='results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2'
SOURCES={
 'encoded_audit':(PIN,PREFIX+'.json'),
 'demand':('f4bce8fa0','results/uarch/w11_crom_demand_20261001/demand_v2.json.gz'),
 'gamma':('3fdbeb823','results/uarch/w11_crom_gamma_interleave_20261001/verification.json'),
 'ISA':('d2c28c279','tools/hdc_isa_v41.py'),
 'emit_source':('7ed62357d','tools/w11_dsrom_crom_demand.py'),
 'floorplan':('541a1d2f','results/floorplan/v41_pack_refit_w10_interim.json'),
 'buffer_reservation':('cda48d1f7','results/uarch/w10_crom_staging_correction_r1/budget.json'),
 'cell_palette':('6da3c7a60','results/uarch/w10_q_elaboration_inventory_r1/construction.json'),
 'compiled_control_receipt':('3c99ce15f','results/uarch/w11_crom_control_catalog_20261001/verification.json'),
 'compiled_control_source_guard':('458081904','results/uarch/w11_crom_control_source_guard_20261001/verification.json'),
 'guarded_catalog_compiler':('04b75f90504cec9b3c6d2c1fa853df201506d40d','tools/w11_dsrom_crom_control_catalog.py'),
}

def raw(pin):return subprocess.check_output(['git','show',pin[0]+':'+pin[1]])
def sha(data):return hashlib.sha256(data).hexdigest()
def ceildiv(a,b):return (a+b-1)//b

def bank_waves(addresses,ports=45):
    bybank=defaultdict(list)
    for c in sorted({a//3 for a in addresses}):bybank[c%ports].append(c)
    out=[]
    for i in range(max(map(len,bybank.values()),default=0)):
        cs=[v[i] for v in bybank.values() if i<len(v)]
        aset={a for a in addresses if a//3 in cs}
        assert len(cs)<=ports
        assert len({c%ports for c in cs})==len(cs)
        out.append(aset)
    assert set().union(*out)==set(addresses) if out else not addresses
    return out

def credit_calendar(packet_count,credits,route=75,payload_cycles=1,reverse_route=None):
    """One source packet per fastcycle, credits through actual cache write.

    Explicit hypothetical fixed bounded sink, fast->slowCDC4slow, one slow
    cache write, reverseCDC31ticks. Stall beyond bound invalidates scenario.
    Credits are not returned at serializer acceptance.
    """
    if reverse_route is None:reverse_route=route
    if credits<1 or packet_count<0 or route<0 or reverse_route<0 or payload_cycles<1:
        raise ValueError('invalid finite service capacity')
    available=[0]*credits;source=0;last=0
    for _ in range(packet_count):
        i=min(range(credits),key=lambda x:available[x])
        launch=max(source,available[i]);source=launch+payload_cycles*3
        arrival=launch+(payload_cycles+route)*3+16
        write=((arrival+3)//4)*4+4
        release=ceildiv(write+31+reverse_route*3+3,3)*3
        available[i]=release;last=max(last,release)
    return dict(packets=packet_count,credits=credits,source_packet_cycles=payload_cycles,
        route_fast_cycles=route,reverse_route_fast_cycles=reverse_route,
        reverse_credit_serialization_fast_cycles=1,
        last_cache_write_and_reverse_credit_tick=last,
        first_credit_return_not_at_acceptance=True,actual_sink_stall_bound=False)

def build(route=75):
    blobs={name:raw(pin) for name,pin in SOURCES.items()}
    pins={name:dict(commit=c,path=p,sha256=sha(blobs[name])) for name,(c,p) in SOURCES.items()}
    demand=json.loads(gzip.decompress(blobs['demand']));audit=json.loads(blobs['encoded_audit'])
    budget=json.loads(blobs['buffer_reservation'])
    palette=json.loads(blobs['cell_palette'])['palette']
    FF_cell=D(palette['storage']['area_um2']);NAND_cell=D(palette['nand']['area_um2'])
    gamma=json.loads(blobs['gamma']);assert gamma['checks']['checkpoint_CHI_operands_per_rank']==0
    records=demand['ranks'][0]['records']
    assert all(r['records']==records for r in demand['ranks'])
    isa=types.ModuleType('pinned_ISA');isa.__file__=str(Path(__file__).resolve().parents[1]/'tools/hdc_isa_v41.py')
    exec(compile(blobs['ISA'],'<pinned ISA>','exec'),isa.__dict__)
    nodes=[n for n in ast.parse(blobs['emit_source']).body if isinstance(n,ast.FunctionDef) and n.name in ('clog','batches')]
    env=dict(I=isa);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned emit>','exec'),env)
    binary=raw((PIN,PREFIX+'.rank0.templates.bin.gz'));encoded=gzip.decompress(binary)
    assert sha(encoded)==audit['ranks'][0]['encoded_template_sha256']
    pins['rank0_encoded']=dict(commit=PIN,path=PREFIX+'.rank0.templates.bin.gz',sha256=sha(binary))
    # All four immutable encoded image digests checked; equivalent demand
    # metadata above permits one shared calendar derivation, not four copies.
    for r in audit['ranks']:
        data=raw((PIN,PREFIX+f".rank{r['rank']}.templates.bin.gz"))
        assert sha(gzip.decompress(data))==r['encoded_template_sha256']
    timeline=[];gamma_count=0;maximum_selector=0;old_selector_aliases=0
    for rec in records:
        f=isa.decode(int.from_bytes(encoded[rec['global_instruction']*256:(rec['global_instruction']+1)*256],'little'),full_shape=True)
        isgamma=any(o.get('tensor')=='norm.weight' or str(o.get('tensor','')).endswith(('attn_norm.weight','ffn_norm.weight')) for o in rec['operand_demands'])
        if isgamma:gamma_count+=1
        bursts=[]
        for coords in env['batches'](f):
            uses=[]
            for oi,o in enumerate(rec['operand_demands']):
                for lane,(outer,inner) in enumerate(coords):
                    address=o['base']+outer*o['outer_stride']+(inner//2 if o['half_inner'] else inner)*o['inner_stride']
                    if o['kind']=='unbound_generated':
                        address+=508800+(20480 if rec['layer']==14 else 0)
                    uses.append((oi,lane,address))
            addresses={a for _,_,a in uses};waves=bank_waves(addresses)
            fill_packets=0;wave_packets=[]
            for wave in waves:
                landing={address:index for index,address in enumerate(sorted(wave))}
                for _,_,address in uses:
                    if address in landing:
                        index=landing[address]
                        maximum_selector=max(maximum_selector,index)
                        old_selector_aliases+=int((index & 127)!=index)
                        assert (index & 255)==index
                # One packet per16-lane group/operand with a16-bit write mask.
                # No arbitrary135-to1024 instantaneous broadcast is assumed.
                targets={(oi,lane//16) for oi,lane,a in uses if a in wave}
                fill_packets+=len(targets)
                wave_packets.append(len(targets))
            bursts.append(dict(unique_words=len(addresses),bank_read_waves=len(waves),
                logical_lane_uses=len(uses),fill_packets=fill_packets,
                wave_fill_packets=wave_packets,
                max_unique_values_per_bank_wave=max(map(len,waves),default=0)))
        assert len(bursts)==rec['emit_bursts']
        assert sum(b['unique_words'] for b in bursts)==rec['one_port_cycles_within_emit_dedup']
        packets=sum(b['fill_packets'] for b in bursts)
        # Conservative no overlap among descriptor/decode/read/capture/mux,
        # then fill transmissions, then coefficient consumer. Pipeline stages
        # are candidate structural costs, not measured contextual closure.
        readwaves=sum(b['bank_read_waves'] for b in bursts)
        bank_ticks=readwaves*(1+1+1+1)*3
        delivery=[]
        for credits in (2,4,128):
            # Hold135value landing until every fill packet from that bank
            # wave is actually accepted and reverse-credited. Then read the
            # next bank wave. This avoids a hidden wholecommand landing or
            # overwriting values while finite TX credits are stalled.
            c=credit_calendar(0,credits,route=route)
            c['packets']=packets
            c['last_cache_write_and_reverse_credit_tick']=sum(
                credit_calendar(n,credits,route=route)['last_cache_write_and_reverse_credit_tick']
                for b in bursts for n in b['wave_fill_packets'])
            c['landing_reuse_policy']='Drain and reverse-credit all current bankwave packets before nextread; no read/fill overlap.'
            c['bank_descriptor_decode_read_capture_ticks']=bank_ticks
            c['cold_fill_plus_credit_ticks']=bank_ticks+c['last_cache_write_and_reverse_credit_tick']
            c['consumer_local_cache_read_ticks']=rec['emit_bursts']*4
            c['total_candidate_partial_ticks']=c['cold_fill_plus_credit_ticks']+c['consumer_local_cache_read_ticks']
            delivery.append(c)
        timeline.append(dict(layer=rec['layer'],global_instruction=rec['global_instruction'],
            pred=rec['pred'],gamma=isgamma,emit_bursts=len(bursts),
            coefficient_reads=rec['one_port_cycles_within_emit_dedup'],
            bank_waves=readwaves,fill_packets=packets,deliveries=delivery,
            actual_consumer_home_and_source_stall_bound=False))
    assert gamma_count==81 and sum(x['coefficient_reads'] for x in timeline)==549760
    FF=327680+131072+4320+12330
    muxbits=2*1024*4*32+16*134*32
    readwaves_total=sum(x['bank_waves'] for x in timeline)
    packets_total=sum(x['fill_packets'] for x in timeline)
    request_pages=ceildiv(readwaves_total,4096)
    fill_pages=ceildiv(packets_total,4096)
    control_macros=3*request_pages+fill_pages
    compiled=json.loads(blobs['compiled_control_receipt'])
    assert compiled['counts']==dict(bank_waves=readwaves_total,coefficient_uses_per_rank=549760,
        commands_per_rank=491,fill_control_words=packets_total,request_control_words=3*readwaves_total)
    assert len(compiled['control_page_images'])==control_macros
    assert compiled['verification']['persisted_word_roundtrip_per_rank_uses']==549760
    assert compiled['verification']['no_missing_or_duplicate_destinations']
    assert not compiled['hardware_admission']
    guard=json.loads(blobs['compiled_control_source_guard'])
    assert sha(blobs['guarded_catalog_compiler'])==guard['source_sha256']
    assert guard['positive_old_catalog_coefficient_uses']==549760
    assert guard['original_artifacts_byte_identical'] and not guard['hardware_admission']
    for name,expected in guard['original_artifacts'].items():
        artifact=raw(('3c99ce15f','results/uarch/w11_crom_control_catalog_20261001/compiled_v2/'+name))
        assert sha(artifact)==expected['compressed_sha256']
        assert sha(gzip.decompress(artifact))==expected['uncompressed_sha256']
    tag_valid_state=2*(256+2+6+8+32+13+1)+2*(256+2+6+13+10+32+1)+4096
    out=dict(schema='opentallas.w17.CROM-finite-prefetch-candidate.v1',source_pins=pins,
        commands=timeline,rank_equivalent_calendars=4,commands_per_rank=491,gamma_commands_per_rank=81,
        bank_placement=dict(physical_banks_per_home=45,physical_depth=4096,physical_width=274,
            proposed_strip_address='container=logical//3;bank=container%45,row=container//45,lane=logical%3',
            maximum_used_row=4072,ports_per_bank=1,max_packed_logical_words_per_fast_cycle=135,
            actual_repacked_image_producer_bound=False,
            theoretical_full5120_norm_read_wave_floor=38,peak1024_burst_wave_floor=8,
            macro_capture_before_mux_required=True),
        placement_alternatives=dict(shared_fullrank45bank_home=dict(homes=4,macros=180,
                actual_nonlocal_layer_routes_and_deadlines=None),
            layer_local45bank_partial_homes=dict(homes=41*4,macros=41*4*45,
                tensor_copies_per_reference_view=1,
                rule='Each source layer/head only; partial home bank depth wasted to buy ports. No full image replicated41times.',
                macro_area_mm2_per_home='0.354661416',aggregate_macro_area_mm2=str(D('0.354661416')*164),
                actual_layer_local_translation_and_hub_placement=False)),
        staging=dict(gamma_FP32_bits=327680,gamma_entries_per_lane_per_family=5,
            gamma_families=2,lanes=1024,gamma_cold_refills_per_rank=81,
            no_all_layer_reuse=True, generic_two_operand_doublebuffer_bits=131072,
            bank_landing_FP32_bits=4320,macro_capture_bits=12330,
            tags=['actualimageSHA','rank','layer','family','command','burst','epoch','validafterlastacceptedfill'],
            local_coefficient_ports_per_lane=2,local_gamma_read_mux='Five entries per family; original base+lane+1024slot.',
            held_RoPE='136CLO+136CHI/provider separate; CHI not zeroed by CROM path.',
            release='After actual lane coefficient acceptance/last use and return credit; no overwrite on backpressure.'),
        fill_port=dict(payload_FP32_bits=512,header_mask_tag_bits=160,raw_packet_bits=672,
            link_bits_per_fast_cycle=1024,group_lanes=16,
            per_packet_source_selector='16 outputs from135 banklanding values; static compiler selection maps exact operand/lane destinations.',
            control_catalog_read_ports_and_MAC_coexistence=None,
            added_forward_reverse_control_tracks=1024+64+64,
            existing_spine_tracks=832,corridor_capacity=1153,corridors_required=ceildiv(832+1152,1153),
            route_fast_cycles=route,reverse_route_fast_cycles=route,
            reverse_credit_serialization_fast_cycles=1,
            fast_to_slow_CDC_ticks=16,reverse_CDC_ticks=31,
            sink_cache_write_slow_cycles=1,actual_receiver_ready_bound=False),
        finite_packet_credit_area_screens=[dict(credits=c,TX_fullpacket_bits=c*672,
            RX_landing_fullpacket_bits=c*672,route_pipeline_bits=route*1024,
            credit_valid_and_return_state_bits=c*2+2*max(1,(c-1).bit_length()),
            fullpacket_route_FF_and_enable_allocated_mm2=str(D(2*c*672+route*1024+c*2+2*max(1,(c-1).bit_length()))*(FF_cell+4*NAND_cell)/D('.5')/D(1000000)),
            no_RF_storage_reuse_credit=True,arbiter_enable_clock_wire_power_unbound=True)
            for c in (2,4,128)],
        gate_screen=dict(added_FF_bits=FF,mux2_bits=muxbits,
            actual_FF_cell_area_um2=str(FF_cell),actual_NAND2_area_um2=str(NAND_cell),
            FF_allocated_area_mm2=str(D(FF)*FF_cell/D('.5')/D(1000000)),
            mux_NAND4_allocated_area_mm2=str(D(muxbits)*4*NAND_cell/D('.5')/D(1000000)),
            additional_descriptor_lookup_enable_fanout_clock_wire_area=None),
        authoritative_current_buffer_reservation=budget,
        compiler_control_storage=dict(request_bank_wave_entries=readwaves_total,
            request_bits_per_entry=45*(12+1+3),request_parallel_ROM_columns=3,
            fill_packet_entries=packets_total,fill_selector_bits_per_entry=16*(8+1)+1+6,
            selector_bits=8,
            request4096pages=request_pages,fill4096pages=fill_pages,
            total4096x274_macros=control_macros,macro_area_mm2=str(D(control_macros)*D('7881.3648')/D(1000000)),
            mandatory_raw_capture_FF_bits=control_macros*274,
            page_select_mux_bits=(3*(request_pages-1)+fill_pages-1)*274,
            tag_valid_and_epoch_state_FF_bits=tag_valid_state,
            tag_state_FF_enable_screen_mm2=str(D(tag_valid_state)*(FF_cell+4*NAND_cell)/D('.5')/D(1000000)),
            source_proof='Enumerated immutable ISA emit coordinates and exact bank/lane destinations; no coefficient tensor payload or producer changed.',
            actual_control_image_or_decompressor_bound=False,
            descriptor_capture_page_mux_and_fanout_extra_cycles=None),
        candidate_delivery_partial_us_by_credit={str(c):str(D(sum(next(d['total_candidate_partial_ticks'] for d in r['deliveries'] if d['credits']==c) for r in timeline))/D(3600)) for c in (2,4,128)},
        gamma_partial_us_by_credit={str(c):str(D(sum(next(d['total_candidate_partial_ticks'] for d in r['deliveries'] if d['credits']==c) for r in timeline if r['gamma']))/D(3600)) for c in (2,4,128)},
        serial_scalar_issue_only_us='458.1333333333333333333333333',
        power_clock_profile='No root stop, ungated newFF/register/route costs require immutable characterization. Neither128credit nor layer-local port proposal admitted.',
        cold_deadline='All81 gamma home refills precede their actual global_instruction firstemit; fillvalid only after last accepted value+matching tag and returned credit. Never issue on partial refill. Other491-command dependencies preserve ISA order; no overlap with unpriced arithmetic.',
        generic_staging_source_correction='Actual source max2 CROM operands; two1024lane FP32operand emit buffers doublebuffered=131072bits, rather than cb50 earlier106496taggedunique store. cb50 historical receipt retained; revised characterization required.',
        full_operator_critical_path_ticks=None,physical_admission=False,hardware_build_ready=False,
        selector_control_exactness=dict(maximum_actual_selector=maximum_selector,
            old7bit_alias_uses=old_selector_aliases,old7bit_format_rejected=True,
            preserved_failed_model_commit='bc1ec8b8f73ce5594a2b65ac7856b88c3f6b027c',
            independent_negative_receipt_commit='785cdfa41',
            corrected_entry_bits=151,actual_compiled_control_image_bound=False),
        compiled_software_catalog=dict(receipt=pins['compiled_control_receipt'],
            metadata_roundtrip_uses_per_rank=549760,physical_pages=control_macros,
            counts_match_current_calendar=True,
            compiler_sha256=guard['source_sha256'],
            preserved_original_compiler_sha256=compiled['compiler_sha256'],
            immutable_source_guard_receipt=pins['compiled_control_source_guard'],
            original_catalog_artifacts_hashes_verified_unchanged=True,
            immutable_source_guard_software_closed=True,
            format=compiled['control_format'],
            scope='Persisted software catalog encode/decode exactness; not coefficient payload repack, physical home or runtime acceptance.',
            original_receipt_reverse_route_gap_priced_here=True,
            runtime_tags_credits_ports_and_contextual_SSFF_bound=False),
        reverse_route_correction=dict(preserved_incomplete_calendar_commit='1360ff9e12f130a656dbbca0b00c02de860584db',
            defect='Earlier return priced reverse CDC but omitted physical return route and credit serialization.',
            forward_and_reverse_envelope_fast_cycles=route,
            actual_local_home_coordinates_bound=False,
            reverse_credit_pipeline_storage_power_additional_unpriced=True,
            historical_credit_power_budget_not_requalified=True),
        classA_exact_metadata=True,full_RTL_exactness=False,adoption=False,headline_rate=None,
        checkpoint_reads=0,jobs_launched=0)
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
