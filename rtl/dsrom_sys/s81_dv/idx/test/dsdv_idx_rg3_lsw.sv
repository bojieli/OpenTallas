`timescale 1ns/1ps
// STW-S81c-TOK4-BAND (10-22): LOCKSTEP wrapper for tb_dsdv_idx_rg3 (run_rg3_band_lsw.sh seds the tb's reader instance to
// this module).  u_ref = dsdv_idx_rg3 (drives the system: controllers, chain, checks unchanged); u_band = the banded
// flat parent dsdv_idx_rg3_bf fed the SAME inputs.  Every edge after the reset: qo / so / rqo equal, st equal one edge
// later (S23's st stage).  Requires IH 0 / OH 1 (the banded chain: W pin flop qr, S23's one output stage).
// BLX / BPD: the banded parent's LX / PD (both 0 here: the flat band composition must be cycle-exact).
// S81/PORTFIX-FLT 10-25: dsdv_idx_rg3's port st[9:0] became the 1-bit sticky fault; the lockstep still compares the
// full former status: st_r = {fc, act, fault} rebuilt from u_ref's own flops (the same register the port had).
module dsdv_idx_rg3_lsw #(
    parameter integer MUT = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer DQR = 24,
    parameter integer SQD = 256,
    parameter integer IQD = 512,
    parameter integer OH = 1,
    parameter integer RH = 2,
    parameter integer IH = 0,
    parameter integer KR = 1
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,
    output wire [512:0]  qo,
    input  wire [275:0]  si,
    output wire [275:0]  so,
    output wire [183:0]  rqo,
    input  wire [1087:0] rri,
    output wire          fault
);
    initial if (OH != 1 || IH != 0 || KR != 1) $fatal(1, "dsdv_idx_rg3_lsw: run with -GOH=1 -GIH=0 -GKR=1");
    dsdv_idx_rg3 #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .SQD(SQD), .IQD(IQD), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u_ref (
        .ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(qo), .si(si), .so(so), .rqo(rqo), .rri(rri), .fault(fault));
    reg  [9:0] st;   // the former st port of u_ref, same register / same edge
    wire act = u_ref.act;   // bench tap (tb end-of-window check)
    always @(posedge ck or negedge u_ref.rl[39]) if (!u_ref.rl[39]) st <= 10'd0; else st <= {u_ref.fc, u_ref.act, u_ref.fc_any};
    wire [512:0] bqo; wire [275:0] bso; wire [183:0] brqo; wire [9:0] bst;
    dsdv_idx_rg3_bf #(.MUTR(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .SQD(SQD), .IQD(IQD), .RH(RH), .KR(KR), .LX(0), .PD(0)) u_band (
        .ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(bqo), .si(si), .so(bso), .rqo(brqo), .rri(rri), .st(bst));
    reg [9:0] st_d;
    reg       live;
    integer   n_cmp = 0, n_bad = 0;
    always @(posedge ck) begin
        st_d <= st;
        live <= rst;
        if (live && rst) begin
            n_cmp = n_cmp + 1;
            if (bqo !== qo || bso !== so || brqo !== rqo || bst !== st_d) begin
                n_bad = n_bad + 1;
                if (n_bad <= 5)
                    $display("TB_LSW MISMATCH sid %0d t %0t qo %0d so %0d rqo %0d st %0d (st %h band %h)", sid, $time,
                             bqo !== qo, bso !== so, brqo !== rqo, bst !== st_d, st_d, bst);
            end
        end
    end
    final $display("TB_LSW sid %0d %s cmp %0d bad %0d", sid, (n_bad == 0 && n_cmp > 0) ? "OK" : "BAD", n_cmp, n_bad);
endmodule
