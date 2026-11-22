module ot_s81_serdes_rx_front3 #(
    parameter int MUTANT = 0
) (
    input wire ck, rst_n, p_v, input wire [543:0] p_d,
    output wire [553:0] front_data, output wire front_reset
);
    wire [543:0] face_p_d;
    wire face_p_v;
    wire [8:0] face_am_parts;
    ot_pl_pad #(.W(544), .N(1)) u_face_p_d (.ck(ck), .d(p_d), .q(face_p_d));
    ot_pl_pad #(.W(1), .N(1)) u_face_p_v (.ck(ck), .d(p_v), .q(face_p_v));
    ot_s81_kp4_am_face3 u_face_am3 (.clk(ck), .p_d(p_d), .parts(face_am_parts));
    ot_pl_pad #(.W(554), .N(MUTANT == 1 ? 2 : 3)) u_transport (.ck(ck),
        .d({face_am_parts, face_p_v, face_p_d}), .q(front_data));
    ot_pl_pad #(.W(1), .N(MUTANT == 2 ? 2 : 3)) u_reset (.ck(ck),
        .d(rst_n), .q(front_reset));
endmodule
