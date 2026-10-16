`timescale 1ps/1fs
// H-DIE 2026-10-15: the die composition of one stack's HBM service, issued by HARDWARE: 8 ot_hbm_svc_sm_group (issuer +
// feed) + ot_hbm_svc_native_sector_pipeline_leaves (32 real controller leaves) + the DRAM fixture at the PHY row/column
// boundary.  The testbench only initializes (programme + descriptor tables) and pulses one run launch per SM; every
// reserve / start / go is issued by ot_hbm_svc_sm_issuer.  Same images, programme words and checks as
// tb_hbm_svc_sm_stack_steady (every packet and S1 consumer line exact, sector counts), steady epoch measured.
// +EARLY: programme mutant of the steady bench (consumer before its row) -> DUT fault.
module tb_hbm_svc_sm_groups_issued;
 parameter integer STACK=0;
 parameter integer ROWS=64;
 parameter integer EPOCHS=8;
 parameter integer LBANKS=4;
 localparam integer SECT=((ROWS*136+127)/128)*4;
 reg stream=0,hbm=0;initial forever begin #416.666 stream=1;#416.667 stream=0;end
 initial begin #173;forever #512 hbm=~hbm;end
 reg srst=0,hrst=0;reg cfg_we=0,desc_we=0,run_v=0;reg[9:0]cfg_addr[0:7];reg[255:0]cfg_data[0:7];reg[6:0]desc_addr=0;reg[255:0]desc_data[0:7];
 wire[7:0]running,run_done,active,fault;
 wire[31:0]kv,krdy,kwe,kdone,rv,rrdy;wire[959:0]ka;wire[127:0]kl,rb;wire[543:0]kt,rt;wire[8191:0]kw,rd;wire[1023:0]ks;
 wire[8*1099-1:0]packet;wire[8*83-1:0]command;wire[8*1082-1:0]lt0,lt1;wire[8*570-1:0]lb0,lb1;wire[95:0]fm;wire[343:0]expected_request;
 genvar g;
 for(g=0;g<8;g=g+1)begin:grp
  ot_hbm_svc_sm_group #(.STACK(STACK[1:0]),.SM(g),.LBANKS(LBANKS)) u(
   .stream_clk(stream),.stream_rst_n(srst),.hbm_clk(hbm),.hbm_rst_n(hrst),.stream_bank_clk({2{stream}}),.hbm_fifo_clk({2{hbm}}),.hbm_pc_clk({4{hbm}}),
   .program_cfg_we(cfg_we),.program_cfg_addr(cfg_addr[g]),.program_cfg_data(cfg_data[g]),
   .desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data[g]),.run_v(run_v),.run_base(7'd0),.run_count(8'(EPOCHS)),
   .running(running[g]),.run_done(run_done[g]),.program_active(active[g]),.fault(fault[g]),
   .sm_packet(packet[g*1099+:1099]),.sm_command(command[g*83+:83]),.expected_request(expected_request[g*43+:43]),
   .lt0(lt0[g*1082+:1082]),.lt1(lt1[g*1082+:1082]),.lb0(lb0[g*570+:570]),.lb1(lb1[g*570+:570]),.fm(fm[g*12+:12]),
   .k_v(kv[g*4+:4]),.k_rdy(krdy[g*4+:4]),.k_addr(ka[g*120+:120]),.k_len(kl[g*16+:16]),.k_tag(kt[g*68+:68]),.k_we(kwe[g*4+:4]),
   .k_wdata(kw[g*1024+:1024]),.k_wstrb(ks[g*128+:128]),.k_wr_done(kdone[g*4+:4]),
   .kr_v(rv[g*4+:4]),.kr_rdy(rrdy[g*4+:4]),.kr_tag(rt[g*68+:68]),.kr_beat(rb[g*16+:16]),.kr_data(rd[g*1024+:1024]));
 end
 wire[31:0]row_v,col_v,col_we,dram_rvalid;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;wire[8191:0]col_data,dram_rdata;wire[1023:0]col_strb;wire native_fault;
 ot_hbm_svc_native_sector_pipeline_leaves controller(.clk(hbm),.rst_n(hrst),.pc_clk({32{hbm}}),
  .k_tag(kt),.k_wdata(kw),.k_addr(ka),.kr_rdy(rrdy),.k_wstrb(ks),.k_we(kwe),.k_len(kl),.k_rdy(krdy),.kr_v(rv),.kr_data(rd),.kr_beat(rb),
  .k_wr_done(kdone),.kr_tag(rt),.k_v(kv),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),
  .col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(32'h28810000),.K_MEM(65536)) dram(
  .clk(hbm),.rst_n(hrst),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 reg[1087:0]records[0:7][0:ROWS-1];reg[1087:0]load_rows[0:ROWS-1];
 integer packets[0:7],feeds[0:7],sectors[0:7];integer cycle=0;string images,path,smname;integer early;
 real launch_at,done_t[0:63];integer ndone=0;
 function automatic[255:0]word(input integer pc,input integer tag,input integer bank,input integer ep,input integer addr);
  reg[134:0]x;reg[25:0]control;integer row;
  begin
   x=0;
   if(pc<ROWS)begin x[83]=1;x[84]=bank[0];x[100:85]=ep[15:0];x[106:101]=pc[5:0];x[116:107]=10'(tag+pc);end
   if(pc>0)begin
    row=pc-1;control={1'b1,1'(row==0),1'(row==ROWS-1),12'(row),1'b1,3'b0,7'b0};
    x[25:0]=control;x[29]=1;x[39:30]=10'(tag+row);
   end
   if(early!=0&&pc==0)begin x[29]=1;x[39:30]=10'(tag);end
   if(pc==ROWS)begin x[117]=1;x[118]=bank[0];x[134:119]=ep[15:0];end
   word=0;word[255:240]=16'hc7a1;word[233:224]=addr[9:0];word[134:0]=x;
  end
 endfunction
 function automatic[255:0]desc(input integer e);
  reg[255:0]d;
  begin
   d=0;d[31:0]=32'(STACK<<30);d[46:32]=15'd20738;d[48:47]=2'(e%LBANKS);d[64:49]=16'(51+e%2);d[71:65]=7'(ROWS);
   d[81:72]=10'(e%2==0?100:300);d[91:82]=10'(128*(e%2));d[102:92]=11'(128*(e%2)+ROWS+1);d[118:103]=16'd1;
   d[255:240]=16'h5d15;d[239:233]=7'(e);desc=d;
  end
 endfunction
 always @(posedge hbm)if(hrst)begin
  if(native_fault)$fatal(1,"SM_STACK PHY aperture");
  for(integer p=0;p<32;p=p+1)if(kv[p]&&krdy[p])begin
   if((((ka[p*30+:30]>>2)^(ka[p*30+:30]>>7)^(ka[p*30+:30]>>12))&31)!=p)$fatal(1,"SM_STACK actualPC mapping");
   sectors[p/4]=sectors[p/4]+kl[p*4+:4];
  end
 end
 always @(posedge stream)begin
  cycle=cycle+1;#2;
  if(srst&&hrst)begin
   if(|fault)$fatal(1,"SM_STACK DUT fault cycle%0d mask%h",cycle,fault);
   if(grp[0].u.feed.program_done)begin done_t[ndone]=$realtime;ndone=ndone+1;end
   for(integer s=0;s<8;s=s+1)begin
    if(packet[s*1099+1098])begin
     if(packet[s*1099+1088+:10]!==10'(((packets[s]/ROWS)%2==0?100:300)+packets[s]%ROWS)||packet[s*1099+:1088]!==records[s][packets[s]%ROWS])$fatal(1,"SM_STACK packet mismatch sm%0d row%0d",s,packets[s]);
     packets[s]=packets[s]+1;
    end
    if(lt0[s*1082+1081])begin
     if(lt0[s*1082+:1056]!==records[s][feeds[s]%ROWS][1055:0]||lt1[s*1082+:1056]!==records[s][feeds[s]%ROWS][1055:0]||lb0[s*570+:544]!=={records[s][feeds[s]%ROWS][1087:1056],records[s][feeds[s]%ROWS][1023:512]}||lb1[s*570+:544]!=={records[s][feeds[s]%ROWS][1087:1056],records[s][feeds[s]%ROWS][1023:512]})$fatal(1,"SM_STACK actual S1 consumer mismatch sm%0d row%0d",s,feeds[s]);
     feeds[s]=feeds[s]+1;
    end
    if(command[s*83+:83]!==grp[s].u.feed.programme_leaf.calendar&{83{grp[s].u.feed.programme_v}})$fatal(1,"SM_STACK sm_command != programme sm%0d",s);
   end
  end
 end
 initial begin
  early=$test$plusargs("EARLY");if(!$value$plusargs("IMAGES=%s",images))$fatal(1,"archive images mandatory");
  for(integer s=0;s<8;s=s+1)begin
   packets[s]=0;feeds[s]=0;sectors[s]=0;
   smname=$sformatf("sm%02d",s+8*STACK);path={images,"/",smname,"/backing.hex"};$readmemh(path,dram.mem);
   path={images,"/",smname,"/records.hex"};$readmemh(path,load_rows);for(integer r=0;r<ROWS;r=r+1)records[s][r]=load_rows[r];
  end
  repeat(4)@(negedge stream);srst=1;repeat(3)@(negedge hbm);hrst=1;repeat(20)@(negedge stream);
  // initialization (host loader): programme words and descriptor table
  for(integer b=0;b<2;b=b+1)for(integer pc=0;pc<ROWS+1;pc=pc+1)begin
   cfg_we=1;for(integer s=0;s<8;s=s+1)begin cfg_addr[s]=10'(b*128+pc);cfg_data[s]=word(pc,b==0?100:300,b,51+b,b*128+pc);end
   @(negedge stream);
  end
  cfg_we=0;
  for(integer e=0;e<EPOCHS;e=e+1)begin desc_we=1;desc_addr=7'(e);for(integer s=0;s<8;s=s+1)desc_data[s]=desc(e);@(negedge stream);end
  desc_we=0;repeat(4)@(negedge stream);
  // one launch; the hardware issues every reserve / start / go
  run_v=1;launch_at=$realtime;@(negedge stream);run_v=0;
  wait(run_done==8'hff||(ndone>=EPOCHS&&running==0));
  repeat(6)@(negedge stream);
  for(integer s=0;s<8;s=s+1)
   if(packets[s]!=ROWS*EPOCHS||feeds[s]!=ROWS*EPOCHS||sectors[s]!=SECT*EPOCHS)$fatal(1,"SM_STACK counts sm%0d packets%0d feeds%0d sectors%0d",s,packets[s],feeds[s],sectors[s]);
  $display("SM_GROUPS_ISSUED PASS stack=%0d rows=%0d epochs=%0d lbanks=%0d first_done_ps=%0f last_done_ps=%0f steady_epoch_ps=%0f bytes_per_epoch_per_SM=%0d tb_issue=0",
   STACK,ROWS,EPOCHS,LBANKS,done_t[0]-launch_at,done_t[EPOCHS-1]-launch_at,(done_t[EPOCHS-1]-done_t[1])/(EPOCHS-2),ROWS*136);
  for(integer e=0;e<EPOCHS;e=e+1)$display("SM_GROUPS_ISSUED epoch=%0d done_ps=%0f",e,done_t[e]-launch_at);
  $finish;
 end
 initial begin #300000000;$fatal(1,"SM_STACK timeout");end
endmodule
