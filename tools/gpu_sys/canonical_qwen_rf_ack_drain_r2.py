"""Actual old-context ports for the additive RF/commonACK continuation leaf."""
from tools.gpu_sys.canonical_qwen_rf_ack_drain import port_bindings as old_bindings,FILES


def source_files(root):
 from pathlib import Path
 return [str(Path(root)/p) for p in (FILES[0],
  'rtl/model/qwen_rf_ack_drain_20261003/r2/ot_gpu_qwen_rf_ack_drain_r2.sv',FILES[2])]


def port_bindings():
 b=old_bindings();b['leaf']='ot_gpu_qwen_rf_ack_drain_r2'
 b['continuation']=dict(
  simd_context_accept='ACTUAL accepted SIMD instruction at guardedFullSM IDLE -> READ, before provider read; acceptance must be gated by simd_context_permit',
  simd_context_owner55='retained accepted SIMD owner46 + accepted destination RFslot9 (never current phase address)',
  simd_identity='same retained actual issuer identity64/reader association as accepted instruction',
  simd_key='same retained actual issuer key20 as accepted instruction',
  simd_KV_related='actual accepted instruction source classification',
  simd_binding_valid='actual source-bound accepted instruction, no default true',
  simd_context_retire='ACTUAL matching held RF ACK taken for accepted SIMD write / matching instruction retirement, not ALU done or idle',
  simd_retire_owner55='actual retained accepted destination tuple',
  wr_continuation_valid='actual provider write is continuation of accepted instruction/parent; claim alone is insufficient',
  wr_continuation_source='0 W6 parent, 1 SIMD accepted context',
  rd_continuation_valid='actual provider read is continuation of accepted instruction/parent',
  rd_continuation_source='0 W6 parent, 1 SIMD accepted context',
  rd_context_owner55='same actual retained command destination/parent55; NOT rf_read_a/rf_read_b',
  write_destination='rf_write_owner55 remains actual proposed write owner46+destination9; exact match required')
 b['admission']['SIMD_context']='actual SIMD command_valid/ready must BOTH include simd_context_permit; OLD READ/ALU/WRITE progression uses matching continuation permits'
 b['continuation_safety']='protected observed old context + exact owner/id/key/classification + positive stage; one write only, no predicate/phase/current-address fabricated context'
 return b
