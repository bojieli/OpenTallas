#!/usr/bin/env python3
"""Source inventory and arithmetic ABI model; no numeric Python/oracle construction."""
import hashlib,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/proto/ot_fp32_mul_rne_pipe.sv',
 'rtl/hdc/v41/ot_hdc_fdiv.sv','rtl/hdc/v41/ot_hdc_fsqrt.sv','rtl/hdc/ot_hdc_sfu.sv']
def model():
 return {'schema':'qwen.native.fp32.datapath.v1','base_commit':'d9b809411d177e64f2cf63578e8e6bc5855193d4',
 'scope':'FADD/FMUL/DIV/SQRT only; ONE Pauli controller owns opcode/transactions/identities/beat leases; no new macro interpreter, Boolean/integer datapath, Python arithmetic or model constructor',
 'source_SHA256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
 'COMMON_NATIVE_source_SHA256':hashlib.sha256((ROOT/'tools/h3_qwen_bounded_native.py').read_bytes()).hexdigest(),
 'ports':{'lanes':4,'a_bits':128,'b_bits':128,'operand_beat_bytes':32,'result_bits':128,'result_bytes':16,'error_bits':8,'valid_ready_per_lane_bits':4,'canonical_zero_bits':4,'operation':'four per-lane onehot enable masks, supplied by controller; no opcode decode'},
 'instances':{'ot_fp32_add_rne_pipe':4,'ot_fp32_mul_rne_pipe':4,'ot_hdc_fdiv':4,'ot_hdc_fsqrt':4},
 'operations':{op:{'source_pipeline_stages':lat,'native_pipe_II':1,'result_visible_edge_distance':lat,'earliest_result_accept_edge_distance':lat+1,'one_completion_seat_lane_reissue_min_distance':lat+2,'full128word_tile_waves':32,'serialized32wave_edge_reservation':32*(lat+2)} for op,lat in [('FADD',5),('FMUL',5),('DIV',31),('SQRT',31)]},
 'capacity':{'inflight_per_lane':1,'total_inflight':4,'held_result_bits':4*(32+2+1),'pending_and_zero_metadata_bits':4*(1+1+1+1),'wrapper_total_FF_bits':156,'temporary_HBM_bytes':0,'additional_source_operand_storage':0},
 'compute':'up to4 independent lane operations per wave; no fused/reordered rounds; actual dependent-chain cost is the matching operation edge distance, not native II1',
 'boundary':'256 operand bits plus4valid/4canonical/16onehot;128 result bits plus8error/4valid/4ready; no new clock domain/CDC/link',
 'faults':'Existing pipelines fail closed with data0: error1 nonfinite/illegal argument, error2 finite overflow/range. COMMON_NATIVE FADD/FMUL/SQRT retains nonfinite host bits: fault-result payload equivalence NOT established, publication must be fault blocked by controller. Finite binary32 RNE and canonical-zero policy tested.',
 'signed_zero':'Canonical true ->+0; false FADD -0+-0->-0, FMUL/DIV sign XOR including rounded underflow, SQRT -0->-0. Flags captured on actual accepted lane input.',
 'replica_mux_cost':'16 original pipes,4 data/error return multiplexers,4 completion seats. No physically free unit sharing; actual source internal pipeline FF/gate totals/area/power require mapping, not inferred from wrapper156bits.',
 'physical':{'mapped_area':None,'floorplan_slot':None,'tracks_and_routes':None,'SS_setup60':None,'FF_hold25':None,'clock_adoption':False},
 'single_user_latency':'32 four-lane waves per128word tile; symbolic edge reservation only, plus Pauli RF/shared publication costs; no fulltoken gain, operation schedule overlap, or measured frequency claim.',
 'default_OPT':0,'RTL_adoption':False,'before_RTL':True}
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.write_text(json.dumps(model(),sort_keys=True,indent=2)+'\n')
if __name__=='__main__':main()
