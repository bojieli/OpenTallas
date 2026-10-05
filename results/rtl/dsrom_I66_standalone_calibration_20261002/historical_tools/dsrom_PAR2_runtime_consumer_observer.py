#!/usr/bin/env python3
"""Current r5 L0.I66 source-consumer observer; no frozen D1 source mutation.
Native adapter selects phase by registered EID VM read; source spine BST17,
full4096/R128/NBF724 logicalfield; final sink exact tile ROM process fragment.
Full core/otherwriter/physical PAR2 transport are expressly outside this cone.
"""
import argparse,collections,gzip,hashlib,json,shutil,sys
from pathlib import Path
import dsrom_PAR2_wholephase_source_trace as M
ROOT=M.ROOT;B=ROOT/'rtl/test/dsrom_PAR2_runtime_consumer_observer';OUT=ROOT/'results/rtl/dsrom_PAR2_runtime_consumer_observer_20261002'

def descriptor():
 J=M.N.J;d=json.loads(gzip.decompress((J.D/'inputs/demand-r5.json.gz').read_bytes()));join=J.Join(d,list(J.C.readrows(J.PHASES)))
 f,p=join.patched('L0.I66',[0,1,2,3,4,5])
 assert (f['qe_xbase'],f['qe_obase'],f['qe_ibase'],f['qe_wbase'],f['qe_istride'],f['qe_nb'],f['qe_nout'])==(46464,398720,366688,2097152,4096,160,576)
 assert p['phase']==10 and p['stage']==0 and p['expert']==0
 return f,p

def adapter_calendar(f,EID=0):
 # Native S_IDLE->S_IDX->S_IDXW->S_LOOK->S_GO registered s_go.
 events=[dict(kind='op_accept',edge=10,phase=10),dict(kind='EID_VM_read_accept',edge=11,address=f['qe_ibase']),dict(kind='EID_VM_response_visible',edge=11,EID=EID),dict(kind='indexed_key_capture',edge=12,key=f['qe_wbase']+EID*f['qe_istride']),dict(kind='phase_lookup_capture',edge=13,phase=10),dict(kind='phase_accept',edge=15,phase=10,key=f['qe_wbase']+EID*f['qe_istride'])]
 return events,15

