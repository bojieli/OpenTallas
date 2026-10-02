#!/usr/bin/env python3
"""Owned epoch startup/1536-tile acceptance checker. No readiness RTL is added.

Full-width accepted payloads are checked; invalid pre-reset payload storage is
left unqualified. Missing parent connection or actual trace remains BLOCKED.
"""
import argparse,hashlib,json,re
from pathlib import Path
from qwen_rom_kv_launch_readiness import startup_ready,instruction,binary
ROOT=Path(__file__).resolve().parents[1]
DEPENDENCY=Path('results/uarch/qwen_rom_kv_launch_readiness_20261002/euclid_dependency_r1.json')

def bit(v,name):
 if type(v) is not int or v not in (0,1):raise ValueError('known binary control required: '+name)
 return v

class OwnedEpochReady:
 """Register one startup join and hold the epoch lease through owned traffic.

 Busy queues after startup do not revoke readiness. Release loss/fault/epoch
 change requires an explicit abort/quarantine, never a silent readiness drop.
 This checker cannot create a CDC handshake or source-owner receipt.
 """
 def __init__(self):self.epoch=None;self.ready=False;self.edge=-1;self.bridges=None
 def sample(self,edge,snapshot,causal,resources,observed_preedge):
  if edge!=self.edge+1:raise ValueError('every consecutive stream edge required')
  if self.epoch is not None and snapshot['epoch']!=self.epoch:raise ValueError('epoch change requires abort/quarantine')
  old=self.ready
  if bit(observed_preedge,'global_ready')!=int(old):raise ValueError('actual global readiness differs from registered epoch lease')
  if old:
   if len(snapshot['stacks'])!=4 or {x['stack'] for x in snapshot['stacks']}!=set(range(4)):raise ValueError('all four source stack snapshots required')
   if len(snapshot['bridges'])!=self.bridges:raise ValueError('source bridge inventory changed')
   for f in snapshot['bridges']:
    if f['wrsync']!=3 or f['rrsync']!=3 or any(f[k]!=1 for k in ('won','ron','ronw2','wonr2')):raise ValueError('bridge release lost: abort/quarantine required')
   for d in ('stream','serial','service'):
    s=snapshot['domains'][d]
    if s['epoch']!=self.epoch or s['released'] is not True or s['acknowledged'] is not True:raise ValueError('domain release lost: abort/quarantine required')
   for s in snapshot['stacks']:
    if bit(s['enabled'],'stack.enabled')!=1 or bit(s['fault'],'stack.fault')!=0:raise ValueError('provider fault/disable: abort/quarantine required')
   if snapshot['serial']['fault']!=0 or snapshot['kv']['fault']!=0:raise ValueError('source fault: abort/quarantine required')
  else:
   self.ready=startup_ready(snapshot,causal,resources)
   if self.ready:self.bridges=len(snapshot['bridges'])
  self.epoch=snapshot['epoch'];self.edge=edge
  return dict(ready_preedge=old,ready_afteredge=self.ready,epoch=self.epoch)

