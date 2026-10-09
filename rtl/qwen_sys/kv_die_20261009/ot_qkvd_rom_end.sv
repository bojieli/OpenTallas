`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// kv-die 2026-10-09: the ROM die's end of the ROM die <-> KV die link (die master qfd_d2d_rom, r22k), between the r21c
// hub's SU / VM face -- unchanged ABI, so the SU, the VM and the sequencer keep their ports -- and the UCIe macro:
//   x3   SU -> link: {x3_d 512, x3_tag 11} + valid, credit back (the SU starts with XS credits).  x3_tag[10:8] = class:
//        3'b001 Q (tag[5:0] beat), 3'b010 KVN (tag[2:0] {v, g, half}).  (The r21c EMB BOOT words no longer use x3:
//        the boot load comes from the host straight into the KV die's HBM.)  Any other class code is a fault.
//   ar   link RES -> VM: 519-b words {g, beat, 16 FP32} (the hub may finish g = 0 / 1 in either order), one per credit (the VM returns ar_cr per word it takes; OCR_AR covers the relays)
//   ea   SU embedding requests {kind, 24-b address} -> EMBQ, credit back per request forwarded (the SU starts with
//        RQD = 32 credits, the gateway's ABI)
//   eq   link EMBD -> SU: posted (the SU's embedding face always accepts, the r21c ABI)
//   dc   sequencer CTL words (ATTN / TOKEN / CSR_RSP) + valid, credit back;  dh  HCTL words -> sequencer, credit back
//   (the forwarded KV-die PLL clock and reset arrive through their own bump cell, qfd_ckbump, straight to qfd_clkrx)
// Every face input is captured at the pin, every output launched from a flop.  Contract:
// results/arch/qwen_kv_die_20261009/CONTRACT.md.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_rom_end #(
    parameter integer XS     = 64,                 // x3 buffer (= the SU's x3 credits)
    parameter integer RQD    = 32,                 // embedding request buffer (= the SU's ea credits)
    parameter integer OCR_AR = 64,                 // RES credits toward the VM (>= the relay round trip)
    parameter integer DCD    = 4,                  // sequencer CTL buffer
    parameter integer OCR_DH = 4,
    parameter integer RB_RES = 32,                 // RES receive buffer (= the KV end's RES link credits)
    parameter integer MUT    = 0,
    parameter integer W      = 528,
    parameter integer FW     = 548
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          x3_v,
    input  wire [511:0]  x3_d,
    input  wire [10:0]   x3_tag,
    output reg           x3_cr,
    output wire          ar_v,
    output wire [518:0]  ar_d,                    // {g, beat[5:0], 16 FP32} (r21c: 512 b, + the 7-b RES tag)
    input  wire          ar_cr,
    input  wire          ea_v,
    input  wire          ea_kind,
    input  wire [23:0]   ea_addr,
    output reg           ea_cr,
    output wire          eq_v,
    output wire [511:0]  eq_d,
    input  wire          dc_v,
    input  wire [W-1:0]  dc_d,
    output reg           dc_cr,
    output wire          dh_v,
    output wire [W-1:0]  dh_d,
    input  wire          dh_cr,
    input  wire          tx_up,
    output wire          tx_v,
    output wire [FW-1:0] tx_flit,
    input  wire          rx_v,
    input  wire [FW-1:0] rx_flit,
    output reg           fault,
    output reg  [7:0]    fault_cause
);
    // ---- input capture ----
    reg          xv, ev, dv;
    reg [522:0]  xd;
    reg [24:0]   ed;
    reg [W-1:0]  dd;
    always @(posedge clk) begin xd <= {x3_tag, x3_d}; ed <= {ea_kind, ea_addr}; dd <= dc_d; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin xv <= 1'b0; ev <= 1'b0; dv <= 1'b0; end
                                           else begin xv <= x3_v; ev <= ea_v; dv <= dc_v; end
    // ---- buffers in front of the adapter's die faces ----
    wire         xe, xf, ee, ef, de, df;
    wire [522:0] xh;
    wire [24:0]  eh;
    wire [W-1:0] dh_w;
    wire [3:0]   t_cr;
    reg  [7:0]   tc [0:3];                        // adapter die-face credits per TX class
    wire [2:0]   xcls = xh[522:520];
    wire         x_q  = (xcls == 3'b001), x_kv = (xcls == 3'b010);
    wire         xpop = !xe && ((x_q && tc[1] != 0) || (x_kv && tc[2] != 0) || (!x_q && !x_kv));
    wire         epop = !ee && tc[3] != 0;
    wire         dpop = !de && tc[0] != 0;
    ot_qkvd_fifo #(.W(523), .D(XS)) u_x (.clk(clk), .rst_n(rst_n), .push(xv), .din(xd), .pop(xpop), .dout(xh),
                                          .empty(xe), .full(xf), .count());
    ot_qkvd_fifo #(.W(25), .D(RQD)) u_e (.clk(clk), .rst_n(rst_n), .push(ev), .din(ed), .pop(epop), .dout(eh),
                                         .empty(ee), .full(ef), .count());
    ot_qkvd_fifo #(.W(W), .D(DCD)) u_d (.clk(clk), .rst_n(rst_n), .push(dv), .din(dd), .pop(dpop), .dout(dh_w),
                                        .empty(de), .full(df), .count());
    reg [3:0]    tv;
    reg [4*W-1:0] td;
    always @(posedge clk) begin
        td[0*W +: W] <= dh_w;
        td[1*W +: W] <= {10'd0, xh[517:512], xh[511:0]};
        td[2*W +: W] <= {13'd0, xh[514:512], xh[511:0]};
        td[3*W +: W] <= {15'd0, eh[24], 488'd0, eh[23:0]};
    end
    // ---- the adapter (ROM end: TX CTL Q KVN EMBQ, RX RES EMBD HCTL) ----
    wire [2:0]     r_v;
    wire [3*W-1:0] r_d;
    reg  [2:0]     r_cr;
    wire [4:0]     afc;
    wire           af;
    ot_qkvd_d2d #(.NT(4), .NR(3), .TXB(0), .RXB(4), .W(W), .IBD({8'd8, 8'd8, 8'd8, 8'd8}),
                  .FCR({8'd32, 8'd8, 8'd32, 8'd4}), .RBD({8'd4, 8'd4, 8'd32, 8'(RB_RES)}),
                  .OCR({8'd4, 8'(OCR_DH), 8'd8, 8'(OCR_AR)}), .MUT(MUT)) u_d2d (
        .clk(clk), .rst_n(rst_n), .t_v(tv), .t_d(td), .t_cr(t_cr), .r_v(r_v), .r_d(r_d), .r_cr(r_cr),
        .tx_up(tx_up), .tx_v(tx_v), .tx_flit(tx_flit), .rx_v(rx_v), .rx_flit(rx_flit), .fault(af), .fault_cause(afc));
    // ---- outputs: RES -> ar, EMBD -> eq (posted: credit back at once), HCTL -> dh ----
    assign ar_v = r_v[0];
    assign ar_d = r_d[0*W +: 519];
    assign eq_v = r_v[1];
    assign eq_d = r_d[1*W +: 512];
    assign dh_v = r_v[2];
    assign dh_d = r_d[2*W +: W];
    reg f_x, f_ovr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tv <= 4'd0; x3_cr <= 1'b0; ea_cr <= 1'b0; dc_cr <= 1'b0; r_cr <= 3'd0;
            tc[0] <= 8'd8; tc[1] <= 8'd8; tc[2] <= 8'd8; tc[3] <= 8'd8;
            f_x <= 1'b0; f_ovr <= 1'b0; fault <= 1'b0; fault_cause <= 8'd0;
        end else begin
            tv <= {epop, xpop && x_kv, xpop && x_q, dpop};
            x3_cr <= xpop; ea_cr <= epop; dc_cr <= dpop;
            tc[0] <= tc[0] - (dpop ? 8'd1 : 8'd0) + (t_cr[0] ? 8'd1 : 8'd0);
            tc[1] <= tc[1] - ((xpop && x_q) ? 8'd1 : 8'd0) + (t_cr[1] ? 8'd1 : 8'd0);
            tc[2] <= tc[2] - ((xpop && x_kv) ? 8'd1 : 8'd0) + (t_cr[2] ? 8'd1 : 8'd0);
            tc[3] <= tc[3] - (epop ? 8'd1 : 8'd0) + (t_cr[3] ? 8'd1 : 8'd0);
            r_cr <= {dh_cr, r_v[1], ar_cr};
            if (xpop && !x_q && !x_kv) f_x <= 1'b1;
            if ((xv && xf && !xpop) || (ev && ef && !epop) || (dv && df && !dpop)) f_ovr <= 1'b1;
            fault_cause <= {1'b0, f_ovr, f_x, afc};
            fault <= af | f_x | f_ovr;
        end
    end
endmodule
