#!/usr/bin/env python3
"""Protected lane sizing before RTL; no routing or system bandwidth claim."""
from pathlib import Path
import json,hashlib,argparse
ROOT=Path(__file__).resolve().parents[1]
def model(depth=256,prefetch=8):
    assert depth>=16 and depth<=256 and depth&(depth-1)==0
    assert prefetch>=8 and prefetch<=16 and prefetch&(prefetch-1)==0
    p=ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.json'
    macro=json.loads(p.read_text());a=macro['area']
    return dict(scope='one protected DMA landing lane,256initialcredits; modelbeforeRTL',default_ENABLE=0,MACs_per_cycle=0,
      replicas=128,ports=dict(input_bytes_per_cycle=32,input_sector_bits=18,input_valid_bits=1,output_bytes_per_cycle=32,output_sector_bits=18,output_valid_ready_bits=2,credit_bits=1,II_target=1),
      storage=dict(depth=depth,prefetch=prefetch,output_slots=1,maximum_held_beats=depth+prefetch+1,
        payload_phase='entryindexbit0',macro_row='entryindexbits7:1;zeroextend7bits tobankrow8',physical_banks_per_lane=2,macro_count_per_lane=4,macro_count_fleet=512,
        macro_rows=256,useful_rows_per_phase=depth//2,useful_raw_bytes_per_lane=depth*32,physical_macro_bytes_per_lane=4*256*256//8,
        metadata_mirrored_FF_per_lane=depth*18*2,metadata_mirrored_FF_fleet=128*depth*18*2,
        allocation_publication_rails_bits=depth*2*2,prefetch_payload_mirrored_bits=prefetch*256*2,prefetch_metadata_mirrored_bits=prefetch*18*2,
        prefetch_identity_mirrored_bits=prefetch*20*2,prefetch_valid_reservation_rails_bits=prefetch*2*2,output_mirrored_bits=(256+18+1)*2,
        protection='qualifiedgolden39,32SECDEDpayload;keep/dont_touch distinctcomplement metadata/control/data rails; mappinggatepending'),
      latency=dict(write_ACK_inclusive_edges=5,write_ACK_elapsed_cycles=4,corrected_read_inclusive_edges=6,corrected_read_elapsed_cycles=5,
        lane_publication_observation_cycles=1,read_issue_after_publication_cycles=1,corrected_capture_cycles=1,output_pin_capture_cycles=1,
        minimum_input_to_credit_elapsed_cycles=12,minimum_input_to_consumer_elapsed_cycles=14,
        read_reservation_to_prefetch_release_elapsed_cycles=7,prefetch8_hides_read_loop_for_II1=True),
      admission=dict(initial_credits=depth,credit_return='only matchedcorrectedreadcapturedinreservedprefetchslot',unpublished_read_forbidden=True,overflow='stickyfault,nosuccesscredit',UE='stickyfault,nosuccesscredit',reserve_before_read=True),
      physical=dict(macro_area_per_lane_um2=4*a['macro_area_um2'],macro_area_all_lanes_mm2=512*a['macro_area_um2']/1e6,
        macro_dimensions_um=[a['macro_width_um'],a['macro_height_um']],floorplan_fit='fourmacros+mirroredmetadata/control/registerbuffers requiremappedlane slot;notyetqualified',
        routes='raw274bits+validinput/output;local two-phasepayloadports',channel_capacity=None,mapped_FF_area=None,admitted=False),
      macro_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),HBM90pct_proven=False,adopted=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'model_before_rtl.json').write_text(json.dumps(model(),indent=2)+'\n')
