#!/usr/bin/env python3
"""Wire the native owner to the actual full-shape SMH; external peers stay explicit."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'rtl/hbm_accel/control_20261007'
def generate():
 source=(BASE/'protected/ot_hbm_sm_serial_protected.sv').read_text()
 header=source[source.index('module ot_hbm_sm_serial_protected #('):source.index('\n);')+3]
 area=header[header.index('(\n input wire')+1:header.index('\n);')]
 ports=[]
 for m in re.finditer(r'(input wire|output wire)(.*?)(?=input wire|output wire|$)',area,re.S):
  part=m[2].strip().rstrip(',');w=re.match(r'\[[^\]]+\]',part);width=w[0]if w else''
  ports.extend((m[1],width,n.strip()) for n in part[len(width):].strip().split(','))
 internal=set('xw_en xw_addr xw_grp xw_data d_valid d_ready d_base d_lines start start_ready op_rows op_c op_g op_gs op_fmt op_xb arrive sm_fault'.split())
 extra=[('output wire','','req_v'),('input wire','','req_ready'),('output wire','[31:0]','req_addr'),('output wire','[9:0]','req_tag'),('input wire','','rsp_v'),('input wire','[9:0]','rsp_tag'),('input wire','[1087:0]','rsp_data'),('output wire','','rv'),('output wire','[11:0]','rrow'),('output wire','[255:0]','rdata'),('input wire','','release_in'),('output wire','','released'),('output wire','','busy')]
 public=[p for p in ports if p[2] not in internal]+extra
 out=['// Candidate: real full-shape native SMH. No external peer is fabricated.',
      '// North owner and south descriptor adapter have separate modeled bays.',
      'module ot_hbm_sm_native_owner_join #(parameter ENABLE=0,PROTECT=0,MAX_RECORDS=256,DESC_HOPS=32)(',
      ',\n'.join(' '+d+' '+w+' '+n for d,w,n in public),' );']
 out += [' wire '+w+' '+n+';'for d,w,n in ports if n in internal]
 out += [' wire owner_fault,south_fault,bridge_fault;', ' wire south_d_valid,south_d_ready;', ' wire[31:0]south_d_base;wire[23:0]south_d_lines;', ' wire sm_rst_n=rst_n && ENABLE;', ' assign fault=owner_fault || sm_fault;']
 out += [' ot_hbm_sm_serial_protected #(.ENABLE(ENABLE),.PROTECT(PROTECT),.MAX_RECORDS(MAX_RECORDS)) owner(',
          ',\n'.join(' .'+n+'('+('owner_fault'if n=='fault'else n)+')'for d,w,n in ports),' );']
 out += [' ot_hbm_sm_descriptor_bridge #(.ENABLE(ENABLE),.HOPS(DESC_HOPS),.DEPTH(2)) descriptor(',
  ' .clk(clk),.rst_n(rst_n),.s_valid(d_valid),.s_ready(d_ready),.s_base(d_base),.s_lines(d_lines),',
  ' .d_valid(south_d_valid),.d_ready(south_d_ready),.d_base(south_d_base),.d_lines(south_d_lines),',
  ' .south_fault(south_fault),.north_fault(sm_fault),.fault(bridge_fault));']
 smports='clk rst_n start start_ready op_rows op_c op_g op_gs op_fmt op_xb busy d_valid d_ready d_base d_lines req_v req_ready req_addr req_tag rsp_v rsp_tag rsp_data xw_en xw_addr xw_grp xw_data rv rrow rdata fault arrive release_in released'.split()
 mapping=dict(rst_n='sm_rst_n',fault='south_fault',d_valid='south_d_valid',d_ready='south_d_ready',d_base='south_d_base',d_lines='south_d_lines')
 out += [' ot_hbm_accel_smh sm(', ',\n'.join(' .'+n+'('+mapping.get(n,n)+')'for n in smports),' );','endmodule','']
 target=BASE/'native_join';target.mkdir(exist_ok=True)
 (target/'ot_hbm_sm_native_owner_join.sv').write_text('\n'.join(out))
if __name__=='__main__':generate()
