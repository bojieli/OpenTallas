"""Finite actual-native aperture collector before RTL; no owner fabrication."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
FIELDS=dict(live=1,fault=1,quarantine=1,tuple=239,owner=55,PC=11,sequence=64,shape=256,
 present=4,double=4,result_double=1,captured=5,slots=90,owners=230,banks=30,versions=55,workspace=5,
 stage_ACK=8,result_ACK=2,visible=1,
 cursor_live=1,cursor_prior=1,terminal=1,advance_pending=1,
 source_descriptor=8,source_operands=3,source_types=8,source_signed_i8=4,source_counts=32,source_vector_mask=4,
 source_template=4,source_step=6,source_substep=2,source_scalars=4,source_tail=8)
OFF={};bit=0
for name,width in FIELDS.items():OFF[name]=(bit,width);bit+=width
BITS=bit;WORDS=(BITS+43)//44

def model():
 old=json.loads((ROOT/'results/uarch/canonical_qwen_banked_manifest_owner_20261003/model.json').read_text())
 factpath=old['source_pins'][0]['path'];facts=json.loads((ROOT/factpath).read_text())['facts']
 narea=facts['NAND2x1_ASAP7_75t_R']['SS']['area_um2'];ff=.2916
 # One64:1 query selection, five captured leases and one actual RF host route.
 qwidth=239+46+9+11+1+1+2
 mux=64*63*qwidth*3
 proofs=64*5*(5*239+5*46+5*11+5*18+3*12)
 return dict(schema='canonical-qwen-native-aperture-collector',ENABLE_default=0,replicas=64,
  state=dict(fields=FIELDS,payload_bits=BITS,sealed_words_per_actor=WORDS,protected_bits_per_actor=WORDS*72,
   protected_bits_total=64*WORDS*72,mutable_protection='existing sealed72 helper; CE stalls/scrubs, DUE quarantines',
   seal_PC='ACTOR_INDEX',seal_WORD_INDEX_begin=700,seal_WORD_INDEX_end=700+WORDS-1,seal_KIND=4,
   warm_reset='retain all records and quarantine; no reset-as-debt-removal'),
  source_bank_delta=dict(query_payload_before=303,query_payload_after=304,query_coded_words_before=7,query_coded_words_after=7,
   query_workspace_flag_uses_sealed_padding=True,additional_physical_FF=0,
   readable_claim='published input row plus live matching consumer239; no overwrite',
   writable_claim='unpublished producer row OR actual actor-held B workspace typed query',
   private_RF_workspace='compiled RF homes start32; reserve0..31; 4 inputs x2 pages slots0..7, result2 pages8..9 under actual B+issuer hold',
   persistent_proof='CURRENT coded B full239/owner55 scope, input terminal/reverse false; claim/source-retire cannot change source row identity while B.live. Initial query captures actual version/owner/bounds; actor-workspace additionally matches issuer.',
   source_roles_preserved=True),
  ports=dict(source_pairs_bits=72,source_owners_bits=184,source_banks_bits=24,result_pairs_bits=18,result_owner_bits=46,result_bank_bits=6,
   shape_bits=256,tuple_bits=239,owner_bits=55,query_lookup_ports=64,lease_current_scope_selectors_per_actor=5,
   lease_probe_address_bits_per_actor=5*(239+11+18+46+6+3),lease_current_scope_comparators=64*5,
   read_selector_requires_actual_controller_operand2_and_page1=True,no_read_slot_bank_alias=True,
   SRAM_RF_ports_unchanged='existing serialized host read/write, one outstanding per actor; mirrors4096each/one4096write'),
  cost=dict(added_FF_body_mm2=64*WORDS*72*ff/1e6,NAND2_upper_bound=mux+proofs,logic_body_mm2_estimate=(mux+proofs)*narea/1e6,
   compute_MACs=0,new_payload_memory_bytes=0,boundary_tracks_and_floorplan_capacity_unknown=True,
   collection='source cursor load one captured edge, independent immutable profile, begin one captured edge; up to5 aperture captures, each actual query latency5edges then one collector capture; queryseat released separately',
   extra_collection_capture_edges_per_command='cursor load1 + profile begin1 + up to4 inputs +1 result =7; no same-edge command admission',
   collector_capture_edges_at_most=7,
   nonoverlapped_source_query_and_capture_edges_at_most=32,
   query_seat_release_edges_at_most=5,
   source_cursor_advance_edges=1,
   added_cycles_qualification='7 collector captures +5*5 existing query edges +5 actual query-seat consumption edges; excludes all physical/codec repair/stalls/CDC/profile lookup. No finite upper latency claim without those bounds',stage_mirror_ACK_and_lease_stalls_unknown=True,loadedSSFFdelay_unknown=True,
   no_new_correction_or_transport_latency_claim=True),
  required_providers=['actual issuer coded root/owner/Bworkspace witness','actual query result version/direction/workspace and held root/slot/owner',
   'CURRENT source-bank B scope plus initial query CURRENT bounds for both pages','immutable source descriptor profile with PC/sequence/full239/shape/presence/pages independent of cmd authority pins',
   'actual accepted mirror ACK taps bank/slot/owner','actual result visibility full239/owner/sequence after allresultACK',
   'actual controller read_operand/page and write_page route exports','matched actual controller reverse and selected RF routes drained'],
  cursor=dict(storage='SAME sealed collector record, no duplicate executor/context',load='actual owned RPC source compiler channel, independent cmd descriptor and aperture size',keys='PC/template/step/substep/descriptor/operands/types/signedI8/counts/vector-mask/scalars/tail',advance='only matched actual result terminal AND reverse, one held positive advance accepted before nextload',sequence='retain original64; no invented seq+1 because other source RPCs intervene',source_producer='Dewey88f26a3831acea0147c587edd26058a441277155 owned DeliverySession RPC source compiler, literal1737/116 descriptors; no payload arithmetic',
   tail='four2bit count%4, zero means full4lane final beat; vector_mask distinguishes scalar[] from vector[1]',
   frame='actual matched issuer frame retirement clears idle cursor prior; never clears a published source lease',
   remaining_enrollment='Pauli shapeROM wired ONLY collector source keys; actual physical source-bank/root/RF/visibility/drain connections'),
  full_factory_ready=False,source_pins={factpath:hashlib.sha256((ROOT/factpath).read_bytes()).hexdigest()})
