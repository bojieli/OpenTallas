module tb;
reg clk=0,fclk=0,rst_n=0,t_rst_n=0; reg [766:0] d=0;
wire [766:0] q0,q1; wire r0,r1,e0,e1; integer n=0,bad=0;
always #5 clk=~clk;
initial begin #2; forever #5 fclk=~fclk; end
always @(posedge fclk) d <= d*8'd13+8'd7;
ot_dp_clk_landing_cas #(.W(767),.DEPTH(4),.WFALL(1),.WREG(1),.DSREP(1)) gold(.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(rst_n),.strap_k(6'd2),.d(d),.q(q0),.ready(r0),.fault(e0));
sle_cland_w767_e_200 gate(.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(rst_n),.strap_k(6'd2),.d(d),.q(q1),.ready(r1),.fault(e1));
initial begin #41;t_rst_n=1;rst_n=1;end
always @(negedge clk) begin
n=n+1;
if(n>10 && ({r0,e0} !== {r1,e1} || (r0 && q0 !== q1)))bad=bad+1;
if(n==500)begin $display("LOCKSTEP bad=%0d ready=%0b fault=%0b",bad,r0,e0); if(bad)$fatal(1,"mismatch");$finish;end
end
endmodule
