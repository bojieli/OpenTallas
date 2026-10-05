#!/usr/bin/env python3
"""Descriptor-dispatched current Qwen accepted-issue/KV-state successor gate.

No reconstruction of absent events. Source consistency alone cannot qualify
trace provenance, a provider receipt, physical timing, or token latency.
"""
import argparse,gzip,json
from pathlib import Path
from hdc_qwen_fullshape_isa_w12 import decode_descriptor,decode_instruction
from qwen_rom_program_identity import ROOT,decoded,sha
from qwen_rom_program_kv_journal import StageJournal,source_pins
from qwen_rom_persistent_kv_g0 import Owner
EXTRA_SOURCES=['rtl/rom/ot_qwen_tp_seq_w12.sv','rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv',
 'tools/qwen_rom_rt_core_emit_w12.py','tools/qwen_rom_arithmetic_contract_w12.py',
 'rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp','tools/qwen_rom_accepted_stage_journal.py']
def pins():return dict(source_pins(),**{p:sha((ROOT/p).read_bytes()) for p in EXTRA_SOURCES})

class DispatchJournal:
 def __init__(self,image,descriptors,owner,token,position):
  self.stage=StageJournal(image,owner,token,position)
  self.words=[int(w,16) for w in descriptors.decode().split()]
  self.desc=[decode_descriptor(w) for w in self.words]
  self.bases=[d['program_base'] for d in self.desc]
  if not self.bases or self.bases[0]!=0 or sorted(set(self.bases))!=self.bases or self.bases[-1]>=len(self.stage.words):
   raise ValueError('descriptor program aperture/order')
  self.index=-1;self.active=False;self.last_edge=-1;self.demand_count=0;self.snapshot=False
  self.receipts=[]
 def event(self,e):
  if e['owner']!=vars(self.stage.owner):raise ValueError('descriptor owner identity')
  edge=e['edge']
  if type(edge) is not int or edge<self.last_edge:raise ValueError('source stream edge order')
  self.last_edge=edge;kind=e['kind']
  if kind=='segment_start':
   if self.active or e['descriptor_index']!=self.index+1:raise ValueError('actual segment dispatch sequence')
   index=e['descriptor_index']
   if index>=len(self.words) or e['descriptor_word']!=f'{self.words[index]:016x}' or e['program_base']!=self.bases[index]:raise ValueError('exact descriptor dispatch')
   if type(e['core_start']) is not int or e['core_start']!=1:raise ValueError('actual core_start edge required')
   self.index=index;self.active=True;self.start_edge=edge
   self.receipts.append({'descriptor_index':index,'program_base':self.bases[index],'start_edge':edge})
  elif kind=='segment_done':
   if not self.active or e['descriptor_index']!=self.index or type(e['core_done']) is not int or e['core_done']!=1 or edge<=self.start_edge:raise ValueError('actual segment completion')
   end=self.bases[self.index+1] if self.index+1<len(self.bases) else len(self.stage.words)
   if self.stage.cursor<len(self.stage.expected) and self.stage.expected[self.stage.cursor]<end:raise ValueError('completion before accepted program')
   self.active=False;self.receipts[-1]['done_edge']=edge
  elif kind in ('accepted_issue','kv_lane_write'):
   if not self.active:raise ValueError('issue/write without actual segment dispatch')
   base=self.bases[self.index];end=self.bases[self.index+1] if self.index+1<len(self.bases) else len(self.stage.words)
   if not base<=e['pc']<end:raise ValueError('PC belongs to another descriptor')
   if kind=='accepted_issue':
    if type(e['core_pc']) is not int or not 0<=e['core_pc']<4096 or e['program_base']!=base or e['pc']!=base+e['core_pc']:
     raise ValueError('actual core PC plus program base binding')
    f=decode_instruction(self.stage.words[e['pc']])
    go=e['me_go'] if f['unit']==1 else e['su_go']
    if type(go) is not int or go!=1:raise ValueError('binary accepted source go')
    if f['unit']==1 and f['me_wsrc']:
     # Current program writes the full K/V row before either KV consumer.
     # These are source-mutable-state bytes, not HBM backing/write-visible receipts.
     self.stage.producer.state();self.demand_count+=1
   self.stage.event(e)
  elif kind=='KV_state_snapshot':
   if self.active or self.index!=len(self.desc)-1 or self.snapshot:raise ValueError('unique state snapshot after full program')
   state=self.stage.producer.state()
   if e['K_hex']!=state['K'].hex() or e['V_hex']!=state['V'].hex():raise ValueError('actual KV snapshot differs from accepted lane writes')
   self.snapshot=True
  else:raise ValueError('unsupported source event')
 def finish(self):
  if self.active or self.index!=len(self.desc)-1 or not self.snapshot:raise ValueError('incomplete descriptor/state journal')
  record=self.stage.finish();record.update(segment_receipts=self.receipts,accepted_KV_ME_count=self.demand_count,
   KV_state_scope='source mutable row; no HBM backing or physical window residency credit')
  return record

def check(bundle,journal):
 if journal is None:return {'status':'BLOCKED_NO_ACTUAL_DISPATCH_ISSUE_KV_STATE_EXPORT','actual_accepted_KV_demand':None,'actual_KV_state':None,'calendar_adoption':False,'physical_adoption':False}
 if (bundle['su_width'],bundle['ar_words'],bundle['TP'],bundle['groups'])!=(1024,256,4,6144):raise ValueError('selected program dimensions')
 if any(sha((ROOT/p).read_bytes())!=v for p,v in bundle['source_sha256'].items()):raise ValueError('source program emitter identity')
 h=journal['header']
 if h['bundle_canonical_sha256']!=sha(json.dumps(bundle,sort_keys=True,separators=(',',':')).encode()):raise ValueError('stage program bundle identity')
 if h['source_sha256']!=pins():raise ValueError('source dispatch/decode/producer pins')
 if h['position']!=0:raise ValueError('single retained position0 only')
 if h['origin']!='actual_source_export':raise ValueError('actual source exports mandatory')
 stages=journal['stages']
 if set(stages)!={f'L{i}/die{r}' for i in range(36) for r in range(4)}:raise ValueError('complete36layer4rank state/demand journal')
 states={}
 for key,events in sorted(stages.items()):
  l,r=key.split('/');owner=Owner(h['user'],int(r[3:]),int(l[1:]),h['epoch']);files=bundle['stages'][key]['files']
  gate=DispatchJournal(decoded(files['program.hex']),decoded(files['segments.hex']),owner,h['token'],h['position'])
  for e in events:gate.event(e)
  states[key]=gate.finish()
 return {'status':'PASS_DISPATCH_STATE_JOURNAL_CONSISTENCY_ONLY','source_provenance_independently_qualified':False,
  'calendar_adoption':False,'physical_adoption':False,'states':states,
  'accepted_KV_ME_count':sum(s['accepted_KV_ME_count'] for s in states.values())}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--journal',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 b=json.loads(gzip.decompress(a.bundle.read_bytes())) if a.bundle.suffix=='.gz' else json.loads(a.bundle.read_text())
 result=check(b,json.loads(a.journal.read_text()) if a.journal else None)
 with a.out.open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
if __name__=='__main__':main()
