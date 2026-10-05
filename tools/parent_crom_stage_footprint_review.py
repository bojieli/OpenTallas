import gzip,json,subprocess,ast,types,collections,hashlib
from pathlib import Path
sources={'demand':('f4bce8fa0','results/uarch/w11_crom_demand_20261001/demand_v2.json.gz'),'program':('4080bb5fd','results/rtl/w17_connected_token_preparation_20261001/full40_crom_bound_templates_v2.rank0.templates.bin.gz'),'ISA':('d2c28c279','tools/hdc_isa_v41.py'),'batches':('7ed62357d','tools/w11_dsrom_crom_demand.py')}
raw={k:subprocess.check_output(['git','show',c+':'+p]) for k,(c,p) in sources.items()}
d=json.loads(gzip.decompress(raw['demand']));recs=d['ranks'][0]['records'];assert all(x['records']==recs for x in d['ranks'])
binary=gzip.decompress(raw['program']);I=types.ModuleType('pinned_ISA');I.__file__=str(Path('tools/hdc_isa_v41.py').resolve());exec(compile(raw['ISA'],'<ISA>','exec'),I.__dict__)
nodes=[n for n in ast.parse(raw['batches']).body if isinstance(n,ast.FunctionDef) and n.name in ('clog','batches')];env={'I':I};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<batches>','exec'),env)
by=collections.defaultdict(set);commands=collections.Counter();reads=0
for rec in recs:
 f=I.decode(int.from_bytes(binary[rec['global_instruction']*256:(rec['global_instruction']+1)*256],'little'),full_shape=True);commands[rec['layer']]+=1
 for coords in env['batches'](f):
  aset=set()
  for o in rec['operand_demands']:
   for outer,inner in coords:
    a=o['base']+outer*o['outer_stride']+(inner//2 if o['half_inner'] else inner)*o['inner_stride']
    if o['kind']=='unbound_generated':a+=508800+(20480 if rec['layer']==14 else 0)
    aset.add(a)
  by[rec['layer']].update(aset);reads+=len(aset)
assert len(recs)==491 and reads==549760
rows=[{'layer':l,'commands':commands[l],'distinct_logical64_words':len(a),'dense_storage_only_minimum4096x3_banks':(len(a)+12287)//12288,'invalid_L1_source_words':sum(508800<=v<529280 for v in a),'local_dense_address_map_sha256':hashlib.sha256(json.dumps(sorted(a),separators=(',',':')).encode()).hexdigest()} for l,a in sorted(by.items(),key=lambda kv:(isinstance(kv[0],str),kv[0]))]
o={'schema':'parent_CROM_stage_read_footprint','generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'pins':{k:{'commit':c,'path':p,'sha256':hashlib.sha256(raw[k]).hexdigest()} for k,(c,p) in sources.items()},'all_four_rank_demand_metadata_equal':True,'decoded_rank':0,'actual_commands':491,'emit_deduplicated_coefficient_uses':reads,'stages':rows,'distinct_stage_copies_sum':sum(x['distinct_logical64_words'] for x in rows),'maximum_stage_words':max(x['distinct_logical64_words'] for x in rows),'scope':'Decoded rank0 operand address footprint with proposed frozen generated spans; actual generated bases remain unencoded. Dense storage capacity only. Does not repack values, preserve read-port bandwidth, compile new bank-wave/fill catalog, place macros, or prove service timing. No bank-count adoption.','current_full_rank_words':549760,'current_full_rank_banks_per_home':45,'required_next':['regular maximum-stage-sized geometry with explicit selected-port bandwidth','complete source value map including invalid L1 hole','exact new bank-wave and fill-mask catalog for all491 commands','all source consumer deadlines, service, physical fit and contextual closure'],'hardware_admission':False,'checkpoint_payload_reads':0}
b=Path('results/rtl/parent_crom_frozen_closure_review_20261001');(b/'stage_footprint.json').write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
print([(x['layer'],x['distinct_logical64_words'],x['dense_storage_only_minimum4096x3_banks']) for x in rows]);print('sum',o['distinct_stage_copies_sum'],'max',o['maximum_stage_words'])
