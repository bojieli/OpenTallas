`timescale 1ps/1ps
// Original master is independently fed from externally accepted packets, not DUT data.
module svg_pair_old_reference #(parameter integer BANK=1)(
 input wire hclk,sclk,hrst,srst,input wire accept,input wire [284:0] in_data,
 input wire pop,input wire [284:0] head,input wire core_ready,
 input wire reserve_v,input wire [1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 input wire read_v,input wire [1:0] read_bank,input wire [5:0] read_row,
 input wire native_complete,input wire [1:0] native_bank,input wire native_fault,
 input wire [255:0] native_data,
 output integer errors=0,packets=0,completions=0
);
 reg [284:0] expected[0:1023],packet_q=0;integer wp=0,rp=0;
 reg rv=0,st=1,rdv=0;reg [1:0] rb=0,rdb=0;reg [15:0] ep=0;reg [11:0] total=0;reg [5:0] row=0;
 wire ready,overflow,cv,fault;wire [1:0] cb;wire [255:0] data;
 reg [255:0] data_q=0;reg exp_c,exp_f;reg [1:0] exp_b;
 ot_hbm_svc_sm8_landing_bank #(.BANK(3'(BANK)),.LBANKS(4)) reference_bank(
  .hbm_clk(hclk),.hbm_rst_n(hrst),.stream_clk(sclk),.stream_rst_n(srst),
  .in_v(pop),.in_ready(ready),.in_data(packet_q),.overflow(overflow),
  .reserve_v(rv),.reserve_bank(rb),.reserve_epoch(ep),.reserve_total(total),.stop(st),
  .complete_v(cv),.complete_bank(cb),.fault(fault),
  .read_v(rdv),.read_bank(rdb),.read_row(row),.read_data(data));
 always @(posedge hclk or negedge hrst)begin
  if(!hrst)begin wp=0;rp=0;end
  else begin
   if(accept)begin expected[wp]=in_data;wp=wp+1;packets=packets+1;end
   if(pop)begin
    if(rp>=wp||head!==expected[rp])begin errors=errors+1;if(errors<5)$display("PAIR_INGRESS_FAIL bank=%0d rp=%0d wp=%0d",BANK,rp,wp);end
    rp=rp+1;
   end
   #1;if(ready!==core_ready||overflow)begin errors=errors+1;if(errors<5)$display("PAIR_CORE_READY_FAIL bank=%0d",BANK);end
  end
 end
 always @(negedge hclk)packet_q=expected[rp];
 always @(posedge sclk or negedge srst)begin
  if(!srst)begin rv<=0;st<=1;rdv<=0;rb<=0;rdb<=0;ep<=0;total<=0;row<=0;data_q<=0;end
  else begin
   rv<=reserve_v;st<=stop;rdv<=read_v;rb<=reserve_bank;rdb<=read_bank;ep<=reserve_epoch;total<=reserve_total;row<=read_row;
   data_q<=data;
  end
 end
 always @(posedge sclk)begin
  if(srst)begin
   exp_c=cv;exp_b=cb;exp_f=fault;
   #80;
   if(native_complete)completions=completions+1;
   if(native_complete!==exp_c||(native_complete&&native_bank!==exp_b)||native_fault!==exp_f||native_data!==data_q)begin
    errors=errors+1;if(errors<5)$display("PAIR_OLD_MASTER_FAIL bank=%0d complete=%0b/%0b fault=%0b/%0b",BANK,native_complete,exp_c,native_fault,exp_f);
   end
  end
 end
endmodule

module tb_svg_landing_pair_native;
 parameter integer MUT=0,J=1;
 reg sched_clk=0,pair_hbm_clk=0,pair_clk=0,return_clk=0;
 always #417 sched_clk=~sched_clk;always #512 pair_hbm_clk=~pair_hbm_clk;
 initial begin #30;forever #417 pair_clk=~pair_clk;end
 initial begin #10;forever #417 return_clk=~return_clk;end
 reg pair_hbm_rst_n=0,pair_rst_n=0,return_rst_n=0;
 reg [1:0] in_v=0;reg [569:0] in_data=0;wire [1:0] in_ready,overflow;
 reg reserve_v=0;reg [1:0] reserve_bank=0;reg [15:0] reserve_epoch=0;reg [11:0] reserve_total=272;reg stop=1;
 reg [1:0] read_v=0;reg [3:0] read_bank=0;reg [11:0] read_row=0;reg [2:0] ordinal=0;reg group_valid=0;
 wire [1:0] complete_v,bank_fault;wire [3:0] complete_bank;
 wire [255:0] out_data;wire [2:0] out_ordinal;wire out_valid,phase_fault;
 ot_hbm_svg_landing_pair_native #(.J(J),.MUT(MUT)) dut(.*);
 wire [31:0] ref_errors[0:1],ref_packets[0:1],ref_completes[0:1];
 genvar b;generate for(b=0;b<2;b=b+1)begin:g_reference
  svg_pair_old_reference #(.BANK(J+4*b)) u_reference(
   .hclk(pair_hbm_clk),.sclk(pair_clk),.hrst(dut.g_bank[b].u_bank.hreset),.srst(dut.g_bank[b].u_bank.sreset),
   .accept(in_v[b]&&in_ready[b]),.in_data(in_data[b*285+:285]),
   .pop(dut.g_bank[b].u_bank.pop),.head(dut.g_bank[b].u_bank.head),.core_ready(dut.g_bank[b].u_bank.core_ready),
   .reserve_v(reserve_v),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),.reserve_total(reserve_total),.stop(stop),
   .read_v(read_v[b]),.read_bank(read_bank[b*2+:2]),.read_row(read_row[b*6+:6]),
   .native_complete(complete_v[b]),.native_bank(complete_bank[b*2+:2]),.native_fault(bank_fault[b]),.native_data(dut.native_data[b*256+:256]),
   .errors(ref_errors[b]),.packets(ref_packets[b]),.completions(ref_completes[b]));
 end endgenerate
 integer errors=0,tick=0,release_edge=0,round=0,lb=0,n=0,k=0,i=0;
 integer outputs=0,data_outputs=0,warm_outputs=0,windows=0,window_start=0,warm_checks=0,first_valid=0;
 integer driver_launch=0,driver_full=0,driver_lb=0,driver_check=0;
 integer latency_min=999999,latency_max=0,independent_valid_cases=0;
 reg check_nominal=1,phase_seen=0;
 reg [255:0] hold0=0,hold1=0;reg [255:0] gold[0:6];reg [2:0] gold_ord[0:6];reg [6:0] gold_v=0,gold_check=0;
 integer gold_launch[0:6],gold_full[0:6];
 function automatic [255:0] pattern(input integer bank,block,row,epoch);
  begin pattern={32'(bank),32'(block),32'(row),32'(epoch),32'(bank+row*17),32'(row^32'hdeadbeef),32'(epoch*136+block*34+row),32'(bank^block^row^epoch)};end
 endfunction
 task idle(input integer count);begin repeat(count)@(negedge sched_clk);end endtask
 task send_bank(input integer b,block,count);
  integer r;begin
   for(r=0;r<count;r=r+1)begin
    @(negedge pair_hbm_clk);while(!in_ready[b])begin in_v[b]=0;@(negedge pair_hbm_clk);end
    in_data[b*285+:285]={11'(J+4*b+8*r),2'(block),16'(round*8+block+7),pattern(J+4*b,block,r,round)};in_v[b]=1;
   end
   @(negedge pair_hbm_clk);in_v[b]=0;
  end
 endtask
 task read_group(input integer block,full,valid_group,check_data);
  reg pick;begin
   driver_launch=tick;driver_full=full;driver_lb=block;driver_check=check_data;
   ordinal=3'(full);group_valid=valid_group;
   read_bank={2'(block),2'(block)};
   read_row={6'((full*11+3*block)%34),6'((full*7+block)%34)};
   read_v=valid_group?3:0;
   pick=ordinal[2]^(J<ordinal[1:0]);
   if(valid_group&&check_data)begin
    if(full%5==0)read_v=0;
    else if(full%7==0)read_v=pick?1:2;
    else if(full%11==0)read_v=pick?2:1;
    if(!(pick?read_v[1]:read_v[0]))independent_valid_cases=independent_valid_cases+1;
   end
  end
 endtask
 always @(posedge sched_clk)begin
  tick=tick+1;
  if(!pair_rst_n)begin gold_v=0;gold_check=0;release_edge=0;first_valid=0;end
  else begin
   release_edge=release_edge+1;
   for(i=6;i>0;i=i-1)begin
    gold[i]=gold[i-1];gold_ord[i]=gold_ord[i-1];gold_v[i]=gold_v[i-1];gold_check[i]=gold_check[i-1];
    gold_launch[i]=gold_launch[i-1];gold_full[i]=gold_full[i-1];
   end
   if(read_v[0]&&!stop)hold0=pattern(J,read_bank[1:0],read_row[5:0],round);
   if(read_v[1]&&!stop)hold1=pattern(J+4,read_bank[3:2],read_row[11:6],round);
   gold[0]=(ordinal[2]^(J<ordinal[1:0]))?hold1:hold0;
   gold_ord[0]=ordinal;gold_v[0]=release_edge>=3&&group_valid;gold_check[0]=driver_check;
   gold_launch[0]=driver_launch;gold_full[0]=driver_full;
  end
  #120;
  if(check_nominal)begin
   if(out_valid!==gold_v[6])begin errors=errors+1;if(errors<8)$display("PAIR_META_ALIGN_FAIL valid=%b/%b tick=%0d",out_valid,gold_v[6],tick);end
   if(out_valid)begin
    outputs=outputs+1;
    if(!first_valid)begin first_valid=release_edge;warm_checks=warm_checks+1;$display("PAIR_RESET_WARM edge=%0d expected=9",first_valid);if(first_valid!=9)errors=errors+1;end
    if(out_ordinal!==gold_ord[6])begin errors=errors+1;if(errors<8)$display("PAIR_META_ALIGN_FAIL ordinal=%0d/%0d",out_ordinal,gold_ord[6]);end
    if(gold_check[6])begin
     data_outputs=data_outputs+1;
     if(out_data!==gold[6])begin errors=errors+1;if(errors<8)$display("PAIR_SELECT_DATA_FAIL ordinal=%0d full=%0d",out_ordinal,gold_full[6]);end
     if(tick-gold_launch[6]<latency_min)latency_min=tick-gold_launch[6];
     if(tick-gold_launch[6]>latency_max)latency_max=tick-gold_launch[6];
     if(tick-gold_launch[6]!=7)errors=errors+1;
     if(gold_full[6]==64)window_start=tick;
     if(gold_full[6]==127)begin windows=windows+1;$display("PAIR_SUSTAIN window=%0d groups=64 pair_edges=%0d bytes_per_edge=32",windows,tick-window_start+1);if(tick-window_start!=63)errors=errors+1;end
    end else warm_outputs=warm_outputs+1;
   end
   if((|bank_fault)||(|overflow))begin errors=errors+1;if(errors<8)$display("PAIR_NATIVE_FAULT_FAIL");end
   if(phase_fault&&!phase_seen)begin phase_seen=1;errors=errors+1;$display("PAIR_RING_PHASE_FAIL");end
  end
 end
 initial begin
  for(round=0;round<3;round=round+1)begin
   pair_hbm_rst_n=0;pair_rst_n=0;return_rst_n=0;group_valid=0;read_v=0;in_v=0;stop=1;reserve_v=0;driver_check=0;
   idle(5);pair_hbm_rst_n=1;pair_rst_n=1;return_rst_n=1;
   // Check reset envelope with all data masked/unused; no power-up payload claim.
   for(n=0;n<10;n=n+1)begin read_group(0,n,1,0);read_v=0;idle(1);end
   read_group(0,0,0,0);idle(12);
   for(lb=0;lb<4;lb=lb+1)begin
    reserve_v=1;reserve_bank=2'(lb);reserve_epoch=16'(round*8+lb+7);stop=1;idle(1);reserve_v=0;idle(3);
    fork
     begin idle(40);stop=0;end
     send_bank(0,lb,34);
     send_bank(1,lb,34);
    join
    idle(20);
   end
   for(lb=0;lb<4;lb=lb+1)begin
    for(n=0;n<272;n=n+1)begin
     if(n>=128&&n%17==0)begin read_group(lb,511-n,0,0);idle(1);end
     read_group(lb,n,1,1);idle(1);
    end
   end
   read_group(0,0,0,0);idle(12);
   if(round<2)begin stop=1;idle(3);fork send_bank(0,0,2);send_bank(1,0,2);join end
  end
  if(data_outputs!=3264||warm_outputs!=24||windows!=12||warm_checks!=3||latency_min!=7||latency_max!=7||independent_valid_cases<100||ref_completes[0]!=12||ref_completes[1]!=12)begin
   errors=errors+1;$display("PAIR_COUNTS_FAIL data=%0d warm=%0d windows=%0d reset=%0d latency=%0d/%0d completes=%0d/%0d",data_outputs,warm_outputs,windows,warm_checks,latency_min,latency_max,ref_completes[0],ref_completes[1]);
  end
  // Original duplicate check survives the composed leaf and its separate fault Q.
  check_nominal=0;send_bank(0,0,1);idle(30);if(!bank_fault[0])begin errors=errors+1;$display("PAIR_DUPLICATE_GUARD_FAIL");end
  errors=errors+ref_errors[0]+ref_errors[1];
  $display("SVG_NATIVE_PAIR %s mut=%0d J=%0d errors=%0d payload_groups=%0d masked_warm_groups=%0d windows=%0d independent_valid=%0d latency=%0d/%0d old_miter_errors=%0d/%0d",errors==0?"PASS":"FAIL",MUT,J,errors,data_outputs,warm_outputs,windows,independent_valid_cases,latency_min,latency_max,ref_errors[0],ref_errors[1]);
  if(errors)$fatal(1,"native landing pair mismatch");$finish;
 end
endmodule
