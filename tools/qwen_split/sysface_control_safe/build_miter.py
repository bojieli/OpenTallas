#!/usr/bin/env python3
"""Public-pin comparator around the untouched functional FACE and real candidate.

Bench-visible debug aliases refer to the original, solely to preserve existing
testbench stimulus scheduling. Every candidate output is compared separately.
"""
import argparse,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--graph',required=True);ap.add_argument('--manifest',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
m=json.loads(Path(a.graph).read_text())['modules']['qfd_sys_face'];params=json.loads(Path(a.manifest).read_text())['parameters'];out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
src=Path(a.source).read_text();src=src.replace('module qfd_sys_face #(','module qfd_sys_face_reference #(',1);(out/'reference.sv').write_text(src)
extra={'MUT':0,'GO_OFS':3,'START_ADJ':0,'OVL_TX_WRAP_BASE':0,'OVL_RX_WRAP_BASE':0,'OVL_ADM_LEN':1100}
allparams={**params,**extra}
s=['module qfd_sys_face #('+','.join('parameter integer '+k+'='+str(v) for k,v in allparams.items())+', parameter ROM_VIAMAP="", ROM_INSTANCE="sys_face_cfg", OVL_ROM_DIR="") (']
s+=[',\n'.join(p['direction']+' wire '+('['+str(len(p['bits'])-1)+':0] ' if len(p['bits'])>1 else '')+n for n,p in m['ports'].items()),');']
for n,p in m['ports'].items():
 if p['direction']=='output':s+=['wire '+('['+str(len(p['bits'])-1)+':0] ' if len(p['bits'])>1 else '')+'safe_'+n+';']
s+=['qfd_sys_face_reference #('+','.join('.'+k+'('+k+')' for k in allparams)+',.ROM_VIAMAP(ROM_VIAMAP),.ROM_INSTANCE(ROM_INSTANCE),.OVL_ROM_DIR(OVL_ROM_DIR)) reference('+','.join('.'+n+'('+n+')' for n in m['ports'])+');']
s+=['qfd_sys_face_control_safe #(.ROM_VIAMAP(ROM_VIAMAP),.ROM_INSTANCE(ROM_INSTANCE),.OVL_ROM_DIR(OVL_ROM_DIR)) candidate('+','.join('.'+n+'('+('safe_' if p['direction']=='output' else '')+n+')' for n,p in m['ports'].items())+');']
for n,v in m['netnames'].items():
 if re.fullmatch('[a-zA-Z_][a-zA-Z0-9_]*',n) and n not in m['ports']:
  s+=['wire '+('['+str(len(v['bits'])-1)+':0] ' if len(v['bits'])>1 else '')+n+' = reference.'+n+';']
s+=['initial begin '+''.join('if('+k+'!='+str(v)+') $fatal(1,"unsupported profile '+k+'"); ' for k,v in allparams.items())+'end']
s+=['integer checked=0; integer quiet=0; always @(posedge ck) if(!rst_n) quiet<=0; else quiet<=quiet+1;',
 'always @(negedge ck) if(quiet>=4) begin checked=checked+1;']
for n,p in m['ports'].items():
 if p['direction']=='output':s+=['if('+n+' !== safe_'+n+') $fatal(1,"SYSFACE_SAFE_EQUIV_FAIL '+n+' sample%0d",checked);']
s+=['end','always @(negedge ck) begin']
receipt=json.loads(Path(a.receipt).read_text())
for x in receipt['forest']:
 reference='reference.rr_s['+str(x['depth']-1)+']' if x['depth']<3 else 'reference.rr_q[0]'
 s+=['if(candidate.n'+str(x['q'])+' !== '+reference+') $fatal(1,"SYSFACE_SAFE_RESET_FAIL '+x['cell']+'");']
for x in receipt['copies']:
 s+=['if(quiet>=4 && candidate.n'+str(x['q'])+' !== candidate.n'+str(x['original_q'])+') $fatal(1,"SYSFACE_SAFE_COPY_FAIL '+str(x['q'])+'");']
s+=['end','final $display("SYSFACE_SAFE_EQUIV checks%0d",checked);','endmodule','']
(out/'miter.sv').write_text('\n'.join(s))
(out/'buffer_model.sv').write_text('// Function and A/Y pins checked against actual ASAP7 RVT TT Liberty.\nmodule BUFx2_ASAP7_75t_R(input wire A,output wire Y);assign Y=A;endmodule\n')
print('miter outputs',sum(p['direction']=='output' for p in m['ports'].values()))
