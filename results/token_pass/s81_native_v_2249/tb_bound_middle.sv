`timescale 1ps/1fs
module tb_bound_middle;
`include "latency_params.svh"
  localparam integer MAXL=235;
  reg ck=0,rst_n=0,inject=0,own_v=0;
  reg[275:0]va=0,vb=0,ea=0,eb=0;
  wire[275:0]q[0:5];wire[3:0]fault;
  native_bound_middle_fixture dut(.ck(ck),.rst_n(rst_n),.inject(inject),.own_v(own_v),.va(va),.vb(vb),
    .gno(q[0]),.gso(q[1]),.bno(q[2]),.bso(q[3]),.eno(q[4]),.eso(q[5]),.fault(fault));
  reg[275:0]ha[0:MAXL],hb[0:MAXL],expected[0:5];
  reg[63:0]rng=64'h123456789abcdef1;
  integer latency[0:5];
  integer errors=0,checks=0,bad_payload=0,bad_age=0,cycle=0;
  reg check_on=0;
  function automatic[63:0]xs(input[63:0]x);
    reg[63:0]t;begin t=x^(x<<13);t=t^(t>>7);xs=t^(t<<17);end
  endfunction
  always #416.5 ck=~ck;
  task step(input bit active,input integer k);
    integer j,ix;
    begin
      @(negedge ck);
      for(j=0;j<4;j=j+1)begin rng=xs(rng);ea[64*j+:64]=rng;
        rng=xs(rng);eb[64*j+:64]=rng;end
      rng=xs(rng);ea[275:256]=rng[19:0];rng=xs(rng);eb[275:256]=rng[19:0];
      ea[3:0]={3'd1,(active&&(k%4==0))};eb[3:0]={3'd2,(active&&(k%4==0))};
      va=ea;vb=eb;
      if(bad_payload&&active&&k==245)va[137]=~va[137];
      @(posedge ck);cycle=cycle+1;
      for(j=0;j<6;j=j+1)begin
        ix=latency[j]-2-(bad_age?1:0);
        expected[j]=(j%2)?hb[ix]:ha[ix];
      end
      for(j=MAXL;j>0;j=j-1)begin ha[j]=ha[j-1];hb[j]=hb[j-1];end
      ha[0]=ea;hb[0]=eb;
      #1;
      if(check_on&&k>=MAXL+5)begin
        for(j=0;j<6;j=j+1)begin
          checks=checks+1;
          if(q[j]!==expected[j])begin errors=errors+1;
            if(errors<8)$display("BAD_PATH path=%0d cycle=%0d expected_age=%0d",j,cycle,latency[j]);end
        end
        if(fault!=0)begin errors=errors+1;if(errors<8)$display("BAD_FAULT %b",fault);end
      end
    end
  endtask
  integer i,r;
  initial begin
    latency[0]=L0;latency[1]=L1;latency[2]=L2;latency[3]=L3;latency[4]=L4;latency[5]=L5;
    if(L0>MAXL||L1>MAXL||L2>MAXL||L3>MAXL||L4>MAXL||L5>MAXL)$fatal(1,"source shape changed");
    bad_payload=$test$plusargs("bad_payload");bad_age=$test$plusargs("bad_age");
    for(i=0;i<=MAXL;i=i+1)begin ha[i]=0;hb[i]=0;end
    for(r=0;r<2;r=r+1)begin
      check_on=0;rst_n=0;for(i=0;i<64;i=i+1)step(0,i);
      @(negedge ck);rst_n=1;for(i=0;i<32;i=i+1)step(0,i);
      check_on=1;for(i=0;i<512;i=i+1)step(1,i);
    end
    check_on=0;@(negedge ck);inject=1;own_v=1;
    for(i=0;i<200;i=i+1)step(1,i);
    if(!fault[0]||!fault[3])begin errors=errors+1;$display("GUARD_CONTROL_NOT_CAUGHT %b",fault);end
    $display("BOUND_MIDDLE_NATIVE_V %s checks=%0d errors=%0d G_N=%0d G_S=%0d BK_N=%0d BK_S=%0d E_N=%0d E_S=%0d guards=%b clock_ps=833",
      errors==0?"PASS":"FAIL",checks,errors,L0,L1,L2,L3,L4,L5,fault);
    if(errors)$fatal(1,"current bound middle-V mismatch");$finish;
  end
endmodule
