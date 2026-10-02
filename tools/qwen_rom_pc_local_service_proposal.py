#!/usr/bin/env python3
"""One source-backed PC-local owner/two-window G0 screen. No policy adoption.

This is an opt-in model proposal. It preserves r3 and does not edit the unified
baseline. Ceilings/composed optimistic floors are never sustained performance.
"""
import argparse,hashlib,json,math,re
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
R3=Path('results/uarch/qwen_rom_kv_rate_risk_20261002/model_r3.json')
LIB=Path('results/uarch/qwen_rom_bank5_control_20261002/fulltile_terminal_r1/inputs')

def area(path,cell):
 s=(ROOT/path).read_text();start=s.index('cell ('+cell+')')
 return float(re.search(r'\barea\s*:\s*([0-9.eE+-]+)',s[start:])[1])

def proposal():
 raw=(ROOT/R3).read_bytes();r=json.loads(raw);pins={}
 for p,h in r['source_sha256'].items():
  actual=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
  if actual!=h:raise ValueError('r3 source mismatch '+p)
  pins[p]=actual
 owner=(ROOT/'rtl/model_ready_hbm_r14/ot_hbm_r14_tag_owner.sv').read_text()
 provider=(ROOT/'rtl/model_ready_hbm_r14/ot_hbm_causal_command_provider.sv').read_text()
 pkg=(ROOT/'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv').read_text()
 for t in ['delay==11','reg [31:0] seen[0:31][0:127]','for(g=0;g<32;g=g+1)','if(held&&ore)']:
  if t not in owner:raise ValueError('owner source changed '+t)
 for t in ['assign owned_v=map_out_valid||grant_valid','assign owned_credit=grant_valid','if(!credit_we)begin credit_match=1;grant_valid<=1','ore(owned_r&&!grant_valid)']:
  if t not in provider:raise ValueError('shared grant/data output source changed '+t)
 if 'owned_t; //465' not in pkg:raise ValueError('owned output width changed')
 pcs=32;stacks=4;hz=10**9;stream=1200000000;lookup_II=14;mux_stages=5
 reads=r['logical_bytes']['conditional_offchip_read_stacks'];writes=r['logical_bytes']['conditional_selected_closing_K_V_write_stacks']
 sectors=[(a+b)//32 for a,b in zip(reads,writes)]
 if any((a+b)%32 for a,b in zip(reads,writes)):raise ValueError('partial sector policy unsupported')
 # Each data acceptance has its reverse-credit grant on the same owned port.
 output_slots=[2*n for n in sectors]
 owner_s=max(Fraction(n*(lookup_II+mux_stages),pcs*hz) for n in sectors)
 command_s=max(Fraction(n,hz) for n in sectors)
 data_grant_s=max(Fraction(n,hz) for n in output_slots)
 fill_s=Fraction(r['token_lower_bounds']['tail_bypass_masked_fill_beats'],stream)
 compute=Fraction(str(r['token_lower_bounds']['conditional_compute_s']))
 floor=max(owner_s,command_s,data_grant_s,fill_s,compute)
 # Literal current owner saved data/control/output registers. PC identity is
 # a local constant after partition; existing global pc_saved register stays
 # conservatively charged (no replacement credit).
 local_bits=256+12+5+7+4+2+1+465
 additional_local=(pcs-1)*local_bits
 pipe_bits=mux_stages*(465+5+1)
 # Candidate retains independent data_seen and credit_seen until quarantine
 # closes. Existing source seen is not released early or silently repurposed.
 new_credit_mask_bits=32*128*32
 total_FFs=additional_local+pipe_bits+new_credit_mask_bits
 seq=LIB/'18_asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
 simple=LIB/'19_asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib'
 invlib=LIB/'16_asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib'
 ff_area=area(seq,'DFFASRHQNx1_ASAP7_75t_R');nand_area=area(simple,'NAND2x1_ASAP7_75t_R');inv_area=area(invlib,'INVx1_ASAP7_75t_R')
 mux_nands=(pcs-1)*465*3;mux_invs=pcs-1
 per_stack_floor=total_FFs*ff_area+mux_nands*nand_area+mux_invs*inv_area
 baseline=(ROOT/'tools/uarch_model.py').read_text().split('def qwen_tp_point(',1)[1].split('\ndef qwen_rom_options',1)[0]
 if 'cycles = r["cycles"] + x["token_cycles"] + math.ceil(emb)' not in baseline or 'kv_stream=4 * HBM_STACK_BPS' not in baseline:raise ValueError('baseline debit reconciliation changed')
 for p in (seq,simple,invlib,'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv'):pins[str(p)]=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
 return dict(schema='QWEN_ONE_PC_LOCAL_OWNER_TWO_WINDOW_G0_PROPOSAL_V1',status='BLOCKED_FULL_SOURCE_COST_CALENDAR_AND_PHYSICAL_JOIN',
 input_r3_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=pins,preserved_r3_status=r['status'],
 candidate=dict(policy='32PC-local lookup actors using existing32contextSRAMs; single465bit data/grant output; existing1shared64Bfill; two leased layer windows',
 PCs_per_stack=pcs,stacks_per_rank=stacks,additional_context_SRAmacros=0,context_RAM_ports='existing1R1W perPC; allocation/read/RMW ownership must arbitrate per bank',
 lookup_II_per_PC_reference=lookup_II,owned_output_mux_stages=mux_stages,PC_reuse_II_floor=lookup_II+mux_stages,
 pipeline='one465bit 32:1 reduction in five registered binary levels, same identity/owner/PC carried with valid; finite backpressure and reverse grant retain quarantine',
 shared_output_slots_per_sector=2,command_ports_per_stack=1,fill_lanes=1,fill_tracks_before_clock_reset=1048,
 layer_window_rows=54,leased_windows=2,tile_rows_required=108,existing_depth=128,rows_spare=20,additional_tile_KV_macros=0,
 residence='current+next layer only, not144MiB all36 resident; remaining backing read charge remains',
 source_missing=['PC-local state namespace/allocation and serialized atomic remaining_PC/retirement updates','valid reverse-credit matching/quarantine through caller visible grants','two-window source read selector and legal current/next window lease/drain','actual service/serial ready owner, CDC and registered global epoch lease','fair finite data/grant mux and PC retirement pipeline backpressure']),
 traffic=dict(read_rank_B=sum(reads),closing_write_rank_B=sum(writes),incremental_second_full_read_B=0,per_stack_sectors=sectors,per_stack_owned_output_slots=output_slots,
 no_duplicated_payload_charge='Grant occupies an owned465bit output slot; it is not another HBM read byte charge'),
 conditional_ceiling_floors_s=dict(PC_lookup= float(owner_s),column_commands=float(command_s),shared_data_plus_credit_output=float(data_grant_s),one_shared_fill=float(fill_s),
 uniform_compute_plus_collectives_reference=float(compute),perfect_overlap_minimum=float(floor),serial_no_overlap_optimistic_composition=float(max(owner_s,command_s,data_grant_s,fill_s)+compute),
 PC_balance_assumption='optimistic uniform distribution across32PCs; actual pc_of sector calendar and hottest-PC service demand remain unmeasured',
 qualified_overlap=0,initial_layer_prefetch_hidden=False,sustained_service_bound=None,final_latency=None,adopted_rate=None),
 source_area_floor=dict(extra_local_FF_bits_per_stack=additional_local,extra_output_pipeline_bits_per_stack=pipe_bits,new_credit_mask_bits_per_stack=new_credit_mask_bits,
 additional_clock_and_reset_sinks_per_stack=total_FFs,FF_area_um2=ff_area,mux_NAND2_count_per_stack=mux_nands,mux_INV_count_per_stack=mux_invs,
 NAND2_area_um2=nand_area,INV_area_um2=inv_area,known_increment_um2_per_stack=per_stack_floor,known_increment_mm2_per_rank=stacks*per_stack_floor/1e6,
 excludes='PC allocation/CAM/atomic retire/control, fanout buffers/wires, CTS/reset/PG/OBS, source-safe tags/credits masks ports and complete actual parent service assembly',complete_area=None,complete_fit=False),
 debit_join=dict(existing_read_B_charged_once=150994944,conditional_tail_bypass_not_adopted_B=304128,old_full_residency_overflow_mm2=111.97386816,
 qwen_tp_point_cycles='compute/control+exchange+embedding; HBM kv_stream is a separate throughput bound, not a removable latency debit',old_KV_bound_subtracted_from_compute=0,
 named_747_65_baseline_components=r['area']['debits_already_in_Maxwell_baseline'],PHY_already_in_baseline='OPEN; do not double-charge or assume replacement',
 inherited66_4063488_service_reservation_is_credit=False,baseline_uarch_changed=False),
 whole_model_prerequisites=['retain+55 tree/MUL/control and actual0.9GHz serial costs; existing reference is all1.2GHz and not a source-calibrated whole token',
 'actual pc_of per-PC demand, fair grants and first-layer prefetch and each K-score/V-PV release from finite current source calendar','one-time stream reset provider2edges plus actual domain/CDC/globalready join once, never perlayer','HBM ACT/PRE/RD/WR/refresh clocks/PHY, reverse grants, tags and assembly stalls at qualified source clock','Ampere local subtree/control/real IO and Russell actual service slot decompose existing baseline debits before build'],
 owners=dict(service_architecture_calendar='Russell/Kepler',tile_control_clock_IO='Euclid/Ampere',baseline_component_ledger='Maxwell/parent'),
 hardware_admitted=False,new_RTL=False,new_map=False,new_token=False,full_position0_preserved=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():p.error('preserve existing verdict')
 result=proposal()
 with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('BLOCKED_FULL_SOURCE_COST_CALENDAR_AND_PHYSICAL_JOIN')
