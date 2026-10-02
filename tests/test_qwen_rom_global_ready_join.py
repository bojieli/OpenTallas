"""Source-join checker fixtures; never an actual owned launch claim."""
import copy,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_global_ready_join import OwnedEpochReady,BroadcastAcceptance,OwnedLaunchJoin,source_join
from qwen_rom_kv_launch_readiness import instruction,StartupBarrier
from qwen_rom_kv_launch_readiness import FIELDS

class FixtureCausal:
 def debts(self):return dict(pending_producer_rows=0,live_allocations=0,pending_read_sectors=0,planned_write_sectors=0)

class FixtureResources:
 def __init__(self):self.tags={};self.assembly={};self.windows={};self.owner_busy={}

def fields():return {n:128 if n=='nout' else 6 if n=='split' else 0 for n,w in FIELDS}

def snapshot():
 occupancy=('ingress','wr_live','wr_backed','wr_mapped','grant_valid','live_tags','owner_state','owner_held','route_held')
 fifo=dict(wrsync=3,rrsync=3,won=1,ron=1,ronw2=1,wonr2=1,wb=0,rb=0,wg=0,rg=0,rgw2=0,wgr2=0)
 return dict(epoch=7,domains={d:dict(epoch=7,released=True,acknowledged=True) for d in ('stream','serial','service')},
 stacks=[dict(stack=i,enabled=1,fault=0,qcount=[0]*32,rcount=[0]*32,**{n:0 for n in occupancy}) for i in range(4)],
 bridges=[dict(fifo),dict(fifo)],serial=dict(active=0,inflight=0,fault=0),
 kv=dict(used=0,fl_v=0,boot_busy=0,boot_any_v=0,desc_pending=0,kvd_v=0,fault=0,adapter_idle=1,tail_state_bound=1))

def transaction_trace(BD=3):
 ib=instruction(fields());x={i:format(i,'0128b') for i in range(1536)}
 rows=[]
 for e in range(BD+1):
  r=dict(rst_n=1,request_go=int(e==0),go=int(e==0),global_ready=1,active=int(e>0),pend=0,ready=int(e==0),owner='fixture-only',pc=67,fields=fields(),ib=ib)
  tiles=[]
  for i in range(1536):
   relevant=e>=BD-1
   # Unknown invalid instruction/x storage must not be zero-filled to pass.
   tiles.append(dict(tile=i,rst_n=1,ib_go=int(e==BD-1),go_q=int(e==BD),active=0,pend=0,global_ready=1,owner='fixture-only',pc=67,
    ib=ib if relevant else 'x'*379,ib_q=ib if e==BD else 'x'*379,xl=x[i] if relevant else 'x'*128,xl_q=x[i] if e==BD else 'x'*128))
  rows.append(dict(edge=e,root=r,tiles=tiles,owned_tile_x=x,epoch=7))
 return rows

def test_old_barrier_drops_ready_on_owned_traffic_counterexample():
 b=StartupBarrier();s=snapshot();c=FixtureCausal();r=FixtureResources()
 assert b.sample(0,s,c,r)['registered_ready_afteredge'] is True
 r.assembly[0]=1
 result=b.sample(1,s,c,r)
 assert result['parent_domains_ready_preedge'] is True
 assert result['registered_ready_afteredge'] is False

def test_epoch_lease_retains_ready_during_busy_then_detects_release_loss():
 b=OwnedEpochReady();s=snapshot();c=FixtureCausal();r=FixtureResources()
 assert b.sample(0,s,c,r,0)['ready_preedge'] is False
 r.assembly[0]=1;s['stacks'][3]['qcount'][31]=1
 for e in range(1,8):assert b.sample(e,s,c,r,1)['ready_afteredge'] is True
 s['domains']['serial']['released']=False
 with pytest.raises(ValueError,match='abort/quarantine'):b.sample(8,s,c,r,1)

def test_constant_high_or_same_edge_credit_is_rejected():
 b=OwnedEpochReady()
 with pytest.raises(ValueError,match='registered epoch lease'):b.sample(0,snapshot(),FixtureCausal(),FixtureResources(),1)

