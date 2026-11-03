`timescale 1ns/1fs
// TOK-QW-3: native table-ROM loader (main rtl/qwen_dv/qfd_dv_table_rom_loader.sv) on the ACTUAL rank0 HEAD37
// source masks (codex-head-source-event-1101/source1/rank0), all 12 slices, stages 1/36/37, 4 users.
// Default and HEAD37 instances must stay in lockstep with the frozen reference for stages 1..36; stage37 writes are
// logged and checked against head37_stage.json + user_relocation.json by check.py (independent of this RTL).
module tb_loader_real;
reg ck=0;always #0.4165 ck=~ck;reg rst_n=0,start=0;reg[5:0]stage=0;reg[1:0]user_id=0;
localparam integer NS=12;
wire [NS-1:0] we_h,we_d,we_r,bz_h,bz_d,bz_r,dn_h,dn_d,dn_r,ft_h,ft_d,ft_r;
wire [23:0] a_h[0:NS-1],a_d[0:NS-1],a_r[0:NS-1];wire[1:0]k_h[0:NS-1],k_d[0:NS-1],k_r[0:NS-1];
wire [1023:0] x_h[0:NS-1],x_d[0:NS-1],x_r[0:NS-1];
genvar g;
generate for(g=0;g<NS;g=g+1)begin:sl
 qfd_dv_table_rom_loader #(.SLICE(g),.BTAB_COMPACT(1),.WE_COPIES(34),.HEAD_STAGE37(1)) h(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we_h[g]),.tw_addr(a_h[g]),.tw_kind(k_h[g]),.tw_data(x_h[g]),.busy(bz_h[g]),.done(dn_h[g]),.fault(ft_h[g]),.tw_we_k());
 qfd_dv_table_rom_loader #(.SLICE(g),.BTAB_COMPACT(1),.WE_COPIES(34)) d(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we_d[g]),.tw_addr(a_d[g]),.tw_kind(k_d[g]),.tw_data(x_d[g]),.busy(bz_d[g]),.done(dn_d[g]),.fault(ft_d[g]),.tw_we_k());
 reference_loader #(.SLICE(g),.BTAB_COMPACT(1),.WE_COPIES(34)) r(.ck(ck),.rst_n(rst_n),.start(start),.stage(stage),.user_id(user_id),.other_table_write(1'b0),.tw_we(we_r[g]),.tw_addr(a_r[g]),.tw_kind(k_r[g]),.tw_data(x_r[g]),.busy(bz_r[g]),.done(dn_r[g]),.fault(ft_r[g]),.tw_we_k());
end endgenerate
integer cyc=0,origin=0,st,u,s,windows=0,w37=0,wpre=0;reg checking=0;
integer n[0:NS-1],firstw[0:NS-1],lastw[0:NS-1],donew[0:NS-1];
initial begin
 #0.001;
 if($test$plusargs("MUT_GAIN"))sl[1].h.m0.arr[486][2]=~sl[1].h.m0.arr[486][2];
 for(st=0;st<3;st=st+1)for(u=0;u<4;u=u+1)begin
  checking=0;rst_n=0;repeat(8)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
  stage=(st==0)?1:(st==1?36:37);user_id=2'(u);
  for(s=0;s<NS;s=s+1)begin n[s]=0;firstw[s]=-1;lastw[s]=-1;donew[s]=-1;end
  start=1;checking=1;origin=cyc+1;@(negedge ck);start=0;repeat(110)@(negedge ck);
  if(ft_h!=0)$fatal(1,"HEAD_FAULT stage%0d user%0d %b",stage,u,ft_h);
  if(st==2&&(ft_d!={NS{1'b1}}||ft_r!={NS{1'b1}}))$fatal(1,"DEFAULT_STAGE37_NOT_REJECTED %b %b",ft_d,ft_r);
  for(s=0;s<NS;s=s+1)$display("CASE stage%0d user%0d slice%0d writes%0d first%0d last%0d done%0d",stage,u,s,n[s],firstw[s],lastw[s],donew[s]);
  windows=windows+1;
 end
 $display("LOADER_REAL_DONE windows%0d prefix_writes%0d head37_writes%0d period833ps",windows,wpre,w37);$finish;
end
always @(posedge ck)begin
 cyc=cyc+1;
 if(checking&&rst_n)for(s=0;s<NS;s=s+1)begin
  if({we_d[s],bz_d[s],dn_d[s],ft_d[s]}!=={we_r[s],bz_r[s],dn_r[s],ft_r[s]})$fatal(1,"DEFAULT_CONTROL_LOCKSTEP s%0d",s);
  if(we_d[s]&&{k_d[s],a_d[s],x_d[s]}!=={k_r[s],a_r[s],x_r[s]})$fatal(1,"DEFAULT_PAYLOAD_LOCKSTEP s%0d",s);
  if(stage<=36)begin
   if({we_h[s],bz_h[s],dn_h[s],ft_h[s]}!=={we_r[s],bz_r[s],dn_r[s],ft_r[s]})$fatal(1,"PREFIX_CONTROL_LOCKSTEP s%0d",s);
   if(we_h[s]&&{k_h[s],a_h[s],x_h[s]}!=={k_r[s],a_r[s],x_r[s]})$fatal(1,"PREFIX_PAYLOAD_LOCKSTEP s%0d",s);
  end
  if(dn_h[s]&&donew[s]<0)donew[s]=cyc-origin;
  if(we_h[s])begin
   if(n[s]==0)firstw[s]=cyc-origin;lastw[s]=cyc-origin;n[s]=n[s]+1;
   if(stage==37)begin $display("W37 %0d %0d %0d %0d %0d %h",s,user_id,cyc-origin,k_h[s],a_h[s],x_h[s]);w37=w37+1;end
   else wpre=wpre+1;
  end
 end
end
endmodule
