`timescale 1ns/1ps
// Primary b2: eight two-lane upper faces. Each valid/fault has its own pin register.
// Original GP4 one-lane leaf source is defined in ot_qwen_halfband_lanes_slots.sv.
// New parent/upper views required; no historical four-lane physical alias.
module qfd_sp_halfband_lanes_b2_l2 (
    input  wire          ck,
    input wire ck_l0,
    input wire ck_l1,
    input wire ck_l2,
    input wire ck_l3,
    input wire ck_l4,
    input wire ck_l5,
    input wire ck_l6,
    input wire ck_l7,
    input wire ck_l8,
    input wire ck_l9,
    input wire ck_l10,
    input wire ck_l11,
    input wire ck_l12,
    input wire ck_l13,
    input wire ck_l14,
    input wire ck_l15,

    input  wire          rst_n,
    input  wire          b0,
    input  wire [5:0]    lnk,
    input  wire [2047:0] tw,
    input  wire [25:0]   c,
    input wire [193:0] tt_l0,tt_l1,tt_l2,tt_l3,tt_l4,tt_l5,tt_l6,tt_l7,
    output wire [512:0]  pw,
    // Direct upper-tree leaves: one independent registered quarter word and
    // fault per leaf, so the die has point-to-point fixed-cycle links.
    output wire [64:0] pw_l0, pw_l1, pw_l2, pw_l3, pw_l4, pw_l5, pw_l6, pw_l7,
    output wire [7:0] f_up,
    output wire [2047:0] ty,
    output wire          f
);
    (* keep *) reg reset_q,b0_q;
    (* keep *) reg [5:0] lnk_q;
    (* keep *) reg [2047:0] tw_q;
    (* keep *) reg [25:0] c_q;
    wire [8*194-1:0] tt_faces={tt_l7,tt_l6,tt_l5,tt_l4,tt_l3,tt_l2,tt_l1,tt_l0};
    (* keep *) reg [8*194-1:0] tt_q;
    always @(posedge ck) begin
        reset_q<=rst_n;b0_q<=b0;lnk_q<=lnk;
        tw_q<=tw;c_q<=c;tt_q<=tt_faces;
    end
    // The parent contributes one output and one return-input edge to the
    // band/upper round trip: two edges, represented by one LNK unit.
    wire [5:0] leaf_lnk=lnk_q+6'd1;
    wire [512:0] pw_i;
    wire [2047:0] ty_i;
    (* keep *) reg [512:0] pw_q;
    (* keep *) reg [2047:0] ty_q;
    always @(posedge ck) begin
        pw_q[511:0]<=pw_i[511:0];pw_q[512]<=reset_q & pw_i[512];
        ty_q<=ty_i;
    end
    assign pw=pw_q;assign ty=ty_q;
    wire [15:0] leaf_ck = {ck_l15, ck_l14, ck_l13, ck_l12, ck_l11, ck_l10, ck_l9, ck_l8, ck_l7, ck_l6, ck_l5, ck_l4, ck_l3, ck_l2, ck_l1, ck_l0};
    wire [15:0] lf, lpv;
    genvar l, k;
    generate for (l = 0; l < 16; l = l + 1) begin : g_lane
        wire [127:0] ltw, lty;
        wire [97:0]  ltt;
        wire [32:0]  lpw;
        for (k = 0; k < 4; k = k + 1) begin : g_k
            assign ltw[32*k +: 32] = tw_q[32*(16*k + l) +: 32];
            assign ty_i[32*(16*k + l) +: 32] = lty[32*k +: 32];
        end
        for (k = 0; k < 3; k = k + 1) begin : g_t
            assign ltt[32*k +: 32] = tt_q[194*(l/2)+64*k+32*(l%2) +: 32];
        end
        assign ltt[97:96] = tt_q[194*(l/2)+192+:2];
        assign pw_i[32*l +: 32] = lpw[31:0];
        assign lpv[l] = lpw[32];
`ifdef OT_QFD_HALFBL_B2_MUT
        if (l == 5) begin : g_mut
            qfd_halfbl_lane_b2_mut u_lane (.ck(leaf_ck[l]), .rst_n(reset_q), .b0(b0_q), .lnk(leaf_lnk), .tw(ltw), .c(c_q), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
        end else begin : g_ok
            qfd_halfbl_lane_b2 u_lane (.ck(leaf_ck[l]), .rst_n(reset_q), .b0(b0_q), .lnk(leaf_lnk), .tw(ltw), .c(c_q), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
        end
`else
        qfd_halfbl_lane_b2 u_lane (.ck(leaf_ck[l]), .rst_n(reset_q), .b0(b0_q), .lnk(leaf_lnk), .tw(ltw), .c(c_q), .tt(ltt), .pw(lpw), .ty(lty), .f(lf[l]));
`endif
    end endgenerate
    wire [7:0] quarter_pv, quarter_fault;
    ot_qfd_halfband_upper_faces_l2 u_upper_faces (.clk(ck),.reset_q(reset_q),.lnk(lnk_q),
        .lpv(lpv),.lf(lf),.quarter_pv(quarter_pv),.quarter_fault(quarter_fault));
    assign pw_l0={quarter_pv[0],pw_q[63:0]};
    assign pw_l1={quarter_pv[1],pw_q[127:64]};
    assign pw_l2={quarter_pv[2],pw_q[191:128]};
    assign pw_l3={quarter_pv[3],pw_q[255:192]};
    assign pw_l4={quarter_pv[4],pw_q[319:256]};
    assign pw_l5={quarter_pv[5],pw_q[383:320]};
    assign pw_l6={quarter_pv[6],pw_q[447:384]};
    assign pw_l7={quarter_pv[7],pw_q[511:448]};
    assign f_up=quarter_fault;
    assign pw_i[512] = lpv[0];        // every lane carries the same valid copy
    (* keep *) reg f_q;
    always @(posedge ck)
        if (!reset_q) f_q <= 1'b0;
        else f_q <= (&lnk_q) | |lf | (|(lpv ^ {16{lpv[0]}}));
    assign f = f_q;
endmodule

// Real registered quarter boundary for direct upper leaves. Data registers
// remain the existing pw_q stations; these status copies observe distinct
// hardened lane outputs, so they cannot collapse into one remote face pin.
module ot_qfd_halfband_upper_faces_l2 #(parameter integer MUT=0) (
    input wire clk,reset_q,input wire [5:0] lnk,
    input wire [15:0] lpv,lf,
    output reg [7:0] quarter_pv,quarter_fault
);
    genvar u;
    generate for(u=0;u<8;u=u+1) begin:g_upper_face
        always @(posedge clk) begin
            quarter_pv[u] <= reset_q & lpv[2*u];
            if(!reset_q) quarter_fault[u] <= 1'b0;
            else quarter_fault[u] <= (&lnk) |
                ((MUT==1 && u==7) ? 1'b0 : (|lf[2*u +: 2])) |
                (|(lpv ^ {16{lpv[0]}}));
        end
    end endgenerate
endmodule
