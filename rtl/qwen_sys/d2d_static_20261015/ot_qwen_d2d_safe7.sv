`timescale 1ns/1ps
// QW-D2D3 SAFE7 (10-19): every native root <= 32 loads, by SOURCE structure only (no ODB copying):
//  * KEPT non-parametric leaf modules (route.synth_keep_modules) for every replicated decision, so Yosys cannot merge
//    copies back (ot_d2d_kff / ot_d2d_kffr / ot_d2d_kand_s7 / ot_d2d_kandn_s7 / ot_d2d_kor_s7 / ot_d2d_status_and_s7 /
//    ot_d2d_useful_and_s7);
//  * reset: ot_d2d_rst_tree_s7 = 2-flop face synchroniser + 2 equal-depth plain stages (4 -> NR kept copies), the
//    same assert/release edges as ot_rst_pipe STAGES 2, one copy per <= 32 async-reset flops;
//  * epoch-begin / halt / start / segment / write-enable / advance copies per register group (<= 16 bits each);
//  * one-hot calendar pointer and segment-1 one-hot split into kept twin registers (same D, reset, enables);
//  * calendar table written through a 2-level kept decode (4 x 8-bit lanes per entry).
// Same ports, edges, TXDP and reset timing as qfd_d2d_static_ovl_sf6s / qfd_d2d_static_ovl (lockstep bench).
module ot_d2d_kand_s7(input wire a, b, output wire y);
    assign y = a & b;
endmodule
module ot_d2d_kandn_s7(input wire a, bn, output wire y);
    assign y = a & ~bn;
endmodule
module ot_d2d_kor_s7(input wire a, b, output wire y);
    assign y = a | b;
endmodule
module ot_d2d_status_and_s7(input wire valid, port_match, output wire slot);
    assign slot = valid & port_match;
endmodule
module ot_d2d_useful_and_s7(input wire a, b, output wire y);
    assign y = a & b;
endmodule
// Reset distribution: rst_n_in -> s0, s1 (asynchronous assert, synchronous release, at the face) -> 4 kept stage-A
// flops -> NR kept stage-B flops (copy r from stage-A r % 4).  Equal depth: every rst_n[r] asserts 2 edges after s1
// and releases 2 + 2 edges after rst_n_in (as ot_rst_pipe #(.STAGES(2))).
module ot_d2d_rst_tree_s7 #(parameter integer NR = 36) (
    input  wire          clk,
    input  wire          rst_n_in,
    output wire [NR-1:0] rst_n
);
    (* keep = "true", dont_touch = "true" *) reg s0, s1;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) begin s0 <= 1'b0; s1 <= 1'b0; end
        else begin s0 <= 1'b1; s1 <= s0; end
    wire [3:0] a;
    genvar t;
    for (t = 0; t < 4; t = t + 1) begin : g_a
        ot_d2d_kff u_a (.ck(clk), .d(s1), .q(a[t]));
    end
    for (t = 0; t < NR; t = t + 1) begin : g_b
        ot_d2d_kff u_b (.ck(clk), .d(a[t % 4]), .q(rst_n[t]));
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Slot-store bank (as the SF6S leaf)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_llr_replay_sram_leaf_s7 #(parameter integer SFMUT = 0) (
    input wire ck, we,
    input wire [5:0] wa, ra,
    input wire [136:0] din,
    output reg [136:0] dout
);
    localparam integer W = 137, SW = 12, NS = (W + SW - 1) / SW;   // 12 slices
    reg wq; reg [5:0] aq; reg [W-1:0] dq, dqq;
    wire [W-1:0] mr;
    always @(posedge ck) begin wq <= we; aq <= wa; dq <= din; dqq <= dq; end
    wire h0d;
    ot_d2d_useful_and_s7 u_h0d (.a(we), .b(wa == ra), .y(h0d));
    wire h1d;
    ot_d2d_useful_and_s7 u_h1d (.a(wq), .b(aq == ra), .y(h1d));
    wire [NS-1:0] h0, h1;
    genvar s;
    for (s = 0; s < NS; s = s + 1) begin : g_hit
        // SFMUT 1 (bench negative control): the last slice's age-0 copy compares the wrong age
        ot_d2d_kff u_h0 (.ck(ck), .d((SFMUT == 1 && s == NS - 1) ? h1d : h0d), .q(h0[s]));
        ot_d2d_kff u_h1 (.ck(ck), .d(h1d), .q(h1[s]));
    end
    d2d_sram_1r1w_64x137_m1_r2c2_p192 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in(dq), .w_mask_in({W{1'b1}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(16'd0));
    integer b;
    always @(posedge ck)
        for (b = 0; b < W; b = b + 1) dout[b] <= h0[b / SW] ? dq[b] : h1[b / SW] ? dqq[b] : mr[b];
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Slot control (ot_qwen_static_slot_ctl), SAFE7: register groups with their own reset / epoch-begin copies, kept
// epoch_abort copies (internal / ownership-map + store / exported) and kept ownership-map enables.
// Function and edges identical to ot_qwen_static_slot_ctl_s6s.
//   rst_n [0] control  [1] s1..s4  [2] s1_oh[31:0]  [3] s1_oh[63:32]  [4] e1, e2, es  [5] e3, re  [6] written lo  [7] hi
//   eb_k  [0] control  [1] s1, s2  [2] s3, s4  [6:3] s1_oh quarters  [7] e1, e2  [8] e3, es  [9] written lo  [10] hi
//         [11] re  [12] slot-store write (slot_link)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_static_slot_ctl_s7 #(parameter integer FW = 548, CW = 16, PW = FW + 19 + CW) (
    input wire clk,
    input wire [7:0] rst_n,
    input wire [12:0] eb_k,
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [5:0] wr_slot,
    input wire [5:0] wr_slot_d,     // kept copy of wr_slot for the one-hot decode
    input wire [FW-1:0] q_data,
    input wire rd_v,
    input wire [5:0] rd_slot,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire p_tx_up,
    output reg p_tx_v,
    output reg [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output reg rx_v,
    output reg [FW-1:0] rx_flit,
    output wire epoch_abort,        // kept exported copy
    output wire epoch_abort_w,      // kept copy for the slot-store write enable
    output reg [7:0] fault_cause
);
    wire epoch_begin = eb_k[0];
    reg [63:0] written;
    reg v1,v2,v3,v4,cmd_wv;
    reg cmd_ov;
    reg [5:0] cmd_ws;
    reg [63:0] cmd_oh;
    reg [5:0] s1,s2,s3,s4;
    reg [63:0] s1_oh;
    reg [7:0] e1,e2,e3;
    reg [FW-1:0] q_pin;
    wire [FW+18:0] body={1'b0,e3,1'b0,1'b1,2'b00,s3,q_pin};
    reg rv,ev;
    reg [5:0] es;
    reg [7:0] re;
    reg [PW-1:0] rf;
    reg ea;                         // internal epoch_abort
    wire ea_w;
    wire [CW-1:0] tx_crc, rx_crc;
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_tx_crc(.d(body),.q(tx_crc));
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(rf[FW+18:0]),.q(rx_crc));
    wire crc_bad=rv && ev && (rx_crc!==rf[PW-1-:CW]);
    wire slot_bad=rv && ev && (rf[FW+7:FW]!=={2'b00,es} || rf[FW+17-:8]!==re ||
                         rf[FW+8]!==1'b1 || rf[FW+9]!==1'b0 || rf[FW+18]!==1'b0);
    wire w_at_cmd = |(written & cmd_oh);
    wire w_at_s1  = |(written & s1_oh);
    wire write_collision=cmd_wv && ((v2 && cmd_ws==s2)||(v3 && cmd_ws==s3)||(v4 && cmd_ws==s4)||
        (w_at_cmd && !(v1 && s1==cmd_ws)));
    wire unread_slot=v1 && !w_at_s1 && !(cmd_wv && cmd_ws==s1);
    wire [7:0] new_fault={cmd_wv && (cmd_ov!==1'b1),write_collision,unread_slot,v3 && !p_tx_up,
                          rv && !ev,ev && !rv,slot_bad,crc_bad};
    always @(posedge clk)begin
        cmd_ws<=wr_slot;cmd_ov<=wr_observed_v;
        cmd_oh<=64'd1<<wr_slot_d;
        q_pin<=q_data;
        rf<=p_rx_flit;
        p_tx_flit<={tx_crc,body};
        rx_flit<=rf[FW-1:0];
    end
    // epoch_abort: internal register + two kept copies, same D (reset 0; epoch_begin 0; else sticky on any new fault)
    wire ea_d = epoch_begin ? 1'b0 : (ea | (|new_fault));
    ot_d2d_kffr u_ea_x (.ck(clk), .rst_n(rst_n[0]), .d(ea_d), .q(epoch_abort));
    ot_d2d_kffr u_ea_w (.ck(clk), .rst_n(rst_n[0]), .d(ea_d), .q(ea_w));
    assign epoch_abort_w = ea_w;
    // ownership map: four 16-bit quarters, each set / clear enable a kept copy (cmd_wv && !epoch_abort, v1 && !...)
    wire [3:0] wv_ok, rv_ok;
    genvar h;
    for (h = 0; h < 4; h = h + 1) begin : g_wq
        ot_d2d_kandn_s7 u_wv (.a(cmd_wv), .bn(ea_w), .y(wv_ok[h]));
        ot_d2d_kandn_s7 u_rv (.a(v1), .bn(ea_w), .y(rv_ok[h]));
        always @(posedge clk or negedge rst_n[6 + h/2])
            if (!rst_n[6 + h/2]) written[16*h +: 16] <= 16'd0;
            else if (eb_k[9 + h/2]) written[16*h +: 16] <= 16'd0;
            else written[16*h +: 16] <= (written[16*h +: 16] | (wv_ok[h] ? cmd_oh[16*h +: 16] : 16'd0))
                                        & ~(rv_ok[h] ? s1_oh[16*h +: 16] : 16'd0);
    end
    // control
    always @(posedge clk or negedge rst_n[0])begin
        if(!rst_n[0])begin
            cmd_wv<=0;v1<=0;v2<=0;v3<=0;v4<=0;rv<=0;ev<=0;p_tx_v<=0;rx_v<=0;ea<=0;fault_cause<=0;
        end else if(epoch_begin)begin
            cmd_wv<=0;v1<=0;v2<=0;v3<=0;v4<=0;rv<=0;ev<=0;p_tx_v<=0;rx_v<=0;ea<=0;fault_cause<=0;
        end else begin
            cmd_wv<=wr_v && !ea;
            v1<=rd_v && !ea;v2<=v1;v3<=v2;v4<=v3;
            p_tx_v<=v3 && !ea;
            rv<=p_rx_v;ev<=rx_expect_v;
            rx_v<=ev && rv && !slot_bad && !crc_bad && !ea;
            if(!ea)begin
                fault_cause<=fault_cause|new_fault;
                if(|new_fault)ea<=1'b1;
            end
        end
    end
    // read-slot pipeline (held under epoch_begin)
    always @(posedge clk or negedge rst_n[1])
        if(!rst_n[1])begin s1<=0;s2<=0; end else if(!eb_k[1])begin s1<=rd_slot;s2<=s1; end
    always @(posedge clk or negedge rst_n[1])
        if(!rst_n[1])begin s3<=0;s4<=0; end else if(!eb_k[2])begin s3<=s2;s4<=s3; end
    wire [63:0] rd_oh = 64'd1<<rd_slot;
    for (h = 0; h < 4; h = h + 1) begin : g_s1q
        always @(posedge clk or negedge rst_n[2 + h/2])
            if(!rst_n[2 + h/2]) s1_oh[16*h +: 16] <= (h == 0) ? 16'd1 : 16'd0;
            else if(!eb_k[3 + h]) s1_oh[16*h +: 16] <= rd_oh[16*h +: 16];
    end
    always @(posedge clk or negedge rst_n[4])
        if(!rst_n[4])begin e1<=0;e2<=0; end else if(!eb_k[7])begin e1<=epoch;e2<=e1; end
    always @(posedge clk or negedge rst_n[4])
        if(!rst_n[4]) es<=0; else if(!eb_k[8]) es<=rx_expect_slot;
    always @(posedge clk or negedge rst_n[5])
        if(!rst_n[5]) e3<=0; else if(!eb_k[8]) e3<=e2;
    always @(posedge clk or negedge rst_n[5])
        if(!rst_n[5]) re<=0; else if(!eb_k[11]) re<=epoch;
endmodule

module ot_qwen_static_slot_link_s7 #(parameter integer FW = 548, CW = 16, PW = FW + 19 + CW, SFMUT = 0) (
    input wire [4:0] ck,
    input wire [7:0] rst_n,
    input wire [12:0] eb_k,
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [5:0] wr_slot, wr_slot_m, wr_slot_d,
    input wire [FW-1:0] wr_flit,
    input wire rd_v,
    input wire [5:0] rd_slot,
    input wire rx_expect_v,
    input wire [5:0] rx_expect_slot,
    input wire p_tx_up,
    output wire p_tx_v,
    output wire [PW-1:0] p_tx_flit,
    input wire p_rx_v,
    input wire [PW-1:0] p_rx_flit,
    output wire rx_v,
    output wire [FW-1:0] rx_flit,
    output wire epoch_abort,
    output wire [7:0] fault_cause
);
    localparam integer BW = 137;
    wire [4*BW-1:0] wd = {{(4*BW-FW){1'b0}}, wr_flit};
    wire [4*BW-1:0] rd;
    wire ea_w;
    wire issue_write = wr_v && !ea_w && !eb_k[12];
    genvar b;
    for (b = 0; b < 4; b = b + 1) begin : g_bank
        ot_qkvd_llr_replay_sram_leaf_s7 #(.SFMUT(b == 0 ? SFMUT : 0)) u_store (
            .ck(ck[b+1]), .we(issue_write), .wa(wr_slot_m), .ra(rd_slot), .din(wd[b*BW +: BW]), .dout(rd[b*BW +: BW]));
    end
    ot_qwen_static_slot_ctl_s7 #(.FW(FW), .CW(CW), .PW(PW)) u_ctl (
        .clk(ck[0]), .q_data(rd[FW-1:0]), .rst_n(rst_n), .eb_k(eb_k), .epoch(epoch), .wr_v(wr_v),
        .wr_observed_v(wr_observed_v), .wr_slot(wr_slot), .wr_slot_d(wr_slot_d), .rd_v(rd_v), .rd_slot(rd_slot),
        .rx_expect_v(rx_expect_v), .rx_expect_slot(rx_expect_slot), .p_tx_up(p_tx_up), .p_tx_v(p_tx_v),
        .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit), .rx_v(rx_v), .rx_flit(rx_flit),
        .epoch_abort(epoch_abort), .epoch_abort_w(ea_w), .fault_cause(fault_cause));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Calendar playback (ot_qwen_d2d_cal, NE 32), SAFE7: per-group reset / halt / start / segment / advance copies,
// kept twin one-hot registers (oh / oh_b, s1oh / s1oh_b: low / high 16 table bits), 2-level kept table-write decode.
// Function and edges identical to ot_qwen_d2d_cal_s6s.
//   rst_n  [0] control + ptr + rep/bcur  [1] cur  [2] cnt  [3] oh  [4] oh_b
//   halt_k [0] control + oh + oh_b      [1] cur / cnt / rep / bcur
//   start_k[0] cur[31:18]  [1] cur[17:0] + rep/bcur  [2] oh  [3] control  [4] cnt  [5] oh_b
//   seg_k  [0] first[31:18]  [1] oh_start[15:0]  [2] segment base  [3] first[17:10]  [4] first[9:0]  [5] oh_start[31:16]
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_cal_s7 #(parameter integer SFMUT = 0) (
    input  wire          ck,
    input  wire [4:0]    rst_n,
    input  wire          cfg_we,
    input  wire [5:0]    cfg_addr,
    input  wire [31:0]   cfg_data,
    input  wire [4:0]    cfg_seg,
    input  wire [5:0]    start_k,
    input  wire [5:0]    seg_k,
    input  wire [1:0]    halt_k,
    output reg           ev_v,
    output reg  [2:0]    ev_port,
    output reg  [3:0]    ev_kind,
    output reg  [4:0]    ev_beat,
    output reg           running,
    output reg           fault
);
    localparam integer NE = 32, AW = 5;
    // ---- table: 32 entries x 4 lanes of 8 bits, each lane written by its own kept enable
    wire cwn = cfg_we && !running;
    wire we_t = cwn && !cfg_addr[AW];
    wire [15:0] wg;                       // [q*4 + c]: entry group q (addr[4:3]), lane c
    wire [127:0] wen;                     // [i*4 + c]
    wire [NE*32-1:0] tblf;
    genvar gq, gc, gi;
    for (gq = 0; gq < 4; gq = gq + 1) begin : g_wq
        wire qm = (cfg_addr[4:3] == gq);
        for (gc = 0; gc < 4; gc = gc + 1) begin : g_c
            ot_d2d_kand_s7 u_g (.a(we_t), .b(qm), .y(wg[gq*4 + gc]));
        end
    end
    for (gi = 0; gi < NE; gi = gi + 1) begin : g_tbl
        wire am = (cfg_addr[2:0] == (gi % 8));
        for (gc = 0; gc < 4; gc = gc + 1) begin : g_c
            reg [7:0] tq;
            // SFMUT 5 (bench negative control): lane 2 of every entry decodes the neighbouring entry address
            wire amc = (SFMUT == 5 && gc == 2) ? (cfg_addr[2:0] == ((gi % 8) ^ 1)) : am;
            ot_d2d_kand_s7 u_e (.a(wg[(gi/8)*4 + gc]), .b(amc), .y(wen[gi*4 + gc]));
            always @(posedge ck) if (wen[gi*4 + gc]) tq <= cfg_data[8*gc +: 8];
            assign tblf[gi*32 + 8*gc +: 8] = tq;
        end
    end
    // ---- segment-1 base and its one-hots (s1oh / s1oh_b twins, s1p1oh), each 16-bit half under its own kept enable
    wire [6:0] ws;
    for (gc = 0; gc < 7; gc = gc + 1) begin : g_ws
        ot_d2d_kand_s7 u_w (.a(cwn), .b(cfg_addr[AW]), .y(ws[gc]));
    end
    wire [NE-1:0] dec0 = 32'd1 << cfg_seg;
    wire [NE-1:0] dec1 = 32'd1 << (cfg_seg + 5'd1);
    reg [AW-1:0] seg1;
    reg [NE-1:0] s1oh, s1oh_b, s1p1oh;
    always @(posedge ck) if (ws[0]) s1oh[15:0]    <= dec0[15:0];
    always @(posedge ck) if (ws[1]) s1oh[31:16]   <= dec0[31:16];
    always @(posedge ck) if (ws[2]) s1oh_b[15:0]  <= dec0[15:0];
    always @(posedge ck) if (ws[3]) s1oh_b[31:16] <= dec0[31:16];
    always @(posedge ck) if (ws[4]) s1p1oh[15:0]  <= dec1[15:0];
    always @(posedge ck) if (ws[5]) s1p1oh[31:16] <= dec1[31:16];
    always @(posedge ck) if (ws[6]) seg1 <= cfg_seg;          // cfg_seg = kept copy of cfg_data[4:0], same edge
    // ---- table reads: low lane by oh / s1oh, high lane by the twins
    reg [31:0] first0_q, first1_q;
    reg cfg_recent;
    integer i;
    reg [NE-1:0] oh, oh_b;
    reg [31:0] t1, tn;
    always @* begin
        t1 = 32'd0; tn = 32'd0;
        for (i = 0; i < NE; i = i + 1) begin
            t1[15:0]  = t1[15:0]  | (s1oh[i]   ? tblf[i*32 +: 16]      : 16'd0);
            t1[31:16] = t1[31:16] | (s1oh_b[i] ? tblf[i*32 + 16 +: 16] : 16'd0);
            tn[15:0]  = tn[15:0]  | (oh[i]     ? tblf[i*32 +: 16]      : 16'd0);
            tn[31:16] = tn[31:16] | (oh_b[i]   ? tblf[i*32 + 16 +: 16] : 16'd0);
        end
    end
    always @(posedge ck) begin
        first0_q <= tblf[31:0]; first1_q <= t1;
        cfg_recent <= cfg_we;
    end
    wire [31:0] first;
    assign first[31:18] = seg_k[0] ? first1_q[31:18] : first0_q[31:18];
    assign first[17:10] = seg_k[3] ? first1_q[17:10] : first0_q[17:10];
    assign first[9:0]   = seg_k[4] ? first1_q[9:0]   : first0_q[9:0];
    wire [31:0] nxt = tn;
    wire [AW-1:0] sb = seg_k[2] ? seg1 : {AW{1'b0}};
    wire [NE-1:0] ohs = (SFMUT == 2) ? s1oh : s1p1oh;                       // SFMUT 2: negative control
    wire [NE-1:0] oh_start = {seg_k[5] ? ohs[31:16] : 16'd0, seg_k[1] ? ohs[15:0] : 16'd2};
    reg [31:0] cur;
    reg [13:0] cnt;
    reg [4:0]  rep, bcur;
    reg [AW:0] ptr;
    wire h0 = halt_k[0], h1 = halt_k[1];
    // advance (fire && rep == 0 && !cur[17], not halted): kept copies per register group
    wire nhf = !h1 && running && cnt == 14'd1;
    wire r0n = rep == 5'd0 && !cur[17];
    wire [8:0] adv;   // [0] oh[15:0] [1] oh_b[15:0] [2] cur[31:18] [3] cnt [4] cur[17:10] [5] cur[9:0] [6] rep/bcur
                      // [7] oh[31:16] [8] oh_b[31:16]
    for (gc = 0; gc < 9; gc = gc + 1) begin : g_adv
        ot_d2d_kand_s7 u_a (.a(nhf), .b(r0n), .y(adv[gc]));
    end
    // control (rst_n[0], halt_k[0], start_k[3])
    always @(posedge ck or negedge rst_n[0]) begin
        if (!rst_n[0]) begin
            running <= 1'b0; ev_v <= 1'b0; ev_port <= 3'd0; ev_kind <= 4'd0; ev_beat <= 5'd0; ptr <= 0; fault <= 1'b0;
        end else begin
            ev_v <= 1'b0;
            if (cfg_we && running) fault <= 1'b1;
            if (h0) running <= 1'b0;
            else if (start_k[3]) begin
                if (running || cfg_we || cfg_recent) fault <= 1'b1;
                running <= 1'b1;
                ptr <= {1'b0, sb} + 1'b1;
                if (first[31:18] == 14'd0 || {1'b0, first[9:5]} + {1'b0, first[4:0]} > 6'd31) fault <= 1'b1;
            end else if (running) begin
                if (cnt == 14'd1) begin
                    ev_v <= 1'b1; ev_port <= cur[16:14]; ev_kind <= cur[13:10]; ev_beat <= bcur;
                    if (rep != 5'd0) begin end
                    else if (cur[17]) running <= 1'b0;
                    else begin
                        if (ptr == NE) fault <= 1'b1;
                        if (nxt[31:18] == 14'd0 || {1'b0, nxt[9:5]} + {1'b0, nxt[4:0]} > 6'd31) fault <= 1'b1;
                        ptr <= ptr + 1'b1;
                    end
                end
            end
        end
    end
    // cur[31:18] (rst_n[1], start_k[0], adv[2])
    always @(posedge ck or negedge rst_n[1])
        if (!rst_n[1]) cur[31:18] <= 14'd0;
        else if (!h1 && start_k[0]) cur[31:18] <= first[31:18];
        else if (adv[2]) cur[31:18] <= nxt[31:18];
    // cnt (rst_n[2], start_k[4], adv[3])
    always @(posedge ck or negedge rst_n[2])
        if (!rst_n[2]) cnt <= 14'd0;
        else if (!h1 && start_k[4]) cnt <= first[31:18];
        else if (adv[3]) cnt <= nxt[31:18];
        else if (!h1 && running && cnt != 14'd1) cnt <= cnt - 1'b1;
    // cur[17:0] (rst_n[1], start_k[1], adv[4] / adv[5])
    always @(posedge ck or negedge rst_n[1])
        if (!rst_n[1]) cur[17:10] <= 8'd0;
        else if (!h1 && start_k[1]) cur[17:10] <= first[17:10];
        else if (adv[4]) cur[17:10] <= nxt[17:10];
    always @(posedge ck or negedge rst_n[1])
        if (!rst_n[1]) cur[9:0] <= 10'd0;
        else if (!h1 && start_k[1]) cur[9:0] <= first[9:0];
        else if (adv[5]) cur[9:0] <= nxt[9:0];
    // rep / bcur (rst_n[0], start_k[1], adv[6])
    always @(posedge ck or negedge rst_n[0])
        if (!rst_n[0]) begin rep <= 5'd0; bcur <= 5'd0; end
        else if (!h1 && start_k[1]) begin rep <= first[4:0]; bcur <= first[9:5]; end
        else if (nhf && rep != 5'd0) begin rep <= rep - 5'd1; bcur <= bcur + 5'd1; end
        else if (adv[6]) begin rep <= nxt[4:0]; bcur <= nxt[9:5]; end
    // one-hot pointer twins (rst_n[3] / rst_n[4], start_k[2] / start_k[5], adv[0] / adv[1])
    wire [NE-1:0] oh_rot = {oh[NE-2:0], oh[NE-1]};
    wire [NE-1:0] ohb_rot = (SFMUT == 4) ? {oh_b[0], oh_b[NE-1:1]} : {oh_b[NE-2:0], oh_b[NE-1]};   // SFMUT 4: twin backwards
    always @(posedge ck or negedge rst_n[3])
        if (!rst_n[3]) oh[15:0] <= 16'd1;
        else if (!h0 && start_k[2]) oh[15:0] <= oh_start[15:0];
        else if (adv[0]) oh[15:0] <= oh_rot[15:0];
    always @(posedge ck or negedge rst_n[3])
        if (!rst_n[3]) oh[31:16] <= 16'd0;
        else if (!h0 && start_k[2]) oh[31:16] <= oh_start[31:16];
        else if (adv[7]) oh[31:16] <= oh_rot[31:16];
    always @(posedge ck or negedge rst_n[4])
        if (!rst_n[4]) oh_b[15:0] <= 16'd1;
        else if (!h0 && start_k[5]) oh_b[15:0] <= oh_start[15:0];
        else if (adv[1]) oh_b[15:0] <= ohb_rot[15:0];
    always @(posedge ck or negedge rst_n[4])
        if (!rst_n[4]) oh_b[31:16] <= 16'd0;
        else if (!h0 && start_k[5]) oh_b[31:16] <= oh_start[31:16];
        else if (adv[8]) oh_b[31:16] <= ohb_rot[31:16];
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Link end (ot_qwen_d2d_static_end, NT = NR = 4, OVL = 1), SAFE7: per-group reset / epoch-begin / halt copies,
// kept write-slot copies.  Function and edges identical to ot_qwen_d2d_static_end_s6s.
//   rst_n [4:0] TX cal  [9:5] RX cal  [13:10] capture delay port 0..3  [14] delay lines + user  [15] group A
//         [16] groups B + C  [17] group D  [25:18] slot link (see slot_ctl_s7)
//   eb_k  [0] group A  [1] group B  [2] group C  [3] group D (r1b, rx_beat)  [4] group D2  [17:5] slot link (13)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_static_end_s7 #(
    parameter integer FW = 548, CW = 16, PW = FW + 19 + CW,
    parameter [8*4-1:0] TXD = {8'd1, 8'd1, 8'd2, 8'd1},
    parameter integer SFMUT = 0
) (
    input  wire [4:0]       ck,
    input  wire [25:0]      rst_n,
    input  wire             cfg_tx_we, cfg_rx_we,
    input  wire [5:0]       cfg_addr,
    input  wire [31:0]      cfg_data_t, cfg_data_r,
    input  wire [4:0]       cfg_seg_t, cfg_seg_r,
    input  wire [17:0]      eb_k,
    input  wire [7:0]       epoch,
    input  wire [6:0]       cal_start_k,  // [5:0] TX calendar, [6] TX user latch
    input  wire [5:0]       cal_seg_k,
    input  wire [6:0]       cal_start_rx_k,
    input  wire [5:0]       cal_seg_rx_k,
    input  wire [1:0]       cal_user_tx, cal_user_rx,
    output wire [1:0]       tx_user,
    output reg  [1:0]       rx_user,
    output wire [3:0]       tx_slot,
    output wire [3:0]       tx_kind,
    output wire [4:0]       tx_beat,
    input  wire [3:0]       tx_valid,
    input  wire [4*FW-1:0]  tx_payload,
    output reg  [3:0]       rx_event,
    output reg  [3:0]       rx_slot,
    output reg  [3:0]       rx_kind,
    output reg  [4:0]       rx_beat,
    output wire [FW-1:0]    rx_payload,
    input  wire             p_tx_up,
    output wire             p_tx_v,
    output wire [PW-1:0]    p_tx_flit,
    input  wire             p_rx_v,
    input  wire [PW-1:0]    p_rx_flit,
    output wire             epoch_abort,
    output wire [7:0]       fault_cause,
    output reg              end_fault,
    output wire             cal_running,
    output wire             status_event_valid, status_port_match
);
    localparam integer NT = 4, NR = 4;
    localparam integer SLW = 18, NSL = (FW + SLW - 1) / SLW;   // 31 payload-select slices
    // halt = epoch_abort | end_fault: kept copies [0] / [1] TX cal, [2] / [3] RX cal, [4] this end
    wire [4:0] halt_k;
    genvar p, s;
    for (p = 0; p < 5; p = p + 1) begin : g_halt
        ot_d2d_kor_s7 u_h (.a(epoch_abort), .b(end_fault), .y(halt_k[p]));
    end
    wire halt = halt_k[4];
    wire tv, rv; wire [2:0] tp, rp; wire [3:0] tk, rk; wire [4:0] tb, rb; wire tf, rf, trun, rrun;
    ot_qwen_d2d_cal_s7 #(.SFMUT(SFMUT)) u_txcal (.ck(ck[0]), .rst_n(rst_n[4:0]), .cfg_we(cfg_tx_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data_t), .cfg_seg(cfg_seg_t), .start_k(cal_start_k[5:0]), .seg_k(cal_seg_k), .halt_k(halt_k[1:0]),
        .ev_v(tv), .ev_port(tp), .ev_kind(tk), .ev_beat(tb), .running(trun), .fault(tf));
    ot_qwen_d2d_cal_s7 u_rxcal (.ck(ck[0]), .rst_n(rst_n[9:5]), .cfg_we(cfg_rx_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data_r), .cfg_seg(cfg_seg_r), .start_k(cal_start_rx_k[5:0]), .seg_k(cal_seg_rx_k), .halt_k(halt_k[3:2]),
        .ev_v(rv), .ev_port(rp), .ev_kind(rk), .ev_beat(rb), .running(rrun), .fault(rf));
    assign cal_running = trun | rrun;
    assign status_event_valid = tv;
    assign status_port_match = (tp == 3'd2);
    wire rst_u = rst_n[14], rst_a = rst_n[15], rst_bc = rst_n[16], rst_d = rst_n[17];
    reg [1:0] utx, urx, r1u;
    always @(posedge ck[0] or negedge rst_u)
        if (!rst_u) begin utx <= 2'd0; urx <= 2'd0; end
        else begin if (cal_start_k[6]) utx <= cal_user_tx; if (cal_start_rx_k[6]) urx <= cal_user_rx; end
    assign tx_user = utx;
    for (p = 0; p < NT; p = p + 1) begin : g_slot
        assign tx_slot[p] = tv && tp == p;
    end
    assign tx_kind = tk;
    assign tx_beat = tb;
    wire [NT*NSL-1:0] fk;
    wire [NT-1:0] fire;
    for (p = 0; p < NT; p = p + 1) begin : g_dly
        localparam integer D = TXD[8*p +: 8];
        wire din = tx_slot[p] & ~halt;
        wire last_d;
        if (D > 1) begin : g_pre
            reg [D-2:0] sr;
            always @(posedge ck[0] or negedge rst_u)
                if (!rst_u) sr <= {(D-1){1'b0}};
                else sr <= {sr, din};
            assign last_d = sr[D-2];
        end else begin : g_one
            assign last_d = din;
        end
        for (s = 0; s < NSL; s = s + 1) begin : g_fk
            ot_d2d_kffr u_fk (.ck(ck[0]), .rst_n(rst_n[10 + p]), .d(last_d), .q(fk[p*NSL + s]));
        end
        assign fire[p] = fk[p*NSL];
    end
    integer i, j, k;
    reg [FW-1:0] wsel;
    reg          wobs;
    wire         multi = |(fire & (fire - 1'b1));
    always @* begin
        wsel = {FW{1'b0}}; wobs = 1'b0;
        for (j = 0; j < NT; j = j + 1) begin
            for (k = 0; k < FW; k = k + 1) if (fk[j*NSL + k / SLW]) wsel[k] = wsel[k] | tx_payload[j*FW + k];
            if (fire[j]) wobs = wobs | tx_valid[j];
        end
    end
    wire wr_v = |fire;
    wire stray = |(tx_valid & ~fire);
    reg [5:0] wcnt, rcnt, rslot; reg rd_v;
    reg [5:0] ecnt;
    reg       r1v, r2v; reg [2:0] r1p, r2p; reg [3:0] r1k; reg [4:0] r1b;
    // group A: write counter (+ kept slot copies: wcnt_m = slot-store address, wcnt_d = ownership one-hot decode)
    wire [5:0] wcnt_nx = eb_k[0] ? 6'd0 : (wr_v ? wcnt + 6'd1 : wcnt);
    wire [5:0] wcnt_m, wcnt_d;
    for (s = 0; s < 6; s = s + 1) begin : g_wc
        ot_d2d_kffr u_m (.ck(ck[0]), .rst_n(rst_a), .d(wcnt_nx[s]), .q(wcnt_m[s]));
        ot_d2d_kffr u_d (.ck(ck[0]), .rst_n(rst_a), .d(wcnt_nx[s]), .q(wcnt_d[s]));
    end
    wire [5:0] wslot = wcnt;
    always @(posedge ck[0] or negedge rst_a) begin
        if (!rst_a) begin wcnt <= 0; rcnt <= 0; rd_v <= 0; end_fault <= 0; end
        else if (eb_k[0]) begin wcnt <= 0; rcnt <= 0; rd_v <= 0; end_fault <= 0; end
        else begin
            if (wr_v) wcnt <= wcnt + 6'd1;
            rd_v <= wr_v & ~halt;
            if (stray | multi | tf | rf) end_fault <= 1'b1;
        end
    end
    // group B
    always @(posedge ck[0] or negedge rst_bc) begin
        if (!rst_bc) begin ecnt <= 0; r1v <= 0; r2v <= 0; rx_slot <= 0; end
        else if (eb_k[1]) begin ecnt <= 0; r1v <= 0; r2v <= 0; rx_slot <= 0; end
        else begin
            if (rv) ecnt <= ecnt + 6'd1;
            r1v <= rv; r2v <= r1v;
            for (i = 0; i < NR; i = i + 1) rx_slot[i] <= r1v && r1p == i;
        end
    end
    // group C (held under epoch_begin)
    always @(posedge ck[0] or negedge rst_bc) begin
        if (!rst_bc) begin rslot <= 0; r1p <= 0; r2p <= 0; r1k <= 0; end
        else if (!eb_k[2]) begin rslot <= wslot; r1p <= rp; r2p <= r1p; r1k <= rk; end
    end
    // group D (held under epoch_begin)
    always @(posedge ck[0] or negedge rst_d) begin
        if (!rst_d) begin r1b <= 0; rx_beat <= 0; end
        else if (!eb_k[3]) begin r1b <= rb; rx_beat <= r1b; end
    end
    always @(posedge ck[0] or negedge rst_d) begin
        if (!rst_d) begin rx_kind <= 0; r1u <= 0; rx_user <= 0; end
        else if (!eb_k[4]) begin r1u <= urx; rx_user <= r1u; rx_kind <= r1k; end
    end
    wire lrx_v;
    always @* for (k = 0; k < NR; k = k + 1) rx_event[k] = lrx_v && r2p == k;
    ot_qwen_static_slot_link_s7 #(.FW(FW), .CW(CW), .PW(PW), .SFMUT(SFMUT)) u_link (
        .ck(ck), .rst_n(rst_n[25:18]), .eb_k(eb_k[17:5]), .epoch(epoch),
        .wr_v(wr_v & ~halt), .wr_observed_v(wobs), .wr_slot(wslot), .wr_slot_m(wcnt_m), .wr_slot_d(wcnt_d), .wr_flit(wsel),
        .rd_v(rd_v), .rd_slot(rslot),
        .rx_expect_v(rv), .rx_expect_slot(ecnt),
        .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit),
        .rx_v(lrx_v), .rx_flit(rx_payload), .epoch_abort(epoch_abort), .fault_cause(fault_cause));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// STATUS/RESULT record (as the SF6S status), held-result reset split into 6 kept copies
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_status_tx_s7 #(parameter integer SFMUT = 0) (
    input  wire         ck,
    input  wire [5:0]   rst_h_k,        // held result: [0] pend + slices 0..3, [g] slices 4g..4g+3 (g 1..5)
    input  wire         rst_t,          // TX register (tx_valid, fault)
    input  wire [15:0]  epoch16,
    input  wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    input  wire [21:0]  result_v_k,     // KEPT pin-flop copies of result_v
    input  wire         result_done, result_fault,
    input  wire [3:0]   result_cause,
    input  wire [58:0]  result_tag,
    input  wire [1:0]   result_gen,
    input  wire [17:0]  result_token,
    input  wire [31:0]  result_value, result_cycles,
    input  wire         status_event_valid, status_port_match, tx_slot_canonical,
    input  wire [3:0]   tx_kind,
    output reg          tx_valid,
    output reg  [547:0] tx_payload,
    output reg          fault
);
    wire [15:0] tx_slot_k;
    genvar sk;
    for (sk = 0; sk < 16; sk = sk + 1) begin : g_slot_decode
        ot_d2d_status_and_s7 u_decode (.valid(status_event_valid), .port_match((SFMUT == 3 && sk == 15) ? ~status_port_match : status_port_match), .slot(tx_slot_k[sk]));
    end
    localparam [87:0] R_OWNER = 88'h43210fedcba98765432100;
    localparam integer RS = 7;        // 149-bit held result in 22 slices of <= 7 bits
    reg pend; reg [148:0] r;
    wire [148:0] rin = {result_cycles, result_value, result_token, result_gen, result_tag, result_cause, result_fault, result_done};
    wire result_v = result_v_k[0];
    reg [148:0] rsel;
    integer b;
    always @* for (b = 0; b < 149; b = b + 1) rsel[b] = result_v_k[b / RS] ? rin[b] : r[b];
    wire psel = pend | result_v;
    wire rst_h = rst_h_k[0];
    always @(posedge ck or negedge rst_h) begin
        if (!rst_h) pend <= 0;
        else if (tx_slot_k[15]) pend <= 1'b0;
        else if (result_v) pend <= 1'b1;
    end
    genvar s;
    for (s = 0; s < 22; s = s + 1) begin : g_r
        localparam integer LO = s * RS, HI = (s * RS + RS > 149) ? 149 : s * RS + RS;
        always @(posedge ck or negedge rst_h_k[s / 4]) begin
            if (!rst_h_k[s / 4]) r[HI-1:LO] <= 0;
            else if (!(s == 0 ? tx_slot_canonical : tx_slot_k[R_OWNER[s*4 +: 4]]) && result_v_k[s]) r[HI-1:LO] <= rin[HI-1:LO];
        end
    end
    always @(posedge ck or negedge rst_t) begin
        if (!rst_t) begin tx_valid <= 0; fault <= 0; end
        else begin
            tx_valid <= tx_slot_k[4];
            if (result_v && pend && !tx_slot_k[5]) fault <= 1'b1;
            if (tx_slot_k[5] && tx_kind != 4'd15) fault <= 1'b1;
        end
    end
    // Original unreset payload capture edge, with private actual slot equations.
    wire [547:0] payload_d = {5'd0, 4'd15, 6'd63, epoch16, 5'd0,
                           356'd0, rsel[148:1], rsel[0], psel,
                           admit_ready, execution_active, crom_fault, collective_busy, collective_drained, vm_drained};
    function automatic integer payload_owner(input integer bit_index);
        begin
            case (bit_index)
                0: payload_owner = 6;
                1: payload_owner = 7;
                2: payload_owner = 8;
                3: payload_owner = 9;
                4: payload_owner = 10;
                5: payload_owner = 11;
                6: payload_owner = 12;
                7: payload_owner = 13;
                8: payload_owner = 14;
                9: payload_owner = 15;
                10: payload_owner = 5;
                11: payload_owner = 6;
                12: payload_owner = 7;
                13: payload_owner = 8;
                14: payload_owner = 9;
                15: payload_owner = 10;
                16: payload_owner = 11;
                17: payload_owner = 12;
                18: payload_owner = 13;
                19: payload_owner = 14;
                20: payload_owner = 15;
                21: payload_owner = 4;
                22: payload_owner = 5;
                23: payload_owner = 6;
                24: payload_owner = 7;
                25: payload_owner = 8;
                26: payload_owner = 9;
                27: payload_owner = 10;
                28: payload_owner = 11;
                29: payload_owner = 12;
                30: payload_owner = 13;
                31: payload_owner = 14;
                32: payload_owner = 15;
                33: payload_owner = 4;
                34: payload_owner = 5;
                35: payload_owner = 6;
                36: payload_owner = 7;
                37: payload_owner = 8;
                38: payload_owner = 9;
                39: payload_owner = 10;
                40: payload_owner = 11;
                41: payload_owner = 12;
                42: payload_owner = 13;
                43: payload_owner = 14;
                44: payload_owner = 15;
                45: payload_owner = 4;
                46: payload_owner = 0;
                47: payload_owner = 1;
                48: payload_owner = 2;
                49: payload_owner = 3;
                50: payload_owner = 5;
                51: payload_owner = 6;
                52: payload_owner = 7;
                53: payload_owner = 8;
                54: payload_owner = 9;
                55: payload_owner = 10;
                56: payload_owner = 11;
                57: payload_owner = 12;
                58: payload_owner = 13;
                59: payload_owner = 14;
                60: payload_owner = 15;
                61: payload_owner = 4;
                62: payload_owner = 0;
                63: payload_owner = 1;
                64: payload_owner = 2;
                65: payload_owner = 3;
                66: payload_owner = 5;
                67: payload_owner = 6;
                68: payload_owner = 7;
                69: payload_owner = 8;
                70: payload_owner = 9;
                71: payload_owner = 10;
                72: payload_owner = 11;
                73: payload_owner = 12;
                74: payload_owner = 13;
                75: payload_owner = 14;
                76: payload_owner = 15;
                77: payload_owner = 4;
                78: payload_owner = 0;
                79: payload_owner = 1;
                80: payload_owner = 2;
                81: payload_owner = 3;
                82: payload_owner = 5;
                83: payload_owner = 6;
                84: payload_owner = 7;
                85: payload_owner = 8;
                86: payload_owner = 9;
                87: payload_owner = 10;
                88: payload_owner = 11;
                89: payload_owner = 12;
                90: payload_owner = 13;
                91: payload_owner = 14;
                92: payload_owner = 15;
                93: payload_owner = 4;
                94: payload_owner = 0;
                95: payload_owner = 1;
                96: payload_owner = 2;
                97: payload_owner = 3;
                98: payload_owner = 5;
                99: payload_owner = 6;
                100: payload_owner = 7;
                101: payload_owner = 8;
                102: payload_owner = 9;
                103: payload_owner = 10;
                104: payload_owner = 11;
                105: payload_owner = 12;
                106: payload_owner = 13;
                107: payload_owner = 14;
                108: payload_owner = 15;
                109: payload_owner = 4;
                110: payload_owner = 0;
                111: payload_owner = 1;
                112: payload_owner = 2;
                113: payload_owner = 3;
                114: payload_owner = 5;
                115: payload_owner = 6;
                116: payload_owner = 7;
                117: payload_owner = 8;
                118: payload_owner = 9;
                119: payload_owner = 10;
                120: payload_owner = 11;
                121: payload_owner = 12;
                122: payload_owner = 13;
                123: payload_owner = 14;
                124: payload_owner = 15;
                125: payload_owner = 4;
                126: payload_owner = 0;
                127: payload_owner = 1;
                128: payload_owner = 2;
                129: payload_owner = 3;
                130: payload_owner = 5;
                131: payload_owner = 6;
                132: payload_owner = 7;
                133: payload_owner = 8;
                134: payload_owner = 9;
                135: payload_owner = 10;
                136: payload_owner = 11;
                137: payload_owner = 12;
                138: payload_owner = 13;
                139: payload_owner = 14;
                140: payload_owner = 15;
                141: payload_owner = 4;
                142: payload_owner = 0;
                143: payload_owner = 1;
                144: payload_owner = 2;
                145: payload_owner = 3;
                146: payload_owner = 5;
                147: payload_owner = 6;
                148: payload_owner = 7;
                149: payload_owner = 8;
                150: payload_owner = 9;
                151: payload_owner = 10;
                152: payload_owner = 11;
                153: payload_owner = 12;
                154: payload_owner = 13;
                155: payload_owner = 14;
                517: payload_owner = 15;
                518: payload_owner = 4;
                519: payload_owner = 0;
                520: payload_owner = 1;
                521: payload_owner = 2;
                522: payload_owner = 3;
                523: payload_owner = 5;
                524: payload_owner = 6;
                525: payload_owner = 7;
                526: payload_owner = 8;
                527: payload_owner = 9;
                528: payload_owner = 10;
                529: payload_owner = 11;
                530: payload_owner = 12;
                531: payload_owner = 13;
                532: payload_owner = 14;
                default: payload_owner = 0; // constant payload bits
            endcase
        end
    endfunction
    genvar pb;
    for (pb = 0; pb < 548; pb = pb + 1) begin : g_payload
        always @(posedge ck)
            if (tx_slot_k[payload_owner(pb)]) tx_payload[pb] <= payload_d[pb];
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Compute D2D core, SAFE7 (qfd_d2d_static_core with OVL = 1): reset tree with one region copy per <= 32 async-reset
// flops (equal depth), 24 kept epoch-begin copies.
// reset copies: [0] recovery  [1] epoch-begin copies  [27:2] end (26)  [33:28] STATUS held result  [34] STATUS TX
//               [35] KVN
// epoch-begin copies: [17:0] end  [23:18] STATUS held result groups  [24] KVN   (STATUS TX register uses [23])
// ---------------------------------------------------------------------------------------------------------------------
module qfd_d2d_static_core_s7 #(parameter [31:0] TXDP = {8'd2, 8'd1, 8'd2, 8'd1}, parameter integer SFMUT = 0, parameter integer HEAD_CONTEXT = 0) (
    input  wire         ck,
    input  wire         por_n, rst_n,
    input  wire         cfg_tx_we, cfg_rx_we, input wire [5:0] cfg_addr,
    input  wire [31:0]  cfg_data_t, cfg_data_r, input wire [4:0] cfg_seg_t, cfg_seg_r,
    input  wire [6:0]   cal_start_k, cal_start_rx_k,
    input  wire [5:0]   cal_seg_k, cal_seg_rx_k,
    input  wire [1:0]   cal_user_tx, cal_user_rx,
    output wire [1:0]   tx_user, rx_user,
    input  wire         fwd_epoch,
    input  wire         fwd_link_rst_n,
    output wire         native_tx_slot, output wire [3:0] native_tx_slot_kind, output wire [4:0] native_tx_slot_beat,
    input  wire         native_tx_v, input wire [547:0] native_tx_payload,
    output wire [547:0] rx_payload,
    output wire         native_rx_v,
    output wire         native_rx_slot, output wire [3:0] native_rx_slot_kind, output wire [4:0] native_rx_slot_beat,
    output wire         prog_witness_slot, output wire prog_auth_slot, output wire prog_context_slot,
    output wire         prog_head_context_slot,
    input  wire         prog_tx_observed_v, input wire [547:0] prog_tx_record,
    output wire         prog_rx_v,
    output wire         emb_rx_v, output wire emb_rx_slot,
    output wire         kv_x3_slot,
    input  wire [523:0] x3, input wire [58:0] x3_identity, input wire [1:0] x3_generation,
    input  wire [15:0]  status_epoch16,
    input  wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    input  wire [21:0]  result_v_k,
    input  wire         result_done, result_fault, input wire [3:0] result_cause, input wire [58:0] result_tag,
    input  wire [1:0]   result_gen, input wire [17:0] result_token, input wire [31:0] result_value, result_cycles,
    input  wire         fdi_tx_up, output wire fdi_tx_v, output wire [582:0] fdi_tx_flit,
    input  wire         fdi_rx_v, input wire [582:0] fdi_rx_flit,
    output wire         phy_rst_n,
    output wire         epoch_abort, output wire [7:0] transport_fault, output wire fault
);
    localparam integer NRST = 36, NEB = 25;
    wire [NRST-1:0] lr;
    wire [0:0] local_por_n;
    ot_d2d_rst_tree_s7 #(.NR(NRST)) u_reset_regions (.clk(ck), .rst_n_in(rst_n), .rst_n(lr));
    ot_rst_pipe #(.REGIONS(1), .STAGES(2)) u_por_region (.clk(ck), .rst_n_in(por_n), .rst_n(local_por_n));
    localparam integer FW = 548;
    wire [3:0] txs, rxe, rxs; wire [3:0] tk, rk; wire [4:0] tb, rb; wire [FW-1:0] rxp;
    wire [3:0] tv; wire [4*FW-1:0] tp;
    wire eb, ab, endf, own_rst_n, rec; wire [7:0] ep, fc;
    wire st_f, kvn_f;
    wire status_event_valid, status_port_match;
    ot_qwen_d2d_recovery #(.MASTER(0)) u_rec (.ck(ck), .por_n(local_por_n[0]), .rst_n(lr[0]), .abort(ab | endf),
        .fault_cause(fc), .end_fault(endf), .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_rx_v(fdi_rx_v),
        .reset_req(1'b0), .recovery_clear(1'b0), .boot_begin(1'b0), .fwd_epoch_i(fwd_epoch), .fwd_epoch_o(),
        .fwd_link_rst_n(), .phy_rst_n(own_rst_n), .epoch_begin(eb), .epoch(ep), .link_up(), .links_drained(),
        .link_reset_seen(), .retrained(), .transport_fault(transport_fault), .recovering(rec), .recovery_cycles());
    // epoch_begin copies: copy of the follower strobe capture chain (same D / reset depth as u_rec.fq) and KEPT copies
    reg [2:0] fq_c;
    always @(posedge ck or negedge lr[1]) if (!lr[1]) fq_c <= 3'd0; else fq_c <= {fq_c[1:0], fwd_epoch};
    wire [NEB-1:0] eb_k;
    genvar e;
    for (e = 0; e < NEB; e = e + 1) begin : g_eb
        ot_d2d_kffr u_eb (.ck(ck), .rst_n(lr[1]), .d(fq_c[2]), .q(eb_k[e]));
    end
    assign phy_rst_n = own_rst_n & fwd_link_rst_n;
    ot_qwen_d2d_static_end_s7 #(.TXD(TXDP), .SFMUT(SFMUT)) u_end (
        .ck({5{ck}}), .rst_n(lr[27:2]), .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr),
        .cfg_data_t(cfg_data_t), .cfg_data_r(cfg_data_r), .cfg_seg_t(cfg_seg_t), .cfg_seg_r(cfg_seg_r),
        .eb_k(eb_k[17:0]), .epoch(ep), .cal_start_k(cal_start_k), .cal_seg_k(cal_seg_k),
        .cal_start_rx_k(cal_start_rx_k), .cal_seg_rx_k(cal_seg_rx_k), .cal_user_tx(cal_user_tx), .cal_user_rx(cal_user_rx),
        .tx_user(tx_user), .rx_user(rx_user),
        .tx_slot(txs), .tx_kind(tk), .tx_beat(tb), .tx_valid(tv), .tx_payload(tp),
        .rx_event(rxe), .rx_slot(rxs), .rx_kind(rk), .rx_beat(rb), .rx_payload(rxp),
        .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_tx_flit(fdi_tx_flit), .p_rx_v(fdi_rx_v), .p_rx_flit(fdi_rx_flit),
        .epoch_abort(ab), .fault_cause(fc), .end_fault(endf), .cal_running(),
        .status_event_valid(status_event_valid), .status_port_match(status_port_match));
    assign epoch_abort = ab;
    assign native_tx_slot = txs[0]; assign native_tx_slot_kind = tk; assign native_tx_slot_beat = tb;
    assign tv[0] = native_tx_v; assign tp[0 +: FW] = native_tx_payload;
    assign rx_payload = rxp;
    assign native_rx_v = rxe[0];
    assign native_rx_slot = rxs[0]; assign native_rx_slot_kind = rk; assign native_rx_slot_beat = rb;
    assign prog_witness_slot = txs[1] && (HEAD_CONTEXT == 0 || tk == 4'd14);
    assign prog_head_context_slot = HEAD_CONTEXT != 0 && txs[1] && tk == 4'd12;
    assign tv[1] = prog_tx_observed_v; assign tp[FW +: FW] = prog_tx_record;
    assign prog_rx_v = rxe[1];
    assign emb_rx_v = rxe[2]; assign emb_rx_slot = rxs[2];
    assign prog_auth_slot = rxs[1] && rk == 4'd13;
    assign prog_context_slot = rxs[1] && rk == 4'd12;
    // STATUS resets: held-result groups and TX register, each = region copy & ~epoch_begin copy (as rst_n & ~eb)
    wire [5:0] st_rh;
    for (e = 0; e < 6; e = e + 1) begin : g_strh
        ot_d2d_kandn_s7 u_r (.a(lr[28 + e]), .bn(eb_k[18 + e]), .y(st_rh[e]));
    end
    wire st_rt;
    ot_d2d_kandn_s7 u_strt (.a(lr[34]), .bn(eb_k[23]), .y(st_rt));
    ot_qwen_d2d_status_tx_s7 #(.SFMUT(SFMUT)) u_st (.ck(ck), .rst_h_k(st_rh), .rst_t(st_rt), .epoch16(status_epoch16),
        .vm_drained(vm_drained), .collective_drained(collective_drained), .collective_busy(collective_busy),
        .crom_fault(crom_fault), .execution_active(execution_active), .admit_ready(admit_ready),
        .result_v_k(result_v_k), .result_done(result_done), .result_fault(result_fault), .result_cause(result_cause),
        .result_tag(result_tag), .result_gen(result_gen), .result_token(result_token), .result_value(result_value),
        .result_cycles(result_cycles), .tx_slot_canonical(txs[2]), .status_event_valid(status_event_valid),
        .status_port_match(status_port_match), .tx_kind(tk), .tx_valid(tv[2]), .tx_payload(tp[2*FW +: FW]),
        .fault(st_f));
    assign kv_x3_slot = txs[3];
    ot_qwen_d2d_kvn_tx u_kvn (.ck(ck), .rst_n(lr[35] & ~eb_k[24]), .x3(x3), .x3_identity(x3_identity),
        .x3_generation(x3_generation), .tx_valid(tv[3]), .tx_payload(tp[3*FW +: FW]), .fault(kvn_f));
    assign fault = endf | st_f | kvn_f;
endmodule
