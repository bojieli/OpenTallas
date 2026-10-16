#!/usr/bin/env python3
"""Compose actual controller/ROM ports, sourcecopies, issuer, capturebanks and E3 VM.
Reduced tree words remain the declared component boundary. Gold is observer-only.
"""
from pathlib import Path
R=Path(__file__).resolve().parents[2]
s=(R/'tools/qwen_b2_join/tb_b2_rom_port.sv').read_text().replace('module tb_b2_rom_port;', 'module tb_b2_rom_e3;\nparameter integer ISSUE_MUT=0;' ).replace('.land_cnt(16\'d0)', '.land_cnt(ld)')
e=(R/'tools/qwen_b2_join/tb_b2_train_e3.sv').read_text();a=e.index('qfd_res_train_half_b2_0');b=e.index('function automatic',a)
join=e[a:b].replace('.rst_n(rst_n)', '.rst_n(rs)')
join=join.replace(' dut(', ' vm(')
decl='''wire start,payload,issuer_fault;wire[3:0]count,nh;wire[31:0]stride;
wire[550:0]rb[0:5];wire[5:0]sf;reg[20:0]svr=0;wire[511:0]svq;wire svq_v;wire[15:0]ld;wire vf;
wire ig,io,itv,itl;wire[17:0]itiles;wire[23:0]its;wire[3:0]isplit;
qfd_b2_train_source src(.ck_head(clk),.ck_tree(clk),.rst_n(rs),.ib(cmd),.tc2(tc[2]),.me_go(ig),.me_tiles(itiles),.me_ts(its),.me_split(isplit),.me_oen(io),.tag_v(itv),.tag_last(itl));
// Literal component phase: raw controller tag->RQ14; independent sourcecopy adds1.
// Issuer TE13 starts on the same observed edge as RQ, consumed by banks next edge.
qfd_res_train_issue_b2 #(.TRAIN_EDGES(13),.MUT(ISSUE_MUT))issuer(.ck(clk),.rst_n(rs),.me_go(ig),.me_tiles(itiles),.me_ts(its),.me_split(isplit),.me_oen(io),.tag_v(itv),.tag_last(itl),.train_start(start),.train_count(count),.capture_stride(stride),.payload_write(payload),.slot_count(nh),.fault(issuer_fault));
'''
s=s.replace('reg[255:0]expected_scale',decl+join+'\nreg[255:0]expected_scale')
s=s.replace('integer amchecks=0;', '''integer amchecks=0;
reg[511:0]gold[0:11112];reg[15:0]goldmask[0:11112];integer pendingrow[0:11112],nread=0,nresponse=0;
integer startcycle=-1,opstride=0,opends=0;reg[550:0]erb;reg[511:0]edata;integer ens,egid,erow,enb,esa,emask;
''')
s=s.replace('cycle=cycle+1;', '''cycle=cycle+1;
 if(start)begin
  if(!rq[0][2212]||firsttag<0||cycle-firsttag!=14)$fatal(1,"actual sourcecopy/issuer start misaligned pc%0d cycle%0d tag%0d",op_pc,cycle,firsttag);
  startcycle=cycle;
 end
 if(startcycle>=0)for(integer h=0;h<6;h=h+1)begin
  erb=0;ens=(op_sp==7)?4:(op_sp==8)?2:(op_sp==10)?3:1;
  for(integer bk=0;bk<8*op_tiles;bk=bk+1)for(integer j=0;j<ens;j=j+1)
  if(cycle==startcycle+2+h*ens+(bk/8)*((8*ens>opstride)?8*ens:opstride)+(bk%8)*ens+j+(op_oen?2:1))begin
   if(op_oen&&(op_sp<=9||h==0))begin
    egid=(op_sp<=9)?h*(1<<(9-op_sp))+j:j;
    erow=op_base+(bk/8)*op_ots*(3072>>op_sp)+(bk%8)*op_ojs+egid*op_ots;
    enb=(bk/8)*(3072>>op_sp)*128+(bk%8)*16;
    esa=op_wcs+enb/16+egid*8;emask=0;edata=0;
    for(integer l=0;l<16;l=l+1)if(enb+egid*128+l<op_nout)begin emask=emask|(1<<l);edata[32*l+:32]={expected_scale[esa][16*l+:16],16'd0};end
    erb={1'b1,1'(h==5&&j==ens-1),1'b0,20'(erow),16'(emask),edata};
   end else if(h==5&&j==ens-1)erb={1'b1,1'b1,1'b1,20'd0,16'd0,512'd0};
  end
  if(rb[h]!==erb)$fatal(1,"actual ROM/E3 exactRB pc%0d h%0d cycle%0d got%h want%h",op_pc,h,cycle,rb[h],erb);
  if(rb[h][550]&&rb[h][549])opends=opends+1;
 end
 if(svq_v)begin
  if(nresponse>=nread)$fatal(1,"unexpected native read response");
  for(integer l=0;l<16;l=l+1)if(goldmask[pendingrow[nresponse]][l]&&svq[32*l+:32]!==gold[pendingrow[nresponse]][32*l+:32])$fatal(1,"actual ROM/E3 readback row%0d lane%0d got%h want%h",pendingrow[nresponse],l,svq[32*l+:32],gold[pendingrow[nresponse]][32*l+:32]);
  nresponse=nresponse+1;
 end''')
