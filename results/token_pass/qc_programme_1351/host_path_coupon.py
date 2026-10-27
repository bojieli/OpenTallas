from pathlib import Path
import json,sys,hashlib,re
bound,root,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
fields=dict(host_epoch=16,host_epoch_valid=1,host_fused_capability=1,host_generation=2,host_tag=59)
a=(bound/'rtl/qfd_qc_glue_part.sv').read_text();b=(bound/'rtl/qfd_qc_native59_part.sv').read_text()
source=(root/'rtl/qwen_split/qfd_native59_svc_obs1.sv').read_text()
head='`timescale 1ns/1ps\nmodule host_path(input clk,rst_n,'+','.join(f'input[{w-1}:0]w_sys_face_{n}' for n,w in fields.items())+',output reg p_hev,p_hfc,output reg[15:0]p_he,output reg[58:0]p_ht,output reg[1:0]p_hg);\n'
body='wire ck=clk,rst_pin=rst_n;\n'
for n,w in fields.items():
 body+=f'wire[{w}:0]sys_face__{n};wire[{w}:0]{n}=sys_face__{n};wire[{w-1}:0]{n}_q;wire {n}_eq;wire[{w-1}:0]bnd_{n}={n}_q;\n'
 for text,prefix in [(a,'u_bout_sys_face__'),(b,'u_bin_')]:
  matches=[line for line in text.splitlines() if re.search(r'\b'+prefix+n+r'\s*\(',line)]
  assert len(matches)==1,(n,prefix)
  body+=matches[0]+'\n'
reset='p_hev<=0;p_hfc<=0;p_he<=0;p_ht<=0;p_hg<=0;'
cap='p_hev<=bnd_host_epoch_valid;p_hfc<=bnd_host_fused_capability;p_he<=bnd_host_epoch;p_ht<=bnd_host_tag;p_hg<=bnd_host_generation;'
assert reset in source and cap in source
body+='always @(posedge ck or negedge rst_pin) if(!rst_pin)begin '+reset+'end else begin '+cap+'end\n'
for m in range(3):
 s=body
 if m==1:
  line=next(x for x in s.splitlines() if 'u_bout_sys_face__host_epoch_valid ' in x)
  s=s.replace(line,"assign sys_face__host_epoch_valid={rst_n,w_sys_face_host_epoch_valid};")
 if m==2:s=s.replace('.d(w_sys_face_host_generation[1:0])','.d(w_sys_face_host_tag[1:0])')
 (out/f'host_path_m{m}.sv').write_text(head+s+'endmodule\n')
cells=(bound/'rtl/bind_cells.sv').read_text();start=cells.index('module ot_dp_st ');end=cells.index('endmodule',start)+len('endmodule');(out/'bind_st.sv').write_text(cells[start:end]+'\n')
(out/'host_extraction.json').write_text(json.dumps(dict(bound=str(bound),source_stage='Exact five source u_bout and sink u_bin instances plus exact native RECV_INPUTS0 p_* capture statements',host_fields=fields,mutants=['nominal exact instances','valid source-boundary bypass (-1)','generation from wrong tag field'],source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [bound/'rtl/qfd_qc_glue_part.sv',bound/'rtl/qfd_qc_native59_part.sv',bound/'rtl/bind_cells.sv',root/'rtl/qwen_split/qfd_native59_svc_obs1.sv']}),indent=2)+'\n')
