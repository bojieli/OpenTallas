#!/usr/bin/env python3
"""Full-region cycle model for uniform registered interfaces; no physical kit or closure claim."""
import json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];P=R/'rtl/qwen_sys/vm_plane_20261013/region';p=json.loads((R/'results/arch/qwen_tp8_1012/vm_rg6.json').read_text());name='ot_qfd_vm_rg6_face_model';ports=p['ports'];meta=p['boundary_inputs']
def decl(d,n,w):return f'    {d} '+(f'[{w-1}:0] ' if w>1 else '')+n
V=['// Behavioral staging candidate ONLY: every real rg6 core/lane child remains in u_base.', '// CLOCK input/output stages and ENGINE lane stages are distinct. Async resets remain direct.',f'module {name} #(parameter integer MUT=0) (',',\n'.join([decl('input wire','face_clk',1)]+[decl(x['direction']+' wire',x['name'],x['bits']) for x in ports]),');'];bindings={};me=next(n for n,m in meta.items() if n.startswith('me_vm_'))
for x in ports:
 n=x['name'];w=x['bits'];bindings[n]=n
 if n in meta and not n.startswith('rst_'):
  V += [decl('reg',n+'_f',w)+"=0;",f'    always @(posedge face_clk) {n}_f <= {n};'];bindings[n]=f'((MUT == 3) ? {n} : {n}_f)'
V += ['    reg face_me_prev=0;',f'    always @(posedge face_clk) face_me_prev <= {me}_f;',f'    wire face_enable = (MUT == 4) ? {me} : face_me_prev;']
for x in ports:
 n=x['name'];w=x['bits']
 if x['direction']=='input' and n.startswith('d_'):
  V += [decl('reg',n+'_f',w)+'=0;',f'    always @(posedge face_clk) if (face_enable) {n}_f <= {n};'];bindings[n]=f'((MUT == 5) ? {n} : {n}_f)'
 if x['direction']=='output':
  V += [decl('wire',n+'_raw',w)+';',decl('reg',n+'_f',w)+'=0;',f'    always @(posedge face_clk) '+('if (face_enable) ' if n.startswith('q_') else '')+f'{n}_f <= {n}_raw;',f'    assign {n} = {n}_f;'];bindings[n]=n+'_raw'
V += ['    ot_qfd_vm_rg6 #(.MUT((MUT < 3) ? MUT : 0)) u_base (',',\n'.join('      .'+n+'('+v+')' for n,v in bindings.items()),'    );','endmodule'];(P/(name+'.sv')).write_text('\n'.join(V)+'\n')
tb=(P/'tb_qfd_vm_rg6.sv').read_text().replace('module tb_qfd_vm_rg6;','module tb_qfd_vm_rg6_face_model;').replace('ot_qfd_vm_rg6 #(.MUT(MUT)) candidate (','ot_qfd_vm_rg6_face_model #(.MUT(MUT)) candidate (.face_clk(clk), ').replace('candidate.xo','candidate.u_base.xo')
width={'me_in':1,'re':8,'ra':64,'we':8,'wl':64,'wm':128,'wd':4096,'xv':1,'rq':1,'rqb':3,'sre':6,'sra':60,'sv':3,'swe':2,'swl':20,'swm':32,'swd':1024,'pop':1}
pos=tb.index('    ot_qfd_vm_region_quarter #(');end=tb.index('    reg lane_me_prev',pos);flat=tb[pos:end];D=[]
for n,w in width.items():
 D += [decl('reg','face_ref_'+n,w)+'=0;',f'    always @(posedge clk) face_ref_{n} <= {n};'];flat=flat.replace('.'+n+'('+n+')','.'+n+'(face_ref_'+n+')')
for n,w in [('ro',512),('so',3072),('ovf',1)]:
 D += [decl('wire','raw_r_'+n,w)+';',decl('reg','delay_r_'+n,w)+'=0;',f'    always @(posedge clk) delay_r_{n} <= raw_r_{n};',f'    assign r_{n} = delay_r_{n};'];flat=flat.replace('.'+n+'(r_'+n+')','.'+n+'(raw_r_'+n+')')
tb=tb[:pos]+'\n'.join(D)+'\n'+flat+tb[end:]
pos=tb.index('    reg lane_me_prev');end=tb.index('    // xorshift64',pos);refs=['    reg lane_me_prev=0;','    integer lane_checks=0,lane_nonzero=0;','    always @(posedge clk) lane_me_prev <= face_ref_me_in;']
for k,s in enumerate(p['segments']):
 inp=f'r_xo[{s["source_bits"]} +: 8]' if s['local_source'] else f'{s["input"][0]}[{s["input"][1]} +: 8]';d=s['stages']+(1 if s['local_source'] else 2);op=f'{s["output"][0]}[{s["output"][1]} +: 8]'
 refs += [f'    reg [{d*8-1}:0] face_ref{k}=0;',f'    always @(posedge clk) if(lane_me_prev) face_ref{k} <= '+(f'{{face_ref{k}[{d*8-9}:0], {inp}}};' if d>1 else inp+';'),f'    always @(posedge clk) begin #1; if(cyc>40) begin lane_checks=lane_checks+1; if(face_ref{k}[{(d-1)*8} +: 8] != 0) lane_nonzero=lane_nonzero+1; if({op} !== face_ref{k}[{(d-1)*8} +: 8]) begin errors=errors+1; if(errors<4) $display("face region lane mismatch segment {k}"); end end end']
tb=tb[:pos]+'\n'.join(refs)+'\n'+tb[end:];tb=tb.replace('PASS qfd_vm_rg6','PASS qfd_vm_rg6_face_model').replace('FAIL qfd_vm_rg6','FAIL qfd_vm_rg6_face_model');(P/'tb_qfd_vm_rg6_face_model.sv').write_text(tb)
a=dict(schema='opentallas.vm-registered-interface-cycle-model.v1',status='BEHAVIORAL_CANDIDATE_ONLY',region=6,core_leaves=72,lane_tiles=77,segments=len(p['segments']),core_command_input_added_clock_edges=1,core_output_added_clock_edges=1,async_reset_policy='direct existing reset ports; no new reset register',engine_qualifier='previous uniformly delayed me: original raw me two CLOCK edges before execution',external_lane_segment_added_engine_edges=2,local_source_segment_added_engine_edges=1,new_boundary_data_regs=sum(x['bits'] for x in ports if (x['name'] in meta and not x['name'].startswith('rst_')) or x['name'].startswith(('d_','q_')) or x['direction']=='output'),mutants={1:'original lane stage bypass',2:'original core row selection defect',3:'core command input CLOCK stage bypass',4:'face ENGINE enable uses raw early me',5:'external ENGINE entry stage bypass'},physical_warning='No physical masters/slots/IOpinmapping/setup/hold/CTS/PG/route assigned to model FFs. Global4..10ENGINE crossing delta needs equalization and throughput measurement. Not production RTL.')
(R/'results/arch/qwen_tp8_1012/rg6_registered_face_model.json').write_text(json.dumps(a,indent=1)+'\n');print(a)
