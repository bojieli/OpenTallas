#!/usr/bin/env python3
"""Explicit actual input/output capture wrapper; replaces the automatic layer."""
import hashlib,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]
OUT=R/'rtl/qwen_split'

def main():
 core=(OUT/'qfd_sys_face_ovl_lctx3.sv').read_text();wrapper=(R/'results/arch/codex_sysface_l_2000/pin_wrapper_lctx2.v').read_text()
 rec=json.loads((R/'results/arch/qw_record32_1020/interfaces.json').read_text());head=json.loads((R/'results/arch/codex_sysface_l_2000/headtx32/record.json').read_text())
 external=[];recbind=[]
 def incoming(kind,index,source,bit=None):
  i=len(external);expr=source if bit is None else f'{source}[{bit}]'
  external.append(dict(index=i,component=kind,component_copy=index,raw_source=expr,capture_edge='posedge ck',input_capture_edges=1,reset='none, identical to original input capture'))
  return f'input_source_copies[{i}]'
 for c in rec['input_copies']:
  n,b=c['source'];idx=c['index']
  if n=='execution_active':val='l_run'
  elif n=='program_obs2':val=incoming('record',idx,'tt_program_obs' if b<76 else 'seq_program_obs',b%76)
  else:
   names=dict(auth_slot='prog_auth_slot',context_slot='prog_context_slot',witness_slot='prog_witness_slot',descriptor_obs='seq_descriptor_obs');val=incoming('record',idx,names[n],b if n=='descriptor_obs' else None)
  recbind.append(f'    assign record_copies[{idx}]={val};')
 hp={b:(n,i) for n,p in head['original_ports'].items() for i,b in enumerate(p['bits'])};headbind=[]
 for c in head['input_copies']:
  n,b=hp[c['original_bit']];assert n=='send_slot'
  headbind.append(f'    assign head_copies[{c["index"]}]='+incoming('head',c['index'],'prog_head_context_slot')+';')
 abort=[]
 for i in range(4):abort.append(incoming('calendar_abort',i,'d2d_epoch_abort'))
 core=core.replace('module qfd_sys_face_ovl_lctx3 #(', 'module qfd_sys_face_lctx3_core #(',1)
 needle='    input  wire          rst_n,';assert core.count(needle)==1
 core=core.replace(needle,needle+f'\n    input wire [{len(external)-1}:0] input_source_copies,',1)
 core=core.replace('wire [65:0] rst_forest;', 'wire [159:0] rst_forest;').replace('#(.LEAVES(66))','#(.LEAVES(160))')
 old='    qfd_sys_face_record_port #(.MU_HEAD(MU_HEAD)) u_record (';assert core.count(old)==1
 core=core.replace(old,'    wire[35:0]record_copies;\n'+'\n'.join(recbind)+'\n    qfd_sys_face_record_port_n32 u_record (',1).replace('.ck(ck), .rst_rn(rst_rec)', '.ck(ck), .rst_leaf(rst_forest[66+:54]), .source_copies(record_copies)',1)
 old='    qfd_mu_head_context_tx u_head_tx(';assert core.count(old)==1
 core=core.replace(old,'    wire[5:0]head_copies;\n    wire[22:0]head_tx_pub;\n'+'\n'.join(headbind)+'\n    qfd_mu_head_context_tx_lctx32 u_head_tx(.source_copies(head_copies),.rst_leaf(rst_forest[120+:40]),.tx_v_pub(head_tx_pub),',1)
 core=core.replace('.ck(ck),.rst_n(rst_rec[0]),.descriptor_v(','.ck(ck),.descriptor_v(',1)
 for i,pre in enumerate('tle'):
  pat=r'qfd_syscal_lctx3 #\(\.NE\(\d+\)\) u_cal_'+pre+r' \(.*?\);';m=re.search(pat,core,re.S);assert m
  core=core[:m.start()]+m.group().replace('.halt(halt)',f'.halt({abort[i]})')+core[m.end():]
 m=re.search(r'qfd_d2d_cal_seq_ovl_rope #.*?\);',core,re.S);assert m;core=core[:m.start()]+m.group().replace('.halt(halt)',f'.halt({abort[3]})')+core[m.end():]
 old='    assign prog_tx_record=head_tx_v?head_tx_record:rp_tx_record;';assert old in core
 mux='    // Independent tx_v publications: the same source D/edge, at most24 mux bits each.\n'
 for i in range(23):
  lo=i*24;w=min(24,548-lo);mux+=f'    qfd_sysface_select_local #(.W({w}),.ID({i})) u_txrec_mux{i}(.s(head_tx_pub[{i}]),.a(rp_tx_record[{lo}+:{w}]),.b(head_tx_record[{lo}+:{w}]),.y(prog_tx_record[{lo}+:{w}]));\n'
 core=core.replace(old,mux)
 # Preserve the actual existing capture wrapper, its per-port order and reset relay.
 params=core[core.index('#(')+2:core.index(') (')]
 for production in ['MU','MU_HEAD','ROPE']:
  params=re.sub(r'(parameter integer '+production+r'\s*=\s*)0',r'\g<1>1',params,count=1)
 wrapper=wrapper.replace('module qfd_sys_face_ovl_lctx2 (','module qfd_sys_face_lctx3_wrapped #('+params+') (',1)
 names=['L_CONTEXTS','MUT','OVL_ROM_DIR','MU','GO_OFS','START_ADJ','ROM_VIAMAP','ROM_INSTANCE','ROPE','MU_HEAD']
 forward=','.join('.'+n+'('+n+')' for n in names)
 needle='  qfd_sys_face_ovl_lctx2__ot_pr_core u_ot_pr_core (';assert needle in wrapper
 ff=f'  wire [{len(external)-1}:0] input_source_copies;\n'
 for c in external:
  i=c['index'];ff+=f'  (* keep="true",dont_touch="true" *) reg copy_{i};\n  always @(posedge ck) copy_{i}<={c["raw_source"]};\n  assign input_source_copies[{i}]=copy_{i};\n'
 wrapper=wrapper.replace(needle,ff+f'  qfd_sys_face_lctx3_core #({forward}) u_ot_pr_core (.input_source_copies(input_source_copies), ',1)
 wrapper=wrapper.replace('endmodule','  initial if(MU!=1 || MU_HEAD!=1 || ROPE!=1) $fatal(1,"LCTX3 wrapper requires actual production MU1/MU_HEAD1/ROPE1");\nendmodule',1)
 (OUT/'qfd_sys_face_lctx3_core.sv').write_text(core);(OUT/'qfd_sys_face_lctx3_wrapped.sv').write_text(wrapper)
 ports=[]
 for direction,width,name in re.findall(r'\b(input|output)\b\s*(\[[^]]+\])?\s*(\w+)\s*;',wrapper):
  ports.append(dict(port=name,direction=direction,width=width or '1',capture_edges=0 if name=='ck' else 2 if name=='rst_n' else 1,reset='two synchronous relay registers, then core third-edge release' if name=='rst_n' else 'none on boundary data capture'))
 receipt=dict(scope='actual explicit capture wrapper replaces automatic pin registers, never stacks them',baseline_wrapper_sha256=hashlib.sha256((R/'results/arch/codex_sysface_l_2000/pin_wrapper_lctx2.v').read_bytes()).hexdigest(),external_copy_map=external,per_port_capture=ports,core_reset_release_edges=3,reset_input_relay_edges=2,record_reset_leaves=54,head_reset_leaves=40,txv_publications=23,calendar_data_publications=28,unqualified='Actual mapped native census and image-specific functional/timing qualification remain required; no old view/age transfer')
 (R/'results/arch/codex_sysface_l_2000/wrapper_source_map.json').write_text(json.dumps(receipt,indent=2)+'\n');print('explicit same-edge input copies',len(external),'ports',len(ports))
if __name__=='__main__':main()
