`timescale 1ns/1ps
// Minimum-component bench of one DSpark MTP step on the as-built V4.1 core (ot_hdc_core_v41, NSLOT 8, MP
// `HDC_MP): ONE section of the ITER program (a draft stage, the DYN + Engram prologue, one verify layer over
// all slots, the head, ACCEPT, ...) from the ISA model's state before it (tools/dsrom_dspark_step_slices.py).
// +DIR: the slice (prog.hex = the section + END, vm_init/kv_init, stok/ttok, prime, expect_vm/kv, exp_heads,
// run.args +TOKEN +POS +NPRIME +NHEAD +EXPACC); +ROMDIR: the ROMs.  The slot tokens and verify targets are
// loaded into the accept unit before start (the start's DYN pass derives every slot's bank from them, as the
// step's DYN control step does); the Engram hash history is primed with the committed ids.  Checked bit for
// bit: every AMAX head in the section, the vector memory and KV SRAM after it, and ACCEPT's count.
// Prints SLICE cycles=<start to END> ...; +TRACE prints every issue.
//
// FUSED DRAFT HEAD bench (tools/dsrom_fused_draft_head.py): the same bench for the successor core
// (rtl/hdc/v41/dspark_fused_head) plus its addend read port (vra), and two more checks: every TOKX's draft
// token and the argmax value behind it against exp_tokx.hex (token, value bits; +NTOKX of them, in order --
// the as-built XU SELECT path latches no value, so +NTOKVAL=0 checks tokens only), and the slot tokens after
// the slice against exp_stok.hex.  Prints TOKX <i> tok=<t> val=<v> issue=<cycle> and FH tokx=.. lines.
`ifndef HDC_SW
`define HDC_SW 8
`endif
`ifndef HDC_MP
`define HDC_MP 1
`endif
module tb_hdc_core_v41_mtp_slice #(
    parameter integer NPC = 8,
    parameter integer LWIN = 10,
    parameter integer CLK_PS = 1000
) (input wire clk);
    localparam integer INSTR_BITS = 1536;
    localparam integer W = 16, G = 4, BL = 16, QLB = 272, AW = 24, NW = 16, PAW = 16, HNL = 3;
    localparam integer SW = `HDC_SW;          // stream-unit lanes
    localparam integer MP = `HDC_MP;          // lane multiplier
    localparam integer NSLOT = 8;
    localparam integer HS = 8;                // HE K chunks
    localparam integer HROM_WORDS = 1 << 16;
    localparam integer WROM_WORDS = 1 << 19, QROM_WORDS = 1 << 16, EROM_WORDS = 1 << 19, CROM_WORDS = 1 << 15;
    localparam integer KV_WORDS = 32768, VM_ELEMS = 131072, VOCAB = 4040, PROG_WORDS = 1 << PAW;
    localparam integer VA = 17;               // vector-memory element address bits
    localparam integer MAXH = 1024;           // heads checked

    reg [G*W*16-1:0]    wrom [0:WROM_WORDS-1];
    reg [HS*HNL*32-1:0] hrom [0:HROM_WORDS-1];
    reg [BL*QLB-1:0]    qrom [0:QROM_WORDS-1];
    reg [263:0]         erom [0:EROM_WORDS-1];
    reg [63:0]          crom [0:CROM_WORDS-1];
    reg [W*32-1:0]      kv   [0:KV_WORDS-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]          vm   [0:VM_ELEMS-1];
    reg [31:0]          e_vm [0:VM_ELEMS-1];
    reg [31:0]          e_kv [0:KV_WORDS*W-1];
    reg [31:0]          lg   [0:VOCAB-1];
    reg [31:0]          e_hd [0:MAXH*VOCAB-1];

    reg rst_n = 1'b0, start = 1'b0;
    reg prime_v = 1'b0;
    reg [11:0] prime_cid = 12'd0;
    reg [NW-1:0] token, pos;
    reg [PAW-1:0] entry;
    wire done, fault;
    wire [NW-1:0] next_token;
    wire [31:0] next_val, cycles;
    wire [3:0] acc_n;
    wire [NSLOT*NW-1:0] acc_tok;

    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
    wire [MP*SW-1:0] ewrom_re; wire [MP*SW*AW-1:0] ewrom_addr; reg [MP*SW*G*W*16-1:0] ewrom_q;
    wire qrom_re; wire [AW-1:0] qrom_addr;
`ifdef HDC_WHBM
    wire [BL*QLB-1:0] qrom_q;
`else
    reg  [BL*QLB-1:0] qrom_q;
