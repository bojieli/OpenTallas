`timescale 1ns/1ps
module tb_hbm_svc_write_source #(parameter MUT=0,SA=1);
 reg ck=0;always #5 ck=~ck;reg fck=0;always #7 fck=~fck;
 reg rst=0;reg [291:0] wq=0;reg [1:0] source=0;reg [31:0] done=0;
 wire [15:0] legacygray;wire [31:0] kv,we,gray;wire [8191:0] wd;wire sf;integer expected[0:2];integer accepted=0,p,r,i;
 ot_hbm_svc_core #(.WB(1),.WB_SOURCE_ACK(SA),.XST(0),.WQ_ST(1)) dut(
 .ck(ck),.rst(rst),.q_d(336'b0),.q_v(8'b0),.q_fclk(8'b0),.e_d(128'b0),.e_fclk(1'b0),
 .k_v(kv),.k_rdy(32'hffffffff),.k_we(we),.k_wdata(wd),
 .kr_v(32'b0),.kr_tag(544'b0),.kr_beat(128'b0),.kr_data(8192'b0),
 .w_rdy(1'b1),.w_room(8'd64),.wr_v(8'b0),.wr_tag(80'b0),.wr_beat(40'b0),.wr_data(2048'b0),
 .wq_d(wq),.wq_fclk(fck),.wq_g(legacygray),.wq_source(MUT==1 ? 2'b0 : source),.wq_source_g(gray),.wq_source_fault(sf),.k_wr_done(done));
 function [7:0] bin(input [7:0] g);integer b;begin bin[7]=g[7];for(b=6;b>=0;b=b-1)bin[b]=bin[b+1]^g[b];end endfunction
 always @(posedge ck) if(rst) for(integer k=0;k<32;k=k+1) if(kv[k]&&we[k]) begin
  if(wd[256*k +: 32]!==accepted)$fatal(1,"payload source transport mismatch");accepted=accepted+1;
 end
 task tick;begin @(posedge ck);#1;end endtask
 initial begin
  expected[0]=0;expected[1]=0;expected[2]=0;#1;rst=0;repeat(3)tick;rst=1;repeat(12)tick;
  for(r=0;r<2;r=r+1)for(p=0;p<32;p=p+1) begin
   // Respect finite FIFO credit by allowing every previous packet to pop.
   @(posedge fck);#1;source=(p+r)%3;wq={224'b0,32'(32*r+p),30'(32*r+p),5'(p),1'b1};
   @(posedge fck);#1;wq[0]=0;
   while(bin(SA ? gray[7:0] : legacygray[7:0]) != 32*r+p+1)tick;
   while(accepted != 32*r+p+1)tick;
   expected[(p+r)%3]=expected[(p+r)%3]+1;
  end
  // Cross-PC reorder, while preserving each PC's command order.
  for(r=0;r<2;r=r+1)for(p=31;p>=0;p=p-1)begin
   @(negedge ck);done=32'b1<<p;tick;@(negedge ck);done=0;tick;
  end
  repeat(150)tick;
  if(SA) for(i=0;i<3;i=i+1)if(bin(gray[8+8*i +: 8])!=expected[i])$fatal(1,"source ACK attribution %0d got%0d expected%0d",i,bin(gray[8+8*i +: 8]),expected[i]);
  if(!SA && bin(legacygray[15:8])!=64)$fatal(1,"legacy ACK");
  if(SA && sf)$fatal(1,"ledger fault");
  $display("PASS 64 source-tagged core writes with reversed PC completions");$finish;
 end
 initial begin #1000000;$fatal(1,"watchdog");end
endmodule
