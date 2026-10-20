module tb_vring;
 reg ck=0, rn=0; always #5 ck=~ck;
 reg [3:0] d; wire q1,q26,q106;
 dsdv_idx_vring #(.D(1)) u1(ck,rn,rn,d,q1);
 dsdv_idx_vring #(.D(26)) u26(ck,rn,rn,d,q26);
 dsdv_idx_vring #(.D(106)) u106(ck,rn,rn,d,q106);
 reg [127:0] history=0; integer age=0; integer n; reg bit_d;
 initial begin
   d=0;
   for(n=0;n<2000;n=n+1) begin
     @(negedge ck); rn=(n%517>=4); bit_d=$urandom_range(0,1);d={4{bit_d}};
     @(posedge ck); #1;
     if(!rn) begin age=0;history=0;end
     else begin age=age+1; history={history[126:0],bit_d}; end
     if(q1 !== ((age>=1)?history[0]:1'b0) || q26 !== ((age>=26)?history[25]:1'b0) || q106 !== ((age>=106)?history[105]:1'b0)) begin
       $display("VRING FAIL n=%0d age=%0d actual=%b%b%b expected=%b%b%b",n,age,q1,q26,q106,(age>=1)?history[0]:0,(age>=26)?history[25]:0,(age>=106)?history[105]:0);$fatal(1);
     end
   end
   $display("VRING PASS depths1/26/106 random2000 resets4");$finish;
 end
endmodule
