// UNQUALIFIED 24-entry successor: actual independent bank/request/return sources per child.
// Numerical benches tie clocks; physical die delivers each routed root phi-R.
// S81 wires-only eight-entry bank parent. Data, bank straps and all child pipeline stages unchanged.
// The die delivers one synchronous phi-R clock at each actual child entry.
module dsfd_vm_bgq28h_mc24 #(parameter integer FORWARD_HOP = 0, parameter integer PIN_OUTPUT_COPY = 0) (
    input wire ck_bank_l0, ck_bank_l1, ck_bank_l2, ck_bank_l3, ck_bank_l4, ck_bank_l5, ck_bank_l6, ck_bank_l7, input wire ck_req_l0, ck_req_l1, ck_req_l2, ck_req_l3, ck_req_l4, ck_req_l5, ck_req_l6, ck_req_l7, input wire ck_ret_l0, ck_ret_l1, ck_ret_l2, ck_ret_l3, ck_ret_l4, ck_ret_l5, ck_ret_l6, ck_ret_l7, input wire [0:0] rs, input wire [1:0] grp,
    input  wire [27:0] i_v, input wire [27:0] i_we, input wire [28*14-1:0] i_row, input wire [28*4-1:0] i_mask,
    input  wire [28*128-1:0] i_d,
    output wire [27:0] f_v, output wire [27:0] f_we, output wire [28*14-1:0] f_row, output wire [28*4-1:0] f_mask,
    output wire [28*128-1:0] f_d,
    input  wire [9:0] r_v, input wire [10*128-1:0] r_d, input wire [3:0] r_f, input wire [2:0] r_o,
    output wire [9:0] o_v, output wire [10*128-1:0] o_d, output wire [3:0] o_f, output wire [2:0] o_o
`ifdef OT_SPVM_RESET_ACK
    ,output wire [23:0] reset_ack
`endif
);
    wire [7:0] ck_req_leaf = {ck_req_l7,ck_req_l6,ck_req_l5,ck_req_l4,ck_req_l3,ck_req_l2,ck_req_l1,ck_req_l0};
    wire [7:0] ck_ret_leaf = {ck_ret_l7,ck_ret_l6,ck_ret_l5,ck_ret_l4,ck_ret_l3,ck_ret_l2,ck_ret_l1,ck_ret_l0};
    wire [7:0] ck_leaf = {ck_bank_l7,ck_bank_l6,ck_bank_l5,ck_bank_l4,ck_bank_l3,ck_bank_l2,ck_bank_l1,ck_bank_l0};
    localparam integer NL = 8;
    wire [27:0] cv [0:NL], cwe [0:NL];
    wire [28*14-1:0] crow [0:NL];
    wire [28*4-1:0] cm [0:NL];
    wire [28*128-1:0] cd [0:NL];
    wire [9:0] cov [0:NL];
    wire [10*128-1:0] cod [0:NL];
    wire [3:0] cof [0:NL];
    wire [2:0] coo [0:NL];
    assign cv[0] = i_v; assign cwe[0] = i_we; assign crow[0] = i_row; assign cm[0] = i_mask; assign cd[0] = i_d;
    assign cov[0] = r_v; assign cod[0] = r_d; assign cof[0] = r_f; assign coo[0] = r_o;
    genvar k;
    generate for (k = 0; k < NL; k = k + 1) begin : g_l
        wire [2:0] bk = k;
        (* keep = 1 *) dsfd_vm_bgl28_mc #(.FORWARD_HOP(FORWARD_HOP), .PIN_OUTPUT_COPY(PIN_OUTPUT_COPY)) u_l (
            .ck(ck_leaf[k]), .ck_req(ck_req_leaf[k]), .ck_ret(ck_ret_leaf[k]), .rs(rs), .grp(grp), .bi(bk),
            .i_v(cv[k]), .i_we(cwe[k]), .i_row(crow[k]), .i_mask(cm[k]), .i_d(cd[k]),
            .f_v(cv[k+1]), .f_we(cwe[k+1]), .f_row(crow[k+1]), .f_mask(cm[k+1]), .f_d(cd[k+1]),
            .r_v(cov[k]), .r_d(cod[k]), .r_f(cof[k]), .r_o(coo[k]),
            .o_v(cov[k+1]), .o_d(cod[k+1]), .o_f(cof[k+1]), .o_o(coo[k+1])
`ifdef OT_SPVM_RESET_ACK
            ,.reset_ack(reset_ack[k*3 +: 3])
`endif
        );
    end endgenerate
    assign f_v = cv[NL]; assign f_we = cwe[NL]; assign f_row = crow[NL]; assign f_mask = cm[NL]; assign f_d = cd[NL];
    assign o_v = cov[NL]; assign o_d = cod[NL]; assign o_f = cof[NL]; assign o_o = coo[NL];
endmodule
