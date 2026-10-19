`timescale 1ps/1ps
module tb_svg_return_regional;
 parameter integer MUT=0;
 reg cache_clk=0;wire [3:0] pair_clk,return_clk;
 always #417 cache_clk=~cache_clk;
 genvar c;generate for(c=0;c<4;c=c+1)begin:g_clk
  reg clk=0;initial begin #(c*10);forever #417 clk=~clk;end
  reg rclk=0;initial begin #(40+c*10);forever #417 rclk=~rclk;end
  assign pair_clk[c]=clk;assign return_clk[c]=rclk;
 end endgenerate
 reg [3:0] pair_rst_n=0,return_rst_n=0;reg cache_rst_n=0;
 reg [2047:0] bank_data=0;reg [11:0] in_ordinal=0;reg [3:0] in_valid=0;
 wire [1023:0] out_data;wire [2:0] out_ordinal;wire out_valid,fault;
 ot_hbm_svg_return_regional #(.MUT(MUT)) dut(.*);
 integer errors=0,outputs=0,tick=0,release_edge=0,first_valid=0,warm_checks=0;
 integer round=0,n=0,b=0,k=0,i=0,tag=0,sweep=0,window_start=0,windows=0;
 integer driver_full=0,driver_sweep=0,driver_round=0,driver_launch=0,latency_min=999999,latency_max=0,latency_samples=0;
 reg check_nominal=1,phase_seen=0;
 reg [1023:0] gold[0:6];reg [2:0] gold_ord[0:6];reg [6:0] gold_v=0;
 integer gold_full[0:6],gold_sweep[0:6],gold_launch[0:6];
 function automatic [255:0] pattern(input integer bank,full,epoch);
  begin pattern={32'(bank),32'(full),32'(epoch),32'(bank+full*17),32'(full^32'hdeadbeef),32'(epoch*271+bank),32'(full*8+bank),32'(epoch^full^bank)};end
 endfunction
 task drive(input integer full,v,sw);
  begin
   driver_full=full;driver_sweep=sw;driver_launch=tick;
   in_ordinal={4{3'(full)}};in_valid=v?4'b1111:0;
   for(b=0;b<8;b=b+1)bank_data[b*256+:256]=pattern(b,full,round);
  end
 endtask
 always @(posedge cache_clk)begin
  tick=tick+1;
  if(!cache_rst_n)begin gold_v=0;release_edge=0;first_valid=0;end
  else begin
   release_edge=release_edge+1;
   for(i=6;i>0;i=i-1)begin
    gold[i]=gold[i-1];gold_ord[i]=gold_ord[i-1];gold_v[i]=gold_v[i-1];
    gold_full[i]=gold_full[i-1];gold_sweep[i]=gold_sweep[i-1];gold_launch[i]=gold_launch[i-1];
   end
   for(k=0;k<4;k=k+1)gold[0][k*256+:256]=bank_data[((in_ordinal[2:0]+k)%8)*256+:256];
   gold_ord[0]=in_ordinal[2:0];gold_v[0]=(release_edge>=3)&&(&in_valid);
   gold_full[0]=driver_full;gold_sweep[0]=driver_sweep;gold_launch[0]=driver_launch;
  end
  #80;
  if(check_nominal)begin
   if(out_valid!==gold_v[6])begin errors=errors+1;if(errors<8)$display("RETURN_VALID_FAIL tick=%0d got=%b expected=%b",tick,out_valid,gold_v[6]);end
   if(out_valid)begin
    outputs=outputs+1;latency_samples=latency_samples+1;
    if(tick-gold_launch[6]<latency_min)latency_min=tick-gold_launch[6];
    if(tick-gold_launch[6]>latency_max)latency_max=tick-gold_launch[6];
    if(tick-gold_launch[6]!=7)begin errors=errors+1;if(errors<8)$display("RETURN_LATENCY_FAIL edges=%0d",tick-gold_launch[6]);end
    if(!first_valid)begin
     first_valid=release_edge;warm_checks=warm_checks+1;
     $display("RESET_WARM edge=%0d expected=9",first_valid);
     if(first_valid!=9)begin errors=errors+1;if(errors<8)$display("RESET_WARM_FAIL");end
    end
    if(out_data!==gold[6]||out_ordinal!==gold_ord[6])begin
     errors=errors+1;if(errors<8)$display("RETURN_DATA_FAIL ordinal=%0d expected=%0d full=%0d",out_ordinal,gold_ord[6],gold_full[6]);
    end
    if(gold_sweep[6]==0&&gold_full[6]==64)window_start=tick;
    if(gold_sweep[6]==0&&gold_full[6]==127)begin
     windows=windows+1;$display("RETURN_SUSTAIN window=%0d groups=64 cache_edges=%0d bytes_per_edge=128",windows,tick-window_start+1);
     if(tick-window_start!=63)errors=errors+1;
    end
   end
   if(fault)begin errors=errors+1;if(errors<8)$display("RETURN_FAULT_FAIL");end
   if((|dut.phase_fault)&&!phase_seen)begin phase_seen=1;errors=errors+1;$display("RING_PHASE_FAIL phase_fault=%b",dut.phase_fault);end
  end
 end
 initial begin
  for(round=0;round<3;round=round+1)begin
   pair_rst_n=0;return_rst_n=0;cache_rst_n=0;in_valid=0;
   repeat(5)@(negedge cache_clk);
   drive(0,1,0);pair_rst_n=15;return_rst_n=15;cache_rst_n=1;
   repeat(2)@(negedge cache_clk);
   for(n=0;n<272;n=n+1)begin drive(n,1,0);@(negedge cache_clk);end
   for(n=0;n<272;n=n+1)begin
    if(n%5==0)begin drive(511-n,0,1);@(negedge cache_clk);end
    if(n%13==0)begin drive(789-n,0,1);@(negedge cache_clk);end
    drive(n,1,1);@(negedge cache_clk);
   end
   drive(0,0,2);repeat(12)@(negedge cache_clk);
   if(round<2)begin
    // Occupied reset discards these three transactions before seven-stage return.
    for(n=0;n<3;n=n+1)begin drive(n+200,1,2);@(negedge cache_clk);end
   end
  end
  if(outputs!=1632||windows!=3||warm_checks!=3||latency_min!=7||latency_max!=7)begin errors=errors+1;$display("RETURN_COUNTS_FAIL outputs=%0d windows=%0d warm_checks=%0d",outputs,windows,warm_checks);end
  $display("RETURN_ROOTS pair_ps=0,10,20,30 return_ps=40,50,60,70 cache_ps=0 physical_stream_trees=9");
  $display("RETURN_LATENCY samples=%0d minimum_edges=%0d maximum_edges=%0d",latency_samples,latency_min,latency_max);
  // Deliberate ordinal disagreement must trip the cache slip guard.
  check_nominal=0;drive(5,1,3);in_ordinal[8:6]=2;@(negedge cache_clk);
  drive(0,0,3);repeat(12)@(negedge cache_clk);
  if(!fault)begin errors=errors+1;$display("ORDINAL_GUARD_FAIL");end
  $display("SVG_RETURN %s mut=%0d errors=%0d outputs=%0d windows=%0d warm_checks=%0d latency_stages=7",errors==0?"PASS":"FAIL",MUT,errors,outputs,windows,warm_checks);
  if(errors)$fatal(1,"regional return mismatch");$finish;
 end
endmodule
