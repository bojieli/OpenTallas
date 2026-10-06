`timescale 1ns/1ps
module tb_native_functions;
 reg clk=0;always #5 clk=~clk;
 reg [3:0] rn=0;
 reg q=0,mv=0;wire mr,mclk;
 reg [2062:0] md;reg [191:0] mo;
 wire [2:0] ov;reg [2:0] ore=0,av=0;reg [575:0] ao=0;
 wire [6188:0] od;wire [575:0] oo;
 wire rel,drain,pause,fault;
 ot_hbm_native_station #(.MODE(1),.ENABLE(1),.W(2063),.IW(2063),.NO(3)) m(
  .fclk_i(clk),.rst_n(rn),.i_v(1'b0),.i_d(2063'b0),.fclk_o(mclk),.o_v(),.o_d(),
  .quiesce(q),.in_v(mv),.in_r(mr),.in_data(md),.in_owner(mo),
  .out_v(ov),.out_r(ore),.out_data(od),.out_owner(oo),
  .ACK_v(av),.ACK_owner(ao),.source_release(rel),.drained(drain),.paused(pause),.fault(fault));
 reg [7:0] gv=0;wire [7:0] gr;reg [2159:0] gd=0;reg [1535:0] go=0;
 wire gov;reg gor=0;wire [2159:0] god;wire [191:0] goo;
 wire grel,gdr,gpause,gfault;
 ot_hbm_native_station #(.MODE(2),.ENABLE(1),.W(2160),.IW(270),.NI(8)) g(
  .fclk_i(clk),.rst_n(rn),.i_v(1'b0),.i_d(2160'b0),.fclk_o(),.o_v(),.o_d(),
  .quiesce(q),.in_v(gv),.in_r(gr),.in_data(gd),.in_owner(go),
  .out_v(gov),.out_r(gor),.out_data(god),.out_owner(goo),
  .ACK_v(1'b0),.ACK_owner(192'b0),.source_release(grel),.drained(gdr),.paused(gpause),.fault(gfault));
 reg [31:0] rng=32'h1062026;
 function automatic [31:0] next(input [31:0] n);
  reg [31:0] x;begin x=n^(n<<13);x=x^(x>>17);next=x^(x<<5);end
 endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task cold;begin @(negedge clk);rn=0;mv=0;gv=0;ore=0;av=0;gor=0;q=0;repeat(3)tick();@(negedge clk);rn=15;repeat(2)tick();end endtask
 integer accepts[0:2];integer releases=0,gaccepts=0;reg count_on=0;
 always @(posedge clk)if(count_on)begin
  for(integer k=0;k<3;k=k+1)if(ov[k]&&ore[k])begin
   if(od[k*2063+:2063]!==md||oo[k*192+:192]!==mo)$fatal(1,"mcast payload/owner mismatch");
   accepts[k]=accepts[k]+1;
  end
  if(rel)releases=releases+1;
  if(gov&&gor)begin
   if(god!==gd||goo!==go[191:0])$fatal(1,"ordered gather golden mismatch");
   gaccepts=gaccepts+1;
  end
 end
 initial begin
  for(integer k=0;k<3;k=k+1)accepts[k]=0;
  md=0;mo=192'h55aa123456789abcdef0;
  for(integer k=0;k<2063;k=k+1)begin rng=next(rng);md[k]=rng[0];end
  for(integer k=0;k<8;k=k+1)begin
   go[k*192+:192]=192'h1234feed;
   gd[k*270+:270]={1'b0,1'b1,12'h37,256'(k+1)*256'h123456789abcdef};
  end
  cold();count_on=1;
  @(negedge clk);mv=1;gv=8'h81;
  tick();@(negedge clk);mv=0;gv=0;
  repeat(3)tick();
  if(!ov||drain||gov)$fatal(1,"publication/partial gather permissions");
  // Real input-bank CE while held. CE must suppress permissions, repair the
  // existing coded seat, preserve ownership, then re-publish the same payload.
  @(negedge clk);m.held.inputs[0].u_cut.u_state.code[0]=m.held.inputs[0].u_cut.u_state.code[0]^72'b1;
  #1;if(!pause||ov||fault)$fatal(1,"CE must pause without false UE");
  repeat(8)tick();
  if(fault||!ov||od[2062:0]!==md)$fatal(1,"CE repair changed held payload");
  // Quiesce stops new acceptances but cannot retire stalled ownership.
  @(negedge clk);q=1;
  repeat(5)tick();if(mr||drain||rel||!ov)$fatal(1,"quiesce fabricated drain/release");
  @(negedge clk);q=0;gv=8'h7e;
  tick();@(negedge clk);gv=0;
  repeat(3)tick();if(!gov||gdr||god!==gd)$fatal(1,"full-width join not held exact");
  repeat(12)begin
   @(negedge clk);rng=next(rng);ore=rng[2:0];tick();
  end
  for(integer k=0;k<3;k=k+1)if(accepts[k]!=1)$fatal(1,"tap duplicate/lost under backpressure");
  if(rel||drain)$fatal(1,"accepted taps are not reverse ACKs");
  @(negedge clk);ore=0;gor=1;
  tick();@(negedge clk);gor=0;
  if(gaccepts!=1)$fatal(1,"join retirement count");
  // Corrupt a real owner data bit while all branches await reverse ACK.
  // Receipt storage must retain ACK0 across the five-edge payload repair.
  @(negedge clk);m.held.inputs[0].u_cut.u_state.code[32]=m.held.inputs[0].u_cut.u_state.code[32]^72'b100;
  for(integer k=0;k<3;k=k+1)begin
   @(negedge clk);av=3'b1<<k;ao[k*192+:192]=mo;
   tick();@(negedge clk);av=0;tick();
  end
  repeat(8)tick();if(releases!=1||!drain||!gdr||fault||gfault)$fatal(1,"finite ownership release");
  $display("PASS held fullshape mcast2063x3/gather270x8 seed1062026; each tap once, one source release, atomic join, quiesce, real CE repair");
  // Real wrong-owner reverse ACK: no source release; sticky permission fault.
  count_on=0;cold();@(negedge clk);mv=1;tick();@(negedge clk);mv=0;
  repeat(3)tick();@(negedge clk);ore=1;tick();@(negedge clk);ore=0;av=1;ao[191:0]=mo^192'b1;
  #1;if(!fault||rel||ov||mr)$fatal(1,"wrong-owner ACK was authorized");
  tick();@(negedge clk);av=0;tick();if(!fault||drain)$fatal(1,"wrong-owner fault lost debt");
  $display("PASS negative actual wrong-owner ACK rejected, debt retained");
  // Real checked permission-seat UE, not a callback/injected fault input.
  cold();@(negedge clk);gv=255;tick();@(negedge clk);gv=0;repeat(3)tick();
  @(negedge clk);g.held.u_permissions.code[0]=g.held.u_permissions.code[0]^72'b11;
  #1;if(!gfault||gov||gr||grel||gdr)$fatal(1,"permission UE allowed consumption");
  repeat(3)tick();if(!gfault)$fatal(1,"permission UE not sticky");
  $display("PASS negative actual permission UE rejected with no retire/reset credit");
  $finish;
 end
endmodule
