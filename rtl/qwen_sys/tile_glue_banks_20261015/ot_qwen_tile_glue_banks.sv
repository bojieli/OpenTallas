// Existing-edge native glue register banks. Each selected master is a real,
// independently clocked physical cell; qualification is inherited only after
// that exact master route and native boundary audit pass.
module ot_qwen_tile_glue_word #(
    parameter integer W=514,
    parameter integer HORIZONTAL=0,
    parameter integer MUT=0,
    parameter integer SPLIT_RESET=0
) (
    input wire ck_lo, ck_hi, rst_n, rst_hi_n,
    input wire [W-1:0] d,
    output wire [W-1:0] q
);
    wire [518:0] padded={{(519-W){1'b0}},d};
    wire [518:0] captured;
    wire hi_clock=(MUT==3) ? ck_lo : ck_hi;
    wire hi_reset=SPLIT_RESET ? rst_hi_n : rst_n;
    generate if (HORIZONTAL != 0) begin : g_h
        qkh_packet_h263 lo(.clk(ck_lo),.rst_n(rst_n),.d(padded[262:0]),.q(captured[262:0]));
        qkh_packet_h256 hi(.clk(hi_clock),.rst_n(hi_reset),.d(padded[518:263]),.q(captured[518:263]));
    end else begin : g_v
        qkh_packet_v263 lo(.clk(ck_lo),.rst_n(rst_n),.d(padded[262:0]),.q(captured[262:0]));
        qkh_packet_v256 hi(.clk(hi_clock),.rst_n(hi_reset),.d(padded[518:263]),.q(captured[518:263]));
    end endgenerate
    // Mutants exercise a missing capture edge and corruption of the upper bank.
    wire [518:0] observed=(MUT==1) ? {captured[518:263],padded[262:0]} : captured;
    assign q=observed[W-1:0] ^ ((MUT==2) ? ({{(W-1){1'b0}},1'b1} << (W-1)) : {W{1'b0}});
`ifndef SYNTHESIS
    initial if(W<264 || W>519) $fatal(1,"tile glue word needs both actual banks, W264..519");
`endif
endmodule

// Candidate replacement for the existing parent face registers. It introduces
// no operational data edge: every face remains one capture. The selected packet
// cells release local reset after three edges; first data capture is edge four.
// Parent integration must publish this reset warmup and exact new clock pins.
module ot_qwen_tile_face_banks #(parameter integer MUT=0) (
    input wire [9:0] ck_face,
    input wire rst_n,
    input wire [507:0] tap_d,
    input wire [513:0] na_d,nb_d,to_d,ny_d,
    output wire [507:0] tap_q,
    output wire [513:0] na_q,nb_q,to_q,ny_q
);
    ot_qwen_tile_glue_word #(.W(508),.MUT(MUT)) tap_bank(.ck_lo(ck_face[0]),.ck_hi(ck_face[1]),.rst_n(rst_n),.d(tap_d),.q(tap_q));
    ot_qwen_tile_glue_word #(.W(514),.MUT(MUT)) na_bank(.ck_lo(ck_face[2]),.ck_hi(ck_face[3]),.rst_n(rst_n),.d(na_d),.q(na_q));
    ot_qwen_tile_glue_word #(.W(514),.MUT(MUT)) nb_bank(.ck_lo(ck_face[4]),.ck_hi(ck_face[5]),.rst_n(rst_n),.d(nb_d),.q(nb_q));
    ot_qwen_tile_glue_word #(.W(514),.MUT(MUT)) to_bank(.ck_lo(ck_face[6]),.ck_hi(ck_face[7]),.rst_n(rst_n),.d(to_d),.q(to_q));
    ot_qwen_tile_glue_word #(.W(514),.MUT(MUT)) ny_bank(.ck_lo(ck_face[8]),.ck_hi(ck_face[9]),.rst_n(rst_n),.d(ny_d),.q(ny_q));
endmodule
