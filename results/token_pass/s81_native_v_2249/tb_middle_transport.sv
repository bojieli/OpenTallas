`timescale 1ps/1fs
// Exact V-channel carve: the real five Gunit N2 pass cells + L2 JREG0
// stop; the BK entry relay + BK stop + real seqhost dsdv_sh_vc body.
// Inter-leaf bound station ages and controller injections are outside scope.
module tb_middle_transport;
  reg ck=0,rst_n=0;
  reg [275:0] va=0,vb=0,ea=0,eb=0;
  reg inject=0;
  wire [275:0] gn[0:6],gs[0:6];
  assign gn[0]=va; assign gs[6]=vb;
  wire gf;
  for(genvar j=0;j<6;j=j+1)begin:g_leaf
    if(j==2)begin:g_l2
      ot_dsdv_vstop #(.V(276),.JREG(0)) u_vs(.clk(ck),.rst_n(rst_n),
        .tap_k(8'ha0),.sink_k(8'ha0),.bk_uid(8'd0),
        .vi_s(gn[j]),.vo_n(gn[j+1]),.vi_n(gs[j+1]),.vo_s(gs[j]),
        .in_nv(inject),.in_n(276'd3),.in_sv(inject),.in_s(276'd3),
        .fault(gf),.dl_nv(),.dl_n(),.dl_sv(),.dl_s(),.ra_s(),.ra_n(),.dk_n(),.dk_s());
    end else begin:g_pass
      dsdv_gunit_pass #(.W(276),.N(2)) u_up(.clk(ck),.rst_n(rst_n),.d(gn[j]),.q(gn[j+1]));
      dsdv_gunit_pass #(.W(276),.N(2)) u_dn(.clk(ck),.rst_n(rst_n),.d(gs[j+1]),.q(gs[j]));
    end
  end
  wire [275:0] brn,brs,bkn,bks,bn,bs;
  dsfd_dvrly_276_SN u_rs(.ck(ck),.rs(rst_n),.i(va),.o(brn),.ck_o());
  dsfd_dvrly_276_NS u_rn(.ck(ck),.rs(rst_n),.i(bs),.o(brs),.ck_o());
  wire bkf,shf;
  ot_dsdv_vstop #(.V(276),.BK_DRAIN_SINK(1)) u_bk_vs(.clk(ck),.rst_n(rst_n),
    .tap_k(8'hff),.sink_k(8'hff),.bk_uid(8'd4),
    .vi_s(brn),.vo_n(bkn),.vi_n(brs),.vo_s(bks),
    .in_nv(1'b0),.in_n(276'd0),.in_sv(1'b0),.in_s(276'd0),
    .fault(bkf),.dl_nv(),.dl_n(),.dl_sv(),.dl_s(),.ra_s(),.ra_n(),.dk_n(),.dk_s());
  dsdv_sh_vc u_sh(.ck(ck),.rst_n(rst_n),.tap_k(8'hff),.sink_k(8'hff),
    .vi_s(bkn),.vo_n(bn),.vi_n(vb),.vo_s(bs),
    .tw_i(194'd0),.cn_i(85'd0),.cs_i(85'd0),.cf_i(267'd0),.cg_i(85'd0),
    .dn_o(),.vf_o(shf),.cw_v(),.cw_a(),.cw_d());
  // Reverse path: seqhost(2), BK N-entry relay(1), BK stop(2), total5.
  // Forward path: BK S-entry relay(1), BK stop(2), seqhost(2), total5.
  reg [275:0] pa[0:11],pb[0:11];
  reg [275:0] eg_a,eg_b,eb_a,eb_b;
  reg [63:0] rng=64'h123456789abcdef1;
  integer errors=0,checks=0,bad_payload=0,bad_age=0,cycle=0;
  reg check_on=0;
  function automatic [63:0] xs(input [63:0] x);
    reg[63:0]t;begin t=x^(x<<13);t=t^(t>>7);xs=t^(t<<17);end
  endfunction
  always #416.5 ck=~ck;
  task step(input bit active,input integer k);
    integer j;
    begin
      @(negedge ck);
      for(j=0;j<4;j=j+1)begin rng=xs(rng);ea[64*j+:64]=rng;
        rng=xs(rng);eb[64*j+:64]=rng;end
      rng=xs(rng);ea[275:256]=rng[19:0];rng=xs(rng);eb[275:256]=rng[19:0];
      ea[3:0]={3'd1,(active&&(k%4==0))};eb[3:0]={3'd2,(active&&(k%4==0))};
      va=ea;vb=eb;
      if(bad_payload&&active&&k==21)va[137]=~va[137];
      @(posedge ck);cycle=cycle+1;
      eg_a=pa[bad_age?9:10];eg_b=pb[bad_age?9:10];
      eb_a=pa[bad_age?2:3];eb_b=pb[bad_age?2:3];
      for(j=11;j>0;j=j-1)begin pa[j]=pa[j-1];pb[j]=pb[j-1];end
      pa[0]=ea;pb[0]=eb;
      #1;
      if(check_on&&k>=16)begin
        checks=checks+4;
        if(gn[6]!==eg_a)begin errors=errors+1;if(errors<6)$display("BAD G_N %0d",cycle);end
        if(gs[0]!==eg_b)begin errors=errors+1;if(errors<6)$display("BAD G_S %0d",cycle);end
        if(bn!==eb_a)begin errors=errors+1;if(errors<6)$display("BAD BKSH_N %0d",cycle);end
        if(bks!==eb_b)begin errors=errors+1;if(errors<6)$display("BAD BKSH_S %0d",cycle);end
        if(gf||bkf||shf)begin errors=errors+1;if(errors<6)$display("BAD fault %b%b%b",gf,bkf,shf);end
      end
    end
  endtask
  integer i,r;
  initial begin
    bad_payload=$test$plusargs("bad_payload");bad_age=$test$plusargs("bad_age");
    for(i=0;i<12;i=i+1)begin pa[i]=0;pb[i]=0;end
    for(r=0;r<2;r=r+1)begin
      rst_n=0;check_on=0;for(i=0;i<64;i=i+1)step(0,i);
      @(negedge ck);rst_n=1;for(i=0;i<32;i=i+1)step(0,i);
      check_on=1;for(i=0;i<256;i=i+1)step(1,i);
    end
    check_on=0;@(negedge ck);inject=1;
    for(i=0;i<12;i=i+1)step(1,i);
    if(!gf)begin errors=errors+1;$display("COLLISION_GUARD_NOT_CAUGHT");end
    $display("MIDDLE_NATIVE_V_TRANSPORT %s checks=%0d errors=%0d gunit_edges=12 bk_seqhost_edges=5 guard=%0d clock_ps=833",
      errors==0?"PASS":"FAIL",checks,errors,gf);
    if(errors)$fatal(1,"middle transport mismatch");$finish;
  end
endmodule
