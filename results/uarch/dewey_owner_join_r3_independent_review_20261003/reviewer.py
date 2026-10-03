import ast,collections,gzip,hashlib,importlib.util,json,subprocess,sys,types
from pathlib import Path
root=Path('/home/ubuntu/OpenTallas-review-dewey-owner-r3');out=Path('/tmp/review-dewey-owner-r3');sys.path.insert(0,str(root/'tools'));sys.path.insert(0,str(root/'tests'))
import h3_complete_native_calendar_owner_join_r3 as m
sha=lambda b:hashlib.sha256(b).hexdigest()
reviewed=subprocess.check_output(['git','rev-parse','b8290b552'],cwd=root,text=True).strip();current=subprocess.check_output(['git','rev-parse','42437d39a'],cwd=root,text=True).strip()
pins={}
for path,want in m.PINS.items():
 archived=(root/path).read_bytes();assert sha(archived)==want,path
 try:now=subprocess.check_output(['git','show',current+':'+path],cwd=root,stderr=subprocess.DEVNULL);s=sha(now)
 except subprocess.CalledProcessError:s=None
 pins[path]=dict(archived_sha256=want,current_main_sha256=s,current_matches_archived=s==want)
req=json.loads((out/'independent_Goodall_requirements.json').read_bytes());assert sha((out/'independent_Goodall_requirements.json').read_bytes())==m.PINS[m.OUT+'/inputs/Goodall_requirements.json']
plan=json.loads(gzip.decompress((root/m.OUT/'inputs/KV_current_plan.json.gz').read_bytes()));native=json.loads(gzip.decompress((root/'results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz').read_bytes()))
join=m.current_consumer_join();raw=[json.loads(x)for x in(out/'raw432.jsonl').read_text().splitlines()];assert len(raw)==432
bykey=collections.defaultdict(list)
for e in raw:bykey[tuple(e['key'])].append(e)
source=(root/'tools/h3_qwen_bounded_native.py').read_bytes();assert sha(source)=='282e57ab97f2dcdd0205b6f4e11ec189b669e3cc48548fab5f6d3c373d63c32b'
tree=ast.parse(source);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='TileWords');method=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='key');ns={};exec(compile(ast.Module(body=[method],type_ignores=[]),'original TileWords.key','exec'),ns)
homes={(v['version'],h['rank'],h['SM']):h for v in native['operands']for h in v['homes']if 'home'in h};mapper=types.SimpleNamespace(homes=homes);plans={tuple(g['key']):g for g in plan['groups']};nativeops={o['pc']:o for o in native['operations']};keys=set();groups=[]
for group in join['groups']:
 key=tuple(group['key']);keys.add(key);events=bykey[key];g=plans[key];assert [e['event']for e in events]==['write_accept','commit_publish','acquire','consumer_done','consumer_done','release'];assert events[3]['stage']=='SCORES'and events[4]['stage']=='PV'
 assert events[0]['tag']==g['writer_tag'] and events[2]['lease']==g['reader_lease']
 assert events[3]['pc']==group['consumer_chain'][0]['pc'] and events[4]['pc']==group['consumer_chain'][2]['pc']
 for o in group['consumer_chain']:
  actual=nativeops[o['pc']];assert all(actual[k]==o[k]for k in ('pc','opcode','reads','writes','dependencies'))
 wanted={(s['version'],s['SM'],s['address'],s['provider_ref'])for s in g['decoded_sectors']};derived=set()
 for v in group['active_cache_mapping']:
  for w in range(512):
   page,lane=ns['key'](mapper,v['version'],w,key[1]);assert page[0]=='HBM';h=homes[v['version'],key[1],page[2]];derived.add((v['version'],page[2],(page[3]+lane*4)&~31,h['provider_ref']))
 assert derived==wanted and len(derived)==128
 for index,e in [(1,events[1]),(2,events[1]),(3,events[2]),(4,events[3]),(5,events[4])]:
  op=g['metadata_writes'][index];address=e['state']['bitmap_address']if index==1 else e['state']['record_address'];payload=bytes([e['state']['bitmap_byte']])if index==1 else bytes.fromhex(e['state']['record_hex']);patch=bytes.fromhex(op['patch_hex']);assert op['source_byte_address']==address;assert patch[address%32:address%32+len(payload)]==payload
 groups.append(dict(key=key,decoded_sectors=128,actual_raw_events=6,consumer_PCs=[o['pc']for o in group['consumer_chain']],metadata_raw_snapshot_match=True))
assert keys==set(bykey)==set(plans) and len(groups)==72
import test_h3_complete_native_calendar_owner_join_r3 as T
mutants={}
def make_retirable():
 t=T.OwnerJoinTests('test_same_SM_contender_waits_through_consumer_and_reverse');t.setUp();t.ACK(read_data=bytes(1024));t.join.merge(**t.key,token=t.token,payload=bytes(t.command['active_words']*4));t.ACK();t.ACK(read_data=bytes(1024));t.join.visibility(**t.key,token=t.token,edge=t.edge);t.edge+=1;t.join.consumer(**t.key,token=t.token,edge=t.edge);t.edge+=1;return t
for label,change in [('wrong_token',{'token':'0'*64}),('wrong_receiver_edge',{'receiver_edge':0}),('unknown_sender_domain',{'sender_domain':'NOT_A_BOUND_CLOCK_DOMAIN'}),('epoch_fields_unsupported',{'sender_epoch':1,'receiver_epoch':1})]:
 t=make_retirable();r=dict(token=t.token,sender_domain='CORE',sender_edge=100,receiver_domain='H1_streaming',receiver_edge=t.edge);r.update(change)
 try:t.join.reverse(**t.key,token=t.token,edge=t.edge,CDC_receipt=r,drain_pins=m.directed_idle_pins(t.join.atomic));mutants[label]=dict(accepted=True,remaining_owner=len(t.join.live))
 except ValueError as e:mutants[label]=dict(accepted=False,error=str(e),remaining_owner=len(t.join.live))
assert not mutants['wrong_token']['accepted'] and not mutants['wrong_receiver_edge']['accepted'];assert mutants['unknown_sender_domain']['accepted'];assert not mutants['epoch_fields_unsupported']['accepted']
r=dict(status='PASS_SOURCE_CONTROL_AND_QWEN_RAW_SPANS_WITH_OPEN_CDC_QUALIFICATION',reviewed_commit=reviewed,current_main_comparison_commit=current,source_tool_sha256=sha((root/'tools/h3_complete_native_calendar_owner_join_r3.py').read_bytes()),source_test_sha256=sha((root/'tests/test_h3_complete_native_calendar_owner_join_r3.py').read_bytes()),pins=pins,independent_requirements_sha256=sha((out/'independent_Goodall_requirements.json').read_bytes()),raw432_sha256=sha((out/'raw432.jsonl').read_bytes()),raw_archive_commit='f9212629928a027742c12bfcfb4a7423b2f0dfd7',Qwen_groups=groups,CDC_mutants=mutants,CDC_epoch_binding='UNIMPLEMENTED_NOT_QUALIFIED; API does not accept reset epochs or bind sender_domain to source',metadata_contract='R3 preserves outdated87ca record-before-bitmap requirement; be3629 actual source correction requires bitmap-before-record plus writer exclusion/fence; no source reorder',production_receipts=False,software_ordinals_are_physical_ticks=False,hardware_qualified=False,R4_authority_review='not reviewed here; no current headline adoption')
(out/'independent_review.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],pins_verified=len(pins),groups=72,events=432,CDC_mutants=mutants),indent=2))
