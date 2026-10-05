#!/usr/bin/env python3
"""Actual retained SECDED source and reused macro pin/OBS union for PAR2.
No implementation source changes, qualification transfer, encoding or payload.
"""
import hashlib,importlib.util,json,math,gzip
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/uarch/dsrom_PAR2_physical_read_context_20261002';BIND=ROOT/'results/uarch/dsrom_PAR2_padding_parity_binding_20261002';PRIOR=ROOT/'results/uarch/dsrom_PAR2_shard_physical_binding_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def build():
 receipt=json.loads((OUT/'input_receipt.json').read_text())
 for n,p in receipt['inputs'].items():assert sha(OUT/'inputs'/n)==p['sha256']
 ecc=module('source_ecc',OUT/'inputs/ecc.py');src=(OUT/'inputs/decoder.sv').read_text();macro=(OUT/'inputs/raw_macro.v').read_text();binding=json.loads((BIND/'model.json').read_text());roles=json.loads(gzip.decompress((BIND/'reused_macro_roles.json.gz').read_bytes()));templates=json.loads((PRIOR/'macro_templates.json').read_text());helper=module('shapes',PRIOR/'inputs/parent_shapes_tool.py')
 assert 'assign syn[gi] = cw[K + gi] ^ (^t);' in src and 'wire overall = ^cw;' in src and 'if (ce_in) rd_out <= word_read(addr_in);' in macro
 assert sha(OUT/'inputs/raw_macro.lef')==sha(PRIOR/'inputs/ROM.lef')
 cones={}
 for k,replicas in [(256,412),(272,256)]:
  r=ecc.check_bits(k);positions=ecc.positions(k);coverage=[sum(bool(p&(1<<i)) for p in positions) for i in range(r)]
  cones[str(k)]=dict(K=k,R=r,N=ecc.codeword_bits(k),replicas=replicas,covered_data_bits_per_check=coverage,independent_syndrome_XOR2_nodes=sum(coverage),overall_XOR2_nodes=ecc.codeword_bits(k)-1,correction_comparators=k,comparator_width=r,data_correction_XOR_bits=k,balanced_syndrome_depth_upper=max(math.ceil(math.log2(n+1)) for n in coverage),balanced_overall_depth_upper=math.ceil(math.log2(ecc.codeword_bits(k))),actual_mapping_balancing_or_delay_not_measured=True)
 assert cones['256']['N']==266 and cones['272']['N']==282
 shapes=[]
 for role in roles:
  t=templates['ROM']
  for kind in ['pins','OBS']:
   for shape in t[kind]:shapes.append(dict(shape,instance=role['name'],kind=kind,bbox_DBU=helper.translate(shape['bbox_DBU'],*role['origin_DBU'],t['size_DBU'],'R0')))
 body_area=sum((r['bbox_DBU'][2]-r['bbox_DBU'][0])*(r['bbox_DBU'][3]-r['bbox_DBU'][1]) for r in roles)/1e12
 result=dict(schema='opentallas.dsrom.PAR2.physical-read-context.v1',candidate=binding['candidate'],source_main_pin=receipt['source_main_pin'],input_receipt_sha256=sha(OUT/'input_receipt.json'),generator_sha256=sha(Path(__file__)),binding_sha256=sha(BIND/'model.json'),
  source_decoder=dict(path='rtl/dft/ot_rom_secded_dec.sv',sha256=sha(OUT/'inputs/decoder.sv'),actual_existing_implementation=True,packing='cw={overallParity,check[R-1:0],data[K-1:0]}; data Hamming positions3,5,6,7,... excluding powers of2',port_tables={k:{'cw_bits':v['N'],'data_bits':v['K'],'corrected_bits':1,'uncorrectable_bits':1} for k,v in cones.items()},replica_cones=cones,source_word_protection_order='Decode protected256+10 sidecar -> matching8-bit parity for each mainword -> combine272 code/scale payload with2inline+8sidecar checks in exact encoder bit order -> K272 decoder terminal -> arithmetic accept.',main_inline_sidecar_to_282bit_order_adapter_missing=True,existing_module_not_connected_field_decoder_proof=True),
  actual_macro_union=dict(existing_reused_instances=412,additional_instances=0,body_union_mm2=body_area,body_debit_already_in694_screen=True,pin_shapes=sum(s['kind']=='pins' for s in shapes),PG_pin_shapes=sum(s['kind']=='pins' and s.get('use') in ['POWER','GROUND'] for s in shapes),OBS_shapes=sum(s['kind']=='OBS' for s in shapes),artifact='parity_full_pin_OBS.json.gz',origin_roles_prerequisite='reused_macro_roles.json.gz',actual_source_hierarchy_connection='Named candidate roles in existing placement; field integration wrapper does not exist.',PG_pin_rectangles_not_PG_stripes_or_connections=True),
  model_area=binding['area'],finite_source_read_and_deadline=binding['source_service'],routing_incidence=binding['routing'],
  enabled_read_capture=dict(raw_macro_CE_holds_output_when_idle=True,required_input_capture='Capture274 raw bits with same leaf,row,stage,phase,opseq/reset generation and valid. Hold or invalidate on no accepted read; never timer-only completion.',capture_seats=412,request_seats=128,one_leaf_read_port=True,source_capture_adapter_missing=True,source_existing_decoder_is_combinational=True,required_stage_accounting='Source macro launch/capture -> sidecar decoder -> gather identity/parity -> mainword decoder -> arithmetic visibility. Each new mapped stage must have explicit cycles and criticalpath traversals in Maxwell source calendar; diagnostic common+2 is not an automatic decoder credit.',SS_macro_clk_to_q_ps=binding['source_service']['macro_SS_clk_to_q_ps'],remaining_before_setup_wire_ps=binding['source_service']['stream_cycle_margin_after60ps_uncertainty_before_setup_route_ps']),
  rejection_criteria=[{'quantity':'source codeword layout','reject_if':'Protected256+10 sidecar not matched to retained encoder;272+10 mainword check concatenation unbound or mismatched.'},{'quantity':'finite accepted service','reject_if':'Any accepted codeword reaches arithmetic before matching good/corrected terminal; poison/reset/stale/duplicate identity accepted; occupancy>128requests or>412captures.'},{'quantity':'one-cycle sidecar service claim','reject_if':'Packed sameleaf differentrow requests need>1read; retained64-row witness requires64 rounds. Deadline must price exposed serialization or source-approved physical layout remedy.'},{'quantity':'macro/capture SS setup','reject_if':'Actual source enabled capture/mux/load/wire/skew exceeds29.37063310661025ps residual before downstreamsetup, or full extracted WNS<0 at1.2GHz/60ps.'},{'quantity':'decoder/capture FF hold','reject_if':'Any capture/decoder/control min path WNS<0 under25ps with actualclock insertion.'},{'quantity':'physical instance union','reject_if':'Named412leaf decode+256main decode, capture, gather/router, PG/vias/CTS do not fit disjoint source-owned slots within positive5.98752mm2 allowance and whole732.965077 screen; allowances alone cannot pass.'},{'quantity':'routing capacity','reject_if':'Actual translatedOBS, pin escape, PG/via/clock exclusions leave fewer admissible tracks than source incidence cut demand; no universal50%reserve.'}],
  next_research_implementation='Use unchanged retained K256 decoder and actual rawmacro/capture source connection after model/source review; map representative SS/FF cone and localpin/PG context before representative parent P&R. No production DFT/yield/ATE task.',new_builds=0)
 return result,shapes

def main():
 result,shapes=build()
 for name,obj in [('model.json',result),('parity_full_pin_OBS.json.gz',shapes)]:
  data=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode();data=gzip.compress(data,mtime=0) if name.endswith('.gz') else data;p=OUT/name
  if p.exists() and p.read_bytes()!=data:raise ValueError('immutable record changed '+name)
  p.write_bytes(data)
 print(json.dumps({'source_decoder_cones':result['source_decoder']['replica_cones'],'macro_union':result['actual_macro_union'],'new_builds':0}))
if __name__=='__main__':main()
