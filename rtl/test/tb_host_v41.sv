`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Host-interface simulation top, DeepSeek-V4.1 ROM die: ot_host_if (MODE 0,
// ENG_CTX 1) driving the V4.1 decode core (ot_hdc_core_v41) with its
// behavioural memories (tools/hdc_program_v41.py images from +DIR).
//
// The V4.1 core keeps user state beyond the KV cache -- the persistent
// vector-memory regions and the Engram hash history inside the core -- so it
// serves one user at a time.  Before a different user's first step the host
// interface raises eng_clr_req; this top then holds the core in reset and
// zeroes its vector memory and KV SRAM (behaviourally, in one cycle: in
// silicon the memories' clear or BIST-initialisation engine) and acknowledges.
// ---------------------------------------------------------------------------
module tb_host_v41 #(
    parameter integer NSLOT = 16
) (
`include "tb_host_ports.svh"
);
    localparam integer INSTR_BITS = 1536;
    localparam integer W = 16, G = 4, BL = 16, QLB = 272, AW = 24, NW = 16, PAW = 14, HNL = 3, PLB = 8;
    localparam integer HROM_WORDS = 1 << 19;
    localparam integer WROM_WORDS = 1 << 19, QROM_WORDS = 1 << 16, EROM_WORDS = 1 << 19, CROM_WORDS = 1 << 15;
    localparam integer KV_WORDS = 32768, VM_ELEMS = 65536, PROG_WORDS = 1 << PAW;
    localparam integer SB = $clog2(NSLOT);

    reg [G*W*16-1:0]    wrom [0:WROM_WORDS-1];
    reg [HNL*32-1:0]    hrom [0:HROM_WORDS-1];
    reg [BL*QLB-1:0]    qrom [0:QROM_WORDS-1];
    reg [263:0]         erom [0:EROM_WORDS-1];
    reg [63:0]          crom [0:CROM_WORDS-1];
    reg [W*32-1:0]      kv   [0:KV_WORDS-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]          vm   [0:VM_ELEMS-1];
    reg [NW-1:0]        pbuf [0:NSLOT*(1<<PLB)-1];

    wire pb_we, pb_re; wire [SB+PLB-1:0] pb_waddr, pb_raddr; wire [NW-1:0] pb_wdata; reg [NW-1:0] pb_q;
    wire start, done, fault;
    wire [NW-1:0] token, pos, next_token;
    wire [31:0] next_val, cycles;
    wire clr_req; reg clr_ack = 1'b0; reg core_rst_n = 1'b1;

    ot_host_if #(.NSLOT(NSLOT), .MODE(0), .ENG_CTX(1), .NW(NW), .PLB(PLB), .CTX_MAX(128), .AW(AW),
                 .KVW(KV_WORDS)) u_host (
`include "tb_host_conn.svh"
        .eng_start(start), .eng_token(token), .eng_pos(pos), .eng_slot(), .kv_base(),
        .eng_done(done), .eng_next_token(next_token), .eng_cycles(cycles), .eng_fault(fault),
        .eng_clr_req(clr_req), .eng_clr_ack(clr_ack),
        .arr_rst_n(), .cfg_users(), .cfg_prompt_len(), .cfg_gen_len(),
        .pr_re(1'b0), .pr_user(8'd0), .pr_pos({NW{1'b0}}),
        .tok_valid(1'b0), .tok_user(8'd0), .tok_pos({NW{1'b0}}), .tok_id({NW{1'b0}}), .users_done(8'd0),
        .arr_fault(1'b0));
    assign eng_busy = u_host.inflight;

    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re, ewrom_re; wire [AW-1:0] wrom_addr, ewrom_addr; reg [G*W*16-1:0] wrom_q, ewrom_q;
    wire qrom_re; wire [AW-1:0] qrom_addr; reg [BL*QLB-1:0] qrom_q;
    wire hrom_re; wire [AW-1:0] hrom_addr; reg [HNL*32-1:0] hrom_q;
    wire vh_re; wire [AW-1:0] vh_addr; reg [31:0] vh_q;
    wire ww_h_we; wire [AW-1:0] ww_h_addr; wire [31:0] ww_h_mask; wire [1023:0] ww_h_data;
    wire erom_re; wire [AW-1:0] erom_addr; reg [263:0] erom_q;
    wire [3:0] crom_re; wire [4*AW-1:0] crom_addr; reg [4*64-1:0] crom_q;
    wire xcrom_re; wire [AW-1:0] xcrom_addr; reg [63:0] xcrom_q;
    wire kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr; reg [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
    wire [3:0] vs_re; wire [4*AW-1:0] vs_addr; reg [4*32-1:0] vs_q;
    wire vi_re, vq_re, vr_re, wqr_re, wxr_re;
    wire [AW-1:0] vi_addr, vq_addr, vr_addr, wqr_addr, wxr_addr;
    reg [31:0] vi_q, vq_q, vr_q;
    reg [1023:0] wqr_q, wxr_q;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr; wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data;
    wire vw_su_we, vw_rd_we, vw_xe_we, ww_q_we, ww_x_we;
    wire [AW-1:0] vw_su_addr, vw_rd_addr, vw_xe_addr, ww_q_addr, ww_x_addr;
    wire [31:0] vw_su_data, vw_rd_data, vw_xe_data, ww_q_mask, ww_x_mask;
    wire [1023:0] ww_q_data, ww_x_data;
    wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire [4:0] unit_busy; wire [2:0] issue_unit;

    ot_hdc_core_v41 core (
        .clk(clk), .rst_n(rst_n && core_rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .next_val(next_val), .cycles(cycles), .fault(fault),
        .prime_v(1'b0), .prime_first(1'b0), .prime_cid(12'd0),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .ewrom_re(ewrom_re), .ewrom_addr(ewrom_addr), .ewrom_q(ewrom_q),
        .qrom_re(qrom_re), .qrom_addr(qrom_addr), .qrom_q(qrom_q),
        .hrom_re(hrom_re), .hrom_addr(hrom_addr), .hrom_q(hrom_q), .vh_re(vh_re), .vh_addr(vh_addr), .vh_q(vh_q),
        .ww_h_we(ww_h_we), .ww_h_addr(ww_h_addr), .ww_h_mask(ww_h_mask), .ww_h_data(ww_h_data),
        .erom_re(erom_re), .erom_addr(erom_addr), .erom_q(erom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .xcrom_re(xcrom_re), .xcrom_addr(xcrom_addr), .xcrom_q(xcrom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q), .vs_re(vs_re), .vs_addr(vs_addr), .vs_q(vs_q),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .vq_re(vq_re), .vq_addr(vq_addr), .vq_q(vq_q),
        .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .wqr_re(wqr_re), .wqr_addr(wqr_addr), .wqr_q(wqr_q),
        .wxr_re(wxr_re), .wxr_addr(wxr_addr), .wxr_q(wxr_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .vw_xe_we(vw_xe_we), .vw_xe_addr(vw_xe_addr), .vw_xe_data(vw_xe_data),
        .ww_q_we(ww_q_we), .ww_q_addr(ww_q_addr), .ww_q_mask(ww_q_mask), .ww_q_data(ww_q_data),
        .ww_x_we(ww_x_we), .ww_x_addr(ww_x_addr), .ww_x_mask(ww_x_mask), .ww_x_data(ww_x_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .unit_busy(unit_busy), .issue_unit(issue_unit));

    integer l, q, i;
    always @(posedge clk) begin
        if (pb_we) pbuf[pb_waddr] <= pb_wdata;
        if (pb_re) pb_q <= pbuf[pb_raddr];
        // clear handshake: reset the core for two cycles, zero its user state, acknowledge
        clr_ack <= 1'b0;
        if (clr_req && !clr_ack && core_rst_n) begin
            core_rst_n <= 1'b0;
            for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
            for (i = 0; i < KV_WORDS; i = i + 1) kv[i] = {(W*32){1'b0}};
        end else if (!core_rst_n) begin
            core_rst_n <= 1'b1; clr_ack <= 1'b1;
        end
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[18:0]];
        if (ewrom_re) ewrom_q <= wrom[ewrom_addr[18:0]];
        if (qrom_re) qrom_q <= qrom[qrom_addr[15:0]];
        if (hrom_re) hrom_q <= hrom[hrom_addr[18:0]];
        if (vh_re) vh_q <= vm[vh_addr[15:0]];
        if (ww_h_we) for (q = 0; q < 32; q = q + 1) if (ww_h_mask[q]) vm[ww_h_addr[15:0] + q] <= ww_h_data[32*q +: 32];
        if (erom_re) erom_q <= erom[erom_addr[18:0]];
        for (q = 0; q < 4; q = q + 1) if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 15]];
        if (xcrom_re) xcrom_q <= crom[xcrom_addr[14:0]];
        for (q = 0; q < G; q = q + 1) if (kv_re) kv_q[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: 15]];
        for (q = 0; q < G; q = q + 1) if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 16]];
        for (q = 0; q < 4; q = q + 1) if (vs_re[q]) vs_q[32*q +: 32] <= vm[vs_addr[q*AW +: 16]];
        if (vi_re) vi_q <= vm[vi_addr[15:0]];
        if (vq_re) vq_q <= vm[vq_addr[15:0]];
        if (vr_re) vr_q <= vm[vr_addr[15:0]];
        if (wqr_re) for (q = 0; q < 32; q = q + 1) wqr_q[32*q +: 32] <= vm[wqr_addr[15:0] + q];
        if (wxr_re) for (q = 0; q < 32; q = q + 1) wxr_q[32*q +: 32] <= vm[wxr_addr[15:0] + q];
        if (kv_we) kv[kv_waddr[18:4]][32*kv_waddr[3:0] +: 32] <= kv_wdata;
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: 12], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
        if (vw_su_we) vm[vw_su_addr[15:0]] <= vw_su_data;
        if (vw_rd_we) vm[vw_rd_addr[15:0]] <= vw_rd_data;
        if (vw_xe_we) vm[vw_xe_addr[15:0]] <= vw_xe_data;
        if (ww_q_we) for (q = 0; q < 32; q = q + 1) if (ww_q_mask[q]) vm[ww_q_addr[15:0] + q] <= ww_q_data[32*q +: 32];
        if (ww_x_we) for (q = 0; q < 32; q = q + 1) if (ww_x_mask[q]) vm[ww_x_addr[15:0] + q] <= ww_x_data[32*q +: 32];
    end

    reg [8*512-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/qrom.hex"}, qrom);
        $readmemh({dir, "/hrom.hex"}, hrom);
        $readmemh({dir, "/erom.hex"}, erom);
        $readmemh({dir, "/crom.hex"}, crom);
        $readmemh({dir, "/prog.hex"}, prog);
        for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
        for (i = 0; i < KV_WORDS; i = i + 1) kv[i] = {(W*32){1'b0}};
    end
endmodule
