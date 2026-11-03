`timescale 1ns/1fs
// SOURCE ONLY: selected REGROOT3/BMUT0/CHILD_CLOCKS1 native node component.
// Independent clocks remain public. No selected phase or count origin implied.
module qwen_native_l6_node_component (
 input wire ck_fa0, ck_fa1, ck_fa3, ck_fa4, ck_node,
 input wire rst_n,
 input wire [513:0] n_a, n_b,
 input wire [511:0] td_x,
 input wire t_vout_i,
 output wire [513:0] n_y,
 output wire node_fault,
 output wire [511:0] t_out_nd,
 output wire t_vout_nd
);
 localparam integer CHILD_CLOCKS=1;
 wire reset_q;
(* keep *) reg q;
        always @(posedge ck_fa4) q <= rst_n;
        assign reset_q = q;
(* keep *) reg [513:0] n_a_q,n_b_q;
    always @(posedge ck_fa0) n_a_q<=n_a;
    always @(posedge ck_fa1) n_b_q<=n_b;
 wire [511:0] na_x=n_a_q[511:0];
 wire n_va=n_a_q[512];
 wire [511:0] ny;
 wire nvy;
 wire clk=ck_node;
 wire rst_n_inner=reset_q;
 generate begin : selected_inner
 wire rst_n=rst_n_inner;
 wire [511:0] n_b=n_b_q[511:0];
 wire [511:0] n_y;
 wire n_vy;
ot_qwen_tile_node u_node (.clk(CHILD_CLOCKS ? ck_node : clk), .rst_n(rst_n), .a(na_x), .b(n_b), .va(n_va),
                                  .y(n_y), .vy(n_vy), .fault(node_fault),
                                  .t_d(td_x), .t_vd(t_vout_i), .t_out(t_out_nd), .t_vout(t_vout_nd));
 assign ny=n_y;
 assign nvy=n_vy;
 end endgenerate
(* keep *) reg fy_q;
    reg mis_q;
    always @(posedge ck_fa3)
        if (!reset_q) begin fy_q <= 1'b0; mis_q <= 1'b0; end
        else begin
            mis_q <= mis_q | (n_a_q[512] ^ n_b_q[512]);
            fy_q  <= n_a_q[513] | n_b_q[513] | mis_q;
        end
    (* keep *) reg [513:0] n_y_q;
    always @(posedge ck_fa3) begin
        n_y_q[511:0]<=ny;
        n_y_q[513:512]<=reset_q ? {fy_q,nvy} : 2'd0;
    end
    assign n_y=n_y_q;
endmodule
