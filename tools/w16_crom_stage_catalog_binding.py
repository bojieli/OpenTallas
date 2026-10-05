"""Exact dense relocation correspondence for owner stage unions and canonical PCs.

This supplies compiler/deadline input, not a new bank choice, image producer or
calendar. Existing global catalog identities are retained solely as source refs.
"""
import argparse,ast,gzip,hashlib,json
from pathlib import Path
from tools.w16_review_crom_control_join import blob,load_tool,require
from tools import w16_crom_program_deadline_contract as C

UNION_COMMIT='dc6e2c8cfb9ec6d80bc6327b428309e0253a1b3f'
UNION_PATH='results/uarch/w11_stage_crom_union_20261001/read_union.json.gz'
FOOT_COMMIT='7082475e079ede86bfab86f7bbb4a3b310a4cb69'
FOOT_PATH='results/rtl/parent_crom_frozen_closure_review_20261001/stage_footprint.json'

def digest(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),sort_keys=True).encode()).hexdigest()

def dense_map(stage):
 values=[a for start,end in stage['ranges'] for a in range(start,end)]
 require(values==sorted(set(values)) and len(values)==stage['unique_words'],'exact sorted stage union')
 return {a:i for i,a in enumerate(values)}

def bind_operand(source,canonical,f,coords,mapping,ordinal):
 axis=source['operand']
 require(axis==canonical['operand'] and source['tensor']==canonical['tensor'] and source['kind']==canonical['kind'],'source operand identity')
 require((source['original_encoded_base'],source['outer_stride'],source['inner_stride'],source['half_inner'])==
         (canonical['base'],canonical['outer_stride'],canonical['inner_stride'],canonical['half_inner']),'source address axes')
 global_base=source['original_encoded_base']
 if source['kind']=='unbound_generated':
  # Frozen producer span, not an encoded replacement source.
  require(len(source['global_ranges'])==1 and source['global_ranges'][0][1]-source['global_ranges'][0][0]==20480,'generated span')
  global_base=source['global_ranges'][0][0]
 require(global_base in mapping,'source operand outside stage')
 local_base=mapping[global_base];affine=True;bursts=[];uses=0
 for bi,positions in enumerate(coords):
  targets=[]
  for lane,(outer,inner) in enumerate(positions):
   offset=outer*source['outer_stride']+(inner//2 if source['half_inner'] else inner)*source['inner_stride']
   global_address=global_base+offset
   require(global_address in mapping,'lane omitted from stage union')
   local=mapping[global_address];affine &= local==local_base+offset
   targets.append([ordinal,lane,local]);uses+=1
  bursts.append(dict(burst=bi,destination_uses=len(targets),operand_lane_local_address_SHA256=digest(targets)))
 return dict(operand_axis=axis,tensor=source['tensor'],source_valid=source['source_valid'],source_provenance=source['provenance'],
  frozen_global_base=global_base,proposed_dense_local_base=local_base,
  original_outer_stride=source['outer_stride'],original_inner_stride=source['inner_stride'],half_inner=source['half_inner'],
  exact_same_stride_translation=bool(affine),destination_uses=uses,bursts=bursts,
  compiler_action='Replace operand base only after source/ISA/repacked-image gates' if affine else 'Explicit new address/descriptor encoding required; base-only translation REFUSED')

def build():
 raw,up=blob(UNION_COMMIT,UNION_PATH);union=json.loads(gzip.decompress(raw))
 fr,fp=blob(FOOT_COMMIT,FOOT_PATH);foot=json.loads(fr)
 # Reuse prior exact canonical verifier and program dependency contract.
 contract=C.build();catalog_raw,cp=blob(C.CAT_COMMIT,C.CAT_PREFIX+'catalog.json.gz');catalog=json.loads(gzip.decompress(catalog_raw))
 commands={c['pc']:c for c in catalog['commands']};pcs={p['PC']:p for p in contract['program']}
 isa_raw,ip=blob('d2c28c279','tools/hdc_isa_v41.py');isa=load_tool(isa_raw,'stage_catalog_pinned_ISA')
 batchraw,bp=blob('7ed62357d','tools/w11_dsrom_crom_demand.py')
 nodes=[n for n in ast.parse(batchraw).body if isinstance(n,ast.FunctionDef) and n.name in ('clog','batches')]
 env=dict(I=isa);exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pinned emit axes>','exec'),env)
 checked=[]
 for pin in union['source_pins']:
  data,actual=blob(pin['commit'],pin['path']);decoded=gzip.decompress(data) if pin['path'].endswith('.gz') else data
  require(hashlib.sha256(decoded).hexdigest()==pin['decoded_sha256'],'union source');checked.append(actual)
 require(len(union['ranks'])==4 and union['max_regular_stage_words']==foot['maximum_stage_words']==33648,'stage/rank inventory')
 parent={s['layer']:s for s in foot['stages']};outputs=[];product_pins={}
 for rank in union['ranks']:
  rid=rank['rank'];binary=gzip.decompress(blob(C.PROGRAM_COMMIT,C.PROGRAM_PREFIX+f'.rank{rid}.templates.bin.gz')[0])
  require(hashlib.sha256(binary).hexdigest()==rank['original_program_sha256'],'rank program source')
  stage_rows=[];visited=set();count=0
  for stage in rank['stages']:
   mapping=dense_map(stage);values=list(mapping)
   require(len(mapping)==parent[stage['layer']]['distinct_logical64_words'] and digest(values)==parent[stage['layer']]['local_dense_address_map_sha256'],'parent dense union identity')
   require(stage['invalid_words']==parent[stage['layer']]['invalid_L1_source_words'],'L1 hole preserved')
   translations=[];cursor=0
   for start,end in stage['ranges']:
    translations.append(dict(global_range=[start,end],dense_local_range=[cursor,cursor+end-start]));cursor+=end-start
   bound=[]
   for cmd in stage['commands']:
    pc=cmd['pc'];f=isa.decode(int.from_bytes(binary[pc*256:(pc+1)*256],'little'),full_shape=True);canonical=commands[pc]
    require(pc not in visited and (canonical['layer'],canonical['pred'])==(stage['layer'],cmd['pred'])==(pcs[pc]['layer'],f['pred']),'unique PC/layer/predicate')
    visited.add(pc);coords=list(env['batches'](f));by_axis={o['operand']:o for o in cmd['operands']}
    require(set(by_axis)=={o['operand'] for o in canonical['operands']},'all source axes')
    operands=[]
    for ordinal,o in enumerate(canonical['operands']):
     item=bind_operand(by_axis[o['operand']],o,f,coords,mapping,ordinal);operands.append(item);count+=item['destination_uses']
     provenance=item['source_provenance']
     if provenance['kind']=='retained_generated_product':
      data,pin=blob(provenance['product_commit'],provenance['product_path']);require(hashlib.sha256(gzip.decompress(data)).hexdigest()==provenance['product_sha256'],'retained L14 logical bits');product_pins[str(rid)+':'+str(pc)]=pin
    require(sum(o['destination_uses'] for o in operands)==sum(b['coefficient_uses'] for b in canonical['bursts']),'canonical use counts')
    bound.append(dict(PC=pc,local_PC=cmd['local_pc'],pred=f['pred'],instruction_sha256=pcs[pc]['instruction_sha256'],
     encoded_wait_predecessor_PCs=pcs[pc]['encoded_wait_predecessor_PCs'],operands=operands,
     canonical_burst_source_refs=[dict(burst=b['burst'],request_fill_global_catalog_refs=b['waves']) for b in canonical['bursts']],
     future_local_bank_waves=None,future_fragmented16word_packets=None,
     cold_fill_visible_and_reverse_credit_ticks=None,actual_prerequisite_retire_tick=None,earliest_consumer_issue_tick=None,
     deadline_constraint='New stage-local fillvalid AND matching returned credits -> priced local register arrival -> actual issue. Prior lease held to consumer lastuse. Old45bank timing is unavailable here.'))
   stage_rows.append(dict(layer=stage['layer'],rank=rid,words=len(mapping),dense_source_map_sha256=digest(values),translation_ranges=translations,
    invalid_source_words=stage['invalid_words'],all_source_values_available=stage['invalid_words']==0,
    shared_constant_operands=stage['global_constant_operands'],commands=bound,
    actual_repacked_image_SHA256=None,image_publication_allowed=False,actual_bank_count=None,catalogue_recompiled=False,hardware_admission=False))
  require(visited==set(commands) and count==549760,'all491PC/all coefficient use relocation')
  outputs.append(dict(rank=rid,source_image_sha256=contract['rank_bindings'][rid]['CROM_image_sha256'],stages=stage_rows,
   PCs_bound=len(visited),destination_uses_bound=count))
 return dict(schema='opentallas.w16.CROM-stage-catalog-relocation-binding.v1',union_pin=up,parent_footprint_pin=fp,
  catalog_pin=cp,ISA_pin=ip,emit_axis_pin=bp,verified_source_pins=checked,retained_L14_product_pins=product_pins,
  ranks=outputs,maximum_stage_words=33648,canonical_generated_L1_invalid_words=20480,
  all_operand_base_only_relocations_proven=all(o['exact_same_stride_translation'] for r in outputs for s in r['stages'] for c in s['commands'] for o in c['operands']),
  per_rank_operand_bindings=731,actual_stage_image_producer_bound=False,
  physical_bank_count=None,old45bank_calendar_transferred=False,actual_operator_cycle_provider=None,
  next_owner_inputs='Ram/Fermat chosen stage bank/read-port map, source-exact local catalog and fragmented16word fill/control calendar; Pasteur slots. Bind selected/capture/local arrival, both routes, CDC/sharedports, actual issue and held lease events before wholepoint.',
  checkpoint_payload_reads=0,physical_admission=False,headline_rate=None,jobs_launched=0)

if __name__=='__main__':
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--out',type=Path);g.add_argument('--check',type=Path);a=p.parse_args()
 text=json.dumps(build(),sort_keys=True,indent=2).encode()+b'\n'
 if a.check:require(gzip.decompress(a.check.read_bytes())==text,'stage binding receipt mismatch');print('PASS source-exact stage relocation correspondence; local bank/calendar/admission UNBOUND')
 else:
  with a.out.open('xb') as f:f.write(gzip.compress(text,mtime=0))
