#!/usr/bin/env python3
"""Replay passive historical TP4-pos0 exports; no current physical transfer."""
import argparse,gzip,json,hashlib
from pathlib import Path
from qwen_rom_program_identity import decoded,sha
from qwen_rom_accepted_stage_journal import DispatchJournal
from qwen_rom_persistent_kv_g0 import Owner
from qwen_rom_kv_launch_readiness import FIELDS,instruction
from qwen_rom_kv_production_join import producer_byte

def file_sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def replay(bundle,raw,require_reads=False,layers=36):
 if type(layers) is not int or not 1<=layers<=36:raise ValueError("historical prefix layer aperture")
 if (bundle['su_width'],bundle['ar_words'],bundle['TP'],bundle['groups'])!=(64,128,4,6144):raise ValueError('frozen historical program/config only')
 gates={};snapshots={};tickets={};writers={};controls={};lifetimes={};memory={};last_me={};last_write_edge={};read_slots={};read_edges={}
 for layer in range(layers):
  for rank in range(4):
   key=f'L{layer}/die{rank}';f=bundle['stages'][key]['files'];owner=Owner(0,rank,layer,0)
   g=DispatchJournal(decoded(f['program.hex']),decoded(f['segments.hex']),owner,0,0)
   gates[(layer,rank)]=g;controls[(layer,rank)]=[];lifetimes[(layer,rank)]={'producer_accepts':[],'KV_consumer_accepts':[],'descriptor_events':[],'committed_writes':[],'first_committed_write_edge':None,'last_committed_write_edge':None,'snapshot_edge':None,'source_port_reads':{},'current_row_first_read':{}};snapshots[(layer,rank)]={};tickets[(layer,rank)]=0
   addresses={}
   for pc,aa in g.stage.producer.expected.items():
    for a in aa:
     if a in addresses:raise ValueError('ambiguous producer source address partition')
     addresses[a]=pc
   writers[(layer,rank)]=addresses;memory[(layer,rank)]={};last_write_edge[(layer,rank)]=-1
 for line in (raw.splitlines() if isinstance(raw,str) else raw):
  if not line:raise ValueError('empty raw record')
  a=line.split();kind=a[0]
  if len(a)<4:raise ValueError('short source record')
  edge,layer,rank=map(int,a[1:4]);key=(layer,rank)
  if key not in gates:raise ValueError('actual full36layer4rank identity')
  g=gates[key];common={'owner':dict(vars(g.stage.owner)),'edge':edge}
  if kind=='B':
   if len(a)!=5 or not 0<=int(a[4])<=7:raise ValueError('actual binary control state')
   history=controls[key]
   if history and edge<history[-1]['edge']:raise ValueError('control source edge order')
   flags=int(a[4]);history.append({'edge':edge,'me_idle':flags&1,'su_idle':(flags>>1)&1,'su_ready':(flags>>2)&1})
  elif kind in ('S','D'):
   if len(a)!=7:raise ValueError('dispatch record width')
   seg,base=int(a[4]),int(a[5]);desc=a[6]
   if kind=='S':e=dict(common,kind='segment_start',descriptor_index=seg,program_base=base,descriptor_word=desc,core_start=1)
   else:
    if not controls[key] or not controls[key][-1]['me_idle'] or not controls[key][-1]['su_idle']:raise ValueError('source drain not observed at completion')
    e=dict(common,kind='segment_done',descriptor_index=seg,core_done=1)
   g.event(e)
   lifetimes[key]['descriptor_events'].append({'kind':kind,'edge':edge,'segment':seg,'program_base':base,'descriptor_word':desc})
  elif kind=='I':
   if len(a)<8:raise ValueError('accepted issue record width')
   seg,base,corepc,unit=map(int,a[4:8]);pc=base+corepc
   if seg!=g.index or base!=g.bases[g.index] or not 0<=pc<len(g.stage.words):raise ValueError('actual accepted dispatch/PC')
   ticket=tickets[key];tickets[key]+=1
   e=dict(common,kind='accepted_issue',pc=pc,core_pc=corepc,program_base=base,word_sha256=sha(f'{g.stage.words[pc]:0256x}'.encode()),core_issue=1,ticket=ticket)
   if unit==1:
    if len(a)!=32:raise ValueError('all24 actual ME fields')
    fields=dict(zip([n for n,w in FIELDS],map(int,a[8:])));e.update(me_go=1,fields=fields,ib379=instruction(fields))
   elif unit==2:
    if len(a)!=8:raise ValueError('source SU record width')
    e['su_go']=1
   else:raise ValueError('actual issue unit')
   g.event(e)
   if unit==2 and pc in g.stage.producer.expected:lifetimes[key]['producer_accepts'].append({'pc':pc,'ticket':ticket,'edge':edge})
   if unit==1:last_me[key]=e
   if unit==1 and e['fields']['wsrc']:lifetimes[key]['KV_consumer_accepts'].append({'pc':pc,'ticket':ticket,'edge':edge,'fields':e['fields'],'ib379':e['ib379']})
  elif kind=='R':
   if len(a)!=23:raise ValueError('actual16lane source KV read width')
   tile,group,address=map(int,a[4:7]);values=[int(v,16) for v in a[7:]]
   if not 0<=tile<1536 or not 0<=group<4 or not 0<=address<1<<24 or any(not 0<=v<1<<32 for v in values):raise ValueError('source KV read geometry')
   if edge<read_edges.get(key,-1):raise ValueError('source read order')
   if edge!=read_edges.get(key):read_edges[key]=edge;read_slots[key]=set()
   if (tile,group) in read_slots[key]:raise ValueError('duplicate source read port sameedge')
   read_slots[key].add((tile,group))
   e=last_me.get(key)
   if e is None or not e['fields']['wsrc'] or edge<e['edge']:raise ValueError('source read without accepted KV consumer')
   if edge<=last_write_edge[key]:raise ValueError('source read must precede sameedge commit')
   for lane,value in enumerate(values):
    scalar=address*16+lane
    if value!=memory[key].get(scalar,0):raise ValueError('actual KV read differs from committed host state')
    if scalar in writers[key]:
     if scalar not in memory[key]:raise ValueError('current row read before producer commit')
     lifetimes[key]['current_row_first_read'].setdefault(str(scalar),{'edge':edge,'consumer_pc':e['pc'],'ticket':e['ticket'],'tile':tile,'group':group})
   reads=lifetimes[key]['source_port_reads'].setdefault(str(e['pc']),{'first_edge':edge,'last_edge':edge,'word_reads':0})
   if edge<reads['last_edge']:raise ValueError('source read order')
   reads['last_edge']=edge;reads['word_reads']+=1
  elif kind=='W':
   if len(a)!=6:raise ValueError('lane record width')
   address=int(a[4]);value=int(a[5],16)
   if address not in writers[key]:raise ValueError('actual producer address outside image')
   pc=writers[key][address]
   if pc not in g.stage.issue_ticket:raise ValueError('actual lane write before accepted producer')
   if lifetimes[key]['first_committed_write_edge'] is None:lifetimes[key]['first_committed_write_edge']=edge
   lifetimes[key]['last_committed_write_edge']=edge
   lifetimes[key]['committed_writes'].append({'pc':pc,'ticket':g.stage.issue_ticket[pc],'edge':edge,'address':address,'fp32_hex':f'{value:08x}','fp8':producer_byte(value)})
   memory[key][address]=value;last_write_edge[key]=edge
   g.event(dict(common,kind='kv_lane_write',pc=pc,word_sha256=sha(f'{g.stage.words[pc]:0256x}'.encode()),ticket=g.stage.issue_ticket[pc],accepted_lane_write=1,address=address,fp32_bits=value))
  elif kind=='K':
   if len(a)!=6:raise ValueError('snapshot record width')
   address=int(a[4]);value=int(a[5],16)
   if address not in writers[key] or address in snapshots[key]:raise ValueError('unique actual snapshot address')
   snapshots[key][address]=producer_byte(value)
   if len(snapshots[key])==512:
    lifetimes[key]['snapshot_edge']=edge
    pp=g.stage.producer
    data={k:bytes(snapshots[key][pp.address(k,h,d)] for h in range(2) for d in range(128)).hex() for k in ('K','V')}
    g.event(dict(common,kind='KV_state_snapshot',K_hex=data['K'],V_hex=data['V']))
  else:raise ValueError('unknown raw source event')
 states={}
 for (l,r),g in gates.items():
  if not controls[(l,r)]:raise ValueError('actual source control transitions missing')
  state=g.finish();state['source_control_transitions']=controls[(l,r)];life=lifetimes[(l,r)]
  last=max(e['edge'] for e in life['KV_consumer_accepts'])
  drains=[e['edge'] for e in controls[(l,r)] if e['edge']>last and e['me_idle']]
  if not drains:raise ValueError('source ME idle after last KV consumer absent')
  life['first_source_ME_idle_after_last_KV_consumer']=min(drains);life['HBM_or_window_owner_reader_drain']=None
  life['producer_completions']=[{'pc':pc,'ticket':g.stage.issue_ticket[pc],'accepted_edge':next(e['edge'] for e in life['producer_accepts'] if e['pc']==pc),'first_write_edge':min(w['edge'] for w in life['committed_writes'] if w['pc']==pc),'last_write_edge':max(w['edge'] for w in life['committed_writes'] if w['pc']==pc),'write_count':len(aa)} for pc,aa in sorted(g.stage.producer.expected.items())]
  life['source_read_deadlines_complete']=len(life['current_row_first_read'])==512 and set(life['source_port_reads'])=={str(e['pc']) for e in life['KV_consumer_accepts']}
  if require_reads and not life['source_read_deadlines_complete']:raise ValueError('all current row reads and consumer deadlines required')
  state['source_lifetimes']=life;states[f'L{l}/die{r}']=state
 return {'status':'PASS_HISTORICAL_DISPATCH_PRODUCER_SNAPSHOT_CONSISTENCY' if layers==36 else 'PASS_HISTORICAL_PREFIX_DISPATCH_PRODUCER_SNAPSHOT_CONSISTENCY','states':states,'layers':layers,'whole36':layers==36,
  'source_provenance_independently_qualified':False,'runtime_source_owner_instantiated':False,
  'identity_scope':'actual stage/rank dispatch; user0/epoch0 observer labels, not provider owner state',
  'SMIN6_plus55_physical_transfer':False,'physical_adoption':False,'provider_calendar_adoption':False}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--require-reads',action='store_true');p.add_argument('--layers',type=int,default=36);a=p.parse_args()
 b=json.loads(gzip.decompress(a.bundle.read_bytes()))
 with a.raw.open() as raw:result=replay(b,raw,require_reads=a.require_reads,layers=a.layers)
 result['raw_sha256']=file_sha256(a.raw)
 with a.out.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
if __name__=='__main__':main()
