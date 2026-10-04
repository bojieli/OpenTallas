"""Source-derived NOREADY fault suffix debit; does not select clock/provider."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'results/uarch/dsrom_s81_native_vm_ports_20261004'

def build(source_root):
    prior=json.loads((B/'joint_r3/model.json').read_text())
    census=json.loads((B/'r2/model.json').read_text())['census']
    rows=max(g['rows'] for g in census['geometry_profiles'])
    # R128 root r owns row2*r+parity modulo256; maximum root quota.
    root_quota=2*(rows//256)+min(2,rows%256)
    frames=root_quota;slots=math.ceil(frames/4)
    packet_code=prior['finite_capture']['codeword_bits']
    coded=slots*4*128*packet_code
    extra=coded-prior['coded_state']['frame_ring']
    # Actual existing W6 encoder+decoder no-CSE NAND/INV construction.
    p=Path(source_root)/'results/uarch/dsrom_native_masked_backend_prepare_20261003/model.json'
    cm=json.loads(p.read_text())['SRAM_protection_candidate']
    pairs=dict(packet=2*128*3,bank_owner=256*4*2,reservation=256,
               receipt=256*2,reverse_counter=128,reverse_context=1,ring_control=1)
    gates=cm['one_source_encoder_decoder_pair_gate_counts']
    total=sum(pairs.values())
    codec_area=total*cm['pair_cell_body_um2']/1e6
    ff_extra_area=extra*.2952/1e6
    return dict(schema='dsrom.s81.vm.source_suffix_cost.v1',
      pins={'generator':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'joint_r3':hashlib.sha256((B/'joint_r3/model.json').read_bytes()).hexdigest(),
        'source_census_r2':hashlib.sha256((B/'r2/model.json').read_bytes()).hexdigest(),
        str(p.relative_to(source_root)):hashlib.sha256(p.read_bytes()).hexdigest(),
        **{name:hashlib.sha256((Path(source_root)/name).read_bytes()).hexdigest() for name in (
          'tools/dsrom_s81_capture_parent.py',
          'results/rtl/dsrom_s81_source_binding_20261004/native_conversion/s0_r0/prog.hex',
          'results/uarch/dsrom_native_masked_backend_prepare_20261003/inputs/w6_codec.sv',
          'results/uarch/dsrom_native_masked_backend_prepare_20261003/inputs/cell_prices.json')}},
      fault_contract={'source_NO_READY':True,'accepted_phase_stop_hook_proven':False,
        'four_slots_proven_only_for_uninterrupted_schedule':True,
        'quarantine_drain_may_stop':True,'healthy_slot_return_not_reset_or_physical_ACK':True,
        'source_suffix_discard_not_allowed':True,
        'proposal':'Reserve and retain complete accepted P1 phase image until matched bank+reverse/allcopy retirement; no slot reuse inside phase. Correctable/uncorrectable words never retire unchecked. Faulted phase stays owned; no second GO.',
        'fault_recovery_service_and_rearm_not_enrolled':True},
      source_suffix={'max_actual_fragment_rows':rows,'max_root_quota':root_quota,
        'max_fast_vector_frames':frames,'required_four_frame_slots':slots,
        'coded_retained_phase_bits':coded,'additional_FF_vs_joint_r3':extra,
        'scope':'P1 geometries in retained1149-call census, no new allocator/runtime proof; not MTP/other writers.'},
      codec_cost={'source_codec':cm['codec_source'],'pair_counts_by_concurrent_port':pairs,
        'parallel_balanced_pairs':total,'pair_gate_counts':gates,
        'total_gate_counts':{k:n*total for k,n in gates.items()},
        'body_area_mm2_no_CSE':codec_area,
        'balanced_pairs_conservative_unused_encoders':True,
        'addressed_seal_and_padding_semantics_extra':True,
        'SSFF_loaded_latency_or_clock_qualified':False},
      prospective_area={'joint_r3_placement_floor_mm2':prior['cost']['added_placement_mm2_floor_at50pct'],
        'retained_suffix_added_placement_mm2':2*ff_extra_area,
        'codec_construction_added_placement_mm2':2*codec_area,
        'combined_placement_floor_mm2':prior['cost']['added_placement_mm2_floor_at50pct']+2*(ff_extra_area+codec_area),
        'excludes':['addressed seal/expectedslot/padding logic','loaded clock/reset/route buffers','bank priority/steering','codec pipeline FF chosen from loaded SSFF','consumer absolute deadline'],
        'replaces_r3_healthy_only_not_adopted':True},
      selected_binding={'VM_clock_GHz':None,'route_stage_count':None,'codec_loaded_stages':None,
        'physical_slot_area_mm2':None,'absolute_consumer_deadline_ns':None,
        'rate_delta':None,'fit':None,'physical_or_RTL_admission':False},
      source_consumer={'native_fragment':'field followed by END wait31, no subsequent consumer in emitted two-instruction fragment',
        'C8_source_wait':'tools/dsrom_s81_capture_parent.py c8_write_quiet depends on !capture_live && capture_drained && !capture_fault && !any_accept',
        'consequence':'Next accepted context may wait for physical publication. Unknown absolute origin/deadline/slack is not zero.',
        'native_behavioral_visible_not_physical':True},RTL_written=False,jobs_launched=False)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();x=build(a.source_root);a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'model.json').write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'suffix':x['source_suffix'],'area':x['prospective_area'],'codec_pairs':x['codec_cost']['parallel_balanced_pairs']},indent=2))
