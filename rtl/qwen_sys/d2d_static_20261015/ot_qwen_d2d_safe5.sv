`timescale 1ns/1ps
// =====================================================================================================================
// QW-D2D SAFE5 (2026-10-19): structurally safe compute D2D end, opt-in through qfd_d2d_static_ovl #(.SF(1)).
// Same function, same edges, same ports as the SF = 0 master (qfd_d2d_static_core + ot_qwen_d2d_static_end): every
// change below is a register COPY (same D / clock / reset as the register it copies) or a ONE-HOT re-encoding of an
// existing binary register (same update edge), so every output is cycle-identical (bench: tb_qfd_d2d_sf_equiv).
// Why (safe-design checklist items 3/5/6; native census of the r9j/mu1 netlist, codex 34d769077 / 8ed89673e):
//   * slot-store SRAM 64x512 used 137 of 512 columns; its faces carried 793 pins at 10.4/um.  Now the right-sized
//     ot_sram_1r1w_64x137_m1_r2c2_p192 (57.9 x 45.7 um, 229 pins / face at 0.192 um = 5.2/um).
//   * bypass selects hit_age0/1 drove 548 / 1072 loads (opt_merge folded the 4 banks' identical compares): now 5
//     KEPT copies per age per bank (<= 28 data bits each).
//   * calendar table read: binary ptr[1] / seg1[1] drove ~900 / ~1027 mux loads.  Now a registered one-hot pointer
//     (oh32, 32 loads per bit) and a one-hot segment-1 base (s1oh / s1p1oh) written with seg1; the binary ptr keeps
//     only the increment / overrun check.  Start / segment selects arrive as KEPT pin-flop copies (<= 32 loads each).
//   * producer capture delays fire[p] drove 374-553 payload-select loads: last stage replicated per 18-bit slice.
//   * slot ownership map written[]: cmd_ws / s1 binary decode (73-76 loads) -> registered one-hot cmd_oh / s1_oh.
//   * result_v (302 loads) -> 10 KEPT pin-flop copies, one per 15-bit slice of the held result.
//   * epoch_begin (215 loads) -> KEPT copies built from a copy of the follower strobe chain (same D, same reset).
//   * cfg_data (66 loads) -> one KEPT pin-flop copy per calendar (+ a 5-bit copy per calendar for the base decode).
//   * STATUS tx_payload loses its reset: it is observed only on the capture edge after a tx_slot, which always
//     reloads it (the KVN payload rule); tx_valid / fault / pend / r keep theirs.
// Keep: ot_d2d_kff / ot_d2d_kffr are non-parameterised leaf modules listed in the kit's route.synth_keep_modules,
// so synthesis never merges a copy back into its sibling (paramod-rename trap, memory yosys-keep-parameterised).
// =====================================================================================================================
module ot_d2d_kff (input wire ck, input wire d, output reg q);
    always @(posedge ck) q <= d;
endmodule
module ot_d2d_kffr (input wire ck, input wire rst_n, input wire d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Slot-store bank: right-sized sparse-pin SRAM + per-slice bypass-select copies (ot_qkvd_llr_replay_sram_leaf, W 137)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_llr_replay_sram_leaf_s #(parameter integer SFMUT = 0) (
    input wire ck, we,
    input wire [5:0] wa, ra,
    input wire [136:0] din,
    output reg [136:0] dout
);
    localparam integer W = 137, SW = 28, NS = (W + SW - 1) / SW;   // 5 slices
    reg wq; reg [5:0] aq; reg [W-1:0] dq, dqq;
    wire [W-1:0] mr;
    always @(posedge ck) begin wq <= we; aq <= wa; dq <= din; dqq <= dq; end
    wire h0d = we && wa == ra;
    wire h1d = wq && aq == ra;
    wire [NS-1:0] h0, h1;
    genvar s;
    for (s = 0; s < NS; s = s + 1) begin : g_hit
        // SFMUT 1 (bench negative control): the last slice's age-0 copy compares the wrong age
        ot_d2d_kff u_h0 (.ck(ck), .d((SFMUT == 1 && s == NS - 1) ? h1d : h0d), .q(h0[s]));
        ot_d2d_kff u_h1 (.ck(ck), .d(h1d), .q(h1[s]));
    end
    ot_sram_1r1w_64x137_m1_r2c2_p192 u_sram (
        .clk(ck), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(mr),
        .w_ce_in(wq), .w_addr_in(aq), .wd_in(dq), .w_mask_in({W{1'b1}}),
        .rr_en(2'd0), .rr_addr(12'd0), .cr_en(2'd0), .cr_sel(16'd0));
    integer b;
    always @(posedge ck)
        for (b = 0; b < W; b = b + 1) dout[b] <= h0[b / SW] ? dq[b] : h1[b / SW] ? dqq[b] : mr[b];
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Slot control: ot_qwen_static_slot_ctl with the ownership map indexed by registered one-hot slots
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_static_slot_ctl_s #(parameter integer FW = 548, CW = 16, PW = FW + 19 + CW) (
    input wire clk,
    input wire rst_n,
    input wire [3:0] eb_k,          // epoch_begin copies: [0] control, [1] written[31:0], [2] written[63:32], [3] spare-free
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [5:0] wr_slot,
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
    output reg epoch_abort,
    output reg [7:0] fault_cause
);
    wire epoch_begin = eb_k[0];
    reg [63:0] written;
    reg v1,v2,v3,v4,cmd_wv;
    reg cmd_ov;
    reg [5:0] cmd_ws;
    reg [63:0] cmd_oh;             // one-hot of cmd_ws (same edge, same D source)
    reg [5:0] s1,s2,s3,s4;
    reg [63:0] s1_oh;              // one-hot of s1 (same reset / hold / load as s1)
    reg [7:0] e1,e2,e3;
    reg [FW-1:0] q_pin;
    wire [FW+18:0] body={1'b0,e3,1'b0,1'b1,2'b00,s3,q_pin};
    reg rv,ev;
    reg [5:0] es;
    reg [7:0] re;
    reg [PW-1:0] rf;
    wire [CW-1:0] tx_crc, rx_crc;
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_tx_crc(.d(body),.q(tx_crc));
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(CW)) u_rx_crc(.d(rf[FW+18:0]),.q(rx_crc));
    wire crc_bad=rv && ev && (rx_crc!==rf[PW-1-:CW]);
    wire slot_bad=rv && ev && (rf[FW+7:FW]!=={2'b00,es} || rf[FW+17-:8]!==re ||
                         rf[FW+8]!==1'b1 || rf[FW+9]!==1'b0 || rf[FW+18]!==1'b0);
    wire w_at_cmd = |(written & cmd_oh);   // = written[cmd_ws]
    wire w_at_s1  = |(written & s1_oh);    // = written[s1]
    wire write_collision=cmd_wv && ((v2 && cmd_ws==s2)||(v3 && cmd_ws==s3)||(v4 && cmd_ws==s4)||
        (w_at_cmd && !(v1 && s1==cmd_ws)));
    wire unread_slot=v1 && !w_at_s1 && !(cmd_wv && cmd_ws==s1);
    wire [7:0] new_fault={cmd_wv && (cmd_ov!==1'b1),write_collision,unread_slot,v3 && !p_tx_up,
                          rv && !ev,ev && !rv,slot_bad,crc_bad};
    always @(posedge clk)begin
        cmd_ws<=wr_slot;cmd_ov<=wr_observed_v;
        cmd_oh<=64'd1<<wr_slot;
        q_pin<=q_data;
        rf<=p_rx_flit;
        p_tx_flit<={tx_crc,body};
        rx_flit<=rf[FW-1:0];
    end
    // ownership map: two halves, each with its own epoch_begin copy (same function as written[cmd_ws] <= 1 then
    // written[s1] <= 0 in one block: the clear wins on the same slot)
    genvar h;
    for (h = 0; h < 2; h = h + 1) begin : g_wh
        always @(posedge clk or negedge rst_n)
            if (!rst_n) written[32*h +: 32] <= 32'd0;
            else if (eb_k[1+h]) written[32*h +: 32] <= 32'd0;
            else written[32*h +: 32] <= (written[32*h +: 32] | ((cmd_wv && !epoch_abort) ? cmd_oh[32*h +: 32] : 32'd0))
                                        & ~((v1 && !epoch_abort) ? s1_oh[32*h +: 32] : 32'd0);
    end
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            cmd_wv<=0;v1<=0;v2<=0;v3<=0;v4<=0;s1<=0;s1_oh<=64'd1;s2<=0;s3<=0;s4<=0;e1<=0;e2<=0;e3<=0;
            rv<=0;ev<=0;es<=0;re<=0;
            p_tx_v<=0;rx_v<=0;
            epoch_abort<=0;fault_cause<=0;
        end else if(epoch_begin)begin
            cmd_wv<=0;v1<=0;v2<=0;v3<=0;v4<=0;rv<=0;ev<=0;
            p_tx_v<=0;rx_v<=0;epoch_abort<=0;fault_cause<=0;
        end else begin
            cmd_wv<=wr_v && !epoch_abort;
            v1<=rd_v && !epoch_abort;v2<=v1;v3<=v2;v4<=v3;
            s1<=rd_slot;s1_oh<=64'd1<<rd_slot;s2<=s1;s3<=s2;s4<=s3;e1<=epoch;e2<=e1;e3<=e2;
            p_tx_v<=v3 && !epoch_abort;
            rv<=p_rx_v;ev<=rx_expect_v;
            es<=rx_expect_slot;re<=epoch;
            rx_v<=ev && rv && !slot_bad && !crc_bad && !epoch_abort;
            if(!epoch_abort)begin
                fault_cause<=fault_cause|new_fault;
                if(|new_fault)epoch_abort<=1'b1;
            end
        end
    end
endmodule

module ot_qwen_static_slot_link_s #(parameter integer FW = 548, CW = 16, PW = FW + 19 + CW, SFMUT = 0) (
    input wire [4:0] ck,
    input wire rst_n,
    input wire [3:0] eb_k,
    input wire [7:0] epoch,
    input wire wr_v, wr_observed_v,
    input wire [5:0] wr_slot,
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
    wire issue_write = wr_v && !epoch_abort && !eb_k[3];
    genvar b;
    for (b = 0; b < 4; b = b + 1) begin : g_bank
        ot_qkvd_llr_replay_sram_leaf_s #(.SFMUT(b == 0 ? SFMUT : 0)) u_store (
            .ck(ck[b+1]), .we(issue_write), .wa(wr_slot), .ra(rd_slot), .din(wd[b*BW +: BW]), .dout(rd[b*BW +: BW]));
    end
    ot_qwen_static_slot_ctl_s #(.FW(FW), .CW(CW), .PW(PW)) u_ctl (
        .clk(ck[0]), .q_data(rd[FW-1:0]), .rst_n(rst_n), .eb_k(eb_k), .epoch(epoch), .wr_v(wr_v),
        .wr_observed_v(wr_observed_v), .wr_slot(wr_slot), .rd_v(rd_v), .rd_slot(rd_slot), .rx_expect_v(rx_expect_v),
        .rx_expect_slot(rx_expect_slot), .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v),
        .p_rx_flit(p_rx_flit), .rx_v(rx_v), .rx_flit(rx_flit), .epoch_abort(epoch_abort), .fault_cause(fault_cause));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Calendar playback (ot_qwen_d2d_cal, NE 32) with one-hot table reads and copied start / segment selects
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_cal_s #(parameter integer SFMUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          cfg_we,
    input  wire [5:0]    cfg_addr,
    input  wire [31:0]   cfg_data,       // this calendar's own copy (tbl entries)
    input  wire [4:0]    cfg_seg,        // this calendar's own copy of cfg_data[4:0] (segment-1 base decode)
    input  wire [3:0]    start_k,        // copies of the compiled start strobe
    input  wire [2:0]    seg_k,          // copies of the segment select
    input  wire          halt,
    output reg           ev_v,
    output reg  [2:0]    ev_port,
    output reg  [3:0]    ev_kind,
    output reg  [4:0]    ev_beat,
    output reg           running,
    output reg           fault
);
    localparam integer NE = 32, AW = 5;
    reg [31:0]   tbl [0:NE-1];
    reg [31:0]   cur;
    reg [13:0]   cnt;
    reg [4:0]    rep, bcur;
    reg [AW:0]   ptr;              // binary: increment + overrun check only
    reg [NE-1:0] oh;               // one-hot of ptr[AW-1:0]
    reg [AW-1:0] seg1;
    reg [NE-1:0] s1oh, s1p1oh;     // one-hot of seg1 and of (seg1 + 1) mod 32, written with seg1
    always @(posedge ck) if (cfg_we && !running) begin
        if (cfg_addr[AW]) begin
            seg1 <= cfg_data[AW-1:0];
            s1oh <= 32'd1 << cfg_seg;
            s1p1oh <= 32'd1 << (cfg_seg + 5'd1);
        end else tbl[cfg_addr[AW-1:0]] <= cfg_data;
    end
    reg [31:0] first0_q, first1_q;
    reg cfg_recent;
    integer i;
    reg [31:0] t1, tn;
    always @* begin
        t1 = 32'd0; tn = 32'd0;
        for (i = 0; i < NE; i = i + 1) begin
            t1 = t1 | (s1oh[i] ? tbl[i] : 32'd0);
            tn = tn | (oh[i] ? tbl[i] : 32'd0);
        end
    end
    always @(posedge ck) begin
        first0_q <= tbl[0]; first1_q <= t1;
        cfg_recent <= cfg_we;
    end
    wire [31:0] first = seg_k[0] ? first1_q : first0_q;
    wire [31:0] nxt = tn;
    wire [AW-1:0] sb = seg_k[2] ? seg1 : {AW{1'b0}};
    wire [NE-1:0] oh_start = seg_k[1] ? ((SFMUT == 2) ? s1oh : s1p1oh) : 32'd2;   // SFMUT 2: negative control
    wire fire = running && cnt == 14'd1;
    wire take = fire && rep == 5'd0 && !cur[17];
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0; ev_v <= 1'b0; ev_port <= 3'd0; ev_kind <= 4'd0; ev_beat <= 5'd0;
            cur <= 32'd0; cnt <= 14'd0; ptr <= 0; oh <= 32'd1; fault <= 1'b0; rep <= 5'd0; bcur <= 5'd0;
        end else begin
            ev_v <= 1'b0;
            if (cfg_we && running) fault <= 1'b1;
            if (halt) running <= 1'b0;
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
            // datapath registers, each group under its own start copy (same priority: halt, start, running)
            if (!halt && start_k[0]) begin cur[31:18] <= first[31:18]; cnt <= first[31:18]; end
            else if (!halt && running) begin
                if (cnt == 14'd1) begin
                    if (rep == 5'd0 && !cur[17]) begin cur[31:18] <= nxt[31:18]; cnt <= nxt[31:18]; end
                end else cnt <= cnt - 1'b1;
            end
            if (!halt && start_k[1]) begin cur[17:0] <= first[17:0]; rep <= first[4:0]; bcur <= first[9:5]; end
            else if (!halt && fire) begin
                if (rep != 5'd0) begin rep <= rep - 5'd1; bcur <= bcur + 5'd1; end
                else if (!cur[17]) begin cur[17:0] <= nxt[17:0]; rep <= nxt[4:0]; bcur <= nxt[9:5]; end
            end
            if (!halt && start_k[2]) oh <= oh_start;
            else if (!halt && take) oh <= {oh[NE-2:0], oh[NE-1]};
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Link end (ot_qwen_d2d_static_end, NT = NR = 4, OVL = 1, NRC = 4) with the SAFE5 structures
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_static_end_s #(
    parameter integer FW = 548, CW = 16, PW = FW + 19 + CW,
    parameter [8*4-1:0] TXD = {8'd1, 8'd1, 8'd2, 8'd1},
    parameter integer SFMUT = 0
) (
    input  wire [4:0]       ck,
    input  wire [3:0]       rst_n,        // [0] TX calendar, [1] control, [2] slot link, [3] RX calendar
    input  wire             cfg_tx_we, cfg_rx_we,
    input  wire [5:0]       cfg_addr,
    input  wire [31:0]      cfg_data_t, cfg_data_r,
    input  wire [4:0]       cfg_seg_t, cfg_seg_r,
    input  wire [4:0]       eb_k,         // epoch_begin copies: [0] end control, [4:1] slot link (see slot_ctl_s)
    input  wire [7:0]       epoch,
    input  wire [4:0]       cal_start_k,  // [3:0] TX calendar, [4] TX user latch
    input  wire [2:0]       cal_seg_k,
    input  wire [4:0]       cal_start_rx_k,
    input  wire [2:0]       cal_seg_rx_k,
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
    output wire             cal_running
);
    localparam integer NT = 4, NR = 4;
    localparam integer SLW = 18, NSL = (FW + SLW - 1) / SLW;   // 31 payload-select slices
    wire epoch_begin = eb_k[0];
    wire halt = epoch_abort | end_fault;
    wire rst_tc = rst_n[0], rst_cl = rst_n[1], rst_lk = rst_n[2], rst_rc = rst_n[3];
    wire tv, rv; wire [2:0] tp, rp; wire [3:0] tk, rk; wire [4:0] tb, rb; wire tf, rf, trun, rrun;
    ot_qwen_d2d_cal_s #(.SFMUT(SFMUT)) u_txcal (.ck(ck[0]), .rst_n(rst_tc), .cfg_we(cfg_tx_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data_t), .cfg_seg(cfg_seg_t), .start_k(cal_start_k[3:0]), .seg_k(cal_seg_k), .halt(halt),
        .ev_v(tv), .ev_port(tp), .ev_kind(tk), .ev_beat(tb), .running(trun), .fault(tf));
    ot_qwen_d2d_cal_s u_rxcal (.ck(ck[0]), .rst_n(rst_rc), .cfg_we(cfg_rx_we), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data_r), .cfg_seg(cfg_seg_r), .start_k(cal_start_rx_k[3:0]), .seg_k(cal_seg_rx_k), .halt(halt),
        .ev_v(rv), .ev_port(rp), .ev_kind(rk), .ev_beat(rb), .running(rrun), .fault(rf));
    assign cal_running = trun | rrun;
    reg [1:0] utx, urx, r1u;
    always @(posedge ck[0] or negedge rst_cl)
        if (!rst_cl) begin utx <= 2'd0; urx <= 2'd0; end
        else begin if (cal_start_k[4]) utx <= cal_user_tx; if (cal_start_rx_k[4]) urx <= cal_user_rx; end
    assign tx_user = utx;
    genvar p, s;
    for (p = 0; p < NT; p = p + 1) begin : g_slot
        assign tx_slot[p] = tv && tp == p;
    end
    assign tx_kind = tk;
    assign tx_beat = tb;
    // per-port fixed capture delay; the LAST stage is replicated once per 18-bit payload slice (copy 0 also feeds the
    // valid / stray / collision logic), so no fire flop drives more than ~24 loads
    wire [NT*NSL-1:0] fk;
    wire [NT-1:0] fire;
    for (p = 0; p < NT; p = p + 1) begin : g_dly
        localparam integer D = TXD[8*p +: 8];
        wire din = tx_slot[p] & ~halt;
        wire last_d;
        if (D > 1) begin : g_pre
            reg [D-2:0] sr;
            always @(posedge ck[0] or negedge rst_cl)
                if (!rst_cl) sr <= {(D-1){1'b0}};
                else sr <= {sr, din};
            assign last_d = sr[D-2];
        end else begin : g_one
            assign last_d = din;
        end
        for (s = 0; s < NSL; s = s + 1) begin : g_fk
            ot_d2d_kffr u_fk (.ck(ck[0]), .rst_n(rst_cl), .d(last_d), .q(fk[p*NSL + s]));
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
    wire [5:0] wslot = wcnt;
    reg [5:0] ecnt;
    reg       r1v, r2v; reg [2:0] r1p, r2p; reg [3:0] r1k; reg [4:0] r1b;
    always @(posedge ck[0] or negedge rst_cl) begin
        if (!rst_cl) begin
            wcnt <= 0; rcnt <= 0; rslot <= 0; rd_v <= 0; ecnt <= 0; end_fault <= 0;
            r1v <= 0; r2v <= 0; r1p <= 0; r2p <= 0; r1k <= 0; r1b <= 0;
            rx_slot <= 0; rx_kind <= 0; rx_beat <= 0; r1u <= 0; rx_user <= 0;
        end else if (epoch_begin) begin
            wcnt <= 0; rcnt <= 0; rd_v <= 0; ecnt <= 0; end_fault <= 0; r1v <= 0; r2v <= 0;
            rx_slot <= 0;
        end else begin
            if (wr_v) wcnt <= wcnt + 6'd1;
            rd_v <= wr_v & ~halt; rslot <= wslot;
            if (rv) ecnt <= ecnt + 6'd1;
            if (stray | multi | tf | rf) end_fault <= 1'b1;
            r1v <= rv; r1p <= rp; r1k <= rk; r1b <= rb; r1u <= urx; rx_user <= r1u;
            r2v <= r1v; r2p <= r1p;
            rx_kind <= r1k; rx_beat <= r1b;
            for (i = 0; i < NR; i = i + 1) rx_slot[i] <= r1v && r1p == i;
        end
    end
    wire lrx_v;
    always @* for (k = 0; k < NR; k = k + 1) rx_event[k] = lrx_v && r2p == k;
    ot_qwen_static_slot_link_s #(.FW(FW), .CW(CW), .PW(PW), .SFMUT(SFMUT)) u_link (
        .ck(ck), .rst_n(rst_lk), .eb_k(eb_k[4:1]), .epoch(epoch),
        .wr_v(wr_v & ~halt), .wr_observed_v(wobs), .wr_slot(wslot), .wr_flit(wsel),
        .rd_v(rd_v), .rd_slot(rslot),
        .rx_expect_v(rv), .rx_expect_slot(ecnt),
        .p_tx_up(p_tx_up), .p_tx_v(p_tx_v), .p_tx_flit(p_tx_flit), .p_rx_v(p_rx_v), .p_rx_flit(p_rx_flit),
        .rx_v(lrx_v), .rx_flit(rx_payload), .epoch_abort(epoch_abort), .fault_cause(fault_cause));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// STATUS/RESULT record (ot_qwen_d2d_status_tx, NRC 2) with result_v copies per held-result slice
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_status_tx_s (
    input  wire         ck,
    input  wire [1:0]   rst_n,          // [0] held result (pend, r), [1] TX register (tx_valid, fault)
    input  wire [15:0]  epoch16,
    input  wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    input  wire [9:0]   result_v_k,     // KEPT pin-flop copies of result_v
    input  wire         result_done, result_fault,
    input  wire [3:0]   result_cause,
    input  wire [58:0]  result_tag,
    input  wire [1:0]   result_gen,
    input  wire [17:0]  result_token,
    input  wire [31:0]  result_value, result_cycles,
    input  wire         tx_slot,
    input  wire [3:0]   tx_kind,
    output reg          tx_valid,
    output reg  [547:0] tx_payload,
    output reg          fault
);
    localparam integer RS = 15;        // 149-bit held result in 10 slices of <= 15 bits
    reg pend; reg [148:0] r;
    wire [148:0] rin = {result_cycles, result_value, result_token, result_gen, result_tag, result_cause, result_fault, result_done};
    wire result_v = result_v_k[0];
    reg [148:0] rsel;
    integer b;
    always @* for (b = 0; b < 149; b = b + 1) rsel[b] = result_v_k[b / RS] ? rin[b] : r[b];
    wire psel = pend | result_v;
    wire rst_h = rst_n[0], rst_t = rst_n[1];
    always @(posedge ck or negedge rst_h) begin
        if (!rst_h) pend <= 0;
        else if (tx_slot) pend <= 1'b0;
        else if (result_v) pend <= 1'b1;
    end
    genvar s;
    for (s = 0; s < 10; s = s + 1) begin : g_r
        localparam integer LO = s * RS, HI = (s * RS + RS > 149) ? 149 : s * RS + RS;
        always @(posedge ck or negedge rst_h) begin
            if (!rst_h) r[HI-1:LO] <= 0;
            else if (!tx_slot && result_v_k[s]) r[HI-1:LO] <= rin[HI-1:LO];
        end
    end
    always @(posedge ck or negedge rst_t) begin
        if (!rst_t) begin tx_valid <= 0; fault <= 0; end
        else begin
            tx_valid <= tx_slot;
            if (result_v && pend && !tx_slot) fault <= 1'b1;
            if (tx_slot && tx_kind != 4'd15) fault <= 1'b1;
        end
    end
    // payload: no reset (observed only at the capture edge after a tx_slot, which reloads it)
    always @(posedge ck)
        if (tx_slot)
            tx_payload <= {5'd0, 4'd15, 6'd63, epoch16, 5'd0,
                           356'd0, rsel[148:1], rsel[0], psel,
                           admit_ready, execution_active, crom_fault, collective_busy, collective_drained, vm_drained};
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Compute D2D core, SAFE5 (qfd_d2d_static_core with OVL = 1, RC = 1)
// ---------------------------------------------------------------------------------------------------------------------
module qfd_d2d_static_core_s #(parameter [31:0] TXDP = {8'd2, 8'd1, 8'd2, 8'd1}, parameter integer SFMUT = 0) (
    input  wire         ck,
    input  wire         por_n, rst_n,
    input  wire         cfg_tx_we, cfg_rx_we, input wire [5:0] cfg_addr,
    input  wire [31:0]  cfg_data_t, cfg_data_r, input wire [4:0] cfg_seg_t, cfg_seg_r,
    input  wire [4:0]   cal_start_k, cal_start_rx_k,
    input  wire [2:0]   cal_seg_k, cal_seg_rx_k,
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
    input  wire         prog_tx_observed_v, input wire [547:0] prog_tx_record,
    output wire         prog_rx_v,
    output wire         emb_rx_v, output wire emb_rx_slot,
    output wire         kv_x3_slot,
    input  wire [523:0] x3, input wire [58:0] x3_identity, input wire [1:0] x3_generation,
    input  wire [15:0]  status_epoch16,
    input  wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    input  wire [9:0]   result_v_k,
    input  wire         result_done, result_fault, input wire [3:0] result_cause, input wire [58:0] result_tag,
    input  wire [1:0]   result_gen, input wire [17:0] result_token, input wire [31:0] result_value, result_cycles,
    input  wire         fdi_tx_up, output wire fdi_tx_v, output wire [582:0] fdi_tx_flit,
    input  wire         fdi_rx_v, input wire [582:0] fdi_rx_flit,
    output wire         phy_rst_n,
    output wire         epoch_abort, output wire [7:0] transport_fault, output wire fault
);
    // reset regions as RC = 1: [0] recovery, [1] end TX calendar, [2] STATUS held result, [3] KVN, [4] end control,
    // [5] end slot link, [6] end RX calendar, [7] STATUS TX register
    wire [7:0] local_rst_n;
    wire [0:0] local_por_n;
    ot_rst_pipe #(.REGIONS(8), .STAGES(2)) u_reset_regions (.clk(ck), .rst_n_in(rst_n), .rst_n(local_rst_n));
    ot_rst_pipe #(.REGIONS(1), .STAGES(2)) u_por_region (.clk(ck), .rst_n_in(por_n), .rst_n(local_por_n));
    wire [3:0] end_rst_n = {local_rst_n[6], local_rst_n[5], local_rst_n[4], local_rst_n[1]};
    wire [1:0] st_rst_n  = {local_rst_n[7], local_rst_n[2]};
    localparam integer FW = 548;
    wire [3:0] txs, rxe, rxs; wire [3:0] tk, rk; wire [4:0] tb, rb; wire [FW-1:0] rxp;
    wire [3:0] tv; wire [4*FW-1:0] tp;
    wire eb, ab, endf, own_rst_n, rec; wire [7:0] ep, fc;
    wire st_f, kvn_f;
    ot_qwen_d2d_recovery #(.MASTER(0)) u_rec (.ck(ck), .por_n(local_por_n[0]), .rst_n(local_rst_n[0]), .abort(ab | endf),
        .fault_cause(fc), .end_fault(endf), .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_rx_v(fdi_rx_v),
        .reset_req(1'b0), .recovery_clear(1'b0), .boot_begin(1'b0), .fwd_epoch_i(fwd_epoch), .fwd_epoch_o(),
        .fwd_link_rst_n(), .phy_rst_n(own_rst_n), .epoch_begin(eb), .epoch(ep), .link_up(), .links_drained(),
        .link_reset_seen(), .retrained(), .transport_fault(transport_fault), .recovering(rec), .recovery_cycles());
    // epoch_begin copies: a copy of the follower strobe capture chain (fq, BUMP 3, same D / reset as u_rec.fq) and
    // KEPT copies of u_rec.epoch_begin <= fq[2] (same reset); u_rec.epoch_begin itself keeps only the epoch counter
    reg [2:0] fq_c;
    always @(posedge ck or negedge local_rst_n[0]) if (!local_rst_n[0]) fq_c <= 3'd0; else fq_c <= {fq_c[1:0], fwd_epoch};
    wire [6:0] eb_k;
    genvar e;
    for (e = 0; e < 7; e = e + 1) begin : g_eb
        ot_d2d_kffr u_eb (.ck(ck), .rst_n(local_rst_n[0]), .d(fq_c[2]), .q(eb_k[e]));
    end
    assign phy_rst_n = own_rst_n & fwd_link_rst_n;
    ot_qwen_d2d_static_end_s #(.TXD(TXDP), .SFMUT(SFMUT)) u_end (
        .ck({5{ck}}), .rst_n(end_rst_n), .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr),
        .cfg_data_t(cfg_data_t), .cfg_data_r(cfg_data_r), .cfg_seg_t(cfg_seg_t), .cfg_seg_r(cfg_seg_r),
        .eb_k(eb_k[4:0]), .epoch(ep), .cal_start_k(cal_start_k), .cal_seg_k(cal_seg_k),
        .cal_start_rx_k(cal_start_rx_k), .cal_seg_rx_k(cal_seg_rx_k), .cal_user_tx(cal_user_tx), .cal_user_rx(cal_user_rx),
        .tx_user(tx_user), .rx_user(rx_user),
        .tx_slot(txs), .tx_kind(tk), .tx_beat(tb), .tx_valid(tv), .tx_payload(tp),
        .rx_event(rxe), .rx_slot(rxs), .rx_kind(rk), .rx_beat(rb), .rx_payload(rxp),
        .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_tx_flit(fdi_tx_flit), .p_rx_v(fdi_rx_v), .p_rx_flit(fdi_rx_flit),
        .epoch_abort(ab), .fault_cause(fc), .end_fault(endf), .cal_running());
    assign epoch_abort = ab;
    assign native_tx_slot = txs[0]; assign native_tx_slot_kind = tk; assign native_tx_slot_beat = tb;
    assign tv[0] = native_tx_v; assign tp[0 +: FW] = native_tx_payload;
    assign rx_payload = rxp;
    assign native_rx_v = rxe[0];
    assign native_rx_slot = rxs[0]; assign native_rx_slot_kind = rk; assign native_rx_slot_beat = rb;
    assign prog_witness_slot = txs[1];
    assign tv[1] = prog_tx_observed_v; assign tp[FW +: FW] = prog_tx_record;
    assign prog_rx_v = rxe[1];
    assign emb_rx_v = rxe[2]; assign emb_rx_slot = rxs[2];
    assign prog_auth_slot = rxs[1] && rk == 4'd13;
    assign prog_context_slot = rxs[1] && rk == 4'd12;
    ot_qwen_d2d_status_tx_s u_st (.ck(ck), .rst_n(st_rst_n & {2{~eb_k[5]}}), .epoch16(status_epoch16),
        .vm_drained(vm_drained), .collective_drained(collective_drained), .collective_busy(collective_busy),
        .crom_fault(crom_fault), .execution_active(execution_active), .admit_ready(admit_ready),
        .result_v_k(result_v_k), .result_done(result_done), .result_fault(result_fault), .result_cause(result_cause),
        .result_tag(result_tag), .result_gen(result_gen), .result_token(result_token), .result_value(result_value),
        .result_cycles(result_cycles), .tx_slot(txs[2]), .tx_kind(tk), .tx_valid(tv[2]), .tx_payload(tp[2*FW +: FW]),
        .fault(st_f));
    assign kv_x3_slot = txs[3];
    ot_qwen_d2d_kvn_tx u_kvn (.ck(ck), .rst_n(local_rst_n[3] & ~eb_k[6]), .x3(x3), .x3_identity(x3_identity),
        .x3_generation(x3_generation), .tx_valid(tv[3]), .tx_payload(tp[3*FW +: FW]), .fault(kvn_f));
    assign fault = endf | st_f | kvn_f;
endmodule