class BroadcastAcceptance:
 """Complete actual pre-edge array trace, not one representative tile.

 Source spine delays go&&ready by BD-IREG; IREG=1 consumes at root_edge+BD.
 Root fields are all24 DYN-adjusted source fields. x is independently owned
 per tile: no zero-fill or homogeneous representative replacement.
 """
 def __init__(self,BD,tiles=1536):
  if type(BD) is not int or BD<1:raise ValueError('IREG1 requires priced BD>=1')
  if tiles!=1536:raise ValueError('current6144/TG4 requires all1536tiles')
  self.BD=BD;self.tiles=tiles;self.edge=-1;self.pending={};self.held=None;self.accepted=0;self.previous_tile_go={}
 def step(self,e):
  edge=e['edge']
  if type(edge) is not int or edge!=self.edge+1:raise ValueError('every consecutive global stream edge required')
  r=e['root']
  for k in ('rst_n','request_go','go','global_ready','active','pend','ready'):bit(r[k],'root.'+k)
  if r['ready']!=int(not r['active'] and not r['pend']):raise ValueError('root ready is not source !active&&!pend')
  if r['go']!=(r['rst_n'] & r['request_go'] & r['global_ready']):raise ValueError('root go bypasses owned global startup barrier')
  if not r['rst_n']:
   if self.pending:raise ValueError('reset interrupted broadcast: abort/quarantine required')
   self.held=None;self.previous_tile_go={}
  rows=e['tiles']
  if len(rows)!=self.tiles or {t['tile'] for t in rows}!=set(range(self.tiles)):raise ValueError('all1536 distinct tile snapshots required')
  bytile={t['tile']:t for t in rows}
  if r['request_go']:
   owner=r['owner'];pc=r['pc'];ib=instruction(r['fields'])
   if not isinstance(owner,str) or not owner or type(pc) is not int or pc<0:raise ValueError('actual owner and issuedPC required')
   if binary(r['ib'],379)!=ib:raise ValueError('complete DYN-adjusted root instruction differs')
   req=dict(owner=owner,pc=pc,ib=ib)
   if self.held is not None and req!=self.held:raise ValueError('root request owner/PC/379bits changed while held')
   self.held=req
  elif self.held is not None:raise ValueError('root withdrew unaccepted owned request')
  if r['go'] and r['ready']:
   if self.held is None:raise ValueError('global acceptance lacks held owner')
   tx=dict(self.held);tx['root_edge']=edge;tx['x']={}
   # These must be source-owner reference words for the *tile boundary*;
   # receipt must identify actual XVM/broadcast stages, not imply constant x.
   x=e['owned_tile_x']
   if set(x)!=set(range(self.tiles)):raise ValueError('all1536 owned128bit x references required')
   tx['x']={i:binary(x[i],128) for i in x}
   self.pending[edge+self.BD]=tx;self.held=None
  future=self.pending.get(edge+1);now=self.pending.get(edge)
  for i,t in bytile.items():
   for k in ('rst_n','ib_go','go_q','active','pend','global_ready'):bit(t[k],'tile.'+k)
   if t['rst_n']!=r['rst_n'] or t['global_ready']!=r['global_ready']:raise ValueError('tile reset/ready epoch differs from global source')
   if t['ib_go']!=int(future is not None) or t['go_q']!=int(now is not None):raise ValueError('actual BD/IREG go or missing/spurious broadcast')
   if future:
    if (t['owner'],t['pc'])!=(future['owner'],future['pc']):raise ValueError('boundary owner/issuedPC differs')
    if binary(t['ib'],379)!=future['ib'] or binary(t['xl'],128)!=future['x'][i]:raise ValueError('boundary379bit instruction/128bit x differs')
   if now:
    if t['active'] or t['pend']:raise ValueError('global ready failed to imply idle tile at consumption')
    if not t['global_ready']:raise ValueError('queued broadcast lost same-epoch readiness')
    if (t['owner'],t['pc'])!=(now['owner'],now['pc']):raise ValueError('accepted owner/issuedPC differs')
    if (binary(t['ib'],379)!=now['ib'] or binary(t['ib_q'],379)!=now['ib'] or
        binary(t['xl'],128)!=now['x'][i] or binary(t['xl_q'],128)!=now['x'][i]):raise ValueError('owner must retain complete379/128 payload through consumption')
  if now:self.accepted+=self.tiles;del self.pending[edge]
  self.edge=edge
 def finish(self):
  if self.pending or self.held:raise ValueError('incomplete accepted broadcast or held owner')
  if not self.accepted:raise ValueError('no actual accepted instruction evidence')
  return dict(all_tile_acceptances=self.accepted,global_transactions=self.accepted//self.tiles,BD=self.BD,IREG=1,hardware_admission=False)

class OwnedLaunchJoin:
 """Compose actual coherent source snapshots with all-tile owner acceptance."""
 def __init__(self,BD):self.lease=OwnedEpochReady();self.broadcast=BroadcastAcceptance(BD)
 def step(self,e,snapshot,causal,resources):
  if e['epoch']!=snapshot['epoch']:raise ValueError('actual launch epoch differs from readiness source')
  self.lease.sample(e['edge'],snapshot,causal,resources,e['root']['global_ready'])
  self.broadcast.step(e)
 def finish(self):return self.broadcast.finish()

def source_join():
 dep=json.loads((ROOT/DEPENDENCY).read_text());matches={}
 for p,h in dep['source_sha256'].items():
  actual=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
  if actual!=h:raise ValueError('Russell source currency differs: '+p)
  matches[p]=actual
 # Remove comments before caller census; a module definition is not an instance.
 callers=[]
 for p in (ROOT/'rtl').rglob('*.sv'):
  s=re.sub(r'/\*.*?\*/|//[^\n]*','',p.read_text(),flags=re.S)
  if re.search(r'(?<!module )\bot_qwen_rom_reset_parent_provider\s*(?:#\s*\([^;]*?\)\s*)?\w+\s*\(',s):callers.append(str(p.relative_to(ROOT)))
 return dict(source_sha256=matches,provider_instance_callers=callers,
  conditional237=json.loads((ROOT/'results/uarch/qwen_rom_owned_binary_source_20261002/contract_and_remaining.json').read_text())['literal_source_gate'],
  actual_ready_owner=None,actual_acceptance_trace=None,actual_global_ready_induction=False,
  status='BLOCKED_ACTUAL_READY_OWNER_AND_ACCEPTANCE_TRACE',new_RTL=False,new_engine=False,new_map=False,new_token=False,
  unpriced_hardware='Epoch ready register, owner abort/quarantine logic, acknowledged service/serial CDC snapshots and fanout to root/1536tiles require Ampere model before implementation',
  accepted_fields='all379 DYN bits+independently owned128x per tile; root go&&!active&&!pend -> each delayed tile idle at acceptance; all1536 required, invalid payload storage unqualified')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():p.error('preserve existing verdict')
 result=source_join()
 with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print('BLOCKED_ACTUAL_READY_OWNER_AND_ACCEPTANCE_TRACE')
