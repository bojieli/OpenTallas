import copy, importlib.util, json, unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'tools/h4_hbm_native_frame_emitter.py'
s=importlib.util.spec_from_file_location('native_frame_r5',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class FrameEmitterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.catalog=m.catalog();cls.compiler=m.NativeCompiler()
  # Actual immutable DS SELECT leaf supplies PC/template/step/attrs. I64 payload views are protocol controls, not inferred source types. Payload
  # addresses below are explicit protocol controls, not production homes.
  candidates=[]
  for PC,op in enumerate(cls.catalog['DeepSeek']['ops']):
   if not op['reads'] or not op['writes']:continue
   for template,code in op['leaves'].items():
    if 0 not in op['ranks'][template]:continue
    for step,node in enumerate(code):
     if node['op']=='SELECT' and len(node['src'])==3:candidates.append((PC,op,template,step,node))
   if candidates:break
  if not candidates:raise AssertionError('actual source SELECT leaf absent')
  PC,op,template,step,node=candidates[0];home={'rank':0,'SM':0,'generation':2**40,'physical_RF_id':'control-RF-0'}
  sources=[];slot=0
  for i,bits in enumerate((32,64,64)):
   h=dict(home,version=sorted(op['reads'])[0],lease='source-'+str(i),RF_vectors=list(range(slot,slot+bits//32)));slot+=bits//32;sources.append(h)
  dest=dict(home,version=sorted(op['writes'])[0],lease='dest',RF_vectors=[slot,slot+1])
  cls.command=dict(model='DeepSeek',family=op['family'],source_PC=PC,program_sha256=cls.catalog['DeepSeek']['hash'],template_id=template,ordered_step_index=step,owner_tag=2**48,generation=2**40,rank=0,SM=0,opcode='SELECT',source_bittypes=[32,64,64],destination_bittype=64,source_version_home_refs=sources,destination_version_home_ref=dest,predicate='source U32',active_lanes=128,source_attrs_rounding=copy.deepcopy(node.get('attrs',{})),response_stall_bound=4)
  cls.binding=dict(model='DeepSeek',rank=0,SM=0,physical_RF_id='control-RF-0',die=0,scope='software_reference',operand_view_scope='protocol_control')
  cls.addresses={}
  for h in sources+[dest]:
   for word,slot in enumerate(h['RF_vectors']):cls.addresses[h['version'],h['lease'],word]=33554432+slot*512
  cls.plan=cls.compiler.compile(cls.command,cls.addresses,cls.binding,0)
 def runtime(self):
  a=m.SourceAllocator(0);ref=a.parent(self.plan,0);r=m.ContinuedCapture(self.plan,ref,a);return a,r
 def fragment(self,a,r):
  frame=r.frame;frag=r.fragment;requests=[]
  for sector in (2*frag,2*frag+1):
   q=a.propose(self.plan,frame,sector)
   if self.plan['frames'][frame]['kind']=='destination_writeback' and not r.writeback_captured:
    r.writeback_RF_capture((r.owners[frame]<<9)|self.plan['frames'][frame]['RFslot9'],bytes([frame])*512)
   requests.append(a.accept(0,q))
  r.admit(frag,requests)
  for q in requests:
   sector=q['child']['sector'];token=frame*16+sector
   if self.plan['frames'][frame]['kind']=='source_refill':r.returned(sector,q['child_owner46'],q['meta92'],token,bytes([sector])*32)
   else:r.returned(sector,q['child_owner46'],q['meta92'],token,None,backing_visible=True)
  return r.continue_capture()
 def complete(self,a,r):
  while r.frame<len(self.plan['frames']):
   frame=r.frame
   for _ in range(8):self.fragment(a,r)
   if self.plan['frames'][frame]['kind']=='source_refill':self.assertEqual(r.assembled(),b''.join(bytes([i])*32 for i in range(16)))
   r.frame_ACK((r.owners[frame]<<9)|self.plan['frames'][frame]['RFslot9'])
  r.consumer_accept()
  for (f,sector),row in r.children.items():r.reverse_child(f,sector,row['request']['child_owner46'],f*16+sector,matched_CDC=True)
 def test_actual_program_inventory_and_envelope(self):
  d=m.model();self.assertEqual((d['programs']['Qwen']['PCs'],d['programs']['DeepSeek']['PCs']),(1737,2213));self.assertEqual((d['programs']['Qwen']['families'],d['programs']['DeepSeek']['families']),(21,30))
  self.assertEqual((d['frame_rows'],d['child_rows'],d['protected_gross_bits']),(256,4096,940464));self.assertEqual(d['additional_RF_data_bits'],0)
 def test_typed_SELECT_emits7frames_not_padding_to8(self):
  self.assertEqual(self.plan['children'],112);self.assertEqual(self.plan['fragments'],56);self.assertEqual(len(self.plan['frames']),7)
  self.assertEqual(self.plan['native_command'],self.command)
 def test_production_views_cannot_be_inferred_from_leaf_inventory(self):
  b=dict(self.binding,operand_view_scope='production')
  with self.assertRaises(ValueError):self.compiler.compile(self.command,self.addresses,b,0)
  self.assertFalse(self.plan['operand_views_production_admitted'])
 def test_actual_leaf_opcode_and_rounding_refuse(self):
  for field,value in [('opcode','IMUL'),('source_attrs_rounding',{'dtype':'F32'}),('program_sha256','0'*64)]:
   c=copy.deepcopy(self.command);c[field]=value
   with self.assertRaises(ValueError):self.compiler.compile(c,self.addresses,self.binding,0)
 def test_wrong_home_missing_address_and_packed_partial_refuse(self):
  c=copy.deepcopy(self.command);c['source_version_home_refs'][0]['version']='invented'
  with self.assertRaises(ValueError):self.compiler.compile(c,self.addresses,self.binding,0)
  with self.assertRaises(ValueError):self.compiler.compile(self.command,{},self.binding,0)
  c=copy.deepcopy(self.command);c['active_lanes']=64
  with self.assertRaises(ValueError):self.compiler.compile(c,self.addresses,self.binding,0)
 def test_KV5_not_reassigned_and_DS_die_not_from_rank(self):
  with self.assertRaises(ValueError):self.compiler.compile(self.command,self.addresses,self.binding,5)
  b=dict(self.binding,die=96)
  with self.assertRaises(ValueError):self.compiler.compile(self.command,self.addresses,b,0)
 def test_tuple_stall_and_parent_binding_before_W2(self):
  a,r=self.runtime();q=a.propose(self.plan,0,0);self.assertEqual(a.next[0],0);self.assertEqual(r.owners[0],q['child_owner46'])
  with self.assertRaises(ValueError):a.propose(self.plan,0,0)
  self.assertEqual(a.held[0],q);a.accept(0,q);self.assertEqual(a.next[0],1);self.assertEqual(a.parents[0]['native']['owner_tag'],2**48)
 def test_tuple_carry_not_native64_truncation(self):
  a,r=self.runtime();a.next[0]=2**32-1;q=a.propose(self.plan,0,0);self.assertEqual(q['tag32'],2**32-1);a.accept(0,q)
  q=a.propose(self.plan,0,1);self.assertEqual((q['tag32'],q['producer_gen4']),(0,1));self.assertEqual(a.parents[0]['native']['generation'],2**40)
 def test_exhaustion_requires_fence_not_runtime_cap(self):
  a,r=self.runtime();a.next[0]=2**36
  with self.assertRaises(ValueError):a.propose(self.plan,0,0)
  with self.assertRaises(ValueError):a.rearm({})
 def test_one_global_parent_port_and_physical_alias_exclusion(self):
  a,r=self.runtime();p=copy.deepcopy(self.plan);p['native_command']['SM']=1;p['binding']['SM']=1
  with self.assertRaises(ValueError):a.parent(p,0)
  with self.assertRaises(ValueError):a.parent(p,1)
 def test_continuation_after64B_does_not_release_physical_lease(self):
  a,r=self.runtime();event=self.fragment(a,r);self.assertEqual(r.fragment,1);self.assertEqual(len(r.children),2);self.assertFalse(event['physical_reverse']);self.assertFalse(r.parent_ready())
  self.fragment(a,r);self.assertEqual(r.fragment,2);self.assertEqual(len(r.children),4)
 def test_credit_held_to_commonACK_is_constructive_deadlock(self):
  self.assertLess(1*64,512);a,r=self.runtime();self.fragment(a,r)
  # The old join cannot obtain a commonACK after just one fragment. The
  # continued-capture path admits the next fragment while physical debt stays.
  with self.assertRaises(ValueError):r.frame_ACK((r.owners[0]<<9)|self.plan['frames'][0]['RFslot9'])
  self.assertEqual(len(r.children),2)
 def test_no_continuation_before_both_sector_captures(self):
  a,r=self.runtime();qs=[]
  for sector in (0,1):qs.append(a.accept(0,a.propose(self.plan,0,sector)))
  r.admit(0,qs);q=qs[0];r.returned(0,q['child_owner46'],q['meta92'],0,bytes(32))
  with self.assertRaises(ValueError):r.continue_capture()
  self.assertIsNotNone(r.seat);self.assertEqual(r.capture_releases,0)
 def test_bad_owner_is_sticky_and_cannot_return_seat(self):
  a,r=self.runtime();qs=[a.accept(0,a.propose(self.plan,0,s)) for s in (0,1)];r.admit(0,qs);q=qs[0]
  with self.assertRaises(ValueError):r.returned(0,q['child_owner46']^1,q['meta92'],0,bytes(32))
  with self.assertRaises(ValueError):r.returned(0,q['child_owner46'],q['meta92'],0,bytes(32))
  self.assertTrue(r.fault);self.assertEqual(r.capture_releases,0)
 def test_mutated_candidate_cannot_impersonate_W2_accept(self):
  a,r=self.runtime();qs=[a.accept(0,a.propose(self.plan,0,s)) for s in (0,1)];qs[0]['child_owner46']^=1
  with self.assertRaises(ValueError):r.admit(0,qs)
  self.assertFalse(r.children)
 def test_physical_tag12_reuse_refused_even_with_new_backend_generation(self):
  a,r=self.runtime();qs=[a.accept(0,a.propose(self.plan,0,s)) for s in (0,1)];r.admit(0,qs);q=qs[0];r.returned(0,q['child_owner46'],q['meta92'],0,bytes(32));q=qs[1]
  with self.assertRaises(ValueError):r.returned(1,q['child_owner46'],q['meta92'],1<<12,bytes(32))
 def test_backend_generation_high4_retained_independently(self):
  a,r=self.runtime();qs=[a.accept(0,a.propose(self.plan,0,s)) for s in (0,1)];r.admit(0,qs)
  for sector,q in enumerate(qs):r.returned(sector,q['child_owner46'],q['meta92'],(10<<12)|sector,bytes(32))
  r.continue_capture();self.assertEqual(r.children[0,0]['physical'][3],10)
  self.assertEqual(qs[0]['producer_gen4'],0);self.assertEqual(r.children[0,1]['physical'][2],1)
 def test_one_assembler_reuse_keeps_all_completed_frame_identities(self):
  a,r=self.runtime()
  for _ in range(8):self.fragment(a,r)
  r.frame_ACK((r.owners[0]<<9)|self.plan['frames'][0]['RFslot9']);self.assertEqual(r.frame,1);self.assertEqual(len(r.data),512);self.assertEqual(len(r.children),16)
  self.assertFalse(r.consumer);self.assertFalse(r.parent_ready())
 def test_exact_parent55_slot_mutation_refuses(self):
  a,r=self.runtime()
  for _ in range(8):self.fragment(a,r)
  with self.assertRaises(ValueError):r.frame_ACK(((r.owners[0]<<9)|self.plan['frames'][0]['RFslot9'])^1)
  self.assertEqual(r.frame,0)
 def test_parent_held_until_all_child_reverseCDC(self):
  a,r=self.runtime();self.complete(a,r);self.assertEqual(len(r.children),112);self.assertTrue(r.parent_ready());a.retire(0,r.parentref,{'source':'software_reference_allcopies','empty':True},r);self.assertFalse(a.parents)
 def test_positive_calendar_capture_vs_reverse_and_no_duplicate_eventIDs(self):
  profile={k:dict(ns=1.0,domain='MODEL_FAST',source='explicit positive test profile') for k in m.COSTS};c=m.calendar(self.plan,profile);events=c['events'];ids=[r['eventID'] for r in events]
  self.assertEqual(len(set(ids)),len(ids));self.assertEqual(c['peak_retained_children'],112);self.assertEqual(c['RF_data_bits_reserved_once'],4096)
  self.assertEqual(sum(r['cost_key']=='continuation' for r in events),56)
  self.assertEqual(sum(r['cost_key']=='capture_data' for r in events),112)
  self.assertEqual(sum(r['cost_key']=='capture_metadata' for r in events),112)
  self.assertEqual(sum(r['cost_key']=='allocate_metadata' for r in events),112)
  self.assertEqual(sum(r['cost_key']=='reverse_metadata' for r in events),112)
  self.assertEqual(sum(r['cost_key']=='native_compute' for r in events),1)
  first_reverse=next(i for i,r in enumerate(events) if r['cost_key']=='reverse_route');last_capture=max(i for i,r in enumerate(events) if r['cost_key']=='continuation');self.assertGreater(first_reverse,last_capture)
  writeframe=next(f['frame'] for f in self.plan['frames'] if f['kind']=='destination_writeback');ack=next(i for i,r in enumerate(events) if r['eventID'].endswith(f'/f{writeframe}/commonACK'));wr=next(i for i,r in enumerate(events) if r['cost_key']=='backend_write_visible');self.assertLess(ack,wr)
 def test_calendar_zero_cost_refuses(self):
  p={k:dict(ns=1,domain='MODEL_FAST',source='test') for k in m.COSTS};p['capture_metadata']['ns']=0
  with self.assertRaises(ValueError):m.calendar(self.plan,p)
 def test_frame_slot_alias_without_lifetime_join_refuses(self):
  c=copy.deepcopy(self.command);c['destination_version_home_ref']['RF_vectors'][0]=0
  with self.assertRaises(ValueError):self.compiler.compile(c,self.addresses,self.binding,0)
 def test_out_of_width_backend_token_latches_fault(self):
  a,r=self.runtime();qs=[a.accept(0,a.propose(self.plan,0,s)) for s in (0,1)];r.admit(0,qs);q=qs[0]
  with self.assertRaises(ValueError):r.returned(0,q['child_owner46'],q['meta92'],1<<16,bytes(32))
  self.assertTrue(r.fault);self.assertFalse(r.parent_ready())

if __name__=='__main__':unittest.main()
