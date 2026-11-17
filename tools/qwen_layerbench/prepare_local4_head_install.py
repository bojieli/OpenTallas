#!/usr/bin/env python3
"""Prepare one actual LOCAL4→STM/RP→SUVM→HEAD native install component.

All PROG/CROM writes originate in the genuine full37-stage table masks. Only
finite VM X/RSTD inputs are preloaded. The native CALR stage37 body and one
verbatim GI request register produce the loader request; no full TT/die runs.
"""
from pathlib import Path
import argparse,json,hashlib,shutil,sys,re

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();b=a.root.resolve();o=b/'head_install1116';o.mkdir(exist_ok=False)
 # Sources have been staged from the already qualified 3/1 native capsule.
 source=b/'head_install_sources';shutil.copytree(source/'input',o/'input')
 for name in ['qfd_dv_slice_tload.sv','qfd_dv_table_rom_loader.sv','qfd_dv_s8_rp1.sv','qfd_dv_s8_kept.sv','qfd_dv_calendar_rom.sv','qfd_dv_cmd_cal_mu_head37.sv','ot_ks_add.sv','qkd_program_pw_observer_p.sv','ot_sram_1r1w_64x512_m1_r2c2.v']:
  shutil.copy(source/name,o/'input'/name)
 shutil.copy(source/'qfd_dv_s6_leaves_head37.sv',o/'input/026_qfd_dv_s6_leaves.sv')
 sys.path[:0]=[str(b/'table_lower_tools/tools/qwen_layerbench'),str(b/'table_lower_tools/tools/qwen_tokfunc/current_path')]
 import programme_store as P,table_roms as T
 mapping={f'tb_mu_native.stm.u_tload.u_ld.m{k}':f'table_s0_m{k}.viamap.hex'for k in range(4)}
 (o/'input/rom.sv').write_text(T.namespace(source/'ot_rom_4096x266_m8.v',mapping))
 # Single real LOCAL4 instruction in a native CALR port, component only.
 words=[0]*4096;words[0]=(8<<116)|(14<<112)|(37<<4)|9
 (o/'calendar').mkdir()
 for k in range(2):(o/'calendar'/f'calendar_m{k}.viamap.hex').write_text(''.join(f'{v:0532x}\n'for v in P.physical_rows(words,k)))
 c=o/'input/034_component.sv';s=c.read_text()
 old='output wire [8:0]     treq_o\n'
 assert old in s
 s=s.replace(old,'''output wire [8:0]     treq_o,
    input wire preload_we,input wire[23:0]preload_addr,input wire[511:0]preload_data,
    input wire install_we,input wire[1:0]install_kind,input wire[23:0]install_addr,input wire[1023:0]install_data
''',1)
 s=s.replace('assign su_cmd={cmd_i[0] && cmd_i[3:1]==3\'d1,cmd_i[12:4]};','assign su_cmd={rp_ctl_cmd[0] && rp_ctl_cmd[3:1]==3\'d1,rp_ctl_cmd[12:4]};')
 alias='assign rp_tw_we=tw_we,rp_tw_kind=tw_kind,rp_tw_addr=tw_addr,rp_tw_data=tw_data;'
 assert alias in s
 s=s.replace(alias,'''qfd_dv_s8_rp1 u_rp(.ck(ck),.rst_n(rst_n),.cmd_q(cmd_i),.chd_q(1038'd0),
 .tw_we(install_we),.tw_kind(install_kind),.tw_addr(install_addr),.tw_data(install_data),
 .ctl_cmd(rp_ctl_cmd),.ctl_chd(rp_ctl_chd),.vtw_we(rp_tw_we),.vtw_kind(rp_tw_kind),.vtw_addr(rp_tw_addr),.vtw_data(rp_tw_data),.fault(rp_fault),.w519_cp('0),.w518_cp('0));
 assign w16_we=preload_we,w16_addr=preload_addr,w16_data=preload_data;
 assign w1_we=1'b0,w1_addr=24'd0,w1_data=32'd0;''')
 c.write_text(s)
 tb=(o/'input/tb_mu_native.sv').read_text()
 tb=tb.replace('.treq_i(\'0));',".treq_i('0),.preload_we(wv),.preload_addr(wa),.preload_data(wd),.install_we(stm_tw_we&&!drop_writes),.install_kind(stm_tw_kind),.install_addr(stm_tw_addr),.install_data(stm_tw_data));",1)
 tb=tb.replace(' force dut.w16_we=wv;force dut.w16_addr=wa;force dut.w16_data=wd;','').replace(' force dut.tw_we=tv;force dut.tw_kind=tk;force dut.tw_addr=ta;force dut.tw_data=td;','')
 start=tb.index('qfd_dv_stream_tile stream(');end=tb.index('function automatic[15:0]bf16',start)
 extra='''wire stm_tw_we;wire[1:0]stm_tw_kind;wire[23:0]stm_tw_addr;wire[1023:0]stm_tw_data;
reg drop_writes=0;integer cmd_delay=96,load_active=0,req_edge=-1,cal_edge=-1,first_tw=-1,last_tw=-1,prog_store=-1,first_gain_store=-1,last_gain_store=-1,loader_done=-1,cal_load_edge=-1;
integer tw_count=0,prog_read_edge=-1,first_gain_read=-1;integer gain_store[0:1023];integer prog_stores[0:255];integer z,tmo;
reg cpw=0,cdw=0,cstart=0;reg[9:0]cpaddr=0;reg[2:0]cdaddr=0;reg[63:0]cddata=0;reg[1:0]cuser=0;
wire cload,cload_off,cready,cfault,cfault_off;wire[5:0]cstage;wire[1:0]ctuser;wire[5:0]ccode;reg[8:0]treq=0;
`define CALPORT .ck(ck),.rst_n(rst_n),.pw_v(cpw),.pw_addr(cpaddr),.pw_data(64'd0),.dw_v(cdw),.dw_addr(cdaddr),.dw_data(cddata),.start(cstart),.stage(6'd37),.start_user(cuser),.start_rng(1'b1),.start_first(10'd0),.start_cnt(10'd1)
qfd_dv_cmd_cal_mu_head37 #(.HEAD_STAGE37(1),.NU(4),.CTX_DW(1),.UFOLD(1),.CALENDAR_ROM(1),.TABLE_ROM(1),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.CALREG(7)) cal(`CALPORT,.table_load(cload),.table_stage(cstage),.table_user(ctuser),.image_ready(cready),.fault(cfault),.fault_code(ccode));
qfd_dv_cmd_cal_mu_head37 #(.HEAD_STAGE37(0),.NU(4),.CTX_DW(1),.UFOLD(1),.CALENDAR_ROM(1),.TABLE_ROM(1),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.CALREG(7)) cal_off(`CALPORT,.table_load(cload_off),.fault(cfault_off));
// Verbatim native GI request-face register; external TT→STM transport is zero only in this component.
always @(posedge ck or negedge rst_n)if(!rst_n)treq<=9'd0;else treq<={cload,cstage,ctuser};
qfd_dv_s6_stm #(.HEAD_STAGE37(1),.TSLICE(0)) stm(.ck(ck),.rst_n(rst_n),.sid(4'd0),.stm_cfg({cfg,2'b11,28'h4845414}),
 .sw_i('0),.se_i('0),.so_e(oe),.so_w(ow),.vm_we(dut.L_vm_we),.vm_waddr(dut.L_vm_waddr),.vm_wdata(dut.L_vm_wdata),
 .treq_i(treq),.tw_we(stm_tw_we),.tw_kind(stm_tw_kind),.tw_addr(stm_tw_addr),.tw_data(stm_tw_data),.xt_v(xv),.xt_a(xa),.xt_d(xd),.xt_bad(xbad),.stm_fault(sfault),.tld_fault());
'''
 tb=tb[:start]+extra+tb[end:]
 loopstart=tb.index(' repeat(64)@(negedge ck);rst_n=1;')
 loopend=tb.index('// Observer samples',loopstart)
 newloop=''' drop_writes=$test$plusargs("DROP_TABLE_WRITES");if($value$plusargs("CMD_AFTER_TREQ=%d",cmd_delay))begin end
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 for(j=0;j<1024;j=j+1)begin cpw=1;cpaddr=10'(j);@(negedge ck);end cpw=0;
 for(j=0;j<8;j=j+1)begin cdw=1;cdaddr=3'(j);cddata=(j==0)?64'h43414c5200000001:(j>=1&&j<=4)?64'd1:(j==6)?64'h4d43000000000000:64'd0;@(negedge ck);end cdw=0;
 repeat(128)@(negedge ck);if(!cready||cfault)$fatal(1,"INSTALL_CALR_BOOT ready%0d fault%0d code%0h",cready,cfault,ccode);
 s=0;
 for(u=0;u<4;u=u+1)begin
  cfg=1;@(negedge ck);cfg=0;
  for(j=0;j<nwords[s];j=j+16)begin wv=1;wa=24'(4096*u+j);for(l=0;l<16;l=l+1)wd[32*l+:32]=32'h40000000+32'(u*8388608);@(negedge ck);end
  wa=24'(4096*u+400);wd=0;wd[31:0]=32'h3f000000;@(negedge ck);wv=0;repeat(16)@(negedge ck);
  req_edge=-1;cal_edge=-1;first_tw=-1;last_tw=-1;prog_store=-1;first_gain_store=-1;last_gain_store=-1;loader_done=-1;cal_load_edge=-1;tw_count=0;prog_read_edge=-1;first_gain_read=-1;
  for(z=0;z<1024;z=z+1)gain_store[z]=-1;for(z=0;z<256;z=z+1)prog_stores[z]=-1;
  load_active=1;cuser=2'(u);cstart=1;@(negedge ck);cstart=0;
  tmo=0;while(req_edge<0&&tmo<64)begin @(negedge ck);tmo=tmo+1;end
  if(req_edge<0)$fatal(1,"INSTALL_TREQ_MISSING fault%0d code%h",cfault,ccode);
  while(sample_edge<req_edge+cmd_delay-1)@(negedge ck);
  active=1;seen=0;beatseen=0;count=0;beats=0;origin=cyc+1;
  issue_edge=-1;first_read_edge=-1;first_operand_edge=-1;first_write_edge=-1;last_write_edge=-1;first_bf16_edge=-1;last_bf16_edge=-1;
  cmd=(116'(16+128*u)<<4)|116'd3;@(negedge ck);cmd=0;repeat(256)@(negedge ck);active=0;load_active=0;
  if(count!=384||beats!=6||tw_count!=25||prog_store<0||last_gain_store<0||loader_done<0)$fatal(1,"INSTALL_COVERAGE user%0d words%0d beats%0d tw%0d",u,count,beats,tw_count);
  if(dut.su_fault||dut.vm_fault||sfault||xbad||dut.rp_fault||stm.tld_fault||cfault||!cfault_off||cload_off)$fatal(1,"INSTALL_NATIVE_FAULT");
  $display("INSTALL_DATES user=%0d cal_start=%0d cal_load=%0d treq=%0d first_tw=%0d last_tw=%0d prog_store=%0d first_gain_store=%0d last_gain_store=%0d loader_done=%0d cmd=%0d prog_read=%0d gain_read=%0d operand=%0d first_write=%0d last_write=%0d first_bf16=%0d last_bf16=%0d",u,cal_edge,cal_load_edge,req_edge,first_tw,last_tw,prog_store,first_gain_store,last_gain_store,loader_done,issue_edge,prog_read_edge,first_gain_read,first_operand_edge,first_write_edge,last_write_edge,first_bf16_edge,last_bf16_edge);
 end
 if(total!=1536)$fatal(1,"INSTALL_TOTAL %0d",total);
 $display("NATIVE_LOCAL4_HEAD_INSTALL_PASS users4 words1536 BF16beats24 actualfull37masks actualCALR37 actualTWstorage nofixturePROGorCROMwrites");$finish;
end
always @(posedge ck)if(load_active)begin
 if(cstart&&cal_edge<0)cal_edge=sample_edge;
 if(cload&&cal_load_edge<0)cal_load_edge=sample_edge;
 if(treq[8]&&req_edge<0)begin req_edge=sample_edge;if(treq[7:2]!=37||treq[1:0]!=2'(u))$fatal(1,"INSTALL_WRONG_TREQ");end
 if(stm_tw_we)begin if(first_tw<0)first_tw=sample_edge;last_tw=sample_edge;tw_count=tw_count+1;end
 if(stm.u_tload.done)loader_done=sample_edge;
 if(dut.u_suvm.u_vm8q.u_pg.g_prog[0].lo_we)begin prog_store=sample_edge;prog_stores[dut.u_suvm.u_vm8q.u_pg.g_prog[0].lo_wa]=sample_edge;end
 if(dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_we)begin if(first_gain_store<0)first_gain_store=sample_edge;last_gain_store=sample_edge;gain_store[dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_wa]=sample_edge;end
 if(active&&dut.u_suvm.u_vm8q.u_pg.g_prog[0].lo_rce)begin
  if(prog_read_edge<0)prog_read_edge=sample_edge;
  if(prog_stores[dut.u_suvm.u_vm8q.u_pg.g_prog[0].lo_ra]<0||sample_edge<=prog_stores[dut.u_suvm.u_vm8q.u_pg.g_prog[0].lo_ra])$fatal(1,"HEAD_PROG_BEFORE_INSTALL");
 end
 if(active&&dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_rce)begin
  if(first_gain_read<0)first_gain_read=sample_edge;
  if(gain_store[dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_ra]<0||sample_edge<=gain_store[dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_ra])$fatal(1,"HEAD_CROM_BEFORE_INSTALL row%0d read%0d store%0d",dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_ra,sample_edge,gain_store[dut.u_suvm.u_vm8q.u_cl.g_crb[0].m_ra]);
 end
end
'''
 tb=tb[:loopstart]+newloop+tb[loopend:]
 if 'force dut' in tb:raise ValueError('fixture still forces native storage inputs')
 (o/'input/tb_mu_native.sv').write_text(tb)
 f=(source/'source.f').read_text().splitlines()
 for name in ['qfd_dv_slice_tload.sv','qfd_dv_table_rom_loader.sv','qfd_dv_s8_rp1.sv','qfd_dv_s8_kept.sv','qfd_dv_calendar_rom.sv','qfd_dv_cmd_cal_mu_head37.sv','ot_ks_add.sv','qkd_program_pw_observer_p.sv','ot_sram_1r1w_64x512_m1_r2c2.v','rom.sv']:f.append('input/'+name)
 (o/'source.f').write_text('\n'.join(f)+'\n')
 (o/'run.sh').write_text('''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
/usr/bin/time -v -o build.time "$V" --binary --timing -j 1 -O0 -finline --output-groups 64 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-WIDTH --x-assign 0 --x-initial 0 -CFLAGS '-O0 -w -fno-var-tracking' --top-module tb_mu_native -f source.f --Mdir obj > build.log 2>&1
/usr/bin/time -v -o run.time ./obj/Vtb_mu_native +OT_ROM_DIR=calendar +OT_QC_TABLE_ROM_DIR=../tables_candidate1116/rank0/masks > run.log 2>&1
cat run.log
grep -q NATIVE_LOCAL4_HEAD_INSTALL_PASS run.log
''')
 meta=dict(scope='actual rank0/full37masks,one native slice, fourusers; zeroexternalphysicaltransport component only',memory_profile=dict(MIF=1,MEMORY_ALIGNMENT=3,MEMORY_READ_EXTRA=1),
 native_TW_path='native CTLM37→verbatimGIrequestreg→actualSTMforwarder/TLOAD→actualRPpass→actualSUVMprogramme/CROM macros→nativeHEAD→actualSTM BF16stream',
 direct_fixture_PROG_CROM_writes=False,VM_X_RSTD_preload_only=True,global_TT_parent_selected=False)
 (o/'preparation.json').write_text(json.dumps(meta,indent=2)+'\n');print(o)
if __name__=='__main__':main()
