"""Private QUERY DROP3 plus exact parent logical cold-state reconstruction; no P&R."""
import re,json
from pathlib import Path
P=Path(__file__).resolve().parent
f=P/'physical_rtl/ot_hbm_idx_query_static__fshell.sv';raw=f.read_text();module='ot_hbm_idx_query_static';start=raw.index('module '+module+' (');head=raw[start:raw.index(');',start)+2]
ports=[]
for d,span,n in re.findall(r'\b(input|output)\s+wire\s*(\[[^]]+\])?\s*(\w+)\s*,?',head):
 w=1
 if span:a,b=map(int,re.findall(r'\d+',span));w=abs(a-b)+1
 ports.append({'direction':d,'range':span or'','name':n,'width':w})
meta=json.loads((P/'face_shell.json').read_text());assert sum(p['width']for p in ports if p['direction']=='output')==570
assert meta['const_out']=={'ql_head':{'5':'0','6':'0','7':'0'}}
# Source model's exact current native public body carries its own PIN1/PIN1.
# The additional outer input/output stages are explicit in this candidate.
s=raw.replace('module '+module+' (','module current_native_query_face (',1)
s=s.replace('ot_hbm_face_reg','bridge_face_reg').replace('ot_hbm_idx_query_static__fcore u_fcore','native_ot_hbm_idx_query_static u_fcore')
(P/'current_native_query_face.sv').write_text(s)
# Physical component loses ONLY the upper three constant-output pins/flops.
s=raw.replace('module '+module+' (','module physical_query_drop3 (',1).replace('ot_hbm_face_reg','bridge_face_reg').replace('ot_hbm_idx_query_static__fcore u_fcore','physical_ot_hbm_idx_query_static__fcore u_fcore')
assert s.count('output wire [7:0] ql_head')==1;s=s.replace('output wire [7:0] ql_head','output wire [4:0] ql_head')
old='ot_hbm_face_reg #(.W(8)) u_bout_ql_head (.clk(clk), .d(ql_head__fc), .q(ql_head));'.replace('ot_hbm_face_reg','bridge_face_reg')
new='bridge_face_reg #(.W(5)) u_bout_ql_head (.clk(clk), .d(ql_head__fc[4:0]), .q(ql_head));'
assert old in s;s=s.replace(old,new);(P/'physical_query_drop3.sv').write_text(s)
# Exact unreset three-stage zero-fed cold-state semantics: corehead, native
# public output, physical outer output. Warm reset must NOT restart this state.
s=head.replace('module '+module+' (','module parent_query_drop_bridge (',1)+'\n'
s+='wire [4:0] physical_head;\n(* keep *) reg[2:0] cold_core,cold_native_pin,cold_outer_pin;\n'
s+="always @(posedge clk) begin cold_core<=3'b0;cold_native_pin<=cold_core;cold_outer_pin<=cold_native_pin;end\n"
s+='assign ql_head={cold_outer_pin,physical_head};\n'
s+='physical_query_drop3 child('+','.join('.'+p['name']+'('+('physical_head'if p['name']=='ql_head'else p['name'])+')'for p in ports)+');\nendmodule\n'
(P/'parent_query_drop_bridge.sv').write_text(s)
(P/'parent_query_drop_bridge_mutant.sv').write_text(s.replace('assign ql_head={cold_outer_pin,physical_head};',"assign ql_head={3'b0,physical_head};"))
(P/'bridge_face_reg.sv').write_text((P/'physical_rtl/ot_hbm_face_reg.sv').read_text().replace('module ot_hbm_face_reg','module bridge_face_reg'))
(P/'ports.json').write_text(json.dumps(ports,indent=2)+'\n')
(P/'drop_contract.json').write_text(json.dumps({'status':'PRIVATE_SOURCE_CANDIDATE_ONLY','removed_physical_pins':['ql_head[5]','ql_head[6]','ql_head[7]'],'physical_output_width_change':'ql_head8->5; everyotherport unchanged','parent_TIE0':'literal zero feeds first unreset3-bit parentstage','parent_cold_state_flops':9,'stages':3,'source_basis':'nativecoreupperzero-fed everyclk unreset; nativepublichead everyclk unreset; physicalouterhead everyclk unreset','warm_reset':'no reset on reconstructedstate; warmresetdoesnotrestartzero pipeline','added_payload_cycles':0,'physical_adoption_holds':['Actualsource/currentclosure proof and wholeparent calendar/context','ActualearlyKEEP/nativegate proof must retain exact9coldFFs OR actualcontextual unobservability proof; RTLkeep alone is not an adoption proof','No new physicalpins, noface_guard exemption; type/view/parentbinding event required']},indent=2)+'\n')
print('QUERY_PORTS',len(ports),'OUTPUTS570','DROP3','PARENTCOLDFF9')
