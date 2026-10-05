#!/usr/bin/env python3
"""Actual source port expansion and conservative residual reconciliation."""
import json,re,hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/dsrom_element_cfg_containment_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(s):return re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
def ports(text,env):
 header=clean(text).split(');',1)[0];rows=[]
 for m in re.finditer(r'\b(input|output|inout)\s+(?:(?:wire|reg|logic|signed)\s+)*(\[[^\]]+\])?\s*(\w+)',header):
  w=1
  if m[2]:
   a,b=m[2][1:-1].split(':');w=abs(eval(a,{'__builtins__':{}},env)-eval(b,{'__builtins__':{}},env))+1
  rows.append(dict(name=m[3],direction=m[1],bits=w))
 return rows
def main():
 receipt=json.loads((OUT/'source_receipt.json').read_text());src={}
 for n,r in receipt['sources'].items():
  p=OUT/'inputs'/n;assert sha(p)==r['sha256'];src[n]=p.read_text()
 a=json.loads((OUT/'inputs/authoritative_excerpt.json').read_text());ledger=a['r6_exact_once_area_ledger'];negative=a['receipt_r4_service_negative'];cap=a['old_S58_capacity']
 oldframe=(cap['q_pairs_per_die']*64825.596+cap['BF16_pairs_per_die']*142971.9984)/1e6
 residual=cap['field_need_mm2']-oldframe
 assert math.isclose(residual,47.208013178655904,abs_tol=1e-9)
 array=a['physical_array'];np=array['compiled_NP'];bf=array['NBF'];assert(np,bf)==(4096,724)
 pairtext=src['ot_v41_pair_w17w10_rne_wake_prepare.sv'];elemtext=src['ot_v41_rom_elem_w10_rne_wake_prepare.sv'];adapttext=src['ot_v41_rom_adapt.sv']
 assert 'reg [47:0] cm [0:DEPTH-1]' in pairtext
 assert 'ot_rom_4096x72_m8' not in clean(pairtext)
 assert '.fault(fault)' in pairtext
 assert 'GRADUAL_RNE' in src['ot_v41_bf16_lanes2_rne_prepare.sv'] and 'ot_v41_bmul_subnormal_rne_prepare' in src['ot_v41_bmul2_rne_prepare.sv']
 env=dict(NB=2,PHW=10,AW=30,NW=21,W=16,IL=8,VAW=19)
 tables={n:ports(src[n],env) for n in ['ot_v41_rom_elem_w10_rne_wake_prepare.sv','ot_v41_pair_w17w10_rne_wake_prepare.sv','ot_v41_rom_adapt.sv','ot_rom_4096x72_m8.v']}
 for ps in tables.values():assert ps and len({p['name'] for p in ps})==len(ps)
 lef=src['ot_rom_4096x72_m8.lef'];pins=re.findall(r'^\s*PIN\s+(\S+)',lef,re.M);obs=lef.split('  OBS',1)[1];layers=re.findall(r'LAYER\s+(\S+)\s*;',obs)
 macro=json.loads(src['ot_rom_4096x72_m8.json']);body=7*np*macro['area']['macro_area_um2']/1e6
 assert math.isclose(body,68.57156984832,abs_tol=1e-9)
 expand=dict(prospective_per_pair_4096x72_depth_slices=7,compiled_pairs=np,prospective_macro_instances=7*np,macro_body_mm2=body,macro_outline_um=[macro['area']['macro_width_um'],macro['area']['macro_height_um']],LEF_pin_count_per_macro=len(pins),expanded_physical_macro_pin_count=7*np*len(pins),OBS_layers=sorted(set(layers)),actual_provider_instances_in_retained_pair_source=0,actual_source_provider='Generic48bit cm array/registered loader; no hard macro or cfgECC decoder instantiation',per_pair_raw_read_bus_bits=7*72,per_pair_selected_payload_bits=48,depth_select_bits=3,physical_macro_address_bits=12,source_logical_address_bits=15,simultaneous_read_contract='One word per pair per loader cycle. Seven macro outputs require select/gating; independent pairs cannot silently share ports.',ECC_candidate=dict(payload_bits=48,SECDED_bits_required=7,physical_word72_spare_bits_after_ECC=17,existing_source_ECC_path=False,payload_decode_and_fault_visibility_bound=False),source_fault_path='u_e fault directly drives pair fault; no cfg read/decode fault or visibility ACK endpoint',source_final_write_guard='Loader c_v/c_a/c_d from ld_run/ld_k/cmr; act from class-valid writes. Configuration must finish before go_e. Replacing cmr requires address/word/valid alignment and final-word visible fence.',physical_read_pipeline='Source generic cm is1cycle loader assumption. Actual macroSS/PP/capture/ECC path needs bounded service;27cycle source schedule cannot be inherited without provider proof.')
 x=dict(schema='opentallas.DSROM.element-cfg-containment.v1',candidate_id=a['r6_candidate'],authoritative_main_receipt=a['source_commit'],source_receipt_sha256=sha(OUT/'source_receipt.json'),authoritative_excerpt_sha256=sha(OUT/'inputs/authoritative_excerpt.json'),source_port_tables=tables,source_parameters=env,residual_equation_receipt_sha256=sha(OUT/'inputs/residual_equation_receipt.json'),
  residual=dict(mm2=residual,arithmetic_origin='Old analyticalfield_need minus oldS58catalogframes (2651q+724BF). The source _cons_need equation uses payloadbytes*density*depthratio plus frame strips minus2oldanchorROM areas/pair; this is a density/frame remainder, not a named netlist collection.',old_field_need_mm2=cap['field_need_mm2'],old_catalog_frame_mm2=oldframe,native_instance_identity_proven=False,cfg_ECC_dispatch_containment_proven=False,credit_mm2=0,conservative_retained_mm2=residual,not_assumed_new_4096_native_logic=True),
  authoritative_ledger=ledger,configuration_expansion=expand,
  whole_dual_element=dict(actual_source='Repaired ot_v41_rom_elem_w10 definition with BF16=1 retains q compute and BF lanes; same4weightmacros. Do not add a second fullBF/qframe.',source_file='ot_v41_rom_elem_w10_rne_wake_prepare.sv',parameters=dict(NB=2,PP=1,FAST=1,BF16=1,XF=8,MTP=1,EARLY=1,BP=0,FRONT_PAR=0,WAKE_REG=1,GRADUAL_RNE=1,FIX_SECOND_ROW_INDEX=1),q_only_parameters=dict(BF16=0,XF=4),shared_RNE_source='ot_v41_bmul2_rne_prepare ->ot_v41_bmul_subnormal_rne_prepare; one implementation only',mapped_disjoint_RNE_WAKE_growth_proven=False,source_matched_hard_LEF_ETM_available=False,complete_numerical_control_gating_gate_PASS=False,source_clock_structure='FAST captures external beats onclk;8wakeFFs reset1 feed8leafICGs. DRAIN127 and cfg_go/finalwrite/quiet endpoints need combined gate.',primitive_arithmetic_PASS_not_full_element=True,cfg_provider_outside_u_e_not_embedded_by_frame_comment=True),
  next_source_contract=dict(named_instances_required=['eachpair.cm provider hard-macro slices+decode+wordmux+capture+cfgfault','eachpair.u_e.g_ir inputFF and g_wake8ICGs plus leaf arithmetic/sharedRNE/rowrepair','adapt.keyrom1024comparators/priority and phase fanout/skids','FP4 sidecarECC provider+decoder and HE/CROM actualconsumer ports'],physical_containment_rule='For each named instance show source class, exact hierarchy, cell/macro area, rectangle+pins/OBS/halos, clocks/PG and unique overlap allocation. No subtraction of47.208 or repair proxy until certificate.',Nash_provider_first='Consume one sameS58 provider-first finalcommit when frozen. Prior frozen24d FAIL retained; symbolic all40/all384 PASS alone cannot close physical budget, cfg timing or token service.',Maxwell_calendar='Rebind actual cfg requests and accepted completions, lease/drain/ECC/cuts; stagehop vsTPcollective separate, no resident phasecount multiplication'),
  coordinated_successor=a['selection_contract'],no_new_candidate_count=True,no_depth_sweep=True,physical_G0=False,RTL_PR_jobs=0,generator_sha256=sha(Path(__file__)))
 assert ledger['conservative_no_containment_credit_reticle_margin']<0
 assert (1<<6)>=48+6+1 and (1<<5)<48+5+1 # 6Hamming+1overall for48payload;9 applies only240payload bundle
 assert len(pins)==88 and sorted(set(layers))==['M1','M2','M3','M4']
 raw=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode();p=OUT/'model.json'
 if p.exists():assert p.read_bytes()==raw
 else:p.write_bytes(raw)
 print(json.dumps(dict(residual_mm2=residual,residual_credit_mm2=0,conservative_total_mm2=ledger['conservative_no_containment_credit_die_total'],cfg_macro_instances=7*np,cfg_macro_physical_pins=expand['expanded_physical_macro_pin_count'],macro_LEF_pins=len(pins),sha256=hashlib.sha256(raw).hexdigest(),G0=False)))
if __name__=='__main__':main()