@pytest.mark.parametrize('mutant',['epoch','fault','bridge','missingstack'])
def test_epoch_lease_does_not_hide_reset_or_source_fault(mutant):
 b=OwnedEpochReady();s=snapshot();c=FixtureCausal();r=FixtureResources();b.sample(0,s,c,r,0)
 if mutant=='epoch':s['epoch']=8
 elif mutant=='fault':s['stacks'][0]['fault']=1
 elif mutant=='bridge':s['bridges'][0]['wonr2']=0
 else:s['stacks'].pop()
 with pytest.raises(ValueError):b.sample(1,s,c,r,1)

def test_all1536_full_instruction_and_heterogeneous_x_acceptance():
 b=BroadcastAcceptance(3)
 for e in transaction_trace():b.step(e)
 assert b.finish()['all_tile_acceptances']==1536
 assert b.finish()['hardware_admission'] is False

@pytest.mark.parametrize('mutant',['missing','busy','heldbit','xowner','spuriousgo','rootconstantready'])
def test_global_acceptance_mutants_are_detected(mutant):
 rows=transaction_trace();last=rows[-1]
 if mutant=='missing':last['tiles'].pop()
 elif mutant=='busy':last['tiles'][1535]['pend']=1
 elif mutant=='heldbit':last['tiles'][1535]['ib']=last['tiles'][1535]['ib'][:-1]+'1'
 elif mutant=='xowner':last['tiles'][1535]['xl_q']='0'*128
 elif mutant=='spuriousgo':rows[1]['tiles'][1535]['go_q']=1
 else:rows[1]['root']['ready']=1
 b=BroadcastAcceptance(3)
 with pytest.raises(ValueError):
  for e in rows:b.step(e)


def test_join_cannot_use_synthetic_constant_ready_as_owned_epoch():
 b=OwnedLaunchJoin(3)
 with pytest.raises(ValueError,match='registered epoch lease'):b.step(transaction_trace()[0],snapshot(),FixtureCausal(),FixtureResources())


def test_current_sources_have_no_provider_or_actual_trace():
 r=source_join()
 assert len(r['source_sha256'])==12
 assert r['provider_instance_callers']==[]
 assert r['actual_ready_owner'] is r['actual_acceptance_trace'] is None
 assert r['actual_global_ready_induction'] is False
 assert r['status']=='BLOCKED_ACTUAL_READY_OWNER_AND_ACCEPTANCE_TRACE'
 assert r['conditional237']['cycles']==237

def test_registered_epoch_join_delivers_broadcast_while_service_becomes_busy():
 b=OwnedLaunchJoin(3);s=snapshot();c=FixtureCausal();r=FixtureResources()
 warm=transaction_trace()[0]
 warm['root'].update(request_go=0,go=0,global_ready=0)
 for t in warm['tiles']:t.update(ib_go=0,go_q=0,global_ready=0)
 b.step(warm,s,c,r)
 rows=transaction_trace()
 for e in rows:e['edge']+=1
 for e in rows:
  if e['edge']>=2:r.assembly[0]=1;s['stacks'][0]['qcount'][0]=1
  b.step(e,s,c,r)
 assert b.finish()['all_tile_acceptances']==1536


def test_accepted_broadcast_cannot_end_before_consumer_edge():
 b=BroadcastAcceptance(3)
 b.step(transaction_trace()[0])
 with pytest.raises(ValueError,match='incomplete'):b.finish()

def test_archived_complete_fixture_replays_and_blocked_source_join_is_exact():
 import gzip,json
 archive=Path(__file__).resolve().parents[1]/'results/uarch/qwen_rom_global_ready_service_g0_20261002'
 trace=json.loads(gzip.decompress((archive/'all_tile_fixture_trace.json.gz').read_bytes()))
 for e in trace:e['owned_tile_x']={int(k):v for k,v in e['owned_tile_x'].items()}
 b=OwnedLaunchJoin(3);s=snapshot();c=FixtureCausal();r=FixtureResources()
 for e in trace:
  if e['edge']>=2:r.assembly[0]=1;s['stacks'][0]['qcount'][0]=1
  b.step(e,s,c,r)
 assert b.finish()==json.loads((archive/'all_tile_fixture_terminal.json').read_text())['result']
 assert source_join()==json.loads((archive/'source_join_blocked.json').read_text())
