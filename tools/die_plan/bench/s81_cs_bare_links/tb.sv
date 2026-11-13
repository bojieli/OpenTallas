module cst_miter #(parameter integer W=740,V=2,D=2)(input wire clk,rst_n,input wire mut);
reg [W-1:0] d;reg [V-1:0] dv;reg [767:0] word;integer j;
wire [W-1:0] q0,q,qbad;wire [V-1:0] v0,qv,vbad;
ot_s81sl_cst #(.W(W),.V(V),.D(0)) baseline(.clk(clk),.rst_n(rst_n),.d(d),.dv(dv),.q(q0),.qv(v0));
ot_s81sl_cst #(.W(W),.V(V),.D(D)) planned(.clk(clk),.rst_n(rst_n),.d(d),.dv(dv),.q(q),.qv(qv));
ot_s81sl_cst #(.W(W),.V(V),.D(D-1)) missing_stage(.clk(clk),.rst_n(rst_n),.d(d),.dv(dv),.q(qbad),.qv(vbad));
reg [W-1:0] ed[0:D-1];reg [V-1:0] ev[0:D-1];integer i;
always @(negedge clk) begin
 for(j=0;j<24;j=j+1) word[j*32+:32]=$random;
 d=word[W-1:0]; dv=V'($random);
end
always @(posedge clk or negedge rst_n) begin
 if(!rst_n) begin for(i=0;i<D;i=i+1)ev[i]<={V{1'b0}};end
 else begin ed[0]<=q0;ev[0]<=v0;for(i=1;i<D;i=i+1)begin ed[i]<=ed[i-1];ev[i]<=ev[i-1];end end
end
wire [W-1:0] observed=(mut && D==2)?qbad:q;
wire [V-1:0] observed_v=(mut && D==2)?vbad:qv;
always @(posedge clk) begin
 #1;
 if(rst_n && (observed_v!==ev[D-1] || ((|observed_v) && observed!==ed[D-1])))
   $fatal(1,"CST_LOCKSTEP_FAIL W=%0d V=%0d D=%0d mutant=%0d",W,V,D,mut);
end
endmodule
module tb;
reg clk=0;always #5 clk=~clk;reg rst_n=0;reg mut;
cst_miter #(.W(740),.V(2),.D(2)) ve(clk,rst_n,mut);
cst_miter #(.W(228),.V(3),.D(2)) ver(clk,rst_n,mut);
cst_miter #(.W(651),.V(4),.D(3)) vni(clk,rst_n,mut);
initial begin
 mut=$test$plusargs("MUT");
 repeat(5)@(negedge clk);rst_n=1;
 repeat(120)@(negedge clk);rst_n=0;
 repeat(5)@(negedge clk);rst_n=1;
 repeat(180)@(negedge clk);
 $display("CST_LOCKSTEP_PASS actual_source VE740x2 VER228x2 VNI651x3 warm_reset bubbles");$finish;
end
endmodule
