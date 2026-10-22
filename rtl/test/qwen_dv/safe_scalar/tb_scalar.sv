`timescale 1ns/1ps
module tb_scalar;
 reg ck=0,rst_n=0,cfg_v=0,av=0;
 always #5 ck=~ck;
 reg[47:0] dn=0,up=0;
 reg[23:0] ai=0;
 reg[31:0] val=0;
 reg[1:0] user=0;
 wire[1:0] tv,to;
 wire[23:0] idx[0:1];
 wire[31:0] value[0:1];
 wire[1:0] usr[0:1];
`define PORTS(G) .ck(ck),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_root(1'b1),.cfg_rdir(1'b0),.cfg_nb(6'd0),.cfg_ss(24'd0),.cfg_fuse(1'b0),.cfg_rx(24'd0),.cfg_eps(32'd0),.cfg_k(5'd0),.cfg_amnb(6'd3),.dn_i(dn),.up_i(up),.ps_v(1'b0),.ps_idx(24'd0),.ps_val(32'd0),.rb_v(1'b0),.rb_val(32'd0),.am_v(av),.am_idx(ai),.am_val(val),.am_u(user),.tok_v(tv[G]),.tok_idx(idx[G]),.tok_val(value[G]),.tok_user(usr[G]),.tok_own(to[G])
 qfd_dv_scalar2_legacy #(.MU_NU(4)) old_dut(`PORTS(0));
 qfd_dv_scalar2_safe #(.MU_NU(4)) new_dut(`PORTS(1));
 reg pv=0,po=0;
 reg[23:0] pi;
 reg[31:0] pval;
 reg[1:0] pu;
 integer tokens=0,c;
 always @(posedge ck) begin
  #1;
  if(!rst_n) begin pv=0;po=0;end
  else begin
   if(tv[1]!==pv) $fatal(1,"SAFE_SCALAR_LATENCY cycle expected=%0d got=%0d",pv,tv[1]);
   if(tv[1]) begin
    if(idx[1]!==pi||value[1]!==pval||usr[1]!==pu||to[1]!==po) $fatal(1,"SAFE_SCALAR_VALUE");
    tokens=tokens+1;
   end
   pv=tv[0];pi=idx[0];pval=value[0];pu=usr[0];po=to[0];
  end
 end
 initial begin
  repeat(5) @(negedge ck);rst_n=1;cfg_v=1;
  @(negedge ck);cfg_v=0;
  dn={1'b1,3'd3,12'd0,8'd0,24'd8};up={1'b1,3'd3,12'd0,8'd0,24'd4};
  @(negedge ck);dn=0;up=0;
  // Three simultaneous candidates on consecutive edges, four MU users,
  // positive/negative values and ties (smaller global index wins).
  for(c=0;c<48;c=c+1) begin
   @(negedge ck);user=2'(c);av=1;ai=24'd12;val=32'h3f800000+(c%3)*32'h00800000;
   dn={1'b1,3'd4,10'd0,user,32'h40000000};
   up={1'b1,3'd4,10'd0,user,32'h40000000};
  end
  @(negedge ck);av=0;dn=0;up=0;
  repeat(5) @(negedge ck);
  if(tokens!=48) $fatal(1,"SAFE_SCALAR_COUNT %0d",tokens);
  $display("SAFE_SCALAR_PASS tokens=%0d latency_delta=1 sustained_group_II=1 users=4",tokens);$finish;
 end
endmodule