`endif
    wire qd_v, q_ok, wrel_v; wire [AW-1:0] qd_wbase; wire [7:0] qd_nb; wire [NW-1:0] qd_tiles;
    wire hrom_re; wire [AW-1:0] hrom_addr; reg [HS*HNL*32-1:0] hrom_q;
    wire [MP*HS-1:0] vh_re; wire [MP*HS*AW-1:0] vh_addr; reg [MP*HS*32-1:0] vh_q;
    wire [MP-1:0] ww_h_we; wire [MP*AW-1:0] ww_h_addr; wire [MP*32-1:0] ww_h_mask; wire [MP*1024-1:0] ww_h_data;
    wire erom_re; wire [AW-1:0] erom_addr; reg [263:0] erom_q;
    wire [MP*4*SW-1:0] crom_re; wire [MP*4*SW*AW-1:0] crom_addr; reg [MP*4*SW*64-1:0] crom_q;
    wire xcrom_re; wire [AW-1:0] xcrom_addr; reg [63:0] xcrom_q;
    wire kv_re; wire [G*AW-1:0] kv_raddr; reg [G*W*32-1:0] kv_q;
    wire [MP*SW-1:0] kv_we; wire [MP*SW*AW-1:0] kv_waddr; wire [MP*SW*32-1:0] kv_wdata;
    wire [MP*G-1:0] vx_re; wire [MP*G*AW-1:0] vx_addr; reg [MP*G*32-1:0] vx_q;
    wire [MP*4*SW-1:0] vs_re; wire [MP*4*SW*AW-1:0] vs_addr; reg [MP*4*SW*32-1:0] vs_q;
    wire [MP*SW-1:0] vi_re; wire [MP*SW*AW-1:0] vi_addr; reg [MP*SW*32-1:0] vi_q;
    wire vq_re, vr_re, wqr_re, wxr_re;
    wire [AW-1:0] vq_addr, vr_addr, wqr_addr, wxr_addr;
    reg [31:0] vq_q, vr_q;
    reg [1023:0] wqr_q, wxr_q;
    wire [MP*G-1:0] vw_me_we; wire [MP*G*AW-1:0] vw_me_addr; wire [MP*G*W-1:0] vw_me_mask;
    wire [MP*G*W*32-1:0] vw_me_data;
    wire [MP*G-1:0] vra_re; wire [MP*G*AW-1:0] vra_addr; reg [MP*G*W*32-1:0] vra_raw; wire [MP*G*W*32-1:0] vra_q;
    ot_hdc_delay #(.W(MP*G*W*32),.D(`OT_FH_RETURN_EXTRA)) u_protected_return (.clk(clk),.rst_n(rst_n),.d(vra_raw),.q(vra_q));
    wire [MP*SW-1:0] vw_su_we, vw_rd_we; wire [MP*SW*AW-1:0] vw_su_addr, vw_rd_addr;
    wire [MP*SW*32-1:0] vw_su_data, vw_rd_data;
    wire vw_xe_we, ww_x_we;
    wire [MP-1:0] ww_q_we; wire [MP*AW-1:0] ww_q_addr; wire [MP*32-1:0] ww_q_mask; wire [MP*1024-1:0] ww_q_data;
    wire [AW-1:0] vw_xe_addr, ww_x_addr;
    wire [31:0] vw_xe_data, ww_x_mask;
    wire [1023:0] ww_x_data;
    wire me_ov; wire [MP*G*AW-1:0] me_oaddr; wire [MP*G*W-1:0] me_omask; wire [MP*G*W*32-1:0] me_odata;
    wire [4:0] unit_busy; wire [2:0] issue_unit;

`ifdef HDC_WHBM
    localparam integer WHBM = 1;
`else
    localparam integer WHBM = 0;
