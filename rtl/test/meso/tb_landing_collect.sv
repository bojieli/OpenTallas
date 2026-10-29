// Reverse-wavefront collector tree. Branch u_b models a SAME-REGION (non-seam) child: its status pin pair
// ready_i[2]/fault_i[2] is captured by its own face flops (ot_dp_landing_face, no reset) before the reduction
// (DIE-S81-29), so that branch reaches the root one status cycle later than the u_a branch.
module tb_landing_collect(input wire clk,rst_n,
    input wire [2:0] ready_i,fault_i,output wire ready_o,fault_o);
    wire r0,f0,r1,f1,fr2,ff2;
    ot_dp_landing_collect #(.N(2)) u_a(.clk(clk),.rst_n(rst_n),.ready_i(ready_i[1:0]),
        .fault_i(fault_i[1:0]),.ready_o(r0),.fault_o(f0));
    ot_dp_landing_face u_face_r(.clk(clk),.d(ready_i[2]),.q(fr2));
    ot_dp_landing_face u_face_f(.clk(clk),.d(fault_i[2]),.q(ff2));
    ot_dp_landing_collect #(.N(1)) u_b(.clk(clk),.rst_n(rst_n),.ready_i(fr2),
        .fault_i(ff2),.ready_o(r1),.fault_o(f1));
    ot_dp_landing_collect #(.N(2)) u_root(.clk(clk),.rst_n(rst_n),.ready_i({r1,r0}),
        .fault_i({f1,f0}),.ready_o(ready_o),.fault_o(fault_o));
endmodule
