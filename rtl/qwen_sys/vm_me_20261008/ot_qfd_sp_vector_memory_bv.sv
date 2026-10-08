`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_sp_vector_memory_bv (qwen-vm-me 2026-10-08): the banked vector memory of qwen-rtl-finish
// (ot_qfd_sp_vector_memory: 64 row banks, the parallel ME x service) completed with the ports the token bench's
// behavioural VM has and the banked one lacked:
//
//   SU lane reads   the split stream unit's 3 x SW scalar lanes (va / vb / vc).  Served by DEDICATED BANKS: NSU = 3
//                   replica copies of the row-banked store, one per operand, so the ME x beats (copy 0) and the three
//                   SU operands never compete for a macro read port.  A replica is NRBS = 16 row banks of two
//                   ot_sram_1r1w_1024x256 macros (row r in bank r mod 16, 695 of 1,024 lines used): 32 macros a copy
//                   against copy 0's 128 ot_sram_1r1w_256x256 (the x beats need 64 banks), 2.4x denser.  The SU sends each operand as a descriptor
//                   {re0, re1, a0, a1} (lane 0 / lane 1 strobes and addresses: every lane reads a0 + l * (a1 - a0),
//                   ot_hdc_vstream_lane), stride a1 - a0 in {0, 1} (the Qwen program's VM operand strides; else
//                   w_fault).  A vector of SW lanes spans <= NWR = (SW + 30) / 16 consecutive rows = NWR distinct
//                   banks: conflict-free in its copy.  Answer: all SW lanes, FIXED latency 1 + VL edges after the
//                   strobe (VL = 7; the base answers at 1): the SU master runs its lanes at ot_hdc_vstream_lane
//                   ML = max(VL, its constant-ROM ML) and delays this answer by ML - VL.
//   SU lane writes  {mask[SW], a0, a1, data}: <= NWR rows (stride 1) or one element (stride 0: the highest masked lane
//                   wins, as the base's lane-ordered commit).
//   reducer write   one element (skid source), the sequencer's row write w_* (skid source), the tree top's per-slot
//                   maxima row mx_* (engine-edge sampled, skid source).
//   ME results      NB = 6 band serializer links (ot_qfd_res_ser) into the 6:1 merge (ot_qfd_res_merge, inside), one
//                   row a cycle onto the bank-write arbiter; land_cnt counts landed bursts for the tree top.
// Writes are BROADCAST to every copy at the same edge (the copies stay identical).  Uniform latency (the exactness
// argument): every read and every write presented at edge t reaches the macros at edge t + 4 (SU reads: descriptor
// register, broadcast register, per-bank address register beside the macro; writes: descriptor register, row
// formation register, per-bank write register beside the macro), and a 1R1W macro reads the old word when it is
// written in the same edge, so an SU read sees exactly the writes presented before it, as the base.  Per bank, the SU
// lane rows have priority (fixed timing, distinct banks; banks counted mod NRBS, which divides NRB, so a grant set
// is conflict-free in every copy); the three skid sources (in the base's commit order mx, rd,
// seq) take a free bank, else wait in a SQD-deep queue; the merge's row takes what is left.  An entry that misses its
// nominal edge is LATE: a read of its row (any copy) or another write onto its row while it is late is w_hazard (the
// contract, as the x path's: programs never touch such a row within the few edges of a bank conflict); a queue
// overflow is w_fault.  The x path (copy 0) is ot_qfd_sp_vector_memory's, its hazard check now over every landing row.
// ME result rows reach the memory at a variable time; the tree top counts LANDED bursts, so consumers that wait on
// its progress / idle (the base's contract for ME outputs) see them.
// me_ok: AND of the band serializers' rok (to the die's me_mem_ok), registered.
// MUT = 1: the SU read lane select takes the element one lane off (bench must FAIL).  MUT = 2: the x shift is off
// by one lane (ot_qfd_sp_vector_memory's mutant).
// ---------------------------------------------------------------------------------------------------------------------
// SU replica bank: NRBS-banked rows (512 b) in two ot_sram_1r1w_1024x256 macros (USE_MACRO) or a behavioural model
// with the same one-edge registered read.
module ot_qfd_vm_rowbank_s #(
    parameter integer DEPTH = 1024,
    parameter integer LAW = 10,
    parameter integer USE_MACRO = 0
) (
    input  wire          clk,
    input  wire          re,
    input  wire [LAW-1:0] raddr,
    output wire [511:0]  q,
    input  wire          we,
    input  wire [LAW-1:0] waddr,
    input  wire [15:0]   wmask,
    input  wire [511:0]  wdata
);
    wire [511:0] bm;
    genvar e;
    generate for (e = 0; e < 16; e = e + 1) begin : g_m
        assign bm[32*e +: 32] = {32{wmask[e]}};
    end endgenerate
    generate if (USE_MACRO != 0) begin : g_mac
        wire [9:0] ra = raddr, wa = waddr;
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(q[255:0]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wdata[255:0]), .w_mask_in(bm[255:0]),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(q[511:256]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wdata[511:256]), .w_mask_in(bm[511:256]),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end else begin : g_beh
        reg [511:0] mem [0:DEPTH-1];
        reg [511:0] qr;
        integer i;
        initial for (i = 0; i < DEPTH; i = i + 1) mem[i] = 512'd0;
        always @(posedge clk) begin
            if (re) qr <= mem[raddr];
            if (we) mem[waddr] <= (mem[waddr] & ~bm) | (wdata & bm);
        end
        assign q = qr;
    end endgenerate
endmodule


module ot_qfd_sp_vector_memory_bv #(
    parameter integer ELEMS = 177808,
    parameter integer NRB = 64,
    parameter integer AW = 24,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer XVM = 14,
    parameter integer BMAX = 8,
    parameter integer ND = 14,
    parameter [ND*8-1:0] DSET = {8'd96, 8'd64, 8'd48, 8'd32, 8'd24, 8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0},
    parameter integer SW = 64,
    parameter integer NSU = 3,
    parameter integer NB = 6,
    parameter integer CRB = 4,
    parameter integer SQD = 2,
    parameter integer NRBS = 16,                       // banks of each SU replica copy (rows r mod NRBS)
    parameter integer USE_MACRO = 0,
    parameter integer MUT = 0
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    me_en,
    // x descriptor (tree top)
    input  wire                    x_dv,
    input  wire [AW-1:0]           x_dc,
    input  wire [AW-1:0]           x_dcs,
    input  wire [3:0]              x_dsp,
    output reg  [(1<<SMAX)*32-1:0] x_q,
    output wire                    x_rdy,
    output reg                     x_fault,
    output reg                     x_hazard,
    // SU lane reads (operand o = 0 a, 1 b, 2 c): descriptors, answers 1 + VL edges later
    input  wire [NSU-1:0]          s_re0,
    input  wire [NSU-1:0]          s_re1,
    input  wire [NSU*AW-1:0]       s_a0,
    input  wire [NSU*AW-1:0]       s_a1,
    output wire [NSU*SW*32-1:0]    s_q,
    // SU lane writes
    input  wire [SW-1:0]           sw_mask,
    input  wire [AW-1:0]           sw_a0,
    input  wire [AW-1:0]           sw_a1,
    input  wire [SW*32-1:0]        sw_data,
    // reducer write
    input  wire                    rd_v,
    input  wire [AW-1:0]           rd_addr,
    input  wire [31:0]             rd_data,
    // sequencer row write / read
    input  wire                    w_v,
    input  wire [AW-5:0]           w_row,
    input  wire [15:0]             w_mask,
    input  wire [511:0]            w_data,
    input  wire                    r_v,
    output wire                    r_rdy,
    input  wire [AW-5:0]           r_row,
    output wire                    r_qv,
    output wire [511:0]            r_q,
    // tree top per-slot maxima (engine-clock registers)
    input  wire                    mx_we,
    input  wire [AW-1:0]           mx_addr,
    input  wire [15:0]             mx_mask,
    input  wire [511:0]            mx_data,
    // ME result links (band serializers)
    input  wire [NB-1:0]           rb_v,
    input  wire [NB-1:0]           rb_end,
    input  wire [NB-1:0]           rb_nul,
    input  wire [NB*(AW-4)-1:0]    rb_row,
    input  wire [NB*16-1:0]        rb_mask,
    input  wire [NB*512-1:0]       rb_data,
    output wire [NB-1:0]           rb_cr,
    input  wire [NB-1:0]           rb_ok,
    output reg                     me_ok,
    output wire [15:0]             land_cnt,
    output reg                     w_fault,
    output reg                     w_hazard
);
    localparam integer RW = AW - 4;
    localparam integer NX = 1 << SMAX;
    localparam integer LNRB = $clog2(NRB);
    localparam integer ROWS = (ELEMS + 15) / 16;
    localparam integer DEPTH = (ROWS + NRB - 1) / NRB;
    localparam integer LAW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer BEAT = (NRB - 1) * 16;
    localparam integer LB = $clog2(BMAX) + 1;
    localparam integer HL = XVM + 2;
    localparam integer RL = 3;
    localparam integer NWR = (SW + 30) / 16;           // rows an SU vector can span
    localparam integer NWE = NWR * 16;
    localparam integer LSW = (SW > 1) ? $clog2(SW) : 1;
    localparam integer NP = NWR + 7;                   // coarse-rotate positions
    localparam integer NK = 3;                         // skid sources: 0 mx, 1 rd, 2 seq (base commit order)
    localparam integer LNRBS = $clog2(NRBS);
    localparam integer DEPTHS = (ROWS + NRBS - 1) / NRBS;
    localparam integer LAWS = (DEPTHS > 1) ? $clog2(DEPTHS) : 1;
    localparam integer NPS = (NWR + 7 < NRBS) ? NWR + 7 : NRBS;   // coarse-rotate positions of an SU copy
    localparam integer NL = NK * (SQD + 1);            // late rows checked per cycle (queue entries + late grants)
    integer i, a, di, k, b;
    genvar g, gc, c, dd;

    // =================================================================================================================
    // x path (copy 0), as ot_qfd_sp_vector_memory
    // =================================================================================================================
    reg  [HL-1:0] h_new;
    reg  [AW-1:0] h_dc [0:HL-1];
    reg  [AW-1:0] h_d  [0:HL-1];
    reg  [3:0]    h_sp [0:HL-1];
    reg  [LB-1:0] h_b  [0:HL-1];
    reg  [AW+12:0] h_span [0:HL-1];
    reg           p_v;
    reg  [AW-1:0] p_dc, p_d;
    reg  [3:0]    p_sp;
    wire [AW+12:0] span_n = (({{13{1'b0}}, {AW{1'b0}}} | ((1 << x_dsp) - 1)) * x_dcs);
    wire           same = p_v && x_dv && p_dc == x_dc && p_d == x_dcs && p_sp == x_dsp;
    wire           nt = x_dv && !same;
    wire [AW+12:0] bq = span_n / BEAT;
    reg  [ND-1:0]  din;
    always @(*) for (di = 0; di < ND; di = di + 1) din[di] = (x_dcs == DSET[di*8 +: 8]);
    reg            bi_v;
    reg  [LB-1:0]  bi_j;
    reg  [AW-1:0]  bi_dc, bi_d;
    reg  [3:0]     bi_sp;
    reg  [1:0]     bi_n;
    reg  [AW+12:0] bi_end;                               // the tuple's last element
    always @(*) begin
        bi_v = 1'b0; bi_j = 0; bi_dc = 0; bi_d = 0; bi_sp = 0; bi_n = 0; bi_end = 0;
        for (a = 0; a < HL; a = a + 1)
            if (h_new[a] && a + h_b[a] >= XVM - 7 && a <= XVM - 8) begin
                bi_v = 1'b1; bi_j = a + h_b[a] - (XVM - 7); bi_dc = h_dc[a]; bi_d = h_d[a]; bi_sp = h_sp[a];
                bi_end = h_dc[a] + h_span[a];
                bi_n = bi_n + 1'b1;
            end
    end
    reg [LB+1:0] xcnt;
    assign x_rdy = (xcnt == BMAX);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) xcnt <= BMAX;
        else if (me_en) xcnt <= nt ? 0 : (xcnt == BMAX) ? xcnt : xcnt + 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            h_new <= 0; p_v <= 1'b0; x_fault <= 1'b0;
        end else if (me_en) begin
            h_new <= {h_new[HL-2:0], nt};
            p_v <= x_dv; p_dc <= x_dc; p_d <= x_dcs; p_sp <= x_dsp;
            if (nt && (bq >= BMAX || !(|din) || x_dsp > SMAX || x_dsp < SMIN)) x_fault <= 1'b1;
            if (bi_n > 1) x_fault <= 1'b1;
        end
    end
    always @(posedge clk) if (me_en) begin
        for (a = HL - 1; a > 0; a = a - 1) begin
            h_dc[a] <= h_dc[a-1]; h_d[a] <= h_d[a-1]; h_sp[a] <= h_sp[a-1]; h_b[a] <= h_b[a-1]; h_span[a] <= h_span[a-1];
        end
        h_dc[0] <= x_dc; h_d[0] <= x_dcs; h_sp[0] <= x_dsp; h_b[0] <= bq[LB-1:0] + 1'b1; h_span[0] <= span_n;
    end
    wire [AW-1:0] ba = bi_dc + bi_j * BEAT;
    wire [AW-5:0] br0 = ba[AW-1:4];
    // only the banks of the rows the beat needs read (ba .. min(ba + BEAT - 1, the tuple's end)): a beat never touches
    // a row outside its tuple's span (the late-write hazard check is then exact for the x path too)
    wire [AW+12:0] bl_e = (ba + BEAT - 1 < bi_end) ? ba + BEAT - 1 : bi_end;
    wire [AW+8:0]  bnr = bl_e[AW+12:4] - br0 + 1'b1;      // rows the beat reads (<= NRB)
    reg  [NRB-1:0] b_re;
    reg  [NRB*LAW-1:0] b_ra;
    assign r_rdy = !(me_en && bi_v);
    generate for (g = 0; g < NRB; g = g + 1) begin : g_s0
        wire [AW-5:0] rowb = br0 + ((g - br0) & (NRB - 1));
        always @(posedge clk) begin
            b_re[g] <= (me_en && bi_v && (((g - br0) & (NRB - 1)) < bnr)) || (r_v && r_rdy && (r_row[LNRB-1:0] == g));
            b_ra[g*LAW +: LAW] <= (me_en && bi_v) ? rowb[LNRB +: LAW] : r_row[LNRB +: LAW];
        end
    end endgenerate
    reg  s1_bv, s2_bv, s3_bv, s4_bv, s5_bv, s6_bv;
    reg  [1:0] bpp, s1_pp, s2_pp, s3_pp;
    reg  [LB-1:0] s1_j, s2_j, s3_j, s4_j, s5_j, s6_j;
    reg  [AW-1:0] s1_a, s2_a, s3_a, s4_a, s5_a;
    reg  [ND-1:0] s1_d, s2_d, s3_d, s4_d, s5_d, s6_d;
    reg  [3:0]    s1_sp, s2_sp, s3_sp, s4_sp, s5_sp, s6_sp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_bv <= 0; s2_bv <= 0; s3_bv <= 0; s4_bv <= 0; s5_bv <= 0; s6_bv <= 0; bpp <= 2'd0; end
        else if (me_en) begin
            s1_bv <= bi_v; s2_bv <= s1_bv; s3_bv <= s2_bv; s4_bv <= s3_bv; s5_bv <= s4_bv; s6_bv <= s5_bv;
            if (bi_v) bpp <= (bpp == 2'd2) ? 2'd0 : bpp + 2'd1;
        end
    end
    reg [ND-1:0] bdin;
    always @(*) for (di = 0; di < ND; di = di + 1) bdin[di] = (bi_d == DSET[di*8 +: 8]);
    always @(posedge clk) if (me_en) begin
        s1_j <= bi_j; s1_a <= ba; s1_d <= bdin; s1_sp <= bi_sp; s1_pp <= bpp; s2_pp <= s1_pp; s3_pp <= s2_pp;
        s6_j <= s5_j; s6_d <= s5_d; s6_sp <= s5_sp;
        s2_j <= s1_j; s2_a <= s1_a; s2_d <= s1_d; s2_sp <= s1_sp;
        s3_j <= s2_j; s3_a <= s2_a; s3_d <= s2_d; s3_sp <= s2_sp;
        s4_j <= s3_j; s4_a <= s3_a; s4_d <= s3_d; s4_sp <= s3_sp;
        s5_j <= s4_j; s5_a <= s4_a; s5_d <= s4_d; s5_sp <= s4_sp;
    end

    // =================================================================================================================
    // write side: SU lane rows (formation), skid queues, the result merge, the per-bank write registers
    // =================================================================================================================
    // ---- E1: input registers ----
    reg  [SW-1:0]    e1_m;
    reg  [AW-1:0]    e1_a0, e1_a1;
    reg  [SW*32-1:0] e1_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) e1_m <= 0; else e1_m <= sw_mask;
    always @(posedge clk) begin e1_a0 <= sw_a0; e1_a1 <= sw_a1; e1_d <= sw_data; end
    // skid sources: input registers (mx sampled on engine edges: the tree top's mx is an engine-clock register)
    reg  [NK-1:0]  k1_v;
    reg  [RW-1:0]  k1_row [0:NK-1];
    reg  [15:0]    k1_mask [0:NK-1];
    reg  [511:0]   k1_data [0:NK-1];
    always @(posedge clk or negedge rst_n) if (!rst_n) k1_v <= 0; else k1_v <= {w_v, rd_v, me_en && mx_we};
    always @(posedge clk) begin
        if (me_en) begin k1_row[0] <= mx_addr[RW-1:0]; k1_mask[0] <= mx_mask; k1_data[0] <= mx_data; end
        k1_row[1] <= rd_addr[AW-1:4]; k1_mask[1] <= 16'd1 << rd_addr[3:0]; k1_data[1] <= {16{rd_data}};
        k1_row[2] <= w_row; k1_mask[2] <= w_mask; k1_data[2] <= w_data;
    end
    // ---- E2: SU rows formed (window of NWR rows from row r0), ELEMS-bounded ----
    wire [AW-1:0] e1_si = e1_a1 - e1_a0;
    reg  [LSW-1:0] hi_l;
    always @(*) begin hi_l = 0; for (i = 0; i < SW; i = i + 1) if (e1_m[i]) hi_l = i; end
    reg            f_v;
    reg  [RW-1:0]  f_r0;
    reg  [NWE-1:0] f_m;
    reg  [NWE*32-1:0] f_d;
    reg            f_bad;
    wire [3:0]     e1_off = e1_a0[3:0];
    wire           e1_s0 = !e1_m[1] || (e1_si == 0);
    generate for (g = 0; g < NWE; g = g + 1) begin : g_form
        reg        mm;
        reg [31:0] md;
        integer ll;
        always @(*) begin
            mm = 1'b0; md = 32'd0; ll = g - e1_off;
            if (e1_s0) begin
                if (g == e1_off) begin mm = |e1_m; md = e1_d[hi_l*32 +: 32]; end
            end else begin
                if (ll >= 0 && ll < SW) begin mm = e1_m[ll]; md = e1_d[ll*32 +: 32]; end
            end
            if ({e1_a0[AW-1:4], 4'h0} + g >= ELEMS) mm = 1'b0;
        end
        always @(posedge clk) begin f_m[g] <= mm; f_d[g*32 +: 32] <= md; end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin f_v <= 1'b0; f_bad <= 1'b0; end
        else begin f_v <= |e1_m; f_bad <= (|e1_m) && e1_m[1] && e1_si > 1; end
    end
    always @(posedge clk) f_r0 <= e1_a0[AW-1:4];
    // ---- skid queues (pushed at E2), ELEMS-bounded masks ----
    reg  [RW-1:0]  q_row  [0:NK*SQD-1];
    reg  [15:0]    q_mask [0:NK*SQD-1];
    reg  [511:0]   q_data [0:NK*SQD-1];
    reg  [SQD-1:0] q_v    [0:NK-1];
    reg  [SQD-1:0] q_late [0:NK-1];
    reg  [15:0]    k1_mb  [0:NK-1];
    always @(*) for (k = 0; k < NK; k = k + 1)
        for (i = 0; i < 16; i = i + 1) k1_mb[k][i] = k1_mask[k][i] && ({k1_row[k], 4'h0} + i < ELEMS);
    // heads (entry 0 of each queue)
    wire [NK-1:0] hq_v;
    generate for (g = 0; g < NK; g = g + 1) begin : g_hq
        assign hq_v[g] = q_v[g][0];
    end endgenerate
    // ---- merge ----
    wire           m_v, m_nowr, m_land;
    wire [RW-1:0]  m_row;
    wire [15:0]    m_mask;
    wire [511:0]   m_data;
    wire           m_take;
    wire           m_busy, m_fault;
    reg  [15:0]    m_mb;
    always @(*) for (i = 0; i < 16; i = i + 1) m_mb[i] = m_mask[i] && ({m_row, 4'h0} + i < ELEMS);
    ot_qfd_res_merge #(.NB(NB), .W(16), .RW(RW), .CRB(CRB)) u_merge (.clk(clk), .rst_n(rst_n),
        .b_v(rb_v), .b_end(rb_end), .b_nul(rb_nul), .b_row(rb_row), .b_mask(rb_mask), .b_data(rb_data), .b_cr(rb_cr),
        .m_v(m_v), .m_nowr(m_nowr), .m_land(m_land), .m_row(m_row), .m_mask(m_mask), .m_data(m_data),
        .m_take(m_take), .land_cnt(land_cnt), .busy(m_busy), .fault(m_fault));
    // ---- E2 -> E3: per-bank arbitration ----
    reg  [NRB-1:0] su_hit;
    reg  [NRB*3-1:0] su_k;
    always @(*) begin
        for (b = 0; b < NRB; b = b + 1) begin : su_b
            reg [LNRB-1:0] kk;
            kk = b[LNRB-1:0] - f_r0[LNRB-1:0];
            su_k[b*3 +: 3] = kk[2:0];
            su_hit[b] = f_v && (kk < NWR) && (|f_m[kk*16 +: 16]);
        end
    end
    // grants in the SU copies' bank space (NRBS | NRB: a set of rows distinct mod NRBS is distinct mod NRB)
    reg  [NRBS-1:0] su_hs;
    always @(*) begin
        for (b = 0; b < NRBS; b = b + 1) begin : su_bs
            reg [LNRBS-1:0] kk;
            kk = b[LNRBS-1:0] - f_r0[LNRBS-1:0];
            su_hs[b] = f_v && (kk < NWR) && (|f_m[kk*16 +: 16]);
        end
    end
    reg  [NK-1:0]  gk;                                  // skid head grants
    reg  [NRBS-1:0] used;
    reg            gm;
    always @(*) begin
        used = su_hs; gk = 0;
        for (k = 0; k < NK; k = k + 1)
            if (hq_v[k] && !used[q_row[k*SQD][LNRBS-1:0]]) begin
                gk[k] = 1'b1; used[q_row[k*SQD][LNRBS-1:0]] = 1'b1;
            end
        gm = m_v && !m_nowr && !used[m_row[LNRBS-1:0]];
    end
    assign m_take = m_v && (m_nowr || gm);
    // per-bank write registers (beside the bank; written into every copy's macro the next edge)
    reg  [NRB-1:0]      bw_we;
    reg  [NRB*LAW-1:0]  bw_line;
    reg  [NRB*16-1:0]   bw_mask;
    reg  [NRB*512-1:0]  bw_data;
    reg  [NRB*3-1:0]    bw_src;
    generate for (g = 0; g < NRB; g = g + 1) begin : g_bw
        wire [2:0] kk = su_k[g*3 +: 3];
        wire [RW-1:0] srow = f_r0 + kk;
        reg  [2:0] src;          // 0 none, 1 su, 2 mx, 3 rd, 4 seq, 5 merge
        always @(*) begin
            src = 3'd0;
            if (su_hit[g]) src = 3'd1;
            else if (gk[0] && q_row[0*SQD][LNRB-1:0] == g) src = 3'd2;
            else if (gk[1] && q_row[1*SQD][LNRB-1:0] == g) src = 3'd3;
            else if (gk[2] && q_row[2*SQD][LNRB-1:0] == g) src = 3'd4;
            else if (gm && m_row[LNRB-1:0] == g) src = 3'd5;
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) bw_we[g] <= 1'b0; else bw_we[g] <= (src != 0);
        always @(posedge clk) begin
            bw_src[g*3 +: 3] <= src;
            case (src)
                3'd1: begin bw_line[g*LAW +: LAW] <= srow[LNRB +: LAW]; bw_mask[g*16 +: 16] <= f_m[kk*16 +: 16];
                            bw_data[g*512 +: 512] <= f_d[kk*512 +: 512]; end
                3'd2: begin bw_line[g*LAW +: LAW] <= q_row[0*SQD][LNRB +: LAW]; bw_mask[g*16 +: 16] <= q_mask[0*SQD];
                            bw_data[g*512 +: 512] <= q_data[0*SQD]; end
                3'd3: begin bw_line[g*LAW +: LAW] <= q_row[1*SQD][LNRB +: LAW]; bw_mask[g*16 +: 16] <= q_mask[1*SQD];
                            bw_data[g*512 +: 512] <= q_data[1*SQD]; end
                3'd4: begin bw_line[g*LAW +: LAW] <= q_row[2*SQD][LNRB +: LAW]; bw_mask[g*16 +: 16] <= q_mask[2*SQD];
                            bw_data[g*512 +: 512] <= q_data[2*SQD]; end
                default: begin bw_line[g*LAW +: LAW] <= m_row[LNRB +: LAW]; bw_mask[g*16 +: 16] <= m_mb;
                            bw_data[g*512 +: 512] <= m_data; end
            endcase
        end
    end endgenerate
    // per-bank write registers of the SU replica copies (NRBS banks, beside them)
    reg  [NRBS-1:0]      ws_we;
    reg  [NRBS*LAWS-1:0] ws_line;
    reg  [NRBS*16-1:0]   ws_mask;
    reg  [NRBS*512-1:0]  ws_data;
    generate for (g = 0; g < NRBS; g = g + 1) begin : g_ws
        wire [LNRBS-1:0] kk = g[LNRBS-1:0] - f_r0[LNRBS-1:0];
        wire [RW-1:0] srow = f_r0 + kk;
        reg  [2:0] src;
        always @(*) begin
            src = 3'd0;
            if (su_hs[g]) src = 3'd1;
            else if (gk[0] && q_row[0*SQD][LNRBS-1:0] == g) src = 3'd2;
            else if (gk[1] && q_row[1*SQD][LNRBS-1:0] == g) src = 3'd3;
            else if (gk[2] && q_row[2*SQD][LNRBS-1:0] == g) src = 3'd4;
            else if (gm && m_row[LNRBS-1:0] == g) src = 3'd5;
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) ws_we[g] <= 1'b0; else ws_we[g] <= (src != 0);
        always @(posedge clk) begin
            case (src)
                3'd1: begin ws_line[g*LAWS +: LAWS] <= srow[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= f_m[kk*16 +: 16];
                            ws_data[g*512 +: 512] <= f_d[kk*512 +: 512]; end
                3'd2: begin ws_line[g*LAWS +: LAWS] <= q_row[0*SQD][LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= q_mask[0*SQD];
                            ws_data[g*512 +: 512] <= q_data[0*SQD]; end
                3'd3: begin ws_line[g*LAWS +: LAWS] <= q_row[1*SQD][LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= q_mask[1*SQD];
                            ws_data[g*512 +: 512] <= q_data[1*SQD]; end
                3'd4: begin ws_line[g*LAWS +: LAWS] <= q_row[2*SQD][LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= q_mask[2*SQD];
                            ws_data[g*512 +: 512] <= q_data[2*SQD]; end
                default: begin ws_line[g*LAWS +: LAWS] <= m_row[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= m_mb;
                            ws_data[g*512 +: 512] <= m_data; end
            endcase
        end
    end endgenerate
    // skid queue state: pop granted heads, push the E1 registers, mark survivors late; late grants for one cycle
    reg  [NK-1:0] lg_v;
    reg  [RW-1:0] lg_row [0:NK-1];
    reg           q_ovf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < NK; k = k + 1) begin q_v[k] <= 0; q_late[k] <= 0; end
            lg_v <= 0; q_ovf <= 1'b0;
        end else begin
            q_ovf <= 1'b0;
            for (k = 0; k < NK; k = k + 1) begin : qk
                reg [SQD-1:0] v, lt;
                reg           pushed;
                v = q_v[k]; lt = q_late[k];
                lg_v[k] <= gk[k] && lt[0];
                if (gk[k]) begin v = v >> 1; lt = lt >> 1; end
                lt = lt | v;                               // survivors of this edge are late
                pushed = 1'b0;
                for (i = 0; i < SQD; i = i + 1)
                    if (k1_v[k] && !pushed && !v[i]) begin v[i] = 1'b1; lt[i] = 1'b0; pushed = 1'b1; end
                if (k1_v[k] && !pushed) q_ovf <= 1'b1;
                q_v[k] <= v; q_late[k] <= lt;
            end
        end
    end
    always @(posedge clk) begin
        for (k = 0; k < NK; k = k + 1) begin : qd
            reg [SQD-1:0] v;
            integer sl, tgt;
            reg pushed;
            v = q_v[k];
            lg_row[k] <= q_row[k*SQD];
            if (gk[k]) begin
                for (sl = 0; sl < SQD - 1; sl = sl + 1) begin
                    q_row[k*SQD + sl] <= q_row[k*SQD + sl + 1]; q_mask[k*SQD + sl] <= q_mask[k*SQD + sl + 1];
                    q_data[k*SQD + sl] <= q_data[k*SQD + sl + 1];
                end
                v = v >> 1;
            end
            pushed = 1'b0; tgt = 0;
            for (sl = 0; sl < SQD; sl = sl + 1) if (!pushed && !v[sl]) begin tgt = sl; pushed = 1'b1; end
            if (k1_v[k] && pushed) begin
                q_row[k*SQD + tgt] <= k1_row[k]; q_mask[k*SQD + tgt] <= k1_mb[k]; q_data[k*SQD + tgt] <= k1_data[k];
            end
        end
    end
    // late rows (queue entries with late set + late grants now in the bank write registers)
    reg  [NL-1:0]  lt_v;
    reg  [NL*RW-1:0] lt_row;
    always @(*) begin
        for (k = 0; k < NK; k = k + 1) begin
            for (i = 0; i < SQD; i = i + 1) begin
                lt_v[k*(SQD+1) + i] = q_v[k][i] && q_late[k][i];
                lt_row[(k*(SQD+1) + i)*RW +: RW] = q_row[k*SQD + i];
            end
            lt_v[k*(SQD+1) + SQD] = lg_v[k];
            lt_row[(k*(SQD+1) + SQD)*RW +: RW] = lg_row[k];
        end
    end

    // =================================================================================================================
    // banks: copy 0 (x path + row read), copies 1..NSU (SU operand reads); one shared write register per bank
    // =================================================================================================================
    wire [NRB*512-1:0] bq_w;
    reg  [NRB*512-1:0] cap0, cap1, cap2;
    reg  m1, m2;
    reg  [1:0] m1_pp, m2_pp;
    generate for (g = 0; g < NRB; g = g + 1) begin : g_bank
        ot_qfd_vm_rowbank #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_b (.clk(clk),
            .re(b_re[g]), .raddr(b_ra[g*LAW +: LAW]), .q(bq_w[g*512 +: 512]),
            .we(bw_we[g]), .waddr(bw_line[g*LAW +: LAW]), .wmask(bw_mask[g*16 +: 16]), .wdata(bw_data[g*512 +: 512]));
    end endgenerate
    reg [RL-1:0] rr_v;
    reg [LNRB-1:0] rr_b0, rr_b1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rr_v <= 0;
        else rr_v <= {rr_v[RL-2:0], r_v && r_rdy};
    end
    always @(posedge clk) begin rr_b0 <= r_row[LNRB-1:0]; rr_b1 <= rr_b0; end
    reg [511:0] r_qr;
    always @(posedge clk) begin
        m1 <= me_en && bi_v; m1_pp <= bpp; m2 <= m1; m2_pp <= m1_pp;
        if (m2 && m2_pp == 2'd0) cap0 <= bq_w;
        if (m2 && m2_pp == 2'd1) cap1 <= bq_w;
        if (m2 && m2_pp == 2'd2) cap2 <= bq_w;
        if (rr_v[1]) r_qr <= bq_w[rr_b1*512 +: 512];
    end
    assign r_qv = rr_v[2];
    assign r_q = r_qr;
    reg [NRB*512-1:0] rot1, rot2;
    wire [LNRB-1:0] rot = s3_a[4 +: LNRB];
    wire [NRB*512-1:0] capx = (s3_pp == 2'd0) ? cap0 : (s3_pp == 2'd1) ? cap1 : cap2;
    always @(posedge clk) if (me_en) begin
        for (i = 0; i < NRB; i = i + 1)
            rot1[i*512 +: 512] <= capx[((i + (rot & ~((NRB >= 8) ? 7 : 0))) % NRB)*512 +: 512];
    end
    wire [LNRB-1:0] rotf = s4_a[4 +: LNRB] & ((NRB >= 8) ? 7 : {LNRB{1'b1}});
    always @(posedge clk) if (me_en) begin
        for (i = 0; i < NRB; i = i + 1) rot2[i*512 +: 512] <= rot1[((i + ((NRB >= 8) ? rotf : 0)) % NRB)*512 +: 512];
    end
    reg [BEAT*32-1:0] bv;
    wire [3:0] sh = s5_a[3:0] + ((MUT == 2) ? 4'd1 : 4'd0);
    always @(posedge clk) if (me_en) begin
        for (i = 0; i < BEAT; i = i + 1)
            bv[i*32 +: 32] <= ((s5_a + i) < ELEMS) ? rot2[(i + sh)*32 +: 32] : 32'd0;
    end
    reg [NX*32-1:0] line;
    generate for (c = 0; c < NX; c = c + 1) begin : g_ent
        wire [ND-1:0] hit;
        wire [ND*32-1:0] src;
        for (dd = 0; dd < ND; dd = dd + 1) begin : g_d
            localparam integer DV = DSET[dd*8 +: 8];
            localparam integer JJ = (c * DV) / BEAT;
            localparam integer MM = (c * DV) % BEAT;
            if (JJ < BMAX) begin : g_ok
                assign hit[dd] = s6_d[dd] && (s6_j == JJ);
                assign src[dd*32 +: 32] = bv[MM*32 +: 32];
            end else begin : g_no
                assign hit[dd] = 1'b0;
                assign src[dd*32 +: 32] = 32'd0;
            end
        end
        reg [31:0] pick;
        integer kk;
        always @(*) begin
            pick = 32'd0;
            for (kk = 0; kk < ND; kk = kk + 1) if (hit[kk]) pick = src[kk*32 +: 32];
        end
        always @(posedge clk) if (me_en && s6_bv && (|hit) && c < (1 << s6_sp)) line[c*32 +: 32] <= pick;
    end endgenerate
    wire       co_v = h_new[XVM-1];
    wire [3:0] co_sp = h_sp[XVM-1];
    always @(posedge clk) if (me_en && co_v) begin
        for (i = 0; i < NX; i = i + 1) x_q[i*32 +: 32] <= line[(i & ((1 << co_sp) - 1))*32 +: 32];
    end

    // ---- SU operand copies ----
    wire [NSU-1:0] su_hz;
    generate for (gc = 0; gc < NSU; gc = gc + 1) begin : g_cp
        // E1: descriptor registers; E2: broadcast registers (window rows, offset, stride)
        reg           d1_v, d1_r1;
        reg  [AW-1:0] d1_a0, d1_a1;
        reg           d2_v, d2_si;
        reg  [AW-1:0] d2_a0;
        reg  [3:0]    d2_nr;
        reg           d2_bad;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin d1_v <= 1'b0; d2_v <= 1'b0; d2_bad <= 1'b0; end
            else begin
                d1_v <= s_re0[gc]; d2_v <= d1_v;
                d2_bad <= d1_v && d1_r1 && (d1_a1 - d1_a0) > 1;
            end
        end
        wire si1 = d1_r1 && (d1_a1 - d1_a0) == 1;
        always @(posedge clk) begin
            d1_r1 <= s_re1[gc]; d1_a0 <= s_a0[gc*AW +: AW]; d1_a1 <= s_a1[gc*AW +: AW];
            d2_a0 <= d1_a0; d2_si <= si1;
            d2_nr <= si1 ? ((d1_a0[3:0] + SW - 1) >> 4) + 1 : 4'd1;
        end
        // E3: per-bank read registers (beside the macros)
        reg  [NRBS-1:0]      sb_re;
        reg  [NRBS*LAWS-1:0] sb_ra;
        wire [RW-1:0]        d2_r0 = d2_a0[AW-1:4];
        for (g = 0; g < NRBS; g = g + 1) begin : g_ra
            wire [LNRBS-1:0] kk = g[LNRBS-1:0] - d2_r0[LNRBS-1:0];
            wire [RW-1:0]    rr = d2_r0 + kk;
            always @(posedge clk) begin
                sb_re[g] <= d2_v && (kk < d2_nr);
                sb_ra[g*LAWS +: LAWS] <= rr[LNRBS +: LAWS];
            end
        end
        reg           d3_v, d4_v, d5_v, d6_v, d7_v;
        reg  [AW-1:0] d3_a0, d4_a0, d5_a0, d6_a0, d7_a0;
        reg           d3_si, d4_si, d5_si, d6_si, d7_si;
        always @(posedge clk) begin
            d3_v <= d2_v; d4_v <= d3_v; d5_v <= d4_v; d6_v <= d5_v; d7_v <= d6_v;
            d3_a0 <= d2_a0; d4_a0 <= d3_a0; d5_a0 <= d4_a0; d6_a0 <= d5_a0; d7_a0 <= d6_a0;
            d3_si <= d2_si; d4_si <= d3_si; d5_si <= d4_si; d6_si <= d5_si; d7_si <= d6_si;
        end
        // E4: macro read; E5: capture beside the macros
        wire [NRBS*512-1:0] sq_w;
        reg  [NRBS*512-1:0] scap;
        for (g = 0; g < NRBS; g = g + 1) begin : g_bank
            ot_qfd_vm_rowbank_s #(.DEPTH(DEPTHS), .LAW(LAWS), .USE_MACRO(USE_MACRO)) u_b (.clk(clk),
                .re(sb_re[g]), .raddr(sb_ra[g*LAWS +: LAWS]), .q(sq_w[g*512 +: 512]),
                .we(ws_we[g]), .waddr(ws_line[g*LAWS +: LAWS]), .wmask(ws_mask[g*16 +: 16]), .wdata(ws_data[g*512 +: 512]));
        end
        always @(posedge clk) if (d4_v) scap <= sq_w;
        // E6: coarse rotate (by the window's first bank, rounded down to 8), E7: fine (by its low 3 bits)
        reg  [NPS*512-1:0] pos;
        reg  [NWR*512-1:0] win;
        wire [LNRBS-1:0] r5 = d5_a0[4 +: LNRBS];
        wire [LNRBS-1:0] r6 = d6_a0[4 +: LNRBS];
        always @(posedge clk) if (d5_v)
            for (i = 0; i < NPS; i = i + 1) pos[i*512 +: 512] <= scap[((i + (r5 & ~7)) % NRBS)*512 +: 512];
        always @(posedge clk) if (d6_v)
            for (i = 0; i < NWR; i = i + 1) win[i*512 +: 512] <= pos[(i + (r6 & 7))*512 +: 512];
        // E8: lane select (stride 1: element off + l; stride 0: element off), ELEMS-bounded
        reg  [SW*32-1:0] q8;
        wire [3:0] off7 = d7_a0[3:0] + ((MUT == 1) ? 4'd1 : 4'd0);
        always @(posedge clk) if (d7_v)
            for (i = 0; i < SW; i = i + 1)
                q8[i*32 +: 32] <= ((d7_a0 + (d7_si ? i : 0)) < ELEMS) ? win[(off7 + (d7_si ? i : 0))*32 +: 32] : 32'd0;
        assign s_q[gc*SW*32 +: SW*32] = q8;
        // hazard: this copy reads (macro edge next) a row with a late write pending
        reg hz;
        always @(*) begin
            hz = 1'b0;
            for (k = 0; k < NL; k = k + 1)
                if (lt_v[k] && sb_re[lt_row[k*RW +: LNRBS]] && sb_ra[lt_row[k*RW +: LNRBS]*LAWS +: LAWS] == lt_row[k*RW + LNRBS +: LAWS])
                    hz = 1'b1;
        end
        assign su_hz[gc] = hz || d2_bad;
    end endgenerate

    // ---- hazards / faults ----
    reg hz0;
    always @(*) begin
        hz0 = 1'b0;
        for (k = 0; k < NL; k = k + 1)
            if (lt_v[k] && b_re[lt_row[k*RW +: LNRB]] && b_ra[lt_row[k*RW +: LNRB]*LAW +: LAW] == lt_row[k*RW + LNRB +: LAW])
                hz0 = 1'b1;
    end
    // WAW: a bank write registered now onto the row of an entry still late in a queue
    reg waw;
    always @(*) begin
        waw = 1'b0;
        for (k = 0; k < NK; k = k + 1)
            for (i = 0; i < SQD; i = i + 1)
                if (q_v[k][i] && q_late[k][i] && bw_we[q_row[k*SQD + i][LNRB-1:0]] &&
                    bw_src[q_row[k*SQD + i][LNRB-1:0]*3 +: 3] != k + 2 &&
                    bw_line[q_row[k*SQD + i][LNRB-1:0]*LAW +: LAW] == q_row[k*SQD + i][LNRB +: LAW]) waw = 1'b1;
    end
    // x hazard: a landing row (registered rows of this edge's bank writes) on the span of a pending x tuple
    reg            lr_su, lr_m;
    reg  [RW-1:0]  lr_r0, lr_mr;
    reg  [NK-1:0]  lr_k;
    reg  [RW-1:0]  lr_kr [0:NK-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin lr_su <= 1'b0; lr_m <= 1'b0; lr_k <= 0; end
        else begin lr_su <= |su_hit; lr_m <= gm; lr_k <= gk; end
    end
    always @(posedge clk) begin
        lr_r0 <= f_r0; lr_mr <= m_row;
        for (k = 0; k < NK; k = k + 1) lr_kr[k] <= q_row[k*SQD];
    end
    function automatic hits(input [RW-1:0] lo, input [RW-1:0] hi, input [AW-1:0] dc, input [AW+12:0] sp);
        hits = ({lo, 4'h0} <= dc + sp) && ({hi, 4'hf} >= dc);
    endfunction
    reg hzx;
    always @(*) begin
        hzx = 1'b0;
        for (a = 0; a <= XVM; a = a + 1) if (h_new[a]) begin
            if (lr_su && hits(lr_r0, lr_r0 + NWR - 1, h_dc[a], h_span[a])) hzx = 1'b1;
            if (lr_m && hits(lr_mr, lr_mr, h_dc[a], h_span[a])) hzx = 1'b1;
            for (k = 0; k < NK; k = k + 1) if (lr_k[k] && hits(lr_kr[k], lr_kr[k], h_dc[a], h_span[a])) hzx = 1'b1;
        end
        if (nt) begin
            if (lr_su && hits(lr_r0, lr_r0 + NWR - 1, x_dc, span_n)) hzx = 1'b1;
            if (lr_m && hits(lr_mr, lr_mr, x_dc, span_n)) hzx = 1'b1;
            for (k = 0; k < NK; k = k + 1) if (lr_k[k] && hits(lr_kr[k], lr_kr[k], x_dc, span_n)) hzx = 1'b1;
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin x_hazard <= 1'b0; w_hazard <= 1'b0; w_fault <= 1'b0; me_ok <= 1'b0; end
        else begin
            if (hzx) x_hazard <= 1'b1;
            if (hz0 || (|su_hz) || waw) w_hazard <= 1'b1;
            if (q_ovf || f_bad || m_fault) w_fault <= 1'b1;
            me_ok <= &rb_ok;
        end
    end
endmodule
