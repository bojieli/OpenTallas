module tb;
reg tclk=0,rclk=0; always #5 tclk=~tclk; initial begin #2; forever #5 rclk=~rclk; end
reg tr=0,rr=0; reg[7:0] d=0; reg[5:0] k=0;
wire[7:0] a,b;wire[3:0] fa,fb;
gold_ot_meso_ring_ca #(.W(8),.DEPTH(4),.CONTROL_STATUS_COPY(1)) g(.tclk(tclk),.wen_clk(tclk),.t_rst_n(tr),.t_d(d),.rclk(rclk),.r_rst_n(rr),.k_s(k),.r_d(a),.r_v(fa[0]),.r_lap_ok(fa[1]),.r_glo_ok(fa[2]),.r_ghi_ok(fa[3]));
ot_meso_ring_ca #(.W(8),.DEPTH(4),.CONTROL_STATUS_COPY(1)) n(.tclk(tclk),.wen_clk(tclk),.t_rst_n(tr),.t_d(d),.rclk(rclk),.r_rst_n(rr),.k_s(k),.r_d(b),.r_v(fb[0]),.r_lap_ok(fb[1]),.r_glo_ok(fb[2]),.r_ghi_ok(fb[3]));
integer j=0, checks=0;always @(negedge tclk) begin d <= d+8'h37;tr <= j%79>3;j<=j+1;end
always @(negedge rclk) begin rr <= j%103>5;if(j%103==0)k <= k+1;end
always @(posedge rclk) begin #1;if(j>20)begin checks=checks+1;if({a,fa}!=={b,fb})$fatal(1,"MISMATCH j%0d k%0d gold%h new%h",j,k,{a,fa},{b,fb});end if(j>12000)begin $display("PASS lockstep checks%0d",checks);$finish;end end
endmodule
