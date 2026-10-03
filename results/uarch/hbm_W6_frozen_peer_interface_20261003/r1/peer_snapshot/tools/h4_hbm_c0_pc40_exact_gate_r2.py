#!/usr/bin/env python3
"""Additive source-enrolled PC40 gate/model. NumPy is GOLDEN vector oracle only.

RTL drives physical RF reads/writes, mirror ACK and actual W6. The next literal
FMIN consumer reads RF19, computes and holds the value before W6 consumption.
Entering leases in the standalone gate derive from cold exclusive hardware
ownership; this never invents an empty live production workspace.
"""
import argparse,copy,hashlib,json,math,struct
from pathlib import Path
import h4_hbm_c0_connected_bridge_model as B
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h4_hbm_c0_connected_bridge_20261003/r2'
INPUT_SHA='1997e87c066b1b1fae986f9a3ce9e3a485580daaa530da96b0309b9dcfa53c3c'
def sources():
 raw=(BASE/'inputs.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=INPUT_SHA:raise ValueError('r2 manifest identity')
 out={}
 for r in json.loads(raw):
  p=ROOT/r['archive']
  if not p.resolve().is_relative_to((BASE/'inputs').resolve()):raise ValueError('archive scope')
  data=p.read_bytes()
  if hashlib.sha256(data).hexdigest()!=r['sha256']:raise ValueError('archive source identity')
  out[p.name]=data
 return out

def compose(wait_edges=4,period_ns=1/1.2):
 model=B.model(wait_edges,period_ns);d=json.loads(sources()['Dewey_PC40_demand.json'])
 if d['source_PC']!=40 or d['W2_HBM_commands']!=0 or d['parent55'] is not None:raise ValueError('actual direct RF demand')
 plan=model['source_operand_plan']
 if any(x['rank']==0 and x['SM']==0 and x['slot'] in [17,18,19] for x in d['existing_live_RF_homes']):raise ValueError('source home workspace alias')
 # Live production entering snapshot is deliberately still absent in r9.
 if d['workspace_admission']!='REFUSED_MISSING_ENTERING_LIVE_LEASES':raise ValueError('historical workspace admission changed')
 next_event=next(e for e in d['events'] if e['phase']=='source_next_consumer')
 if next_event['opcode']!='FMIN' or next_event['source_slot']!=19 or next_event['literal_bits']!=0x42b00000:raise ValueError('actual next source consumer')
 # New RTL: one72b context,12872b held FMIN lanes, no added RF macro.
 ff=129*72;code_gates=129*768*2;cmp_gates=128*(31*8+32*3+40);mux_gates=8192*2;control_gates=1024
 clocks=math.ceil(ff/64)
 cell=ff*.2916+(code_gates+cmp_gates+mux_gates+control_gates)*.3+clocks*2
 added=cell/.5/1e6
 events=copy.deepcopy(model['calendar']['event_edges']);events.update(consumer_RF19_read=3,consumer_FMIN=2,consumer_result_accept_wait=wait_edges)
 return dict(schema='CONNECTED_PC40_RF_ACK_W6_FMIN_GATE_R2',selected_source_packet=B.emit_source(B.source_plan(2**32+1,2**32+18),enabled=True),
  source_next_consumer=next_event,source_Dewey_eventIDs=[e['eventID'] for e in d['events']],
  model_before_new_RTL=True,default_enabled=False,
  replaced_subtree='selected PC40/tile0 producer+FMAX+FMIN; replace paid r9 events once, never add atop previous per-action RF/ACK',
  fusion=dict(level=1,steps=['BITCAST_U','XOR','BITCAST_F'],ordering='lane-local exact bitcast chain, no reassociation',source_literal_mask=0x80000000),
  workspace=dict(slots=[17,18,19],max_outstanding=1,source_static_disjoint=True,
   production_entering_workspace=d['workspace_admission'],standalone_entering_snapshot='observed cold exclusive actor: zero live lease until actual req handshake',
   acquire='req_valid && req_ready; protects all3 slots',release='held native retire handshake after actual RF19/FMIN consumption + matched W6 reverse/drain',
   gate_up_caller_lifetimes='retained outside this single callee; no release at FMAX/FMIN gate'),
  cost_events=events,cycles_conditional=sum(events.values()),period_ns=period_ns,latency_ns_conditional=sum(events.values())*period_ns,
  eligibility=f'every exposed ready/consumer/reverse/drain eligible within{wait_edges} stream edges; actual trace checks separate; fullprogram upper UNKNOWN',
  ports=dict(RF_read_commands=4,RF_read_pair_bytes=1024,RF_write_commands=5,RF_write_payload_bytes=512,
   mirror_write_bytes=5*1024,native_identity_bits=128,common_identity_bits=55,consumer_result_bits=4096,HBM_commands=0,MACs=0),
  incremental=dict(protected_context_bits=72,protected_FMIN_result_bits=128*72,codec_word_count=129,
   prefix_comparators=128,new_RF_macros=0,read_response_demux_width=8192,demux_sinks=2,clock_buffer_count_ASSUMED=clocks,
   cell_um2_ASSUMED=cell,footprint_mm2_at50pct_ASSUMED=added),
  total_controller_consumer_footprint_mm2_ASSUMED=model['area']['controller_footprint_mm2_50pct_ASSUMED']+added,
  full32SM_area_mm2_ASSUMED=32*(model['area']['controller_footprint_mm2_50pct_ASSUMED']+added),
  clock=dict(target_ns=period_ns,source='streaming AGENTS 1.2GHz',setup_ps=60,hold_ps=25,loaded_SS_FF=False),
  cuts=dict(read_payload_bits=8192,response_demux=2,lower_read_tracks=8192+18+4,lower_write_tracks=4096+9+2,
   physical_channel_capacity=None,physical_build_admitted=False),
  source_identity='opaque accepted issuer owner46 retained, not allocated from SW PC40 and not a W2 physical tag',
  W2=model['W2'],production_issuer_connected=False,production_entering_workspace_admitted=False,
  protected_hardware_qualified=False,physical_qualified=False,whole_token_ns=None,
  scope='source-enrolled exact standalone connected operation; caller identity and allcopy authorities scoped protocol endpoints, no live production/fulltoken claim')

def oracle_vectors():
 import numpy as np
 patterns=[0x42c80000,0xc2c80000,0,0x80000000,0x42ae0000,0x42b00000,1,0x80000001,0x3f800000,0xbf800000,0x7f7fffff,0xff7fffff]
 rows=[]
 for i in range(128):
  u=patterns[i%len(patterns)];gate=np.array([u],dtype=np.uint32).view(np.float32)
  neg=np.negative(gate).astype(np.float32);maximum=np.maximum(neg,np.float32(-87)).astype(np.float32)
  maximum[maximum==np.float32(0)]=np.float32(0)
  minimum=np.minimum(maximum,np.float32(88)).astype(np.float32);minimum[minimum==np.float32(0)]=np.float32(0)
  rows.append(dict(lane=i,gate=u,FMAX=int(maximum.view(np.uint32)[0]),FMIN=int(minimum.view(np.uint32)[0])))
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
 outputs={'model.json':B.canonical(dict(model=compose(),sensitivity=[compose(w,t)['latency_ns_conditional'] for w in [1,4,16] for t in [1/1.2,1,1/0.9]])),
          'golden_vectors.json':B.canonical(dict(scope='NumPy source arithmetic oracle only, never execution callback',vectors=oracle_vectors()))}
 for name,raw in outputs.items():
  path=BASE/name
  if a.verify:
   if path.read_bytes()!=raw:raise ValueError('byteexact replay '+name)
  else:path.write_bytes(raw)
 print('PASS source/model/vector replay' if a.verify else 'WROTE source model before consumer RTL')
if __name__=='__main__':main()
