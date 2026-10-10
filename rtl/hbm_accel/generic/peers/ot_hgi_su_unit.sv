`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 stream-unit die body (hgi-adapters, 2026-10-09) on the D1 memory model (spec 2.4 "How engines reach VM",
// main aeac6fa40): record -> ot_hgi_su_record (decode) -> STAGE the op's VM operands into the unit's local fixed-latency
// operand memory -> the unchanged stream unit ot_hdc_v41x_vec runs on local addresses -> DRAIN the words it wrote back to
// VM -> retire.  VM is reached only through ONE hfd_hgi_vm packet client (up to 4 requests outstanding, in-order
// responses: ot_hgi_vm_unit fast path).
//   stage: per operand the op reads (A always; B, C, D by the template; c_pair widens A by its pair word) the span
//     [lo, hi] = [base, base + (no - 1) so + (ni' - 1) si] (ni' = ceil(ni / 2) for b_half B / D) is copied sector by
//     sector into a local region placed at lb (lb = lo mod 8: sector to sector); the op word's bases are relocated
//     (base - lo + lb), strides unchanged, so the unit's address arithmetic is untouched;
//   drain: O (dst VM) and R (red) are local regions too; every word the unit writes (element writes and reducer results)
//     sets a dirty bit, and the drain writes each dirty sector back with its word mask, so words the op did not write are
//     never touched in VM (no read-modify-write of neighbours);
//   ordering: one record at a time in the unit (spec 4.1); the record retires when its last drain write is acknowledged.
//   Copies have exactly the golden's semantics (Machine.su1 reads every operand before it writes any result).
// Refusals (record fault): a gather (a_ind != 0: its span depends on the id table), a stream source / sink (STREAM is the
//   stream-port successor), an operand set larger than one local region set (LW words).
// Local memory: LW words (behavioural here; on the die the unit's r25 operand macros).  Single region set in v1; the
//   double-buffered successor stages record k+1 while record k computes when k+1 reads nothing k writes.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_ctl #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,           // log2 local words (the Qwen head: 37,984 B + O + the stream region)
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,            // 1: the SFU die body (SFU.GLU records; ot_hgi_su_record GLU mode)
    parameter integer SLB = 16,           // log2 words of the stream-0 landing region (top of the local memory)
    parameter integer MUT_DIRTY = 0,      // mutant: drain whole sectors (overwrites words the op did not write)
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB,   // local memory group sizes (log2 words; G0 = LWB)
    parameter integer LGO = LWB, RWB = 6                  // the O group, the reducer-result file
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr,
    // STREAM 0 (SM -> SU): element idx of the stream (slot x M + row) and its value; lands in the stream region
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    // STREAM to ARGMAX (the 523-b su_red stream: {bias_en, bias 256, vals 256, mask 8, last, v}); am_rdy = the argmax
    // unit holds a STREAM record (it consumes every beat once busy)
    output reg  [522:0]  am_stream,
    input  wire          am_rdy,
    // the stream unit (ot_hdc_v41x_vec): go / ready / idle / fault, the relocated op word
    output reg           go,
    input  wire          ready,
    input  wire          idle,
    input  wire          vfault,
    output reg  [669:0]  wl,
    // the local memory (ot_hgi_su_lmem; on the die the r25 operand macros): every port registered here
    output reg           sl_v,                // a STREAM 0 word lands
    output reg  [LWB-1:0] sl_addr,
    output reg  [31:0]   sl_data,
    output reg           sw_v,                // staged words (up to 8 consecutive local words)
    output reg  [255:0]  sw_data,
    output reg  [3:0]    sw_g,                // the groups the staged words land in (A + C for c_pair)
    output reg  [LWB-1:0] sw_addr,            // local word address of word 0 of the 8 (any alignment)
    output reg  [7:0]    sw_mask,             // the words written
    output reg           sr_v,                // read 8 consecutive words of a group (any alignment), one edge later
    output reg  [1:0]    sr_g,                // 1 = O, 2 = R
    output reg  [LWB-1:0] sr_addr,
    input  wire [255:0]  sr_data,
    output reg  [3:0]    use_p,               // the op's read ports in use (A, B, C or c_pair, D)
    input  wire          sl_pend,             // STREAM landing words still queued in the memory
    output wire          a_str,               // the op's A is the STREAM region
    input  wire          cfault               // memory bank conflict / overflow (sticky): fail closed
);
    localparam integer AW = 24, NR = N / 8, LW = 1 << LWB;
    // ---- the record adapter (decode) and the op it issues
    wire op_v; reg op_rdy_r; wire [669:0] op_w; reg su_idle_r, su_fault_r;
    wire [1:0] strm;
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(!GLU), .PAYLOAD_RESET(PAYLOAD_RESET)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a), .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o),
        .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted),
        .drained(), .op_strm(strm), .lg_v(1'b0), .lg_rdy(), .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy_r), .op_w(op_w),
        .su_idle(su_idle_r), .su_fault(su_fault_r));
    // ---- the op word (PFIELDS) fields
    reg [669:0] w;
    wire [15:0] no = w[0 +: 16], ni = w[16 +: 16];
    wire [1:0]  aind = w[136 +: 2], dst = w[380 +: 2], red = w[478 +: 2];
    wire        bhalf = w[210], cpair = w[283], redwhole = w[481], redtree = w[482];
    wire [2:0]  m1 = w[360 +: 3], qm = w[365 +: 3], ad = w[368 +: 3], e1 = w[374 +: 3];
    wire [1:0]  m2 = w[363 +: 2], e2 = w[377 +: 2];
    wire use_b = (m1 == 3'd1) || (m1 == 3'd4) || (m1 == 3'd6) || (ad == 3'd3) || (e2 == 2'd1);
    wire use_c = !cpair && ((m2 == 2'd1) || (qm != 3'd0) || (ad == 3'd1) || (ad == 3'd2) || (e1 == 3'd1) || (e1 == 3'd2));
    wire use_d = (qm != 3'd0) || (ad == 3'd5);
    // region k: 0 A, 1 B, 2 C, 3 D (sources), 4 O, 5 R (sinks); base / so / si offsets in the word
    reg [2:0] rk;                                         // region walk
    reg [23:0] base_k, so_k, si_k; reg [15:0] nr_k, ni_k; reg used_k; reg hf_k;
    always @* begin
        case (rk)
            3'd0: begin base_k = w[40 +: 24];  so_k = w[64 +: 24];  si_k = w[88 +: 24];  used_k = 1'b1; end
            3'd1: begin base_k = w[138 +: 24]; so_k = w[162 +: 24]; si_k = w[186 +: 24]; used_k = use_b; end
            3'd2: begin base_k = w[211 +: 24]; so_k = w[235 +: 24]; si_k = w[259 +: 24]; used_k = use_c; end
            3'd3: begin base_k = w[284 +: 24]; so_k = w[308 +: 24]; si_k = w[332 +: 24]; used_k = use_d; end
            3'd4: begin base_k = w[382 +: 24]; so_k = w[406 +: 24]; si_k = w[430 +: 24]; used_k = (dst == 2'd1); end
            default: begin base_k = w[484 +: 24]; so_k = w[508 +: 24]; si_k = 24'd0; used_k = (red != 2'd0); end
        endcase
        hf_k = bhalf && (rk == 3'd1 || rk == 3'd3);
        nr_k = (rk == 3'd5) ? ((redwhole || redtree) ? 16'd1 : no) : no;
        ni_k = (rk == 3'd5) ? 16'd1 : (hf_k ? ((ni + 16'd1) >> 1) : ni);          // words a row
    end
    // ---- DENSE RELAYOUT (hgi-1010/d, the lane-local memory): every region is copied to an N-aligned base with element
    //      (o, i) at base + o L + i (inner stride 1; broadcast operands replicated), L chosen so the vec's lanes fall on
    //      their own banks (or the few fixed partners the memory's network serves):
    //        an op the vec flattens (no per-row reduction, no gather / KV-T, even width for half / ALT ops): L = the row
    //        width (all rows contiguous: the vec runs one row, vectors at multiples of its width VW);
    //        otherwise L = the vec's slot S (packed rows, ni <= S) or roundup(ni, N) (spanning rows);
    //        S = min(VW, pow2ceil(max(ni, 8 if reducing else 1))), VW = 1 (scalar class) / M (SFU class) / N (ot_hdc_v41x_vec)
    //      the op word's base / row stride / inner stride name the local layout (inner stride 1); STREAM A / O keep the
    //      contiguous stream layout (rows of ni).  R (one word a row) is dense in the result file.
    function automatic [LWB:0] p2c(input [15:0] x);      // pow2ceil(x), x >= 1
        integer b2; p2c = 1;
        for (b2 = 0; b2 < 16; b2 = b2 + 1) if (p2c < x) p2c = p2c << 1;
    endfunction
    wire [2:0] sfu = w[371 +: 3];
    wire scalar_c = (sfu == 3'd2) || (sfu == 3'd3) || (sfu == 3'd6) || (sfu == 3'd7);
    wire sfu_c = (sfu == 3'd1) || (sfu == 3'd4) || (sfu == 3'd5) || (m1 == 3'd4) || (m1 == 3'd5);
    wire [15:0] vw = scalar_c ? 16'd1 : sfu_c ? M : N;
    wire red_on = (red != 2'd0);
    wire flatc = (!red_on || redwhole || redtree) && (aind == 2'd0) && (dst != 2'd3) &&
                 (!ni[0] || !(bhalf || qm == 3'd3 || qm == 3'd4));
    wire [LWB:0] s_el0 = p2c((ni > (red_on ? 16'd8 : 16'd1)) ? ni : (red_on ? 16'd8 : 16'd1));
    wire [LWB:0] s_el = (s_el0 > vw) ? vw : s_el0;
    wire [LWB:0] l_el = flatc ? ni : (ni <= s_el) ? s_el : ((ni + N - 1) & ~(N - 1));
    wire [LWB:0] L_k = (rk == 3'd5) ? 1 : !hf_k ? l_el : flatc ? (ni >> 1) : ((l_el >> 1) == 0 ? 1 : (l_el >> 1));
    // ---- per region state
    reg [23:0] lo [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5]; reg [LWB:0] Lr [0:5]; reg [23:0] sor [0:5], sir [0:5];
    reg [15:0] nrr [0:5], nir [0:5]; reg [LWB:0] lsz [0:5];
    reg [39:0] macc; reg [4:0] mbit; reg [1:0] mph;        // (nr - 1) L + nw by shift-add
    // ---- VM traffic
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg [2:0] outst; reg [26:0] q_sec [0:3]; reg [1:0] q_h, q_t;  // outstanding requests, in order
    // per request: how its response lands: 0 run (the sector's words in [q_lo, q_hi] at word + q_off), 1 rep (word q_w
    // replicated over q_msk at q_la), 2 elem (word q_w at q_la)
    reg [1:0] q_md [0:3]; reg [2:0] q_w [0:3]; reg [7:0] q_msk [0:3]; reg [LWB-1:0] q_la [0:3];
    reg [23:0] q_lo [0:3], q_hi [0:3]; reg [25:0] q_off [0:3];
    // staging cursor: row, VM row base, local row base, element (word) index, the run mode's sector walk
    reg [15:0] s_rows, s_j; reg [23:0] s_rb, s_va; reg [LWB:0] s_lr; reg [26:0] cur_sec, end_sec; reg [1:0] s_md;
    reg [3:0] st;
    localparam [3:0] S_IDLE = 0, S_SPAN = 1, S_MUL = 2, S_NEXTR = 3, S_STAGE = 4, S_STW = 5, S_RUN = 6, S_RUNW = 7,
                     S_DRAIN = 8, S_DRW = 9, S_DONE = 10, S_FAULT = 11, S_SOUT = 12;
    reg [2:0] dk;                                         // drain region (4 O, 5 R)
    reg [26:0] rsec_d, rsec_d2, rsec_d3; reg so_w;
    reg [3:0] rp;                                         // read pipe
    reg [255:0] sr_data_q;
    always @(posedge clk) sr_data_q <= sr_data;
    reg cfault_q; always @(posedge clk) cfault_q <= cfault;
    // ---- allocation: G0 A, G1 B, G2 C (+ A's copy for c_pair), G3 D, G4 O, G5 R (the result file)
    reg [LWB:0] galloc [0:5];
    // ---- drain walker: the O / R shape; local and VM cursors
    reg [15:0] d_row, d_rem, d_ni; reg [23:0] d_cur, d_rowb, d_so, d_si; reg d_run, d_live;
    reg [LWB:0] d_lcur, d_lrow, d_L;
    reg [7:0] mk_d, mk_d2, mk_d3;
    // ---- STREAM 0 landing (the GS region, addresses SBASE..) and the op's stream flags
    localparam integer SW = 1 << SLB;
    localparam [LWB:0] SBASE = LW - SW;
    function automatic [LWB:0] gsz(input [2:0] g);
        case (g) 3'd0: gsz = SBASE; 3'd1: gsz = 1 << LG1; 3'd2: gsz = 1 << LG2; 3'd3: gsz = 1 << LG3; 3'd4: gsz = 1 << LGO;
                 default: gsz = 1 << RWB; endcase
    endfunction
    reg [20:0] scount; reg a_s, o_s; reg s_clr;
    assign a_str = a_s;
    reg s0v_q; reg [19:0] s0i_q; reg [31:0] s0d_q;
    always @(posedge clk) begin s0v_q <= s0_v; s0i_q <= s0_idx; s0d_q <= s0_data; end
    reg [20:0] etot; reg [20:0] ebeat; reg [LWB:0] o_lb; reg amr_q;
    always @(posedge clk) amr_q <= am_rdy;
    reg ready_q, idle_q, vfault_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; end
        else begin ready_q <= ready; idle_q <= idle; vfault_q <= vfault; end
    end
    reg vf_seen; reg [1:0] idle_ph;
    wire [2:0] gk = (rk == 3'd4) ? 3'd4 : (rk == 3'd5) ? 3'd5 : rk;
    wire [LWB:0] lbk = (galloc[gk] + N - 1) & ~(N - 1);
    wire [LWB:0] gend = lbk + lsz[rk];
    integer k2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; op_rdy_r <= 1'b1; su_idle_r <= 1'b1; su_fault_r <= 1'b0; go <= 1'b0; vmq <= 338'd0;
            sl_v <= 1'b0; sw_v <= 1'b0; sr_v <= 1'b0; rp <= 4'd0; use_p <= 4'd0;
            outst <= 3'd0; q_h <= 2'd0; q_t <= 2'd0; vf_seen <= 1'b0; scount <= 21'd0; s_clr <= 1'b0; am_stream <= 523'd0;
        end else begin
            vmq[337] <= 1'b0; su_fault_r <= 1'b0; am_stream[0] <= 1'b0; am_stream[1] <= 1'b0;
            sl_v <= s0v_q && s0i_q < SW; sl_addr <= SBASE + s0i_q; sl_data <= s0d_q;
            sw_v <= 1'b0; sr_v <= 1'b0;
            if (s0v_q && s0i_q >= SW) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (cfault_q && st != S_FAULT) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (s_clr) scount <= {20'd0, s0v_q}; else if (s0v_q) scount <= scount + 21'd1;
            if (vfault_q && st == S_RUNW) vf_seen <= 1'b1;
            case (st)
                S_IDLE: begin
                    s_clr <= 1'b0;
                    if (op_v && op_rdy_r) begin
                        w <= op_w; wl <= op_w; op_rdy_r <= 1'b0; su_idle_r <= 1'b0; rk <= 3'd0; vf_seen <= 1'b0;
                        for (k2 = 0; k2 < 6; k2 = k2 + 1) galloc[k2] <= 0;
                        a_s <= strm[0]; o_s <= strm[1]; st <= S_SPAN;
                    end
                end
                S_SPAN: begin                                       // region rk: used? its layout
                    rv[rk] <= used_k && !(rk == 3'd0 && a_s);
                    lo[rk] <= base_k; sor[rk] <= so_k; sir[rk] <= si_k; nrr[rk] <= nr_k; nir[rk] <= ni_k;
                    Lr[rk] <= L_k;
                    if (rk == 3'd0 && a_s) begin                    // A = STREAM: rows of ni, element o ni + i = idx
                        wl[40 +: 24] <= SBASE; wl[64 +: 24] <= {8'd0, ni}; wl[88 +: 24] <= 24'd1; st <= S_NEXTR;
                    end else if (rk == 3'd4 && o_s) begin           // O = STREAM: contiguous rows of ni in G4, no drain
                        Lr[4] <= ni; nrr[4] <= no; nir[4] <= ni; rv[4] <= 1'b1;
                        macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL;
                    end
                    else if (!used_k) st <= S_NEXTR;
                    else begin macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL; end
                    if (rk == 3'd0 && (aind != 2'd0 || w[32 +: 8] != 8'd0)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                end
                S_MUL: begin                                        // lsz = (nr - 1) L + nw, a bit an edge
                    if (mph == 2'd0) begin
                        if ((nrr[rk] - 16'd1) >> mbit & 16'd1) macc <= macc + ({{(39-LWB){1'b0}}, Lr[rk]} << mbit);
                        if (mbit == 5'd15) mph <= 2'd1; else mbit <= mbit + 5'd1;
                    end else begin
                        lsz[rk] <= macc[LWB:0] + nir[rk]; st <= S_NEXTR;
                    end
                end
                S_NEXTR: begin                                      // place region rk (N-aligned), rewrite its fields
                    if (rv[rk]) begin
                        lb[rk] <= lbk;
                        galloc[gk] <= gend;
                        if (rk == 3'd0 && cpair) galloc[2] <= gend;           // A's copy in G2 (C reads A[e ^ 1])
                        if (gend > gsz(gk) || (rk == 3'd0 && cpair && gend > gsz(3'd2))) begin
                            su_fault_r <= 1'b1; st <= S_FAULT; end
                        case (rk)
                            3'd0: begin wl[40 +: 24]  <= lbk; wl[64 +: 24]  <= Lr[0]; wl[88 +: 24]  <= 24'd1; end
                            3'd1: begin wl[138 +: 24] <= lbk; wl[162 +: 24] <= Lr[1]; wl[186 +: 24] <= 24'd1; end
                            3'd2: begin wl[211 +: 24] <= lbk; wl[235 +: 24] <= Lr[2]; wl[259 +: 24] <= 24'd1; end
                            3'd3: begin wl[284 +: 24] <= lbk; wl[308 +: 24] <= Lr[3]; wl[332 +: 24] <= 24'd1; end
                            3'd4: begin wl[382 +: 24] <= lbk; wl[406 +: 24] <= Lr[4]; wl[430 +: 24] <= 24'd1; end
                            default: begin wl[484 +: 24] <= lbk; wl[508 +: 24] <= 24'd1; end
                        endcase
                    end
                    if (st != S_FAULT) begin
                        if (rk == 3'd5) begin rk <= 3'd0; st <= S_STAGE; end
                        else begin rk <= rk + 3'd1; st <= S_SPAN; end
                    end
                end
                S_STAGE: begin                                      // sources: gather the rows into the dense layout
                    if (rk == 3'd4) st <= S_RUN;
                    else if (!rv[rk]) rk <= rk + 3'd1;
                    else begin
                        st <= S_STW; q_h <= 0; q_t <= 0; outst <= 0;
                        sw_g <= (rk == 3'd0 && cpair) ? 4'b0101 : (4'b0001 << rk);
                        s_rows <= nrr[rk]; s_rb <= lo[rk]; s_lr <= lb[rk]; s_j <= 16'd0; s_va <= lo[rk];
                        s_md <= (sir[rk] == 24'd1) ? 2'd0 : (sir[rk] == 24'd0) ? 2'd1 : 2'd2;
                        cur_sec <= lo[rk] >> 3; end_sec <= (lo[rk] + nir[rk] - 24'd1) >> 3;
                    end
                end
                S_STW: begin
                    // issue (up to 4 outstanding, in order): run = the row's sectors; rep = one read per 8 copies;
                    // elem = one read per element
                    begin : iss
                        reg go_; reg [26:0] sc_; reg last_;
                        go_ = outst < 3'd4 && s_rows != 16'd0 && !(vr[273] && outst == 3'd4);
                        sc_ = (s_md == 2'd0) ? cur_sec : {3'd0, s_va[23:3]};
                        if (go_) begin
                            vmq <= {1'b1, 1'b0, sc_, 5'd0, 256'd0, 32'd0, 16'h5355};
                            q_sec[q_t] <= sc_; q_md[q_t] <= s_md; q_w[q_t] <= s_va[2:0];
                            q_lo[q_t] <= s_rb; q_hi[q_t] <= s_rb + nir[rk] - 24'd1;
                            q_off[q_t] <= {{(25-LWB){1'b0}}, s_lr} - {2'b00, s_rb};
                            q_la[q_t] <= s_lr + s_j;
                            q_msk[q_t] <= (s_md == 2'd1) ? ((nir[rk] - s_j >= 16'd8) ? 8'hFF :
                                                            ((8'd1 << (nir[rk] - s_j)) - 8'd1)) : 8'd1;
                            q_t <= q_t + 2'd1;
                            // advance the cursor
                            case (s_md)
                                2'd0: last_ = (cur_sec == end_sec);
                                2'd1: last_ = (nir[rk] - s_j <= 16'd8);
                                default: last_ = (s_j + 16'd1 == nir[rk]);
                            endcase
                            if (last_) begin                              // the next row
                                s_rows <= s_rows - 16'd1; s_rb <= s_rb + sor[rk]; s_va <= s_rb + sor[rk];
                                s_lr <= s_lr + Lr[rk]; s_j <= 16'd0;
                                cur_sec <= (s_rb + sor[rk]) >> 3; end_sec <= (s_rb + sor[rk] + nir[rk] - 24'd1) >> 3;
                            end else begin
                                cur_sec <= cur_sec + 27'd1;
                                if (s_md == 2'd1) s_j <= s_j + 16'd8;
                                else if (s_md == 2'd2) begin s_j <= s_j + 16'd1; s_va <= s_va + sir[rk]; end
                            end
                        end
                        outst <= outst + (go_ ? 3'd1 : 3'd0) - ((vr[273] && !vr[256]) ? 3'd1 : 3'd0);
                        if (s_rows == 16'd0 && outst == ((vr[273] && !vr[256]) ? 3'd1 : 3'd0)) begin
                            rk <= rk + 3'd1; st <= S_STAGE;
                        end
                    end
                    if (vr[273] && !vr[256]) begin : land
                        reg [23:0] w0; integer q; reg [31:0] wd_;
                        w0 = {q_sec[q_h][20:0], 3'b000}; wd_ = vr[32*q_w[q_h] +: 32];
                        sw_v <= 1'b1; q_h <= q_h + 2'd1;
                        case (q_md[q_h])
                            2'd0: begin
                                sw_addr <= w0 + q_off[q_h][LWB-1:0]; sw_data <= vr[255:0];
                                for (q = 0; q < 8; q = q + 1) sw_mask[q] <= (w0 + q >= q_lo[q_h]) && (w0 + q <= q_hi[q_h]);
                            end
                            2'd1: begin sw_addr <= q_la[q_h]; sw_data <= {8{wd_}}; sw_mask <= q_msk[q_h]; end
                            default: begin sw_addr <= q_la[q_h]; sw_data <= {224'd0, wd_}; sw_mask <= 8'd1; end
                        endcase
                    end
                end
                S_RUN: if (ready_q && !sl_pend && (!a_s || scount >= {5'd0, no} * {5'd0, ni})) begin
                    go <= 1'b1; st <= S_RUNW; idle_ph <= 2'd0; use_p <= {use_d, use_c || cpair, use_b, 1'b1};
                end
                S_RUNW: begin
                    go <= 1'b0;
                    if (idle_ph != 2'd3) idle_ph <= idle_ph + 2'd1;
                    else if (idle_q) begin
                        if (vf_seen || vfault_q) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        else begin dk <= 3'd4; st <= S_DRAIN; end
                    end
                end
                S_DRAIN: begin
                    use_p <= 4'd0;
                    if (dk == 3'd6) begin
                        if (o_s) begin etot <= {5'd0, no} * {5'd0, ni}; ebeat <= 21'd0; o_lb <= lb[4]; rp <= 4'd0; so_w <= 1'b0;
                                       st <= S_SOUT; end
                        else st <= S_DONE;
                    end
                    else if (!rv[dk] || (dk == 3'd4 && o_s)) dk <= dk + 3'd1;
                    else begin
                        // the shape: O = no rows of ni at (so, si); R = nr rows of one word at r_so
                        d_cur <= lo[dk]; d_rowb <= lo[dk]; d_so <= sor[dk]; d_si <= (dk == 3'd4) ? sir[dk] : 24'd0;
                        d_row <= nrr[dk]; d_ni <= nir[dk]; d_rem <= nir[dk];
                        d_run <= (dk == 3'd4) && (sir[dk] == 24'd1);
                        d_lcur <= lb[dk]; d_lrow <= lb[dk]; d_L <= Lr[dk];
                        d_live <= (nrr[dk] != 16'd0 && nir[dk] != 16'd0);
                        st <= S_DRW; outst <= 0; rp <= 4'd0;
                    end
                end
                S_DRW: begin                                        // the shape's words back to VM, word-masked
                    begin : dw
                        reg issue; reg [3:0] cnt; reg [7:0] mk; reg [2:0] off;
                        off = d_cur[2:0];
                        cnt = d_run ? (({12'd0, 4'd8} - {13'd0, off} < d_rem) ? 4'd8 - {1'b0, off} : d_rem[3:0]) : 4'd1;
                        mk = (MUT_DIRTY && d_run) ? 8'hFF : (((8'd1 << cnt) - 8'd1) << off);
                        issue = d_live && outst + {2'd0, rp[0]} + {2'd0, rp[2]} + {2'd0, rp[3]} < 3'd4;
                        if (issue) begin
                            // 8 consecutive local words whose word 'off' is the element at d_cur
                            sr_v <= 1'b1; sr_g <= (dk == 3'd4) ? 2'd1 : 2'd2; sr_addr <= d_lcur[LWB-1:0] - off;
                            if (d_rem == {12'd0, cnt}) begin
                                if (d_row == 16'd1) d_live <= 1'b0;
                                else begin d_row <= d_row - 16'd1; d_rowb <= d_rowb + d_so; d_cur <= d_rowb + d_so;
                                           d_rem <= d_ni; d_lrow <= d_lrow + d_L; d_lcur <= d_lrow + d_L; end
                            end else begin
                                d_cur <= d_cur + (d_run ? {20'd0, cnt} : d_si); d_rem <= d_rem - {12'd0, cnt};
                                d_lcur <= d_lcur + cnt;
                            end
                        end
                        rp[0] <= issue; rp[2] <= rp[0]; rp[3] <= rp[2]; rsec_d2 <= rsec_d; rsec_d3 <= rsec_d2;
                        mk_d2 <= mk_d; mk_d3 <= mk_d2;
                        if (rp[3])
                            vmq <= {1'b1, 1'b1, rsec_d3, 5'd0, sr_data_q,
                                    {{4{mk_d3[7]}}, {4{mk_d3[6]}}, {4{mk_d3[5]}}, {4{mk_d3[4]}}, {4{mk_d3[3]}}, {4{mk_d3[2]}},
                                     {4{mk_d3[1]}}, {4{mk_d3[0]}}},
                                    16'h5357};
                        if (issue) begin rsec_d <= {3'd0, d_cur[23:3]}; mk_d <= mk; end
                        outst <= outst + (rp[3] ? 3'd1 : 3'd0) - ((vr[273] && vr[256]) ? 3'd1 : 3'd0);
                        if (!d_live && !rp[0] && !rp[2] && !rp[3] && !issue && outst == ((vr[273] && vr[256]) ? 3'd1 : 3'd0)) begin
                            dk <= dk + 3'd1; st <= S_DRAIN; end
                    end
                end
                S_SOUT: if (amr_q && !rp[1] && !rp[3] && !so_w) begin         // 8 elements a beat, in element order
                    sr_v <= 1'b1; sr_g <= 2'd1; sr_addr <= o_lb + ebeat; so_w <= 1'b1;
                end else if (so_w) begin so_w <= 1'b0; rp[1] <= 1'b1; end   // the memory registers the sector
                else if (rp[1]) begin rp[1] <= 1'b0; rp[3] <= 1'b1; end
                else if (rp[3]) begin                               // memory data captured at its controller pin
                    begin : so
                        reg [7:0] mk; integer q;
                        for (q = 0; q < 8; q = q + 1) mk[q] = (ebeat + q < etot);
                        am_stream <= {1'b0, 256'd0, sr_data_q, mk, (ebeat + 21'd8 >= etot), 1'b1};
                    end
                    rp[3] <= 1'b0;
                    if (ebeat + 21'd8 >= etot) st <= S_DONE; else ebeat <= ebeat + 21'd8;
                end
                S_DONE: begin su_idle_r <= 1'b1; op_rdy_r <= 1'b1; st <= S_IDLE; if (a_s) s_clr <= 1'b1; end
                S_FAULT: ;                                           // sticky (the adapter halts)
                default: st <= S_FAULT;
            endcase
        end
    end
endmodule

module ot_hgi_su_lbank #(
    parameter integer RB = 13,             // log2 words in the bank
    parameter integer MACRO = 1            // 1: ot_sram_1r1w_1024x256 rows (RB = 13); 0: behavioural
) (
    input  wire          clk,
    input  wire          re,
    input  wire [RB-1:0] ra,
    output wire [31:0]   rd,
    input  wire          we,
    input  wire [RB-1:0] wa,
    input  wire [31:0]   wd
);
    reg [2:0] ks;
    always @(posedge clk) if (re) ks <= ra[2:0];
    wire [255:0] wm = {224'd0, 32'hFFFF_FFFF} << {wa[2:0], 5'd0};
    generate if (MACRO && RB == 13) begin : g_m
        wire [255:0] ro;
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00), .rr_addr(18'd0),
            .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 12) begin : g_m12       // 512 rows: the 1,024-row macro, upper half unused
        wire [255:0] ro;
        ot_sram_1r1w_1024x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in({1'b0, ra[RB-1:3]}), .rd_out(ro),
            .w_ce_in(we), .w_addr_in({1'b0, wa[RB-1:3]}), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 11) begin : g_m11
        wire [255:0] ro;
        ot_sram_1r1w_256x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO && RB == 10) begin : g_m10
        wire [255:0] ro;
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(ra[RB-1:3]), .rd_out(ro),
            .w_ce_in(we), .w_addr_in(wa[RB-1:3]), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else begin : g_b
        reg [31:0] m [0:(1 << RB) - 1];
        reg [31:0] q;
        always @(posedge clk) begin if (re) q <= m[ra]; if (we) m[wa] <= wd; end
        assign rd = q;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The unit's local operand memory, LANE-LOCAL (hgi-1010/d, 2026-10-10; scales to N = 512 lanes, Tensix-style).
// Every group is N word-interleaved banks (bank b holds the words whose local address = b mod N), one bank a lane.  The
// controller lays EVERY region out dense (element (o, i) at base + o L + i, base N-aligned, L = the vec's slot / row
// span; broadcast operands replicated; see ot_hgi_su_ctl), so a lane reads its own bank or one of a few fixed partners:
//   rot_j    (l + j M) mod N       j < N / M      (SFU-class ops issue M lanes; the vector start is a multiple of M)
//   swp_j    ((l ^ 1) + j M) mod N               (c_pair: C reads A[e ^ 1])
//   half_j   ((l >> 1) + j M / 2) mod N  j < 2N/M  (BF16-pair streams B / D: lanes 2k, 2k + 1 share word k)
//   lane 0   any bank                            (scalar-class ops run on lane 0)
// so the read network is a few-way mux a lane, not an N x N crossbar.  A bank serves one row an edge: the row of the
// first requesting candidate lane mapped to it.  A qualified read (used port, vector memory source) whose bank is not a
// candidate, or whose row differs from its bank's row, raises cfault (fail closed, never a wrong value).
// Groups: G0 A, G1 B, G2 C (+ A's copy for c_pair), G3 D (staged; read by ports A..D), GO (the lanes' element writes),
// GR (the reducer results, a small register file with NR write ports), GS (the STREAM-0 landing region, read by port A
// when A is STREAM).  Staging writes / drain reads move 8 consecutive words (any alignment: 8 distinct banks).
// Read latency: one edge (the address at edge k, the data after edge k + 1), as ot_hdc_v41x_vec expects.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_lgroup2 #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24,
    parameter integer NLW = 0,             // lane write ports (GO: N)
    parameter integer MACRO = 1,
    parameter integer MUT_XBAR = 0         // bench mutant: identity lanes take the neighbouring bank's word
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [N-1:0]      rq,                    // qualified lane reads (used port, vector-memory source)
    input  wire [N-1:0]      rr,                    // raw lane read enables
    input  wire [N*AW-1:0]   ra,
    output wire [N*32-1:0]   rd,
    input  wire              sr_v,                  // 8 consecutive words (drain / STREAM-out)
    input  wire [LWB-1:0]    sr_addr,
    output wire [255:0]      sr_d,
    input  wire              sw_v,                  // up to 8 consecutive words (stage)
    input  wire [LWB-1:0]    sw_addr,
    input  wire [7:0]        sw_mask,
    input  wire [255:0]      sw_d,
    input  wire [(NLW>0?NLW:1)-1:0]    lw,          // lane writes (element writes)
    input  wire [(NLW>0?NLW:1)*AW-1:0] lwa,
    input  wire [(NLW>0?NLW:1)*32-1:0] lwd,
    input  wire              s1_v,                  // one word (STREAM landing)
    input  wire [LWB-1:0]    s1_a,
    input  wire [31:0]       s1_d,
    output reg               flt
);
    localparam integer LN = $clog2(N), RB = LWB - LN, NROT = N / M, NHALF = (2 * N) / M, HM = (M / 2 > 0) ? M / 2 : 1;
    localparam integer NCAND = 2 * NROT + NHALF;
    localparam integer NL = (NLW > 0) ? NLW : 1;
    // candidate bank c of lane l (k < NCAND)
    function automatic [LN-1:0] cbank(input integer l, input integer k);
        integer j;
        if (k < NROT) cbank = (l + k * M) % N;
        else if (k < 2 * NROT) begin j = k - NROT; cbank = ((l ^ 1) + j * M) % N; end
        else begin j = k - 2 * NROT; cbank = ((l >> 1) + j * HM) % N; end
    endfunction
    // ---- read side: per bank, the row of the first requesting candidate lane mapped to it
    reg  [N-1:0]  b_re; reg [RB-1:0] b_ra [0:N-1];
    wire [31:0]   b_rd [0:N-1];
    reg  [N-1:0]  lok;                               // the lane's bank is one of its candidates
    integer b, l, k;
    always @* begin : rsel
        integer rj_; reg [LWB-1:0] sa; reg [LN-1:0] bl;
        sa = {LWB{1'b0}}; bl = {LN{1'b0}};
        for (b = 0; b < N; b = b + 1) begin b_re[b] = 1'b0; b_ra[b] = {RB{1'b0}}; end
        for (l = 0; l < N; l = l + 1) begin
            bl = ra[l*AW +: LN]; lok[l] = (l == 0);
            for (k = 0; k < NCAND; k = k + 1) if (cbank(l, k) == bl) lok[l] = 1'b1;
        end
        if (sr_v) begin
            for (rj_ = 0; rj_ < 8; rj_ = rj_ + 1) begin
                sa = sr_addr + rj_; b_re[sa[LN-1:0]] = 1'b1; b_ra[sa[LN-1:0]] = sa[LWB-1:LN];
            end
        end else begin
            // lowest-index lane wins a bank (the bank's row); the others must agree (checked below)
            for (l = N - 1; l >= 0; l = l - 1)
                if (rr[l] && lok[l]) begin
                    bl = ra[l*AW +: LN]; b_re[bl] = 1'b1; b_ra[bl] = ra[l*AW + LN +: RB];
                end
        end
    end
    reg [LN-1:0] lb_q [0:N-1]; reg [LN-1:0] sr_lo;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) if (rr[l]) lb_q[l] <= ra[l*AW +: LN];
        if (sr_v) sr_lo <= sr_addr[LN-1:0];
    end
    // the data network: a lane takes its bank among its candidates (lane 0: any bank)
    genvar gl, gj, gk;
    for (gl = 0; gl < N; gl = gl + 1) begin : g_rd
        if (gl == 0) begin : g_any
            wire [LN-1:0] bs = lb_q[gl] + MUT_XBAR[LN-1:0];
            assign rd[0 +: 32] = b_rd[bs];
        end else begin : g_c
            reg [31:0] dv;
            always @* begin : mx
                integer kk;
                dv = 32'd0;
                for (kk = NCAND - 1; kk >= 0; kk = kk - 1)
                    if (lb_q[gl] == cbank(gl, kk)) dv = b_rd[(cbank(gl, kk) + MUT_XBAR) % N];
            end
            assign rd[32*gl +: 32] = dv;
        end
    end
    for (gj = 0; gj < 8; gj = gj + 1) begin : g_sr
        wire [LN-1:0] bj = sr_lo + gj;
        assign sr_d[32*gj +: 32] = b_rd[bj];
    end
    // ---- write side: stage (8 words) > lane writes > the single-word STREAM landing (its own group in practice)
    reg  [N-1:0] b_we; reg [RB-1:0] b_wa [0:N-1]; reg [31:0] b_wd [0:N-1];
    reg  wcoll;
    always @* begin : wsel
        integer wl_, wj_, wk_; reg [LWB-1:0] sb; reg [LN-1:0] wb_; reg ok_;
        sb = {LWB{1'b0}}; wb_ = {LN{1'b0}}; ok_ = 1'b0;
        for (b = 0; b < N; b = b + 1) begin b_we[b] = 1'b0; b_wa[b] = {RB{1'b0}}; b_wd[b] = 32'd0; end
        wcoll = 1'b0;
        if (sw_v)
            for (wj_ = 0; wj_ < 8; wj_ = wj_ + 1) if (sw_mask[wj_]) begin
                sb = sw_addr + wj_;
                b_we[sb[LN-1:0]] = 1'b1; b_wa[sb[LN-1:0]] = sb[LWB-1:LN]; b_wd[sb[LN-1:0]] = sw_d[32*wj_ +: 32];
            end
        if (NLW > 0) begin
            if (sw_v && |lw) wcoll = 1'b1;
            for (wl_ = 0; wl_ < NL; wl_ = wl_ + 1)
                if (lw[wl_]) begin
                    wb_ = lwa[wl_*AW +: LN]; ok_ = (wl_ == 0);
                    for (wk_ = 0; wk_ < NROT; wk_ = wk_ + 1) if (cbank(wl_, wk_) == wb_) ok_ = 1'b1;
                    if (!ok_) wcoll = 1'b1;
                    // two lanes on one bank must write the same row (the later lane wins, as a behavioural memory)
                    if (b_we[wb_] && b_wa[wb_] != lwa[wl_*AW + LN +: RB]) wcoll = 1'b1;
                    if (!sw_v) begin b_we[wb_] = 1'b1; b_wa[wb_] = lwa[wl_*AW + LN +: RB]; b_wd[wb_] = lwd[32*wl_ +: 32]; end
                end
        end
        if (s1_v) begin
            if (b_we[s1_a[LN-1:0]]) wcoll = 1'b1;
            b_we[s1_a[LN-1:0]] = 1'b1; b_wa[s1_a[LN-1:0]] = s1_a[LWB-1:LN]; b_wd[s1_a[LN-1:0]] = s1_d;
        end
    end
    // ---- fail-closed checks (registered)
    reg [N-1:0] rq_q, lok_q; reg [RB-1:0] lr_q [0:N-1]; reg [RB-1:0] br_q [0:N-1]; reg srv_q, wcoll_q;
    always @(posedge clk) begin
        rq_q <= sr_v ? {N{1'b0}} : rq; lok_q <= lok; srv_q <= sr_v && |rq; wcoll_q <= wcoll;
        for (l = 0; l < N; l = l + 1) lr_q[l] <= ra[l*AW + LN +: RB];
        for (b = 0; b < N; b = b + 1) br_q[b] <= b_ra[b];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) flt <= 1'b0;
        else begin
            if (srv_q || wcoll_q) flt <= 1'b1;
            for (l = 0; l < N; l = l + 1)
                if (rq_q[l] && (!lok_q[l] || lr_q[l] != br_q[lb_q[l]])) flt <= 1'b1;
`ifdef LMEM_DBG
            if (srv_q) $display("LMEM_DBG %m sr during lane reads");
            if (wcoll_q) $display("LMEM_DBG %m write collision");
            for (l = 0; l < N; l = l + 1)
                if (rq_q[l] && (!lok_q[l] || lr_q[l] != br_q[lb_q[l]]))
                    $display("LMEM_DBG %m read lane %0d bank %0d cand %0d row %0d bank-row %0d", l, lb_q[l], lok_q[l],
                             lr_q[l], br_q[lb_q[l]]);
