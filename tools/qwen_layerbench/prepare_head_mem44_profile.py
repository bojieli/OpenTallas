#!/usr/bin/env python3
"""Prepare ONE current private HEAD with actual native SUVM and coherent read43.

The seven packer companions are explicitly software-golden input producers.
No other HEAD arithmetic instance, global calendar, physical source selection or
load-overlap window is qualified by this component.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,sys,importlib.util

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def field(w,lo,n):return (w>>lo)&((1<<n)-1)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ('source','stage','golden','out'):ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);d=a.out/'input';d.mkdir();common=a.source/'results/token_pass/qwen_head_memory_loop_1116/source_packet/common'
 for p in sorted((common/'src').glob('*/*')):
  q=d/('src_'+p.parent.name+'_'+p.name);shutil.copy(p,q)
 for name in ['ot_sram_1r1w_1024x256_m2_r2c2.v','ot_sram_1r1w_32x64_m1.v']:shutil.copy(common/name,d/name)
 head=a.source/'results/token_pass/qwen_head_memory_loop_1116/source_packet/E0/qfd_dv_lane_h_su_mem9.sv'
 if digest(head)!='6aadb6ea7e868120c514e5cb447ed3616d82b66d7e3f2f52421afeaf2e922c94':raise ValueError('actual44868 private head source differs')
 shutil.copy(head,d/head.name);shutil.copy(a.source/'qfd_dv_stream_tile.sv',d/'qfd_dv_stream_tile.sv');shutil.copy(a.source/'qfd_dv_s5_su8.sv',d/'qfd_dv_s5_su8.sv')
 c=(a.source/'component_mif31.sv').read_text();first=c.index('    // ---- lane 1:');last=c.index(' assign su_cmd=',first);c=c[:first]+c[last:]
 needle='    output wire [8:0]     treq_o\n';assert needle in c
 c=c.replace(needle,'''    output wire [8:0]     treq_o,
    input wire preload16_we,input wire[23:0]preload16_addr,input wire[511:0]preload16_data,
    input wire preload1_we,input wire[23:0]preload1_addr,input wire[31:0]preload1_data,
    input wire install_we,input wire[1:0]install_kind,input wire[23:0]install_addr,input wire[1023:0]install_data,
    input wire[2:0]logical_head,input wire bad_reply
''')
 c=c.replace('parameter integer PROBE_MIF=0, PROBE_BAD_REPLY=0','parameter integer PROBE_MIF=1, PROBE_BAD_REPLY=0')
 old='qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(S8_MEMORY_ALIGNMENT), .MEMORY_READ_EXTRA(PROBE_BAD_REPLY ? 0 : S8_SRAM_MIF))';assert c.count(old)==1
 c=c.replace(old,'qfd_dv_lane_h_su_mem9 #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(44),.SEGMENTED_MEMORY_DELAY(1),.KV_WR_PIPE(1))')
 c=c.replace('.lv1(lv1[0]), .pd1(pd1[95:0])','.lv1(lv1[logical_head]), .pd1(pd1[96*logical_head+:96])')
 # Keep only one physical lane. Its logical lane projection changes input addresses,
 # never the private HEAD implementation or native memory bank selection.
 ties='\n'
 for n in ['va_re','vb_re','vc_re','crom_re','wrom_re','vm_we','kv_we','l_ov','l_last','retire','l_fault','l_redsq']:ties+=f'assign L_{n}[7:1]=0;\n'
 for n in ['va_addr','vb_addr','vc_addr','crom_addr','wrom_addr','vm_waddr','kv_waddr','l_raddr']:ties+=f'assign L_{n}[191:24]=0;\n'
 for n in ['vm_wdata','kv_wdata','l_out']:ties+=f'assign L_{n}[255:32]=0;\n'
 ties+='assign L_l_red[15:2]=0;\n'
 c=c.replace(' assign rp_tw_we=tw_we,rp_tw_kind=tw_kind,rp_tw_addr=tw_addr,rp_tw_data=tw_data;', ''' assign rp_tw_we=install_we,rp_tw_kind=install_kind,rp_tw_addr=install_addr,rp_tw_data=install_data;
 assign w16_we=preload16_we,w16_addr=preload16_addr,w16_data=preload16_data;
 assign w1_we=preload1_we,w1_addr=preload1_addr,w1_data=preload1_data;''')
 # Explicit actual E0/head0 transport endpoints: request22, reply21.
 # Native MIF1 and CROM alignment are already in the actual modules, not added here.
 transport='''
wire[7:0]M_va_re,M_vb_re,M_vc_re,M_cr_re;
wire[191:0]M_va_addr,M_vb_addr,M_vc_addr,M_cr_addr;
wire[255:0]M_va_q,M_vb_q,M_vc_q;wire[511:0]M_cr_q;
reg[799:0]request_pipe[0:21];reg[1279:0]reply_pipe[0:20];
always @(posedge ck)begin
 request_pipe[0]<={L_crom_re,L_crom_addr,L_vc_re,L_vc_addr,L_vb_re,L_vb_addr,L_va_re,L_va_addr};
 for(integer z=1;z<22;z=z+1)request_pipe[z]<=request_pipe[z-1];
 reply_pipe[0]<={M_cr_q,M_vc_q,M_vb_q,M_va_q};
 for(integer z=1;z<21;z=z+1)reply_pipe[z]<=reply_pipe[z-1];
end
assign {M_cr_re,M_cr_addr,M_vc_re,M_vc_addr,M_vb_re,M_vb_addr,M_va_re,M_va_addr}=request_pipe[21];
assign {cr_q,vc_q,vb_q,va_q}=reply_pipe[bad_reply?19:20];
'''
 start=c.index('    qfd_dv_s8_suvm_rp1 ');end=c.index('    // ---- lane 0:',start);inst=c[start:end]
 for pin,old,new in [('va_re','L_va_re','M_va_re'),('vb_re','L_vb_re','M_vb_re'),('vc_re','L_vc_re','M_vc_re'),('cr_re','L_crom_re','M_cr_re'),('va_addr','L_va_addr','M_va_addr'),('vb_addr','L_vb_addr','M_vb_addr'),('vc_addr','L_vc_addr','M_vc_addr'),('cr_addr','L_crom_addr','M_cr_addr'),('va_q','va_q','M_va_q'),('vb_q','vb_q','M_vb_q'),('vc_q','vc_q','M_vc_q'),('cr_q','cr_q','M_cr_q')]:
  assert inst.count('.'+pin+'('+old+')')==1;inst=inst.replace('.'+pin+'('+old+')','.'+pin+'('+new+')')
 c=c[:start]+transport+inst+c[end:];c=c.replace('endmodule',ties+'endmodule',1);(d/'component.sv').write_text(c)
 stage=json.loads(a.stage.read_text());cases=[];si={}
 for s in stage['slices']:
  w=int(s['prog_users'][0][0]['payload_hex'],16)&((1<<457)-1);si[s['slice']]=field(w,1,18)*field(w,19,18)
 chosen=[next(k for k,n in si.items()if n==384),next(k for k,n in si.items()if n==256)]
 init=[];progs=[];gains=[];expected=[]
 for sid in chosen:
  s=next(s for s in stage['slices']if s['slice']==sid)
  vals=[]
  for row in s['crom']:
   z=int(row['payload_hex'],16);vals.extend(field(z,64*i,32)for i in range(16))
  for user in range(4):
   for logical in [0,7]:
    k=len(cases);pr=int(s['prog_users'][user][0]['payload_hex'],16);w=pr&((1<<457)-1);n=si[sid]
    cases.append({'id':k,'slice':sid,'user':user,'logical_head':logical,'FP32_words_in_cohort':n,'actual_private_HEAD_words':n//8,'pidx':16+128*user,'dso':field(w,294,24),'nin':field(w,19,18),'xbase':field(w,38,24),'rstd':field(w,111,24),'gainbase':field(w,184,24),'dbase':field(w,270,24),'kind':'GENUINE_HEAD37'})
    for key,value in [('csid',sid),('cuser',user),('chead',logical),('cn',n),('cdso',field(w,294,24)),('cxbase',field(w,38,24)),('crstd',field(w,111,24)),('cpidx',16+128*user),('cdbase',field(w,270,24))]:init.append(f'{key}[{k}]={value};')
    progs.append(f'{pr:0256x}')
    for j in range(24):gains.append(f'{int(s["crom"][j]["payload_hex"],16)if j<len(s["crom"])else 0:0256x}')
    for j in range(384):
     if j<n:
      v=vals[j];delta=(j*3+user)%5-3;exp=field(v,23,8)+delta;assert 0<exp<255;v=(v&0x807fffff)|(exp<<23)
     else:v=0
     expected.append(f'{v:08x}')
 (a.out/'prog.hex').write_text('\n'.join(progs)+'\n');(a.out/'gains.hex').write_text('\n'.join(gains)+'\n');(a.out/'expected.hex').write_text('\n'.join(expected)+'\n')
 spec=importlib.util.spec_from_file_location('native_gold',a.golden);G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
 import numpy as np
 f2=np.float32(2);sig=G.reciprocal(G.add(np.float32(1),G.exp(np.float32(-2))));silu=int(G.bits(G.mul(f2,sig)));rsq=int(G.bits(G.rsqrt(f2)))
 # Source constants/order are the actual three-step Newton and Cody-Waite/Horner
 # specification; the arithmetic outputs are checked independently of old ages.
 assert '5f3759df' in (d/'src_8_ot_hdc_sfu_q.sv').read_text().lower()
 hexsingle=[int(v,16)for v in (a.source/'single.hex').read_text().split()];hexsilu=[int(v,16)for v in (a.source/'silu_sigm.hex').read_text().split()]
 mask=(1<<457)-1;copyword=hexsingle[0]&mask;siluw=(hexsilu[0]>>512)&mask;rsqw=(hexsingle[1]>>512)&mask
 rsqvec=(rsqw&~(((1<<18)-1)<<19))|(128<<19)
 (a.out/'sfu_program.hex').write_text(f'{copyword|(siluw<<512):0256x}\n{rsqvec|(rsqw<<512):0256x}\n')
 sg=[]
 for operation in range(4):
  for i in range(128):
   x=np.float32([2,4,8][i%3]);y=x if operation==0 else G.mul(G.mul(G.reciprocal(G.add(np.float32(1),G.exp(G.neg(x)))),x),np.float32([2,4,8][(i+128)%3]))if operation==1 else G.rsqrt(x)
   sg.append(f'{int(G.bits(y)):08x}')
 (a.out/'sfu_expected.hex').write_text('\n'.join(sg)+'\n')
 tb=TB.replace('@NCASE@',str(len(cases))).replace('@INIT@','\n'.join(init)).replace('@SILU@',f'{silu:08x}').replace('@RSQ@',f'{rsq:08x}')
 (d/'tb.sv').write_text(tb);(a.out/'source.f').write_text(''.join('input/'+p.name+'\n'for p in sorted(d.iterdir())))
 (a.out/'run.sh').write_text(RUN)
 rec={'schema':'opentallas.qc.native-mem44-one-head-profile-prep.v1','status':'SOURCE_READY_NOT_LAUNCHED','head_source_commit':'44868df838a11577adfe2bf02b7df99313ed11c6','head_sha256':digest(head),'profile':{'MIF':1,'MEMORY_ALIGNMENT':3,'MEMORY_READ_EXTRA':44,'SEGMENTED_MEMORY_DELAY':1,'KV_WR_PIPE':1},'external_read_packet':{'request':22,'reply':21,'VM_CROM_source':'actual N43emit5 E0/head0 endpoint census','WROM':'not exercised by these programmes'},'extra_retire_transport':0,'global_physical_control_profile':'OPEN','actual_HEAD_instances':1,'native_SFU_instances':3,'genuine_stage_sha256':digest(a.stage),'golden_library_sha256':digest(a.golden),'cases':cases,'SFU':{'plain_SILU2_model_check':f'{silu:08x}','selected_SILU_opcode':'MC=1 MD=1: mul(mul(sigmoid(A),C),B), C=A, B=VM[i+128]; both FP32 rounding points retained','RSQ2_check':f'{rsq:08x}','inputs':'repeated finite2/4/8 per element; independent per-word oracle','operations':['COPY128','SILU128','RSQ128 shape-only expansion','actual RSQ1'],'oracle':'tools/hdc_golden.py FP32 three-step reciprocal/RSQ and exp Cody-Waite polynomial; no historical latency reused'},'packer_companions':'7 software-golden cohort inputs at the actual private HEAD output edges; only1 HEAD arithmetic RTL','table_publication':'native actual TW/CROM store; external STM/RP table transport not installed; load-overlap window remainsOPEN','finite_completion_budget':512,'budget_basis':'prior nativeSILU last203+read43+128 tail+16control <512; functional finite-flow deadline, no build walltime cap','direct_memory_forces':False,'files':{}}
 for p in sorted(a.out.rglob('*')):
  if p.is_file():rec['files'][str(p.relative_to(a.out))]=digest(p)
 (a.out/'preparation.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps({k:rec[k]for k in ['status','actual_HEAD_instances','native_SFU_instances','profile','external_read_packet','SFU']}))

RUN='''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o build.time "$V" --binary --timing -j 1 -O0 -finline --output-groups 64 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' --top-module tb -f source.f --Mdir obj > build.log 2>&1
/usr/bin/time -v -o run.time ./obj/Vtb > run.log 2>&1
grep -q MEM44_ONE_HEAD_PROFILE_PASS run.log
set +e
./obj/Vtb +BAD_REPLY > bad_reply.log 2>&1
rc=$?
set -e
[ "$rc" != 0 ] && grep -Eq 'HEAD_PAYLOAD|PACK_PAYLOAD|HEAD_COUNT|NATIVE_FAULT' bad_reply.log
echo MEM44_REPLY_CONTROL_CAUGHT
'''

TB=r'''`timescale 1ns/1fs
module tb;
localparam integer NCASE=@NCASE@;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[115:0]cmd=0;reg w16=0,w1=0,tw=0;reg[23:0]w16a=0,w1a=0,twa=0;
reg[511:0]w16d=0;reg[31:0]w1d=0;reg[1023:0]twd=0;reg[1:0]twk=0;reg[2:0]logical_head=0;reg bad_reply=0;
integer csid[0:NCASE-1],cuser[0:NCASE-1],chead[0:NCASE-1],cn[0:NCASE-1],cdso[0:NCASE-1],cxbase[0:NCASE-1],crstd[0:NCASE-1],cpidx[0:NCASE-1],cdbase[0:NCASE-1];
reg[1023:0]progs[0:NCASE-1],gainrows[0:NCASE*24-1],sfu_program[0:1];reg[31:0]gold[0:NCASE*384-1],sfu_gold[0:511];
integer cid=0,user_id=0,sid=0,n=0,dso=0,active=0,mode=0,op=0,cy=0,issue=-1,origin=0;
integer count=0,beats=0,retires=0,first_req=-1,first_bound=-1,first_gain_read=-1,first_operand=-1,first_pin_write=-1,last_pin_write=-1,first_write=-1,last_write=-1,first_retire=-1,last_retire=-1,first_BF16=-1,last_BF16=-1,first_ready=-1,first_gain_store=-1,last_gain_store=-1,programme_store=-1,first_emit=-1;
integer rowidx,colidx,outidx,j,k,t,err=0,total=0,totalbeats=0,expected_count=0;reg[383:0]seen;reg[63:0]beatseen;
integer sfu_outidx;
native_su_component #(.PROBE_MIF(1)) dut(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0),
 .preload16_we(w16),.preload16_addr(w16a),.preload16_data(w16d),.preload1_we(w1),.preload1_addr(w1a),.preload1_data(w1d),.install_we(tw),.install_kind(twk),.install_addr(twa),.install_data(twd),.logical_head(logical_head),.bad_reply(bad_reply));
// Complete production pack cohort: one actual private HEAD result and seven
// explicitly software-golden companion producers. No companion HEAD arithmetic.
reg[191:0]pack_addr;reg[255:0]pack_data;wire[7:0]pack_we=(active&&mode==0&&dut.L_vm_we[0])?8'hff:8'd0;
integer pp,pa,rr,cc,gi;
always @*begin
 pack_addr=0;pack_data=0;
 pa=(dut.L_vm_waddr[23:0]&24'h3fffff)-logical_head;
 rr=(mode==0&&cid<NCASE&&dso>0)?(pa-(cdbase[cid]&24'h3fffff))/dso:0;cc=(mode==0&&cid<NCASE&&dso>0)?(pa-(cdbase[cid]&24'h3fffff))%dso:0;
 for(integer p=0;p<8;p=p+1)begin
  pack_addr[24*p+:24]=24'(pa+p);
  gi=rr*128+cc+p;
  if(mode==0&&cid<NCASE&&gi>=0&&gi<384)pack_data[32*p+:32]=gold[cid*384+gi];
  if(p==logical_head)pack_data[32*p+:32]=dut.L_vm_wdata[31:0];
 end
end
wire srst; qfd_dv_s5_rst2 u_sr(.ck(ck),.rst_n(rst_n),.rst(srst));
reg cfg=0;wire[1087:0]oe,ow;wire xv,xbad,sfault;wire[23:0]xa;wire[1023:0]xd;
qfd_dv_stream_tile stream(.ck(ck),.rst_n(srst),.sid(4'(sid)),.cfg_v(cfg),.cfg_dir(2'b11),.cfg_tag(28'h4845414),
 .sw_lo('0),.sw_v(1'b0),.sw_hi('0),.se_lo('0),.se_v(1'b0),.se_hi('0),.so_e(oe),.so_w(ow),
 .xw_we(pack_we),.xw_addr(pack_addr),.xw_data(pack_data),.tw_we(),.tw_kind(),.tw_addr(),.tw_data_lo(),.tw_data_hi(),.xt_v(xv),.xt_a(xa),.xt_d_lo(xd[511:0]),.xt_d_hi(xd[1023:512]),.xt_bad(xbad),.fault(sfault));
function automatic[15:0]bf16(input[31:0]v);reg[32:0]r;begin r={1'b0,v}+33'h7fff+{32'd0,v[16]};bf16=r[31:16];end endfunction
function automatic[31:0]xvalue(input integer i,input integer u);integer e;begin e=127+(i*3+u)%5-2;xvalue=32'(e<<23);end endfunction
always @(posedge ck)begin
 cy=cy+1;
 if(active)begin
  if(cmd[0]&&issue<0)issue=cy;
  if(dut.c0_emit0&&first_emit<0)first_emit=cy;
  if(dut.L_va_re[0]&&first_req<0)first_req=cy;
  if(dut.M_va_re[0]&&first_bound<0)first_bound=cy;
  if(dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_rce&&first_gain_read<0)first_gain_read=cy;
  if(dut.u_head0.u_h.u_lane.s1_v&&first_operand<0)first_operand=cy;
  if(dut.h0_vm_we)begin if(first_pin_write<0)first_pin_write=cy;last_pin_write=cy;end
  if(dut.h0_retire)begin if(first_retire<0)first_retire=cy;last_retire=cy;retires=retires+1;end
  if(dut.u_suvm.u_su8.ready&&dut.u_suvm.u_su8.inflight==0&&count>0&&first_ready<0)first_ready=cy;
  if(dut.L_vm_we[0])begin
   if(first_write<0)first_write=cy;last_write=cy;
   if(mode==0)begin
    outidx=(dut.L_vm_waddr[23:0]&24'h3fffff)-(cdbase[cid]&24'h3fffff);rowidx=outidx/dso;colidx=outidx%dso;outidx=rowidx*128+colidx;
    if(outidx<0||outidx>=n||seen[outidx]||dut.L_vm_wdata[31:0]!==gold[cid*384+outidx])$fatal(1,"HEAD_PAYLOAD case%0d logical%0d idx%0d got%08x expected%08x",cid,logical_head,outidx,dut.L_vm_wdata[31:0],gold[cid*384+outidx]);
    seen[outidx]=1;
   end else begin
    sfu_outidx=dut.L_vm_waddr[23:0]-((op==0)?1024:(op==1)?1280:1536);
    if(sfu_outidx<0||sfu_outidx>=128||dut.L_vm_wdata[31:0]!==sfu_gold[op*128+sfu_outidx])$fatal(1,"SFU_PAYLOAD op%0d idx%0d got%08x expected%08x",op,sfu_outidx,dut.L_vm_wdata[31:0],sfu_gold[op*128+sfu_outidx]);
   end
   count=count+1;
  end
  if(mode==0&&oe[1087])begin
   outidx=oe[1075:1052]-(cdbase[cid]&24'h3fffff);rowidx=outidx/dso;colidx=outidx%dso;outidx=rowidx*128+colidx;
   if(outidx<0||outidx+63>=n||beatseen[outidx/64])$fatal(1,"PACK_ADDRESS");
   for(integer bi=0;bi<64;bi=bi+1)if(oe[16*bi+:16]!==bf16(gold[cid*384+outidx+bi]))$fatal(1,"PACK_PAYLOAD case%0d idx%0d",cid,outidx+bi);
   beatseen[outidx/64]=1;beats=beats+1;if(first_BF16<0)first_BF16=cy;last_BF16=cy;
  end
 end
 if(rst_n&&dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_we&&mode==0)begin
  if(dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_wa==10'(68+128*user_id)&&first_gain_store<0)first_gain_store=cy;
  if(dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_wa==10'(68+128*user_id+n/16-1))last_gain_store=cy;
 end
 if(rst_n&&dut.u_suvm.u_vm8q.u_pg.g_prog[0].lo_we)programme_store=cy;
end

task automatic clear_dates;
 begin count=0;beats=0;retires=0;issue=-1;first_emit=-1;first_req=-1;first_bound=-1;first_gain_read=-1;first_operand=-1;first_pin_write=-1;last_pin_write=-1;first_write=-1;last_write=-1;first_retire=-1;last_retire=-1;first_BF16=-1;last_BF16=-1;first_ready=-1;seen=0;beatseen=0;end
endtask
task automatic report_dates;
 begin
 $display("PROFILE_DATES mode=%0d case=%0d op=%0d logical=%0d cmd=%0d emit=%0d req=%0d vm_bound=%0d gain_read=%0d operand_visible=%0d head_write=%0d head_lastwrite=%0d LRLYwrite=%0d LRLYlastwrite=%0d head_retire=%0d head_lastretire=%0d SU8ready=%0d BF16=%0d lastBF16=%0d programme_store=%0d first_gain_store=%0d last_gain_store=%0d count=%0d retires=%0d beats=%0d",mode,cid,op,logical_head,issue,first_emit,first_req,first_bound,first_gain_read,first_operand,first_pin_write,last_pin_write,first_write,last_write,first_retire,last_retire,first_ready,first_BF16,last_BF16,programme_store,first_gain_store,last_gain_store,count,retires,beats);
 end
endtask
initial begin
 @INIT@
 bad_reply=$test$plusargs("BAD_REPLY");
 $readmemh("prog.hex",progs);$readmemh("gains.hex",gainrows);$readmemh("expected.hex",gold);$readmemh("sfu_program.hex",sfu_program);$readmemh("sfu_expected.hex",sfu_gold);
 for(cid=0;cid<NCASE;cid=cid+1)begin
  mode=0;active=0;cfg=0;cmd=0;w16=0;w1=0;tw=0;rst_n=0;repeat(64)@(negedge ck);
  user_id=cuser[cid];sid=csid[cid];logical_head=3'(chead[cid]);n=cn[cid];dso=cdso[cid];first_gain_store=-1;last_gain_store=-1;programme_store=-1;
  rst_n=1;repeat(512)@(negedge ck);
  for(j=0;j<n;j=j+16)begin w16=1;w16a=24'(cxbase[cid]+j);for(k=0;k<16;k=k+1)w16d[32*k+:32]=xvalue(j+k,user_id);@(negedge ck);end
  w16=0;w1=1;w1a=24'(crstd[cid]);w1d=32'h3f000000;@(negedge ck);w1=0;
  tw=1;twk=3;twa=24'(cpidx[cid]/2);twd=progs[cid];@(negedge ck);
  for(j=0;j<n/16;j=j+1)begin twk=1;twa=24'(68+128*user_id+j);twd=gainrows[cid*24+j];@(negedge ck);end
  tw=0;repeat(128)@(negedge ck);cfg=1;@(negedge ck);cfg=0;repeat(16)@(negedge ck);
  clear_dates();active=1;cmd=(116'(cpidx[cid])<<4)|116'd3;@(negedge ck);cmd=0;
  repeat(512)@(negedge ck);report_dates();
  if(count!=n/8||retires!=n/8||beats!=n/64||first_gain_store<0||last_gain_store<0||first_gain_read<=first_gain_store)$fatal(1,"HEAD_COUNT case%0d got%0d/%0d/%0d",cid,count,retires,beats);
  if(dut.su_fault||dut.vm_fault||sfault||xbad)$fatal(1,"NATIVE_FAULT head case%0d su%0b vm%0b pack%0b",cid,dut.su_fault,dut.vm_fault,sfault);
  total=total+count;totalbeats=totalbeats+beats;active=0;
 end
 // Real SFUs and minimal native class changes, one physical head. The controller
 // independently observes its actual inflight/ready state; no fixed busy charge.
 mode=1;active=0;rst_n=0;cmd=0;cfg=0;logical_head=0;repeat(64)@(negedge ck);rst_n=1;repeat(512)@(negedge ck);
 for(j=0;j<384;j=j+16)begin w16=1;w16a=j;for(k=0;k<16;k=k+1)w16d[32*k+:32]=((j+k)%3==0)?32'h40000000:((j+k)%3==1)?32'h40800000:32'h41000000;@(negedge ck);end
 w16=0;tw=1;twk=3;twa=0;twd=sfu_program[0];@(negedge ck);twa=1;twd=sfu_program[1];@(negedge ck);tw=0;repeat(128)@(negedge ck);
 for(op=0;op<4;op=op+1)begin
  clear_dates();active=1;cmd=(116'(op)<<4)|116'd3;@(negedge ck);cmd=0;
  expected_count=(op==3)?1:16;
  for(t=0;t<512;t=t+1)begin
   @(negedge ck);
   if(count==expected_count&&retires==expected_count&&dut.su_idle&&dut.u_suvm.u_su8.ready&&dut.u_suvm.u_su8.inflight==0)break;
  end
  report_dates();
  if(count!=expected_count||retires!=expected_count||dut.su_fault||dut.vm_fault)$fatal(1,"SFU_COUNT op%0d count%0d retire%0d fault%0b/%0b",op,count,retires,dut.su_fault,dut.vm_fault);
  active=0;@(negedge ck);
 end
 $display("MEM44_ONE_HEAD_PROFILE_PASS genuine_cases%0d actual_FP32words%0d fullcohort_BF16beats%0d independent_SILU_RSQ_PASS companions7golden extra_retire_transport0",NCASE,total,totalbeats);$finish;
end
endmodule
'''
if __name__=='__main__':main()
