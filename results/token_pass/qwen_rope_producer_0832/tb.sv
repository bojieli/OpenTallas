`timescale 1ns/1ps
module tb;
 reg ck=0; always #0.4165 ck=~ck;
 reg rst_n=0; reg[379:0]cmd=0;
 integer mut=0,cyc=0,first=-1,last=-1,n=0,reads=0,scales=0,errors=0;
 wire cr,sr,fault;wire[23:0]ca;wire[17:0]sa;wire[519:0]dr;
 reg[511:0]cq=0,lagcq=0;reg[15:0]sq=0;
 function automatic[511:0] value(input[23:0]a);
  reg[511:0]v;integer j;begin for(j=0;j<16;j++)v[j*32+:32]={8'd0,a}^(32'h9e3779b9*32'(j+1));return v;end
 endfunction
 qfd_native59_svc_obs1 #(.ROPE(1),.HEAD_PREP(1),.NU(4),.USER_BIND(1),.MCTX(1),.EMB_RELAY(1)) dut(
 .ck(ck),.rst_n(rst_n),.native_cmd(cmd),.native_token(18'd123),.native_position(18'd79),
 .host_epoch_valid(1'b0),.host_fused_capability(1'b0),.host_epoch(16'd0),.host_tag(59'd0),.host_generation(2'd0),
 .layer_context_v(1'b0),.command_stage(6'd0),.head_prepare_v(1'b0),.head_prepare_user(2'd0),.head_prepare_token(18'd0),.head_prepare_position(18'd0),
 .dd_i(548'd0),.kv_word_slot(1'b0),.kv_word_index(2'd0),.kv_x3_slot(1'b0),
 .qb_v(1'b0),.qb_beat(5'd0),.qb_row(512'd0),.qb_full(1'b0),.qb_committed(1'b0),.qb_bad(1'b0),
 .tx_user(2'd0),.rx_user(2'd0),.tx_slot(1'b0),.tx_slot_kind(4'd0),.tx_slot_beat(5'd0),
 .native_rx_v(1'b0),.native_rx_payload(548'd0),.rx_slot(1'b0),.rx_slot_kind(4'd0),.rx_slot_beat(5'd0),
 .emb_code_re(cr),.emb_code_addr(ca),.emb_scale_re(sr),.emb_scale_addr(sa),.emb_code_q(cq),.emb_scale_q(sq),
 .dr_o(dr),.visibility_slot(1'b0),.complete_slot(1'b0),.fault(fault));
 always @(posedge ck)begin
  if(cr)begin cq<=(mut==2)?lagcq:(value(ca)^(mut==1?512'd1:512'd0));lagcq<=value(ca);reads++;end
  if(sr)begin sq<=16'h3c42;scales++;if(sa!=18'd123)errors++;end
 end
 reg[511:0]want;integer idx;
 initial begin
  void'($value$plusargs("MUT=%d",mut));repeat(12)@(negedge ck);rst_n=1;repeat(12)@(negedge ck);
  for(cyc=0;cyc<1627;cyc++)begin
   if(cyc==0)cmd={4'hE,18'd123,358'd0};else cmd=0;
   @(negedge ck);
   if(dr[519])begin
    if(first<0)first=cyc;last=cyc;
    idx=n<64?n:(n==64?0:n-65);
    want=n<64?value(24'(123*64+n)):(n==64?{496'd0,16'h3c42}:value(24'(9723904+123*8+n-65)));
    if(dr[518]!=1||dr[517:512]!=6'(idx)||dr[511:0]!==want)begin
     errors++;if(errors<4)$display("MISM n%0d edge%0d got%h want%h",n,cyc,dr,want);
    end
    n++;
   end
  end
  if(fault||n!=73||reads!=72||scales!=1||errors||last>=1627)$fatal(1,"ROPE_PRODUCER_FAIL mutant%0d words%0d reads%0d scales%0d first%0d last%0d errors%0d fault%0d",mut,n,reads,scales,first,last,errors,fault);
  $display("ROPE_PRODUCER_PASS words%0d reads%0d scales%0d first%0d last%0d window1627 spare%0d",n,reads,scales,first,last,1626-last);$finish;
 end
endmodule
