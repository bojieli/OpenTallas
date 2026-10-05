`timescale 1ns/1ps
// Changed metadata-control unit only. No memory/provider, engine arithmetic,
// production installer, 96x512 candidates or fabricated CP completion.
module tb_hbm_integrated_prior_debt;
 reg clk=0;always #500 clk=~clk;
 reg por_n=0;
 reg [3:0] rq=0,rs=0,rqw=0,rsw=0,offer=0;
 reg [63:0] rt=0,st=0;
 reg [31:0] job=32'h12345678;reg [3:0] gen=4'h9;
 reg [16:0] token=17'h10001;reg [19:0] pos=20'hfffff;
 wire [3:0] authorized;wire debt,violation,uncorrectable;
 ot_hbm_integrated_prior_debt #(.ENABLE(1),.NC(4)) u (
  .clk(clk),.por_n(por_n),.observe_req(rq),.observe_rsp(rs),
  .observe_req_we(rqw),.observe_rsp_we(rsw),.observe_req_tag(rt),.observe_rsp_tag(st),
  .return_offer(offer),.native_job(job),.native_gen(gen),.native_token(token),.native_pos(pos),
  .response_authorized(authorized),.debt(debt),.violation(violation),.uncorrectable(uncorrectable));
 task settle;begin #1;end endtask
 task clocked;begin @(posedge clk);#1;@(negedge clk);end endtask
 initial begin
  clocked();por_n=1;clocked();
  for(integer k=0;k<32;k=k+1)begin
   rq=4'hf;rqw=4'b1010;
   for(integer c=0;c<4;c=c+1)rt[c*16+:16]=16'(32*c+k);
   settle();if(violation||uncorrectable)$fatal(1,"legal native credit refused");clocked();
  end
  rq=0;settle();if(!debt)$fatal(1,"128 native credits disappeared");
  // Real attempted overflow is refused and does not replace a live credit.
  rq=1;rt[15:0]=16'h7000;settle();if(!violation)$fatal(1,"33rd credit accepted");clocked();rq=0;
  // The physical response must match route/tag/kind AND retained CP context.
  offer=4'hf;st={16'd96,16'd64,16'd32,16'd0};rsw=4'b1010;settle();
  if(authorized!=4'hf||violation)$fatal(1,"matched original producer return refused");
  gen=4'ha;settle();if(authorized!=0||!violation||!debt)$fatal(1,"foreign CP context accepted/canceled debt");
  clocked();gen=4'h9;settle();if(authorized!=4'hf||!debt)$fatal(1,"context refusal erased native credit");
  st[15:0]=16'h7000;settle();if(authorized[0]||!violation)$fatal(1,"foreign physical tag accepted");
  clocked();offer=0;rs=0;
  for(integer k=0;k<32;k=k+1)begin
   for(integer c=0;c<4;c=c+1)st[c*16+:16]=16'(32*c+k);
   offer=4'hf;rs=4'hf;rsw=4'b1010;settle();
   if(authorized!=4'hf||violation||uncorrectable)$fatal(1,"original credit lost/identity mismatch");clocked();
  end
  offer=0;rs=0;settle();if(debt||violation||uncorrectable)$fatal(1,"consumed original responses retained debt");
  $display("PASS_PRIOR_DEBT_4x32 full_context overflow_foreign_noACK retained_until_128_consumed");
  $finish;
 end
endmodule
