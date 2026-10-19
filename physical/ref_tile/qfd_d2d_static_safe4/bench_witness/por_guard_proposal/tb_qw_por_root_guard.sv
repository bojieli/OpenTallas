module tb;
 reg ck=0,por_n=1; wire a3,a17,a31,g3,g17,g31;integer n,seed;
 qw_por_root_guard_proposal #(.FLUSH(3)) u3(ck,por_n,a3,g3);
 qw_por_root_guard_proposal #(.FLUSH(17)) u17(ck,por_n,a17,g17);
 qw_por_root_guard_proposal #(.FLUSH(31),.MUT_EARLY(`MUT_EARLY)) u31(ck,por_n,a31,g31);
 task step;
 begin #2;ck=1;#1;ck=0;#1;end
 endtask
 task pulse;
 begin
  // Assert with clock STOPPED, at a phase unrelated to a rising edge.
  #1;por_n=0;#1;
  if ({a3,a17,a31,g3,g17,g31} !== 6'b0) $fatal(1,"asynchronous guard assertion failed");
  if(u3.count!==0||u17.count!==0||u31.count!==0) $fatal(1,"async count initialization failed");
  #1;por_n=1;#1;
 end
 endtask
 initial begin
  u3.count='x;u3.armed='x;u17.count='x;u17.armed='x;u31.count='x;u31.armed='x;
  pulse();
  for(n=1;n<=32;n=n+1) begin step();if(a3!==(n>=3)||a17!==(n>=17)||a31!==(n>=31)) $fatal(1,"X-prestate release mismatch edge=%0d",n);end
  // Exhaust every 6-bit guard prestate; do not assume zeros or equality.
  for(seed=0;seed<64;seed=seed+1) begin
   u3.count=seed;u3.armed=seed[5];u17.count=seed;u17.armed=seed[5];u31.count=seed;u31.armed=seed[5];
   pulse();
   for(n=1;n<=40;n=n+1) begin
    step();
    if(a3!==(n>=3)||a17!==(n>=17)||a31!==(n>=31)) $fatal(1,"first qualified release mismatch seed=%0d edge=%0d a31=%b",seed,n,a31);
    if(g3!==a3||g17!==a17||g31!==a31) $fatal(1,"release polarity mismatch");
   end
   // Reassert during normal armed execution, then restart before arming.
   pulse();repeat(2) step();pulse();
   for(n=1;n<=32;n=n+1) begin
    step();if(a31!==(n>=31)) $fatal(1,"restart first release mismatch");
   end
  end
  $display("POR_GUARD_PROPOSAL_PASS arbitrary_prestate64_plusX stopped_clock_assert restart exactK3_17_31 no_zero_init");$finish;
 end
endmodule
