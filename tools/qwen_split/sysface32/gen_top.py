#!/usr/bin/env python3
"""Build the private SYSFACE32 intermediate and real pin-register copy wrapper.

This intermediate intentionally retains replicated net references. Only the
weighted source constructor plus a full flattened native census may qualify
its bounded implementation. Original SYSFACE source and pin wrapper are inputs.
"""
import argparse,hashlib,json,re
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(core_path,wrapper_path,receipt_path,out):
 core=Path(core_path).read_text();wrapper=Path(wrapper_path).read_text();record=json.loads(Path(receipt_path).read_text())
 ports={b:(name,i) for name,row in record['original_ports'].items() if row['direction']=='input' for i,b in enumerate(row['bits'])}
 copies=record['input_copies'];external=[];bindings=[]
 rawport={'auth_slot':'prog_auth_slot','context_slot':'prog_context_slot','witness_slot':'prog_witness_slot','descriptor_obs':'seq_descriptor_obs'}
 for c in copies:
  name,bit=ports[c['original_bit']];idx=c['index']
  if name=='execution_active':
   assert bit==0;bindings.append(f'    assign record_copies[{idx}]=l_run;');continue
  if name=='program_obs2':
   parent='tt_program_obs' if bit<76 else 'seq_program_obs';source=f'{parent}[{bit%76}]'
  else:
   if name not in rawport:raise ValueError(f'No actual parent producer for {name}[{bit}]')
   parent=rawport[name];source=parent if name.endswith('_slot') else f'{parent}[{bit}]'
  n=len(external);external.append(dict(record_copy=idx,parent_raw_bit=source,original_record_port=name,original_record_index=bit))
  bindings.append(f'    assign record_copies[{idx}]=pin_source_copies[{n}];')
 assert [x['index'] for x in copies]==list(range(len(copies)))
 assert len(record['reset_leaves'])<=128
 core=core.replace('module qfd_sys_face #(', 'module qfd_sys_face_core_n32 #(',1)
 needle='    input  wire          rst_n,'
 assert core.count(needle)==1
 core=core.replace(needle,needle+f'\n    input wire [{len(external)-1}:0] pin_source_copies,',1)
 a=core.index('    localparam integer RST_REGIONS = 14;');end=core.index('    // ================================================================ config ROM',a)
 reset='    wire [511:0] rst_leaf;\n    qfd_sysface_reset32 #(.LEAVES(512)) u_reset32(.ck(ck),.rst_n(rst_n),.leaf_n(rst_leaf));\n    wire rst_boot=rst_leaf[192],rst_loop=rst_leaf[193],rst_out=rst_leaf[194];\n    wire rst_bpay=rst_leaf[195],rst_emb=rst_leaf[196],rst_st=rst_leaf[197];\n    wire [5:0] rst_rec=rst_leaf[0+:6];\n    // Production specialization is source-pinned; original defaults untouched.\n    initial if(MU!=1 || MU_HEAD!=1) $fatal(1,"SYSFACE32 needs MU1/MU_HEAD1");\n\n'
 core=core[:a]+reset+core[end:]
 old='    qfd_sys_face_record_port #(.MU_HEAD(MU_HEAD)) u_record ('
 assert core.count(old)==1
 new=f'    wire [{len(copies)-1}:0] record_copies;\n'+"\n".join(bindings)+'\n    qfd_sys_face_record_port_n32 u_record ('
 core=core.replace(old,new,1).replace('.ck(ck), .rst_rn(rst_rec), .auth_slot(',f'.ck(ck), .rst_leaf(rst_leaf[0+:{len(record["reset_leaves"])}]), .source_copies(record_copies), .auth_slot(',1)
 for prefix,ne,start,rstbase in [('t',64,'t_go',128),('l',32,'l_go',139),('e',16,'ecal_go',146)]:
  aw=ne.bit_length()-1;g=ne//16;nb=(ne+31)//32;nr=3+2*g;ns=6+2*g;nseg=4+g;nsegdata=3*g+1
  pattern=r'    ot_qwen_d2d_cal #\(\.NE\('+str(ne)+r'\)\) u_cal_'+prefix+r' \(.*?\);'
  m=re.search(pattern,core,re.S)
  if not m:raise ValueError('Missing exact original calendar '+prefix)
  original=m.group();outputs=re.search(r'\.ev_v\(.*',original,re.S).group()
  replacement=(f'    qfd_syscal{ne}_n32 u_cal_{prefix} (.ck(ck), .rst_n(rst_leaf[{rstbase}+:{nr}]), '
   f'.cfg_we({prefix}_we), .cfg_addr({{c_addr[7],c_addr[{aw-1}:0]}}), .cfg_data_k({{{nb}{{c_data}}}}), '
   f'.cfg_seg_k({{{nsegdata}{{c_data[{aw-1}:0]}}}}), .start_k({{{ns}{{{start}}}}}), '
   f'.seg_k({nseg}\'d0), .halt_k({{{ns}{{halt}}}}), '+outputs)
  core=core[:m.start()]+replacement+core[m.end():]
 wrapper=wrapper.replace('module qfd_sys_face (','module qfd_sys_face_n32 (',1)
 regs=[f'  (* keep="true", dont_touch="true" *) reg [{len(external)-1}:0] pin_source_copies;']
 for i,row in enumerate(external):regs.append(f'  always @(posedge ck) pin_source_copies[{i}] <= {row["parent_raw_bit"]};')
 old='  qfd_sys_face__ot_pr_core u_ot_pr_core ('
 assert wrapper.count(old)==1
 wrapper=wrapper.replace(old,'\n'.join(regs)+'\n  qfd_sys_face_core_n32 #(.MU(1),.MU_HEAD(1)) u_ot_pr_core (.pin_source_copies(pin_source_copies), ',1)
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 (out/'qfd_sys_face_core_n32.sv').write_text(core)
 (out/'qfd_sys_face_n32.sv').write_text(wrapper)
 manifest=dict(schema='opentallas.sysface32.intermediate.v1',qualification='SOURCE_INTERMEDIATE_ONLY_UNBOUNDED_UNTIL_WEIGHTED_CONSTRUCTION_AND_NATIVE',core_source_sha256=sha(core_path),actual_pin_wrapper_sha256=sha(wrapper_path),record_receipt_sha256=sha(receipt_path),external_same_edge_boundary_copies=external,internal_record_copy_note='execution_active maps to actual calL running; native fanout remains required',added_boot_reset_edges=1,added_token_edges=0)
 (out/'INTERMEDIATE.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--core',required=True);p.add_argument('--wrapper',required=True);p.add_argument('--record',required=True);p.add_argument('--out',required=True);a=p.parse_args();generate(a.core,a.wrapper,a.record,a.out)
