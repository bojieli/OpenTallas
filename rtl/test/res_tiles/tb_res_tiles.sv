`timescale 1ns/1ps
module tb_res_tiles #(parameter integer MUT=0, USE_MACRO=1);
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,me_en=0,i_ov=0;reg [7:0] i_we=0;reg [191:0] i_addr=0;reg [127:0] i_mask=0;reg [4095:0] i_data=0;
 wire ov,oe,onul,rok,fault;wire [19:0] row;wire [15:0] mask;wire [511:0] data;reg cr=0;
 ot_qfd_res_tiles #(.MUT(MUT),.USE_MACRO(USE_MACRO)) dut(.clk(clk),.rst_n(rst_n),.me_en(me_en),.i_ov(i_ov),.i_we(i_we),
 .i_addr(i_addr),.i_mask(i_mask),.i_data(i_data),.o_v(ov),.o_end(oe),.o_nul(onul),.o_row(row),.o_mask(mask),.o_data(data),.o_cr(cr),.rok(rok),.fault(fault));
 reg [550:0] expq[0:40000];integer ew=0,er=0,pending=0,burst=0,c=0,k,j,last,stopdebt=0;
 integer rq_cycle[0:40000];integer qw=0,qr=0;
 reg [7:0] wen;reg endbit;integer x;reg [511:0] word;
 task tick;
 begin
 @(negedge clk);
 if(dut.u_ctl.rq_v) begin rq_cycle[qw]=c;qw=qw+1;end
 if(dut.u_ctl.rv) begin
  if(qr==qw || c-rq_cycle[qr]!=19) $fatal(1,"CONVEYOR latency=%0d",c-rq_cycle[qr]);
  qr=qr+1;
 end
 if(fault) $fatal(1,"FAULT cycle=%0d n=%0d cr=%0d",c,dut.u_ctl.n,dut.u_ctl.cr);
 if(ov) begin
  if(er==ew) $fatal(1,"unexpected beat");
  if({1'b1,oe,onul,row,mask,(onul?512'd0:data)}!==expq[er])
   $fatal(1,"MISMATCH beat=%0d cycle=%0d got row=%0d end=%0d nul=%0d want row=%0d end=%0d nul=%0d",er,c,row,oe,onul,expq[er][547:528],expq[er][549],expq[er][548]);
  er=er+1;pending=pending+1;
 end
 cr=0;if(pending>0 && (c%251>95)) begin cr=1;pending=pending-1;end
 c=c+1;
 end endtask
 initial begin
 repeat(5) @(negedge clk);rst_n=1;
 for(x=0;x<12000;x=x+1) begin
  tick();
  // A falling ready permits a realistic 42-edge engine stopping debt.
  if(rok) stopdebt=42;else if(stopdebt>0) stopdebt=stopdebt-1;
  me_en=(rok||stopdebt>0)&&x%7!=0;
  i_ov=me_en && x%11==0 && burst<360;
  if(i_ov) begin
   wen=8'((burst*53)^ (burst>>2));if(burst%13==0) wen=0;if(burst%17==0) wen=255;
   i_we=wen;last=-1;for(k=0;k<8;k=k+1) if(wen[k]) last=k;
   for(k=0;k<8;k=k+1) begin
    i_addr[k*24+:24]=burst*8+k;i_mask[k*16+:16]=16'((burst*31+k)^16'hac95);
    for(j=0;j<16;j=j+1) word[j*32+:32]=32'((burst*131+k*17+j)^32'hd3915827);
    i_data[k*512+:512]=word;
    if(wen[k]) begin expq[ew]={1'b1,1'(k==last),1'b0,20'(burst*8+k),i_mask[k*16+:16],word};ew=ew+1;end
   end
   if(wen==0) begin expq[ew]={1'b1,1'b1,1'b1,20'(burst*8+7),16'd0,512'd0};ew=ew+1;end
   burst=burst+1;
  end
  // Held valid while clock-disabled must never be captured a second time.
  if(x%7==0) begin me_en=0;i_ov=1;end
 end
 me_en=0;i_ov=0;
 while(er<ew && c<30000) tick();
 if(er!=ew||burst!=360||qw!=qr) $fatal(1,"DRAIN er=%0d ew=%0d bursts=%0d",er,ew,burst);
 $display("PASS res_tiles bursts=%0d beats=%0d cycles=%0d request_to_chain=19 request_to_output=21",burst,er,c);$finish;
 end
endmodule
