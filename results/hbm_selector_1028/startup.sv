`timescale 1ns/1ps
module startup;
reg clk=0,rst_n=0;always #1 clk=~clk;
wire[3:0] v0,v1,vr;wire[2367:0]l0,l1,lr;wire f0,f1,fr;
ot_hbm_idx_selector_static r(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(4'd0),.pass(2'd0),.addr(8'd0),.k(10'd0),.in_line(2368'd0),.out_v(),.out_line(),.threshold_observe(),.selected_observe(),.selected_v(vr),.selected_line(lr),.fault(fr));
ot_hbm_idx_selector_static_sel #(.STRUCT(0)) s0(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(4'd0),.pass(2'd0),.addr(8'd0),.k(10'd0),.in_line(2368'd0),.selected_v(v0),.selected_line(l0),.fault(f0));
ot_hbm_idx_selector_static_sel #(.STRUCT(1)) s1(.clk_ctl(clk),.clk_q({4{clk}}),.clk_mem({12{clk}}),.rst_n(rst_n),.op(4'd0),.pass(2'd0),.addr(8'd0),.k(10'd0),.in_line(2368'd0),.selected_v(v1),.selected_line(l1),.fault(f1));
integer cy=0;
always @(negedge clk)begin
 $display("cy%0d rst%b v%b/%b/%b l0=%b/%b/%b p=%b/%b/%b",cy,rst_n,vr,v0,v1,lr[36:0],l0[36:0],l1[36:0],r.core.gq[0].mask_choose,s0.core.gq[0].mask_choose,s1.core.gq[0].mask_choose);
 for(integer i=0;i<2368;i=i+1)if(lr[i]!==l1[i])$display("diffbit%0d r%b 0%b 1%b",i,lr[i],l0[i],l1[i]);
 cy=cy+1;
 if(cy==4)rst_n=1;
 if(cy==12)$finish;
end
endmodule
