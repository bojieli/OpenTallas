`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Host-interface simulation top, ROM array: ot_host_if (MODE 1) fronting the
// SOURCE package of a layer-per-package array (the structure of
// tb_hdc_array.sv, point-to-point ot_rom_pkg_link fabric, lm_head on the last
// layer's package).  Package n is one ot_hdc_core and one ot_rom_pkg_ctrl
// with behavioural memories; programs are prog_stageNN.hex from
// tools/hdc_program.py --stages NODES.
//
// The host interface owns the array's reset and run configuration (users,
// prompt length, generation length), serves package 0's prompt reads from the
// prompt buffer ({user, position}), and takes package 0's reduced token
// stream.  Package controller users are the host interface's slots.
// ---------------------------------------------------------------------------
module tb_host_array #(
    parameter integer G = 4,
    parameter integer NODES = 4,
    parameter integer NSLOT = 16
) (
`include "tb_host_ports.svh"
);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12, PLB = 8;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096;
    localparam integer KVW = 1024;
    localparam integer VM_ELEMS = 4096, PROG_WORDS = 4096;
    localparam integer FLIT = 512, XWORDS = 8, MAXU = NSLOT;
    localparam integer SB = $clog2(NSLOT);

    reg [G*W*16-1:0] wrom [0:WROM_WORDS-1];
    reg [63:0]       crom [0:CROM_WORDS-1];
    reg [NW-1:0]     pbuf [0:NSLOT*(1<<PLB)-1];

    wire pb_we, pb_re; wire [SB+PLB-1:0] pb_waddr, pb_raddr; wire [NW-1:0] pb_wdata; reg [NW-1:0] pb_q;
    wire arr_rst_n; wire [7:0] cfg_users; wire [NW-1:0] cfg_plen, cfg_glen;
    wire pr_re; wire [7:0] pr_user; wire [NW-1:0] pr_pos;
    wire tok_v; wire [7:0] tok_u; wire [NW-1:0] tok_p, tok_i; wire [7:0] users_done;
    wire [NODES-1:0] fault_w, pfault_w, busy_w;
    wire a_rst_n = rst_n && arr_rst_n;

    ot_host_if #(.NSLOT(NSLOT), .MODE(1), .ENG_CTX(NSLOT), .NW(NW), .PLB(PLB), .CTX_MAX(64), .AW(AW),
                 .KVW(KVW)) u_host (
`include "tb_host_conn.svh"
        .eng_start(), .eng_token(), .eng_pos(), .eng_slot(), .kv_base(),
        .eng_done(1'b0), .eng_next_token({NW{1'b0}}), .eng_cycles(32'd0), .eng_fault(1'b0),
        .eng_clr_req(), .eng_clr_ack(1'b0),
        .arr_rst_n(arr_rst_n), .cfg_users(cfg_users), .cfg_prompt_len(cfg_plen), .cfg_gen_len(cfg_glen),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos),
        .tok_valid(tok_v), .tok_user(tok_u), .tok_pos(tok_p), .tok_id(tok_i), .users_done(users_done),
        .arr_fault(|fault_w || |pfault_w));
    assign eng_busy = |busy_w;

    always @(posedge clk) begin
        if (pb_we) pbuf[pb_waddr] <= pb_wdata;
        if (pb_re) pb_q <= pbuf[pb_raddr];
    end

    // point-to-point fabric: package n -> n+1, last -> 0
    wire [NODES-1:0] tx_v, tx_r, tx_l, rx_v, rx_r, rx_l;
    wire [NODES*FLIT-1:0] tx_d, rx_d;
    genvar n;
    generate
        for (n = 0; n < NODES; n = n + 1) begin : g_link
            localparam integer DST = (n + 1) % NODES;
            ot_rom_pkg_link #(.FLIT_BYTES(FLIT / 8), .TX_STAGES(2), .CHANNEL_CYCLES(60), .RX_STAGES(2),
                              .CREDITS(32)) u_link (
                .clk(clk), .rst_n(a_rst_n),
                .in_valid(tx_v[n]), .in_ready(tx_r[n]), .in_data(tx_d[n*FLIT +: FLIT]), .in_last(tx_l[n]),
                .out_valid(rx_v[DST]), .out_ready(rx_r[DST]), .out_data(rx_d[DST*FLIT +: FLIT]),
                .out_last(rx_l[DST]), .credit_stalls());
        end

        for (n = 0; n < NODES; n = n + 1) begin : g_node
            localparam integer LAST = (n == NODES - 1);
            reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
            reg [31:0]           vm [0:VM_ELEMS-1];
            reg [W*32-1:0]       kv [0:NSLOT*KVW-1];

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
            wire          start, done;
            wire [NW-1:0] token, pos, ntok;
            wire [31:0]   nval;
            wire [AW-1:0] kv_base;
            wire          c_we, c_re; wire [7:0] c_waddr, c_raddr;
            wire [FLIT-1:0] c_wdata; reg [FLIT-1:0] c_rq;
            wire          n_pr_re; wire [7:0] n_pr_user; wire [NW-1:0] n_pr_pos;

            ot_hdc_core #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW)) core (
                .clk(clk), .rst_n(a_rst_n), .start(start), .token(token), .pos(pos),
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

            wire t_v; wire [7:0] t_u; wire [NW-1:0] t_p, t_i; wire [7:0] u_done;
            ot_rom_pkg_ctrl #(.PKG_ID(n), .FLIT(FLIT), .NW(NW), .AW(AW), .VWA(8), .MAXU(MAXU), .KVW(KVW),
                              .XWORDS(XWORDS), .RXB(0), .TXB(0), .SOURCE(n == 0), .RESULT_PARTS(1),
                              .SEND_HIDDEN(!LAST), .HID_DEST((n + 1) % NODES), .SEND_RESULT(LAST),
                              .RES_DEST(0), .COMBINE_IN(0), .ROW0(0)) ctrl (
                .clk(clk), .rst_n(a_rst_n),
                .cfg_users(cfg_users), .cfg_prompt_len(cfg_plen), .cfg_gen_len(cfg_glen),
                .in_valid(rx_v[n]), .in_ready(rx_r[n]), .in_data(rx_d[n*FLIT +: FLIT]), .in_last(rx_l[n]),
                .out_valid(tx_v[n]), .out_ready(tx_r[n]), .out_data(tx_d[n*FLIT +: FLIT]), .out_last(tx_l[n]),
                .core_start(start), .core_token(token), .core_pos(pos), .core_done(done),
                .core_next_token(ntok), .core_next_val(nval), .kv_base(kv_base),
                .vm_we(c_we), .vm_waddr(c_waddr), .vm_wdata(c_wdata), .vm_re(c_re), .vm_raddr(c_raddr), .vm_rq(c_rq),
                .pr_re(n_pr_re), .pr_user(n_pr_user), .pr_pos(n_pr_pos), .pr_q(pb_q),
                .core_busy(busy_w[n]), .tok_valid(t_v), .tok_user(t_u), .tok_pos(t_p), .tok_id(t_i),
                .users_done(u_done), .proto_fault(pfault_w[n]));
            if (n == 0) begin : g_src
                assign tok_v = t_v; assign tok_u = t_u; assign tok_p = t_p; assign tok_i = t_i;
                assign users_done = u_done;
                assign pr_re = n_pr_re; assign pr_user = n_pr_user; assign pr_pos = n_pr_pos;
            end

            integer k, q, l;
            reg [8*512-1:0] pdir;
            localparam [7:0] D1 = 8'h30 + n / 10;
            localparam [7:0] D0 = 8'h30 + n % 10;
            initial begin
                if (!$value$plusargs("DIR=%s", pdir)) pdir = ".";
                $readmemh({pdir, "/prog_stage", D1, D0, ".hex"}, prog);
                for (k = 0; k < VM_ELEMS; k = k + 1) vm[k] = 32'd0;
                for (k = 0; k < NSLOT * KVW; k = k + 1) kv[k] = {(W*32){1'b0}};
            end
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
                if (c_we) for (l = 0; l < W; l = l + 1) vm[{c_waddr, 4'b0} + l] <= c_wdata[32*l +: 32];
                if (c_re) for (l = 0; l < W; l = l + 1) c_rq[32*l +: 32] <= vm[{c_raddr, 4'b0} + l];
            end
        end
    endgenerate

    reg [8*512-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/crom.hex"}, crom);
    end
endmodule
