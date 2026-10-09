`timescale 1ns/1ps
module tb_qwen_r25_causal_mask_pipe #(parameter OWNER_W=73);
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0,in_v=0,out_rdy=0;
 reg [1:0] in_checked=3;
 reg [OWNER_W-1:0] in_owner=0;
 reg [79:0] in_query_positions=0;
 reg [2:0] in_queries=4;
 reg [19:0] in_row0=0;
 wire in_rdy,out_v,fault;wire [OWNER_W-1:0] out_owner;
 wire [19:0] out_row0;wire [83:0] out_valid_lengths;wire [127:0] out_live;
 ot_qwen_r25_causal_mask_pipe #(.ENABLE(1),.CAPACITY(8224),.OWNER_W(OWNER_W)) dut(.*);
 integer block_id,q,r,checks=0,mutant_leaks=0;
 integer value,a,b,byte_checks=0;reg [12:0] code8;reg [9:0] decoded8;
 reg [127:0] expected,held;
 task reset;
  begin
   @(negedge clk);rst_n=0;in_v=0;out_rdy=0;in_checked=3;in_queries=4;
   for(q=0;q<4;q=q+1)in_query_positions[q*20+:20]=8191+q;
   repeat(3)@(negedge clk);rst_n=1;
  end
 endtask
 task accept_frame(input integer row0,input integer owner_id);
  begin
   @(negedge clk);in_row0=row0;in_owner={{(OWNER_W-64){1'b1}},64'h123456789abc0000}+owner_id;in_v=1;
   do @(posedge clk);while(!in_rdy);
   @(negedge clk);in_v=0;
   if(!fault)begin wait(out_v);@(negedge clk);end
  end
 endtask
 initial begin
  reset();
  // Independent corruption oracle: all bytes, all single and double bit flips.
  for(value=0;value<256;value=value+1)begin
   code8=dut.enabled.enc8(value[7:0]);decoded8=dut.enabled.dec8(code8);
   if(decoded8!=={2'b00,value[7:0]})$fatal(1,"SECDED8 clean byte");
   byte_checks=byte_checks+1;
   for(a=0;a<13;a=a+1)begin
    decoded8=dut.enabled.dec8(code8^(13'd1<<a));
    if(decoded8!=={2'b01,value[7:0]})$fatal(1,"SECDED8 single bit");
    byte_checks=byte_checks+1;
    for(b=a+1;b<13;b=b+1)begin
     decoded8=dut.enabled.dec8(code8^(13'd1<<a)^(13'd1<<b));
     if(!decoded8[9]||decoded8[8])$fatal(1,"SECDED8 double bit");
     byte_checks=byte_checks+1;
    end
   end
  end
  $display("PASS_SECDED8_EXHAUSTIVE checks%0d",byte_checks);
  for(block_id=0;block_id<257;block_id=block_id+1)begin
   accept_frame(block_id*32,block_id);
   expected=0;
   for(q=0;q<4;q=q+1)begin
    if(out_valid_lengths[q*21+:21]!==8192+q)$fatal(1,"query length truncated");
    for(r=0;r<32;r=r+1)begin
     expected[q*32+r]=(block_id*32+r)<8192+q;
     if(((block_id*32+r)<8195)!=expected[q*32+r])mutant_leaks=mutant_leaks+1;
     checks=checks+1;
    end
   end
   if(fault||!out_v||out_live!==expected||out_row0!==block_id*32||out_owner!==in_owner)
    $fatal(1,"full p4 mask/owner mismatch group%0d",block_id);
   held=out_live;
   repeat(3)begin @(negedge clk);if(out_live!==held||!out_v)$fatal(1,"held frame changed");end
   out_rdy=1;@(negedge clk);out_rdy=0;
  end
  if(mutant_leaks!=6)$fatal(1,"shared latest-query limit negative control vacuous");
  // A real transient byte error must be corrected or fence the held frame.
  accept_frame(8192,299);held=out_live;
  @(negedge clk);dut.enabled.pbyte[0]=dut.enabled.pbyte[0]^13'd4;
  #0.01;if(fault||out_live!==held||!out_v)$fatal(1,"transient data CE");
  dut.enabled.pbyte[0]=dut.enabled.pbyte[0]^13'd8;
  #0.01;if(!fault||out_v||in_rdy)$fatal(1,"transient data UE admitted");
  reset();
  // Correctable mutable-mask upset preserves every output bit.
  accept_frame(8192,300);
  held=out_live;
  @(negedge clk);dut.enabled.seat[0]=dut.enabled.seat[0]^72'd4;
  #0.01;if(fault||out_live!==held||!out_v)$fatal(1,"CE correction lost exact mask");
  // Two independent bit flips must suppress visibility and fence the frame.
  dut.enabled.seat[0]=dut.enabled.seat[0]^72'd8;
  #0.01;if(!fault||out_v||in_rdy)$fatal(1,"UE mask admitted");
  reset();in_query_positions[39:20]=20'd0;
  accept_frame(8192,301);
  if(!fault||out_v)$fatal(1,"13-bit position truncation mutant admitted");
  reset();in_checked=1;
  accept_frame(8192,302);
  if(!fault||out_v)$fatal(1,"unchecked owner admitted");
  reset();in_queries=1;in_query_positions[19:0]=8224;
  accept_frame(8192,303);
  if(!fault||out_v)$fatal(1,"capacity overflow admitted");
  $display("PASS_QWEN_R25_P4_CAUSAL_MASK_PIPE capacity8224 groups257 query_positions8191_8194 lengths8192_8195 checks%0d shared_limit_leaks%0d held_frames CE UE truncation checked_owner capacity_negative",checks,mutant_leaks);
  $finish;
 end
endmodule
