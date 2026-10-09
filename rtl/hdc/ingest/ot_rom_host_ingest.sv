`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_rom_host_ingest (stream ingest, 2026-10-08): the ROM dies' host-side block.  It puts the unchanged KV ingest
// engine (ot_hdc_kv_ingest) between a host link and the die's HBM write fabric, so a GPU-prefilled KV image (QKV /
// ROWS / IKEY descriptors) or any boot image (RAW: e.g. the Qwen embedding table in HBM, emb-hbm) lands in the
// attached HBM exactly where decode reads it.  Spec: claude-takeover-20261007/review_queue/ingest.md, the engine's
// own spec docs/ARCH_SPEC_QWEN3.md section 16 (R-P1..R-P5).
//
// Three clock domains, every crossing a Gray-pointer async FIFO (ot_link_afifo) or a toggle-qualified static CSR:
//   clk_h  host link user clock (PCIe / board-SerDes controller side).  Pin flops on every input and output.
//   clk_i  the ingest core clock.  The engine is OFF the token path, so it runs on a slow clock of its own (the
//          die's 1.2 GHz divided by 2 = 600 MHz, a separate CTS root, no clock gating): its 64 FP8 quantisers and
//          granule walk get 1.667 ns, and nothing in this domain times against the 833 ps die clock.
//   ck     the die core clock: the HBM write fabric face (sector words with credits), pin flops.
// Host stream (clk_h, valid + 2-b class + 512 b; the sender holds 2^HFA credits, h_crn returns freed entries):
//   class 0 CSR write  d[7:0] index, d[63:32] value:  0 = share (ingest sectors per die cycle x 256, 0 = unpaced;
//                      change it only while the block is idle), 1 = completion of every descriptor (bit 0).
//   class 1 descriptor d[255:0] (the engine's 256-b descriptor).  The host sends a descriptor, then its payload;
//                      at most DQ (4) descriptors ahead of their payloads.
//   class 2 payload    one 512-b beat.
//   class 3 reserved   (fault).
// Completion stream (clk_h, t_v / t_d, one host credit t_cr per word taken; TCRED credits at reset):
//   {8'h01, 8'b0, tag[7:0], 8'b0, sectors written so far[31:0]} per fenced descriptor done (engine done_v);
//   {8'hFF, 48'b0, code[7:0]} once, on the first fault.
// Die face (ck): o_v / o_we / o_addr / o_d = one 32-B sector write (o_we 1) or an RMW sector read (o_we 0), sent
//   only against a downstream credit (OCRED at reset, o_cr returns one) and the share pacer; the read data returns
//   in request order on i_rv / i_rd.  RMW_EN 0: the read path is absent and an rmw descriptor is a fault.
// Fault codes (sticky, fail closed: after a fault the host stream is drained and dropped): 1 QKV descriptor with
//   QKV_EN 0, 2 rmw descriptor with RMW_EN 0, 3 reserved class, 4 host overflow (sender ignored credits),
//   5 completion FIFO overflow, 6 read-return overflow (die fabric returned more reads than issued).
// MUT (bench mutants, must FAIL): 1 flips bit 30 (element 0 exponent MSB) of the 7th payload beat; 2 reports done tags + 1.
// ---------------------------------------------------------------------------
module ot_rom_host_ingest #(
    parameter integer AW     = 32,
    parameter integer HDMAX  = 128,
    parameter integer KVHMAX = 2,      // Qwen3-8B TP4: 8 KV heads / 4 dies
    parameter integer QKV_EN = 1,      // 0: ROWS / IKEY / RAW only (V4.1 dies), a QKV descriptor is a fault
    parameter integer RMW_EN = 1,
    parameter integer HFA    = 4,      // host receive FIFO, 2^HFA entries = the host's credits
    parameter integer OFA    = 4,      // request FIFO clk_i -> ck
    parameter integer RFA    = 4,      // read-return FIFO ck -> clk_i (= the RMW reads in flight)
    parameter integer CFA    = 4,      // completion FIFO clk_i -> clk_h
    parameter integer OCRED  = 8,      // die-fabric credits at reset
    parameter integer TCRED  = 4,      // host completion credits at reset
    parameter integer PCAP   = 16,     // pacer burst (sectors)
    parameter integer MUT    = 0
) (
    input  wire              rst_n,
    // host link face
    input  wire              clk_h,
    input  wire              h_v,
    input  wire [1:0]        h_cls,
    input  wire [511:0]      h_d,
    output reg  [HFA:0]      h_crn,
    output reg               t_v,
    output reg  [63:0]       t_d,
    input  wire              t_cr,
    // ingest core clock
    input  wire              clk_i,
    // die face
    input  wire              ck,
    output reg               o_v,
    output reg               o_we,
    output reg  [AW-1:0]     o_addr,
    output reg  [255:0]      o_d,
    input  wire              o_cr,
    input  wire              i_rv,
    input  wire [255:0]      i_rd,
    output wire              fault
);
    wire rn_h, rn_i, rn_c;
    ot_reset_sync u_rsh (.clk(clk_h), .async_rst_n(rst_n), .sync_rst_n(rn_h));
    ot_reset_sync u_rsi (.clk(clk_i), .async_rst_n(rst_n), .sync_rst_n(rn_i));
    ot_reset_sync u_rsc (.clk(ck),    .async_rst_n(rst_n), .sync_rst_n(rn_c));
    // cross-domain nets (declared ahead of use)
    wire         hx_ovf_i, rx_ovf_i, ox_pop, cx_pop;
    reg          irv_q;
    reg  [255:0] ird_q;

    // =============================================================================================================
    // host face (clk_h): pin flops -> host receive FIFO
    // =============================================================================================================
    reg          hv_q;
    reg [1:0]    hc_q;
    reg [511:0]  hd_q;
    always @(posedge clk_h) begin hc_q <= h_cls; hd_q <= h_d; end
    always @(posedge clk_h or negedge rn_h) if (!rn_h) hv_q <= 1'b0; else hv_q <= h_v;
    wire         hx_full, hx_empty, hx_ovf;
    wire [HFA:0] hx_freed, hx_cnt;
    wire [513:0] hx_head;
    reg          hx_pop;
    ot_link_afifo #(.W(514), .AW(HFA)) u_hx (
        .wclk(clk_h), .wrst_n(rn_h), .wr(hv_q), .wdata({hc_q, hd_q}), .wfull(hx_full), .wfreed(hx_freed), .ovf(hx_ovf),
        .rclk(clk_i), .rrst_n(rn_i), .rd(hx_pop), .rempty(hx_empty), .rdata(hx_head), .rcount(hx_cnt));
    always @(posedge clk_h or negedge rn_h) if (!rn_h) h_crn <= 0; else h_crn <= hx_freed;

    // =============================================================================================================
    // ingest core (clk_i)
    // =============================================================================================================
    reg  [7:0]   f_code;                    // first fault (sticky)
    wire         f_any = f_code != 8'd0;
    wire [1:0]   hcl = hx_head[513:512];
    wire [255:0] hdesc = hx_head[255:0];
    wire         dq_qkv = hdesc[3:0] == 4'd1;
    wire         bad_qkv = (QKV_EN == 0) && dq_qkv;
    wire         bad_rmw = (RMW_EN == 0) && dq_qkv && hdesc[6];
    // engine
    wire         e_drdy, e_inrdy, e_wv, e_rv, e_done, e_busy;
    wire [AW-1:0] e_waddr, e_raddr;
    wire [255:0] e_wdata;
    wire [7:0]   e_tag;
    wire [31:0]  e_nsec, e_nbeat;
    reg          e_rdv;
    reg  [255:0] e_rdd;
    wire         e_wrdy, e_rrdy;
    reg  [3:0]   pcnt;                      // payload beats seen (MUT 1)
    wire [511:0] pay = (MUT == 1 && pcnt == 4'd6) ? (hx_head[511:0] ^ (512'd1 << 30)) : hx_head[511:0];
    wire         hv_i = !hx_empty;
    wire         take_d = hv_i && !f_any && hcl == 2'd1 && !bad_qkv && !bad_rmw;
    wire         take_p = hv_i && !f_any && hcl == 2'd2;
    ot_hdc_kv_ingest #(.AW(AW), .HDMAX(HDMAX), .KVHMAX(KVHMAX)) u_eng (
        .clk(clk_i), .rst_n(rn_i),
        .d_v(take_d), .d_rdy(e_drdy), .d_data(hdesc),
        .in_v(take_p), .in_rdy(e_inrdy), .in_data(pay),
        .w_v(e_wv), .w_rdy(e_wrdy), .w_addr(e_waddr), .w_data(e_wdata),
        .r_v(e_rv), .r_rdy(e_rrdy), .r_addr(e_raddr), .rd_v(e_rdv), .rd_data(e_rdd),
        .done_v(e_done), .done_tag(e_tag), .busy(e_busy), .n_sectors(e_nsec), .n_beats(e_nbeat));
    always @(*) begin
        hx_pop = 1'b0;
        if (hv_i) begin
            if (f_any) hx_pop = 1'b1;                                   // fail closed: drain and drop
            else case (hcl)
                2'd0: hx_pop = 1'b1;
                2'd1: hx_pop = (bad_qkv || bad_rmw) ? 1'b1 : e_drdy;
                2'd2: hx_pop = e_inrdy;
                default: hx_pop = 1'b1;
            endcase
        end
    end
    // CSRs
    reg  [8:0]   share_i;
    reg          csr_tgl;
    reg          all_done;                  // reserved (bit 0 of CSR 1); completions follow the descriptor fence bit
    // request FIFO clk_i -> ck: {we, addr, data}; writes before reads, reads capped by the return FIFO
    wire         ox_full, ox_empty, ox_ovf;
    wire [OFA:0] ox_freed, ox_cnt;
    wire [AW+256:0] ox_head;
    reg  [RFA+1:0] outst;                   // RMW reads issued, not yet handed to the engine
    wire         rd_room = outst < (1 << RFA);
    assign e_wrdy = !ox_full;
    assign e_rrdy = (RMW_EN != 0) && !e_wv && !ox_full && rd_room;
    wire         ox_wr = (e_wv && e_wrdy) || (e_rv && e_rrdy);
    wire [AW+256:0] ox_w = e_wv ? {1'b1, e_waddr, e_wdata} : {1'b0, e_raddr, 256'd0};
    // read returns ck -> clk_i
    wire         rx_full, rx_empty, rx_ovf;
    wire [RFA:0] rx_freed, rx_cnt;
    wire [255:0] rx_head;
    wire         rx_pop = !rx_empty;
    // completions clk_i -> clk_h
    wire         cx_full, cx_empty, cx_ovf;
    wire [CFA:0] cx_freed, cx_cnt;
    wire [63:0]  cx_head;
    reg          cx_wr;
    reg  [63:0]  cx_w;
    reg          f_sent;
    always @(posedge clk_i or negedge rn_i) begin
        if (!rn_i) begin
            f_code <= 0; share_i <= 0; csr_tgl <= 1'b0; all_done <= 1'b0; pcnt <= 0; outst <= 0;
            e_rdv <= 1'b0; e_rdd <= 0; cx_wr <= 1'b0; cx_w <= 0; f_sent <= 1'b0;
        end else begin
            if (hv_i && !f_any && hcl == 2'd0) begin
                if (hx_head[7:0] == 8'd0) begin share_i <= hx_head[40:32]; csr_tgl <= ~csr_tgl; end
                if (hx_head[7:0] == 8'd1) all_done <= hx_head[32];
            end
            if (take_p && e_inrdy && pcnt != 4'd15) pcnt <= pcnt + 4'd1;
            // faults: the first one wins
            if (!f_any) begin
                if (hv_i && hcl == 2'd1 && bad_qkv)      f_code <= 8'd1;
                else if (hv_i && hcl == 2'd1 && bad_rmw) f_code <= 8'd2;
                else if (hv_i && hcl == 2'd3)            f_code <= 8'd3;
                else if (hx_ovf_i)                        f_code <= 8'd4;
                else if (cx_ovf)                          f_code <= 8'd5;
                else if (rx_ovf_i)                        f_code <= 8'd6;
            end
            // read return: registered into the engine (it always accepts)
            e_rdv <= rx_pop;
            e_rdd <= rx_head;
            outst <= outst + ((e_rv && e_rrdy) ? 1 : 0) - (rx_pop ? 1 : 0);
            // completions: done words, then the fault word once
            cx_wr <= 1'b0;
            if (e_done) begin
                cx_wr <= 1'b1;
                cx_w <= {8'h01, 8'd0, (MUT == 2) ? e_tag + 8'd1 : e_tag, 8'd0, e_nsec};
            end else if (f_any && !f_sent) begin
                cx_wr <= 1'b1; cx_w <= {8'hFF, 48'd0, f_code}; f_sent <= 1'b1;
            end
        end
    end
    // overflow flags from the other domains, synchronised (sticky at their source)
    (* async_reg = "true" *) reg [1:0] hov_s, rov_s;
    assign hx_ovf_i = hov_s[1];
    assign rx_ovf_i = rov_s[1];
    always @(posedge clk_i or negedge rn_i)
        if (!rn_i) begin hov_s <= 0; rov_s <= 0; end
        else begin hov_s <= {hov_s[0], hx_ovf}; rov_s <= {rov_s[0], rx_ovf}; end

    ot_link_afifo #(.W(AW + 257), .AW(OFA)) u_ox (
        .wclk(clk_i), .wrst_n(rn_i), .wr(ox_wr), .wdata(ox_w), .wfull(ox_full), .wfreed(ox_freed), .ovf(ox_ovf),
        .rclk(ck), .rrst_n(rn_c), .rd(ox_pop), .rempty(ox_empty), .rdata(ox_head), .rcount(ox_cnt));
    ot_link_afifo #(.W(256), .AW(RFA)) u_rx (
        .wclk(ck), .wrst_n(rn_c), .wr(irv_q), .wdata(ird_q), .wfull(rx_full), .wfreed(rx_freed), .ovf(rx_ovf),
        .rclk(clk_i), .rrst_n(rn_i), .rd(rx_pop), .rempty(rx_empty), .rdata(rx_head), .rcount(rx_cnt));
    ot_link_afifo #(.W(64), .AW(CFA)) u_cx (
        .wclk(clk_i), .wrst_n(rn_i), .wr(cx_wr), .wdata(cx_w), .wfull(cx_full), .wfreed(cx_freed), .ovf(cx_ovf),
        .rclk(clk_h), .rrst_n(rn_h), .rd(cx_pop), .rempty(cx_empty), .rdata(cx_head), .rcount(cx_cnt));

    // =============================================================================================================
    // completion face (clk_h): host credits, pin flops
    // =============================================================================================================
    reg  [7:0] tcr;
    reg        tcr_q;
    assign     cx_pop = !cx_empty && tcr != 0;
    always @(posedge clk_h or negedge rn_h) begin
        if (!rn_h) begin t_v <= 1'b0; t_d <= 0; tcr <= TCRED; tcr_q <= 1'b0; end
        else begin
            tcr_q <= t_cr;
            tcr <= tcr + (tcr_q ? 8'd1 : 8'd0) - (cx_pop ? 8'd1 : 8'd0);
            t_v <= cx_pop;
            if (cx_pop) t_d <= cx_head;
        end
    end

    // =============================================================================================================
    // die face (ck): share CSR (toggle-qualified), pacer, credits, pin flops
    // =============================================================================================================
    (* async_reg = "true" *) reg [2:0] tg_s;
    reg  [8:0]  share_c;
    always @(posedge ck or negedge rn_c)
        if (!rn_c) begin tg_s <= 0; share_c <= 0; end
        else begin
            tg_s <= {tg_s[1:0], csr_tgl};
            if (tg_s[2] != tg_s[1]) share_c <= share_i;        // share_i stable since the toggle (>= 2 ck earlier)
        end
    localparam integer PW = $clog2(PCAP * 256 + 512) + 1;
    reg  [PW-1:0] tok;
    reg  [7:0]    ocr;
    reg           ocr_q;
    wire          pace_ok = (share_c == 9'd0) || (tok >= 256);
    assign        ox_pop = !ox_empty && ocr != 0 && pace_ok;
    always @(posedge ck or negedge rn_c) begin
        if (!rn_c) begin
            o_v <= 1'b0; o_we <= 1'b0; o_addr <= 0; o_d <= 0; ocr <= OCRED; ocr_q <= 1'b0; tok <= 0;
        end else begin
            ocr_q <= o_cr;
            ocr <= ocr + (ocr_q ? 8'd1 : 8'd0) - (ox_pop ? 8'd1 : 8'd0);
            if (share_c == 9'd0) tok <= 0;
            else tok <= ((tok + share_c > PCAP * 256) ? PCAP * 256 : tok + share_c) - (ox_pop ? 256 : 0);
            o_v <= ox_pop;
            if (ox_pop) begin o_we <= ox_head[AW+256]; o_addr <= ox_head[AW+255:256]; o_d <= ox_head[255:0]; end
        end
    end
    always @(posedge ck) ird_q <= i_rd;
    always @(posedge ck or negedge rn_c) if (!rn_c) irv_q <= 1'b0; else irv_q <= i_rv && (RMW_EN != 0);
    // sticky fault, seen in the die domain
    (* async_reg = "true" *) reg [1:0] fs;
    reg         fault_c;
    always @(posedge ck or negedge rn_c)
        if (!rn_c) begin fs <= 0; fault_c <= 1'b0; end
        else begin fs <= {fs[0], f_any}; fault_c <= fault_c | fs[1]; end   // ox_ovf cannot happen (writes need !ox_full)
    assign fault = fault_c;
endmodule