`endif
        end
    end
    genvar gb;
    for (gb = 0; gb < N; gb = gb + 1) begin : g_bank
        ot_hgi_su_lbank #(.RB(RB), .MACRO(MACRO)) u_b (.clk(clk), .re(b_re[gb]), .ra(b_ra[gb]), .rd(b_rd[gb]),
            .we(b_we[gb]), .wa(b_wa[gb]), .wd(b_wd[gb]));
    end
endmodule

// the reducer results: a small register file, NR write ports (any address), 8-word reads
module ot_hgi_su_rfile #(parameter integer NR = 2, RWB = 6, AW = 24) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NR-1:0]     we,
    input  wire [NR*AW-1:0]  wa,
    input  wire [NR*32-1:0]  wd,
    input  wire              sr_v,
    input  wire [RWB-1:0]    sr_addr,
    output reg  [255:0]      sr_d,
    output reg               flt                    // a result outside the file
);
    reg [31:0] m [0:(1 << RWB) - 1];
    integer j, q;
    always @(posedge clk) begin
        for (j = 0; j < NR; j = j + 1) if (we[j]) m[wa[j*AW +: RWB]] <= wd[32*j +: 32];
        if (sr_v) for (q = 0; q < 8; q = q + 1) sr_d[32*q +: 32] <= m[(sr_addr + q) & ((1 << RWB) - 1)];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flt <= 1'b0;
        else for (j = 0; j < NR; j = j + 1) if (we[j] && |wa[j*AW + RWB +: AW - RWB]) flt <= 1'b1;
endmodule

module ot_hgi_su_lmem #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24, NR = N / 8, MACRO = 1,
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB, LGO = LWB,   // log2 words of B, C, D, O (G0 = LWB: A)
    parameter integer RWB = 6,                                      // log2 words of the reducer-result file
    parameter integer SLB = 16,
    parameter integer NOSTR = 0,
    parameter integer MUT_XBAR = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [3:0]        use_p,
    input  wire [N-1:0]      vi_re,
    input  wire [N*AW-1:0]   vi_addr,
    output wire [N*32-1:0]   vi_q,
    input  wire [4*N-1:0]    rd_re,
    input  wire [4*N*AW-1:0] rd_addr,
    input  wire [8*N-1:0]    rd_src,
    output wire [4*N*32-1:0] rd_q,
    input  wire [N-1:0]      vm_we,
    input  wire [N*AW-1:0]   vm_waddr,
    input  wire [N*32-1:0]   vm_wdata,
    input  wire [NR-1:0]     res_we,
    input  wire [NR*AW-1:0]  res_addr,
    input  wire [NR*32-1:0]  res_data,
    input  wire              sl_v,
    input  wire [LWB-1:0]    sl_addr,
    input  wire [31:0]       sl_data,
    output wire              sl_pend,
    input  wire              a_str,
    input  wire              sw_v,
    input  wire [3:0]        sw_g,                  // staging groups (A, B, C, D; A + C for c_pair)
    input  wire [LWB-1:0]    sw_addr,
    input  wire [7:0]        sw_mask,
    input  wire [255:0]      sw_data,
    input  wire              sr_v,
    input  wire [1:0]        sr_g,                  // drain reads: 1 = O, 2 = R
    input  wire [LWB-1:0]    sr_addr,
    output wire [255:0]      sr_data,
    output reg               cfault
);
    wire [6:0] gf; wire [255:0] o_sr, r_sr;
    reg [1:0] srg_q; always @(posedge clk) if (sr_v) srg_q <= sr_g;
    assign sr_data = (srg_q == 2'd2) ? r_sr : o_sr;
    assign vi_q = {N*32{1'b0}};
    assign sl_pend = 1'b0;
    reg vi_bad; always @(posedge clk) vi_bad <= |vi_re;
    always @(posedge clk or negedge rst_n) if (!rst_n) cfault <= 1'b0; else if (vi_bad || |gf) cfault <= 1'b1;
`ifdef LMEM_DBG
    always @(posedge clk) if (vi_bad) $display("LMEM_DBG gather read");
