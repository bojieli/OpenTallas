from pathlib import Path
import json,re,hashlib
O=Path(__file__).resolve().parent;p=O/'selected_safe_leaves_a36c24de8.sv';s=p.read_text();sha=hashlib.sha256(p.read_bytes()).hexdigest();assert sha=='f612ec8c28f9feed7f5c5cb22136962ac9d8e7fafbf5ab5e7d739ebffd0632bc'
a=s.index('module ot_hgi_coll_static_program_target_s128');target=s[a:s.index('endmodule',a)];assigns=re.findall(r'issuer_cfg\s*<=\s*([^;]+);',target);assert len(assigns)==6 and assigns.count('0')==2,assigns
payload=[]
for a in assigns:
 if a=='0':payload.append({'rhs':a,'bits35_34':0});continue
 m=re.match(r"\{1'b1,4'd([0-3]),",a);assert m,a;tag=int(m[1]);assert tag>>2==0;payload.append({'rhs':a,'tag':tag,'bits35_34':(tag>>2)&3})
assert "assign cause_now[15:14]=2'b00;" in s
assert "if(k<NPT)begin:p assign link3[k]=lk_q[k]; end else begin:z assign link3[k]=1'b0;" in s
assert "if(!rst_q)begin fault<=1'b0;fault_cause<=16'd0;end" in s
assert 'fault_cause<=fault_cause | cause_now;' in s
for top in ['ot_hgi_coll_fj_n2s1_r128','ot_hgi_coll_fj_q2_r128']:
 a=s.index('module '+top);part=s[a:s.index('endmodule',a)];assert '.NPT(2)' in part
proof={'status':'PASS','selected_commit':'a36c24de86d0dceaca2ae2dfb115ae486326d34d','selected_source':'rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_safe_leaves.sv','selected_source_sha256':sha,'issuer_cfg_assignments_complete':payload,'bits':{'issuer_cfg[35]':'all assignments give0: command tags0..3 tag[3]=0, reset/default0','issuer_cfg[34]':'all assignments give0: command tags0..3 tag[2]=0, reset/default0','fault_cause[15]':'cause_now[15]=0; reset0; next=old|0 preserves0','fault_cause[14]':'cause_now[14]=0; reset0; next=old|0 preserves0','fault_cause[8]':'both wrappers NPT2; k2>=2 =>link3[2]=0 =>cause_now[8]=0; reset0; next=old|0 preserves0'},'domain':'All configuration/descriptor/fault modes AFTER required reset. issuer_cfg upperbits also0 after firstedge. No claim for stickyfault arbitrary pre-reset retained state. No input constraint/mask is introduced.','induction':{'reset_value':0,'next_if_invariant0':0|0,'all_current_cases':[[q,q|0] for q in [0,1]],'statement':'reset base0; preservation0 OR0=0; repeated asynchronous reset reestablishes0. Initial-state assumption is exactly required architectural reset, never arbitrary-state zeroing.'},'excerpts':[{'line':i+1,'text':l} for i,l in enumerate(s.splitlines()) if any(t in l for t in ['issuer_cfg<=','cause_now[15:14]','link3[k]','cause_now[8:6]','fault_cause<=','ot_hgi_coll_fj_core_s128 #(.NPT(2)'])]}
(O/'selected_constant_source_proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('SELECTED_RTL_CONSTANT_PROOF_PASS',sha)
