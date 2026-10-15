`timescale 1ns/1ps
module tb_stepped_frame_bits;
 parameter integer MUT=0;
 reg clk=0,rst_n=0;always #5 clk=~clk;
 integer c=0,jtx=0,checks=0,errors=0;
 reg ts=0,rs=0,txstep=0,rxstep=0,slot=0,valid=0;reg[611:0]frame=0;
 wire wv,rv,tf,rf;wire[486:0]word;wire[611:0]received;
 reg want=0,want_valid=0;reg[611:0]want_frame=0;
 function automatic integer T(input integer k);T=511+17*k/16;endfunction
 function automatic[611:0]pattern(input integer j);
  reg[31:0]x;begin x=32'h915ab246^(j*32'h9e3779b9);for(integer i=0;i<612;i=i+1)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);pattern[i]=x[0];end end
 endfunction
 ot_hbm_static_frame_transport_step tx(.clk(clk),.rst_n(rst_n),.tx_start(ts),.rx_start(1'b0),.tx_word_step(txstep),.rx_word_step(1'b0),
 .tx_slot_v(slot),.endpoint_tx_v(valid),.endpoint_tx_frame(frame),.expected_tx_slot(),.transport_tx_v(wv),.transport_tx_word(word),
 .transport_rx_v(1'b0),.transport_rx_word(487'b0),.endpoint_rx_v(),.endpoint_rx_frame(),.fault(tf));
 ot_hbm_static_frame_transport_step rx(.clk(clk),.rst_n(rst_n),.tx_start(1'b0),.rx_start(rs),.tx_word_step(1'b0),.rx_word_step(rxstep),
 .tx_slot_v(1'b0),.endpoint_tx_v(1'b0),.endpoint_tx_frame(612'b0),.expected_tx_slot(),.transport_tx_v(),.transport_tx_word(),
 .transport_rx_v(wv && !(MUT==2&&c==512)),.transport_rx_word(word^((MUT==1&&c==512)?487'd1:487'd0)),
 .endpoint_rx_v(rv),.endpoint_rx_frame(received),.fault(rf));
 always @(negedge clk)begin
  rst_n=c>=8;ts=c+1==510;rs=c+1==511;slot=0;txstep=0;rxstep=0;want=0;
  for(integer k=0;k<2048;k=k+1)begin if(c+1==T(k))txstep=1;if(c+1==T(k)+1)rxstep=1;end
  for(integer j=0;j<1628;j=j+1)begin
   if(c+1==T(613*j/487))begin slot=1;valid=j%5!=3;frame=pattern(j);end
   if(j<1627 && c+1==T((613*(j+1)+486)/487-1)+2)begin want=1;want_valid=j%5!=3;want_frame=pattern(j);end
  end
 end
 always @(posedge clk)begin c=c+1;#1;
  if(want)begin checks=checks+1;if({rv,received}!=={want_valid,want_frame})errors=errors+1;end
  else if(rv)errors=errors+1;
  if(c==2700)begin
   if(MUT==0)begin
    if(errors||tf||rf||checks!=1627)$fatal(1,"STEP_BITS_FAIL checks%0d errors%0d fault%b%b",checks,errors,tf,rf);
    $display("STEP_BITS_PASS frames1627 all613bits997351 idlevalidpreserved wordpauses16of17 stoptail25bits");
   end else begin
    if(MUT==1&&errors==0)$fatal(1,"bitflip mutantescaped");
    if(MUT==2&&!rf)$fatal(1,"wordvalid mutantescaped");
    $display("STEP_BITS_MUTANT_REJECTED m%0d errors%0d fault%b%b",MUT,errors,tf,rf);
   end
   $finish;
  end
 end
endmodule
