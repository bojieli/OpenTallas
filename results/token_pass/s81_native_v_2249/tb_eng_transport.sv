`timescale 1ps/1fs
module tb_eng_transport;
  reg ck=0, rst_n=0, own_v=0;
  reg [275:0] va=0,vb=0;
  reg [275:0] ea=0,eb=0;
  wire [275:0] oa,ob;
  wire fault;
  integer bad_payload=0,bad_age=0,checks=0,errors=0,cycle=0,phase=0,seed=7,collisions=0;
  reg [63:0] rng;
  reg [275:0] pa=0,pb=0,qa=0,qb=0;
  reg check_on=0;
  ot_s81eng_xq_n32 dut(.ck(ck),.rst_n(rst_n),.o_v(own_v),
    .o_col(5'd0),.o_beat(3'd1),.o_d(264'd0),
    .vi_a(va),.vo_a(oa),.vi_b(vb),.vo_b(ob),.fault(fault));
  always #416.5 ck=~ck;
  function automatic [63:0] xs(input [63:0] x);
    reg [63:0] t;
    begin t=x^(x<<13);t=t^(t>>7);xs=t^(t<<17);end
  endfunction
  task step(input bit active,input integer k);
    integer j;
    begin
      @(negedge ck);
      for(j=0;j<4;j=j+1)begin rng=xs(rng);ea[64*j+:64]=rng;
        rng=xs(rng);eb[64*j+:64]=rng;end
      rng=xs(rng);ea[275:256]=rng[19:0];rng=xs(rng);eb[275:256]=rng[19:0];
      // Four-fragment V trains: header valid only on fragment0; the other
      // three words retain all275 payload bits and traverse the real body.
      ea[3:0]={3'd1,(active&&(k%4==0))};
      eb[3:0]={3'd2,(active&&(k%4==0))};
      va=ea;vb=eb;
      if(bad_payload&&active&&k==9) va[137]=~va[137];
      @(posedge ck);cycle=cycle+1;
      if(dut.tx&&(dut.pva||dut.pvb))collisions=collisions+1;
      qa=pa;qb=pb;pa=ea;pb=eb;
      #1;
      if(check_on)begin
        checks=checks+2;
        if(ob !== (bad_age?pa:qa))begin errors=errors+1;
          if(errors<4)$display("BAD_A cycle=%0d",cycle);end
        if(oa !== (bad_age?pb:qb))begin errors=errors+1;
          if(errors<4)$display("BAD_B cycle=%0d",cycle);end
        if(fault)begin errors=errors+1;
          if(errors<4)$display("UNEXPECTED_FAULT cycle=%0d",cycle);end
      end
    end
  endtask
  integer i,reset_round;
  initial begin
    bad_payload=$test$plusargs("bad_payload");bad_age=$test$plusargs("bad_age");
    if(!$value$plusargs("seed=%d",seed))seed=7;
    rng=64'h123456789abcdef1^seed;
    // Cold and warm reset use the declared64-edge hold, with empty traffic.
    for(reset_round=0;reset_round<2;reset_round=reset_round+1)begin
      check_on=0;rst_n=0;own_v=0;
      for(i=0;i<64;i=i+1)step(0,i);
      @(negedge ck);rst_n=1;
      for(i=0;i<12;i=i+1)step(0,i);
      check_on=1;
      for(i=0;i<256;i=i+1)step(1,i);
    end
    check_on=0;
    // Trigger a genuine own train while a foreign four-fragment train is
    // crossing. The real collision/underfilled-train fault must remain live.
    @(negedge ck);own_v=1;
    for(i=0;i<200;i=i+1)step(1,i);
    if(!fault||collisions==0)begin errors=errors+1;$display("FAULT_CONTROL_NOT_CAUGHT");end
    $display("ENG_NATIVE_V_TRANSPORT %s checks=%0d errors=%0d latency_edges=2 fault=%0d collisions=%0d clock_ps=833",
      errors==0?"PASS":"FAIL",checks,errors,fault,collisions);
    if(errors)$fatal(1,"transport mismatch");
    $finish;
  end
endmodule
