`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM-array token simulation: a layer-per-package pipeline of hardwired decode
// cores (docs/ANALYTICAL_REPORT.md sections 1 and 9).
//
// NODES packages in a line, package n holding layer n (package 0 also the
// embedding, the last also the final norm and lm_head).  Each package is one
// ot_hdc_core with its own vector memory, KV SRAM (a slice per user) and
// program; the weight and constant ROMs are one image read through per-package
// ports.  Between packages the 128-float hidden state travels over
// ot_rom_pkg_link as one header flit {user, position} and 8 data flits, which
// the receiver writes straight into its vector memory as they arrive.  The last
// package returns {user, position, token} to package 0 over a feedback link.
//
// USERS users decode concurrently.  Each runs the oracle's 16-token prompt
// through the array from an EMPTY KV cache and then generates +NGEN tokens,
// feeding each output back; up to USERS tokens are in flight, one per package.
// Every generated id is compared with the torch oracle's.
// ---------------------------------------------------------------------------
module tb_hdc_array #(
    parameter integer G = 4,
    parameter integer NODES = 4,
    parameter integer USERS = 4
) (input wire clk);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096;
    localparam integer KVW = 1024;                 // KV words per user per package
    localparam integer VM_ELEMS = 4096, PROG_WORDS = 4096;
    localparam integer FLIT = 512;                 // bits: one vector-memory word
    localparam integer XWORDS = 8;                 // hidden state: 128 floats

    reg [G*W*16-1:0] wrom [0:WROM_WORDS-1];
    reg [63:0]       crom [0:CROM_WORDS-1];
    reg [NW-1:0]     prompt [0:255];
    reg [NW-1:0]     gold [0:255];
    reg [8*512-1:0]  dir;
    integer n_prompt = 16, n_gen = 3;
    reg rst_n = 1'b0;
    reg fin_d = 1'b0;
    integer cyc = 0;

    // per-node control, flattened across the generate
    wire [NODES-1:0] done_w, fault_w;
    wire [NODES*NW-1:0] ntok_w;
    // links: node n -> n+1 (index n), feedback last -> 0 (index NODES-1)
    wire [NODES-1:0] l_in_valid, l_in_ready, l_in_last, l_out_valid, l_out_ready, l_out_last;
    wire [NODES*FLIT-1:0] l_in_data, l_out_data;
    wire [NODES*32-1:0] l_stalls;
    genvar n;
    generate
        for (n = 0; n < NODES; n = n + 1) begin : g_link
            ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(60), .RX_STAGES(2),
                              .CREDITS(32)) u_link (
                .clk(clk), .rst_n(rst_n),
                .in_valid(l_in_valid[n]), .in_ready(l_in_ready[n]), .in_data(l_in_data[n*FLIT +: FLIT]),
                .in_last(l_in_last[n]),
                .out_valid(l_out_valid[n]), .out_ready(l_out_ready[n]), .out_data(l_out_data[n*FLIT +: FLIT]),
                .out_last(l_out_last[n]), .credit_stalls(l_stalls[n*32 +: 32]));
        end
    endgenerate

    // bookkeeping of generated tokens
    integer gen_n [0:USERS-1];
    integer bad = 0, finished = 0, gen_total = 0;
    reg [63:0] first_cyc [0:USERS-1];
    reg [63:0] last_cyc [0:USERS-1];

    generate
        for (n = 0; n < NODES; n = n + 1) begin : g_node
            // -- memories ---------------------------------------------------------
            reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
            reg [31:0]           vm [0:VM_ELEMS-1];
            reg [W*32-1:0]       kv [0:USERS*KVW-1];

            wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
            wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
            wire crom_re; wire [AW-1:0] crom_addr; reg [63:0] crom_q;
            wire kv_re, kv_we; wire [AW-1:0] kv_raddr, kv_waddr; reg [W*32-1:0] kv_q; wire [31:0] kv_wdata;
            wire va_re, vb_re, vc_re; wire [AW-1:0] va_addr, vb_addr, vc_addr;
            wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
            reg [31:0] va_q, vb_q, vc_q;
            wire vw_su_we, vw_rd_we; wire [AW-1:0] vw_su_addr, vw_rd_addr;
            wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr;
            wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data; wire [31:0] vw_su_data, vw_rd_data;
            wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
            wire [31:0] cycles;

            reg          start;
            reg [NW-1:0] token, pos;
            reg [7:0]    user;
            ot_hdc_core #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW)) core (
                .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
                .done(done_w[n]), .next_token(ntok_w[n*NW +: NW]), .cycles(cycles), .fault(fault_w[n]),
                .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
                .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
                .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
                .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
                .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
                .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q),
                .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
                .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
                .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
                .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
                .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
                .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
                .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata));

            // -- node control -------------------------------------------------------
            localparam [2:0] N_IDLE = 0, N_RECV = 1, N_RUN = 2, N_WAIT = 3, N_SEND = 4;
            reg [2:0] st;
            reg [3:0] fl;                          // flit index
            reg [63:0] busy_cycles;
            // inbound: node 0 takes jobs from the feedback link, others from the previous node
            localparam integer IN = (n == 0) ? NODES - 1 : n - 1;
            wire in_v = l_out_valid[IN];
            wire [FLIT-1:0] in_d = l_out_data[IN*FLIT +: FLIT];
            assign l_out_ready[IN] = (st == N_IDLE) || (st == N_RECV);
            // outbound
            reg out_v, out_last;
            reg [FLIT-1:0] out_d;
            assign l_in_valid[n] = out_v;
            assign l_in_last[n] = out_last;
            assign l_in_data[n*FLIT +: FLIT] = out_d;

            // node 0: users start at position 0 with the first prompt token
            integer next_u, k, q, l;
            reg [8*512-1:0] pdir;
            localparam [7:0] NCH = 8'h30 + n;
            reg printed = 1'b0;
            initial begin
                if (!$value$plusargs("DIR=%s", pdir)) pdir = ".";
                $readmemh({pdir, "/prog_stage", NCH, ".hex"}, prog);
                for (k = 0; k < VM_ELEMS; k = k + 1) vm[k] = 32'd0;
                for (k = 0; k < USERS * KVW; k = k + 1) kv[k] = {(W*32){1'b0}};
            end
            // KV slice of the running user
            wire [AW-1:0] kv_rword = kv_raddr + user * KVW;
            wire [AW-1:0] kv_wword = (kv_waddr >> 4) + user * KVW;

            always @(posedge clk) begin
                if (prog_re) prog_q <= prog[prog_addr];
                if (wrom_re) wrom_q <= wrom[wrom_addr[16:0]];
                if (crom_re) crom_q <= crom[crom_addr[11:0]];
                if (kv_re) kv_q <= kv[kv_rword];
                for (q = 0; q < G; q = q + 1)
                    if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 12]];
                if (va_re) va_q <= vm[va_addr[11:0]];
                if (vb_re) vb_q <= vm[vb_addr[11:0]];
                if (vc_re) vc_q <= vm[vc_addr[11:0]];
                if (kv_we) kv[kv_wword][32*kv_waddr[3:0] +: 32] <= kv_wdata;
                for (q = 0; q < G; q = q + 1)
                    if (vw_me_we[q])
                        for (l = 0; l < W; l = l + 1)
                            if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: 8], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
                if (vw_su_we) vm[vw_su_addr[11:0]] <= vw_su_data;
                if (vw_rd_we) vm[vw_rd_addr[11:0]] <= vw_rd_data;
                // received hidden-state flits land in X (words 0..7)
                if (st == N_RECV && in_v)
                    for (l = 0; l < W; l = l + 1) vm[{fl[2:0], 4'b0} + l] <= in_d[32*l +: 32];
            end

            always @(posedge clk) begin
                start <= 1'b0;
                if (!rst_n) begin
                    st <= N_IDLE; out_v <= 1'b0; out_last <= 1'b0; busy_cycles <= 0;
                    next_u = 0;
                end else begin
                    if (st == N_RUN || st == N_WAIT) busy_cycles <= busy_cycles + 1;
                    if (finished == USERS && !printed) begin
                        $display("NODE_BUSY node=%0d cycles=%0d", n, busy_cycles); printed <= 1'b1;
                    end
                    case (st)
                        N_IDLE: begin
                            if (n == 0 && next_u < USERS) begin
                                // a fresh user: position 0, first prompt token
                                user <= next_u; token <= prompt[0]; pos <= 0;
                                next_u = next_u + 1;
                                start <= 1'b1; st <= N_RUN;
                            end else if (in_v) begin
                                if (n == 0) begin
                                    // feedback {user, pos, token}: the next step of that user
                                    user <= in_d[39:32];
                                    pos <= in_d[31:16] + 1'b1;
                                    token <= (in_d[31:16] + 1 < n_prompt) ? prompt[in_d[31:16] + 1] : in_d[15:0];
                                    start <= 1'b1; st <= N_RUN;
                                end else begin
                                    user <= in_d[39:32]; pos <= in_d[31:16]; token <= 0;
                                    fl <= 0; st <= N_RECV;
                                end
                            end
                        end
                        N_RECV: if (in_v) begin
                            fl <= fl + 1'b1;
                            if (fl == XWORDS - 1) begin start <= 1'b1; st <= N_RUN; end
                        end
                        N_RUN: st <= N_WAIT;                   // start is taken this cycle
                        N_WAIT: if (done_w[n] && !start) begin
                            fl <= 0; st <= N_SEND;
                            if (n == NODES - 1) begin
                                if (fault_w[n]) bad = bad + 1;
                                if (pos >= n_prompt - 1) begin
                                    if (ntok_w[n*NW +: NW] != gold[gen_n[user]]) begin
                                        bad = bad + 1;
                                        $display("MISMATCH user=%0d step=%0d got=%0d gold=%0d", user, gen_n[user],
                                                 ntok_w[n*NW +: NW], gold[gen_n[user]]);
                                    end
                                    $display("GEN user=%0d pos=%0d token=%0d cycle=%0d", user, pos,
                                             ntok_w[n*NW +: NW], cyc);
                                    gen_n[user] = gen_n[user] + 1; gen_total = gen_total + 1;
                                    last_cyc[user] = cyc;
                                    if (gen_n[user] == 1) first_cyc[user] = cyc;
                                    if (gen_n[user] == n_gen) finished = finished + 1;
                                end
                            end
                        end
                        N_SEND: begin
                            if (!out_v || l_in_ready[n]) begin
                                if (n == NODES - 1) begin
                                    // feedback: one flit, only while the user has steps left
                                    out_v <= (pos + 1 < n_prompt + n_gen - 1);
                                    out_d <= {{(FLIT-40){1'b0}}, user, pos, ntok_w[n*NW +: NW]};
                                    out_last <= 1'b1;
                                    st <= N_IDLE;
                                end else if (fl == 0) begin
                                    out_v <= 1'b1; out_last <= 1'b0;
                                    out_d <= {{(FLIT-40){1'b0}}, user, pos, 16'd0};
                                    fl <= 1;
                                end else begin
                                    out_v <= 1'b1; out_last <= (fl == XWORDS);
                                    for (l = 0; l < W; l = l + 1) out_d[32*l +: 32] <= vm[{fl[2:0] - 3'd1, 4'b0} + l];
                                    fl <= fl + 1'b1;
                                    if (fl == XWORDS) st <= N_IDLE;
                                end
                            end
                        end
                        default: st <= N_IDLE;
                    endcase
                    // drop the valid once the link has taken the last flit
                    if (st == N_IDLE && out_v && l_in_ready[n]) out_v <= 1'b0;
                end
            end
        end
    endgenerate

    integer i, u;
    reg [31:0] l_stall_sum;
    always @(*) begin
        l_stall_sum = 0;
        for (i = 0; i < NODES; i = i + 1) l_stall_sum = l_stall_sum + l_stalls[i*32 +: 32];
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 3;
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/crom.hex"}, crom);
        $readmemh({dir, "/prompt.hex"}, prompt);
        $readmemh({dir, "/generated.hex"}, gold);
        for (u = 0; u < USERS; u = u + 1) begin gen_n[u] = 0; first_cyc[u] = 0; last_cyc[u] = 0; end
    end

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        fin_d <= (finished == USERS);
        if (fin_d) begin
            $display("HDC_ARRAY nodes=%0d users=%0d generated=%0d mismatches=%0d total_cycles=%0d",
                     NODES, USERS, gen_total, bad, cyc);
            $display("LINK_STALLS %0d", l_stall_sum);
            if (bad == 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
        if (cyc > 20000000) begin $display("TIMEOUT finished=%0d", finished); $finish; end
    end
endmodule