def prepare(out):
 if out.exists():raise ValueError('fresh immutable preparation')
 out.mkdir(parents=True);f,p=descriptor();m,mp=M.matrix();pr=M.primitives();adapter,origin=adapter_calendar(f)
 M.BST=17
 up,accepted,state,go=M.upstream(M.N.stream_inputs(m),opedge=origin)
 for x in up:
  if x['kind']=='VM_read_accept':x['address']+=f['qe_xbase']
 # Core operation acceptance belongs to adapter; spine phase acceptance is separate.
 up=[x for x in up if x['kind']!='op_accept']+adapter
 sparse=[0]*(max(a for a,w in accepted)-3)
 for a,w in accepted:sparse[a-4]=w
 ce=[];leaves=[];pair_receipts=[]
 for si,g,first,n,stride,start,w in m['plans']:
  e,size=m['segments'][si]
  ps=[dict(fmt=m['format'],e0=e,elems=size,row=first+i*stride,mi=0,seg=si,nseg=len(m['segments']),base=start,tensor=m['tensor']) for i in range(n)]
  issues,q=pr['pair_issue'](ps,sparse);ls,s=pr['pair_leaves'](ps,issues);assert not q['overflow'] and not s['faults']
  pair_receipts.append(dict(global_pair=g,**q,**s))
  for wi,(edge,i,u,b,h,pos,slot) in enumerate(issues):ce.append(dict(kind='main_CE_accept',edge=edge,pair=g,logical_address=start+wi,slot=slot))
  for t,mb,tag,expr in ls:
   if tag[1]<576:leaves.append((t,2*g+mb,tag,expr))
 root,ret=M.return_calendar(leaves,pr)
 writes=[dict(kind='VM_write_accept',edge=x['edge']+1,port=x['root'],address=f['qe_obase']+x['row'],row=x['row'],data=0x45a00000) for x in root]
 spine_idle=max(x['edge'] for x in root)+1;adapter_retire=spine_idle+1
 img=out/'img';img.mkdir()
 active={x[1] for x in m['plans']};(img/'config.txt').write_text(''.join(f'{g} {k} {v:x}\n' for g in range(4096) for k,v in enumerate(M.N.C.phase_cfg(m,g) if g in active else [0]*25)))
 beats=M.N.stream_inputs(m);pw=(5120<<1)|(len(beats)<<14)|(576<<46)
 (img/'spine_phase.hex').write_text(''.join(f'{pw if i==20 else 0:016x}\n' for i in range(2048)))
 (img/'spine_keys.hex').write_text(''.join(f'{p["source_key_word"] if i==10 else 0:08x}\n' for i in range(1024)))
 (img/'spine_stream.hex').write_text(''.join(f'{w:012x}\n' for w in beats))
 (img/'vm.hex').write_text(f'@{f["qe_xbase"]:x}\n'+'3f800000\n'*5120+f'@{f["qe_ibase"]:x}\n00000000\n')
 for name,es in [('upstream_prediction',up),('CE_prediction',sorted(ce,key=lambda x:(x['edge'],x['pair']))),('root_prediction',root),('VM_write_prediction',writes)]:
  (out/(name+'.jsonl')).write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in es))
 (out/'upstream_state_prediction.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in state))
 originals={str(x.relative_to(B/'pinned')):M.sha(x) for x in (B/'pinned').rglob('*.sv')}
 tile=(B/'pinned/rtl/w17_runtime/chip/ot_chip_v41x_tile.sv').read_text();fragment=(B/'tile_ROM_VM_consumer_fragment.sv.txt').read_text();wrapper=(B/'dsrom_runtime_consumers.sv').read_text();assert fragment in tile and fragment in wrapper
 baseline=json.loads((ROOT/'results/rtl/dsrom_PAR2_wholephase_source_trace_20261002/preparation_r2/prediction.json').read_text())
 model=dict(schema='opentallas.dsrom.PAR2.current-native-consumer-observer.v1',case=dict(node='L0.I66',descriptor=f,stage=0,phase=10,key_word=p['source_key_word'],rank=0,EID=0,positions=1),compiled=dict(logical_NP=4096,PAR2_shards=2,NP_per_shard=2048,R=128,roots_per_shard=64,NBF=724,BST=17,PHW=10,AW=30,VM_AW=19,FAST=1,PP=1,BP=0,full_inactive_sites_instantiated=True),source_bindings=dict(adapter='original ot_v41_rom_adapt native indexed read/CAM, no forced phase',spine='original ot_v41_spine_w17w10 ROM_BST17 from actual runtime source',VM_sink='byte-exact original tile X_ROM read/write process cone; registered VI/64wordread and perroot increasing-port-order writes',other_writer_scope='isolated current ROM operation; every other tile writer absent/inactive, no universal collision or collective completion proof',clock='native source clk/gclk simulation edges only; no clock/SSFF qualification',passive_observer=dict(added_engine_latency_cycles=0,added_engine_state_bits=0,added_engine_ports=0,ro_probe='host samples combinational VM probe after original sink NBA, no datapath feedback'),D1_frozen_source_touched=False),data_contract=dict(input='nonzero synthetic FP32ones at actualXN46464; EID0 atactual366688',weights='generated FP4code2=1 bothhalves, E8M0scales127=1 through original274bit macro callback; no checkpoint reads',independent_oracle='integer exact 5120 unitproducts; golden block32/chunk8 ordered trees all exact, FP32 and BF16 result5120=0x45a00000',root_forced_or_zero_injected=False,payload_checkpoint_qualification=False),absolute_edges=dict(op_accept=10,phase_accept=origin,field_GO=go,first_VM_read=min(x['edge'] for x in up if x['kind']=='VM_read_accept'),first_activation=accepted[0][0],last_activation=accepted[-1][0],first_CE=min(x['edge'] for x in ce),last_CE=max(x['edge'] for x in ce),last_root=max(x['edge'] for x in root),last_VM_write=max(x['edge'] for x in writes),spine_idle_preedge=spine_idle,adapter_retire_preedge=adapter_retire),prediction_counts=dict(cfg_ROM_reads=102400,cfg_element_writes=102400,EID_reads=1,VM_reads=80,AQ_inputs=80,AQ_outputs=80,valid_activation_beats=len(accepted),paired_CE=len(ce),macro_MB_reads=len(ce)*2,root_rows=576,VM_sink_writes=576,post_NBA_visible_words=576),pair_receipts=pair_receipts,return_resources=ret,original_sources=originals,fixture_sha256={x.name:M.sha(x) for x in B.iterdir() if x.is_file()},source_fragment_sha256=M.sha(B/'tile_ROM_VM_consumer_fragment.sv.txt'),resource_plan=baseline['resource_plan'],macro_physical_or_PAR2_interdie_credit=False,full_core_scheduler_or_coll_busy_bound=False,fulltoken_credit=False,no_ECC_pool_or_new_ACK=True,retained_templates='pq/pb/retn/root ONLY; exact parameter/source/interface comparison before reuse. Fresh native adapter/spine/VM consumer cone, no frozenD1elaboration reuse.')
 (out/'prediction.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
 (B/'sources.json').write_text(json.dumps(originals,indent=2,sort_keys=True)+'\n')
 print(json.dumps(dict(result='CURRENT_NATIVE_ROM_CONSUMER_CONE_MODEL_READY',counts=model['prediction_counts'],edges=model['absolute_edges'])))
 return model

def expected(preparation):
 p=Path(preparation);m=json.loads((p/'prediction.json').read_text());es=[]
 for x in [json.loads(l) for l in (p/'upstream_prediction.jsonl').read_text().splitlines()]:
  k=x['kind'];e=x['edge']
  if k in ('cfg_ROM_read_accept','cfg_element_write_accept'):
   for g in range(4096):es.append((k,e,g,x['word']))
  elif k=='VM_read_accept':es.append((k,e,x['address'],64))
  elif k=='EID_VM_read_accept':es.append((k,e,x['address'],-1))
  elif k=='AQ_input_accept':es.append((k,e,x['first_element'],-1))
  elif k=='AQ_output_capture':es.append((k,e,-1,-1))
  elif k in ('field_cfg_accept','op_accept','phase_accept'):es.append((k,e,10,-1))
  elif k=='field_go_accept':es.append((k,e,-1,-1))
  elif k=='activation_field_accept':es.append((k,e,(x['word']>>1)&255,(x['word']>>9)&7))
  elif k in ('stream_ROM_advance','stream_have_stall'):es.append((k,e,x['index'],-1))
 for x in [json.loads(l) for l in (p/'CE_prediction.jsonl').read_text().splitlines()]:
  es.extend([('main_CE_accept',x['edge'],x['pair'],x['logical_address']),('bank_capture',x['edge']+2,x['pair'],x['logical_address']&1),('lane_consumer_sample',x['edge']+3,x['pair'],-1)])
  for mb in (0,1):es.append(('macro_read_accept',x['edge'],x['pair'],(mb<<14)|x['logical_address']))
 for x in [json.loads(l) for l in (p/'root_prediction.jsonl').read_text().splitlines()]:es.append(('root_row_accept',x['edge'],x['root'],x['row']))
 for x in [json.loads(l) for l in (p/'VM_write_prediction.jsonl').read_text().splitlines()]:es.extend([('VM_write_accept',x['edge'],x['port'],x['address']),('final_destination_visible',x['edge'],x['address'],-1)])
 es.extend([('spine_idle',m['absolute_edges']['spine_idle_preedge'],-1,-1),('phase_retire',m['absolute_edges']['adapter_retire_preedge'],-1,-1)])
 return sorted(es)

def compare(p,events):
 wanted={x[0] for x in expected(p)};obs=[]
 for x in events:
  k=x['kind'];a=x['a'];b=x['b']
  if k not in wanted:continue
  if k in ('AQ_output_capture','spine_idle','phase_retire'):a=b=-1
  if k in ('stream_ROM_advance','stream_have_stall'):b=-1
  if k=='main_CE_accept':b=x['c']
  if k=='macro_read_accept':b=(b<<14)|x['c']
  obs.append((k,x['edge'],a,b))
 a=collections.Counter(expected(p));b=collections.Counter(obs);missing=a-b;extra=b-a
 bad=[x for x in events if x['kind'] in ('root_row_accept','VM_write_accept','final_destination_visible') and x['c']!=0x45a00000]
 return dict(result='PASS' if not missing and not extra and not bad else 'FAIL',expected_events=sum(a.values()),observed_events=sum(b.values()),missing_events=sum(missing.values()),extra_events=sum(extra.values()),nonzero_oracle_mismatches=len(bad),first_missing=list(missing.items())[:12],first_extra=list(extra.items())[:12],categories={k:dict(missing=sum(v for x,v in missing.items() if x[0]==k),extra=sum(v for x,v in extra.items() if x[0]==k)) for k in sorted({x[0] for x in missing}|{x[0] for x in extra})})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepare',type=Path,required=True);a=p.parse_args();prepare(a.prepare)
