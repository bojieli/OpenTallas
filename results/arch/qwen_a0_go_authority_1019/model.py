"""Bounded exact native source extraction; no RTL simulation or EDA."""
import collections,gzip,hashlib,itertools,json,pathlib
P=pathlib.Path(__file__).resolve().parent
A=P.parent
parser=A/'qwen_a0_compact_engine_1019/model.py'
g={'__file__':str(parser)}
exec(parser.read_text().split('# The issue assignment')[0],g)
cells,upstream=g['cells'],g['upstream']
def dump(n,x): (P/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def cname(e): return e.rsplit('/',1)[0]
def details(n):
 m,ps=cells[n]
 return {'cell':n,'master':m,'pins':ps,'input_storage_or_ports':{p:sorted(upstream(net)) for p,net in ps.items() if p not in g['outs'](m,ps)}}
cut=json.load(gzip.open(A/'qwen_a0_cut_contract_1019/cross_clock_data_ports.json.gz'))
rows=[]
for r in cut:
 s,t=details(cname(r['producer'])),details(cname(r['consumer']))
 assert s['master']=='DFFHQNx1_ASAP7_75t_R'
 assert s['pins']['CLK']=='ck_fa4' and t['pins']['CLK']=='ck'
 assert s['input_storage_or_ports']['D']==['PORT/'+s['pins']['D']]
 rows.append({'producer':s,'receiver':t,'cut_nets':r['cut_nets'],'external_transaction_identity':None,'native_relative_phase':None,'production_boot_authority':None})
assert len(rows)==24
all_ib=[]
for n,(m,ps) in cells.items():
 if 'u_logic.ib_i' in n:
  all_ib.append(details(n))
roots=json.load(gzip.open(A/'qwen_a0_cut_contract_1019/root_contracts.json.gz'))
rootrows=[]
for r in roots:
 if not r.get('master','').startswith('DFF'):continue
 n=cname(r['driver']);d=details(n)
 witness=r.get('specific_counterexample')
 rootrows.append({'driver':r['driver'],'native':d,'canonical_feedback_input_boundaries':r['canonical_input_source_boundaries'],'original_feedback_preserved':True,'original_reset_preserved':True,'first_storage_controls':r['first_storage_actual_controls'],'inherited_binary_arbitrary_start_witness':witness,'witness_is_production_reset_reachable':None,'qualified_boot_first_use':None,'complete_configuration_identity':None,'authority_status':'UNRESOLVED_EXTERNAL_TAP_AND_NATIVE_PHASE'})
assert len(rootrows)==7
resetrows=[details(n) for n in cells if n.startswith('a0_reset') and cells[n][0].startswith('DFF')]
# Exhaustive one-bit shared-D induction lemma. This checks only the stated
# recurrence, never asserts its premises for a production clone.
checks=[]
for q,c,d,dnext in itertools.product(range(2),repeat=4):
 q1,c1=d,d
 q2,c2=dnext,dnext
 assert q1==c1 and q2==c2
 checks.append({'q0':q,'clone0':c,'D0':d,'D1':dnext,'equal_after_first_common_capture':True})
# Accepted GO cannot establish common identity from GO alone. Enumerate all
# split and wsrc pairs with GO asserted; both are allowed external port words.
identity_pairs=0
for split0,split1,w0,w1 in itertools.product(range(16),range(16),range(2),range(2)):
 if (split0,w0)!=(split1,w1):identity_pairs+=1
assert identity_pairs==992
files=[parser,A/'qwen_a0_reset_1019/r3/candidate.v.gz',A/'qwen_a0_cut_contract_1019/semantic_source.sv',A/'qwen_a0_cut_contract_1019/root_contracts.json.gz',A/'qwen_a0_cut_contract_1019/cross_clock_data_ports.json.gz',A/'qwen_a0_reset_1019/r3/manifest.json']
dump('input_hashes.json',{str(f.relative_to(A.parent.parent)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
# Native field identities are confirmed by canonical root D boundary names;
# packed semantic offsets are only an explicitly conditional NW18/AW24 mapping.
fields=[('mbase',24),('rmax',1),('amax',1),('oen',1),('mmode',1),('ojs',24),('ots',24),('obase',24),('round',1),('wcs',24),('split',4),('jsh',3),('xcs',24),('xjs',24),('xks',24),('xbase',24),('js',24),('ks',24),('ts',24),('wbase',24),('wsrc',1),('k',18),('tiles',18),('nout',18)]
offset=0; packing={}
for name,width in fields:
 packing[name]={'low':offset,'high':offset+width-1};offset+=width
assert packing['split']=={'low':125,'high':128}
assert packing['wsrc']=={'low':324,'high':324}
assert packing['k']=={'low':325,'high':342}
assert offset==379
dump('conditional_semantic_packing.json',{'parameters':{'NW':18,'AW':24},'IBW':offset,'packing':packing,'exact_native_parent_parameter_binding':None,'status':'CONDITIONAL_SEMANTIC_CORRELATION_NOT_PARENT_SUBSTITUTION'})
dump('crossings.json',rows)
dump('all_ib_receivers.json',all_ib)
dump('root_authority.json',rootrows)
dump('reset_sources.json',resetrows)
dump('finite_recurrence.json',{'shared_D_lemma_cases':checks,'GO_alone_distinct_split_wsrc_word_pairs':identity_pairs,'scope':'binary equation and unconstrained external word authority only; not RTL simulation or physical phase proof'})
dump('summary.json',{'status':'SOURCE_AUTHORITY_UNRESOLVED','native_cells':len(cells),'exact_crossings':len(rows),'producer_master':'DFFHQNx1_ASAP7_75t_R','producer_clock':'ck_fa4','consumer_clock':'ck','producer_async_reset_pins':0,'all_ib_receivers':len(all_ib),'sequential_roots':len(rootrows),'reset_sequential_cells':len(resetrows),'boot_first_use':None,'complete_configuration_identity':None,'new_state_selected':None,'new_latency_edges':None,'builds_launched':0})
print(json.dumps(json.load((P/'summary.json').open()),sort_keys=True))