`endif
    reg as_q; always @(posedge clk) as_q <= a_str;
    wire [N*32-1:0] gs_rd;
    genvar g, l;
    for (g = 0; g < 4; g = g + 1) begin : g_grp
        wire [N-1:0] rr, rq; wire [N*AW-1:0] ra; wire [N*32-1:0] rd;
        for (l = 0; l < N; l = l + 1) begin : g_l
            assign rr[l] = rd_re[4*l + g] && !(g == 0 && a_str);
            assign rq[l] = rr[l] && use_p[g] && rd_src[8*l + 2*g +: 2] == 2'd0;
            assign ra[l*AW +: AW] = rd_addr[(4*l + g)*AW +: AW];
            if (g == 0) begin : g_a
                assign rd_q[(4*l)*32 +: 32] = as_q ? gs_rd[32*l +: 32] : rd[32*l +: 32];
            end else begin : g_o
                assign rd_q[(4*l + g)*32 +: 32] = rd[32*l +: 32];
            end
        end
        localparam integer GB = (g == 0) ? LWB : (g == 1) ? LG1 : (g == 2) ? LG2 : LG3;
        ot_hgi_su_lgroup2 #(.N(N), .M(M), .LWB(GB), .AW(AW), .NLW(0), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR)) u_g (
            .clk(clk), .rst_n(rst_n), .rq(rq), .rr(rr), .ra(ra), .rd(rd), .sr_v(1'b0), .sr_addr({GB{1'b0}}), .sr_d(),
            .sw_v(sw_v && sw_g[g]), .sw_addr(sw_addr[GB-1:0]), .sw_mask(sw_mask), .sw_d(sw_data), .lw(1'b0),
            .lwa({AW{1'b0}}), .lwd(32'd0), .s1_v(1'b0), .s1_a({GB{1'b0}}), .s1_d(32'd0), .flt(gf[g]));
    end
    // GO: the lanes' element writes; drain / STREAM-out reads
    ot_hgi_su_lgroup2 #(.N(N), .M(M), .LWB(LGO), .AW(AW), .NLW(N), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR)) u_go (
        .clk(clk), .rst_n(rst_n), .rq({N{1'b0}}), .rr({N{1'b0}}), .ra({N*AW{1'b0}}), .rd(), .sr_v(sr_v && sr_g == 2'd1),
        .sr_addr(sr_addr[LGO-1:0]), .sr_d(o_sr), .sw_v(1'b0), .sw_addr({LGO{1'b0}}), .sw_mask(8'd0), .sw_d(256'd0),
        .lw(vm_we), .lwa(vm_waddr), .lwd(vm_wdata), .s1_v(1'b0), .s1_a({LGO{1'b0}}), .s1_d(32'd0), .flt(gf[4]));
    // GR: the reducer results
    ot_hgi_su_rfile #(.NR(NR), .RWB(RWB), .AW(AW)) u_gr (.clk(clk), .rst_n(rst_n), .we(res_we), .wa(res_addr),
        .wd(res_data), .sr_v(sr_v && sr_g == 2'd2), .sr_addr(sr_addr[RWB-1:0]), .sr_d(r_sr), .flt(gf[5]));
    // GS: the STREAM-0 landing region (port A reads it when the op's A is STREAM)
    wire [N-1:0] gs_rr, gs_rq; wire [N*AW-1:0] gs_ra;
    for (l = 0; l < N; l = l + 1) begin : g_sa
        assign gs_rr[l] = rd_re[4*l] && a_str;
        assign gs_rq[l] = gs_rr[l] && use_p[0] && rd_src[8*l +: 2] == 2'd0;
        assign gs_ra[l*AW +: AW] = rd_addr[(4*l)*AW +: AW];
    end
    if (NOSTR) begin : g_nostr
        reg bad; always @(posedge clk) bad <= sl_v || |gs_rq;
        assign gs_rd = {N*32{1'b0}}; assign gf[6] = bad;
    end else begin : g_str
        ot_hgi_su_lgroup2 #(.N(N), .M(M), .LWB(SLB), .AW(AW), .NLW(0), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR)) u_gs (
            .clk(clk), .rst_n(rst_n), .rq(gs_rq), .rr(gs_rr), .ra(gs_ra), .rd(gs_rd), .sr_v(1'b0), .sr_addr({SLB{1'b0}}),
            .sr_d(), .sw_v(1'b0), .sw_addr({SLB{1'b0}}), .sw_mask(8'd0), .sw_d(256'd0), .lw(1'b0), .lwa({AW{1'b0}}),
            .lwd(32'd0), .s1_v(sl_v), .s1_a(sl_addr[SLB-1:0]), .s1_d(sl_data), .flt(gf[6]));
    end
`ifdef LMEM_PROF
    final $display("LMEM_GROUPS cfault %0d", cfault);
