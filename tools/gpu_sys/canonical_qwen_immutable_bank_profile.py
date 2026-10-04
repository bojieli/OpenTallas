"""Euclid's packed held-root lookup, using the proven bank-owner ROM verbatim.

Immutable requirement profile only. No clock, owner state, grant or admission
is created. The receiver must match actual coded contexts on all required banks.
"""
from pathlib import Path
import hashlib,json
from tools.gpu_sys.canonical_qwen_banked_manifest_owner import mask_rom,bank_masks,required_banks
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement,uint
ROOT=Path(__file__).resolve().parents[2]
MODULE='ot_gpu_qwen_immutable_bank_profile'


def lookup(p,root,enabled=False):
 uint(root,239,'unmodified held root')
 pc=(root>>164)&2047;version=(root>>19)&2047;actor=(root>>30)&63
 _,initial=bank_masks(p)
 valid=bool(enabled and (pc<1737 or (pc==2047 and version in initial)))
 return valid,required_banks(p,pc,actor,version if pc==2047 else None) if valid else 0


def generate(out,p=None):
 p=p or SourcePlacement.released()
 source='''// Actual immutable source profile; default OFF. No owner/state/clock.
module ot_gpu_qwen_immutable_bank_profile #(
 parameter integer ENABLE=0
)(
 input wire [64*239-1:0] root_tuple,
 output wire [63:0] profile_valid,
 output wire [64*64-1:0] required_banks
);
'''+mask_rom(p)+'''
 genvar actor_port;
 generate for(actor_port=0;actor_port<64;actor_port=actor_port+1)begin:g_profile
  wire [238:0] root=root_tuple[actor_port*239 +:239];
  wire [10:0] pc=root[174:164];
  wire [10:0] version=root[29:19];
  wire legal_pc=(pc<11'd1737)||((pc==11'd2047)&&(operation_bank_mask(pc,version)!=0));
  assign profile_valid[actor_port]=(ENABLE!=0)&&legal_pc;
  assign required_banks[actor_port*64 +:64]=profile_valid[actor_port]?
   (operation_bank_mask(pc,version)|(64'h1<<root[35:30])):64'b0;
 end endgenerate
endmodule
'''
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 f=out/(MODULE+'.sv');f.write_text(source);return f


def model(p=None):
 p=p or SourcePlacement.released();normal,initial=bank_masks(p)
 prior=json.loads((ROOT/'results/uarch/canonical_qwen_banked_manifest_owner_20261003/model.json').read_text())
 facts_path=prior['source_pins'][0]['path'];facts=json.loads((ROOT/facts_path).read_text())['facts']
 cell_area=facts['NAND2x1_ASAP7_75t_R']['SS']['area_um2']
 entries=sum(bool(v) for v in normal.values())+len(initial)
 # Standalone HDL entails64 independent roots, so debit64 additional lookup
 # replicas even if a synthesizer later shares equal address subexpressions.
 rom=64*entries*(5*11+3*64)
 decode_or_valid=64*((5*6+3*64)+3*64+5*11*2+3*3)
 nands=rom+decode_or_valid
 paths=['tools/gpu_sys/canonical_qwen_banked_manifest_owner.py',
        'results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz',facts_path,
        'rtl/experimental/canonical_qwen_banked_manifest_owner_20261003/ot_gpu_qwen_banked_manifest_range_owner.sv']
 return dict(schema='canonical-qwen-immutable-bank-profile',module=MODULE,ENABLE_default=0,
  ABI=dict(root_tuple_bits=64*239,profile_valid_bits=64,required_banks_bits=64*64,ports=64,
   tuple_preserved_bits=239,PC_slice='174:164',version_slice='29:19',actual_actor_slice='35:30',
   required_banks='operation_bank_mask(PC,version) OR onehot(actual root actor)',
   legal='native PC0..1736; INITIAL PC2047 only immutable initial version; all otherPCs refused',
   disabled='profile_valid=0 and required_banks=0',lane_order='root_tuple[i*239+:239] -> profile_valid[i], required_banks[i*64+:64]'),
  cost=dict(additional_lookup_ports=64,immutable_entries_per_port=entries,
   additional_mutable_FF=0,additional_owner_records=0,MACs_per_cycle=0,memory_payload_bytes_per_cycle=0,
   required_mask_output_bits_per_comb_evaluation=4096,valid_output_bits=64,input_boundary_bits=15296,
   two_terminal_boundary_signal_tracks_lower_bound=19456,channel_capacity_tracks_unknown=True,
   NAND2_upper_bound=nands,ROM_NAND2_upper_bound=rom,decode_valid_OR_NAND2_upper_bound=decode_or_valid,
   NAND2_cell_area_um2=cell_area,additional_body_area_estimate_mm2=nands*cell_area/1e6,
   shared_ROM_reuse_credit=0,registered_edges=0,additional_cycle_debit=0,
   prospective_combinational_chain='11bit PC/INITIAL decode -> immutable64bit mask; 6bit actor onehot in parallel -> OR -> valid gating',
   loaded_delay_ps_unknown=True,existing_clock_target_unchanged=True,SSFF_clock_qualified=False,
   floorplan_slot_and_route_fit_unknown=True,
   composed_latency='combinational part of pre-GO receiver readiness; requests stall until every actual bank ready. Zero NEW registered edges is source structure, not zero delay or clock closure.'),
  semantics=dict(grants=False,host_mask=False,coded_owner_replacement=False,payload=False,
   all_RF_inputs_and_outputs=True,whole_operation_scope=True,source_consumer_lifetimes_unchanged=True,
   all239_identity_match_and_positive_bank_captures_owned_by='Euclid atomic receiver',full_factory_ready=False),
  ROM_sha256=hashlib.sha256(mask_rom(p).encode()).hexdigest(),
  source_pins={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in paths})

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);args=a.parse_args()
 p=SourcePlacement.released();print(generate(args.out,p))