`endif
    ot_hdc_core_v41 #(.SW(SW), .HS(HS), .PAW(PAW), .NSLOT(NSLOT), .MP(MP), .W_HBM(WHBM)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos), .entry(entry), .acc_n(acc_n),
        .acc_tok(acc_tok),
        .done(done), .next_token(next_token), .next_val(next_val), .cycles(cycles), .fault(fault),
        .prime_v(prime_v), .prime_first(1'b0), .prime_cid(prime_cid),
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
        .vra_re(vra_re), .vra_addr(vra_addr), .vra_q(vra_q),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .vw_xe_we(vw_xe_we), .vw_xe_addr(vw_xe_addr), .vw_xe_data(vw_xe_data),
        .ww_q_we(ww_q_we), .ww_q_addr(ww_q_addr), .ww_q_mask(ww_q_mask), .ww_q_data(ww_q_data),
        .ww_x_we(ww_x_we), .ww_x_addr(ww_x_addr), .ww_x_mask(ww_x_mask), .ww_x_data(ww_x_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .unit_busy(unit_busy), .issue_unit(issue_unit),
        .qd_v(qd_v), .qd_wbase(qd_wbase), .qd_nb(qd_nb), .qd_tiles(qd_tiles), .q_ok(q_ok), .wrel_v(wrel_v));

    reg [8*512-1:0] dir;
    integer qb;
`ifdef HDC_WHBM
    // ---- QE weight streamer, its window and fetch list, HBM ------------------------------------
    localparam integer SPW = BL * QLB / 256, HMEM = 1 << 20, LAW = 13;
    reg [127:0]         qlist [0:(1 << LAW)-1];
    reg [255:0]         qwin [0:SPW-1][0:(1 << LWIN)-1];
    reg  [15:0] qlead, qrate;
    reg  [LAW-1:0] lbase, lbase_iter;
    wire l_re; wire [LAW-1:0] l_addr; reg [127:0] l_q;
    wire xi_re; wire [AW-1:0] xi_addr; reg [31:0] xi_q;
    wire [SPW-1:0] qw_we; wire [SPW*LWIN-1:0] qw_waddr; wire [BL*QLB-1:0] qw_wdata;
    wire qw_re; wire [LWIN-1:0] qw_raddr; reg [BL*QLB-1:0] qw_q;
    wire hq_v, hq_rdy; wire [23:0] hq_addr; wire [5:0] hq_len; wire [LWIN-1:0] hq_tag;
    wire [NPC-1:0] hr_v, hr_rdy, pc_room; wire [NPC*LWIN-1:0] hr_tag; wire [NPC*5-1:0] hr_beat;
    wire [NPC*256-1:0] hr_data;
    wire qs_fault; wire [3:0] qs_why; wire [31:0] qs_fetched, qs_consumed;
    ot_hdc_qstream #(.BL(BL), .QLB(QLB), .AW(AW), .HAW(24), .NW(NW), .LWIN(LWIN), .NPC(NPC), .LENW(6),
                     .BEATW(5), .LAW(LAW)) u_qs (
        .clk(clk), .rst_n(rst_n), .cfg_base(24'd0), .cfg_lbase(lbase), .cfg_lead(qlead), .cfg_rate(qrate),
        .tok_start(start), .pos(pos),
        .l_re(l_re), .l_addr(l_addr), .l_q(l_q), .vi_re(xi_re), .vi_addr(xi_addr), .vi_q(xi_q), .wrel_v(wrel_v),
        .qd_v(qd_v), .qd_nb(qd_nb), .qd_tiles(qd_tiles), .q_ok(q_ok),
        .qr_re(qrom_re), .qr_addr(qrom_addr), .qr_q(qrom_q),
        .win_we(qw_we), .win_waddr(qw_waddr), .win_wdata(qw_wdata), .win_re(qw_re), .win_raddr(qw_raddr),
        .win_q(qw_q),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag), .hq_room(pc_room),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(qs_fault), .fault_why(qs_why), .st_fetched(qs_fetched), .st_consumed(qs_consumed));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(24), .DW(256), .MEM_WORDS(HMEM), .TAGW(LWIN), .LENW(6), .BEATW(5),
                       .CLK_PS(CLK_PS), .PC_RDY(1), .PC_ROOM(16)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy), .pc_room(pc_room), .req_we(1'b0),
        .req_addr(hq_addr), .req_len(hq_len), .req_tag(hq_tag), .req_wdata(256'd0),
        .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag), .rsp_beat(hr_beat), .rsp_data(hr_data));
    always @(posedge clk) begin
        if (l_re) l_q <= qlist[l_addr];
        if (xi_re) xi_q <= vm[xi_addr[VA-1:0]];
        for (qb = 0; qb < SPW; qb = qb + 1) begin
            if (qw_re) qw_q[qb*256 +: 256] <= qwin[qb][qw_raddr];
            if (qw_we[qb]) qwin[qb][qw_waddr[qb*LWIN +: LWIN]] <= qw_wdata[qb*256 +: 256];
        end
    end
    // every delivered word against the ROM image
    reg qchk_v; reg [AW-1:0] qchk_a;
    integer q_bad = 0, q_words = 0, q_stall = 0;
    always @(posedge clk) begin
        qchk_v <= qrom_re; qchk_a <= qrom_addr;
        if (qchk_v) begin
            q_words <= q_words + 1;
            if (qrom_q !== qrom[qchk_a[15:0]]) q_bad = q_bad + 1;
        end
        if (dut.st == 6 && !dut.d_skip && dut.d_unit == 3 && dut.waited && dut.unit_ready && !dut.q_gate)
            q_stall <= q_stall + 1;
    end
    task qstats;
        integer p, sum_rd;
        begin
            sum_rd = 0;
            for (p = 0; p < NPC; p = p + 1) sum_rd = sum_rd + u_hbm.st_rd[p];
            $display("QSTREAM q_stall_cycles=%0d q_words=%0d q_bad=%0d qs_fault=%0d fetched=%0d consumed=%0d hbm_reads=%0d",
                     q_stall, q_words, q_bad, qs_fault, qs_fetched, qs_consumed, sum_rd);
        end
    endtask
    wire hbm_bad = qs_fault || (q_bad != 0);
