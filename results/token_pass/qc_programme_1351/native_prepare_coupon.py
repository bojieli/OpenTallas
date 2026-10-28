from pathlib import Path
import sys,json,hashlib
root,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
p=root/'rtl/qwen_split/qfd_native59_svc_obs1.sv';s=p.read_text()
def cut(a,b):return s[s.index(a):s.index(b,s.index(a))]
body=cut(' reg[1:0]hp_v;',' // ---------------------------------------------------------------- command context')
body+=' reg[13:0]fseq[0:3];reg[3:0]fstart;reg mu_fault;\n'
body+=cut(' wire hp_fill=',' wire[1:0]c_tag=')
body+=cut(' integer fu;',' generate if(MU==0)begin:g_ctx1')
body+=cut(' always @(posedge ck or negedge rst_top)\n  if(!rst_top)begin head_descriptor_v<=0;',' // ---------------------------------------------------------------- dd word decode')
header='''`timescale 1ns/1ps
module dut(input ck,rst_top,head_prepare_v,input[1:0]head_prepare_user,input[17:0]head_prepare_token,head_prepare_position,
 input p_hev,p_hfc,input[15:0]p_he,input[58:0]p_ht,input[1:0]p_hg,
 output reg head_descriptor_v,output reg[58:0]head_descriptor_tag,output reg[1:0]head_descriptor_generation);
 localparam integer HEAD_PREP=1,MU=1,NU=4,MU_SEQ0=0;
 wire native_context=0,c_l0=0,begin_slot=0;wire[1:0]c_user_w=0,c_user=0;wire[13:0]c_seq=0;wire[58:0]begin_tag=0;
'''
for m in range(3):
 b=body
 if m==1:b=b.replace('hp_host_pending&&p_hev','1\'b1&&p_hev')
 if m==2:b=b.replace('p_ht[36:19]==hp_host_token','1\'b1')
 (out/f'dut_m{m}.sv').write_text(header+b+'\nendmodule\n')
(out/'extraction.json').write_text(json.dumps(dict(source=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Actual input pipeline, pending/cohort join, filler sequence and descriptor blocks. Other native command-context input stays inactive; HOST p_* inputs are already core-published, not external HOST pins.',mutants=['nominal exact blocks','pending-authority bypass','token-identity bypass']),indent=2)+'\n')
