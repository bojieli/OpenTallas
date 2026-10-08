#!/usr/bin/env python3
"""Generate a separate protected successor without changing baseline source."""
from pathlib import Path
import re,hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'rtl/hbm_accel/control_20261007/ot_hbm_sm_serial_owner.sv'
OUT=ROOT/'rtl/hbm_accel/control_20261007/protected'

def generate():
    original=BASE.read_text()
    text=original.replace('module ot_hbm_sm_serial_owner #(', '(* keep = 1, keep_hierarchy = 1, dont_touch = 1 *)\nmodule ot_hbm_sm_serial_protected_core #(')
    text=text.replace('output reg fault\n);','output reg fault, output wire state_parity\n);')
    critical='state,record,address,limit,count,index,word_index,group,ordinal,weight_base,resident,resident_base,resident_extent,resident_c,resident_fmt,arrive_q,arrived,published,started,fault,xw_en,xw_addr,xw_grp,xw_data'
    text=text.replace('wire[31:0] rows=', 'assign state_parity=^{'+critical+'};\n wire[31:0] rows=')
    digest=hashlib.sha256(BASE.read_bytes()).hexdigest()
    text='// Generated additive core; baseline SHA256 '+digest+'\n'+text
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/'ot_hbm_sm_serial_protected_core.sv').write_text(text)
    header=original[original.index('module ot_hbm_sm_serial_owner #('):original.index('\n);')+3]
    header=header.replace('ot_hbm_sm_serial_owner #(', 'ot_hbm_sm_serial_protected #(').replace('ENABLE=0, MAX_RECORDS=256','ENABLE=0, MAX_RECORDS=256, PROTECT=0').replace('output reg','output wire')
    ports=[]
    area=header[header.index('(\n input wire')+1:header.index('\n);')]
    for m in re.finditer(r'(input wire|output wire)(.*?)(?=input wire|output wire|$)',area,re.S):
        part=m[2].strip().rstrip(',');w=re.match(r'\[[^\]]+\]',part)
        width=w[0] if w else '';names=part[len(width):].strip().split(',')
        for n in names:ports.append((m[1].startswith('input'),width,n.strip()))
    out=['// Opt-in DMR candidate. Any disagreement aborts, never votes or retries.',header]
    outputs=[n for i,w,n in ports if not i]
    for i,w,n in ports:
        if not i:out.append(f' wire {w} a_{n},b_{n};')
    out+=[' wire a_parity,b_parity;', ' reg abort_latched;', ' wire mismatch;']
    for prefix in ['a','b']:
        if prefix=='b':out.append(' generate if(PROTECT)begin: g_secondary')
        con=[f'.{n}({n if i else prefix+"_"+n})' for i,w,n in ports]
        con.append('.state_parity('+prefix+'_parity)')
        out.append(' (* keep = 1, keep_hierarchy = 1, dont_touch = 1 *) ot_hbm_sm_serial_protected_core #(.ENABLE(ENABLE),.MAX_RECORDS(MAX_RECORDS)) '+prefix+'('+','.join(con)+');')
        if prefix=='b':
            out.append(' end else begin:g_unprotected')
            out += [f' assign b_{n}=a_{n};' for n in outputs]
            out += [' assign b_parity=a_parity;',' end endgenerate']
    flags=['run_ready','mem_req_valid','mem_rsp_ready','alloc_valid','alloc_rsp_ready','x_req_valid','x_ready','xw_en','d_valid','start','publication_ready','done','fault']
    def different(names):
        return '({'+','.join('a_'+n for n in names)+'} != {'+','.join('b_'+n for n in names)+'})'
    comparisons=[different(flags), '(a_parity != b_parity)']
    for valid,names in [('mem_req_valid',['mem_req_addr']),('alloc_valid',['alloc_record','alloc_lines']),('x_req_valid',['x_req_record','x_req_base','x_req_extent']),('xw_en',['xw_addr','xw_grp','xw_data']),('d_valid',['d_base','d_lines']),('start',['op_rows','op_c','op_g','op_gs','op_fmt','op_xb'])]:
        comparisons.append('(a_'+valid+' && '+different(names)+')')
    out.append(' assign mismatch=PROTECT && ('+' || '.join(comparisons)+');')
    out += [' wire blocked=abort_latched || mismatch || a_fault || b_fault;',
            ' always @(posedge clk or negedge rst_n)if(!rst_n)abort_latched<=0;else if(blocked)abort_latched<=1;']
    out += [' assign fault=blocked;']
    for i,w,n in ports:
        if not i and n!='fault':
            out.append(f" assign {n}="+(f"blocked ? '0 : a_{n};" if n in flags else f"a_{n};"))
    out += ['endmodule','']
    (OUT/'ot_hbm_sm_serial_protected.sv').write_text('\n'.join(out))
if __name__=='__main__':generate()