`else
    assign q_ok = 1'b1;
    wire hbm_bad = 1'b0;
    task qstats; begin end endtask
`endif

    // synchronous-read memories
    integer l, q;
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[18:0]];
        for (q = 0; q < MP*SW; q = q + 1) if (ewrom_re[q]) ewrom_q[q*G*W*16 +: G*W*16] <= wrom[ewrom_addr[q*AW +: 19]];
`ifndef HDC_WHBM
        if (qrom_re) qrom_q <= qrom[qrom_addr[15:0]];
`endif
        if (hrom_re) hrom_q <= hrom[hrom_addr[15:0]];
        for (q = 0; q < MP*HS; q = q + 1) if (vh_re[q]) vh_q[32*q +: 32] <= vm[vh_addr[q*AW +: VA]];
        for (q = 0; q < MP; q = q + 1)
            if (ww_h_we[q]) for (l = 0; l < 32; l = l + 1)
                if (ww_h_mask[q*32 + l]) vm[ww_h_addr[q*AW +: VA] + l] <= ww_h_data[q*1024 + 32*l +: 32];
        if (erom_re) erom_q <= erom[erom_addr[18:0]];
        for (q = 0; q < MP*4*SW; q = q + 1) if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 15]];
        if (xcrom_re) xcrom_q <= crom[xcrom_addr[14:0]];
        for (q = 0; q < G; q = q + 1) if (kv_re) kv_q[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: 15]];
        for (q = 0; q < MP*G; q = q + 1) if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: VA]];
        for (q = 0; q < MP*G; q = q + 1)
            if (vra_re[q]) for (l = 0; l < W; l = l + 1)
                vra_raw[32*(q*W + l) +: 32] <= vm[{vra_addr[q*AW +: VA-4], 4'b0} + l];
        for (q = 0; q < MP*4*SW; q = q + 1) if (vs_re[q]) vs_q[32*q +: 32] <= vm[vs_addr[q*AW +: VA]];
        for (q = 0; q < MP*SW; q = q + 1) if (vi_re[q]) vi_q[32*q +: 32] <= vm[vi_addr[q*AW +: VA]];
        if (vq_re) vq_q <= vm[vq_addr[VA-1:0]];
        if (vr_re) vr_q <= vm[vr_addr[VA-1:0]];
        if (wqr_re) for (q = 0; q < 32; q = q + 1) wqr_q[32*q +: 32] <= vm[wqr_addr[VA-1:0] + q];
        if (wxr_re) for (q = 0; q < 32; q = q + 1) wxr_q[32*q +: 32] <= vm[wxr_addr[VA-1:0] + q];
        for (q = 0; q < MP*SW; q = q + 1)
            if (kv_we[q]) kv[kv_waddr[q*AW+4 +: 15]][32*kv_waddr[q*AW +: 4] +: 32] <= kv_wdata[32*q +: 32];
        for (q = 0; q < MP*G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: VA-4], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
        for (q = 0; q < MP*SW; q = q + 1) if (vw_su_we[q]) vm[vw_su_addr[q*AW +: VA]] <= vw_su_data[32*q +: 32];
        for (q = 0; q < MP*SW; q = q + 1) if (vw_rd_we[q]) vm[vw_rd_addr[q*AW +: VA]] <= vw_rd_data[32*q +: 32];
        if (vw_xe_we) vm[vw_xe_addr[VA-1:0]] <= vw_xe_data;
        for (q = 0; q < MP; q = q + 1)
            if (ww_q_we[q]) for (l = 0; l < 32; l = l + 1)
                if (ww_q_mask[q*32 + l]) vm[ww_q_addr[q*AW +: VA] + l] <= ww_q_data[q*1024 + 32*l +: 32];
        if (ww_x_we) for (q = 0; q < 32; q = q + 1) if (ww_x_mask[q]) vm[ww_x_addr[VA-1:0] + q] <= ww_x_data[32*q +: 32];
        // the result words of an unwritten matrix-vector op (a head with its argmax) are logits
        if (me_ov && vw_me_we == 0)
            for (q = 0; q < G; q = q + 1)
                for (l = 0; l < W; l = l + 1)
                    if (me_omask[q*W + l] && ({me_oaddr[q*AW +: 12], 4'b0} + l) < VOCAB)
                        lg[{me_oaddr[q*AW +: 12], 4'b0} + l] <= me_odata[32*(q*W + l) +: 32];
    end


    integer cyc = 0, i, k, bad_vm, bad_kv;
    reg trace = 1'b0;
    reg [8*512-1:0] romdir;
    reg [NW-1:0] stok_i [0:7];
    reg [NW-1:0] ttok_i [0:7];
    reg [NW-1:0] prime [0:7];
    reg [31:0] kvflat [0:KV_WORDS*W-1];
    integer n_prime = 0, prime_i = 0, nh = 0, head_bad = 0, n_head = 0, exp_acc = 0, tok0 = 0, pos0 = 0;
    reg [31:0] kv_e;
    integer busy_me = 0, busy_su = 0, busy_qe = 0, busy_xu = 0, busy_he = 0;
    always @(posedge clk) if (dut.st != 0) begin
        if (unit_busy[0]) busy_me <= busy_me + 1;
        if (unit_busy[1]) busy_su <= busy_su + 1;
        if (unit_busy[2]) busy_qe <= busy_qe + 1;
        if (unit_busy[3]) busy_xu <= busy_xu + 1;
        if (unit_busy[4]) busy_he <= busy_he + 1;
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("ROMDIR=%s", romdir)) romdir = dir;
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if (!$value$plusargs("TOKEN=%d", tok0)) tok0 = 0;
        if (!$value$plusargs("POS=%d", pos0)) pos0 = 0;
        if (!$value$plusargs("NPRIME=%d", n_prime)) n_prime = 0;
        if (!$value$plusargs("NHEAD=%d", n_head)) n_head = 0;
        if (!$value$plusargs("EXPACC=%d", exp_acc)) exp_acc = 0;
        $readmemh({romdir, "/wrom.hex"}, wrom);
        $readmemh({romdir, "/qrom.hex"}, qrom);
        $readmemh({romdir, "/hrom.hex"}, hrom);
        $readmemh({romdir, "/erom.hex"}, erom);
        $readmemh({romdir, "/crom.hex"}, crom);
        $readmemh({dir, "/prog.hex"}, prog);
        $readmemh({dir, "/stok.hex"}, stok_i);
        $readmemh({dir, "/ttok.hex"}, ttok_i);
        $readmemh({dir, "/prime.hex"}, prime);
        $readmemh({dir, "/exp_heads.hex"}, e_hd);
        $readmemh({dir, "/expect_vm.hex"}, e_vm);
        $readmemh({dir, "/expect_kv.hex"}, e_kv);
        $readmemh({dir, "/vm_init.hex"}, vm);
        $readmemh({dir, "/kv_init.hex"}, kvflat);
        for (i = 0; i < 32; i = i + 1) e_tokx[i] = 0;
        for (i = 0; i < 8; i = i + 1) e_stok[i] = 0;
        if (!$value$plusargs("NTOKX=%d", ntokx_exp)) ntokx_exp = 0;
        if (!$value$plusargs("NTOKVAL=%d", ntokval)) ntokval = 1;
        if (ntokx_exp > 0) $readmemh({dir, "/exp_tokx.hex"}, e_tokx);
        $readmemh({dir, "/exp_stok.hex"}, e_stok);
        for (i = 0; i < KV_WORDS * W; i = i + 1) kv[i / W][32*(i % W) +: 32] = kvflat[i];
        for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
    end

    task check_head;
        integer hb;
        begin
            hb = 0;
            for (i = 0; i < VOCAB; i = i + 1) if (lg[i] !== e_hd[nh * VOCAB + i]) hb = hb + 1;
            if (hb != 0) begin
                if (head_bad < 5) $display("HEAD %0d: %0d logits differ", nh, hb);
                head_bad = head_bad + 1;
            end
            nh = nh + 1;
            for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
        end
    endtask

    task check_state;
        begin
            bad_vm = 0; bad_kv = 0;
            for (i = 0; i < VM_ELEMS; i = i + 1) if (vm[i] !== e_vm[i]) begin
                if (bad_vm < 10) $display("vm %0d rtl %h expect %h", i, vm[i], e_vm[i]);
                bad_vm = bad_vm + 1;
            end
            for (i = 0; i < KV_WORDS * W; i = i + 1) begin
                kv_e = kv[i / W][32*(i % W) +: 32];
                if (kv_e !== e_kv[i]) begin
                    if (bad_kv < 10) $display("kv %0d rtl %h expect %h", i, kv_e, e_kv[i]);
                    bad_kv = bad_kv + 1;
                end
            end
        end
    endtask

    always @(posedge clk) if (dut.amax_v) check_head();

    // FUSED: every TOKX (token and the ME argmax value behind it), and the slot tokens after the slice
    reg [31:0] e_tokx [0:31];
    reg [NW-1:0] e_stok [0:7];
    integer n_tokx = 0, tokx_bad = 0, ntokx_exp = 0, ntokval = 1, stok_bad = 0, last_issue = 0;
    always @(posedge clk) if (dut.st != 0 && issue_unit != 0) last_issue <= cycles;
    always @(posedge clk) if (dut.tokx_v) begin
        $display("TOKX %0d tok=%0d val=%h cyc=%0d", n_tokx, dut.tokx_me ? dut.amax_tok : dut.xu_sel_first[NW-1:0],
                 dut.am_val_v[31:0], cycles);
        if ((dut.tokx_me ? dut.amax_tok : dut.xu_sel_first[NW-1:0]) !== e_tokx[2 * n_tokx][NW-1:0] ||
            (ntokval != 0 && dut.am_val_v[31:0] !== e_tokx[2 * n_tokx + 1]))
            tokx_bad = tokx_bad + 1;
        n_tokx = n_tokx + 1;
    end

    reg started = 1'b0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        // the committed Engram history, one id a cycle
        prime_v <= 1'b0;
        if (cyc >= 8 && prime_i < n_prime) begin
            prime_v <= 1'b1; prime_cid <= prime[prime_i][11:0]; prime_i <= prime_i + 1;
        end
        start <= 1'b0;
        if (cyc == 40) begin
            for (k = 1; k < 8; k = k + 1) dut.g_acc.u_acc.s[k] = stok_i[k];
            for (k = 0; k < 8; k = k + 1) dut.g_acc.u_acc.t[k] = ttok_i[k];
            token <= stok_i[0]; pos <= pos0; entry <= 0; start <= 1'b1; started <= 1'b1;
        end
        if (started && cyc > 42 && done && !start) begin
            check_state();
            for (k = 0; k < 8; k = k + 1) if (dut.stok[k * NW +: NW] !== e_stok[k]) stok_bad = stok_bad + 1;
            $display("FH tokx=%0d exp_tokx=%0d tokx_bad=%0d stok_bad=%0d", n_tokx, ntokx_exp, tokx_bad, stok_bad);
            $display("SLICE cycles=%0d heads=%0d head_mismatches=%0d acc_n=%0d exp_acc_n=%0d vm_mismatch=%0d kv_mismatch=%0d fault=%0d busy_me=%0d busy_su=%0d busy_qe=%0d busy_xu=%0d busy_he=%0d",
                     cycles, nh, head_bad, acc_n, exp_acc, bad_vm, bad_kv, fault, busy_me, busy_su, busy_qe, busy_xu,
                     busy_he);
            if (head_bad == 0 && nh == n_head && bad_vm == 0 && bad_kv == 0 && !fault && acc_n == exp_acc && !hbm_bad &&
                tokx_bad == 0 && n_tokx == ntokx_exp && stok_bad == 0)
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
        if (trace && issue_unit != 0)
            $display("ISSUE cyc=%0d pc=%0d unit=%0d", cycles, dut.pc, issue_unit);
        if (cyc > 50000000) begin
            $display("TIMEOUT pc=%0d st=%0d idles=%b", dut.pc, dut.st, dut.idles);
            $display("FAIL");
            $finish;
        end
    end
endmodule
