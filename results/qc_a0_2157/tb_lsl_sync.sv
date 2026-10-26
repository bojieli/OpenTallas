`timescale 1ns/1ps
module tb;
reg clk=0;always #1 clk=~clk;
reg rst_n=0,rs_model=0,v_d=0,first_d=0;reg[3:0]split_d=0;reg[255:0]w_d=0;reg[127:0]x_d=0;
wire[63:0]old_t,new_t;wire[7:0]old_l,new_l;wire old_f,new_f;
reg[7:0]expected_l=0;reg expected_f=0;
always @(posedge clk)begin rs_model<=rst_n;if(!rs_model)begin expected_l<=0;expected_f<=0;end else begin expected_l<=old_l;expected_f<=old_f;end end
 ot_qwen_tile_lsl reference(.clk(clk),.rst_n(rs_model),.v_d(v_d),.first_d(first_d),.split_d(split_d),.w_d(w_d),.x_d(x_d),.t_out(old_t),.lfault(old_l),.tfault(old_f));
 ot_qwen_tile_lsl_sync_fault candidate(.clk(clk),.rst_n(rst_n),.v_d(v_d),.first_d(first_d),.split_d(split_d),.w_d(w_d),.x_d(x_d),.t_out(new_t),.lfault(new_l),.tfault(new_f));
integer c,i,data_checks=0,fault_checks=0,nonzero_data=0,nonzero_fault=0;reg[63:0]xs=64'hcafe12344567abcd;
function[31:0]rnd;input unused;begin xs=xs^(xs<<13);xs=xs^(xs>>7);xs=xs^(xs<<17);rnd=xs[31:0];end endfunction
initial begin for(c=0;c<20000;c=c+1)begin @(negedge clk);if(c>20)begin
if(new_t!==old_t)$fatal(1,"data mismatch %0d",c);
if({new_f,new_l}!=={expected_f,expected_l})$fatal(1,"fault edge mismatch %0d",c);
data_checks=data_checks+1;fault_checks=fault_checks+1;if(old_t!=0)nonzero_data=nonzero_data+1;if({old_f,old_l}!=0)nonzero_fault=nonzero_fault+1;end
rst_n=(c>3 && c%509>3);v_d=rst_n && c%509>12 && (rnd(0)&3)!=0;first_d=c%8==0;split_d=rnd(0);
for(i=0;i<8;i=i+1)w_d[32*i+:32]=rnd(0);for(i=0;i<4;i=i+1)x_d[32*i+:32]=rnd(0);
end
$display("LSL_SYNC PASS data_checks=%0d shifted_fault_checks=%0d nonzero_data=%0d nonzero_fault=%0d data_edges_added=0 fault_edges_added=1 boot_edges_added=1",data_checks,fault_checks,nonzero_data,nonzero_fault);$finish;end
endmodule
