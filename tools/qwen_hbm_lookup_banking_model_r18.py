"""Price a conservative source-preserving32-PC ownership banking candidate."""
import json, math, argparse, hashlib
from pathlib import Path
from qwen_hbm_snapshot_r18 import snapshot

PIN='693bba78d04ec371d9fb8dc8eb9e0d19437dddaf'
SOURCE='rtl/model_ready_hbm_r15/ot_hbm_r15_tag_owner.sv'
COST='results/uarch/qwen_hbm_retirement_r15_20261002/cost_before_build_r6.json'

def model():
    raw=snapshot(PIN,SOURCE); cost=json.loads(snapshot(PIN,COST))
    lane={'state':2,'delay':4,'pc_saved':5,'tag_saved':12,'beat_saved':5,'data_saved':256,'slot_saved':7,'held':1,'output_reg':465,'credit_mode_credit_WE_saved_output_WE':3}
    # New banks are fully charged, while retained singleton gets no removal credit.
    ff=32*sum(lane.values())+32*(12+5+7+1)
    mux=465*31+26*31+ff*2;compare=32*192
    levels=0;n=ff
    while n>1:n=math.ceil(n/16);levels+=n
    area=(ff*cost['FF_area_um2']+mux*cost['mux_bit_area_um2']+compare*.2/.5+2*levels*cost['BUF_area_um2']/.5)/1e6
    margin=cost['geometry']['area_budget_margin_mm2_per_stack']
    return {'status':'PRICED_CANDIDATE_NOT_ADOPTED_NOT_RTL_READY','source_commit':PIN,'source_sha256':hashlib.sha256(raw).hexdigest(),'cost_sha256':hashlib.sha256(snapshot(PIN,COST)).hexdigest(),
      'retained_original':{'lookup_edges':12,'held_accept_min_edges':1,'lookups_per_sector':2,'optimistic_bytes_per_second_at_1GHz':32e9/26},
      'candidate':'32PC_BANKED_RETAIN12EDGE_LOOKUP_WITH_ONE_SHARED_HELD_OUTPUT_AND_SERIAL_ROOT_RETIRE',
      'lane_state_bits':lane,'new_lanes':32,'root_retirement_record_bits_each':25,'root_retirement_records':32,'extra_FF_bits_per_stack':ff,'extra_mux_bit_equivalents':mux,'credit_comparison_bits':compare,'clock_buffers':levels,'reset_buffers':levels,
      'extra_area_proxy_mm2_per_stack':area,'replacement_credit_mm2':0,'retained_slot_margin_mm2_per_stack':margin,'slot_margin_after_extra_mm2':margin-area,'slot_fit':area<=margin,
      'ports':{'retained_context_macros':32,'context_macro_each':'128x2561R1W','new_memory_ports':0,'PC_lookup_accepts_per_edge_max':32,'shared_owned_output_bits':465,'shared_owned_output_transactions_per_edge':1,'root_retire_transactions_per_edge':1,'new_PHY_ports':0},
      'service_bounds':{'per_PC_sectors_per_edge':'1/26 before backpressure','32PC_uniform_lookup_sector_ceiling_per_edge':32/26,'shared_return_plus_grant_sector_ceiling_per_edge':.5,'uniform_optimistic_bytes_per_second_at_1GHz':16e9,'hot_single_PC_bytes_per_second_at_1GHz':32e9/26,'measured_or_guaranteed_bandwidth':False},
      'causal_contract':['One active12edge lookup perPC; return/reverse sharing1R port arbitrated, no simultaneous samePC read','Each lane holds immutable identity/tag/beat/WE until selected shared output handshake','Root-retire FIFO slot reserved before lane final grant acceptance; full slot causes backpressure','Central arbiter serializes remaining_PC decrement, live_tags updates and allocation; same root never loses concurrent decrements','No retirement callback from latency bounds: source handshake alone grants release','Duplicate/wrong reverse identity or mode quarantines ownership; coordinated drain/reset required'],
      'latency_composition':'max(PC port availability, reserved root-retire slot, downstream held-output room, source12edge context read); shared arbitration and CDC charged separately by accepted events, not serial floor sums',
      'required_before_RTL':['Maxwell/Kepler bind mixedPC demand and return/credit fairness','Price actual input/output fanout and pins against channel tracks','Reconcile failed slot margin with revised composed geometry, CTS/PDN/OBS retained','Source scoreboard proof for simultaneous same-root completions and delayed credit','Actual nativePHY port concurrency, source1GHz versus SS/FF target and CDC unchanged open'],
      'qualification':{'hardware':False,'SSFF':False,'rate':False,'compile':False,'full_program_calendar':False},'jobs':[]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(model(),indent=2,sort_keys=True)+'\n')
