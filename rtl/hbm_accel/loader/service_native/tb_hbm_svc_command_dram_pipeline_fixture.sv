`timescale 1ps/1fs
// OFFCHIP TEST FIXTURE ONLY. Consumes physical commands; owns no controller,
// request scheduling, ready signals, or refresh policy. Full native address
// reconstructed from PC/bank/row/column accesses a bounded mutable array.
module ot_hbm_svc_command_dram_pipeline_fixture #(
 parameter integer K_BASE=32'h28800000,K_MEM=65536
)(input wire clk,rst_n,input wire [31:0]row_v,col_v,col_we,
 input wire [95:0]row_op,input wire [159:0]row_bank,col_bank,col_col,
 input wire [607:0]row_row,input wire [8191:0]col_data,input wire [1023:0]col_strb,
 output reg [31:0]dram_rvalid=0,output reg [8191:0]dram_rdata=0);
 reg [255:0]mem[0:K_MEM-1];
 reg opened[0:31][0:31];integer current_row[0:31][0:31];
 integer act_at[0:31][0:31],pre_at[0:31][0:31],refresh_until[0:31][0:31],write_at[0:31][0:31],read_at[0:31][0:31];
 integer last_act[0:31],last_act_bg[0:31][0:3],last_col_bg[0:31][0:3],last_rd[0:31],last_wr[0:31];
 integer faw[0:31][0:3],ref_at[0:31],writes=0,reads=0,refreshes=0,cyc=0;
 // CL12500ps + BURST1024ps + response path10000ps =23524ps, ceil23 HBM edges.
 reg [22:0]due_v[0:31];reg [255:0]due_data[0:31][0:22];
 function automatic [29:0]sector(input integer pc,bank,row,col);
 reg [29:0]s;begin s=30'(row)<<15;s[11:7]=5'(col);s[14:12]=3'(bank>>2)^3'(row>>2);s[1:0]=2'(bank)^2'(row);s[6:2]=5'(pc)^s[11:7]^s[16:12];sector=s;end endfunction
 initial begin
 for(integer p=0;p<32;p=p+1)begin
  due_v[p]=0;for(integer d=0;d<23;d=d+1)due_data[p][d]=0;last_act[p]=-1000;last_rd[p]=-1000;last_wr[p]=-1000;ref_at[p]=-1000;
  for(integer b=0;b<32;b=b+1)begin opened[p][b]=0;current_row[p][b]=0;act_at[p][b]=-1000;pre_at[p][b]=-1000;refresh_until[p][b]=-1000;write_at[p][b]=-1000;read_at[p][b]=-1000;end
  for(integer g=0;g<4;g=g+1)begin last_act_bg[p][g]=-1000;last_col_bg[p][g]=-1000;faw[p][g]=-1000;end
 end
 end
 always @(posedge clk)begin:COMMANDS
 integer b,kind,bg;reg [29:0]s;
 cyc=cyc+1;dram_rvalid<=0;
 if(rst_n)for(integer p=0;p<32;p=p+1)begin
  due_v[p]<={due_v[p][21:0],col_v[p]&&!col_we[p]};
  for(integer d=1;d<23;d=d+1)due_data[p][d]<=due_data[p][d-1];
  if(due_v[p][22])begin dram_rvalid[p]<=1;dram_rdata[p*256+:256]<=due_data[p][22];end
  if(row_v[p])begin
   b=row_bank[p*5+:5];bg=b&3;kind=row_op[p*3+:3];
   if(kind==1)begin
    if(opened[p][b]||cyc-pre_at[p][b]<16||cyc<refresh_until[p][b]||cyc-last_act[p]<3||cyc-last_act_bg[p][bg]<4||cyc-faw[p][0]<15||cyc-ref_at[p]<8)$fatal(1,"native command illegal ACT p%0d b%0d cyc%0d",p,b,cyc);
    opened[p][b]=1;current_row[p][b]=row_row[p*19+:19];act_at[p][b]=cyc;last_act[p]=cyc;last_act_bg[p][bg]=cyc;
    for(integer g=0;g<3;g=g+1)faw[p][g]=faw[p][g+1];faw[p][3]=cyc;
   end else if(kind==0)begin
    if(opened[p][b]&&(cyc-act_at[p][b]<28||cyc-write_at[p][b]<28||cyc-read_at[p][b]<6))$fatal(1,"native command early PRE p%0d b%0d",p,b);
    opened[p][b]=0;pre_at[p][b]=cyc;
   end else if(kind==6)begin
    if(opened[p][b]||cyc-pre_at[p][b]<16||cyc<refresh_until[p][b]||cyc-last_act[p]<8||cyc-ref_at[p]<8)$fatal(1,"native command illegal REFpb p%0d b%0d",p,b);
    refresh_until[p][b]=cyc+196;refreshes=refreshes+1;ref_at[p]=cyc;
   end else if(kind==5)begin
    for(integer bb=0;bb<32;bb=bb+1)begin
     if(opened[p][bb]&&(cyc-act_at[p][bb]<28||cyc-write_at[p][bb]<28||cyc-read_at[p][bb]<6))$fatal(1,"native command early PREab");
     opened[p][bb]=0;pre_at[p][bb]=cyc;
    end
   end else $fatal(1,"native command unsupported row op%0d",kind);
  end
  if(col_v[p])begin
   b=col_bank[p*5+:5];bg=b&3;
   if(!opened[p][b]||cyc-act_at[p][b]<(col_we[p]?10:19)||cyc<refresh_until[p][b]||cyc-last_col_bg[p][bg]<3)$fatal(1,"native command column timing p%0d b%0d",p,b);
   if(col_we[p]&&cyc-last_rd[p]<10||!col_we[p]&&cyc-last_wr[p]<14)$fatal(1,"native command RD/WR turnaround");
   s=sector(p,b,current_row[p][b],col_col[p*5+:5]);
   if(s<K_BASE||{1'b0,s}>=33'(K_BASE)+K_MEM)$fatal(1,"native command outside actual COLB range %h",s);
   last_col_bg[p][bg]=cyc;
   if(col_we[p])begin
    for(integer by=0;by<32;by=by+1)if(col_strb[p*32+by])mem[(s-K_BASE)][8*by+:8]=col_data[p*256+8*by+:8];
    writes=writes+1;write_at[p][b]=cyc;last_wr[p]=cyc;
   end else begin
    due_data[p][0]<=mem[(s-K_BASE)];reads=reads+1;read_at[p][b]=cyc;last_rd[p]=cyc;
   end
  end

 end
 end
endmodule
