#!/usr/bin/env python3
"""Static bank/port enumeration for the selected XFIN source; no RTL build/simulation."""
import hashlib,json,math,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[3]
NV,K,P,NVP=80,5,3,128
HB=7

def isadd(n):
 h=HB-(n.bit_length()-1)
 return 1<=n<NVP and (((2*n+1)<<(h-1))-NVP)<NV

def model(mut=False,leaf_mut=False):
 adds=[n for n in range(1,NVP) if isadd(n)]
 def canonical(n):
  while n<NVP and not isadd(n):n*=2
  assert n<NVP or n-NVP<NV
  return n
 def operands(n):
  a,b=2*n,2*n+1
  if mut and n in (4,5):a,b=(8,10) if n==4 else (9,11)
  return canonical(a),canonical(b)
 roles={};consumers={}
 for n in adds:
  for role,c in zip(('LEFT','RIGHT'),operands(n)):
   assert c not in consumers,(c,n,consumers.get(c))
   consumers[c]={'node':n,'role':role}
   if c<NVP:roles[c]=role
 assert len(adds)==79 and len(roles)==78
 assert set(roles)==set(adds)-{1}
 ranked={role:sorted(n for n,r in roles.items() if r==role) for role in ('LEFT','RIGHT')}
 assert all(len(v)==39 for v in ranked.values())
 pair_types={'leaf_leaf':0,'internal_internal':0,'mixed':0};checks=0
 for n in adds:
  aa,bb=operands(n)
  typ=('leaf_leaf' if aa>=NVP and bb>=NVP else 'internal_internal' if aa<NVP and bb<NVP else 'mixed')
  pair_types[typ]+=1
  aopts=range(P) if aa>=NVP else [None]
  bopts=range(P) if bb>=NVP else [None]
  for pa in aopts:
   for pb in bopts:
    def bank(c,port):
     if c>=NVP:
      ix=c-NVP
      if leaf_mut and ix==1:ix=2
      return ('LEAF',port,ix%K)
     return ('INTERNAL',roles[c])
    assert bank(aa,pa)!=bank(bb,pb),(n,aa,bb,pa,pb)
    checks+=1
 return {'real_add_nodes':adds,'stored_internal_by_role':ranked,
         'pair_types':pair_types,'read_owner_cases_no_conflict':checks,
         'canonical_alias_example':{'raw_child':3,'canonical_value':canonical(3),'consumer':consumers[canonical(3)]},
         'role_map':{str(n):r for n,r in roles.items()},
         'consumer_map':{str(n):v for n,v in consumers.items()}}

base=model();eassoc=model(mut=True);leafmut=model(leaf_mut=True)
# Norm flits can start at ANY 8-bit base. Widened base+k never wraps.
max_per_bank=0;max_writes=0
for base_in in range(256):
 counts={};total=0
 for k in range(K):
  ix=base_in+k
  if ix<NV:counts[ix%K]=counts.get(ix%K,0)+1;total+=1
 assert max(counts.values(),default=0)<=1
 max_per_bank=max(max_per_bank,max(counts.values(),default=0));max_writes=max(max_writes,total)
assert max_per_bank==1 and max_writes==5
profiles={}
for name,trees in [('ENG',3),('NORM',1)]:
 leaf_values=trees*(NV//K);role_values=trees*39
 leaf_rows=(leaf_values+1)//2;role_macros=(role_values+63)//64
 assert leaf_rows<=32
 count=P*K+2*role_macros
 profiles[name]={'trees':trees,'leaf_banks':P*K,'leaf_values_per_bank_address_space':leaf_values,
  'leaf_active_rows_per_macro':leaf_rows,'leaf_macros_per_bank':1,
  'internal_values_per_role':role_values,'internal_macros_per_role':role_macros,
  'internal_used_rows_total_per_role':(role_values+1)//2,'macros':count,
  'logical_leaf_values':trees*NV,'logical_internal_stored_values':trees*78,
  'owner_bits':trees*NV*2}
assert profiles['ENG']['macros']==19 and profiles['NORM']['macros']==17
primitive='physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1'
sha={}
for ext in ['.v','.lef','_bb.v','_tt.lib','_ff.lib','_ss.lib']:
 p=ROOT/(primitive+ext);sha[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
source='rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv';sha[source]=hashlib.sha256((ROOT/source).read_bytes()).hexdigest()
out={'schema':'opentallas.xfin_sram_model.v1','status':'MODEL_ONLY_NO_BUILD',
 'source_commit':'0618133cbc','params':{'NV':NV,'K':K,'P':P,'NS':16,'LM':5,'LA':6},
 'primitive':{'master':'ot_sram_1r1w_32x64_m1','depth':32,'bits':64,'address_bits':5,
  'read_ports':1,'write_ports':1,'same_clock':True,'read_latency_edges':1,
  'read_during_same_address_write':'OLD_WORD','write_mask':'64 active-high per-bit enables',
  'size_um':[31.968,17.28],'area_um2':31.968*17.28},
 'profiles':profiles,'xfin':{'ENG_instances':4,'NORM_instances':1,'trees':13,
  'macros':4*19+17,'macro_area_um2':(4*19+17)*31.968*17.28,
  'macro_capacity_bits':93*32*64,'persistent_value_bits_before':13*(80+79)*32,
  'persistent_value_bits_in_SRAM':13*(80+78)*32,'root_result_bits_existing_capture':13*32,
  'additional_owner_bits':4*profiles['ENG']['owner_bits']+profiles['NORM']['owner_bits'],
  'maximum_leaf_writes_per_cycle':15,'maximum_internal_writes_per_cycle':1,
  'no_new_payload_edges_proposed':True,'first_output_dates':'UNCLAIMED_UNTIL_EXISTING_RTL_PROOF'},
 'static_port_enumeration':{'norm_all_8bit_bases':256,'max_writes_per_leaf_bank':max_per_bank,
  'max_writes_per_input_port':max_writes,'production':base,'EASSOC':eassoc,'LEAF':leafmut},
 'sha256':sha}
p=pathlib.Path(__file__).with_name('MODEL.json');p.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'macros':out['xfin']['macros'],'area_um2':out['xfin']['macro_area_um2'],
 'roles_per_tree':[39,39],'port_owner_cases_per_tree':base['read_owner_cases_no_conflict'],
 'pair_types':base['pair_types'],'additional_owner_bits':out['xfin']['additional_owner_bits']},sort_keys=True))
