#!/usr/bin/env python3
"""Observed pin relations only. Never emits a timing profile or DUT stimulus."""
import argparse,collections,copy,hashlib,json,re
from pathlib import Path

def parse(p):
 out=[]
 for line in p.read_text().splitlines():
  if not line.startswith('QWEVENT|'):continue
  t=line.split('|')
  if len(t)!=8:raise ValueError(line)
  event=t[5];out.append(dict(raw_quantized_time_label=int(t[1]),instance=t[2],edge=int(t[3]),reset_epoch=int(t[4]),event=event,value=t[6],aux=t[7],clock='functional_ck',sampling='negedge settled pins' if event=='XPF_LEAF_Q_PINS' else 'posedge pre-NBA'))
 return out

def leafno(e):
 m=re.search(r'g_ch\[(\d+)\].g_leaf\[(\d+)\]',e['instance'])
 if not m:raise ValueError('missing actual leaf hierarchy '+e['instance'])
 return 4*int(m[1])+int(m[2])

def validate(ev):
 errors=[];relations=[];by=collections.defaultdict(list);origin={}
 for e in ev:
  by[e['event']].append(e)
  if e['reset_epoch']!=1:errors.append('RESET_EPOCH')
  key=(e['instance'],e['event']);old=origin.setdefault(key,e['edge'])
  if e['edge']<old:errors.append('CLOCK_EDGE_ORDER')
  origin[key]=e['edge']
 for name,n in [('ME_ACCEPT',4),('XPF_HEAD_GO_CAPTURE',4)]:
  if len(by[name])!=n:errors.append('COVERAGE_'+name)
 for name in ['ME_MEM_PIPE_CAPTURE_TAG_MV','ME_WEIGHT_READ_PINS','ME_PART_RESULT_VALID','XPF_LEAF_WRITE_CAPTURE','XPF_LEAF_CLEAR_CAPTURE','XPF_LEAF_REQUEST_PINS','XPF_LEAF_READ_CAPTURE','XPF_LEAF_Q_PINS','XPF_QD_INPUT_CAPTURE']:
  if not by[name]:errors.append('MISSING_'+name)
 reads={(e['edge'],leafno(e)):e for e in by['XPF_LEAF_READ_CAPTURE']}
 consumed=set()
 for h in by['XPF_LEAF_REQUEST_PINS']:
  mask=int(h['aux'],16);addresses=int(h['value'],16)
  for leaf in range(8):
   if not mask>>leaf&1:continue
   k=(h['edge'],leaf);r=reads.get(k)
   if r is None:errors.append('HEAD_TO_LEAF_CAPTURE_MISSING');continue
   consumed.add(k);address=addresses>>(28*leaf)&((1<<28)-1)
   if int(r['value'],16)!=address:errors.append('HEAD_TO_LEAF_ADDRESS')
   relations.append(dict(kind='head_request_to_actual_leaf_capture',edge=h['edge'],leaf=leaf,address_hex=hex(address),observed_common_clock_edges=0,native_qualified=False))
 if set(reads)!=consumed:errors.append('LEAF_CAPTURE_WITHOUT_HEAD_REQUEST')
 qs={(e['edge'],leafno(e)):e for e in by['XPF_LEAF_Q_PINS']}
 for h in by['XPF_QD_INPUT_CAPTURE']:
  mask=int(h['aux'],16);data=int(h['value'],16)
  for leaf in range(8):
   if not mask>>leaf&1:continue
   q=qs.get((h['edge']-1,leaf))
   if q is None:errors.append('LEAF_Q_TO_HEAD_QD_MISSING');continue
   if int(q['value'],16)!=(data>>(64*leaf)&((1<<64)-1)):errors.append('LEAF_Q_TO_HEAD_QD_DATA')
   relations.append(dict(kind='settled_leaf_Q_to_head_QD_input',source_edge=q['edge'],capture_edge=h['edge'],leaf=leaf,source_sample_phase="negedge",capture_phase="next posedge",native_time=None,native_qualified=False,read_identity=None))
 return sorted(set(errors)),relations

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);ap.add_argument('--consumer-only',action='store_true');a=ap.parse_args();p=a.root
 ev=parse(p/'receipts/attempt2/probes.log');errors,relations=validate(ev)
 controls={}
 for name,event,field,value in [('missing_read','XPF_LEAF_READ_CAPTURE',None,None),('wrong_address','XPF_LEAF_READ_CAPTURE','value','ffffffff'),('wrong_clock','ME_MEM_PIPE_CAPTURE_TAG_MV','edge',999999),('wrong_reset','XPF_LEAF_READ_CAPTURE','reset_epoch',2)]:
  x=copy.deepcopy(ev);i=next(i for i,e in enumerate(x)if e['event']==event)
  if field:x[i][field]=value
  else:x.pop(i)
  reject,_=validate(x);controls[name]=reject
  if not reject:errors.append('HOLLOW_GRAPH_CONTROL_'+name)
 base=p/'receipts/attempt2/baseline.trace';probe=p/'receipts/attempt2/probes.trace';eq=base.read_bytes()==probe.read_bytes()
 if not eq:errors.append('PASSIVE_TRACE_CHANGED')
 original='\n'.join(x for x in (p/'inputs/original_xt1.log').read_text().splitlines()if len(x.split())>1 and x.split()[1]in('TGO','TX','TOUT'))+'\n'
 original_equal=base.read_bytes()==original.encode()
 if not original_equal:errors.append('ORIGINAL_XT1_CONE_TRACE_CHANGED')
 witness=(p/'receipts/attempt2/read_address_mut.log').read_text()
 causal='STAGE1_CONSUMER_TERMINAL hd_fault=1 stream_fault=0' in witness and 'SIM_RC=0' in witness
 if not causal:errors.append('MISSING_ACTUAL_DUT_READ_ADDRESS_REJECT')
 if 'STAGE1_CONSUMER_TERMINAL hd_fault=0 stream_fault=0' not in (p/'receipts/attempt2/probes.log').read_text():errors.append('NOMINAL_DUT_FAULT')
 report=dict(schema='opentallas.qwen.private-source-event-graph.consumer-stage1.v1',verdict='PASS' if not errors else 'FAIL',errors=errors,counts=dict(collections.Counter(e['event']for e in ev)),events=ev,relations=relations,graph_controls=controls,actual_DUT_control=dict(kind="first GO read xbase bit0 corruption",sticky_head_fault=1,nominal_sticky_head_fault=0,wrapper_rc=0,qualified_causal_reject=causal),architectural_trace_equal=eq,original_XT1_cone_trace_equal=original_equal,original_XT1_cone_trace_lines=len(original.splitlines()),baseline_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),complete_graph_verdict='UNRESOLVED_FAIL_CLOSED',unresolved=['Actual SYSFACE producer/ROM replay absent','Selected CALR-to-frozen-CALD command interface absent','This fixed four-operation XT1 profile is independent of selected25-instruction CALR profile','Issue immutable ROM entry identity absent','ME/XPF authenticated final-read receipt identity absent','Original four ME timing mismatches retained','Native clock/reset phase and first-use NULL','Original expected serialization1f5b bytes absent'],native_phase=None,token_cycles=None,profile_modified=False,handles_or_list_size_choice=None)
 (p/'consumer_graph.json').write_text(json.dumps(report,indent=2)+'\n')
 print('CONSUMER_OBSERVATION_'+report['verdict'],json.dumps(report['counts'],sort_keys=True))
 print('FULL_STAGE1_UNRESOLVED_FAIL_CLOSED')
 if errors:raise SystemExit(1)
 if not a.consumer_only:raise SystemExit(2)
if __name__=='__main__':main()
