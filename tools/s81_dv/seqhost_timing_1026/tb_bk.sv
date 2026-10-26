`timescale 1ns/1ps
module tb_bk_timing;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0;reg[275:0]vi_n=0;wire[275:0]vo_s;wire fault;
 dsdv_bk_sel_vmtx #(.TX_SRAM(1)) dut(.clk(clk),.rst_n(rst_n),.tap_k(8'h11),.sink_k(8'h10),.ik(3'd4),.ek(3'd5),
 .uid(8'h5B),.eg_n(1'b0),.vi_s(276'd0),.vi_n(vi_n),.vo_s(vo_s),.vi_idx(276'd0),.ca(276'd0),.cb(276'd0),.tpn_i(276'd0),.fault(fault));
 integer cyc=0,sent=0,seen=0,errors=0,mut_payload=0;reg[275:0]exp[0:31];integer edges[0:31];
 always @(posedge clk)begin
  cyc=cyc+1;
  if(rst_n&&vi_n[0])begin edges[sent]=cyc;exp[sent]=vi_n;sent=sent+1;end
  #0.01;
  if(rst_n&&vo_s[0])begin
   if(seen>=sent||vo_s!==(exp[seen]^(mut_payload?276'd1<<100:276'd0)))errors=errors+1;
   $display("BK_OUT item=%0d input_edge=%0d output_edge=%0d edge_delta=%0d word=%h",seen,edges[seen],cyc,cyc-edges[seen],vo_s);seen=seen+1;
  end
  if(rst_n&&cyc>40&&fault)begin errors=errors+1;if(errors<4)$display("BK_FAULT edge=%0d",cyc);end
 end
 integer i,j;
 initial begin
  if($value$plusargs("mut_payload=%d",mut_payload))begin end
  repeat(25)@(negedge clk);rst_n=1;repeat(25)@(negedge clk);
  for(i=0;i<32;i=i+1)begin
   vi_n=0;vi_n[0]=1;vi_n[3:1]=0;vi_n[12:9]=i%16;vi_n[21+:16]=16'hA5A5;
   vi_n[47+:160]={32'h12345678+i,64'habcdef0123456789,64'h0706050403020100+i};
   @(negedge clk);vi_n=0;for(j=0;j<i%3+2;j=j+1)@(negedge clk);
  end
  repeat(25)@(negedge clk);
  if(sent!=32||seen!=32)errors=errors+1;
  $display("BK_TIMING sent=%0d seen=%0d errors=%0d",sent,seen,errors);if(errors==0)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
