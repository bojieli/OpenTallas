`timescale 1ns/1ps
// ot_s81_done_word (s81-ctl-1011, 2026-10-11): done-word endpoint shared by the selector / collector masters: vd = {data 512, valid, rst_n}; DONE = data[511:508]
// == 4, tag = data[507:500]; FAULT words (type 5) raise the slab fault.
module ot_s81_done_word #(parameter integer SKIP_FIRST = 0, MUT = 0) (
    input wire ck, input wire rst,
    input wire [513:0] vd,
    input wire [84:0] c_cmd, output wire [8:0] c_done, output wire [1:0] c_st
);
    reg [1:0] rs_s;
    always @(posedge ck or negedge rst) if (!rst) rs_s <= 2'b00; else rs_s <= {rs_s[0], 1'b1};
    wire rs_n = rs_s[1];
    reg dv_q, fw_q, seen; reg [7:0] tg_q;
    always @(posedge ck or negedge rs_n)
        if (!rs_n) begin dv_q <= 1'b0; fw_q <= 1'b0; seen <= 1'b0; tg_q <= 8'd0; end
        else begin
            dv_q <= vd[1] && vd[513:510] == 4'd4 && (seen || SKIP_FIRST == 0);
            if (vd[1] && vd[513:510] == 4'd4) seen <= 1'b1;
            if (vd[1] && vd[513:510] == 4'd5) fw_q <= 1'b1;
            tg_q <= vd[509:502];
        end
    wire jv, jnew; wire [83:0] jd, jnd; wire epf;
    wire ok = dv_q && jv && tg_q == jd[14:7];
    reg sf;
    always @(posedge ck or negedge rs_n)
        if (!rs_n) sf <= 1'b0; else if ((dv_q && jv && !ok) || fw_q) sf <= 1'b1;
    ot_s81_slab_ep #(.QD(8), .JQ(2), .MUT(MUT)) u_ep (.c_clk(ck), .c_rst_n(rst), .c_cmd(c_cmd), .c_done(c_done),
        .c_st(c_st), .e_clk(ck), .e_rst_n(rst), .j_v(jv), .j_d(jd), .j_new(jnew), .j_new_d(jnd),
        .j_present(vd[0]), .j_done(ok || (dv_q && !jv)), .slab_fault(sf), .ep_fault(epf));
endmodule
