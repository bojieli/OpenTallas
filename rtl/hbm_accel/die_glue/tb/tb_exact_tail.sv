`timescale 1ns/1ps
module tail_rly_pair #(parameter integer W=1)(input wire ck, rs, input wire [623:0] data);
  wire [623:0] old;
  wire [W-1:0] narrow;
`ifdef MUT_NO_RELAY
  localparam integer KEEP_RESET = 0;
`else
  localparam integer KEEP_RESET = 1;
`endif
  ot_hbm_rly #(.W(624)) a (.ck(ck),.rs(rs),.i(data),.o(old));
  ot_hbm_rly #(.W(W),.RS_RELAY(KEEP_RESET)) b (.ck(ck),.rs(rs),.i(data[W-1:0]),.o(narrow));
  always @(negedge ck or negedge rs) begin
    #0.001;
    if (old[W-1:0] !== narrow) $fatal(1,"TAIL_RESET_OR_DATA_MISMATCH W=%0d",W);
  end
endmodule

module tb_exact_tail;
  reg ck=0, enable=1, rs=1;
  reg [623:0] data='1;
  always #0.4 if(enable) ck=~ck;
  tail_rly_pair #(.W(1)) p1(ck,rs,data);
  tail_rly_pair #(.W(255)) p255(ck,rs,data);
  tail_rly_pair #(.W(256)) p256(ck,rs,data);
  tail_rly_pair #(.W(257)) p257(ck,rs,data);
  tail_rly_pair #(.W(623)) p623(ck,rs,data);
  wire [407:0] wide_fork;
  wire [50:0] tail_fork;
  wire [2:0] ew,et,cw,ct;
  ot_hbm_lane_stf #(.W(136),.N(3),.FIRST(0)) lf (.ck(ck),.en(rs),.a(data[135:0]),.b(wide_fork),.eb(ew),.ck_o(cw));
  ot_hbm_lane_stf #(.W(17),.N(3),.FIRST(0)) lt (.ck(ck),.en(rs),.a(data[16:0]),.b(tail_fork),.eb(et),.ck_o(ct));
  wire [623:0] wide_land;
  wire [103:0] tail_land;
  wire fw,ft;
  ot_qfd_land #(.W(624),.D(4),.FIRST(0)) lw (.ckf(cw[0]),.ea(ew[0]),.i(data),.ck(ck),.rs(rs),.k(3'd2),.o(wide_land),.fault(fw));
  ot_qfd_land #(.W(104),.D(4),.FIRST(0)) ln (.ckf(ct[0]),.ea(et[0]),.i(data[103:0]),.ck(ck),.rs(rs),.k(3'd2),.o(tail_land),.fault(ft));
  integer checks=0;
  always @(negedge ck) begin
    #0.002;
    if ({wide_fork[16:0],wide_fork[152:136],wide_fork[288:272],ew,cw} !== {tail_fork[16:0],tail_fork[33:17],tail_fork[50:34],et,ct})
      $fatal(1,"TAIL_FORK_DATA_EPOCH_CLOCK_MISMATCH");
    if ({wide_land[103:0],fw} !== {tail_land,ft}) $fatal(1,"TAIL_LANDING_DATA_OR_FAULT_MISMATCH");
    checks=checks+1;
  end
  initial begin
    #0.1;rs=0;
    #2;rs=1;
    repeat(80) begin @(negedge ck);#0.05;data={data[622:0],data[623]^data[620]^1'b1}; end
    // Assertion while the clock is stopped must retain identical behaviour.
    @(negedge ck);#0.05;enable=0;#1;rs=0;#1;rs=1;#2;enable=1;
    repeat(24) @(negedge ck);
    #0.1;$display("EXACT_TAIL_NATIVE_PASS checks=%0d",checks);$finish;
  end
endmodule
