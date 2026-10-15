`timescale 1ns/1ps
module tb_static_pinreg_endpoint_transport;
 parameter integer MUT=0,N=300;
 localparam integer PW=612,W=487,STOP=17+(613*N)/487+20;
 reg clk=0,rst_n=0,epoch_begin=0,wr=0,rd=0,expect_v=0;
 reg [15:0] ws=0,rs=0,es=0;
 reg [544:0] wd=0;
 wire tv,recv_v,abort_a,abort_b,retry_a,retry_b;
 wire [611:0] tf,rf;
 wire [544:0] recv_data;
 wire [10:0] ca,cb;
 wire txword_v,rxframe_v,txdue,fault_tx,fault_rx;
 wire [486:0] txword;
 wire [611:0] rxframe;
 reg [2:0] vp=0;
 reg [1460:0] word_pipe=0;
 reg slot_v=0,txstart=0,rxstart=0;
 integer cycle,checks=0,errors=0,aborts=0,tfaults=0,seqw,seqr,seqe;
 reg want_v;reg [544:0] want_data;
 function automatic integer valid_slot(input integer j);
  valid_slot=(j%7!=3 && j%11!=8);
 endfunction
 function automatic [544:0] payload(input integer seq);
  reg [31:0] x;begin x=32'h471abd09^(seq*32'h9e3779b9);
  for(integer k=0;k<545;k=k+1)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);payload[k]=x[0];end
  end
 endfunction
 always @(posedge clk)begin
  vp<={vp[1:0],txword_v};word_pipe<={word_pipe[973:0],txword};
 end
 wire [486:0] incoming_word=word_pipe[1460:974] ^ ((MUT==3 && cycle==21)?487'd1:487'd0);
 ot_hgi_coll_static_link_pinreg a(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h72),
 .wr_v(wr),.wr_observed_v(wr),.wr_seq(ws),.wr_flit(wd),.rd_v(rd),.rd_seq(rs),
 .rx_expect_v(1'b0),.rx_expect_seq(16'b0),.phy_up(!(MUT==4&&cycle==16)),
 .tx_pin_v(tv),.tx_pin_flit(tf),.rx_pin_v(1'b0),.rx_pin_flit(612'b0),
 .rx_v(),.rx_flit(),.epoch_abort(abort_a),.retry_requested(retry_a),.fault_cause(ca));
 ot_hbm_static_frame_transport tx(.clk(clk),.rst_n(rst_n),.tx_start(txstart),.rx_start(1'b0),
 .tx_slot_v(slot_v),.endpoint_tx_v(tv ^ (MUT==1 && cycle==23)),.endpoint_tx_frame(tf),
 .expected_tx_slot(txdue),.transport_tx_v(txword_v),.transport_tx_word(txword),
 .transport_rx_v(1'b0),.transport_rx_word(487'b0),.endpoint_rx_v(),.endpoint_rx_frame(),.fault(fault_tx));
 ot_hbm_static_frame_transport rx(.clk(clk),.rst_n(rst_n),.tx_start(1'b0),.rx_start(rxstart),
 .tx_slot_v(1'b0),.endpoint_tx_v(1'b0),.endpoint_tx_frame(612'b0),.expected_tx_slot(),.transport_tx_v(),.transport_tx_word(),
 .transport_rx_v(vp[2] && !(MUT==2&&cycle==21)),.transport_rx_word(incoming_word),
 .endpoint_rx_v(rxframe_v),.endpoint_rx_frame(rxframe),.fault(fault_rx));
 ot_hgi_coll_static_link_pinreg b(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h72),
 .wr_v(1'b0),.wr_observed_v(1'b0),.wr_seq(16'b0),.wr_flit(545'b0),.rd_v(1'b0),.rd_seq(16'b0),
 .rx_expect_v(expect_v),.rx_expect_seq(es),.phy_up(1'b1),.tx_pin_v(),.tx_pin_flit(),
 .rx_pin_v(rxframe_v),.rx_pin_flit(rxframe),.rx_v(recv_v),.rx_flit(recv_data),.epoch_abort(abort_b),.retry_requested(retry_b),.fault_cause(cb));
 initial begin
  for(cycle=0;cycle<STOP;cycle=cycle+1)begin
   rst_n=cycle>=4;epoch_begin=cycle==6;txstart=cycle==16;rxstart=cycle==20;
   wr=0;rd=0;expect_v=0;want_v=0;slot_v=0;seqw=0;seqr=0;seqe=0;
   // Static unbounded gearbox slots after payload end still carry genuine idle.
   for(integer j=0;j<STOP;j=j+1)begin
    if(cycle==17+(613*j)/487)slot_v=1;
   end
   for(integer j=0;j<N;j=j+1)begin
    if(valid_slot(j))begin
     if(cycle==7+(613*j)/487)begin wr=1;ws=16'(seqw);wd=payload(seqw);end
     if(cycle==11+(613*j)/487)begin rd=1;rs=16'(seqr);end
     if(cycle==23+((613*(j+1)+486)/487)-1)begin expect_v=1;es=16'(seqe);end
     if(cycle==24+((613*(j+1)+486)/487)-1)begin want_v=1;want_data=payload(seqe);end
     seqw=seqw+1;seqr=seqr+1;seqe=seqe+1;
    end
   end
   #5;clk=1;#1;
   if(rst_n)begin
    if(abort_a||abort_b)aborts=aborts+1;
    if(fault_tx||fault_rx)tfaults=tfaults+1;
    if(recv_v!==want_v)errors=errors+1;
    if(want_v)begin checks=checks+1;if(recv_data!==want_data)errors=errors+1;end
    if(MUT==0&&(abort_a||abort_b||fault_tx||fault_rx))begin errors=errors+1;if(errors<8)$display("fault cycle%0d cause%h/%h transport%b/%b",cycle,ca,cb,fault_tx,fault_rx);end
   end
   #4;clk=0;
  end
  if(MUT==0)begin
   if(errors||aborts||tfaults)$fatal(1,"PINREG_TRANSPORT FAIL errors%0d aborts%0d tfaults%0d causes%h/%h",errors,aborts,tfaults,ca,cb);
   $display("PINREG_TRANSPORT PASS slots%0d checks%0d wire613 word487 TX5 RX1 flightwords3",N,checks);
  end else begin
   if(MUT==2 && !fault_rx)$fatal(1,"missingword undetected");
   if(MUT==1 && !cb[2])$fatal(1,"validflip missing expected-frame fault");
   if(MUT==3 && !cb[0])$fatal(1,"word corruption missing CRC fault");
   if(MUT==4 && !ca[4])$fatal(1,"PHY-down missing epoch abort fault");
   if(MUT!=2 && !(abort_a||abort_b))$fatal(1,"endpoint mutant undetected%0d",MUT);
   $display("PINREG_TRANSPORT MUTANT PASS m%0d errors%0d abortcycles%0d transportfaults%0d causes%h/%h",MUT,errors,aborts,tfaults,ca,cb);
  end
  $finish;
 end
endmodule
