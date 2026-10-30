module tb_ring_local_start(input wire fclk,clk,t_rst_n,rst_n,
 input wire [31:0] d,input wire [5:0] k,input wire r2,
 output wire [31:0] qb,qc,qm,output wire rb,rc,rm,fb,fc,fm,
 output wire vb,vc,lb,lc,gb,gc,hb,hc,output wire delayed);
 reg [1:0] sr;
 always @(posedge clk) if(!rst_n) sr<=0;else sr<={sr[0],1'b1};
 assign delayed=r2?sr[1]:sr[0];
 wire [5:0] kc=k-(r2?6'd2:6'd1);
 ot_dp_clk_landing_cas #(.W(32),.DEPTH(4)) b(.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(rst_n),.strap_k(k),.d(d),.q(qb),.ready(rb),.fault(fb));
 ot_dp_clk_landing_cas #(.W(32),.DEPTH(4)) c(.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(delayed),.strap_k(kc),.d(d),.q(qc),.ready(rc),.fault(fc));
 ot_dp_clk_landing_cas #(.W(32),.DEPTH(4)) m(.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(delayed),.strap_k(k),.d(d),.q(qm),.ready(rm),.fault(fm));
 assign vb=b.u_ring.r_v;assign vc=c.u_ring.r_v;
 assign lb=b.u_ring.r_lap_ok;assign lc=c.u_ring.r_lap_ok;
 assign gb=b.u_ring.r_glo_ok;assign gc=c.u_ring.r_glo_ok;
 assign hb=b.u_ring.r_ghi_ok;assign hc=c.u_ring.r_ghi_ok;
endmodule
