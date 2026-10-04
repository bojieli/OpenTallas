"""Priced old-continuation delta; r1 source/model remain immutable."""
import json
from tools.gpu_sys.qwen_rf_ack_drain_model import model as baseline,constant

def model():
 b=baseline();raw=624;FF=720;extra_FF=FF-b['storage']['leaf_protected_FF']
 extra_compare_bits=2*(55+64+20+1)
 extra_gates=2*1536+extra_compare_bits*5+(raw-479)*8+512
 extra_cell=extra_FF*constant('DFF_UM2')+extra_gates*.0648
 return dict(schema='RF-commonACK-owned-continuation-r2',baseline=b,
  continuation_ports=dict(accepted_SIMD_context=55+64+20+1+1,
   SIMD_retire_owner55=55,write_claim=2,read_claim=2+55,
   instruction_admission_permit=1),
  storage=dict(leaf_raw_bits=raw,leaf_words=10,leaf_protected_FF=FF,
   extra_protected_FF_per_leaf=extra_FF,full64leaf_twojoin_protected_FF=64*FF+2*216,
   accepted_SIMD_context='owner55/id64/key20/related/live/read-started/read-captured/write-started in protected leaf; source acceptance event only',
   W6_old_write_started_bits=1,new_SRAM_macros=0),
  area=dict(extra_compare_bits=extra_compare_bits,extra_NAND_equivalent_ASSUMED=extra_gates,
   extra_cell_mm2_per_leaf_ASSUMED=extra_cell/1e6,
   full50pct_footprint_mm2_ASSUMED=b['area']['full_two_rank_50pct_footprint_mm2_ASSUMED']+2*64*extra_cell/1e6),
  control=dict(new_context_capture_ports=1,SIMD_retire_lookup_ports=1,
   new_boundaries_bits=55+64+20+2+55+2+57+1,
   candidate_mux_replicas=2,candidate_comparator_fanout=2,additional_pipe_edges=0,
   continuation='old retained SIMD or W6 owner55 AND id64/key20/classification AND direction/stage; claim alone grants nothing',
   new_admission='matching-key new W6/SIMD/contextless read/write blocked under drain request/hold',
   retirement='SIMD context remains through real paired-read capture, ALU stall, one write, matching held W4ACK; no idle/timer retire'),
  latency=dict(context_capture_edges=1,read_capture_edges=1,write_capture_edges=1,
   SIMD_retire_edges=1,no_contextless_bypass=True,additional_wait='actual ALU/write/ACK eligibility already in source; no second service charge',
   prospective_clock_ns=b['clock']['prospective_ns'],whole_token=None,SSFF=False),
  fixture_scope='one directed codedleaf stall/drain/reset/fault component test; no native math/provider/fullSM/fulltoken qualification')

if __name__=='__main__':print(json.dumps(model(),sort_keys=True,indent=2))
