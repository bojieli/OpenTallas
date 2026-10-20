import pathlib,re,subprocess,json,hashlib
w=pathlib.Path('/home/ubuntu/wt/kv-native-join-default-compare-1019'); d=w/'results/arch/kv_native_join_default_compare_1019'; p=w/'results/arch/kv_native_owner_join_component_1019/private'; old=w/'results/arch/kv_retained_commit_component_1019'
def blob(path):return subprocess.check_output(['git','-C',str(w),'show','60bb2c145:'+path],text=True)
def ports(s):
 h=s[s.index(' input '):s.index(');')]
 result={};direction=None;width=''
 for t in h.split(','):
  t=re.sub(r'//[^\n]*','',t).strip()
  m=re.match(r'(input|output)\s+(?:(?:wire|reg)\s*)?(\[[^]]+\])?\s*(\w+)\s*$',t)
  if m:direction,width,name=m.groups();width=width or ''
  else:
   m=re.fullmatch(r'(\w+)',t)
   if not m:raise ValueError(t)
   name=m.group(1)
  result[name]=(direction,width)
 return result
# scheduler port list via declaration section (header includes comments)
sched=(p/'ot_host_if_pb2_observed_rc.sv').read_text(); base=blob('results/arch/kv_retained_commit_component_1019/private/ot_host_if_pb2_observed_rc.sv')
(d/'scheduler_candidate.sv').write_text(sched);(d/'scheduler_baseline.sv').write_text(base.replace('module ot_host_if_pb2_observed_rc','module scheduler_baseline',1))
# use regex over declaration header for output groups, stripping comments
head=re.sub(r'//[^\n]*','',base[:base.index(');')]); outs=[]
for m in re.finditer(r'output\s+(?:(?:wire|reg)\s+)?(?:\[[^]]+\]\s*)?([^;]+?)(?=\b(?:input|output)\b|\)\s*$)',head,re.S):
 outs += re.findall(r'\b\w+\b',m.group(1).replace(',',' '))
# direct header parser more reliable by begin after parameter closing
clean=re.sub(r'//[^\n]*','',base[base.index('module '):]); start=clean.index('input '); header=clean[start:clean.index(');')];outs=[];direction=None
for t in header.split(','):
 t=t.strip();m=re.match(r'(input|output)\s+(?:(?:wire|reg)\s*)?(?:\[[^]]+\]\s*)?(\w+)\s*$',t)
 if m:direction,name=m.groups()
 elif re.fullmatch(r'\w+',t):name=t
 elif not t:continue
 else:raise ValueError(t)
 if direction=='output':outs.append(name)
b=(old/'scheduler_descriptor_baseline.sv').read_text();match=re.search(r'  ot_host_if_pb2_observed_rc #\(.*?\) dut \(.*?\);',b,re.S);inst=match.group();ref=inst.replace('ot_host_if_pb2_observed_rc #','scheduler_baseline #',1).replace(') dut (',') refdut (')
for o in outs:ref=re.sub(r'\.'+o+r'\([^()]*\)',f'.{o}()',ref)
checks='\n  integer compared_edges=0;\n  always @(negedge clk) begin\n    compared_edges=compared_edges+1;\n'+''.join(f'    if (dut.{o} !== refdut.{o}) $fatal(1,"DEFAULT_MISMATCH {o} edge=%0d",edge_n);\n' for o in outs)+'  end\n'
b=b.replace(inst,inst+'\n'+ref+checks).replace('SCHED_PASS case=','DEFAULT_SCHED_PASS outputs='+str(len(outs))+' case=')
(d/'scheduler_compare.sv').write_text(b)
coverage={'scheduler_original_outputs':outs,'codec_outputs':{}}
for kind in ['rank','coordinator']:
 name='qkd_host_peer_'+kind+'_codec';orig=blob('results/arch/kv_retained_commit_source_plan_1019/selected_source/rtl/qwen_sys/host_integrated_20261014/'+name+'.sv');cand=(p/(name+'_rc.sv')).read_text();(d/(kind+'_baseline.sv')).write_text(orig);(d/(kind+'_candidate.sv')).write_text(cand)
 ps=ports(orig);cs=ports(cand);outputs=[n for n,(di,wi) in ps.items() if di=='output'];inputs=[n for n,(di,wi) in cs.items() if di=='input'];coverage['codec_outputs'][kind]=outputs
 sv='`timescale 1ns/1ps\nmodule '+kind+'_compare;\n'
 for n in inputs:sv+=' reg '+cs[n][1]+' '+n+'=0;\n'
 sv+=' always #5 ck=~ck;\n'
 def instance(module,which):return module+' '+which+' ('+','.join('.'+n+'('+ (n if di=='input' else '') +')' for n,(di,wi) in (cs if which=='dut' else ps).items())+');\n'
 sv+=instance(name+'_rc','dut')+instance(name,'refdut')
 sv+=' integer edge_n=0; always @(negedge ck) begin edge_n=edge_n+1;\n'+''.join(f'if(dut.{n} !== refdut.{n}) $fatal(1,"CODEC_DEFAULT_MISMATCH {kind} {n} edge=%0d",edge_n);\n' for n in outputs)+'end\n'
 sv+='task automatic tick(input integer n); repeat(n) @(negedge ck); endtask\ninteger scenario; initial begin\n'
 sv+='for(scenario=0;scenario<24;scenario=scenario+1)begin\n'
 for n in inputs:
  if n!='ck':sv+=n+'=0;\n'
 sv+='tick(3); por_n=1; tick(3);\n'
 if kind=='rank':
  sv+='tx_ready=scenario[0]; step_retire_native_valid=1; cq_native_valid_observed=1;\ncase(scenario%12)\n'
  for j,n in enumerate(['request_v','cancel_valid','step_issue_v','step_retire_v','cq_commit_v','certificate_v','service_ready','cancel_released','result_cr','rx_valid']):sv+=f'{j}: {n}=1;\n'
  sv+='endcase\nrequest_tag=59\'h123; request_gen=2; cancel_tag=59\'h123; cancel_done=1; step_client_tag=16\'h1234; step_slot=3; step_pos=7; step_retire_client_tag=16\'h1234;step_retire_pos=7;step_retire_token=42;cq_client_tag=16\'h1234;cq_pos=7;cq_token=42;rx_data=512\'h86;\n'
 else:
  sv+='tx_ready={8{scenario[0]}};allocated_valid=1;allocated_tag=59\'h123;allocated_gen=2;allocated_position=7;\n'
  sv+='rx_valid=1;rx_data=0;rx_data[7:0]=8\'(scenario%10+1);rx_data[88:30]=59\'h123;rx_data[90:89]=2;\n'
 sv+='tick(1);\n'
 for n in inputs:
  if n.endswith('_v') or n in ['rx_valid','cancel_valid','cancel_released','result_cr']:sv+=n+'=0;\n'
 sv+='tick(12);end\n$display("CODEC_DEFAULT_PASS '+kind+' outputs='+str(len(outputs))+' scenarios=24 edges=%0d",edge_n);$finish;end\nendmodule\n'
 (d/(kind+'_compare.sv')).write_text(sv)
(d/'coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
print({k:len(v) if isinstance(v,list) else {x:len(y) for x,y in v.items()} for k,v in coverage.items()})
