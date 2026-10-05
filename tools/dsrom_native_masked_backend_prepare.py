#!/usr/bin/env python3
"""Size retained native mask/visibility component and mutable-VM protection gap.
Only raw backend component source preparation is admitted; no hardware launch.
"""
import hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_native_masked_backend_prepare_20261003'


def inputs():
 rows=json.loads((BASE/'inputs/origins.json').read_text())
 for r in rows:
  if hashlib.sha256((BASE/'inputs'/r['copy']).read_bytes()).hexdigest()!=r['sha256']:raise ValueError('Input drift '+r['copy'])
 return rows


def parity_home(word):
 if type(word) is not int or not 0<=word<32768:raise ValueError('VM word bounds')
 return dict(bank=word&3,pair=(word>>11)//2,row=(word>>2)&511,half=(word>>11)&1)


def codec():
 p=BASE/'inputs/codec_model.py';s=importlib.util.spec_from_file_location('retained_w6_integer',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def update_stripe(code,half,value):
 if type(half) is not int or half not in (0,1) or type(value) is not int or not 0<=value<1<<32:raise ValueError('Raw32 lane update bounds')
 m=codec();old,corrected,ue=m.decode64(code)
 if ue:raise ValueError('Uncorrectable old stripe; no write or winning ACK')
 shift=half*32;data=(old&~(((1<<32)-1)<<shift))|(value<<shift)
 return m.encode64(data),corrected


def build():
 rows=inputs();sram=json.loads((BASE/'inputs/SRAM.json').read_text());f=json.loads((BASE/'inputs/cell_prices.json').read_text())['facts'];m=codec();g=m.Gates();g.codec();gates=g.dict()
 pair_area=sum(n*f[name]['SS']['area_um2'] for name,n in gates.items())
 raw_state=1088+4144+1135 # masks, WR owner/addr/mask/valid event, RD owner
 tag=169+32+16+10
 model=dict(schema='DS_NATIVE_MASKED_BACKEND_PREPARE_R1',source_pins=rows,
 candidate='DS4096-TP4-S58-PAR2-NP2048',MACs_per_cycle=0,
 raw_component=dict(original='ot_v41_vm_bank4_macro_pipe',successor='ot_v41_vm_bank4_macro_pipe_masked_visible',opt_in='MASKED_VISIBLE=0',
  DEPTH_GROUPS=16,AW=15,element_AW=19,banks=4,groups_per_bank=16,macros=256,data_bits=16777216,
  TAG_W=tag,owner_fields='fullctx169 +resetera32 +batch16 +requestID10; expanded FP32 address reconstructed from word15 and lane mask',
  write_mask_bits=64,mask_state_bits=1088,write_owner_event_state_bits=4144,read_owner_state_bits=1135,new_state_bits=raw_state,
  new_FF_body_floor_mm2=raw_state*f['DFFHQNx1_ASAP7_75t_R']['SS']['area_um2']/1e6,
  native_read_bits_per_cycle=2048,native_write_bits_per_cycle=2048,read_bytes_per_cycle=256,write_bytes_per_cycle=256,
  actual_ports='One consecutive4word read command; at most1word/bank write,4banks. No1520freeports.',
  proposed_new_signals=dict(write_lane_masks=64,write_owner_input=4*tag,write_ack_owner=4*tag,write_ack_addr=60,write_ack_mask=64,write_ack_valid=4,write_accept_valid=4,read_accept_valid=1,read_owner_input=tag,read_owner_output=tag),
  new_boundary_signal_bits=2467,new_boundary_tracks_lower_bound=2467,new_boundary_width_floor_um_at_48nm=2467*.048,
  route_capacity=dict(selected_channel=None,PG_OBS_pin_via_exclusions_bound=False,fit=False,scope='Distinct added interface signals at literal track pitch only; local direction/bus multiplexing and physical escapes must bind before capacity credit'),
  replicas=dict(per_selected_native_backend=1,fleet_or_shard_count_enrolled=False,read_owner_shift_records=5,write_owner_event_records_per_bank=4,write_mask_local_groups=64),
  latency=dict(raw_read_edges=4,macro_write_visible_edges=2,registered_raw_visibility_event_edges=3),
  acceptance='Bad bank/address or zero-enabled-lane requests fault and do not emitwinningACK. Native rawoutputs assume finite external reserved response seats; no self-contained downstream backpressure proof.',
  event_scope='Raw macro-write visibility event +owner tag, not complete mutable protection or consumer retirement. Parent winningACK withheld until guard/protection/publication verifies.',
  reset='No admittedreset with accepteddebt: caller muststop+drain oldowner/read/write/ACK before localreset. Reset cancels oldvalids; cannotundo actualmacro writes or certify retirement.',
  mutable_metadata_protection_installed=False,tag_state_scope='Raw tag/pipeline state only; protected owner envelope and finite held records require separate source-bound cost, no automatic guard3811 containment',freeze_original_source=True,clocks_GHz=.9,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25),
 SRAM_protection_candidate=dict(name='W6_64bit_stripes_native32sidecars',required_not_ROM_ECC=True,
  codec_source='ot_gpu_w6_secded_pkg.encode64/decode64 unchanged64data/72code; syndrome<=71 andoverall, UE quarantine',
  data_words512=32768,stripes64_per_word=8,data_bits=16777216,check_bits=2097152,check_bytes=262144,
  sidecar_macros=32,sidecar_macro='ot_sram_1r1w_512x128_m4_r2c2',sidecar_capacity_bits=2097152,
  sidecar_layout='perbank8pairs; group>>1 selects pair, group&1 selects64bit half, row=(word>>2)&511. Two independent datagroups share distinctmasked halves, one sourceR/W perbank; not extra concurrent ports.',
  sidecar_macro_body_mm2=32*sram['area']['macro_area_um2']/1e6,total288_macro_body_mm2=288*sram['area']['macro_area_um2']/1e6,
  native_macro_SS_CLK_cap_total_fF=288*sram['timing']['ss']['clk_cap_ff'],native_macro_FF_CLK_cap_total_fF=288*sram['timing']['ff']['clk_cap_ff'],
  full_read_decoder_replicas=32,max4bank_fullword_write_encoder_replicas=32,
  one_source_encoder_decoder_pair_gate_counts=gates,full32pair_gate_counts={k:v*32 for k,v in gates.items()},
  pair_cell_body_um2=pair_area,full32pair_cell_body_mm2=32*pair_area/1e6,
  codec_area_is_unmapped_conservative=True,
  scalar_partial_write='Read+decode old64bit stripe, merge enabled32bit lane, encode same resulting64bit stripe andwrite onlyenabled data lanes+exact8 check bits. UE refuses write/publication; corrected sibling used. Mask alone cannotkeep parity valid.',
  initialization='Allowned VM extents/checkhalves valid before firstread; no constructor-zero or unwritten macro syntheticzero assumption. Source RNE/rounding untouched.',
  metadata='Full owner/address/mask/version/epoch/batch protected controlrecords plus guard3811FF cost remain in joined context. ROMwaiver gives no mutablemetadata credit.',
  stage_options='Full source codec cones require loadedSSFF mapping to select actual registered cuts. No inherited ROMchecker timing; no singlecycle decoder claim.',
  nominal_diagnostic_stage_plan=dict(raw_macro_read_to_checked_capture_extra_edges=3,raw4edge_plus_diagnostic_read_edges=7,three_read_record_bits=3*(2048+256+tag+64),three_read_record_FF_floor_mm2=3*(2048+256+tag+64)*f['DFFHQNx1_ASAP7_75t_R']['SS']['area_um2']/1e6,scope='Reservation/example, not selected/certifiedminimum or buildtiming. Codec delay mayrequire differentcuts, pricedbeforebuild.'),
  raw_Nplus3_ACK_not_protected_publication=True,
  RMW_and_postwrite_checked_visibility_schedule='Separate finite service schedule mustprice protected read, merge, encode, nativeN+2 commit andchecked publication. PreserveMaxwellrawN+3 asrawevent; noACKtoirreversibleconsumer beforevalidation.',
  protection_source_realization_present=False,physical_admission=False),
 complete_G0_missing_costs=[dict(owner='Archimedes',datum='Map actualretained W6 fullencoder+decoder withactual64data/72code andSSFFreceiverpinloads; select/priceregisteredcut latency/state beforeprotectfrontendbuild'),dict(owner='Archimedes+Maxwell',datum='Selectedsidecar32macrohome/portcalendar, bankRMW grants, checked postwritepublication and errorheldseat/sourceclock/reset/PG/OBS union'),dict(owner='Maxwell',datum='Name actualVM/co-residenthome forfull288macrobody and existingbackendFF/new6367FF/guard3811FF/codec andsidecarcontrol; no containmentcredit'),dict(owner='Hubble/Maxwell',datum='Actual full169owner12writer exclusion and visiblecallback acceptance/enrollment; static affinecert isconditional')],
 four_targets=dict(DS_ROM='Selected nativeVMcorrectness component and proposedmutableprotection only',DS_HBM='Mutableprotection methodology only, no DSROMnativebank/capacity transfertobaselineGPU',Qwen_ROM='No actualDSprovider instantiation credit',Qwen_HBM='No DSnative topology orromwaiver transfer'),
 admission=dict(raw_component_RTL_source_preparation=True,raw_component_build=False,connected_protected_VM_build=False,physical=False,full_token=False,reason='Rawmask/owner/visibility component sized andsourcepreparation authorized; protection storage/cost bounded above but actualcodec cuts, finiteRMW/publication andslot mustenroll beforehardwarebuild'),
 no_new_jobs=True,no_new_PVE2_PVE3_jobs=True,global_Z3_unchanged=True)
 return model

if __name__=='__main__':
 out=BASE/'model.json';out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n');print(out)
