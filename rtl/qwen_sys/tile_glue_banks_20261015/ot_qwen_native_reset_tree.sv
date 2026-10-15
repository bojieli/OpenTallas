// Three real registered reset edges. The tree's own local reset inputs are
// constant high, avoiding a recursive asynchronous reset fanout. The compiler
// must clock at least16 initial asserted-reset edges before issuing work.
// Each branch q bit then feeds one real child reset pin; no output broadcast.
module ot_qwen_native_reset_tree #(parameter integer MUT=0) (
    input wire [8:0] ck_reset,
    input wire rst_n,
    output wire [95:0] child_reset_n
);
    wire [15:0] root_q;
    wire [31:0] mid_q;
    qkh_packet_v16 u_root(.clk(ck_reset[0]),.rst_n(1'b1),.d({16{rst_n}}),.q(root_q));
    wire mid0=(MUT==1) ? rst_n : root_q[0];
    qkh_packet_v16 u_mid0(.clk(ck_reset[1]),.rst_n(1'b1),.d({16{mid0}}),.q(mid_q[15:0]));
    qkh_packet_v16 u_mid1(.clk(ck_reset[2]),.rst_n(1'b1),.d({16{root_q[1]}}),.q(mid_q[31:16]));
    genvar b;
    generate for(b=0;b<6;b=b+1)begin:g_branch
        // Three different mid output pins per physical mid master.
        wire reset_d=(b<3) ? mid_q[b] : mid_q[16+b-3];
        wire [15:0] branch_q;
        qkh_packet_v16 u_branch(.clk(ck_reset[3+b]),.rst_n(1'b1),.d({16{reset_d}}),.q(branch_q));
        assign child_reset_n[16*b +:16]=branch_q ^ ((MUT==2 && b==0) ? 16'd1 : 16'd0);
    end endgenerate
endmodule