s=s.replace('rowchecks=rowchecks+1;if(op_oen)actualwrites=actualwrites+1;', '''rowchecks=rowchecks+1;if(op_oen)begin
     actualwrites=actualwrites+1;if(addr>11112)$fatal(1,"native row capacity exceeded");
     for(integer l=0;l<16;l=l+1)if(mask&(1<<l))begin gold[addr][32*l+:32]={expected_scale[sa][16*l+:16],16'd0};goldmask[addr][l]=1;end
    end''')
s=s.replace('op_oen=output_en;', '''startcycle=-1;opends=0;opstride=spacing;nread=0;nresponse=0;svr=0;
 for(integer r=0;r<11113;r=r+1)goldmask[r]=0;
 op_oen=output_en;''')
s=s.replace('if(amax_en&&', '''if(opends!=8*tiles||ld!=16'(8*tiles)||sf||vf||issuer_fault)$fatal(1,"native ROM/issuer/train/E3 fault pc%0d ends%0d landed%0d sf%b vf%b issuer%b",pc,opends,ld,sf,vf,issuer_fault);
 for(integer r=0;r<11113;r=r+1)if(goldmask[r])begin
  pendingrow[nread]=r;nread=nread+1;svr={1'b1,20'(r)};@(negedge clk);#0.01;
 end
 svr=0;repeat(80)@(negedge clk);#0.01;
 if(nresponse!=nread)$fatal(1,"missing actual E3 readback pc%0d got%0d want%0d",pc,nresponse,nread);
 $display("PASS actualROM_E3 pc%0d writes%0d reads%0d landed%0d exactallRB",pc,actualwrites,nresponse,ld);
 if(amax_en&&''')
s=s.replace('PASS actual native controller→releasedROM→384hardmul port operations', 'PASS actual native controller→releasedROM→384hardmul→source50FF→issuer→sixhalftrain→E3 component')
(R/'tools/qwen_b2_join/tb_b2_rom_e3.sv').write_text(s)
# Exact union, preserving native files from existing E3 runner.
import re
sh=(R/'tools/qwen_b2_join/run_e3_bench.sh').read_text();raw=re.search(r'F="(.*?)"',sh,re.S)[1]
for v,p in {'P':'rtl/qwen_sys/vm_plane_20261013','S':'rtl/qwen_sys/vm_die_split_20261012','N':'rtl/qwen_sys/vm_nox_20261014'}.items():raw=raw.replace('$'+v,p)
files=(R/'tools/qwen_b2_join/rom_port_sources.f').read_text().split()+raw.split()+['rtl/qwen_split/qfd_res_train_issue_b2.sv','tools/qwen_b2_join/tb_b2_rom_e3.sv']
files=[f for f in dict.fromkeys(files)if not f.endswith(('tb_b2_rom_port.sv','tb_b2_train_e3.sv'))]
(R/'tools/qwen_b2_join/rom_e3_sources.f').write_text('\n'.join(files)+'\n')
