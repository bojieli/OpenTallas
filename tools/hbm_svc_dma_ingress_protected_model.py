"""Additive protected native ingress sizing before RTL; composes wide model."""
import hashlib,json,pathlib
from hbm_svc_dma_wide_model import wide_model
ROOT=pathlib.Path(__file__).resolve().parents[1]
def model():
 base=wide_model(); banks=4;depth=32;pub=4;pcs=128
 metadata=6+8+1+1 # slot,index,native epoch,fault
 fifo=banks*depth*(256+32+2*metadata)
 control_primary=3*banks*6+2*banks*5+2+3+2+2+18+1+2*18+2
 publication=pub*(2*256+2*18+2)
 return dict(schema='opentallas.hbm_svc.dma_ingress_protected.v1',adopted=False,
  base_wide_model=base,MACs_per_cycle=0,compute_intensity=0,
  banks_per_PC=banks,entries_per_bank=depth,PC_replicas=pcs,
  metadata_bits=metadata,paired_metadata_bits=2*metadata,
  epoch_metadata_increment_bits_per_PC=banks*depth*2,
  epoch_metadata_increment_bits_four_stacks=pcs*banks*depth*2,
  payload_codeword_bits=4*72,SECDED_K=64,SECDED_R=8,
  FIFO_storage_bits_per_PC=fifo,paired_control_bits_per_PC=2*control_primary,
  decoder_publication_slots=pub,paired_publication_storage_bits_per_PC=publication,
  total_storage_bits_per_PC=fifo+2*control_primary+publication,
  total_storage_bits_four_stacks=pcs*(fifo+2*control_primary+publication),
  native_input_bits_per_cycle=256+18+1,bank_output_bits_per_cycle=256+18+1,
  encoder_output_bits_per_cycle=288,encoder_replicas_per_PC=4,decoder_replicas_per_PC=4,
  data_store_fanout='one bank decoder mux over4 heads; paired controls local to one PC; four independent64bit codecs',
  native_peak_Bcycle_per_PC=32,bank_peak_Bcycle_per_PC=32,decode_publication_Bcycle_per_PC=32,
  capacity='Reserve every burst beat per destination bank before native issue; reservations include encoder, stored FIFO, decoder and held publication debt until actual bank write',
  codec_cycles=3,planned_native_to_bank_write_min_cycles=5,
  latency_composition='encoder1 + FIFO capture boundary1 + real decoder2 + protected publication boundary1; actual edge count measured before integration',
  latency_delta_vs_reference_cycles=4,
  publication_admission='At most4 launched or held decoded sectors; release exactly on output bank write; no native return-ready port',
  payload_protection='Four64bit SECDED words per FIFO entry; single bit correction, UE zero whole sector+fault. Corrected held publication payload paired; metadata/control complements checked continuously fail closed.',
  fault_response='Sticky control_fault immediately suppresses reserve_ready/decode/output publication on mismatched metadata or controls; existing reserved native debt remains finite and fault diagnosis explicit',
  area_floorplan_fit='HOLD: storage counts are analytical; mapped synthesis/full tile floorplan must price codec/paired-state mux and routing. No hardened-fit claim before measurement.',
  replicas_floorplan='128 native PC tiles in the existing wide service island reservation; increased inventory must be admitted against real slots before P&R',
  protected_reference_source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in ['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh','tools/hbm_svc_dma_wide_model.py']})
if __name__=='__main__':print(json.dumps(model(),indent=2))
