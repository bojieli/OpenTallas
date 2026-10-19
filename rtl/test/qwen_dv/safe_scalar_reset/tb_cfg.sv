`timescale 1ns/1ps
module tb_cfg;
 reg ck=0,rst=0;always #5 ck=~ck;
 reg cfg=0;reg[23:0] ss=0;reg ps=0;
 wire fault;integer cycle=-1;integer early;
 initial early=$test$plusargs("EARLY");
 qfd_dv_scalar2 #(.MU_NU(4)) dut(.ck(ck),.rst_n(rst),.cfg_v(cfg),.cfg_root(1'b1),.cfg_rdir(1'b0),
 .cfg_nb(6'd32),.cfg_ss(ss),.cfg_fuse(1'b0),.cfg_rx(24'd91),.cfg_eps(32'h12345678),.cfg_k(5'd7),.cfg_amnb(6'd1),
 .dn_i(48'd0),.up_i(48'd0),.ps_v(ps),.ps_idx(24'd3),.ps_val(32'hdeadbeef),.rb_v(1'b0),.rb_val(32'd0),
 .am_v(1'b0),.am_idx(24'd0),.am_val(32'd0),.am_u(2'd0),.fault(fault));
 always @(negedge ck) begin
  rst=(cycle>=5);
  cfg=(cycle+1>=40&&cycle+1<=43);
  ss=24'(cycle+1);
  ps=(cycle+1==(early?44:46));
 end
 always @(posedge ck) begin
  cycle=cycle+1;#1;
  if(cycle>=42&&cycle<=45) begin
   if(dut.ss!==24'(cycle-2)||dut.nb!==6'd32||dut.eps!==32'h12345678||!dut.root)
    $fatal(1,"CFG_PAYLOAD_ALIGNMENT cycle%0d ss%0d",cycle,dut.ss);
  end
  if(cycle==47&&!early&&dut.s[3]!==32'hdeadbeef) $fatal(1,"CFG_GUARDED_WRITE_LOST %h",dut.s[3]);
  if(cycle==100) begin
   if(early) begin
    if(!fault) begin $display("CFG_EARLY_MUTANT_SURVIVED");$finish;end
    $fatal(1,"CFG_EARLY_WRITE_REJECTED expected mutant failure");
   end
   if(fault||dut.ss!==24'd43) $fatal(1,"CFG_BACK_TO_BACK_LOST_OR_FAULT");
   $display("SAFE_CFG PASS configs4 II1 acceptance+2 firstdata+3 exactslotwrite");$finish;
  end
 end
endmodule