`endif
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The stream-unit die body: the controller (ot_hgi_su_ctl: record adapter + stage / drain / STREAM) + the unchanged
// stream unit ot_hdc_v41x_vec + its local memory.  Ports as before the split (2026-10-10).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_unit #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer MUT_DIRTY = 0,
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB, LGO = LWB, RWB = 6,
    parameter integer MACRO = 1           // local memory: 1 = banked ot_sram_1r1w_1024x256 macros, 0 = behavioural banks
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rec_v,
    output wire          rec_rdy,
    input  wire [127:0]  rec_hdr,
    input  wire [255:0]  rec_sut,
    input  wire [255:0]  rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i,
    input  wire [20:0]   rec_n_a,
    output wire          rec_done,
    output wire          rec_fault,
    output wire          halted,
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr,
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    output wire [522:0]  am_stream,
    input  wire          am_rdy
);
    localparam integer AW = 24, NR = N / 8;
    wire go, ready, idle, vfault, ofault, ro; wire [669:0] wl;
    wire sl_v, sw_v, sr_v, sl_pend, cfault, a_str; wire [LWB-1:0] sl_addr; wire [31:0] sl_data; wire [LWB-1:0] sw_addr, sr_addr; wire [7:0] sw_mask;
    wire [255:0] sw_data, sr_data; wire [3:0] sw_g, use_p; wire [1:0] sr_g;
    ot_hgi_su_ctl #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET), .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sw_v(sw_v),
        .sw_addr(sw_addr), .sw_mask(sw_mask), .sw_data(sw_data), .sw_g(sw_g), .sr_v(sr_v), .sr_g(sr_g), .sr_addr(sr_addr),
        .sr_data(sr_data), .use_p(use_p), .sl_pend(sl_pend), .a_str(a_str), .cfault(cfault));
    wire [N-1:0] vi_re, vm_we, kv_we; wire [N*AW-1:0] vi_addr, vm_waddr, kv_waddr; wire [N*32-1:0] vi_q;
    wire [4*N*AW-1:0] rd_addr; wire [4*N-1:0] rd_re; wire [8*N-1:0] rd_src; wire [4*N*32-1:0] rd_q;
    wire [N*32-1:0] vm_wdata, kv_wdata; wire [NR-1:0] res_we; wire [NR*AW-1:0] res_addr; wire [NR*32-1:0] res_data;
    wire [7:0] cr_seq, cr_dseq, cr_rseq; wire [15:0] cr_cnt, emitted; wire de, dr, ds; wire [7:0] es, rs, ss;
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV)) u_vec (.clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
        .i_nout(wl[0 +: 16]), .i_nin(wl[16 +: 16]), .i_asrc(wl[32 +: 2]), .i_bsrc(wl[34 +: 2]), .i_csrc(wl[36 +: 2]),
        .i_dsrc(wl[38 +: 2]), .i_abase(wl[40 +: 24]), .i_aso(wl[64 +: 24]), .i_asi(wl[88 +: 24]),
        .i_aibase(wl[112 +: 24]), .i_aind(wl[136 +: 2]), .i_bbase(wl[138 +: 24]), .i_bso(wl[162 +: 24]),
        .i_bsi(wl[186 +: 24]), .i_bhalf(wl[210]), .i_cbase(wl[211 +: 24]), .i_cso(wl[235 +: 24]),
        .i_csi(wl[259 +: 24]), .i_cpair(wl[283]), .i_dbase(wl[284 +: 24]), .i_dso(wl[308 +: 24]),
        .i_dsi(wl[332 +: 24]), .i_arnd(wl[356]), .i_arelu(wl[357]), .i_amin(wl[358]), .i_cclip(wl[359]),
        .i_m1(wl[360 +: 3]), .i_m2(wl[363 +: 2]), .i_qm(wl[365 +: 3]), .i_ad(wl[368 +: 3]), .i_sfu(wl[371 +: 3]),
        .i_e1(wl[374 +: 3]), .i_e2(wl[377 +: 2]), .i_rnd(wl[379]), .i_dst(wl[380 +: 2]), .i_obase(wl[382 +: 24]),
        .i_oso(wl[406 +: 24]), .i_osi(wl[430 +: 24]), .i_orow(wl[454 +: 24]), .i_red(wl[478 +: 2]),
        .i_redsq(wl[480]), .i_redwhole(wl[481]), .i_redtree(wl[482]), .i_redrnd(wl[483]), .i_rbase(wl[484 +: 24]),
        .i_rso(wl[508 +: 24]), .i_imm1(wl[532 +: 32]), .i_imm2(wl[564 +: 32]), .i_imm3(wl[596 +: 32]),
        .i_ch_src(wl[628 +: 2]), .i_ch_seq(wl[630 +: 8]), .i_ch_lead(wl[638 +: 16]), .i_ch_mul(wl[654 +: 16]),
        .x_seq(8'd0), .x_dseq(8'hFF), .x_cnt(16'd0), .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq),
        .cr_cnt(cr_cnt), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re),
        .rd_src(rd_src), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we),
        .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .fault(vfault), .order_fault(ofault), .emitted(emitted), .retire_o(ro), .dbg_emit(de), .dbg_eseq(es),
        .dbg_ret(dr), .dbg_rseq(rs), .dbg_res(ds), .dbg_sseq(ss));
    ot_hgi_su_lmem #(.N(N), .M(M), .LWB(LWB), .AW(AW), .MACRO(MACRO), .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO),
        .RWB(RWB), .SLB(SLB), .NOSTR(GLU)) u_mem (.clk(clk), .rst_n(rst_n), .use_p(use_p),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_re(rd_re), .rd_addr(rd_addr), .rd_src(rd_src), .rd_q(rd_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .res_we(res_we), .res_addr(res_addr),
        .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sl_pend(sl_pend), .a_str(a_str), .sw_v(sw_v),
        .sw_g(sw_g), .sw_addr(sw_addr), .sw_mask(sw_mask), .sw_data(sw_data), .sr_v(sr_v), .sr_g(sr_g), .sr_addr(sr_addr),
        .sr_data(sr_data),
        .cfault(cfault));
endmodule
`default_nettype wire
