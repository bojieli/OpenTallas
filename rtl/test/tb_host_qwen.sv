`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Host-interface simulation top, Qwen3 ROM reticle: ot_host_if (MODE 0, one
// context per slot) driving one hardwired decode core (ot_hdc_core) with its
// behavioural memories (tools/hdc_program.py images from +DIR).  The KV SRAM
// holds NSLOT slices of KVW words; the host interface's kv_base selects the
// running user's slice, as ot_rom_pkg_ctrl does in the array.
// Host side: tb_host_ports.svh, driven by rtl/test/host_bridge_harness.cpp.
// ---------------------------------------------------------------------------
module tb_host_qwen #(
    parameter integer G = 4,
    parameter integer NSLOT = 16
) (
`include "tb_host_ports.svh"
);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12, PLB = 8;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096, KVW = 1024;
    localparam integer VM_ELEMS = 4096, PROG_WORDS = 4096;
    localparam integer SB = $clog2(NSLOT);

    reg [G*W*16-1:0]     wrom [0:WROM_WORDS-1];
    reg [63:0]           crom [0:CROM_WORDS-1];
    reg [W*32-1:0]       kv   [0:NSLOT*KVW-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]           vm   [0:VM_ELEMS-1];
    reg [NW-1:0]         pbuf [0:NSLOT*(1<<PLB)-1];

    wire pb_we, pb_re; wire [SB+PLB-1:0] pb_waddr, pb_raddr; wire [NW-1:0] pb_wdata; reg [NW-1:0] pb_q;
    wire start, done, fault;
    wire [NW-1:0] token, pos, next_token;
    wire [31:0] next_val, cycles;
    wire [SB-1:0] slot;
    wire [AW-1:0] kv_base;

    ot_host_if #(.NSLOT(NSLOT), .MODE(0), .ENG_CTX(NSLOT), .NW(NW), .PLB(PLB), .CTX_MAX(64), .AW(AW),
                 .KVW(KVW)) u_host (
`include "tb_host_conn.svh"
        .eng_start(start), .eng_token(token), .eng_pos(pos), .eng_slot(slot), .kv_base(kv_base),
        .eng_done(done), .eng_next_token(next_token), .eng_cycles(cycles), .eng_fault(fault),
        .eng_clr_req(), .eng_clr_ack(1'b0),
        .arr_rst_n(), .cfg_users(), .cfg_prompt_len(), .cfg_gen_len(),
        .pr_re(1'b0), .pr_user(8'd0), .pr_pos({NW{1'b0}}),
        .tok_valid(1'b0), .tok_user(8'd0), .tok_pos({NW{1'b0}}), .tok_id({NW{1'b0}}), .users_done(8'd0),
        .arr_fault(1'b0));
    assign eng_busy = u_host.inflight;

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

    ot_hdc_core #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW)) core (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .next_val(next_val), .cycles(cycles), .fault(fault),
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

    wire [AW-1:0] kv_wword = (kv_waddr >> 4) + kv_base;
    integer l, q, i;
    always @(posedge clk) begin
        if (pb_we) pbuf[pb_waddr] <= pb_wdata;
        if (pb_re) pb_q <= pbuf[pb_raddr];
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
    end

    reg [8*512-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/crom.hex"}, crom);
        $readmemh({dir, "/prog.hex"}, prog);
        for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
        for (i = 0; i < NSLOT*KVW; i = i + 1) kv[i] = {(W*32){1'b0}};
    end
endmodule
