module tb;
 reg clk=0,rst_n=0; reg [1023:0] t0,t1,t2,t3; reg go; reg [7:0] sf;
 wire [511:0] ya,yb; wire va,vb,fa,fb; integer i,err=0,nv=0;
 pvj_old #(.RESET_PIN(1)) a(.clk(clk),.rst_n(rst_n),.ts0(t0),.ts1(t1),.ts2(t2),.ts3(t3),.join_go(go),.sf(sf),.y(ya),.y_valid(va),.fault(fa));
 ot_qwen_tp8_pv_join_t #(.RESET_PIN(1)) b(.clk(clk),.rst_n(rst_n),.ts0(t0),.ts1(t1),.ts2(t2),.ts3(t3),.join_go(go),.sf(sf),.y(yb),.y_valid(vb),.fault(fb));
 function [1023:0] rnd(input integer z); integer k; begin for(k=0;k<32;k=k+1) rnd[32*k+:32]={$random}; end endfunction
 always #5 clk=~clk;
 initial begin
  go=0;sf=0;t0=0;t1=0;t2=0;t3=0;
  repeat(4) @(negedge clk); rst_n=1;
  for(i=0;i<6000;i=i+1) begin
   @(negedge clk);
   t0=rnd(0);t1=rnd(0);t2=rnd(0);t3=rnd(0);
   go=(($random & 63)==0); sf=(i>4000 && ($random&511)==0)? 8'h10:8'h0;
   if(i==3000) begin rst_n=0; end if(i==3003) rst_n=1;
   if(va) nv=nv+1;
   if(i>8 && (ya!==yb || va!==vb || fa!==fb)) begin err=err+1; if(err<5) $display("MISMATCH i=%0d va=%b vb=%b fa=%b fb=%b",i,va,vb,fa,fb); end
  end
  $display("DONE err=%0d valid=%0d fault=%b",err,nv,fa); $finish;
 end
endmodule
