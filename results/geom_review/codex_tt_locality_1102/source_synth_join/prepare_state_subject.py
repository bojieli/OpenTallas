"""Prepare exact selected witness-control context for a future finite23-state relation."""
from pathlib import Path
import argparse,re,json,hashlib
ap=argparse.ArgumentParser();ap.add_argument('--old',type=Path,required=True);ap.add_argument('--new',type=Path,required=True);ap.add_argument('--transition',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
def balanced(s,start):
 if s[start]!='(':raise ValueError('Expected parenthesized source')
 depth=0
 for i in range(start,len(s)):
  if s[i]=='(':depth+=1
  elif s[i]==')':
   depth-=1
   if not depth:return s[start+1:i],i+1
 raise ValueError('Unclosed selected source expression')
def module(text,name):
 m=re.search(r'\bmodule\s+'+re.escape(name)+r'\b',text)
 if not m:raise ValueError('Missing selected module '+name)
 end=text.index('endmodule',m.end())+len('endmodule');return text[m.start():end]
def params(body):
 m=re.match(r'module\s+\w+\s*#\s*\(',body)
 if not m:return {}
 p,_=balanced(body,m.end()-1);return dict(re.findall(r'\b([A-Za-z_]\w*)\s*=\s*([^,]+)',p))
def argmap(text):
 out={};pos=0
 while True:
  m=re.search(r'\.(\w+)\s*\(',text[pos:])
  if not m:break
  start=pos+m.end()-1;v,pos=balanced(text,start);out[m[1]]=re.sub(r'\s+','',v)
 return out
def instance(text,module_name,instance_name):
 m=re.search(r'\b'+re.escape(module_name)+r'\s+',text)
 if not m:raise ValueError('Missing selected callee')
 pos=m.end();overrides={}
 if text[pos]=='#':
  start=text.index('(',pos);p,pos=balanced(text,start);overrides=argmap(p)
 m2=re.match(r'\s*'+re.escape(instance_name)+r'\s*\(',text[pos:])
 if not m2:raise ValueError('Unexpected selected instance')
 p,end=balanced(text,pos+m2.end()-1);return dict(text=text[m.start():end+1],parameters=overrides,ports=argmap(p))
oldctx=json.loads((a.old/'core_context.json').read_text());newctx=json.loads((a.new/'core_context.json').read_text())
if oldctx!=newctx:raise ValueError('Actual core callsite/clock/reset chain differs')
rows={};body_files={}
for name,file in [('qfd_dv_typed_witness_control','qfd_dv_typed_witness_control_frozen.sv'),('qfd_wtn_kept_select','qfd_dv_typed_witness_control_frozen.sv'),('qfd_tt_ctlm_dv_wtn','qfd_tt_ctlm_dv_wtn.sv'),('qfd_bmath_dff_p','qfd_tt_ctlm_dv_hp13_rrloc_helpers.sv')]:
 old=module((a.old/file).read_text(),name);new=module((a.new/file).read_text(),name)
 if old!=new:raise ValueError('Selected module body differs '+name)
 (a.out/(name+'_BODY.sv')).write_text(old+'\n');body_files[name]=dict(body_equal=True,body_sha256=hashlib.sha256(old.encode()).hexdigest(),declared_parameters=params(old))
 rows[name]=old
ctlcall=instance(rows['qfd_tt_ctlm_dv_wtn'],'qfd_dv_typed_witness_control','u_ctl')
resolved={k:v.strip() for k,v in body_files['qfd_dv_typed_witness_control']['declared_parameters'].items()};resolved.update(ctlcall['parameters'])
expected=dict(ENABLE='1',SAFE_COMPARE='1',SAFE_SELECT='1',SAFE_PHYS='1',GROUPS='13',TEMPLATE_BITS='134',PROFILE_DIGEST="64'h198f7708b478a667",PROFILE_EPOCH="16'd7")
if resolved!=expected:raise ValueError('Resolved selected control parameters differ: '+repr(resolved))
if body_files['qfd_tt_ctlm_dv_wtn']['declared_parameters']!={'MUT':'0\n'} and {k:v.strip() for k,v in body_files['qfd_tt_ctlm_dv_wtn']['declared_parameters'].items()}!={'MUT':'0'}:raise ValueError('Wrapper MUT default differs')
calltext=newctx['actual_wtn_callsite'];ports=argmap(balanced(calltext,calltext.index('('))[0])
if '#(' in calltext:raise ValueError('Unexpected actual wrapper parameter override')
corecalls={}
for tag,root in [('old',a.old),('new',a.new)]:
 corecalls[tag]=instance((root/'qfd_qc_tt_ctlm_part_bound.sv').read_text(),'qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1','u_core')
if corecalls['old']!=corecalls['new']:raise ValueError('Actual parent/core callsite port ABI differs')
if corecalls['new']['ports']['ck_core']!='clk' or corecalls['new']['ports']['rst_n']!='rst_n':raise ValueError('Unexpected selected core clock/reset source')
bound_traces={}
for tag,root in [('old',a.old),('new',a.new)]:
 text=(root/'qfd_qc_tt_ctlm_part_bound.sv').read_text()
 if not re.search(r'wire\s+rst_n\s*=\s*rst_n_t0\s*;',text):raise ValueError('Core raw reset alias differs')
 producers={}
 for m in re.finditer(r'ot_dp_rrelay\s+(\w+)\s*\((.*?)\);',text):
  ports0=argmap(m[2]);producers[ports0['q']]=dict(instance=m[1],ports=ports0,text=m[0])
 trace=[];net='rst_n_t0';seen=set()
 while net in producers:
  if net in seen:raise ValueError('Bound reset relay loop')
  seen.add(net);r=producers[net]
  if r['ports']['clk']!='clk':raise ValueError('Bound reset clock differs')
  trace.append(dict(net=net,**r));net=r['ports']['d']
 if net!='arst_n' or len(trace)!=4:raise ValueError('Actual bound reset is not the observed4relays from arst_n')
 bound_traces[tag]=trace
if bound_traces['old']!=bound_traces['new']:raise ValueError('Actual bound reset path changed')
# Source wrapper resolves MUT0 to these exact bit expressions; source body is included.
resolved_ctl=dict(ctlcall['ports']);resolved_ctl.update(all_copies_authenticated='auth[81]&&!auth[82]',installed_epoch='auth[15:0]',start_epoch='start[15:0]',retire_user='retire[2:1]')
def corebits(expr):
 m=re.fullmatch(r'(\w+)\[(\d+)(?::(\d+))?\]',expr)
 if not m:return None
 port,hi,lo=m[1],int(m[2]),int(m[3] or m[2]);v=ports[port]
 bits=v[1:-1].split(',') if v.startswith('{') and v.endswith('}') else [v]
 if hi>=len(bits) or lo>hi:raise ValueError('Selected core bus index outside actual width')
 return [bits[len(bits)-1-i] for i in range(hi,lo-1,-1)]
input_keys=['ck','rst_n','pw_v','pw_addr','pw_data','all_copies_authenticated','fusedcap','installed_digest','installed_epoch','start_v','start_user','start_stage','start_epoch','retire_v','retire_user','ME_XPF_retired','observation','event_stage','event_epoch']
inputs={}
for key in input_keys:
 expr=resolved_ctl[key];entry=dict(wrapper_expression=expr)
 if expr in ('ck','rst_n'):entry['actual_core_expression']=ports[expr]
 elif key=='all_copies_authenticated':entry['actual_core_expression']=dict(and_inputs=[corebits('auth[81]')[0],dict(not_input=corebits('auth[82]')[0])])
 else:entry['actual_core_bits_msb_first']=corebits(expr)
 inputs[key]=entry
trans=json.loads(a.transition.read_text());captures=[]
for n,nn in sorted(trans['proposed_correspondence'].items()):
 k=int(n.strip('_'))
 if 50814<=k<=50819:source=f'gp.f_start_stage[{k-50814}]'
 elif 50821<=k<=50836:source=f'gp.f_start_epoch[{k-50821}]'
 else:source='actual133-leaf comparator D function, universal proof unit3390831'
 captures.append(dict(old_native=n,fresh_native_candidate=nn,source_D_identity=source,actual_clock='clk',clock_edge='posedge',primitive='DFFHQNx1_ASAP7_75t_R',actual_primitive_state_vars=['IQN','IQNN'],primitive_next_state='!D',primitive_output_function='IQN',external_output_capture='QN(t+1)=!D(t)',async_reset_pin=None,enable_pin=None,initial_relation='UNPROVED',alias_accepted=False))
# Preserve actual reset/enable statements verbatim, without treating source comments as assumptions.
control_lines=rows['qfd_dv_typed_witness_control'].splitlines();context='\n'.join(l for l in control_lines if any(t in l for t in ('reg rs1,rs2','rs1<=','rli(','rlr(','rlo(','f_start_stage<=','f_start_epoch<=','if(!rl_ins)','if(!rl_run)','if(!rl_out)')))
(a.out/'selected_reset_enable_context.txt').write_text(context+'\n')
subject=dict(status='PREP_EXACT_COMPOSITIONAL_STATE_SUBJECT_ONLY',module_bodies=body_files,resolved_control_parameters=resolved,resolved_wrapper_parameters=dict(MUT=0),derived_NC=6,actual_wrapper_to_control_callsite=ctlcall,actual_core_to_wrapper_callsite=newctx['actual_wtn_callsite'],actual_parent_to_core_callsite=corecalls['new'],actual_selected_control_inputs=inputs,old_new_callsite_input_identity=True,actual_clock_alias=newctx['clock_alias'],actual_reset_trace=newctx['reset_trace'],reset_trace_terminal=newctx['reset_trace_terminal'],upstream_registered_reset_edges=6,actual_bound_reset_alias='rst_n= rst_n_t0',actual_bound_reset_trace=bound_traces['new'],actual_root_reset_port='arst_n',total_synchronous_reset_relays_before_control=10,internal_reset_context='same source rs1/rs2 and rli/rlr/rlo; actual context included, no protocol/initial assumption added',capture_abi=captures,source_event_declared_netff=13,source_event_actual_netff=12,cycles_added=0,comparison_policy='Unconditional actual23 state relation; retain invalid-cycle comparison and all reset transitions. None/None is not proof.',native_base_proved=False,native_step_relation_accepted=False,physical_release=False,full_source_credit=False)
(a.out/'subject.json').write_text(json.dumps(subject,indent=1)+'\n');print('EXACT_STATE_SUBJECT moduleBODY+params+allcallsiteinputs+6resetedges+23captureABI; no proof')
