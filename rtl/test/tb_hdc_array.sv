`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM-array token simulation: a layer-per-package pipeline of hardwired decode
// cores (docs/ANALYTICAL_REPORT.md sections 1 and 9, docs/ROM_ARRAY_FABRIC_RTL.md).
//
// NODES packages, package n holding layer n (package 0 also the embedding, the
// last also the final norm and lm_head).  Each package is one ot_hdc_core and
// one ot_rom_pkg_ctrl (the synthesizable package controller) with the
// package's memories -- vector memory, KV SRAM (a slice per user) and program
// -- which stay behavioural here; the weight and constant ROMs are one image
// read through per-package ports.  The 128-float hidden state travels as a
// HIDDEN message (header + 8 flits) that the receiving controller writes into
// its vector memory as it arrives; lm_head packages send a RESULT message
// {user, position, token, logit} to package 0, which reduces the parts of a
// step and feeds the token back.
//
// Fabric (FABRIC):
//   0  point-to-point ot_rom_pkg_link: package n -> n+1, last -> 0;
//   1  a NODES-port ot_rom_fabric_router (a board switch), each package
//      reaching it over an uplink and being reached over a downlink, each half
//      the channel delay of the point-to-point link.
// MCAST (needs FABRIC=1 and HEADSPLIT >= 2): the last body package MULTICASTS
// its hidden state to all HEADSPLIT lm_head packages at once (router group id
// MG); each applies the final norm itself and its vocabulary part, in
// parallel, and sends its RESULT to package 0, which reduces the parts.
// Without MCAST the parts form a chain (part 0 normalises and forwards the
// normalised state with the running argmax).
//
// STALL > 0 gates every controller link port off at random (stress of the
// back-pressure and receive/send interlocks; USERS > NODES queues messages).
//
// USERS users (+NUSERS=n: the first n only) decode concurrently, each from
// an EMPTY KV cache through the oracle's 16-token prompt, then +NGEN generated
// tokens; package 0 checks every generated id against the torch oracle's.
// ---------------------------------------------------------------------------
module tb_hdc_array #(
    parameter integer G = 4,
    parameter integer NODES = 4,
    parameter integer USERS = 4,
    parameter integer HEADSPLIT = 0,     // N >= 2: the last N packages split lm_head by vocabulary
    parameter integer VOCAB = 4096,
    parameter integer FABRIC = 0,
    parameter integer MCAST = 0,
    parameter integer STALL = 0          // percent of cycles each controller port is held off (stress)
) (input wire clk);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096;
    localparam integer KVW = 1024;                 // KV words per user per package
    localparam integer VM_ELEMS = 4096, PROG_WORDS = 4096;
    localparam integer FLIT = 512;                 // bits: one vector-memory word
    localparam integer XWORDS = 8;                 // hidden state: 128 floats
    localparam integer MAXU = 16;
    localparam integer P = (HEADSPLIT >= 2) ? HEADSPLIT : 0;
    localparam integer MG = 16;                    // router id of the lm_head group
    localparam integer DESTS = 32;
    localparam integer LINK_CH = FABRIC ? 30 : 60; // channel cycles per link

    reg [G*W*16-1:0] wrom [0:WROM_WORDS-1];
    reg [63:0]       crom [0:CROM_WORDS-1];
    reg [NW-1:0]     prompt [0:255];
    reg [NW-1:0]     gold [0:255];
    reg [8*512-1:0]  dir;
    integer n_prompt = 16, n_gen = 3, n_users = USERS;
    reg rst_n = 1'b0;
    reg fin_d = 1'b0;
    integer cyc = 0;

    // controller link ports, per package
    wire [NODES-1:0] tx_v, tx_r, tx_l, rx_v, rx_r, rx_l;
    wire [NODES*FLIT-1:0] tx_d, rx_d;
    wire [NODES-1:0] fault_w, pfault_w, busy_w;
    wire [7:0] users_done;
    wire tok_v; wire [7:0] tok_u; wire [NW-1:0] tok_p, tok_i;

    // -- fabric ------------------------------------------------------------------------
    localparam integer NLINKS = FABRIC ? 2 * NODES : NODES;
    wire [NLINKS*32-1:0] l_stalls;
    genvar n;
    generate
        if (FABRIC == 0) begin : g_p2p
            for (n = 0; n < NODES; n = n + 1) begin : g_link
                localparam integer DST = (n + 1) % NODES;
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH), .RX_STAGES(2),
                                  .CREDITS(32)) u_link (
                    .clk(clk), .rst_n(rst_n),
                    .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                    .out_valid(rx_v[DST]), .out_ready(rx_r[DST]), .out_data(rx_d[DST*FLIT +: FLIT]),
                    .out_last(rx_l[DST]), .credit_stalls(l_stalls[n*32 +: 32]));
            end
        end else begin : g_star
            // routing table: id d < NODES -> package d; MG -> every lm_head package
            function automatic [DESTS*NODES-1:0] route_init(input integer unused);
                integer d, m;
                begin
                    route_init = {DESTS*NODES{1'b0}};
                    for (d = 0; d < NODES; d = d + 1) route_init[d*NODES + d] = 1'b1;
                    for (m = NODES - P; m < NODES; m = m + 1)
                        if (P >= 2) route_init[MG*NODES + m] = 1'b1;
                end
            endfunction
            wire [NODES-1:0] ri_v, ri_r, ri_l, ro_v, ro_r, ro_l, ri_c;
            wire [NODES*FLIT-1:0] ri_d, ro_d;
            wire [31:0] drops; wire overflow;
            ot_rom_fabric_router #(.NP(NODES), .FW(FLIT), .BUF(4), .DESTS(DESTS),
                                   .ROUTE_INIT(route_init(0))) u_router (
                .clk(clk), .rst_n(rst_n),
                .in_valid(ri_v), .in_ready(ri_r), .in_credit(ri_c), .in_data(ri_d), .in_last(ri_l),
                .out_valid(ro_v), .out_ready(ro_r), .out_data(ro_d), .out_last(ro_l),
                .cfg_we(1'b0), .cfg_dest(8'd0), .cfg_mask({NODES{1'b0}}), .drops(drops), .overflow(overflow));
            for (n = 0; n < NODES; n = n + 1) begin : g_link
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH), .RX_STAGES(2),
                                  .CREDITS(32)) u_up (
                    .clk(clk), .rst_n(rst_n),
                    .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                    .out_valid(ri_v[n]), .out_ready(ri_r[n]), .out_data(ri_d[n*FLIT +: FLIT]),
                    .out_last(ri_l[n]), .credit_stalls(l_stalls[n*32 +: 32]));
                ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(LINK_CH), .RX_STAGES(2),
                                  .CREDITS(32)) u_down (
                    .clk(clk), .rst_n(rst_n),
                    .in_valid(ro_v[n]), .in_ready(ro_r[n]), .in_data(ro_d[n*FLIT +: FLIT]), .in_last(ro_l[n]),
                    .out_valid(rx_v[n]), .out_ready(rx_r[n]), .out_data(rx_d[n*FLIT +: FLIT]),
                    .out_last(rx_l[n]), .credit_stalls(l_stalls[(NODES + n)*32 +: 32]));
            end
        end
    endgenerate

    // bookkeeping of generated tokens
    integer gen_n [0:USERS-1];
    integer bad = 0, finished = 0, gen_total = 0;

    generate
        for (n = 0; n < NODES; n = n + 1) begin : g_node
            // -- role of this package ---------------------------------------------------
            // head part h of P (-1: not an lm_head part); LB: the last body package
            localparam integer HP = (P >= 2 && n >= NODES - P) ? n - (NODES - P) : -1;
            localparam integer LB = NODES - P - 1;
            localparam integer MC = (MCAST != 0 && P >= 2);
            localparam integer LAST = (n == NODES - 1);
            localparam integer SEND_HID = MC ? (HP < 0) : !LAST;
            localparam integer HID_DST  = (MC && n == LB) ? MG : (n + 1) % NODES;
            localparam integer SEND_RES = MC ? (HP >= 0) : LAST;
            localparam integer RXB = (!MC && HP > 0) ? 8 : 0;
            localparam integer TXB = (!MC && HP >= 0 && HP < P - 1) ? 8 : 0;
            localparam integer COMB = !MC && HP > 0;
            localparam integer ROW0 = (HP > 0) ? HP * (VOCAB / P) : 0;

            // -- memories ---------------------------------------------------------
            reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
            reg [31:0]           vm [0:VM_ELEMS-1];
            reg [W*32-1:0]       kv [0:USERS*KVW-1];

            wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
            wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
            wire crom_re; wire [AW-1:0] crom_addr; reg [63:0] crom_q;
            wire kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr; reg [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
            wire va_re, vb_re, vc_re; wire [AW-1:0] va_addr, vb_addr, vc_addr;
            wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
            reg [31:0] va_q, vb_q, vc_q;
            wire vw_su_we, vw_rd_we; wire [AW-1:0] vw_su_addr, vw_rd_addr;
            wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr;
            wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data; wire [31:0] vw_su_data, vw_rd_data;
            wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
            wire [31:0] cycles;

            // core <-> controller
            wire          start, done;
            wire [NW-1:0] token, pos, ntok;
            wire [31:0]   nval;
            wire [AW-1:0] kv_base;
            wire          c_we, c_re; wire [7:0] c_waddr, c_raddr;
            wire [FLIT-1:0] c_wdata; reg [FLIT-1:0] c_rq;
            wire          pr_re; wire [7:0] pr_user; wire [NW-1:0] pr_pos; reg [NW-1:0] pr_q;

            ot_hdc_core #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW)) core (
                .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
                .done(done), .next_token(ntok), .next_val(nval),
                .cycles(cycles), .fault(fault_w[n]),
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

            // stress: random hold-off on both link ports of the controller
            reg in_ok = 1'b1, out_ok = 1'b1;
            if (STALL > 0) begin : g_stall
                always @(posedge clk) begin
                    in_ok  <= ($unsigned($random) % 100) >= STALL;
                    out_ok <= ($unsigned($random) % 100) >= STALL;
                end
            end
            wire c_in_ready;
            assign rx_r[n] = c_in_ready && in_ok;
            wire c_out_valid;
            assign tx_v[n] = c_out_valid && out_ok;

            wire          t_v; wire [7:0] t_u; wire [NW-1:0] t_p, t_i; wire [7:0] u_done;
            ot_rom_pkg_ctrl #(.PKG_ID(n), .FLIT(FLIT), .NW(NW), .AW(AW), .VWA(8), .MAXU(MAXU), .KVW(KVW),
                              .XWORDS(XWORDS), .RXB(RXB), .TXB(TXB), .SOURCE(n == 0),
                              .RESULT_PARTS(MC ? P : 1), .SEND_HIDDEN(SEND_HID), .HID_DEST(HID_DST),
                              .SEND_RESULT(SEND_RES), .RES_DEST(0), .COMBINE_IN(COMB), .ROW0(ROW0)) ctrl (
                .clk(clk), .rst_n(rst_n),
                .cfg_users(n_users[7:0]), .cfg_prompt_len(n_prompt[NW-1:0]), .cfg_gen_len(n_gen[NW-1:0]),
                .in_valid(rx_v[n] && in_ok), .in_ready(c_in_ready), .in_data(rx_d[n*FLIT +: FLIT]), .in_last(rx_l[n]),
                .out_valid(c_out_valid), .out_ready(tx_r[n] && out_ok), .out_data(tx_d[n*FLIT +: FLIT]), .out_last(tx_l[n]),
                .core_start(start), .core_token(token), .core_pos(pos), .core_done(done),
                .core_next_token(ntok), .core_next_val(nval), .kv_base(kv_base),
                .vm_we(c_we), .vm_waddr(c_waddr), .vm_wdata(c_wdata), .vm_re(c_re), .vm_raddr(c_raddr), .vm_rq(c_rq),
                .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
                .core_busy(busy_w[n]), .tok_valid(t_v), .tok_user(t_u), .tok_pos(t_p), .tok_id(t_i),
                .users_done(u_done), .proto_fault(pfault_w[n]));
            if (n == 0) begin : g_obs
                assign tok_v = t_v; assign tok_u = t_u; assign tok_p = t_p; assign tok_i = t_i;
                assign users_done = u_done;
            end

            integer k, q, l;
            reg [8*512-1:0] pdir;
            localparam [7:0] D1 = 8'h30 + n / 10;
            localparam [7:0] D0 = 8'h30 + n % 10;
            initial begin
                if (!$value$plusargs("DIR=%s", pdir)) pdir = ".";
                $readmemh({pdir, "/prog_stage", D1, D0, ".hex"}, prog);
                for (k = 0; k < VM_ELEMS; k = k + 1) vm[k] = 32'd0;
                for (k = 0; k < USERS * KVW; k = k + 1) kv[k] = {(W*32){1'b0}};
            end
            // KV slice of the running user
            wire [AW-1:0] kv_wword = (kv_waddr >> 4) + kv_base;

            always @(posedge clk) begin
                if (prog_re) prog_q <= prog[prog_addr];
                if (wrom_re) wrom_q <= wrom[wrom_addr[16:0]];
                if (crom_re) crom_q <= crom[crom_addr[11:0]];
                for (q = 0; q < G; q = q + 1)
                    if (kv_re) kv_q[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: AW] + kv_base];
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
                // controller word ports: received flits in, outbound payload out
                if (c_we) for (l = 0; l < W; l = l + 1) vm[{c_waddr, 4'b0} + l] <= c_wdata[32*l +: 32];
                if (c_re) for (l = 0; l < W; l = l + 1) c_rq[32*l +: 32] <= vm[{c_raddr, 4'b0} + l];
                if (pr_re) pr_q <= prompt[pr_pos[7:0]];
            end

            reg [63:0] busy_cycles = 0;
            reg printed = 1'b0;
            always @(posedge clk) begin
                if (busy_w[n]) busy_cycles <= busy_cycles + 1;
                if (finished == n_users && !printed) begin
                    $display("NODE_BUSY node=%0d cycles=%0d", n, busy_cycles); printed <= 1'b1;
                end
            end
        end
    endgenerate

    // -- token check at package 0 -----------------------------------------------------
    integer i, u;
    always @(posedge clk) if (rst_n) begin
        if (tok_v && tok_p >= n_prompt - 1) begin
            if (tok_i != gold[gen_n[tok_u]]) begin
                bad = bad + 1;
                $display("MISMATCH user=%0d step=%0d got=%0d gold=%0d", tok_u, gen_n[tok_u], tok_i, gold[gen_n[tok_u]]);
            end
            $display("GEN user=%0d pos=%0d token=%0d cycle=%0d", tok_u, tok_p, tok_i, cyc);
            gen_n[tok_u] = gen_n[tok_u] + 1; gen_total = gen_total + 1;
            if (gen_n[tok_u] == n_gen) finished = finished + 1;
        end
    end

    reg [31:0] l_stall_sum;
    always @(*) begin
        l_stall_sum = 0;
        for (i = 0; i < NLINKS; i = i + 1) l_stall_sum = l_stall_sum + l_stalls[i*32 +: 32];
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 3;
        if (!$value$plusargs("NUSERS=%d", n_users)) n_users = USERS;
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/crom.hex"}, crom);
        $readmemh({dir, "/prompt.hex"}, prompt);
        $readmemh({dir, "/generated.hex"}, gold);
        for (u = 0; u < USERS; u = u + 1) gen_n[u] = 0;
    end

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        fin_d <= (finished == n_users);
        if (fin_d) begin
            if (fault_w != 0 || pfault_w != 0) begin
                bad = bad + 1;
                $display("FAULT core=%b protocol=%b", fault_w, pfault_w);
            end
            $display("HDC_ARRAY nodes=%0d users=%0d generated=%0d mismatches=%0d total_cycles=%0d",
                     NODES, n_users, gen_total, bad, cyc);
            $display("USERS_DONE %0d", users_done);
            $display("LINK_STALLS %0d", l_stall_sum);
            if (bad == 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
        if (cyc > 20000000) begin $display("TIMEOUT finished=%0d", finished); $finish; end
    end
endmodule
