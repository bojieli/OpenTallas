#!/usr/bin/env python3
"""Extract source register cones verbatim; upstream internal pins are bench inputs."""
import pathlib,json,hashlib
O=pathlib.Path(__file__).resolve().parent;S=O.parent/'qw_source_age_1019';rec=[]
def block(file,start,end):
 text=(S/'source'/file).read_text();lines=text.splitlines();out='\n'.join(lines[start-1:end])+'\n';rec.append(dict(snapshot=file,first_line=start,last_line=end,source_sha256=hashlib.sha256(text.encode()).hexdigest(),extract_sha256=hashlib.sha256(out.encode()).hexdigest()));return out
emb=block('115_qfd_sys_face.sv',520,520)
cc=block('050_qfd_dv_slice2.sv',299,303)
hr=block('110_qfd_tt_ctlm_dv.sv',429,434)
ar=block('050_qfd_dv_slice2.sv',342,345)
status=block('115_qfd_sys_face.sv',527,555)
text='''`timescale 1ns/1ps
module original_publish #(parameter KIND=0,W=512)(input ck,rst,input[31:0]pattern,output wire[W-1:0]pin);
 generate if(KIND==0) begin:g_emb
 wire is_hdr=pattern[0];wire[547:0]rx_payload={17{pattern}};reg[511:0]emb_word_data;
'''+emb+''' assign pin=emb_word_data;
 end else if(KIND==1) begin:g_status
 wire rst_st=rst;wire[15:0]host_epoch=pattern[15:0];wire[58:0]host_tag={pattern,pattern[26:0]};wire[1:0]host_generation=pattern[1:0];
 wire[55:0]seq_dc={pattern,pattern[23:0]};wire[31:0]tcyc=pattern;
 wire t_running_q=pattern[0],io_cmd_free=pattern[1],boot_done=pattern[2],rp_program_ready=pattern[3],face_fault=pattern[4],ev_res=pattern[0];
 wire io_fault=pattern[5],io_shared_fault=pattern[6],native_fault=pattern[7],d2d_fault=pattern[8];
 wire t_bad=pattern[9],l_bad=pattern[10],e_bad=pattern[11],lev_clash=pattern[12],t_cf=pattern[13],l_cf=pattern[14],e_cf=pattern[15];
 wire ev_lay=pattern[16],l_run=pattern[17],ev_tok=pattern[18],e_run=pattern[19],t_go=pattern[20],cs_fault=pattern[21];
 wire cal_tok=pattern[22],cal_exp=pattern[23],cal_seg=pattern[24],seg_exp=pattern[25],cal_adm=pattern[26];
 reg[15:0]status_epoch16;reg vm_drained,collective_drained,collective_busy,crom_fault,execution_active,admit_ready,result_v,result_done,result_fault;
 reg[3:0]result_cause;reg[58:0]result_tag;reg[1:0]result_gen;reg[17:0]result_token;reg[31:0]result_value,result_cycles;reg tt_fab,cal_fault;
'''+status+''' assign pin=result_cycles;
 end else if(KIND==2)begin:g_cc
 localparam MUT=0;wire rst=rst;wire c_xc=pattern[0];wire[115:0]cmd_q={{3{pattern}},20'd0};reg[49:0]cc_o;
'''+cc.replace('wire rst=rst;','')+''' assign pin=cc_o[49];
 end else if(KIND==4)begin:g_ar
 wire[1094:0]chu_q={34{pattern}};wire p_ar=pattern[0],p_dd=pattern[1],own_ar=pattern[2],arx_v=pattern[3],own_dd=pattern[4];
 wire[546:0]own_arw={17{pattern}},arx_w=~{17{pattern}};wire[547:0]own_ddw={17{pattern}};reg[1094:0]ch_dn_o;
'''+ar+''' assign pin=ch_dn_o[1059:548];
 end else if(KIND==7)begin:g_hr
 wire rst_n=rst;wire[71:0]xpf={pattern,pattern,pattern[7:0]};reg hv;reg[72:0]hr_lo;
'''+hr+''' assign pin=hr_lo;
 end else begin:g_unknown
 // Explicit synthetic publication control: collective source cone remains UNKNOWN.
 reg[W-1:0]q;always @(posedge ck)q<=pattern;assign pin=q;
 end endgenerate
endmodule
'''
# The cc block uses rst, which is the module's original input; remove a duplicate self declaration.
text=text.replace('localparam MUT=0;wire rst=rst;','localparam MUT=0;')
(O/'original_publish.sv').write_text(text)
(O/'extract_manifest.json').write_text(json.dumps(dict(scope='Verbatim register blocks only; internal predecessor signals are explicit test inputs. Not complete hard-child modules or production calendar proof.',extracts=rec),indent=1)+'\n')
