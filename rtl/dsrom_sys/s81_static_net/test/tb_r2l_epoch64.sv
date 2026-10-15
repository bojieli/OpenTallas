`timescale 1ps/1ps
module tb_r2l_epoch64 #(parameter integer WPH=0,RPH=0,MUT=0,STOP=0,NFRAME=256);
 localparam integer T=12; // normalized exact VCO ticks; frequency-independent functional test, physical API uses3.6GHz.
 reg wc=0,ec=0,rc=0,rst=0;reg [513:0] di=0;wire [514:0] actual,flat;
 integer wcycle=0,n,k,checks=0,errors=0,ai=-1,fi=-1;integer afirst=-1,ffirst=-1,alast=-1,flast=-1;
 reg [511:0] payload;reg valid_word;wire [7:0] epoch_clocks;reg epoch7=0;
 initial begin #(WPH*T);forever begin wc=1;#(3*T/2);wc=0;#(3*T/2);end end
 initial begin forever begin ec=1;#(6*T);ec=0;#(6*T);end end
 initial begin #(RPH*T);forever begin rc=1;#(2*T);rc=0;#(2*T);end end
 assign epoch_clocks={epoch7,{7{ec}}};
 always @(ec)begin epoch7=(STOP && $time>= (120+12*32)*T && $time<(120+12*33)*T)?1'b0:ec;end
 dsfd_r2l_epoch64 #(.MUT(MUT)) dut(.clk_source({8{wc}}),.clk_epoch(epoch_clocks),.clk_serial({9{rc}}),
  .rst_source_n({8{rst}}),.rst_epoch_n({8{rst}}),.rst_serial_n({8{rst}}),.di0(di),.o(actual));
 dsfd_r2l_vr_512x1__hcol original(.ck(rc),.fi0(wc),.rs(rst),.di0(di),.o(flat));
 function automatic [511:0] pattern(input integer idx);
  integer q;reg [511:0] z;
  begin for(q=0;q<8;q=q+1)z[64*q+:64]=64'h936da50100000000 ^ (64'h000034b500000000*q) ^ (64'h000000005bd1e995*idx);pattern=z;end
 endfunction
 function automatic expected_valid(input integer index);
  begin expected_valid=(index%11!=7);end
 endfunction
 always @(posedge wc)begin
  if(wcycle>=38 && wcycle<38+4*NFRAME)begin
   n=wcycle-38;k=3*(n/4)+(n%4);payload=pattern(k);
   valid_word=(n%4<3)?expected_valid(k):0;di<={payload,valid_word,1'b1};
  end else if(wcycle>=38+4*NFRAME)di<={512'd0,1'b0,1'b1};else di<=0;
  wcycle=wcycle+1;
 end
 always @(negedge rc)begin
  if(ai<0 && actual[513] && actual[512:1]===pattern(0))begin ai=0;afirst=$time/T-2;end
  if(fi<0 && flat[513] && flat[512:1]===pattern(0))begin fi=0;ffirst=$time/T-2;end
  if(ai>=0 && ai<3*NFRAME)begin
   checks=checks+1;
   if(actual[512:1]!==pattern(ai) || actual[0]!==expected_valid(ai) || actual[514]!==1'b0)begin
    errors=errors+1;if(errors<3)$display("EPOCH_MISMATCH w%0d r%0d idx%0d time%0d flags%h",WPH,RPH,ai,$time/T,actual[514:513]);
   end
   ai=ai+1;alast=$time/T-2;
  end
  if(fi>=0 && fi<3*NFRAME)begin
   checks=checks+1;
   if(flat[512:1]!==pattern(fi) || flat[0]!==expected_valid(fi) || flat[514]!==1'b0)begin
    errors=errors+1;if(errors<3)$display("REFERENCE_MISMATCH idx%0d",fi);
   end
   fi=fi+1;flast=$time/T-2;
  end
 end
 initial begin
  #(80*T);rst=1;#((120+12*NFRAME+80)*T-80*T);
  if(ai!=3*NFRAME || fi!=3*NFRAME || errors || checks!=6*NFRAME)
   $fatal(1,"R2L_EPOCH_FAIL WPH%0d RPH%0d actual%0d flat%0d checks%0d errors%0d",WPH,RPH,ai,fi,checks,errors);
  if(alast-afirst!=4*(3*NFRAME-1) || flast-ffirst!=4*(3*NFRAME-1))$fatal(1,"NONSTATIC_OUTPUT_SPAN");
  $display("R2L_EPOCH_PASS WPH%0d RPH%0d checks%0d frames%0d first%0d oldfirst%0d addedVCO%0d last%0d throughput3per12=1",WPH,RPH,checks,NFRAME,afirst,ffirst,afirst-ffirst,alast);$finish;
 end
endmodule
