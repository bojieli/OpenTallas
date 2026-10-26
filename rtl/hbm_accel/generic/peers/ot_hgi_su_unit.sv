`timescale 1ns/1ps
`default_nettype none
`ifndef OT_SU_C12_RSLICE
`define OT_SU_C12_RSLICE 64
`endif
`ifndef OT_SU_C12_DENR
`define OT_SU_C12_DENR 1
`endif
`ifndef OT_SU_C12_SFUT
`define OT_SU_C12_SFUT 0
`endif
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
    parameter integer LGO = LWB, RWB = 6,                 // the O group, the reducer-result file
    // FILL-9 (2026-10-10) opt-in timing structure, both default 0 (historical elaboration); -D flips them for benches.
    // RST_RELAY 1: the rst_n port drives only rtl/lib/ot_rst_relay (async assert, release 3 edges later; regions 0 record
    // adapter, 1 controller, 2 engine-status / return pins); rec_rdy is held low until region 0 has left reset.
    parameter integer RST_RELAY = `ifdef OT_SU_RST_RELAY 1 `else 0 `endif,
    // PRE_PIPE 1: the op-level layout (pow2ceil slot, row width) and no x ni are computed over 3 registered phases of
    // S_PRE instead of one edge (routed worst path: w -> 16x16 multiply / pow2ceil ripple -> compare; +2 cycles an op)
    parameter integer PRE_PIPE = `ifdef OT_SU_PRE_PIPE 1 `else 0 `endif
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
    output reg           sr_v,                // read 8 consecutive words of a group (any alignment)
    output reg  [1:0]    sr_g,                // 1 = O, 2 = R
    output reg  [LWB-1:0] sr_addr,
    input  wire [255:0]  sr_data,
    input  wire          sr_rv,               // sr_data valid (the memory's response; reads return in order)
    output reg  [3:0]    use_p,               // the op's read ports in use (A, B, C or c_pair, D)
    input  wire          sl_pend,             // STREAM landing words still queued in the memory
    output wire          a_str,               // the op's A is the STREAM region
    input  wire          cfault               // memory bank conflict / overflow (sticky): fail closed
);
    localparam integer AW = 24, NR = N / 8, LW = 1 << LWB;
    // ---- the record adapter (decode) and the op it issues
    wire op_v; reg op_rdy_r; wire [669:0] op_w; reg su_idle_r, su_fault_r;
    wire [1:0] strm;
    // ---- reset (RST_RELAY): region 0 the record adapter, 1 the controller, 2 the engine-status / return pin flops
    wire [2:0] rr; wire rec_rdy_rec;
    generate if (RST_RELAY) begin : g_rr
        ot_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
        assign rec_rdy = rec_rdy_rec && rr[0];
    end else begin : g_rr_port
        assign rr = {3{rst_n}};
        assign rec_rdy = rec_rdy_rec;
    end endgenerate
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(!GLU), .PAYLOAD_RESET(PAYLOAD_RESET)) u_rec (.clk(clk), .rst_n(rr[0]), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy_rec),
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
    // (hgi-1010/c timing: the op-level layout is registered once per op in S_PRE; regions then mux registers only)
    reg [LWB:0] l_full_q, l_half_q; reg [31:0] nn_q;
    wire [LWB:0] L_k = (rk == 3'd5) ? 1 : hf_k ? l_half_q : l_full_q;
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
                     S_DRAIN = 8, S_DRW = 9, S_DONE = 10, S_FAULT = 11, S_SOUT = 12, S_PRE = 13, S_NX1 = 14, S_NX2 = 15;
    // registered region operands (hgi-1010/c timing): the multiply's shift registers, the placement, the stage cursor
    reg [15:0] nrm1_s; reg [39:0] lsh_s; reg [15:0] nw_s; reg [2:0] gk_s; reg [LWB:0] lbk_s, gend_s, gsz_s, gsz2_s;
    reg [23:0] c_so, c_si; reg [15:0] c_nw; reg [LWB:0] c_L;
    reg [2:0] dk;                                         // drain region (4 O, 5 R)
    reg [26:0] rsec_d, rsec_d2, rsec_d3; reg so_w;
    reg [3:0] rp;                                         // read pipe
    reg [255:0] sr_data_q; reg sr_rv_q;
    always @(posedge clk) sr_data_q <= sr_data;
    always @(posedge clk or negedge rr[2]) if (!rr[2]) sr_rv_q <= 1'b0; else sr_rv_q <= sr_rv;
    // drain reads in flight: {VM sector, word mask} of each issued read, popped by its response (valid-driven, any
    // memory latency; hgi-1010/d exactness audit: no reader counts edges)
    reg [34:0] df [0:3]; reg [1:0] df_h, df_t; reg [2:0] nf;
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
    always @(posedge clk or negedge rr[2]) begin
        if (!rr[2]) begin ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; end
        else begin ready_q <= ready; idle_q <= idle; vfault_q <= vfault; end
    end
    reg vf_seen; reg [1:0] idle_ph;
    // PRE_PIPE: the op layout over 3 phases (pre_ph), every phase register to register
    function automatic [LWB:0] p2c_f(input [LWB:0] x);  // pow2ceil(x), x >= 1: smear(x - 1) + 1 (log depth)
        reg [LWB:0] y; integer b3;
        y = x - 1;
        for (b3 = 1; b3 <= LWB; b3 = b3 << 1) y = y | (y >> b3);
        p2c_f = y + 1;
    endfunction
    reg [1:0] pre_ph; reg [LWB:0] px_q, ps0_q, prnd_q, pvw_q; reg pflat_q; reg [23:0] pml_q, pmh_q;
    integer k2;
    always @(posedge clk or negedge rr[1]) begin
        if (!rr[1]) begin
            st <= S_IDLE; pre_ph <= 2'd0; op_rdy_r <= 1'b1; su_idle_r <= 1'b1; su_fault_r <= 1'b0; go <= 1'b0; vmq <= 338'd0;
            sl_v <= 1'b0; sw_v <= 1'b0; sr_v <= 1'b0; rp <= 4'd0; use_p <= 4'd0; nf <= 3'd0; df_h <= 2'd0; df_t <= 2'd0;
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
                        a_s <= strm[0]; o_s <= strm[1]; st <= S_PRE;
                    end
                end
                S_PRE: if (PRE_PIPE == 0) begin                     // the op's layout (registered once)
                    l_full_q <= l_el; l_half_q <= flatc ? (ni >> 1) : ((l_el >> 1) == 0 ? 1 : (l_el >> 1));
                    nn_q <= {16'd0, no} * {16'd0, ni};
                    st <= S_SPAN;
                end else begin : pre3                               // same values, 3 register-to-register phases
                    reg [LWB:0] se_;
                    case (pre_ph)
                        2'd0: begin                                 // operands: max(ni, 8 | 1), vw, flat, roundup, partials
                            px_q <= (ni > (red_on ? 16'd8 : 16'd1)) ? ni : (red_on ? 16'd8 : 16'd1);
                            pvw_q <= vw; pflat_q <= flatc; prnd_q <= (ni + N - 1) & ~(N - 1);
                            pml_q <= {8'd0, no} * {16'd0, ni[7:0]}; pmh_q <= {8'd0, no} * {16'd0, ni[15:8]};
                            pre_ph <= 2'd1;
                        end
                        2'd1: begin                                 // pow2ceil; the product
                            ps0_q <= p2c_f(px_q);
                            nn_q <= {8'd0, pml_q} + {pmh_q, 8'd0};
                            pre_ph <= 2'd2;
                        end
                        default: begin                              // slot = min(pow2ceil, vw); row width
                            se_ = (ps0_q > pvw_q) ? pvw_q : ps0_q;
                            if (pflat_q) begin l_full_q <= ni; l_half_q <= ni >> 1; end
                            else if (ni <= se_) begin l_full_q <= se_; l_half_q <= ((se_ >> 1) == 0) ? 1 : (se_ >> 1); end
                            else begin l_full_q <= prnd_q; l_half_q <= ((prnd_q >> 1) == 0) ? 1 : (prnd_q >> 1); end
                            pre_ph <= 2'd0; st <= S_SPAN;
                        end
                    endcase
                end
                S_SPAN: begin                                       // region rk: used? its layout
                    rv[rk] <= used_k && !(rk == 3'd0 && a_s);
                    lo[rk] <= base_k; sor[rk] <= so_k; sir[rk] <= si_k; nrr[rk] <= nr_k; nir[rk] <= ni_k;
                    Lr[rk] <= L_k; nrm1_s <= nr_k - 16'd1; lsh_s <= {{(39-LWB){1'b0}}, L_k}; nw_s <= ni_k;
                    gk_s <= (rk == 3'd4) ? 3'd4 : (rk == 3'd5) ? 3'd5 : rk;
                    if (rk == 3'd0 && a_s) begin                    // A = STREAM: rows of ni, element o ni + i = idx
                        wl[40 +: 24] <= SBASE; wl[64 +: 24] <= {8'd0, ni}; wl[88 +: 24] <= 24'd1; st <= S_NEXTR;
                    end else if (rk == 3'd4 && o_s) begin           // O = STREAM: contiguous rows of ni in G4, no drain
                        Lr[4] <= ni; nrr[4] <= no; nir[4] <= ni; rv[4] <= 1'b1;
                        nrm1_s <= no - 16'd1; lsh_s <= {24'd0, ni}; nw_s <= ni;
                        macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL;
                    end
                    else if (!used_k) st <= S_NEXTR;
                    else begin macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL; end
                    if (rk == 3'd0 && (aind != 2'd0 || w[32 +: 8] != 8'd0)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                end
                S_MUL: begin                                        // lsz = (nr - 1) L + nw: shift registers, a bit an edge
                    if (mph == 2'd0) begin
                        if (nrm1_s[0]) macc <= macc + lsh_s;
                        nrm1_s <= nrm1_s >> 1; lsh_s <= lsh_s << 1;
                        if (mbit == 5'd15) mph <= 2'd1; else mbit <= mbit + 5'd1;
                    end else begin
                        lsz[rk] <= macc[LWB:0] + nw_s; st <= S_NEXTR;
                    end
                end
                S_NEXTR: begin                                      // placement: the aligned base (registered)
                    lbk_s <= (galloc[gk_s] + N - 1) & ~(N - 1); gsz_s <= gsz(gk_s); gsz2_s <= gsz(3'd2);
                    st <= rv[rk] ? S_NX1 : S_NX2;
                end
                S_NX1: begin gend_s <= lbk_s + lsz[rk]; st <= S_NX2; end
                S_NX2: begin                                        // place region rk (N-aligned), rewrite its fields
                    if (rv[rk]) begin
                        lb[rk] <= lbk_s;
                        galloc[gk_s] <= gend_s;
                        if (rk == 3'd0 && cpair) galloc[2] <= gend_s;         // A's copy in G2 (C reads A[e ^ 1])
                        if (gend_s > gsz_s || (rk == 3'd0 && cpair && gend_s > gsz2_s)) begin
                            su_fault_r <= 1'b1; st <= S_FAULT; end
                        case (rk)
                            3'd0: begin wl[40 +: 24]  <= lbk_s; wl[64 +: 24]  <= Lr[0]; wl[88 +: 24]  <= 24'd1; end
                            3'd1: begin wl[138 +: 24] <= lbk_s; wl[162 +: 24] <= Lr[1]; wl[186 +: 24] <= 24'd1; end
                            3'd2: begin wl[211 +: 24] <= lbk_s; wl[235 +: 24] <= Lr[2]; wl[259 +: 24] <= 24'd1; end
                            3'd3: begin wl[284 +: 24] <= lbk_s; wl[308 +: 24] <= Lr[3]; wl[332 +: 24] <= 24'd1; end
                            3'd4: begin wl[382 +: 24] <= lbk_s; wl[406 +: 24] <= Lr[4]; wl[430 +: 24] <= 24'd1; end
                            default: begin wl[484 +: 24] <= lbk_s; wl[508 +: 24] <= 24'd1; end
                        endcase
                    end else begin
                        // an unused stream: give it the flat-consistent stride (so = row words, si = 1) so the vec's
                        // flatten test (every stream contiguous across rows) agrees with the dense layout's choice
                        // (flatc).  Without it an absent B / C / D (record so 0, si 1) made the vec run a flatc op
                        // unflattened: a whole-op reduction over rows of ni then issues 2^tz(ni)-element vectors at
                        // row offsets the lane-local banks cannot serve (cfault; DS L0 q_norm.ss, ni 160, at N 64).
                        // Same rule as ot_hgi_su_ctlx.
                        case (rk)
                            3'd1: begin wl[162 +: 24] <= bhalf ? {8'd0, ni >> 1} : {8'd0, ni}; wl[186 +: 24] <= 24'd1; end
                            3'd2: begin wl[235 +: 24] <= {8'd0, ni}; wl[259 +: 24] <= 24'd1; end
                            3'd3: begin wl[308 +: 24] <= bhalf ? {8'd0, ni >> 1} : {8'd0, ni}; wl[332 +: 24] <= 24'd1; end
                            3'd4: if (!o_s) begin wl[406 +: 24] <= {8'd0, ni}; wl[430 +: 24] <= 24'd1; end
                            default: ;
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
                        c_so <= sor[rk]; c_si <= sir[rk]; c_nw <= nir[rk]; c_L <= Lr[rk];
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
                            q_lo[q_t] <= s_rb; q_hi[q_t] <= s_rb + c_nw - 24'd1;
                            q_off[q_t] <= {{(25-LWB){1'b0}}, s_lr} - {2'b00, s_rb};
                            q_la[q_t] <= s_lr + s_j;
                            q_msk[q_t] <= (s_md == 2'd1) ? ((c_nw - s_j >= 16'd8) ? 8'hFF :
                                                            ((8'd1 << (c_nw - s_j)) - 8'd1)) : 8'd1;
                            q_t <= q_t + 2'd1;
                            // advance the cursor
                            case (s_md)
                                2'd0: last_ = (cur_sec == end_sec);
                                2'd1: last_ = (c_nw - s_j <= 16'd8);
                                default: last_ = (s_j + 16'd1 == c_nw);
                            endcase
                            if (last_) begin                              // the next row
                                s_rows <= s_rows - 16'd1; s_rb <= s_rb + c_so; s_va <= s_rb + c_so;
                                s_lr <= s_lr + c_L; s_j <= 16'd0;
                                cur_sec <= (s_rb + c_so) >> 3; end_sec <= (s_rb + c_so + c_nw - 24'd1) >> 3;
                            end else begin
                                cur_sec <= cur_sec + 27'd1;
                                if (s_md == 2'd1) s_j <= s_j + 16'd8;
                                else if (s_md == 2'd2) begin s_j <= s_j + 16'd1; s_va <= s_va + c_si; end
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
                S_RUN: if (ready_q && !sl_pend && (!a_s || {11'd0, scount} >= nn_q)) begin
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
                        if (o_s) begin etot <= PRE_PIPE ? nn_q[20:0] : {5'd0, no} * {5'd0, ni}; ebeat <= 21'd0; o_lb <= lb[4]; rp <= 4'd0; so_w <= 1'b0;
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
                        mk = MUT_DIRTY ? 8'hFF : (((8'd1 << cnt) - 8'd1) << off);
                        issue = d_live && outst + nf < 3'd4;
                        if (issue) begin
                            // 8 consecutive local words whose word 'off' is the element at d_cur
                            sr_v <= 1'b1; sr_g <= (dk == 3'd4) ? 2'd1 : 2'd2; sr_addr <= d_lcur[LWB-1:0] - off;
                            df[df_t] <= {27'({3'd0, d_cur[23:3]}), mk}; df_t <= df_t + 2'd1;
                            if (d_rem == {12'd0, cnt}) begin
                                if (d_row == 16'd1) d_live <= 1'b0;
                                else begin d_row <= d_row - 16'd1; d_rowb <= d_rowb + d_so; d_cur <= d_rowb + d_so;
                                           d_rem <= d_ni; d_lrow <= d_lrow + d_L; d_lcur <= d_lrow + d_L; end
                            end else begin
                                d_cur <= d_cur + (d_run ? {20'd0, cnt} : d_si); d_rem <= d_rem - {12'd0, cnt};
                                d_lcur <= d_lcur + cnt;
                            end
                        end
                        if (sr_rv_q) begin                          // a read's response: its sector to VM, word-masked
                            vmq <= {1'b1, 1'b1, df[df_h][34:8], 5'd0, sr_data_q,
                                    {{4{df[df_h][7]}}, {4{df[df_h][6]}}, {4{df[df_h][5]}}, {4{df[df_h][4]}},
                                     {4{df[df_h][3]}}, {4{df[df_h][2]}}, {4{df[df_h][1]}}, {4{df[df_h][0]}}},
                                    16'h5357};
                            df_h <= df_h + 2'd1;
                        end
                        nf <= nf + (issue ? 3'd1 : 3'd0) - (sr_rv_q ? 3'd1 : 3'd0);
                        outst <= outst + (sr_rv_q ? 3'd1 : 3'd0) - ((vr[273] && vr[256]) ? 3'd1 : 3'd0);
                        if (!d_live && nf == 3'd0 && outst == ((vr[273] && vr[256]) ? 3'd1 : 3'd0)) begin
                            dk <= dk + 3'd1; st <= S_DRAIN; end
                    end
                end
                S_SOUT: if (amr_q && !so_w) begin                  // 8 elements a beat, in element order
                    sr_v <= 1'b1; sr_g <= 2'd1; sr_addr <= o_lb + ebeat; so_w <= 1'b1;
                end else if (so_w && sr_rv_q) begin                 // the memory's response (valid-driven)
                    begin : so
                        reg [7:0] mk; integer q;
                        for (q = 0; q < 8; q = q + 1) mk[q] = (ebeat + q < etot);
                        am_stream <= {1'b0, 256'd0, sr_data_q, mk, (ebeat + 21'd8 >= etot), 1'b1};
                    end
                    so_w <= 1'b0;
                    if (ebeat + 21'd8 >= etot) st <= S_DONE; else ebeat <= ebeat + 21'd8;
                end
                S_DONE: begin su_idle_r <= 1'b1; op_rdy_r <= 1'b1; st <= S_IDLE; if (a_s) s_clr <= 1'b1; end
                S_FAULT: ;                                           // sticky (the adapter halts)
                default: st <= S_FAULT;
            endcase
        end
    end
`ifdef SU_DBG
    reg sfr_d; always @(posedge clk) sfr_d <= su_fault_r;
    always @(posedge clk) if (su_fault_r && !sfr_d)
        $display("SU_DBG %m fault st %0d rk %0d cfault %0d s0 %0d vf %0d gend %0d gsz %0d gsz2 %0d ni %0d no %0d L %0d lsz %0d",
                 st, rk, cfault_q, s0v_q && s0i_q >= SW, vf_seen, gend_s, gsz_s, gsz2_s, ni, no, Lr[rk], lsz[rk]);
`endif
endmodule

module ot_hgi_su_lbank #(
    parameter integer RB = 13,             // log2 words in the bank
    parameter integer MACRO = 1,           // 1: ot_sram_1r1w_1024x256 rows (RB = 13); 0: behavioural
    parameter integer LAT = 0              // bench mutant (behavioural banks): 1 = read latency 2 edges, 2 = 0 edges
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
    end else if (MACRO && RB == 9) begin : g_m9
        // 512 words occupy the lower 64 rows; the upper 64 physical rows are unused.
        wire [255:0] ro;
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in({1'b0, ra[RB-1:3]}), .rd_out(ro),
            .w_ce_in(we), .w_addr_in({1'b0, wa[RB-1:3]}), .wd_in({8{wd}}), .w_mask_in(wm), .rr_en(2'b00),
            .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
        assign rd = ro[{ks, 5'd0} +: 32];
    end else if (MACRO) begin : g_unsupported_macro
        initial $fatal(1, "ot_hgi_su_lbank: unsupported MACRO=1 RB=%0d", RB);
        assign rd = 32'd0;
    end else begin : g_b
        reg [31:0] m [0:(1 << RB) - 1];
        reg [31:0] q, q2;
        always @(posedge clk) begin if (re) q <= m[ra]; q2 <= q; if (we) m[wa] <= wd; end
        assign rd = (LAT == 1) ? q2 : (LAT == 2) ? m[ra] : q;
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
    parameter integer MUT_XBAR = 0,        // bench mutant: identity lanes take the neighbouring bank's word
    parameter integer LAT = 0,             // bench mutant: bank read latency 1 = +1 edge, 2 = -1 edge (see ot_hgi_su_lbank)
    parameter integer NS = 1               // sector lanes: NS independent 8-word stage writes / drain reads an edge
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [N-1:0]      rq,                    // qualified lane reads (used port, vector-memory source)
    input  wire [N-1:0]      rr,                    // raw lane read enables
    input  wire [N*AW-1:0]   ra,
    output wire [N*32-1:0]   rd,
    input  wire [NS-1:0]     sr_v,                  // per sector lane: 8 consecutive words (drain / STREAM-out)
    input  wire [NS*LWB-1:0] sr_addr,
    output wire [NS*256-1:0] sr_d,
    output wire [NS-1:0]     sr_rv,                 // sr_d valid: the sector read's response (follows the banks' latency)
    input  wire [NS-1:0]     sw_v,                  // per sector lane: up to 8 consecutive words (stage)
    input  wire [NS*LWB-1:0] sw_addr,
    input  wire [NS*8-1:0]   sw_mask,
    input  wire [NS*256-1:0] sw_d,
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
    reg src;                                         // sector-lane read conflict (this edge)
    always @* begin : rsel
        integer rj_, sl_; reg [LWB-1:0] sa; reg [LN-1:0] bl;
        sa = {LWB{1'b0}}; bl = {LN{1'b0}};
        for (b = 0; b < N; b = b + 1) begin b_re[b] = 1'b0; b_ra[b] = {RB{1'b0}}; end
        for (l = 0; l < N; l = l + 1) begin
            bl = ra[l*AW +: LN]; lok[l] = (l == 0);
            for (k = 0; k < NCAND; k = k + 1) if (cbank(l, k) == bl) lok[l] = 1'b1;
        end
        src = 1'b0;
        if (|sr_v) begin
            // sector lanes: 8 words each; two words on one bank must be one row (else a sector-lane conflict, fail closed)
            for (sl_ = 0; sl_ < NS; sl_ = sl_ + 1) if (sr_v[sl_])
                for (rj_ = 0; rj_ < 8; rj_ = rj_ + 1) begin
                    sa = sr_addr[sl_*LWB +: LWB] + rj_;
                    if (b_re[sa[LN-1:0]] && b_ra[sa[LN-1:0]] != sa[LWB-1:LN]) src = 1'b1;
                    b_re[sa[LN-1:0]] = 1'b1; b_ra[sa[LN-1:0]] = sa[LWB-1:LN];
                end
        end else begin
            // lowest-index lane wins a bank (the bank's row); the others must agree (checked below)
            for (l = N - 1; l >= 0; l = l - 1)
                if (rr[l] && lok[l]) begin
                    bl = ra[l*AW +: LN]; b_re[bl] = 1'b1; b_ra[bl] = ra[l*AW + LN +: RB];
                end
        end
    end
    reg [LN-1:0] lb_q [0:N-1]; reg [LN-1:0] sr_lo [0:NS-1];
    reg [LN-1:0] lb_q2 [0:N-1]; reg [LN-1:0] sr_lo2 [0:NS-1]; reg [NS-1:0] srv1, srv2;
    integer s_;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) if (rr[l]) lb_q[l] <= ra[l*AW +: LN];
        for (s_ = 0; s_ < NS; s_ = s_ + 1) begin if (sr_v[s_]) sr_lo[s_] <= sr_addr[s_*LWB +: LN]; sr_lo2[s_] <= sr_lo[s_]; end
        for (l = 0; l < N; l = l + 1) lb_q2[l] <= lb_q[l];
        srv2 <= srv1;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) srv1 <= {NS{1'b0}}; else srv1 <= sr_v;
    // the response valid and the network selects follow the banks' latency (LAT mutants move the data, valid and
    // selects together, so a valid-driven reader stays exact and a fixed-latency one does not)
    assign sr_rv = (LAT == 1) ? srv2 : (LAT == 2) ? sr_v : srv1;
    wire [LN-1:0] lb_s [0:N-1];
    for (genvar gs_ = 0; gs_ < N; gs_ = gs_ + 1) begin : g_ls
        assign lb_s[gs_] = (LAT == 1) ? lb_q2[gs_] : (LAT == 2) ? ra[gs_*AW +: LN] : lb_q[gs_];
    end
    // the data network: a lane takes its bank among its candidates (lane 0: any bank)
    genvar gl, gj, gk;
    for (gl = 0; gl < N; gl = gl + 1) begin : g_rd
        if (gl == 0) begin : g_any
            wire [LN-1:0] bs = lb_s[gl] + MUT_XBAR[LN-1:0];
            assign rd[0 +: 32] = b_rd[bs];
        end else begin : g_c
            reg [31:0] dv;
            always @* begin : mx
                integer kk;
                dv = 32'd0;
                for (kk = NCAND - 1; kk >= 0; kk = kk - 1)
                    if (lb_s[gl] == cbank(gl, kk)) dv = b_rd[(cbank(gl, kk) + MUT_XBAR) % N];
            end
            assign rd[32*gl +: 32] = dv;
        end
    end
    for (gk = 0; gk < NS; gk = gk + 1) begin : g_srl
        wire [LN-1:0] sr_s = (LAT == 1) ? sr_lo2[gk] : (LAT == 2) ? sr_addr[gk*LWB +: LN] : sr_lo[gk];
        for (gj = 0; gj < 8; gj = gj + 1) begin : g_sr
            wire [LN-1:0] bj = sr_s + gj;
            assign sr_d[256*gk + 32*gj +: 32] = b_rd[bj];
        end
    end
    // ---- write side: stage (8 words) > lane writes > the single-word STREAM landing (its own group in practice)
    reg  [N-1:0] b_we; reg [RB-1:0] b_wa [0:N-1]; reg [31:0] b_wd [0:N-1];
    reg  wcoll;
    always @* begin : wsel
        integer wl_, wj_, wk_, ws_; reg [LWB-1:0] sb; reg [LN-1:0] wb_; reg ok_;
        sb = {LWB{1'b0}}; wb_ = {LN{1'b0}}; ok_ = 1'b0;
        for (b = 0; b < N; b = b + 1) begin b_we[b] = 1'b0; b_wa[b] = {RB{1'b0}}; b_wd[b] = 32'd0; end
        wcoll = 1'b0;
        for (ws_ = 0; ws_ < NS; ws_ = ws_ + 1) if (sw_v[ws_])
            for (wj_ = 0; wj_ < 8; wj_ = wj_ + 1) if (sw_mask[ws_*8 + wj_]) begin
                sb = sw_addr[ws_*LWB +: LWB] + wj_;
                if (b_we[sb[LN-1:0]]) wcoll = 1'b1;          // two sector lanes on one bank: fail closed
                b_we[sb[LN-1:0]] = 1'b1; b_wa[sb[LN-1:0]] = sb[LWB-1:LN]; b_wd[sb[LN-1:0]] = sw_d[ws_*256 + 32*wj_ +: 32];
            end
        if (NLW > 0) begin
            if (|sw_v && |lw) wcoll = 1'b1;
            for (wl_ = 0; wl_ < NL; wl_ = wl_ + 1)
                if (lw[wl_]) begin
                    wb_ = lwa[wl_*AW +: LN]; ok_ = (wl_ == 0);
                    for (wk_ = 0; wk_ < NROT; wk_ = wk_ + 1) if (cbank(wl_, wk_) == wb_) ok_ = 1'b1;
                    if (!ok_) wcoll = 1'b1;
                    // two lanes on one bank must write the same row (the later lane wins, as a behavioural memory)
                    if (b_we[wb_] && b_wa[wb_] != lwa[wl_*AW + LN +: RB]) wcoll = 1'b1;
                    if (!(|sw_v)) begin b_we[wb_] = 1'b1; b_wa[wb_] = lwa[wl_*AW + LN +: RB]; b_wd[wb_] = lwd[32*wl_ +: 32]; end
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
        rq_q <= (|sr_v) ? {N{1'b0}} : rq; lok_q <= lok; srv_q <= ((|sr_v) && |rq) || src; wcoll_q <= wcoll;
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
            if (srv_q) $display("LMEM_DBG %m sr during lane reads / sector-lane conflict");
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
        ot_hgi_su_lbank #(.RB(RB), .MACRO(MACRO), .LAT(LAT)) u_b (.clk(clk), .re(b_re[gb]), .ra(b_ra[gb]), .rd(b_rd[gb]),
            .we(b_we[gb]), .wa(b_wa[gb]), .wd(b_wd[gb]));
    end
endmodule

// the reducer results: a small register file, NR write ports (any address), 8-word reads
module ot_hgi_su_rfile #(parameter integer NR = 2, RWB = 6, AW = 24, NS = 1) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NR-1:0]     we,
    input  wire [NR*AW-1:0]  wa,
    input  wire [NR*32-1:0]  wd,
    input  wire [NS-1:0]     sr_v,
    input  wire [NS*RWB-1:0] sr_addr,
    output reg  [NS*256-1:0] sr_d,
    output reg  [NS-1:0]     sr_rv,                 // sr_d valid (one edge after sr_v)
    output reg               flt                    // a result outside the file
);
    reg [31:0] m [0:(1 << RWB) - 1];
    integer j, q, s;
    always @(posedge clk) begin
        for (j = 0; j < NR; j = j + 1) if (we[j]) m[wa[j*AW +: RWB]] <= wd[32*j +: 32];
        for (s = 0; s < NS; s = s + 1)
            if (sr_v[s]) for (q = 0; q < 8; q = q + 1) sr_d[256*s + 32*q +: 32] <= m[(sr_addr[s*RWB +: RWB] + q) & ((1 << RWB) - 1)];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) flt <= 1'b0;
        else for (j = 0; j < NR; j = j + 1) if (we[j] && |wa[j*AW + RWB +: AW - RWB]) flt <= 1'b1;
    always @(posedge clk or negedge rst_n) if (!rst_n) sr_rv <= {NS{1'b0}}; else sr_rv <= sr_v;
endmodule

module ot_hgi_su_lmem #(
    parameter integer N = 16, M = 8, LWB = 17, AW = 24, NR = N / 8, MACRO = 1,
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB, LGO = LWB,   // log2 words of B, C, D, O (G0 = LWB: A)
    parameter integer RWB = 6,                                      // log2 words of the reducer-result file
    parameter integer SLB = 16,
    parameter integer NOSTR = 0,
    parameter integer MUT_XBAR = 0,
    parameter integer MUT_LAT = 0,         // bench mutants: 1 / 2 = every bank's read latency +1 / -1 edge (behavioural
                                           //   banks; the lane ports' 1-edge contract breaks), 3 / 4 = the drain response
                                           //   valid one edge early / late against its data
    parameter integer NS = 1               // sector lanes (stage writes / drain reads an edge; WIDE: 32, lane b = sector b)
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
    input  wire [NS-1:0]     sw_v,                  // per sector lane: up to 8 consecutive words (any alignment)
    input  wire [3:0]        sw_g,                  // staging groups of this edge's writes (A, B, C, D; A + C for c_pair)
    input  wire [NS*LWB-1:0] sw_addr,
    input  wire [NS*8-1:0]   sw_mask,
    input  wire [NS*256-1:0] sw_data,
    input  wire [NS-1:0]     sr_v,                  // per sector lane: 8 consecutive words (any alignment)
    input  wire [1:0]        sr_g,                  // this edge's drain reads: 1 = O, 2 = R
    input  wire [NS*LWB-1:0] sr_addr,
    output wire [NS*256-1:0] sr_data,
    output wire [NS-1:0]     sr_rv,                 // sr_data valid per lane: drain / STREAM-out readers consume on it
    output reg               cfault
);
    localparam integer LAT = (MUT_LAT == 1 || MUT_LAT == 2) ? MUT_LAT : 0;
    wire [6:0] gf; wire [NS*256-1:0] o_sr, r_sr; wire [NS-1:0] o_rv, r_rv;
    reg [1:0] srg_q; always @(posedge clk) if (|sr_v) srg_q <= sr_g;
    assign sr_data = (srg_q == 2'd2) ? r_sr : o_sr;
    wire [NS-1:0] srv0 = (srg_q == 2'd2) ? r_rv : o_rv;
    reg [NS-1:0] srv_late; always @(posedge clk or negedge rst_n) if (!rst_n) srv_late <= {NS{1'b0}}; else srv_late <= srv0;
    assign sr_rv = (MUT_LAT == 3) ? (sr_v & {NS{sr_g == 2'd1 || sr_g == 2'd2}}) : (MUT_LAT == 4) ? srv_late : srv0;
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
        wire [NS*GB-1:0] sw_ga;
        for (genvar s = 0; s < NS; s = s + 1) begin : g_swa assign sw_ga[s*GB +: GB] = sw_addr[s*LWB +: GB]; end
        ot_hgi_su_lgroup2 #(.N(N), .M(M), .LWB(GB), .AW(AW), .NLW(0), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR), .LAT(LAT), .NS(NS)) u_g (
            .clk(clk), .rst_n(rst_n), .rq(rq), .rr(rr), .ra(ra), .rd(rd), .sr_v({NS{1'b0}}), .sr_addr({NS*GB{1'b0}}), .sr_d(), .sr_rv(),
            .sw_v(sw_v & {NS{sw_g[g]}}), .sw_addr(sw_ga), .sw_mask(sw_mask), .sw_d(sw_data), .lw(1'b0),
            .lwa({AW{1'b0}}), .lwd(32'd0), .s1_v(1'b0), .s1_a({GB{1'b0}}), .s1_d(32'd0), .flt(gf[g]));
    end
    // GO: the lanes' element writes; drain / STREAM-out reads
    wire [NS*LGO-1:0] sr_oa; wire [NS*RWB-1:0] sr_ra;
    for (genvar s = 0; s < NS; s = s + 1) begin : g_sra
        assign sr_oa[s*LGO +: LGO] = sr_addr[s*LWB +: LGO]; assign sr_ra[s*RWB +: RWB] = sr_addr[s*LWB +: RWB];
    end
    ot_hgi_su_lgroup2 #(.N(N), .M(M), .LWB(LGO), .AW(AW), .NLW(N), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR), .LAT(LAT), .NS(NS)) u_go (
        .clk(clk), .rst_n(rst_n), .rq({N{1'b0}}), .rr({N{1'b0}}), .ra({N*AW{1'b0}}), .rd(), .sr_v(sr_v & {NS{sr_g == 2'd1}}),
        .sr_addr(sr_oa), .sr_d(o_sr), .sr_rv(o_rv), .sw_v({NS{1'b0}}), .sw_addr({NS*LGO{1'b0}}), .sw_mask({NS*8{1'b0}}), .sw_d({NS*256{1'b0}}),
        .lw(vm_we), .lwa(vm_waddr), .lwd(vm_wdata), .s1_v(1'b0), .s1_a({LGO{1'b0}}), .s1_d(32'd0), .flt(gf[4]));
    // GR: the reducer results
    ot_hgi_su_rfile #(.NR(NR), .RWB(RWB), .AW(AW), .NS(NS)) u_gr (.clk(clk), .rst_n(rst_n), .we(res_we), .wa(res_addr),
        .wd(res_data), .sr_v(sr_v & {NS{sr_g == 2'd2}}), .sr_addr(sr_ra), .sr_d(r_sr), .sr_rv(r_rv), .flt(gf[5]));
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
        ot_hgi_su_lgroup2 #(.N(N), .M(M), .LWB(SLB), .AW(AW), .NLW(0), .MACRO(MACRO), .MUT_XBAR(MUT_XBAR), .LAT(LAT)) u_gs (
            .clk(clk), .rst_n(rst_n), .rq(gs_rq), .rr(gs_rr), .ra(gs_ra), .rd(gs_rd), .sr_v(1'b0), .sr_addr({SLB{1'b0}}),
            .sr_d(), .sr_rv(), .sw_v(1'b0), .sw_addr({SLB{1'b0}}), .sw_mask(8'd0), .sw_d(256'd0), .lw(1'b0), .lwa({AW{1'b0}}),
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
    parameter integer WIDE = 0,           // hgi-unitrate: 1 = ot_hgi_su_ctlw on the behavioural wide lmem (bench model);
                                          //   2 = ot_hgi_su_ctlx on d's lane-local lmem (NS 32): the PRODUCTION engine
    parameter integer MUT_X = 0,          // WIDE = 2 bench mutants (ot_hgi_su_ctlx)
    parameter integer DF = 16,            // WIDE = 2: landed-but-unwritten stage sectors a lane
    parameter integer LQ = 8,             // WIDE: credits a lane holds (size to the lane-group round trip incl. relays)
    parameter integer LRLAT = 1,          // WIDE bench: the wide lmem model's read latency (the controller is valid-driven)
    parameter integer MUT_RV = 0,         // WIDE bench: lmem read valid 1 early / 2 late (must FAIL)
    parameter integer MUT_W = 0,          // WIDE bench mutants (ot_hgi_su_ctlw)
    // WIDE = 0 (hgi-1010/d): the lane-local banked local memory (ot_hgi_su_lmem) and its dense-layout controller
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB, LGO = LWB, RWB = 6,
    parameter integer MACRO = 1,          // local memory: 1 = banked SRAM macros, 0 = behavioural banks
    parameter integer MUT_LAT = 0         // bench mutants (ot_hgi_su_lmem MUT_LAT; 1 / 2 force behavioural banks)
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
    input  wire          am_rdy,
    // WIDE = 1 only (tie off / leave open otherwise): the VM wide lanes, lane b <-> VM bank b (ot_hgi_su_ctlw)
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,           // shared lane groups: request / grant (tie grants 1 for a dedicated group)
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    localparam integer AW = 24, NR = N / 8;
    wire go, ready, idle, vfault, ofault, ro; wire [669:0] wl;
    wire sl_v, sw_v, dc_v, sr_v; wire [LWB-1:0] sl_addr; wire [31:0] sl_data; wire [LWB-4:0] sw_sec, dc_sec, sr_sec;
    wire [255:0] sw_data, sr_data; wire [7:0] sr_dm;
    wire [31:0] lsw_v, ldc_v, ldr_v; wire [32*(LWB-3)-1:0] lsw_sec, ldc_sec, ldr_sec; wire [32*256-1:0] lsw_d, ldr_d;
    wire [32*8-1:0] ldr_dm; wire lm_bank_err; wire [31:0] ldr_rv; wire sr_rv;
    // WIDE = 0: the lane-local memory's controller ports
    wire [LWB-1:0] l_sw_addr, l_sr_addr; wire [7:0] l_sw_mask; wire [3:0] l_sw_g, l_use_p; wire [1:0] l_sr_g;
    wire l_sl_pend, l_cfault, l_a_str, l_sr_rv;
    // WIDE = 2: the production engine's 32 lmem sector lanes
    wire [31:0] x_sw_v, x_sr_v, x_sr_rv; wire [32*256-1:0] x_sw_data, x_sr_data; wire [3:0] x_sw_g, x_use_p; wire [1:0] x_sr_g;
    wire [32*LWB-1:0] x_sw_addr, x_sr_addr; wire [32*8-1:0] x_sw_mask; wire x_a_str, x_cfault, x_sl_pend;
    generate if (WIDE == 2) begin : g_xctl
    ot_hgi_su_ctlx #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET),
        .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB), .LQ(LQ), .DF(DF), .MUT_X(MUT_X)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data),
        .sw_v(x_sw_v), .sw_data(x_sw_data), .sw_g(x_sw_g), .sw_addr(x_sw_addr), .sw_mask(x_sw_mask), .sr_v(x_sr_v), .sr_g(x_sr_g),
        .sr_addr(x_sr_addr), .sr_data(x_sr_data), .sr_rv(x_sr_rv), .use_p(x_use_p), .sl_pend(x_sl_pend), .a_str(x_a_str),
        .cfault(x_cfault), .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done),
        .rg_req(rg_req), .rg_gnt(rg_gnt), .wg_req(wg_req), .wg_gnt(wg_gnt));
    end else if (WIDE == 1) begin : g_wctl
`ifndef OT_CTLW_SLICES
`define OT_CTLW_SLICES 0
`endif
    ot_hgi_su_ctlw #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET), .MUT_W(MUT_W), .LQ(LQ), .SLICES(`OT_CTLW_SLICES)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sw_v(sw_v),
        .sw_sec(sw_sec), .sw_data(sw_data), .dc_v(dc_v), .dc_sec(dc_sec), .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm),
        .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .rg_req(rg_req), .rg_gnt(rg_gnt),
        .wg_req(wg_req), .wg_gnt(wg_gnt), .ldr_rv(ldr_rv), .sr_rv(sr_rv), .lsw_v(lsw_v), .lsw_sec(lsw_sec),
        .lsw_d(lsw_d), .ldc_v(ldc_v), .ldc_sec(ldc_sec), .ldr_v(ldr_v), .ldr_sec(ldr_sec), .ldr_d(ldr_d), .ldr_dm(ldr_dm));
    end else begin : g_ctl
    ot_hgi_su_ctl #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET), .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sw_v(sw_v),
        .sw_addr(l_sw_addr), .sw_mask(l_sw_mask), .sw_data(sw_data), .sw_g(l_sw_g), .sr_v(sr_v), .sr_g(l_sr_g),
        .sr_addr(l_sr_addr), .sr_data(sr_data), .sr_rv(l_sr_rv), .use_p(l_use_p), .sl_pend(l_sl_pend), .a_str(l_a_str),
        .cfault(l_cfault));
        assign wrq = '0; assign wwq = '0; assign rg_req = 1'b0; assign wg_req = 1'b0;
    end endgenerate
    wire [N-1:0] vi_re, vm_we, kv_we; wire [N*AW-1:0] vi_addr, vm_waddr, kv_waddr; wire [N*32-1:0] vi_q;
    wire [4*N*AW-1:0] rd_addr; wire [4*N-1:0] rd_re; wire [8*N-1:0] rd_src; wire [4*N*32-1:0] rd_q;
    wire [N*32-1:0] vm_wdata, kv_wdata; wire [NR-1:0] res_we; wire [NR*AW-1:0] res_addr; wire [NR*32-1:0] res_data;
    wire [7:0] cr_seq, cr_dseq, cr_rseq; wire [15:0] cr_cnt, emitted; wire de, dr, ds; wire [7:0] es, rs, ss;
`ifdef OT_SU_C12
    // tput-fix-1011 (bench only, -DOT_SU_C12 with the *_c12 file set): the stream unit as the die's c12 lane array --
    // ot_su13_ctl64's functional parameter set (rtl/hdc/v41x/phys/ot_hdc_su_ctl_c13_phys.sv less the physical-only CTL13;
    // lanes = ot_su12_sfu / ot_su12_light: MLAT 6, ALAT 6, OPR 1, DDIV 21, SIDEX 4, CAPR 1)
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV), .BCAST_STAGES(7), .RET_STAGES(8), .MLAT(6), .ALAT(6), .OPR(1), .DDIV(21),
                      .SIDEX(4), .FSQ(1), .CAPR(1), .RPAD(1), .RSL(2), .RTAP(1), .ROUT(1), .RSLICE(`OT_SU_C12_RSLICE),
                      .CTL12(1), .DENR(`OT_SU_C12_DENR), .SFUT(`OT_SU_C12_SFUT))
                    u_vec (.clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
`else
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(LV)) u_vec (.clk(clk), .rst_n(rst_n), .go(go), .ready(ready), .idle(idle),
`endif
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
    generate if (WIDE == 2) begin : g_xmem
    ot_hgi_su_lmem #(.N(N), .M(M), .LWB(LWB), .AW(AW), .MACRO(MACRO && (MUT_LAT == 0 || MUT_LAT > 2)), .MUT_LAT(MUT_LAT),
        .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB), .SLB(SLB), .NOSTR(GLU), .NS(32)) u_mem (.clk(clk), .rst_n(rst_n),
        .use_p(x_use_p), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_re(rd_re), .rd_addr(rd_addr), .rd_src(rd_src),
        .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .res_we(res_we), .res_addr(res_addr),
        .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sl_pend(x_sl_pend), .a_str(x_a_str),
        .sw_v(x_sw_v), .sw_g(x_sw_g), .sw_addr(x_sw_addr), .sw_mask(x_sw_mask), .sw_data(x_sw_data), .sr_v(x_sr_v), .sr_g(x_sr_g),
        .sr_addr(x_sr_addr), .sr_data(x_sr_data), .sr_rv(x_sr_rv), .cfault(x_cfault));
    end else if (WIDE == 1) begin : g_wmem
    ot_hgi_su_lmemw #(.N(N), .LWB(LWB), .AW(AW), .RLAT(LRLAT), .MUT_RV(MUT_RV)) u_mem (.clk(clk), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .rd_re(rd_re), .rd_addr(rd_addr), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data),
        .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm),
        .lsw_v(lsw_v), .lsw_sec(lsw_sec), .lsw_d(lsw_d), .ldc_v(ldc_v), .ldc_sec(ldc_sec), .ldr_v(ldr_v), .ldr_sec(ldr_sec),
        .ldr_d(ldr_d), .ldr_dm(ldr_dm), .ldr_rv(ldr_rv), .sr_rv(sr_rv), .bank_err(lm_bank_err));
    end else begin : g_mem
    ot_hgi_su_lmem #(.N(N), .M(M), .LWB(LWB), .AW(AW), .MACRO(MACRO && (MUT_LAT == 0 || MUT_LAT > 2)), .MUT_LAT(MUT_LAT),
        .LG1(LG1), .LG2(LG2), .LG3(LG3), .LGO(LGO), .RWB(RWB), .SLB(SLB), .NOSTR(GLU)) u_mem (.clk(clk), .rst_n(rst_n),
        .use_p(l_use_p), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_re(rd_re), .rd_addr(rd_addr), .rd_src(rd_src),
        .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .res_we(res_we), .res_addr(res_addr),
        .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sl_pend(l_sl_pend), .a_str(l_a_str),
        .sw_v(sw_v), .sw_g(l_sw_g), .sw_addr(l_sw_addr), .sw_mask(l_sw_mask), .sw_data(sw_data), .sr_v(sr_v), .sr_g(l_sr_g),
        .sr_addr(l_sr_addr), .sr_data(sr_data), .sr_rv(l_sr_rv), .cfault(l_cfault));
    end endgenerate
endmodule
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 stream-unit / SFU die body controller, WIDE successor (hgi-unitrate 2026-10-10; ot_hgi_su_unit WIDE = 1).
// Same record semantics as ot_hgi_su_ctl (stage the op's VM operands into the local operand memory, run the unchanged
// ot_hdc_v41x_vec on local addresses, drain the words it wrote, retire on the last drain write), re-architected for
// throughput at the production record shapes (Qwen3-8B P 8,191: 31,276 sectors staged and 19,682 drained a layer):
//   * span: the (no - 1) so + (ni - 1) si extent is a 3-edge pipelined multiply (4 partial products of 8 x 24),
//     not 32 serial shift-add edges a region;
//   * placement: every region is placed with lb == lo (mod 256 words), so a VM sector and its local copy sit in the
//     same bank (sector mod 32): the 32 wide lanes need no crossbar;
//   * stage: 32 lanes, lane b streams bank b's sectors of every source region through the VM wide read lanes (LQ
//     credits a lane, in-order responses landed through a per-lane FIFO of local sector numbers), while the same lane
//     clears its sink sectors' dirty masks: one sector a lane an edge, 1 KB an edge per unit;
//   * drain: 32 lanes read {data, dirty mask} of their local sink sectors (read pipe 3 edges) and write each dirty
//     sector word-masked through the VM wide write lanes (credit at acceptance, retire on the last done).
// The packet client (vmq / vmr) stays idle in this mode.  Order, faults and STREAM paths are those of ot_hgi_su_ctl.
// ---------------------------------------------------------------------------------------------------------------------
`ifndef OT_CTLW_NLP
`ifdef OT_CTLW_HEAD_EXT
`define OT_CTLW_NLP 8      // GLUE PLACEMENT (el1011-hbm-sfu 10-11): the ctlw HEAD tile = control + slice 0 (lanes 0-7)
`else
`define OT_CTLW_NLP 32
`endif
`endif
module ot_hgi_su_ctlw #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,           // log2 local words (the Qwen head: 37,984 B + O + the stream region)
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,            // 1: the SFU die body (SFU.GLU records; ot_hgi_su_record GLU mode)
    parameter integer SLB = 16,           // log2 words of the stream-0 landing region (top of the local memory)
    parameter integer MUT_DIRTY = 0,      // mutant: drain whole sectors (overwrites words the op did not write)
    parameter integer LQ = 8,             // credits a wide lane holds (= the VM lane queue depth)
    parameter integer MUT_W = 0,          // bench mutants: 1 stage lands every sector at its lane's first slot (no
                                          //   advance), 2 the drain skips the last sector of each lane, 3 the record
                                          //   retires before its drain writes are in VM (no done wait), 4 no source / live-sink hazard check
                                          //   (a record stages an operand an older record has not drained yet)
    parameter integer SLICES = 0,         // el1011-hbm-sfu: 1 = 4 hardened 8-lane slices + 2-stage reduction hub, 2 = and
                                          //   the lanes' landing FIFOs in 64x16 SRAM (default 0: flat)
    parameter integer OVL = 1             // 1: three-slot record pipeline (span + stage | run | drain overlap); 0: one
                                          //   record at a time (each slot waits for the younger ones to empty)
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
    output reg           sw_v,                // a staged sector (8 words, local sector address)
    output reg  [LWB-4:0] sw_sec,
    output reg  [255:0]  sw_data,
    output reg           dc_v,                // clear a sector's dirty mask
    output reg  [LWB-4:0] dc_sec,
    output reg           sr_v,                // read a sector: words + dirty mask, one edge later
    output reg  [LWB-4:0] sr_sec,
    input  wire [255:0]  sr_data,
    input  wire [7:0]    sr_dm,
    // WIDE STAGE / DRAIN (hgi-unitrate 2026-10-10): 32 lanes, lane b <-> VM bank b <-> local bank b (every region is
    // placed with lb == lo mod 256 words, so a VM sector and its local copy share the bank: no crossbar)
    output wire  [`OT_CTLW_NLP*16-1:0]  wrq,          // VM wide read lane b {v, sector 15}: LQ credits a lane
    input  wire [`OT_CTLW_NLP-1:0]       wrq_cr,       // a credit back (the request reached its bank)
    input  wire [`OT_CTLW_NLP*257-1:0] wrr,          // the sector {v, data 256}, in request order
    output wire  [`OT_CTLW_NLP*280-1:0] wwq,          // VM wide write lane b {v, sector 15, wdata 256, word mask 8}
    input  wire [`OT_CTLW_NLP-1:0]       wwq_cr,       // a credit back (the write reached its bank)
    input  wire [`OT_CTLW_NLP-1:0]       wwq_done,     // a write in the macro (the record retires after the last)
    // shared lane groups (ot_hgi_vm_lanearb): a burst (a record's stage / drain) holds its group from grant to release;
    // tie the grants high for a dedicated group
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt,
    output wire  [`OT_CTLW_NLP-1:0]       lsw_v,        // local stage write lane b (sector, data)
    output wire  [`OT_CTLW_NLP*(LWB-3)-1:0] lsw_sec,
    output wire  [`OT_CTLW_NLP*256-1:0] lsw_d,
    output wire  [`OT_CTLW_NLP-1:0]       ldc_v,        // local dirty clear lane b
    output wire  [`OT_CTLW_NLP*(LWB-3)-1:0] ldc_sec,
    output wire  [`OT_CTLW_NLP-1:0]       ldr_v,        // local drain read lane b: {data, dirty mask} one edge later
    output wire  [`OT_CTLW_NLP*(LWB-3)-1:0] ldr_sec,
    input  wire [`OT_CTLW_NLP*256-1:0] ldr_d,
    input  wire [`OT_CTLW_NLP*8-1:0]   ldr_dm,
    input  wire [`OT_CTLW_NLP-1:0]       ldr_rv,       // the lane's drain read data is valid (any latency, in request order)
    input  wire              sr_rv         // the STREAM-out sector read data is valid
`ifdef OT_CTLW_HEAD_EXT
    // the edge-registered nearest-neighbour link to slice tile 1 (descriptor / go forward from slice 0's pin registers,
    // the done / overflow combine back into slice 0's pin flops)
    , output wire c_wst_go, output wire c_wdr_go, output wire c_d_os,
    output wire [6*24-1:0] c_lo, output wire [6*24-1:0] c_hi, output wire [6*(LWB+1)-1:0] c_lb, output wire [5:0] c_rv,
    output wire [6*21-1:0] c_dsec, output wire [2*24-1:0] c_dlo, output wire [2*24-1:0] c_dhi,
    output wire [2*(LWB+1)-1:0] c_dlb, output wire [1:0] c_drv, output wire [2*21-1:0] c_ddsec,
    input  wire c_wst_dn, input wire c_wdr_dn, input wire c_ovf
`endif
);
    localparam integer AW = 24, NR = N / 8, LW = 1 << LWB;
    // ---- the record adapter (decode) and the op it issues
    wire op_v; reg op_rdy_r; wire [669:0] op_w; reg su_idle_r, su_fault_r;
    wire [1:0] strm;
    reg su_ret;
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(!GLU), .PAYLOAD_RESET(PAYLOAD_RESET), .PIPED(1)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a), .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o),
        .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a), .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted),
        .drained(), .op_strm(strm), .lg_v(1'b0), .lg_rdy(), .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy_r), .op_w(op_w),
        .su_idle(su_idle_r), .su_fault(su_fault_r), .su_ret(su_ret));
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
    function automatic [23:0] fb(input integer k);
        case (k) 0: fb = 40; 1: fb = 138; 2: fb = 211; 3: fb = 284; 4: fb = 382; default: fb = 484; endcase
    endfunction
    reg [2:0] rk;                                         // region walk
    reg [23:0] base_k, so_k, si_k; reg [15:0] nr_k, ni_k; reg used_k;
    always @* begin
        case (rk)
            3'd0: begin base_k = w[40 +: 24];  so_k = w[64 +: 24];  si_k = w[88 +: 24];  used_k = 1'b1; end
            3'd1: begin base_k = w[138 +: 24]; so_k = w[162 +: 24]; si_k = w[186 +: 24]; used_k = use_b; end
            3'd2: begin base_k = w[211 +: 24]; so_k = w[235 +: 24]; si_k = w[259 +: 24]; used_k = use_c; end
            3'd3: begin base_k = w[284 +: 24]; so_k = w[308 +: 24]; si_k = w[332 +: 24]; used_k = use_d; end
            3'd4: begin base_k = w[382 +: 24]; so_k = w[406 +: 24]; si_k = w[430 +: 24]; used_k = (dst == 2'd1); end
            default: begin base_k = w[484 +: 24]; so_k = w[508 +: 24]; si_k = 24'd0; used_k = (red != 2'd0); end
        endcase
        nr_k = (rk == 3'd5) ? ((redwhole || redtree) ? 16'd1 : no) : no;
        ni_k = (rk == 3'd5) ? 16'd1 : ((bhalf && (rk == 3'd1 || rk == 3'd3)) ? ((ni + 16'd1) >> 1) : ni);
    end
    // ---- span / relocation per region
    reg [23:0] lo [0:5]; reg [23:0] hi [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5];
    reg [LWB:0] alloc;
    reg [39:0] macc; reg [4:0] mbit; reg [1:0] mph;        // (nr - 1) so + (ni - 1) si
    reg [15:0] ma, mc; reg [23:0] mb, md; reg [31:0] pp0, pp1, pp2, pp3;
    reg [23:0] span_hi;
    // ---- VM traffic
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg [2:0] outst; reg [26:0] q_sec [0:3]; reg [1:0] q_h, q_t;  // outstanding requests (sectors), in order
    reg [26:0] cur_sec, end_sec;
    reg [3:0] st;
    localparam [3:0] S_IDLE = 0, S_SPAN = 1, S_MUL = 2, S_NEXTR = 3, S_STAGE = 4, S_STW = 5, S_RUN = 6, S_RUNW = 7,
                     S_DRAIN = 8, S_DRW = 9, S_DONE = 10, S_FAULT = 11, S_SOUT = 12;
    reg [2:0] dk;                                         // drain region (4 O, 5 R)
    reg [26:0] rsec_d, rsec_d2, rsec_d3; reg so_w;
    reg [3:0] rp;                                         // read pipe: a sector read is in flight
    // Local-memory return pin registers; advance data, mask, valid and sector identity together.
    reg [255:0] sr_data_q; reg [7:0] sr_dm_q;
    reg sr_rv_q;
    always @(posedge clk) begin sr_data_q <= sr_data; sr_dm_q <= sr_dm; end
    always @(posedge clk or negedge rst_n) if (!rst_n) sr_rv_q <= 1'b0; else sr_rv_q <= sr_rv;
    reg [255:0] rd_hold; reg [7:0] rd_dm_hold;
    // ---- STREAM 0 landing (top SW words of the local memory) and the op's stream flags
    localparam integer SW = 1 << SLB;
    localparam [LWB:0] SBASE = LW - SW;
    reg [20:0] scount; reg a_s, o_s; reg s_clr;
    reg s0v_q; reg [19:0] s0i_q; reg [31:0] s0d_q;
    always @(posedge clk) begin s0v_q <= s0_v; s0i_q <= s0_idx; s0d_q <= s0_data; end
    reg [20:0] etot; reg [20:0] ebeat; reg [LWB:0] o_lb; reg amr_q;
    always @(posedge clk) amr_q <= am_rdy;

    // RUN slot
    reg r_v, r_gop, r_cdone, r_as, r_os, r_ser; reg [15:0] r_no, r_ni; reg [LWB:0] r_rs, r_re;
    reg [23:0] r_lo [4:5]; reg [23:0] r_hi [4:5]; reg [LWB:0] r_lb [4:5]; reg r_rv [4:5]; reg [20:0] r_dsec [4:5];
    // DRAIN slot
    reg d_v, d_go, d_as, d_os, d_ser; reg [15:0] d_no, d_ni; reg [LWB:0] d_rs, d_re;
    reg [23:0] d_lo [4:5]; reg [23:0] d_hi [4:5]; reg [LWB:0] d_lb [4:5]; reg d_rv [4:5]; reg [20:0] d_dsec [4:5];
    reg [1:0] d_ph;                                       // 0 start, 1 lanes, 2 STREAM out
    // =================================================================================================================
    // WIDE LANES.  Lane b owns the sectors of bank b (sector mod 32) of every region.  Stage: per source region the
    // lane issues its sectors (LQ credits), the responses land in order into local bank b (a per-lane FIFO of the
    // local sector each request lands at); the same lane clears the dirty masks of its sink sectors.  Drain: per sink
    // region the lane reads its local sectors {data, dirty}, and writes each dirty one (word-masked) to VM.
    // =================================================================================================================
    localparam integer LSW = LWB - 3, QB = $clog2(LQ);
    reg [20:0] dsec [0:5];                                 // local sector - VM sector, per region
    reg wst_go, wdr_go;
    // flat lane outputs (SLICES = 0) / sliced (SLICES != 0)
    reg  [32*16-1:0] wrq_f; reg [32*280-1:0] wwq_f; reg [31:0] lsw_v_f; reg [32*(LWB-3)-1:0] lsw_sec_f;
    reg  [32*256-1:0] lsw_d_f; reg [31:0] ldc_v_f; reg [32*(LWB-3)-1:0] ldc_sec_f; reg [31:0] ldr_v_f;
    reg  [32*(LWB-3)-1:0] ldr_sec_f;
    wire wst_done, wdr_done, lane_ovf;
    reg [273:0] vr_unused;
    reg [31:0] wrq_cr_q, wwq_cr_q, wwq_done_q; reg [32*257-1:0] wrr_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wrq_cr_q <= '0; wwq_cr_q <= '0; wwq_done_q <= '0; wrr_q <= '0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr; end
    reg [32*256-1:0] ldr_d_q; reg [32*8-1:0] ldr_dm_q;
    reg [31:0] ldr_rv_q;
    always @(posedge clk) begin ldr_d_q <= ldr_d; ldr_dm_q <= ldr_dm; end
    always @(posedge clk or negedge rst_n) if (!rst_n) ldr_rv_q <= '0; else ldr_rv_q <= ldr_rv;
    // drain reads are VALID-driven: each lane keeps the VM sector of every read in flight (in order); a returned
    // {data, dirty} (ldr_rv, pin-flopped) pops it, whatever the memory latency
    reg [20:0] dq_s [0:31][0:LQ-1]; reg [QB-1:0] dq_h [0:31], dq_t [0:31]; reg [QB:0] dq_n [0:31];
    // per-lane state
    reg [2:0]  sg_r [0:31]; reg sg_on [0:31]; reg [20:0] sg_nx [0:31]; reg [20:0] sg_end [0:31];
    // landing FIFO: LQ queued at the VM + the accepted-not-landed pipe (VM core + relays): power of two >= 2 LQ + 32
    localparam integer LFB = $clog2(2 * LQ + 32), LFD = 1 << LFB;
    reg [QB:0] cr [0:31]; reg [LSW-1:0] lq [0:31][0:LFD-1]; reg [LFB-1:0] lqh [0:31], lqt [0:31]; reg [LFB:0] lqn [0:31];
    reg [5:0] wpend [0:31]; reg lane_ovf_f;
    reg [2:0]  cl_r [0:31]; reg cl_on [0:31]; reg [LSW-1:0] cl_nx [0:31]; reg [LSW-1:0] cl_end [0:31];
    reg [2:0]  dg_r [0:31]; reg dg_on [0:31]; reg [LSW-1:0] dg_nx [0:31]; reg [LSW-1:0] dg_end [0:31];
    reg [QB:0] wcr [0:31]; reg [31:0] dp1, dp2, dp3; reg [20:0] dp1_s [0:31]; reg [20:0] dp2_s [0:31]; reg [20:0] dp3_s [0:31];
    reg [31:0] wst_ldone, wdr_ldone;
    wire wst_done_f = &wst_ldone, wdr_done_f = &wdr_ldone;
    function automatic [20:0] first_of(input [20:0] lo_s, input integer b);
        first_of = lo_s + 21'((5'(b) - lo_s[4:0]) & 5'd31);
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wrq_f <= '0; wwq_f <= '0; lsw_v_f <= '0; ldc_v_f <= '0; ldr_v_f <= '0; dp1 <= '0; dp2 <= '0; dp3 <= '0;
            for (integer b = 0; b < 32; b = b + 1) begin dq_h[b] <= '0; dq_t[b] <= '0; dq_n[b] <= '0; end
            wst_ldone <= '1; wdr_ldone <= '1; lane_ovf_f <= 1'b0;
            for (integer b = 0; b < 32; b = b + 1) begin
                sg_r[b] <= 3'd7; sg_on[b] <= 1'b0; cl_r[b] <= 3'd7; cl_on[b] <= 1'b0; dg_r[b] <= 3'd7; dg_on[b] <= 1'b0;
                cr[b] <= (QB+1)'(LQ); wcr[b] <= (QB+1)'(LQ); lqh[b] <= '0; lqt[b] <= '0; lqn[b] <= '0; wpend[b] <= '0;
            end
        end else begin
            for (integer b = 0; b < 32; b = b + 1) begin : lane
                reg iss, land, dr_iss, wsend, wfree;
                reg [20:0] f;
                iss = 1'b0; land = 1'b0; dr_iss = 1'b0; wsend = 1'b0; wfree = 1'b0;
                wrq_f[b*16 + 15] <= 1'b0; lsw_v_f[b] <= 1'b0; ldc_v_f[b] <= 1'b0; ldr_v_f[b] <= 1'b0; wwq_f[b*280 + 279] <= 1'b0;
                // ---------------- stage: source region walk (regions 0..3)
                if (wst_go) begin sg_r[b] <= 3'd0; sg_on[b] <= 1'b0; cl_r[b] <= 3'd4; cl_on[b] <= 1'b0; wst_ldone[b] <= 1'b0; end
                else if (sg_r[b] < 3'd4) begin
                    if (!sg_on[b]) begin
                        f = first_of(21'(lo[sg_r[b]] >> 3), b);
                        if (rv[sg_r[b]] && f <= 21'(hi[sg_r[b]] >> 3)) begin
                            sg_nx[b] <= f; sg_end[b] <= 21'(hi[sg_r[b]] >> 3); sg_on[b] <= 1'b1;
                        end else sg_r[b] <= sg_r[b] + 3'd1;
                    end else if (cr[b] != 0) begin
                        iss = 1'b1;
                        wrq_f[b*16 +: 16] <= {1'b1, sg_nx[b][14:0]};
                        lq[b][lqt[b]] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        lqt[b] <= lqt[b] + 1'b1;
                        if (sg_nx[b] + 21'd32 > sg_end[b]) begin sg_on[b] <= 1'b0; sg_r[b] <= sg_r[b] + 3'd1; end
                        else sg_nx[b] <= sg_nx[b] + 21'd32;
                    end
                end
                // responses land in request order
                if (wrr_q[b*257 + 256]) begin
                    land = 1'b1;
                    lsw_v_f[b] <= 1'b1; lsw_sec_f[b*LSW +: LSW] <= (MUT_W == 1) ? lq[b][0] : lq[b][lqh[b]];
                    lsw_d_f[b*256 +: 256] <= wrr_q[b*257 +: 256];
                    lqh[b] <= lqh[b] + 1'b1;
                end
                lqn[b] <= lqn[b] + iss - land;
                if (lqn[b] == (LFB+1)'(LFD) && iss && !land) lane_ovf_f <= 1'b1;
                cr[b] <= cr[b] - iss + wrq_cr_q[b];
                // sink dirty-mask clears (regions 4, 5; the local span), one sector a lane an edge
                if (!wst_go && cl_r[b] < 3'd6) begin
                    if (!cl_on[b]) begin
                        f = first_of(21'(lb[cl_r[b]] >> 3), b);
                        if (rv[cl_r[b]] && f <= 21'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3)) begin
                            cl_nx[b] <= LSW'(f); cl_end[b] <= LSW'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3);
                            cl_on[b] <= 1'b1;
                        end else cl_r[b] <= cl_r[b] + 3'd1;
                    end else begin
                        ldc_v_f[b] <= 1'b1; ldc_sec_f[b*LSW +: LSW] <= cl_nx[b];
                        if (21'(cl_nx[b]) + 21'd32 > 21'(cl_end[b])) begin cl_on[b] <= 1'b0; cl_r[b] <= cl_r[b] + 3'd1; end
                        else cl_nx[b] <= cl_nx[b] + LSW'(32);
                    end
                end
                if (!wst_go && sg_r[b] >= 3'd4 && sg_r[b] != 3'd7 && cl_r[b] >= 3'd6 &&
                    ((lqn[b] + iss - land) == 0 && (cr[b] - iss + wrq_cr_q[b]) == (QB+1)'(LQ))) wst_ldone[b] <= 1'b1;
                // ---------------- drain: sink regions 4 (O, unless STREAM) and 5 (R)
                if (wdr_go) begin dg_r[b] <= 3'd4; dg_on[b] <= 1'b0; wdr_ldone[b] <= 1'b0; end
                else if (dg_r[b] < 3'd6) begin
                    if (!dg_on[b]) begin
                        f = first_of(21'(d_lb[dg_r[b]] >> 3), b);
                        if (d_rv[dg_r[b]] && !(dg_r[b] == 3'd4 && d_os) &&
                            f <= 21'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3)) begin
                            dg_nx[b] <= LSW'(f); dg_end[b] <= LSW'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3);
                            dg_on[b] <= 1'b1;
                        end else dg_r[b] <= dg_r[b] + 3'd1;
                    end else if (wcr[b] != 0) begin
                        if (!(MUT_W == 2 && 21'(dg_nx[b]) + 21'd32 > 21'(dg_end[b]))) begin
                            dr_iss = 1'b1;
                            ldr_v_f[b] <= 1'b1; ldr_sec_f[b*LSW +: LSW] <= dg_nx[b];
                            dq_s[b][dq_t[b]] <= 21'(dg_nx[b]) - d_dsec[dg_r[b]]; dq_t[b] <= dq_t[b] + 1'b1;
                        end
                        if (21'(dg_nx[b]) + 21'd32 > 21'(dg_end[b])) begin dg_on[b] <= 1'b0; dg_r[b] <= dg_r[b] + 3'd1; end
                        else dg_nx[b] <= dg_nx[b] + LSW'(32);
                    end
                end
                // read return: valid-driven (ldr_rv pin flop), the sector identity from the lane's in-flight FIFO
                begin : wpub
                    reg [7:0] mk; reg v3; reg [20:0] s3;
                    mk = MUT_DIRTY ? 8'hFF : ldr_dm_q[b*8 +: 8];
                    v3 = ldr_rv_q[b]; s3 = dq_s[b][dq_h[b]];
                    if (v3) dq_h[b] <= dq_h[b] + 1'b1;
                    dq_n[b] <= dq_n[b] + dr_iss - v3;
                    if (v3) begin
                        if (mk != 8'd0) begin
                            wsend = 1'b1;
                            wwq_f[b*280 +: 280] <= {1'b1, s3[14:0], ldr_d_q[b*256 +: 256], mk};
                        end else wfree = 1'b1;
                    end
                end
                wcr[b] <= wcr[b] - dr_iss + wfree + wwq_cr_q[b];
                wpend[b] <= wpend[b] + wsend - wwq_done_q[b];
                if (!wdr_go && dg_r[b] >= 3'd6 && dg_r[b] != 3'd7 && !dr_iss && (dq_n[b] - ldr_rv_q[b]) == 0 &&
                    (MUT_W == 3 || ((wpend[b] + wsend - wwq_done_q[b]) == 0 && (wcr[b] - dr_iss + wfree + wwq_cr_q[b]) == (QB+1)'(LQ)))) wdr_ldone[b] <= 1'b1;
            end
        end
    end
    // ---- SLICES (el1011-hbm-sfu, default off): four hardened 8-lane slices + a two-stage registered reduction hub
    generate if (SLICES != 0) begin : g_slices
        wire [3:0] s_wst, s_wdr, s_ovf;
        wire [6*24-1:0] lo_v, hi_v; wire [6*(LWB+1)-1:0] lb_v; wire [5:0] rv_v; wire [6*21-1:0] dsec_v;
        wire [2*24-1:0] dlo_v, dhi_v; wire [2*(LWB+1)-1:0] dlb_v; wire [1:0] drv_v; wire [2*21-1:0] ddsec_v;
        for (genvar q = 0; q < 6; q = q + 1) begin : g_rq
            assign lo_v[q*24 +: 24] = lo[q]; assign hi_v[q*24 +: 24] = hi[q]; assign lb_v[q*(LWB+1) +: LWB+1] = lb[q];
            assign rv_v[q] = rv[q]; assign dsec_v[q*21 +: 21] = dsec[q];
        end
        for (genvar q = 4; q < 6; q = q + 1) begin : g_dq
            assign dlo_v[(q-4)*24 +: 24] = d_lo[q]; assign dhi_v[(q-4)*24 +: 24] = d_hi[q];
            assign dlb_v[(q-4)*(LWB+1) +: LWB+1] = d_lb[q]; assign drv_v[q-4] = d_rv[q]; assign ddsec_v[(q-4)*21 +: 21] = d_dsec[q];
        end
        // GLUE PLACEMENT (owner 10-11 ~19:15): no hub.  The slices form a chain of edge-registered nearest-neighbour
        // links: descriptors / go forward (slice g's pin registers drive slice g+1's pin registers, one edge a hop),
        // done / overflow combine backward (slice g pin-flops slice g+1's combined flags, ANDs / ORs its own, registers
        // the result: two edges a hop).  Slice 0's combined flags are the whole unit's.
        localparam integer NSL = 4;
        wire [NSL:0] c_go_s, c_go_d, c_os;
        wire [6*24-1:0] c_lo_v [0:NSL]; wire [6*24-1:0] c_hi_v [0:NSL]; wire [6*(LWB+1)-1:0] c_lb_v [0:NSL];
        wire [5:0] c_rv_v [0:NSL]; wire [6*21-1:0] c_dsec_v [0:NSL]; wire [2*24-1:0] c_dlo_v [0:NSL];
        wire [2*24-1:0] c_dhi_v [0:NSL]; wire [2*(LWB+1)-1:0] c_dlb_v [0:NSL]; wire [1:0] c_drv_v [0:NSL];
        wire [2*21-1:0] c_ddsec_v [0:NSL];
        wire [NSL:0] dn_st, dn_dr, dn_ov;           // dn_*[g]: slice g's combined flags (g .. NSL-1); [NSL] = the chain end
        assign c_go_s[0] = wst_go; assign c_go_d[0] = wdr_go; assign c_os[0] = d_os;
        assign c_lo_v[0] = lo_v; assign c_hi_v[0] = hi_v; assign c_lb_v[0] = lb_v; assign c_rv_v[0] = rv_v;
        assign c_dsec_v[0] = dsec_v; assign c_dlo_v[0] = dlo_v; assign c_dhi_v[0] = dhi_v; assign c_dlb_v[0] = dlb_v;
        assign c_drv_v[0] = drv_v; assign c_ddsec_v[0] = ddsec_v;
`ifdef OT_CTLW_HEAD_EXT
        localparam integer NIN = 1;                 // the head tile holds slice 0; slices 1..3 are die-placed tiles
        assign c_wst_go = c_go_s[1]; assign c_wdr_go = c_go_d[1]; assign c_d_os = c_os[1];
        assign c_lo = c_lo_v[1]; assign c_hi = c_hi_v[1]; assign c_lb = c_lb_v[1]; assign c_rv = c_rv_v[1];
        assign c_dsec = c_dsec_v[1]; assign c_dlo = c_dlo_v[1]; assign c_dhi = c_dhi_v[1]; assign c_dlb = c_dlb_v[1];
        assign c_drv = c_drv_v[1]; assign c_ddsec = c_ddsec_v[1];
        assign dn_st[1] = c_wst_dn; assign dn_dr[1] = c_wdr_dn; assign dn_ov[1] = c_ovf;
`else
        localparam integer NIN = NSL;
        assign dn_st[NSL] = 1'b1; assign dn_dr[NSL] = 1'b1; assign dn_ov[NSL] = 1'b0;
`endif
        for (genvar g = 0; g < NIN; g = g + 1) begin : g_s
`ifdef OT_CTLW_SLICE_H   // el1013-hbm-qdq opt-in (default off): the slice as the physical cluster of four hard 2-lane leaves
            ot_hgi_su_ctlw_slice_h #(.SL(g), .NL(8), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(0)) u_slice (
`else
            ot_hgi_su_ctlw_slice #(.SL(g), .NL(8), .LWB(LWB), .LQ(LQ), .MUT_W(MUT_W), .MUT_DIRTY(MUT_DIRTY), .LQSRAM(SLICES >= 2 ? 1 : 0)) u_slice (
`endif
                .clk(clk), .rst_n(rst_n), .sl_i(2'(g)), .wst_go_i(c_go_s[g]), .wdr_go_i(c_go_d[g]),
                .lo_i(c_lo_v[g]), .hi_i(c_hi_v[g]), .lb_i(c_lb_v[g]), .rv_i(c_rv_v[g]), .dsec_i(c_dsec_v[g]),
                .d_lo_i(c_dlo_v[g]), .d_hi_i(c_dhi_v[g]), .d_lb_i(c_dlb_v[g]), .d_rv_i(c_drv_v[g]), .d_dsec_i(c_ddsec_v[g]), .d_os_i(c_os[g]),
                .wst_go_o(c_go_s[g+1]), .wdr_go_o(c_go_d[g+1]), .lo_o(c_lo_v[g+1]), .hi_o(c_hi_v[g+1]), .lb_o(c_lb_v[g+1]),
                .rv_o(c_rv_v[g+1]), .dsec_o(c_dsec_v[g+1]), .d_lo_o(c_dlo_v[g+1]), .d_hi_o(c_dhi_v[g+1]), .d_lb_o(c_dlb_v[g+1]),
                .d_rv_o(c_drv_v[g+1]), .d_dsec_o(c_ddsec_v[g+1]), .d_os_o(c_os[g+1]),
                .wst_dn_i(dn_st[g+1]), .wdr_dn_i(dn_dr[g+1]), .ovf_i(dn_ov[g+1]),
                .wrq(wrq[g*8*16 +: 8*16]), .wrq_cr(wrq_cr[g*8 +: 8]), .wrr(wrr[g*8*257 +: 8*257]),
                .wwq(wwq[g*8*280 +: 8*280]), .wwq_cr(wwq_cr[g*8 +: 8]), .wwq_done(wwq_done[g*8 +: 8]),
                .lsw_v(lsw_v[g*8 +: 8]), .lsw_sec(lsw_sec[g*8*(LWB-3) +: 8*(LWB-3)]), .lsw_d(lsw_d[g*8*256 +: 8*256]),
                .ldc_v(ldc_v[g*8 +: 8]), .ldc_sec(ldc_sec[g*8*(LWB-3) +: 8*(LWB-3)]),
                .ldr_v(ldr_v[g*8 +: 8]), .ldr_sec(ldr_sec[g*8*(LWB-3) +: 8*(LWB-3)]),
                .ldr_d(ldr_d[g*8*256 +: 8*256]), .ldr_dm(ldr_dm[g*8*8 +: 8*8]), .ldr_rv(ldr_rv[g*8 +: 8]),
                .wst_dn(dn_st[g]), .wdr_dn(dn_dr[g]), .ovf(dn_ov[g]));
        end
        // go blanking: a done seen within BL edges of its go belongs to the previous burst.  Worst path, slice 3: go
        // ctlw -> s0 .. s3 pins (4), lane done (1), s3 combine (1), back s2 / s1 / s0 (2 each: 6), the capture here (1)
        // = 13 (the single-slice hub path was 4 with BL 6): BL = 15
`ifdef OT_CTLW_SLICE_H
        // slice_h: 3 forward edges a hop and 4 back (N-face flag flop, leaf pin flop, leaf flag, AND4): go -> s3 f0 (10),
        // fm (11), leaf pin flop (12), lane done (13), leaf flag (14), s3 AND4 (15), back s2 / s1 / s0 (4 each: 27),
        // the capture here (28): BL = 30
        localparam integer BL = 30;
        reg h_wst, h_wdr, h_ovf; reg [4:0] bl_st, bl_dr;
`else
        localparam integer BL = 15;
        reg h_wst, h_wdr, h_ovf; reg [3:0] bl_st, bl_dr;
`endif
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin h_wst <= 1'b1; h_wdr <= 1'b1; h_ovf <= 1'b0; bl_st <= '0; bl_dr <= '0; end
            else begin
                h_wst <= dn_st[0]; h_wdr <= dn_dr[0]; h_ovf <= dn_ov[0];
`ifdef OT_CTLW_SLICE_H
                bl_st <= wst_go ? 5'(BL) : (bl_st != 0 ? bl_st - 5'd1 : 5'd0);
                bl_dr <= wdr_go ? 5'(BL) : (bl_dr != 0 ? bl_dr - 5'd1 : 5'd0);
`else
                bl_st <= wst_go ? 4'(BL) : (bl_st != 0 ? bl_st - 4'd1 : 4'd0);
                bl_dr <= wdr_go ? 4'(BL) : (bl_dr != 0 ? bl_dr - 4'd1 : 4'd0);
`endif
            end
        assign wst_done = h_wst && bl_st == 0 && !wst_go;
        assign wdr_done = h_wdr && bl_dr == 0 && !wdr_go;
        assign lane_ovf = h_ovf;
    end else begin : g_flat
        assign wrq = wrq_f; assign wwq = wwq_f; assign lsw_v = lsw_v_f; assign lsw_sec = lsw_sec_f; assign lsw_d = lsw_d_f;
        assign ldc_v = ldc_v_f; assign ldc_sec = ldc_sec_f; assign ldr_v = ldr_v_f; assign ldr_sec = ldr_sec_f;
        assign wst_done = wst_done_f; assign wdr_done = wdr_done_f; assign lane_ovf = lane_ovf_f;
    end endgenerate
    // =================================================================================================================
    // RECORD PIPELINE (OVL): three slots.  FRONT: decode -> extents (pipelined multiply) -> local allocation (a ring
    // over [0, SBASE): a record's regions sit after the previous record's, wrapping to 0, never over a live record's)
    // -> placement -> wait until no source region overlaps the VM sink span of an older record not yet drained (its
    // results must be read from VM after they land there) -> wide stage.  RUN: the vec (go when ready) on the staged
    // record.  DRAIN: the wide drain (or the STREAM-out to ARGMAX), then the in-order retire pulse (su_ret).  A FRONT
    // record stages while an older one runs or drains; RUN starts while an older one drains (its sinks are other local
    // words; its drain follows the older drain, so VM write order is program order).  STREAM records (A from STREAM 0,
    // O to ARGMAX) run alone (the landing region and its count belong to one record).
    // =================================================================================================================
    reg ready_q, idle_q, vfault_q, rg_q, wg_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; rg_q <= 1'b0; wg_q <= 1'b0; end
        else begin ready_q <= ready; idle_q <= idle; vfault_q <= vfault; rg_q <= rg_gnt && rg_req; wg_q <= wg_gnt && wg_req; end
    end
    reg vf_seen; reg [1:0] idle_ph;
    reg [669:0] fw;                                       // FRONT: the relocated op word being built
    reg [LWB:0] f_rs, ap; reg [LWB+1:0] fsize; reg f_ser;
    // census (bench): which slots are busy this edge
    wire a_span = (st == S_SPAN || st == S_MUL || st == S_NEXTR || st == S_STAGE);
    wire a_stage = (st == S_STW);
    wire a_run = r_v && !r_cdone;
    wire a_drain = d_v;
    // live-range / hazard predicates for the FRONT record
    function automatic ovl_r(input [LWB:0] a0, input [LWB:0] a1, input [LWB:0] b0, input [LWB:0] b1);
        ovl_r = (a0 < b1) && (b0 < a1);
    endfunction
    function automatic ovl_v(input [23:0] a0, input [23:0] a1, input [23:0] b0, input [23:0] b1);
        ovl_v = (a0 <= b1) && (b0 <= a1);                 // inclusive word spans
    endfunction
    wire [LWB:0] fb_try = ({1'b0, ap} + fsize <= {2'b0, SBASE}) ? ap : '0;
    wire alloc_ok = !(r_v && ovl_r(fb_try, LWB'(fb_try + fsize), r_rs, r_re)) &&
                    !(d_v && ovl_r(fb_try, LWB'(fb_try + fsize), d_rs, d_re)) &&
                    ({1'b0, fb_try} + fsize <= {2'b0, SBASE}) &&
                    (!f_ser || (!r_v && !d_v)) && !(r_v && r_ser) && !(d_v && d_ser) && (OVL != 0 || (!r_v && !d_v));
    reg haz;
    always @* begin
        haz = 1'b0;
        for (integer q = 0; q < 4; q = q + 1) if (rv[q]) begin
            for (integer k = 4; k < 6; k = k + 1) begin
                if (r_v && r_rv[k] && !(k == 4 && r_os) && ovl_v(lo[q], hi[q], r_lo[k], r_hi[k])) haz = 1'b1;
                if (d_v && d_rv[k] && !(k == 4 && d_os) && ovl_v(lo[q], hi[q], d_lo[k], d_hi[k])) haz = 1'b1;
            end
        end
        if (MUT_W == 4) haz = 1'b0;
    end
    wire [LWB:0] lbk = alloc + (LWB+1)'((lo[rk][7:0] - alloc[7:0]) & 8'hFF);   // lb == lo (mod 256 words): bank-aligned
    localparam [3:0] S_WAITA = 4'd13, S_RDY = 4'd14;
    integer k2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; op_rdy_r <= 1'b1; su_idle_r <= 1'b1; su_fault_r <= 1'b0; go <= 1'b0; vmq <= 338'd0; su_ret <= 1'b0;
            sl_v <= 1'b0; sw_v <= 1'b0; dc_v <= 1'b0; sr_v <= 1'b0; rp <= 4'd0; wst_go <= 1'b0; wdr_go <= 1'b0;
            outst <= 3'd0; q_h <= 2'd0; q_t <= 2'd0; vf_seen <= 1'b0; scount <= 21'd0; s_clr <= 1'b0; am_stream <= 523'd0;
            r_v <= 1'b0; r_gop <= 1'b0; r_cdone <= 1'b0; d_v <= 1'b0; d_go <= 1'b0; ap <= '0; r_ser <= 1'b0; d_ser <= 1'b0;
            rg_req <= 1'b0; wg_req <= 1'b0;
        end else begin
            vmq[337] <= 1'b0; su_fault_r <= 1'b0; am_stream[0] <= 1'b0; am_stream[1] <= 1'b0; su_ret <= 1'b0;
            sl_v <= s0v_q && s0i_q < SW; sl_addr <= SBASE + s0i_q; sl_data <= s0d_q;
            sw_v <= 1'b0; dc_v <= 1'b0; sr_v <= 1'b0; wst_go <= 1'b0; wdr_go <= 1'b0; go <= 1'b0;
            if ((s0v_q && s0i_q >= SW) || lane_ovf) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (s_clr) scount <= {20'd0, s0v_q}; else if (s0v_q) scount <= scount + 21'd1;
            s_clr <= 1'b0;
            if (vfault_q && r_v && !r_gop) vf_seen <= 1'b1;
            su_idle_r <= (st == S_IDLE) && !r_v && !d_v;
            // ------------------------------------------------------------------ FRONT
            case (st)
                S_IDLE: begin
                    if (op_v && op_rdy_r) begin
                        w <= op_w; fw <= op_w; op_rdy_r <= 1'b0; rk <= 3'd0; fsize <= '0;
                        a_s <= strm[0]; o_s <= strm[1]; f_ser <= strm[0] | strm[1]; st <= S_SPAN;
                        for (k2 = 0; k2 < 6; k2 = k2 + 1) rv[k2] <= 1'b0;
                    end
                end
                S_SPAN: begin                                       // region rk: used? span start
                    rv[rk] <= used_k && !(rk == 3'd0 && a_s);
                    if (rk == 3'd0 && a_s) begin                    // A = STREAM: rows of ni, element o ni + i = idx
                        fw[40 +: 24] <= SBASE; fw[64 +: 24] <= {8'd0, ni}; fw[88 +: 24] <= 24'd1; rk <= rk + 3'd1;
                    end else if (rk == 3'd4 && o_s && a_s && red == 2'd0) begin
                        // O = STREAM over A = STREAM, element-wise: O aliases the stream landing region
                        fw[382 +: 24] <= SBASE; fw[406 +: 24] <= {8'd0, ni}; fw[430 +: 24] <= 24'd1;
                        lb[4] <= SBASE; rv[4] <= 1'b0; rk <= rk + 3'd1;
                    end else if (rk == 3'd4 && o_s) begin           // O = STREAM: a contiguous local region, no drain
                        fw[406 +: 24] <= {8'd0, ni}; fw[430 +: 24] <= 24'd1; w[406 +: 24] <= {8'd0, ni}; w[430 +: 24] <= 24'd1;
                        w[382 +: 24] <= 24'd0; fw[382 +: 24] <= 24'd0; lo[4] <= 24'd0; macc <= 40'd0; mbit <= 5'd0;
                        mph <= 2'd0; rv[4] <= 1'b1; st <= S_MUL;
                    end else if (!used_k) begin
                        if (rk == 3'd5) st <= S_WAITA; else rk <= rk + 3'd1;
                    end else begin
                        lo[rk] <= base_k; macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL;
                    end
                    if (rk == 3'd0 && (aind != 2'd0 || w[32 +: 8] != 8'd0)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                end
                S_MUL: begin                                        // macc = (nr - 1) so + (ni - 1) si, PIPELINED:
                    // edge 0 operand flops, edge 1 four 8 x 24 partial products, edge 2 their sum, edge 3 the extent
                    if (mph == 2'd0) begin
                        ma <= nr_k - 16'd1; mb <= so_k; mc <= ni_k - 16'd1; md <= si_k; mph <= 2'd1; mbit <= 5'd0;
                    end else if (mph == 2'd1) begin
                        if (mbit == 5'd0) begin
                            pp0 <= ma[7:0] * mb; pp1 <= ma[15:8] * mb; pp2 <= mc[7:0] * md; pp3 <= mc[15:8] * md;
                            mbit <= 5'd1;
                        end else begin
                            macc <= {8'd0, pp0} + {pp1, 8'd0} + {8'd0, pp2} + {pp3, 8'd0}; mph <= 2'd2;
                        end
                    end else begin
                        // c_pair reads A[e ^ 1]: widen A to whole pairs
                        if (rk == 3'd0 && cpair) begin
                            lo[0] <= base_k & ~24'd1; hi[0] <= (base_k + macc[23:0]) | 24'd1;
                            fsize <= fsize + (LWB+2)'(((base_k + macc[23:0]) | 24'd1) - (base_k & ~24'd1)) + 265;
                        end else begin
                            hi[rk] <= base_k + macc[23:0];
                            fsize <= fsize + (LWB+2)'(base_k + macc[23:0] - lo[rk]) + 265;   // span + guard 8 + align 256
                        end
                        if (rk == 3'd5) st <= S_WAITA; else begin rk <= rk + 3'd1; st <= S_SPAN; end
                    end
                end
                S_WAITA: if (alloc_ok) begin                         // a free local range for the whole record
                    alloc <= fb_try; f_rs <= fb_try; rk <= 3'd0; st <= S_NEXTR;
                end
                S_NEXTR: begin                                      // place region rk, relocate its base
                    if (rv[rk]) begin
                        lb[rk] <= lbk;
                        alloc <= lbk + (hi[rk] - lo[rk]) + 1 + 8;
                        if (lbk + (hi[rk] - lo[rk]) + 1 > SBASE) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        case (rk)
                            3'd0: fw[40 +: 24]  <= w[40 +: 24]  - lo[0] + lbk;
                            3'd1: fw[138 +: 24] <= w[138 +: 24] - lo[1] + lbk;
                            3'd2: fw[211 +: 24] <= w[211 +: 24] - lo[2] + lbk;
                            3'd3: fw[284 +: 24] <= w[284 +: 24] - lo[3] + lbk;
                            3'd4: fw[382 +: 24] <= w[382 +: 24] - lo[4] + lbk;
                            default: fw[484 +: 24] <= w[484 +: 24] - lo[5] + lbk;
                        endcase
                    end
                    if (!(rv[rk] && lbk + (hi[rk] - lo[rk]) + 1 > SBASE)) begin
                        if (rk == 3'd5) begin rk <= 3'd0; st <= S_STAGE; end
                        else rk <= rk + 3'd1;
                    end
                end
                S_STAGE: begin                                      // sources clear of every older undrained sink?
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) dsec[k2] <= 21'((lb[k2] >> 3) - (lo[k2] >> 3));
                    if (!haz) rg_req <= 1'b1;                       // the read lane group for the stage burst
                    if (!haz && rg_req && rg_q) begin st <= S_STW; wst_go <= 1'b1; ap <= alloc; end
                end
                S_STW: if (!wst_go && wst_done) begin st <= S_RDY; rg_req <= 1'b0; end
                S_RDY: if (!r_v) begin                              // into RUN
                    r_v <= 1'b1; r_gop <= 1'b1; r_cdone <= 1'b0; wl <= fw; r_as <= a_s; r_os <= o_s; r_ser <= f_ser;
                    r_no <= no; r_ni <= ni; r_rs <= f_rs; r_re <= ap;
                    for (k2 = 4; k2 < 6; k2 = k2 + 1) begin
                        r_lo[k2] <= lo[k2]; r_hi[k2] <= hi[k2]; r_lb[k2] <= lb[k2]; r_rv[k2] <= rv[k2]; r_dsec[k2] <= dsec[k2];
                    end
                    op_rdy_r <= 1'b1; st <= S_IDLE;
                end
                S_FAULT: ;                                           // sticky (the adapter halts)
                default: st <= S_FAULT;
            endcase
            // ------------------------------------------------------------------ RUN
            if (r_v && st != S_FAULT) begin
                if (r_gop) begin
                    if (ready_q && (!r_as || scount >= {5'd0, r_no} * {5'd0, r_ni})) begin
                        go <= 1'b1; r_gop <= 1'b0; idle_ph <= 2'd0; vf_seen <= 1'b0;
                    end
                end else if (!r_cdone) begin
                    if (idle_ph != 2'd3) idle_ph <= idle_ph + 2'd1;
                    else if (idle_q) begin
                        if (vf_seen || vfault_q) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        else r_cdone <= 1'b1;
                    end
                end else if (!d_v) begin                            // into DRAIN
                    d_v <= 1'b1; d_ph <= 2'd0; d_as <= r_as; d_os <= r_os; d_ser <= r_ser; d_no <= r_no; d_ni <= r_ni;
                    d_rs <= r_rs; d_re <= r_re;
                    for (k2 = 4; k2 < 6; k2 = k2 + 1) begin
                        d_lo[k2] <= r_lo[k2]; d_hi[k2] <= r_hi[k2]; d_lb[k2] <= r_lb[k2]; d_rv[k2] <= r_rv[k2]; d_dsec[k2] <= r_dsec[k2];
                    end
                    r_v <= 1'b0; r_ser <= 1'b0;
                end
            end
            // ------------------------------------------------------------------ DRAIN
            if (d_v && st != S_FAULT) begin
                case (d_ph)
                    2'd0: if ((d_rv[4] && !d_os) || d_rv[5]) begin
                              wg_req <= 1'b1;                       // the write lane group for the drain burst
                              if (wg_req && wg_q) begin wdr_go <= 1'b1; d_ph <= 2'd1; end
                          end
                          else if (d_os) begin etot <= {5'd0, d_no} * {5'd0, d_ni}; ebeat <= 21'd0; o_lb <= d_lb[4]; rp <= 4'd0;
                                               so_w <= 1'b0; d_ph <= 2'd2; end
                          else begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                    2'd1: if (!wdr_go && wdr_done) begin
                              wg_req <= 1'b0;
                              if (d_os) begin etot <= {5'd0, d_no} * {5'd0, d_ni}; ebeat <= 21'd0; o_lb <= d_lb[4]; rp <= 4'd0;
                                              so_w <= 1'b0; d_ph <= 2'd2; end
                              else begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                          end
                    default: begin                                  // STREAM out: 8 elements a beat, in element order
                        // one sector read in flight; its data is taken on the memory's valid (any latency)
                        if (amr_q && !so_w) begin
                            sr_v <= 1'b1; sr_sec <= (o_lb + ebeat) >> 3; so_w <= 1'b1;
                        end else if (so_w && sr_rv_q) begin
                            begin : so
                                reg [7:0] mk; integer q;
                                for (q = 0; q < 8; q = q + 1) mk[q] = (ebeat + q < etot);
                                am_stream <= {1'b0, 256'd0, sr_data_q, mk, (ebeat + 21'd8 >= etot), 1'b1};
                            end
                            so_w <= 1'b0;
                            if (ebeat + 21'd8 >= etot) begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                            else ebeat <= ebeat + 21'd8;
                        end
                    end
                endcase
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Local operand memory with the 32 wide lanes (behavioural; the banked-macro build is sub-agent d's ot_hgi_su_lmem
// successor, requirement in hgi-1010.log "b -> d"): ot_hgi_su_lmem's ports plus, per lane b (local bank b): a stage
// sector write, a dirty-mask clear and a drain sector read {data, dirty mask} one edge later.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_lmemw #(
    parameter integer N = 16, LWB = 17, AW = 24, NR = N / 8,
    parameter integer RLAT = 1,           // bench: drain / STREAM-out read latency (edges); the controller is valid-driven
    parameter integer MUT_RV = 0          // bench mutants: 1 the read valid one edge EARLY, 2 one edge LATE (vs its data)
) (
    input  wire              clk,
    input  wire [N-1:0]      vi_re,
    input  wire [N*AW-1:0]   vi_addr,
    output reg  [N*32-1:0]   vi_q,
    input  wire [4*N-1:0]    rd_re,
    input  wire [4*N*AW-1:0] rd_addr,
    output reg  [4*N*32-1:0] rd_q,
    input  wire [N-1:0]      vm_we,
    input  wire [N*AW-1:0]   vm_waddr,
    input  wire [N*32-1:0]   vm_wdata,
    input  wire [NR-1:0]     res_we,
    input  wire [NR*AW-1:0]  res_addr,
    input  wire [NR*32-1:0]  res_data,
    input  wire              sl_v,
    input  wire [LWB-1:0]    sl_addr,
    input  wire [31:0]       sl_data,
    input  wire              sr_v,
    input  wire [LWB-4:0]    sr_sec,
    output reg  [255:0]      sr_data,
    output reg  [7:0]        sr_dm,
    input  wire [31:0]       lsw_v,
    input  wire [32*(LWB-3)-1:0] lsw_sec,
    input  wire [32*256-1:0] lsw_d,
    input  wire [31:0]       ldc_v,
    input  wire [32*(LWB-3)-1:0] ldc_sec,
    input  wire [31:0]       ldr_v,
    input  wire [32*(LWB-3)-1:0] ldr_sec,
    output reg  [32*256-1:0] ldr_d,
    output reg  [32*8-1:0]   ldr_dm,
    output wire [31:0]       ldr_rv,
    output wire              sr_rv,
    output reg               bank_err          // a lane addressed another bank (controller bug): sticky
);
    localparam integer LW = 1 << LWB, LS = LWB - 3;
    reg [31:0] lm [0:LW-1];
    // read data leaves after RLAT edges: ldr_d / sr_data are the last stage of a delay line, valids alongside
    reg [32*256-1:0] ld_p [1:4]; reg [32*8-1:0] lm_p [1:4]; reg [31:0] lv_p [0:5]; reg [255:0] sd_p [1:4]; reg [7:0] sm_p [1:4]; reg sv_p [0:5];
    reg [32*256-1:0] ld0; reg [32*8-1:0] lm0; reg [255:0] sd0; reg [7:0] sm0;
    always @* begin lv_p[0] = ldr_v; sv_p[0] = sr_v; end
    always @(posedge clk) begin
        lv_p[1] <= lv_p[0]; sv_p[1] <= sv_p[0];
        for (integer q = 2; q <= 4; q = q + 1) begin ld_p[q] <= ld_p[q-1]; lm_p[q] <= lm_p[q-1]; sd_p[q] <= sd_p[q-1]; sm_p[q] <= sm_p[q-1]; end
        for (integer q = 2; q <= 5; q = q + 1) begin lv_p[q] <= lv_p[q-1]; sv_p[q] <= sv_p[q-1]; end
    end
    always @* begin ldr_d = ld_p[RLAT]; ldr_dm = lm_p[RLAT]; sr_data = sd_p[RLAT]; sr_dm = sm_p[RLAT]; end
    localparam integer VL = (MUT_RV == 1) ? RLAT - 1 : (MUT_RV == 2) ? RLAT + 1 : RLAT;
    assign ldr_rv = lv_p[VL]; assign sr_rv = sv_p[VL];
    reg [7:0]  dm [0:LW/8-1];
    integer l, s2, q;
    initial bank_err = 1'b0;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) begin
            if (vi_re[l]) vi_q[32*l +: 32] <= lm[vi_addr[l*AW +: AW] & (LW - 1)];
            for (s2 = 0; s2 < 4; s2 = s2 + 1)
                if (rd_re[4*l + s2]) rd_q[(4*l + s2)*32 +: 32] <= lm[rd_addr[(4*l + s2)*AW +: AW] & (LW - 1)];
        end
        if (sr_v) begin for (q = 0; q < 8; q = q + 1) sd0[32*q +: 32] = lm[{sr_sec, 3'b000} + q]; sm0 = dm[sr_sec]; end
        sd_p[1] <= sd0; sm_p[1] <= sm0;
        for (l = 0; l < 32; l = l + 1) begin
            if (ldr_v[l]) begin
                for (q = 0; q < 8; q = q + 1) ld0[l*256 + 32*q +: 32] = lm[{ldr_sec[l*LS +: LS], 3'b000} + q];
                lm0[l*8 +: 8] = dm[ldr_sec[l*LS +: LS]];
            end
            ld_p[1][l*256 +: 256] <= ld0[l*256 +: 256]; lm_p[1][l*8 +: 8] <= lm0[l*8 +: 8];
            if ((lsw_v[l] && lsw_sec[l*LS +: 5] != 5'(l)) || (ldc_v[l] && ldc_sec[l*LS +: 5] != 5'(l)) ||
                (ldr_v[l] && ldr_sec[l*LS +: 5] != 5'(l))) bank_err <= 1'b1;
        end
        if (sl_v) lm[sl_addr] <= sl_data;
        for (l = 0; l < 32; l = l + 1) begin
            if (lsw_v[l]) for (q = 0; q < 8; q = q + 1) lm[{lsw_sec[l*LS +: LS], 3'b000} + q] <= lsw_d[l*256 + 32*q +: 32];
            if (ldc_v[l]) dm[ldc_sec[l*LS +: LS]] <= 8'd0;
        end
        for (l = 0; l < N; l = l + 1)
            if (vm_we[l]) begin
                lm[vm_waddr[l*AW +: AW] & (LW - 1)] <= vm_wdata[32*l +: 32];
                dm[(vm_waddr[l*AW +: AW] & (LW - 1)) >> 3][vm_waddr[l*AW +: 3]] <= 1'b1;
            end
        for (l = 0; l < NR; l = l + 1)
            if (res_we[l]) begin
                lm[res_addr[l*AW +: AW] & (LW - 1)] <= res_data[32*l +: 32];
                dm[(res_addr[l*AW +: AW] & (LW - 1)) >> 3][res_addr[l*AW +: 3]] <= 1'b1;
            end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 stream-unit / SFU / FUSED die-body controller, PRODUCTION form (hgi-unitrate 2026-10-10, lead decision: one
// production SU = the wide engine on sub-agent d's lane-local lmem; ot_hgi_su_unit WIDE = 2).
//   * layout: d's dense relayout (ot_hgi_su_ctl): every region at an N-aligned base, element (o, i) at base + o L + i,
//     broadcast operands replicated, groups G0 A, G1 B, G2 C (+ A's copy for c_pair), G3 D, GO O, GR R;
//   * span: (nr - 1) L + nw by a 3-edge pipelined multiply (4 partial products), not a bit-serial walk;
//   * stage: the VM wide read lanes (lane b <-> VM bank b, LQ credits) and NS = 32 lmem sector lanes.  A BEAT is the
//     consecutive VM sectors of one row (up to 32: distinct VM banks and, the row being contiguous in the dense layout,
//     256 consecutive local words = distinct lmem banks for N >= 256).  Responses land per lane in order; a landing
//     scheduler writes one beat an edge (oldest first), so an edge's sector writes never collide.  Broadcast (inner
//     stride 0) rows: one VM read, then the replicate engine writes the row's L words, 32 sectors an edge.  Any other
//     inner stride: one element an edge.
//   * drain: the shape walk of O / R (no dirty bits): a beat = up to 32 VM sectors of a contiguous row (one lmem sector
//     read each, word-masked VM write on that sector's lane), valid-driven on the lmem's sr_rv; other shapes one
//     element an edge;
//   * record pipeline: FRONT (decode, span, place, stage) | RUN (the vec) | DRAIN, in-order retire (ot_hgi_su_record
//     PIPED).  A FRONT record allocates per group after the previous record (ring; never over a live RUN / DRAIN
//     record's range), and stages a source only once no older undrained record's sink overlaps it in VM.
//     STREAM records (A = STREAM 0, O = STREAM to ARGMAX) run alone.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_ctlx #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer MUT_DIRTY = 0,      // mutant: drain whole sectors (writes words outside the op's shape)
    parameter integer LG1 = LWB, LG2 = LWB, LG3 = LWB, LGO = LWB, RWB = 6,
    parameter integer LQ = 8,             // VM lane credits (size to the lane-group round trip)
    parameter integer DF = 16,            // per-lane landed-but-unwritten stage sectors
    parameter integer OVL = 1,            // 1: record pipeline; 0: one record at a time
    parameter integer MUT_X = 0           // mutants: 1 a beat's landing ignores its row mask, 2 no source / live-sink
                                          //   hazard, 3 the replicate engine writes one sector short
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
    input  wire          s0_v,
    input  wire [19:0]   s0_idx,
    input  wire [31:0]   s0_data,
    output reg  [522:0]  am_stream,
    input  wire          am_rdy,
    output reg           go,
    input  wire          ready,
    input  wire          idle,
    input  wire          vfault,
    output reg  [669:0]  wl,
    output reg           sl_v,
    output reg  [LWB-1:0] sl_addr,
    output reg  [31:0]   sl_data,
    // lmem sector lanes (NS = 32)
    output reg  [31:0]       sw_v,
    output reg  [32*256-1:0] sw_data,
    output reg  [3:0]        sw_g,
    output reg  [32*LWB-1:0] sw_addr,
    output reg  [32*8-1:0]   sw_mask,
    output reg  [31:0]       sr_v,
    output reg  [1:0]        sr_g,
    output reg  [32*LWB-1:0] sr_addr,
    input  wire [32*256-1:0] sr_data,
    input  wire [31:0]       sr_rv,
    output reg  [3:0]        use_p,
    input  wire              sl_pend,
    output wire              a_str,
    input  wire              cfault,
    // VM wide lane group ports
    output reg  [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output reg  [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt
);
    localparam integer AW = 24, LW = 1 << LWB, QB = $clog2(LQ), DB = $clog2(DF);
    // sectors a beat: 8 x BL consecutive local words must fall on distinct banks (d's lmem rule) -> BL = min(32, N / 8)
    generate if ((1 << QB) != LQ || (1 << DB) != DF) begin : g_pow2
        ot_hgi_su_ctlx_LQ_and_DF_must_be_powers_of_two u_trap ();
    end endgenerate
    localparam integer BL = (N / 8 < 32) ? ((N / 8 < 1) ? 1 : N / 8) : 32;
    // ---- the record adapter (decode), PIPED: retire on su_ret
    wire op_v; reg op_rdy_r; wire [669:0] op_w; reg su_idle_r, su_fault_r, su_ret;
    wire [1:0] strm;
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(!GLU), .PAYLOAD_RESET(PAYLOAD_RESET), .PIPED(1)) u_rec (.clk(clk),
        .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .drained(), .op_strm(strm), .lg_v(1'b0), .lg_rdy(),
        .lg_w(670'd0), .op_v(op_v), .op_rdy(op_rdy_r), .op_w(op_w), .su_idle(su_idle_r), .su_fault(su_fault_r), .su_ret(su_ret));
    // ---- FRONT: the op word fields
    reg [669:0] w, fw;
    wire [15:0] no = w[0 +: 16], ni = w[16 +: 16];
    wire [1:0]  aind = w[136 +: 2], dst = w[380 +: 2], red = w[478 +: 2];
    wire        bhalf = w[210], cpair = w[283], redwhole = w[481], redtree = w[482];
    wire [2:0]  m1 = w[360 +: 3], qm = w[365 +: 3], ad = w[368 +: 3], e1 = w[374 +: 3];
    wire [1:0]  m2 = w[363 +: 2], e2 = w[377 +: 2];
    wire use_b = (m1 == 3'd1) || (m1 == 3'd4) || (m1 == 3'd6) || (ad == 3'd3) || (e2 == 2'd1);
    wire use_c = !cpair && ((m2 == 2'd1) || (qm != 3'd0) || (ad == 3'd1) || (ad == 3'd2) || (e1 == 3'd1) || (e1 == 3'd2));
    wire use_d = (qm != 3'd0) || (ad == 3'd5);
    reg [2:0] rk;
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
        ni_k = (rk == 3'd5) ? 16'd1 : (hf_k ? ((ni + 16'd1) >> 1) : ni);
    end
    // ---- the dense layout (d's ot_hgi_su_ctl, unchanged rule)
    function automatic [LWB:0] p2c(input [15:0] x);
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
    reg [LWB:0] l_full_q, l_half_q; reg [31:0] nn_q;
    wire [LWB:0] L_k = (rk == 3'd5) ? 1 : hf_k ? l_half_q : l_full_q;
    // ---- FRONT per-region state
    reg [23:0] lo [0:5]; reg [23:0] vhi [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5]; reg [LWB:0] Lr [0:5];
    reg [23:0] sor [0:5], sir [0:5]; reg [15:0] nrr [0:5], nir [0:5]; reg [LWB:0] lsz [0:5];
    reg a_s, o_s, f_ser;
    // pipelined multiply: lsz = (nr - 1) L + nw ; VM extent vhi = lo + (nr - 1) so + (nw - 1) si
    reg [15:0] ma; reg [LWB:0] mb; reg [23:0] mc, md; reg [15:0] me;
    reg [39:0] pa0, pa1, pc0, pc1, pe0, pe1; reg [1:0] mph;
    // ---- groups: G0 A, G1 B, G2 C, G3 D, G4 O, G5 R; per group the FRONT record's need, the ring pointer, live ranges
    localparam [LWB:0] SBASE = LW - (1 << SLB);
    function automatic [LWB:0] gsz(input [2:0] g);
        case (g) 3'd0: gsz = SBASE; 3'd1: gsz = 1 << LG1; 3'd2: gsz = 1 << LG2; 3'd3: gsz = 1 << LG3; 3'd4: gsz = 1 << LGO;
                 default: gsz = 1 << RWB; endcase
    endfunction
    function automatic [2:0] grp(input [2:0] r); grp = r; endfunction        // region k lives in group k
    reg [LWB+1:0] need [0:5]; reg [LWB:0] gap [0:5];                         // the FRONT record's need, ring pointers
    reg [LWB:0] gbase [0:5]; reg [LWB:0] galloc [0:5];                       // FRONT placement base / cursor per group
    reg [LWB:0] r_gs [0:5], r_ge [0:5], d_gs [0:5], d_ge [0:5];              // RUN / DRAIN live ranges per group
    // ---- RUN / DRAIN slots
    reg r_v, r_gop, r_cdone, r_as, r_os, r_ser; reg [15:0] r_no, r_ni; reg [31:0] r_nn;
    reg d_v, d_as, d_os, d_ser; reg [15:0] d_no, d_ni; reg [2:0] d_ph; reg [2:0] dk;
    reg [23:0] r_lo [4:5], r_vhi [4:5], r_so [4:5], r_si [4:5]; reg [15:0] r_nr [4:5], r_nw [4:5]; reg [LWB:0] r_lb [4:5], r_L [4:5]; reg r_rv [4:5];
    reg [23:0] d_lo [4:5], d_vhi [4:5], d_so [4:5], d_si [4:5]; reg [15:0] d_nr [4:5], d_nw [4:5]; reg [LWB:0] d_lb [4:5], d_L [4:5]; reg d_rv [4:5];
    // ---- STREAM 0 landing and the stream flags
    localparam integer SW = 1 << SLB;
    reg [20:0] scount; reg s_clr;
    assign a_str = r_v ? r_as : a_s;
    reg s0v_q; reg [19:0] s0i_q; reg [31:0] s0d_q;
    always @(posedge clk) begin s0v_q <= s0_v; s0i_q <= s0_idx; s0d_q <= s0_data; end
    reg [20:0] etot, ebeat; reg [LWB:0] o_lb; reg amr_q, so_w;
    always @(posedge clk) amr_q <= am_rdy;
    reg ready_q, idle_q, vfault_q, rg_q, wg_q, cfault_q;
    reg [255:0] sr0_q; reg [31:0] sr_rv_q; reg [32*256-1:0] sr_d_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; rg_q <= 1'b0; wg_q <= 1'b0; cfault_q <= 1'b0; sr_rv_q <= '0; end
        else begin ready_q <= ready; idle_q <= idle; vfault_q <= vfault; rg_q <= rg_gnt && rg_req; wg_q <= wg_gnt && wg_req;
                   cfault_q <= cfault; sr_rv_q <= sr_rv; end
    end
    always @(posedge clk) sr_d_q <= sr_data;
    reg [31:0] wrq_cr_q, wwq_cr_q, wwq_done_q; reg [32*257-1:0] wrr_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wrq_cr_q <= '0; wwq_cr_q <= '0; wwq_done_q <= '0; wrr_q <= '0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr; end
    reg vf_seen; reg [1:0] idle_ph;
    // =================================================================================================================
    // STAGE engine (FRONT record): issuer -> per-lane in-flight meta FIFO -> landed {meta, data} FIFO -> beat scheduler
    // meta: {beat 8, mode 2 (0 run, 1 rep, 2 elem), group 4, local addr LWB, mask 8, word idx 3, rep count LWB+1}
    // =================================================================================================================
    localparam integer MW = 8 + 2 + 4 + LWB + 8 + 3 + (LWB + 1);
    reg st_go, st_busy, st_done;
    reg [2:0] sk;                                         // region being issued (0..3)
    reg [15:0] s_rows; reg [23:0] s_rb, s_va, s_nw, s_j; reg [LWB:0] s_lr, s_L; reg [23:0] s_so, s_si; reg [1:0] s_md;
    reg [20:0] s_cur, s_end; reg [3:0] s_g; reg [7:0] s_beat;
    reg [QB:0] cr [0:31]; reg [DB:0] slot [0:31];
    // in-flight meta FIFO: a power of two deep (pointers wrap at 2^n; LQ + DF need not be one)
    localparam integer MQB = $clog2(LQ + DF), MQD = 1 << MQB;
    reg [MW-1:0] mq [0:31][0:MQD-1]; reg [MQB:0] mq_n [0:31]; reg [MQB-1:0] mq_h [0:31], mq_t [0:31];
    reg [MW+255:0] lq [0:31][0:DF-1]; reg [DB:0] lq_n [0:31]; reg [DB-1:0] lq_h [0:31], lq_t [0:31];
    // beat queue: {beat id, count of sectors, mode}
    reg [7:0] bq_id [0:63]; reg [5:0] bq_cnt [0:63]; reg [5:0] bq_h, bq_t; reg [6:0] bq_n; reg [5:0] b_left; reg b_act;
    // replicate engine
    reg rp_on; reg [LWB:0] rp_a, rp_end; reg [31:0] rp_w; reg [3:0] rp_g;
    reg lane_ovf;
    function automatic [MW-1:0] meta(input [7:0] bt, input [1:0] mdd, input [3:0] g, input [LWB-1:0] la, input [7:0] mk,
                                     input [2:0] wi, input [LWB:0] rc);
        meta = {bt, mdd, g, la, mk, wi, rc};
    endfunction
    // meta field extraction
    function automatic [7:0] m_bt(input [MW-1:0] x); m_bt = x[MW-1 -: 8]; endfunction
    function automatic [1:0] m_md(input [MW-1:0] x); m_md = x[MW-9 -: 2]; endfunction
    function automatic [3:0] m_g(input [MW-1:0] x); m_g = x[MW-11 -: 4]; endfunction
    function automatic [LWB-1:0] m_la(input [MW-1:0] x); m_la = x[MW-15 -: LWB]; endfunction
    function automatic [7:0] m_mk(input [MW-1:0] x); m_mk = x[(LWB+1) + 3 + 7 -: 8]; endfunction
    function automatic [2:0] m_wi(input [MW-1:0] x); m_wi = x[(LWB+1) + 2 -: 3]; endfunction
    function automatic [LWB:0] m_rc(input [MW-1:0] x); m_rc = x[LWB:0]; endfunction
    // =================================================================================================================
    // DRAIN engine (DRAIN record): beats of VM sectors of the O / R shape, one lmem sector read each, VM write on the
    // sector's lane when the read returns (valid-driven, per-lane in-order sector FIFO)
    // =================================================================================================================
    reg dr_go, dr_done; reg dr_live; reg [2:0] drk;
    reg [15:0] e_rows; reg [23:0] e_rb, e_nw, e_va, e_j; reg [LWB:0] e_lr, e_L; reg [23:0] e_so, e_si; reg e_run;
    reg [20:0] e_cur, e_end; reg [1:0] e_g; reg e_wait;
    reg [QB:0] wcr [0:31]; reg [5:0] wpend [0:31];
    reg [28:0] dq [0:31][0:LQ-1]; reg [QB:0] dq_n [0:31]; reg [QB-1:0] dq_h [0:31], dq_t [0:31];   // {VM sector 21, mask 8}
    reg [31:0] dq_any;
    // ---- hazard / allocation predicates
    function automatic ovl_v(input [23:0] a0, input [23:0] a1, input [23:0] b0, input [23:0] b1);
        ovl_v = (a0 <= b1) && (b0 <= a1);
    endfunction
    function automatic ovl_r(input [LWB:0] a0, input [LWB:0] a1, input [LWB:0] b0, input [LWB:0] b1);
        ovl_r = (a0 < a1) && (b0 < b1) && (a0 < b1) && (b0 < a1);
    endfunction
    reg haz; reg alloc_ok; reg [LWB:0] try_b [0:5];
    always @* begin
        haz = 1'b0;
        for (integer q = 0; q < 4; q = q + 1) if (rv[q])
            for (integer k = 4; k < 6; k = k + 1) begin
                if (r_v && r_rv[k] && !(k == 4 && r_os) && ovl_v(lo[q], vhi[q], r_lo[k], r_vhi[k])) haz = 1'b1;
                if (d_v && d_rv[k] && !(k == 4 && d_os) && ovl_v(lo[q], vhi[q], d_lo[k], d_vhi[k])) haz = 1'b1;
            end
        if (MUT_X == 2) haz = 1'b0;
        alloc_ok = (!f_ser || (!r_v && !d_v)) && !(r_v && r_ser) && !(d_v && d_ser) && (OVL != 0 || (!r_v && !d_v));
        for (integer g = 0; g < 6; g = g + 1) begin
            try_b[g] = ({1'b0, gap[g]} + need[g] <= {1'b0, gsz(g[2:0])}) ? gap[g] : '0;
            if (need[g] != 0) begin
                if ({1'b0, try_b[g]} + need[g] > {1'b0, gsz(g[2:0])}) alloc_ok = 1'b0;
                if (r_v && ovl_r(try_b[g], LWB'(try_b[g] + need[g]), r_gs[g], r_ge[g])) alloc_ok = 1'b0;
                if (d_v && ovl_r(try_b[g], LWB'(try_b[g] + need[g]), d_gs[g], d_ge[g])) alloc_ok = 1'b0;
            end
        end
        if (cpair && need[2] != 0) alloc_ok = 1'b0;      // c_pair puts A's copy in G2: only with C unused (as d)
    end
    localparam [3:0] S_IDLE = 0, S_SPAN = 1, S_MUL = 2, S_NEXTR = 3, S_STAGE = 4, S_STW = 5, S_FAULT = 11,
                     S_PRE = 13, S_WAITA = 14, S_RDY = 15;
    reg [3:0] st;
    // census (bench)
    wire a_span = (st == S_SPAN || st == S_MUL || st == S_NEXTR || st == S_WAITA || st == S_PRE || st == S_STAGE);
    wire a_stage = (st == S_STW);
    wire a_run = r_v && !r_cdone;
    wire a_drain = d_v;
    integer k2;
    // =================================================================================================================
    // control
    // =================================================================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; op_rdy_r <= 1'b1; su_idle_r <= 1'b1; su_fault_r <= 1'b0; su_ret <= 1'b0; go <= 1'b0; vmq <= 338'd0;
            sl_v <= 1'b0; use_p <= 4'd0; vf_seen <= 1'b0; scount <= 21'd0; s_clr <= 1'b0; am_stream <= 523'd0;
            r_v <= 1'b0; r_gop <= 1'b0; r_cdone <= 1'b0; r_ser <= 1'b0; d_v <= 1'b0; d_ser <= 1'b0; d_ph <= 3'd0;
            st_go <= 1'b0; dr_go <= 1'b0; rg_req <= 1'b0; wg_req <= 1'b0; so_w <= 1'b0; f_ser <= 1'b0;
            for (k2 = 0; k2 < 6; k2 = k2 + 1) begin gap[k2] <= '0; need[k2] <= '0; r_gs[k2] <= '0; r_ge[k2] <= '0; d_gs[k2] <= '0; d_ge[k2] <= '0; end
        end else begin
            vmq[337] <= 1'b0; su_fault_r <= 1'b0; su_ret <= 1'b0; am_stream[0] <= 1'b0; am_stream[1] <= 1'b0; go <= 1'b0;
            st_go <= 1'b0; dr_go <= 1'b0;
            sl_v <= s0v_q && s0i_q < SW; sl_addr <= SBASE + s0i_q; sl_data <= s0d_q;
            if ((s0v_q && s0i_q >= SW) || lane_ovf || (cfault_q && st != S_FAULT)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (s_clr) scount <= {20'd0, s0v_q}; else if (s0v_q) scount <= scount + 21'd1;
            s_clr <= 1'b0;
            if (vfault_q && r_v && !r_gop) vf_seen <= 1'b1;
            su_idle_r <= (st == S_IDLE) && !r_v && !d_v;
            case (st)
                S_IDLE: if (op_v && op_rdy_r) begin
                    w <= op_w; fw <= op_w; op_rdy_r <= 1'b0; rk <= 3'd0;
                    a_s <= strm[0]; o_s <= strm[1]; f_ser <= strm[0] | strm[1]; st <= S_PRE;
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) begin rv[k2] <= 1'b0; need[k2] <= '0; end
                end
                S_PRE: begin
                    l_full_q <= l_el; l_half_q <= flatc ? (ni >> 1) : ((l_el >> 1) == 0 ? 1 : (l_el >> 1));
                    nn_q <= {16'd0, no} * {16'd0, ni};
                    st <= S_SPAN;
                end
                S_SPAN: begin
                    rv[rk] <= used_k && !(rk == 3'd0 && a_s);
                    lo[rk] <= base_k; sor[rk] <= so_k; sir[rk] <= si_k; nrr[rk] <= nr_k; nir[rk] <= ni_k; Lr[rk] <= L_k;
                    ma <= nr_k - 16'd1; mb <= L_k; mc <= so_k; md <= si_k; me <= ni_k - 16'd1; mph <= 2'd0;
                    if (rk == 3'd0 && a_s) begin
                        fw[40 +: 24] <= SBASE; fw[64 +: 24] <= {8'd0, ni}; fw[88 +: 24] <= 24'd1; rk <= rk + 3'd1;
                    end else if (rk == 3'd4 && o_s) begin             // O = STREAM: contiguous rows of ni in GO, no drain
                        Lr[4] <= ni; nrr[4] <= no; nir[4] <= ni; rv[4] <= 1'b1;
                        ma <= no - 16'd1; mb <= ni; me <= ni - 16'd1; st <= S_MUL;
                    end else if (!used_k) begin
                        if (rk == 3'd5) st <= S_WAITA; else rk <= rk + 3'd1;
                    end else st <= S_MUL;
                    if (rk == 3'd0 && (aind != 2'd0 || w[32 +: 8] != 8'd0)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                end
                S_MUL: begin                                        // 3 edges: partial products, sums, extent
                    if (mph == 2'd0) begin
                        pa0 <= ma[7:0] * mb; pa1 <= ma[15:8] * mb; pc0 <= ma[7:0] * mc; pc1 <= ma[15:8] * mc;
                        pe0 <= me[7:0] * md; pe1 <= me[15:8] * md; mph <= 2'd1;
                    end else if (mph == 2'd1) begin
                        lsz[rk] <= LWB'(pa0 + (pa1 << 8)) + LWB'(nir[rk]);
                        vhi[rk] <= lo[rk] + 24'(pc0 + (pc1 << 8)) + 24'(pe0 + (pe1 << 8));
                        need[grp(rk)] <= need[grp(rk)] + (LWB+2)'(((pa0 + (pa1 << 8)) + nir[rk] + N - 1) & ~(N - 1));
                        if (rk == 3'd0 && cpair) need[2] <= need[2];
                        mph <= 2'd2;
                    end else begin
                        if (rk == 3'd5) st <= S_WAITA; else begin rk <= rk + 3'd1; st <= S_SPAN; end
                    end
                end
                S_WAITA: if (alloc_ok) begin                         // ring placement per group, clear of live records
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) begin gbase[k2] <= try_b[k2]; galloc[k2] <= try_b[k2]; end
                    rk <= 3'd0; st <= S_NEXTR;
                end
                S_NEXTR: begin                                      // place region rk (N-aligned), rewrite its fields
                    if (rv[rk]) begin
                        lb[rk] <= galloc[rk];
                        galloc[rk] <= (galloc[rk] + lsz[rk] + N - 1) & ~(N - 1);
                        case (rk)
                            3'd0: begin fw[40 +: 24]  <= galloc[0]; fw[64 +: 24]  <= Lr[0]; fw[88 +: 24]  <= 24'd1; end
                            3'd1: begin fw[138 +: 24] <= galloc[1]; fw[162 +: 24] <= Lr[1]; fw[186 +: 24] <= 24'd1; end
                            3'd2: begin fw[211 +: 24] <= galloc[2]; fw[235 +: 24] <= Lr[2]; fw[259 +: 24] <= 24'd1; end
                            3'd3: begin fw[284 +: 24] <= galloc[3]; fw[308 +: 24] <= Lr[3]; fw[332 +: 24] <= 24'd1; end
                            3'd4: begin fw[382 +: 24] <= galloc[4]; fw[406 +: 24] <= Lr[4]; fw[430 +: 24] <= 24'd1; end
                            default: begin fw[484 +: 24] <= galloc[5]; fw[508 +: 24] <= 24'd1; end
                        endcase
                    end
                    else begin
                        // an unused stream: give it the flat-consistent stride (so = row words, si = 1) so the vec's
                        // flatten test (every stream contiguous across rows) agrees with the dense layout's choice
                        case (rk)
                            3'd1: begin fw[162 +: 24] <= bhalf ? {8'd0, ni >> 1} : {8'd0, ni}; fw[186 +: 24] <= 24'd1; end
                            3'd2: begin fw[235 +: 24] <= {8'd0, ni}; fw[259 +: 24] <= 24'd1; end
                            3'd3: begin fw[308 +: 24] <= bhalf ? {8'd0, ni >> 1} : {8'd0, ni}; fw[332 +: 24] <= 24'd1; end
                            3'd4: if (!o_s) begin fw[406 +: 24] <= {8'd0, ni}; fw[430 +: 24] <= 24'd1; end
                            default: ;
                        endcase
                    end
                    if (rk == 3'd5) st <= S_STAGE; else rk <= rk + 3'd1;
                end
                S_STAGE: begin                                      // sources clear of older undrained sinks?
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) gap[k2] <= galloc[k2];
                    if (!haz) rg_req <= 1'b1;
                    if (!haz && rg_req && rg_q) begin st <= S_STW; st_go <= 1'b1; end
                end
                S_STW: if (!st_go && st_done) begin st <= S_RDY; rg_req <= 1'b0; end
                S_RDY: if (!r_v) begin                              // into RUN
                    r_v <= 1'b1; r_gop <= 1'b1; r_cdone <= 1'b0; wl <= fw; r_as <= a_s; r_os <= o_s; r_ser <= f_ser;
                    r_no <= no; r_ni <= ni; r_nn <= nn_q;
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) begin r_gs[k2] <= gbase[k2]; r_ge[k2] <= galloc[k2]; end
                    for (k2 = 4; k2 < 6; k2 = k2 + 1) begin
                        r_lo[k2] <= lo[k2]; r_vhi[k2] <= vhi[k2]; r_so[k2] <= sor[k2]; r_si[k2] <= sir[k2]; r_nr[k2] <= nrr[k2];
                        r_nw[k2] <= nir[k2]; r_lb[k2] <= lb[k2]; r_L[k2] <= Lr[k2]; r_rv[k2] <= rv[k2];
                    end
                    op_rdy_r <= 1'b1; st <= S_IDLE;
                end
                S_FAULT: ;
                default: st <= S_FAULT;
            endcase
            // ---------------------------------------------------------------- RUN
            if (r_v && st != S_FAULT) begin
                if (r_gop) begin
                    if (ready_q && !sl_pend && (!r_as || {11'd0, scount} >= r_nn)) begin
                        go <= 1'b1; r_gop <= 1'b0; idle_ph <= 2'd0; vf_seen <= 1'b0;
                        use_p <= {wl[365 +: 3] != 3'd0 || wl[368 +: 3] == 3'd5,
                                  wl[283] || (wl[363 +: 2] == 2'd1) || (wl[365 +: 3] != 3'd0) || (wl[368 +: 3] == 3'd1) ||
                                  (wl[368 +: 3] == 3'd2) || (wl[374 +: 3] == 3'd1) || (wl[374 +: 3] == 3'd2),
                                  (wl[360 +: 3] == 3'd1) || (wl[360 +: 3] == 3'd4) || (wl[360 +: 3] == 3'd6) ||
                                  (wl[368 +: 3] == 3'd3) || (wl[377 +: 2] == 2'd1), 1'b1};
                    end
                end else if (!r_cdone) begin
                    if (idle_ph != 2'd3) idle_ph <= idle_ph + 2'd1;
                    else if (idle_q) begin
                        if (vf_seen || vfault_q) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        else begin r_cdone <= 1'b1; use_p <= 4'd0; end
                    end
                end else if (!d_v) begin                            // into DRAIN
                    d_v <= 1'b1; d_ph <= 3'd0; d_as <= r_as; d_os <= r_os; d_ser <= r_ser; d_no <= r_no; d_ni <= r_ni;
                    for (k2 = 0; k2 < 6; k2 = k2 + 1) begin d_gs[k2] <= r_gs[k2]; d_ge[k2] <= r_ge[k2]; end
                    for (k2 = 4; k2 < 6; k2 = k2 + 1) begin
                        d_lo[k2] <= r_lo[k2]; d_vhi[k2] <= r_vhi[k2]; d_so[k2] <= r_so[k2]; d_si[k2] <= r_si[k2];
                        d_nr[k2] <= r_nr[k2]; d_nw[k2] <= r_nw[k2]; d_lb[k2] <= r_lb[k2]; d_L[k2] <= r_L[k2]; d_rv[k2] <= r_rv[k2];
                    end
                    r_v <= 1'b0; r_ser <= 1'b0;
                end
            end
            // ---------------------------------------------------------------- DRAIN
            if (d_v && st != S_FAULT) begin
                case (d_ph)
                    3'd0: begin
                        if ((d_rv[4] && !d_os) || d_rv[5]) begin
                            wg_req <= 1'b1;
                            if (wg_req && wg_q) begin dr_go <= 1'b1; d_ph <= 3'd1; end
                        end else if (d_os) d_ph <= 3'd2;
                        else begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                    end
                    3'd1: if (!dr_go && dr_done) begin
                        wg_req <= 1'b0;
                        if (d_os) d_ph <= 3'd2;
                        else begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                    end
                    3'd2: begin etot <= {5'd0, d_no} * {5'd0, d_ni}; ebeat <= 21'd0; o_lb <= d_lb[4]; so_w <= 1'b0; d_ph <= 3'd3; end
                    default: begin                                  // STREAM out on sector lane 0, valid-driven
                        if (amr_q && !so_w) so_w <= 1'b1;
                        else if (so_w && sr_rv_q[0]) begin
                            begin : so
                                reg [7:0] mk; integer q;
                                for (q = 0; q < 8; q = q + 1) mk[q] = (ebeat + q < etot);
                                am_stream <= {1'b0, 256'd0, sr_d_q[255:0], mk, (ebeat + 21'd8 >= etot), 1'b1};
                            end
                            so_w <= 1'b0;
                            if (ebeat + 21'd8 >= etot) begin su_ret <= 1'b1; d_v <= 1'b0; d_ser <= 1'b0; if (d_as) s_clr <= 1'b1; end
                            else ebeat <= ebeat + 21'd8;
                        end
                    end
                endcase
            end
        end
    end
    // STREAM-out read issue (one sector read when so_w rises)
    reg so_iss;
    // =================================================================================================================
    // the lane engines (stage issue / landing / beat scheduler; drain issue / return / VM write)
    // =================================================================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wrq <= '0; wwq <= '0; sw_v <= '0; sr_v <= '0; st_busy <= 1'b0; st_done <= 1'b1; dr_live <= 1'b0; dr_done <= 1'b1;
            bq_h <= '0; bq_t <= '0; bq_n <= '0; b_act <= 1'b0; rp_on <= 1'b0; lane_ovf <= 1'b0; s_beat <= '0; so_iss <= 1'b0;
            for (integer b = 0; b < 32; b = b + 1) begin
                cr[b] <= (QB+1)'(LQ); slot[b] <= (DB+1)'(DF); mq_n[b] <= '0; mq_h[b] <= '0; mq_t[b] <= '0;
                lq_n[b] <= '0; lq_h[b] <= '0; lq_t[b] <= '0; wcr[b] <= (QB+1)'(LQ); wpend[b] <= '0; dq_n[b] <= '0; dq_h[b] <= '0; dq_t[b] <= '0;
            end
        end else begin : eng
            reg [31:0] iss; reg [31:0] land; reg [31:0] wr; reg [31:0] dri; reg [31:0] dret; reg [31:0] wsend;
            reg [MW-1:0] mh; integer n_ok; reg [20:0] sc; reg [4:0] bl; reg stop; reg [23:0] w0; reg [7:0] mk;
            reg bq_push; reg [7:0] bq_pid; reg [5:0] bq_pcnt; reg bq_pop;
            iss = '0; land = '0; wr = '0; dri = '0; dret = '0; wsend = '0; bq_push = 1'b0; bq_pid = '0; bq_pcnt = '0; bq_pop = 1'b0;
            for (integer b = 0; b < 32; b = b + 1) begin wrq[b*16 + 15] <= 1'b0; wwq[b*280 + 279] <= 1'b0; end
            sw_v <= '0; sr_v <= '0;
            // ---------------------------------------------------------------- stage: start
            if (st_go) begin
                st_busy <= 1'b1; st_done <= 1'b0; sk <= 3'd0; s_rows <= 16'd0;
            end
            // ---------------------------------------------------------------- stage: issuer (one beat an edge)
            if (st_busy && !st_go) begin
                if (s_rows == 16'd0) begin                      // the next used source region
                    if (sk >= 3'd4) st_busy <= 1'b0;
                    else if (!rv[sk]) sk <= sk + 3'd1;
                    else begin : rsetup
                        reg [1:0] mdd; reg merge;
                        mdd = (sir[sk] == 24'd1) ? 2'd0 : (sir[sk] == 24'd0) ? 2'd1 : 2'd2;
                        merge = (mdd == 2'd0) && (sor[sk] == {8'd0, nir[sk]}) && (Lr[sk] == nir[sk]);
                        s_md <= mdd; s_g <= (sk == 3'd0 && cpair) ? 4'b0101 : (4'b0001 << sk);
                        s_rows <= merge ? 16'd1 : nrr[sk];
                        s_nw <= merge ? 24'({8'd0, nrr[sk]} * {8'd0, nir[sk]}) : {8'd0, nir[sk]};
                        s_rb <= lo[sk]; s_va <= lo[sk]; s_lr <= lb[sk]; s_j <= 24'd0; s_so <= sor[sk]; s_si <= sir[sk];
                        s_L <= Lr[sk]; s_cur <= 21'(lo[sk] >> 3);
                        s_end <= 21'((lo[sk] + (merge ? 24'({8'd0, nrr[sk]} * {8'd0, nir[sk]}) : {8'd0, nir[sk]}) - 24'd1) >> 3);
                        sk <= sk + 3'd1;
                    end
                end else begin
                    // a beat: the run's next sectors (prefix with credits / slots), or one rep / elem request
                    n_ok = 0; stop = 1'b0;
                    if (s_md == 2'd0) begin
                        for (integer k = 0; k < BL; k = k + 1) begin
                            sc = s_cur + 21'(k); bl = sc[4:0];
                            if (!stop && sc <= s_end && cr[bl] != 0 && slot[bl] != 0 && mq_n[bl] < (MQB+1)'(MQD)) begin
                                iss[bl] = 1'b1; n_ok = n_ok + 1;
                                w0 = {sc, 3'b000};
                                for (integer q = 0; q < 8; q = q + 1) mk[q] = MUT_X == 1 ? 1'b1 : ((w0 + q >= s_rb) && (w0 + q < s_rb + s_nw));
                                wrq[bl*16 +: 16] <= {1'b1, sc[14:0]};
                                mq[bl][mq_t[bl]] <= meta(s_beat, 2'd0, s_g, LWB'(w0 - s_rb + s_lr), mk, 3'd0, '0);
                            end else stop = 1'b1;
                        end
                        if (n_ok > 0) begin
                            bq_push = 1'b1; bq_pid = s_beat; bq_pcnt = 6'(n_ok); s_beat <= s_beat + 8'd1;
                            if (s_cur + 21'(n_ok) > s_end) begin       // the row is issued: the next row
                                s_rows <= s_rows - 16'd1; s_rb <= s_rb + s_so; s_lr <= s_lr + s_L;
                                s_cur <= 21'((s_rb + s_so) >> 3); s_end <= 21'((s_rb + s_so + s_nw - 24'd1) >> 3);
                            end else s_cur <= s_cur + 21'(n_ok);
                        end
                    end else begin
                        sc = (s_md == 2'd1) ? 21'(s_rb >> 3) : 21'(s_va >> 3); bl = sc[4:0];
                        if (cr[bl] != 0 && slot[bl] != 0 && mq_n[bl] < (MQB+1)'(MQD) && bq_n < 7'd60) begin
                            iss[bl] = 1'b1;
                            wrq[bl*16 +: 16] <= {1'b1, sc[14:0]};
                            if (s_md == 2'd1)                      // broadcast row: one read, the row's L words
                                mq[bl][mq_t[bl]] <= meta(s_beat, 2'd1, s_g, s_lr[LWB-1:0], 8'hFF, s_rb[2:0], LWB'(s_nw));
                            else
                                mq[bl][mq_t[bl]] <= meta(s_beat, 2'd2, s_g, LWB'(s_lr + s_j), 8'h01, s_va[2:0], '0);
                            bq_push = 1'b1; bq_pid = s_beat; bq_pcnt = 6'd1; s_beat <= s_beat + 8'd1;
                            if (s_md == 2'd1 || s_j + 24'd1 == s_nw) begin
                                s_rows <= s_rows - 16'd1; s_rb <= s_rb + s_so; s_va <= s_rb + s_so; s_lr <= s_lr + s_L; s_j <= 24'd0;
                            end else begin s_j <= s_j + 24'd1; s_va <= s_va + s_si; end
                        end
                    end
                end
            end
            // ---------------------------------------------------------------- stage: responses land in the lane FIFOs
            for (integer b = 0; b < 32; b = b + 1) begin
                if (wrr_q[b*257 + 256]) begin
                    land[b] = 1'b1;
                    lq[b][lq_t[b]] <= {mq[b][mq_h[b]], wrr_q[b*257 +: 256]};
                    if (lq_n[b] == (DB+1)'(DF)) lane_ovf <= 1'b1;
                end
            end
            // ---------------------------------------------------------------- stage: the beat scheduler (oldest beat)
            if (rp_on) begin                                    // replicate engine: 32 sectors of copies an edge
                sw_g <= rp_g;
                for (integer b = 0; b < 32; b = b + 1) begin : rpl
                    reg [LWB:0] a_;
                    a_ = rp_a + (LWB+1)'(8 * b);
                    if (b < BL && a_ < rp_end && !(MUT_X == 3 && a_ + 8 >= rp_end)) begin
                        sw_v[b] <= 1'b1; sw_addr[b*LWB +: LWB] <= a_[LWB-1:0]; sw_data[b*256 +: 256] <= {8{rp_w}};
                        for (integer q = 0; q < 8; q = q + 1) sw_mask[b*8 + q] <= (a_ + q < rp_end);
                    end
                end
                if (rp_a + 8 * BL >= rp_end) begin rp_on <= 1'b0; bq_pop = 1'b1; end
                else rp_a <= rp_a + 8 * BL;
            end else if (bq_n != 0) begin : sched
                reg [5:0] got_; reg [5:0] need_; reg rep_;
                got_ = '0; need_ = b_act ? b_left : bq_cnt[bq_h]; rep_ = 1'b0;
                for (integer b = 0; b < 32; b = b + 1)
                    if (lq_n[b] != 0 && m_bt(lq[b][lq_h[b]][MW+255 -: MW]) == bq_id[bq_h]) begin : one
                        reg [MW-1:0] mm; reg [255:0] dd;
                        mm = lq[b][lq_h[b]][MW+255 -: MW]; dd = lq[b][lq_h[b]][255:0];
                        wr[b] = 1'b1; got_ = got_ + 6'd1;
                        sw_g <= m_g(mm);
                        case (m_md(mm))
                            2'd0: begin sw_v[b] <= 1'b1; sw_addr[b*LWB +: LWB] <= m_la(mm); sw_data[b*256 +: 256] <= dd;
                                        sw_mask[b*8 +: 8] <= m_mk(mm); end
                            2'd1: begin rep_ = 1'b1; rp_on <= 1'b1; rp_a <= {1'b0, m_la(mm)}; rp_end <= {1'b0, m_la(mm)} + m_rc(mm);
                                        rp_w <= dd[32*m_wi(mm) +: 32]; rp_g <= m_g(mm); end
                            default: begin sw_v[b] <= 1'b1; sw_addr[b*LWB +: LWB] <= m_la(mm); sw_data[b*256 +: 256] <= {224'd0, dd[32*m_wi(mm) +: 32]};
                                           sw_mask[b*8 +: 8] <= 8'h01; end
                        endcase
                    end
                if (got_ != 0 && !rep_) begin
                    if (got_ == need_) begin b_act <= 1'b0; bq_pop = 1'b1; end
                    else begin b_act <= 1'b1; b_left <= need_ - got_; end
                end
            end
            for (integer b = 0; b < 32; b = b + 1) begin
                if (iss[b]) mq_t[b] <= mq_t[b] + 1'b1;
                if (land[b]) begin mq_h[b] <= mq_h[b] + 1'b1; lq_t[b] <= lq_t[b] + 1'b1; end
                if (wr[b]) lq_h[b] <= lq_h[b] + 1'b1;
                mq_n[b] <= mq_n[b] + iss[b] - land[b];
                lq_n[b] <= lq_n[b] + land[b] - wr[b];
                cr[b] <= cr[b] - iss[b] + wrq_cr_q[b];
                slot[b] <= slot[b] - iss[b] + wr[b];
            end
            if (bq_push) begin bq_id[bq_t] <= bq_pid; bq_cnt[bq_t] <= bq_pcnt; bq_t <= bq_t + 6'd1; end
            if (bq_pop) bq_h <= bq_h + 6'd1;
            bq_n <= bq_n + bq_push - bq_pop;
            if (bq_push && bq_n == 7'd64) lane_ovf <= 1'b1;
            begin : sdone
                reg idle_; idle_ = !st_busy && !st_go && (bq_n + bq_push - bq_pop) == 0 && !rp_on;
                for (integer b = 0; b < 32; b = b + 1)
                    if (mq_n[b] + iss[b] - land[b] != 0 || (cr[b] - iss[b] + wrq_cr_q[b]) != (QB+1)'(LQ)) idle_ = 1'b0;
                if (!st_done && idle_ && !st_go) st_done <= 1'b1;
            end
            // ---------------------------------------------------------------- drain: start
            if (dr_go) begin dr_live <= 1'b1; dr_done <= 1'b0; drk <= 3'd4; e_rows <= 16'd0; e_wait <= 1'b0; end
            else if (dr_live) begin
                if (e_rows == 16'd0) begin                      // the next sink region (after the previous one's reads)
                    if (dq_any == 0 && !e_wait) begin
                        if (drk >= 3'd6) dr_live <= 1'b0;
                        else if (!d_rv[drk] || (drk == 3'd4 && d_os)) drk <= drk + 3'd1;
                        else begin : dsetup
                            reg run_; reg merge_; reg [23:0] so_; reg [15:0] nr_, nw_;
                            nr_ = d_nr[drk]; nw_ = d_nw[drk]; so_ = d_so[drk];
                            run_ = (drk == 3'd4) ? (d_si[drk] == 24'd1) : (so_ == 24'd1 || nr_ == 16'd1);
                            if (drk == 3'd5) begin                  // R: one word a row at r_so (stride 0 = 1)
                                merge_ = (so_ == 24'd1 || so_ == 24'd0 || nr_ == 16'd1);
                                e_nw <= merge_ ? {8'd0, nr_} : 24'd1; e_rows <= merge_ ? 16'd1 : nr_;
                                e_so <= (so_ == 24'd0) ? 24'd1 : so_; e_L <= 1; e_run <= 1'b1; e_si <= 24'd0;
                                e_end <= 21'((d_lo[drk] + (merge_ ? {8'd0, nr_} : 24'd1) - 24'd1) >> 3);
                            end else begin
                                merge_ = run_ && (so_ == {8'd0, nw_}) && (d_L[drk] == nw_);
                                e_nw <= merge_ ? 24'({8'd0, nr_} * {8'd0, nw_}) : {8'd0, nw_}; e_rows <= merge_ ? 16'd1 : nr_;
                                e_so <= so_; e_L <= d_L[drk]; e_run <= run_; e_si <= d_si[drk];
                                e_end <= 21'((d_lo[drk] + (merge_ ? 24'({8'd0, nr_} * {8'd0, nw_}) : {8'd0, nw_}) - 24'd1) >> 3);
                            end
                            e_rb <= d_lo[drk]; e_va <= d_lo[drk]; e_lr <= d_lb[drk]; e_j <= 24'd0; e_cur <= 21'(d_lo[drk] >> 3);
                            e_g <= (drk == 3'd4) ? 2'd1 : 2'd2;
                            drk <= drk + 3'd1;
                        end
                    end
                    e_wait <= 1'b0;
                end else begin
                    stop = 1'b0; n_ok = 0;
                    sr_g <= e_g;
                    if (e_run) begin                            // a beat: the row's next sectors, one lmem read each
                        for (integer k = 0; k < BL; k = k + 1) begin
                            sc = e_cur + 21'(k); bl = sc[4:0];
                            if (!stop && sc <= e_end && wcr[bl] != 0 && dq_n[bl] < (QB+1)'(LQ)) begin
                                dri[bl] = 1'b1; n_ok = n_ok + 1;
                                w0 = {sc, 3'b000};
                                for (integer q = 0; q < 8; q = q + 1) mk[q] = MUT_DIRTY ? 1'b1 : ((w0 + q >= e_rb) && (w0 + q < e_rb + e_nw));
                                sr_v[bl] <= 1'b1; sr_addr[bl*LWB +: LWB] <= LWB'(w0 - e_rb + e_lr);
                                dq[bl][dq_t[bl]] <= {sc, mk};
                            end else stop = 1'b1;
                        end
                        if (n_ok > 0) begin
                            if (e_cur + 21'(n_ok) > e_end) begin
                                e_rows <= e_rows - 16'd1; e_rb <= e_rb + e_so; e_lr <= e_lr + e_L;
                                e_cur <= 21'((e_rb + e_so) >> 3); e_end <= 21'((e_rb + e_so + e_nw - 24'd1) >> 3);
                                if (e_rows == 16'd1) e_wait <= 1'b1;
                            end else e_cur <= e_cur + 21'(n_ok);
                        end
                    end else begin                              // one element an edge
                        sc = 21'(e_va >> 3); bl = sc[4:0];
                        if (wcr[bl] != 0 && dq_n[bl] < (QB+1)'(LQ)) begin
                            dri[bl] = 1'b1;
                            sr_v[bl] <= 1'b1; sr_addr[bl*LWB +: LWB] <= LWB'(e_lr + e_j - e_va[2:0]);
                            dq[bl][dq_t[bl]] <= {sc, (MUT_DIRTY ? 8'hFF : (8'd1 << e_va[2:0]))};
                            if (e_j + 24'd1 == e_nw) begin
                                e_rows <= e_rows - 16'd1; e_rb <= e_rb + e_so; e_va <= e_rb + e_so; e_lr <= e_lr + e_L; e_j <= 24'd0;
                                if (e_rows == 16'd1) e_wait <= 1'b1;
                            end else begin e_j <= e_j + 24'd1; e_va <= e_va + e_si; end
                        end
                    end
                end
            end
            // STREAM-out sector read (lane 0) when the DRAIN slot asks
            so_iss <= so_w;
            if (so_w && !so_iss && d_ph == 3'd3) begin sr_v[0] <= 1'b1; sr_g <= 2'd1; sr_addr[0 +: LWB] <= LWB'(o_lb + ebeat); end
            // drain returns -> VM writes
            for (integer b = 0; b < 32; b = b + 1) begin
                if (sr_rv_q[b] && dq_n[b] != 0) begin
                    dret[b] = 1'b1; wsend[b] = 1'b1;
                    wwq[b*280 +: 280] <= {1'b1, dq[b][dq_h[b]][22:8], sr_d_q[b*256 +: 256], dq[b][dq_h[b]][7:0]};
                end
                if (dri[b]) dq_t[b] <= dq_t[b] + 1'b1;
                if (dret[b]) dq_h[b] <= dq_h[b] + 1'b1;
                dq_n[b] <= dq_n[b] + dri[b] - dret[b];
                wcr[b] <= wcr[b] - dri[b] + wwq_cr_q[b];
                wpend[b] <= wpend[b] + wsend[b] - wwq_done_q[b];
            end
            dq_any <= '0;
            for (integer b = 0; b < 32; b = b + 1) if (dq_n[b] + dri[b] - dret[b] != 0) dq_any[b] <= 1'b1;
            begin : ddone
                reg idle_; idle_ = !dr_live && !dr_go;
                for (integer b = 0; b < 32; b = b + 1)
                    if (dq_n[b] + dri[b] - dret[b] != 0 || wpend[b] + wsend[b] - wwq_done_q[b] != 0 ||
                        (wcr[b] - dri[b] + wwq_cr_q[b]) != (QB+1)'(LQ)) idle_ = 1'b0;
                if (!dr_done && idle_) dr_done <= 1'b1;
            end
        end
    end
endmodule

`default_nettype wire

// el1011-hbm-sfu 2026-10-11 (textbook classes 1 + 6: ot_hgi_su_ctlw was one 80,059-flop clock tree in a 1 x 1 mm die at
// 5.7 % utilisation, 40,691 pins): eight of the 32 wide lanes as a hardened slice.  The lane logic is the flat
// ctlw's, verbatim (lane b of slice SL is global lane SL*NL+b: its first sector, its VM / local bank); every slice input
// is a pin register (the shared region descriptors and go pulses arrive one edge later, together), every output a
// register; the slice's all-lanes-done / overflow reductions leave registered (the hub reduces the four again).
module ot_hgi_su_ctlw_slice #(
    parameter integer SL = 0, parameter integer NL = 8, parameter integer LWB = 17, parameter integer LQ = 8,
    parameter integer MUT_W = 0, parameter integer MUT_DIRTY = 0,
    parameter integer LQSRAM = 0          // 1: each lane's landing FIFO in a 64x16 1R1W SRAM (FWFT), not 64 x LSW flops
) (
    input  wire clk, input wire rst_n,
    input  wire wst_go_i, input wire wdr_go_i,
    input  wire [6*24-1:0] lo_i, input wire [6*24-1:0] hi_i, input wire [6*(LWB+1)-1:0] lb_i, input wire [5:0] rv_i,
    input  wire [6*21-1:0] dsec_i,
    input  wire [2*24-1:0] d_lo_i, input wire [2*24-1:0] d_hi_i, input wire [2*(LWB+1)-1:0] d_lb_i, input wire [1:0] d_rv_i,
    input  wire [2*21-1:0] d_dsec_i, input wire d_os_i,
    // GLUE PLACEMENT (el1011-hbm-sfu 10-11): slice id strap (one hard tile for every slice), the forward link (this
    // slice's descriptor / go pin registers, to the next slice) and the backward done / overflow combine link
    input  wire [1:0] sl_i,
    output wire wst_go_o, output wire wdr_go_o, output wire d_os_o,
    output wire [6*24-1:0] lo_o, output wire [6*24-1:0] hi_o, output wire [6*(LWB+1)-1:0] lb_o, output wire [5:0] rv_o,
    output wire [6*21-1:0] dsec_o, output wire [2*24-1:0] d_lo_o, output wire [2*24-1:0] d_hi_o,
    output wire [2*(LWB+1)-1:0] d_lb_o, output wire [1:0] d_rv_o, output wire [2*21-1:0] d_dsec_o,
    input  wire wst_dn_i, input wire wdr_dn_i, input wire ovf_i,
    output reg  [NL*16-1:0] wrq, input wire [NL-1:0] wrq_cr, input wire [NL*257-1:0] wrr,
    output reg  [NL*280-1:0] wwq, input wire [NL-1:0] wwq_cr, input wire [NL-1:0] wwq_done,
    output reg  [NL-1:0] lsw_v, output reg [NL*(LWB-3)-1:0] lsw_sec, output reg [NL*256-1:0] lsw_d,
    output reg  [NL-1:0] ldc_v, output reg [NL*(LWB-3)-1:0] ldc_sec,
    output reg  [NL-1:0] ldr_v, output reg [NL*(LWB-3)-1:0] ldr_sec,
    input  wire [NL*256-1:0] ldr_d, input wire [NL*8-1:0] ldr_dm, input wire [NL-1:0] ldr_rv,
    output reg  wst_dn, output reg wdr_dn, output reg ovf
);
    localparam integer LSW = LWB - 3, QB = $clog2(LQ);
    reg rst_l; always @(posedge clk) rst_l <= rst_n;          // the slice's reset pin flop
    reg wst_go, wdr_go;
    always @(posedge clk or negedge rst_l) if (!rst_l) begin wst_go <= 1'b0; wdr_go <= 1'b0; end
                                           else begin wst_go <= wst_go_i; wdr_go <= wdr_go_i; end
    reg [23:0] lo [0:5]; reg [23:0] hi [0:5]; reg [LWB:0] lb [0:5]; reg rv [0:5]; reg [20:0] dsec [0:5];
    reg [23:0] d_lo [4:5]; reg [23:0] d_hi [4:5]; reg [LWB:0] d_lb [4:5]; reg d_rv [4:5]; reg [20:0] d_dsec [4:5]; reg d_os;
    always @(posedge clk) begin
        for (integer q = 0; q < 6; q = q + 1) begin
            lo[q] <= lo_i[q*24 +: 24]; hi[q] <= hi_i[q*24 +: 24]; lb[q] <= lb_i[q*(LWB+1) +: LWB+1]; rv[q] <= rv_i[q];
            dsec[q] <= dsec_i[q*21 +: 21];
        end
        for (integer q = 4; q < 6; q = q + 1) begin
            d_lo[q] <= d_lo_i[(q-4)*24 +: 24]; d_hi[q] <= d_hi_i[(q-4)*24 +: 24]; d_lb[q] <= d_lb_i[(q-4)*(LWB+1) +: LWB+1];
            d_rv[q] <= d_rv_i[q-4]; d_dsec[q] <= d_dsec_i[(q-4)*21 +: 21];
        end
        d_os <= d_os_i;
    end
    reg [1:0] sl_q; always @(posedge clk) sl_q <= sl_i;      // strap pin flop
    assign wst_go_o = wst_go; assign wdr_go_o = wdr_go; assign d_os_o = d_os;
    for (genvar q = 0; q < 6; q = q + 1) begin : g_fo
        assign lo_o[q*24 +: 24] = lo[q]; assign hi_o[q*24 +: 24] = hi[q]; assign lb_o[q*(LWB+1) +: LWB+1] = lb[q];
        assign rv_o[q] = rv[q]; assign dsec_o[q*21 +: 21] = dsec[q];
    end
    for (genvar q = 4; q < 6; q = q + 1) begin : g_fd
        assign d_lo_o[(q-4)*24 +: 24] = d_lo[q]; assign d_hi_o[(q-4)*24 +: 24] = d_hi[q];
        assign d_lb_o[(q-4)*(LWB+1) +: LWB+1] = d_lb[q]; assign d_rv_o[q-4] = d_rv[q]; assign d_dsec_o[(q-4)*21 +: 21] = d_dsec[q];
    end
    reg dn_st_q, dn_dr_q, dn_ov_q;                           // the next slice's combined flags, pin-flopped
    always @(posedge clk or negedge rst_l) if (!rst_l) begin dn_st_q <= 1'b1; dn_dr_q <= 1'b1; dn_ov_q <= 1'b0; end
                                           else begin dn_st_q <= wst_dn_i; dn_dr_q <= wdr_dn_i; dn_ov_q <= ovf_i; end
    reg [NL-1:0] wrq_cr_q, wwq_cr_q, wwq_done_q; reg [NL*257-1:0] wrr_q;
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin wrq_cr_q <= '0; wwq_cr_q <= '0; wwq_done_q <= '0; wrr_q <= '0; end
        else begin wrq_cr_q <= wrq_cr; wwq_cr_q <= wwq_cr; wwq_done_q <= wwq_done; wrr_q <= wrr; end
    reg [NL*256-1:0] ldr_d_q; reg [NL*8-1:0] ldr_dm_q;
    reg [NL-1:0] ldr_rv_q;
    always @(posedge clk) begin ldr_d_q <= ldr_d; ldr_dm_q <= ldr_dm; end
    always @(posedge clk or negedge rst_l) if (!rst_l) ldr_rv_q <= '0; else ldr_rv_q <= ldr_rv;
    // drain reads are VALID-driven: each lane keeps the VM sector of every read in flight (in order); a returned
    // {data, dirty} (ldr_rv, pin-flopped) pops it, whatever the memory latency
    reg [20:0] dq_s [0:NL-1][0:LQ-1]; reg [QB-1:0] dq_h [0:NL-1], dq_t [0:NL-1]; reg [QB:0] dq_n [0:NL-1];
    // per-lane state
    reg [2:0]  sg_r [0:NL-1]; reg sg_on [0:NL-1]; reg [20:0] sg_nx [0:NL-1]; reg [20:0] sg_end [0:NL-1];
    // landing FIFO: LQ queued at the VM + the accepted-not-landed pipe (VM core + relays): power of two >= 2 LQ + 32
    localparam integer LFB = $clog2(2 * LQ + 32), LFD = 1 << LFB;
    reg [QB:0] cr [0:NL-1]; reg [LSW-1:0] lq [0:NL-1][0:LFD-1]; reg [LFB-1:0] lqh [0:NL-1], lqt [0:NL-1]; reg [LFB:0] lqn [0:NL-1];
    reg [5:0] wpend [0:NL-1]; reg lane_ovf;
    reg [2:0]  cl_r [0:NL-1]; reg cl_on [0:NL-1]; reg [LSW-1:0] cl_nx [0:NL-1]; reg [LSW-1:0] cl_end [0:NL-1];
    reg [2:0]  dg_r [0:NL-1]; reg dg_on [0:NL-1]; reg [LSW-1:0] dg_nx [0:NL-1]; reg [LSW-1:0] dg_end [0:NL-1];
    reg [QB:0] wcr [0:NL-1]; reg [NL-1:0] dp1, dp2, dp3; reg [20:0] dp1_s [0:NL-1]; reg [20:0] dp2_s [0:NL-1]; reg [20:0] dp3_s [0:NL-1];
    reg [NL-1:0] wst_ldone, wdr_ldone;
    function automatic [20:0] first_of(input [20:0] lo_s, input integer b);
        first_of = lo_s + 21'((5'(b) - lo_s[4:0]) & 5'd31);
    endfunction
    // landing FIFO head per lane: flops (LQSRAM 0) or an SRAM first-word-fall-through FIFO (LQSRAM 1); lq_first = slot 0
    wire [LSW-1:0] lq_head [0:NL-1]; reg [LSW-1:0] lq_first [0:NL-1];
    generate if (LQSRAM != 0) begin : g_lqm
        initial if (LFD != 64 || LSW > 16) $error("ot_hgi_su_ctlw_slice LQSRAM: needs LFD 64 and LSW <= 16");
        for (genvar g = 0; g < NL; g = g + 1) begin : g_l
            wire push = !wst_go && sg_r[g] < 3'd4 && sg_on[g] && cr[g] != 0;
            // MUT_W 4 (bench mutant, el1011-hbm-sfu 10-11): the SRAM FIFO pop one edge late -> a back-to-back landing
            // reads the previous head (wrong sector); the only mutant that exercises this FIFO's read-ahead (MUT_DIRTY is
            // unobservable on the production shapes: every drained sink sector is whole, dirty mask 8'hFF)
            reg pop_d;
            always @(posedge clk or negedge rst_l) if (!rst_l) pop_d <= 1'b0; else pop_d <= wrr_q[g*257 + 256];
            wire pop = (MUT_W == 4) ? pop_d : wrr_q[g*257 + 256];
            wire hv, ovf_l;
            ot_fifo_sram_fwft #(.W(LSW), .DEPTH(64), .MACRO(3)) u_lq (.clk(clk), .rst_n(rst_l), .push(push),
                .wdata(LSW'(sg_nx[g] + dsec[sg_r[g]])), .pop(pop), .hv(hv), .head(lq_head[g]), .ovf(ovf_l));
            // synthesis translate_off
            always @(posedge clk) if (rst_l && pop && !hv)
                $error("ctlw slice %0d lane %0d: a response landed before its FIFO head was readable", SL, g);
            // synthesis translate_on
        end
    end else begin : g_lqf
        for (genvar g = 0; g < NL; g = g + 1) begin : g_l
            assign lq_head[g] = lq[g][lqh[g]];
        end
    end endgenerate
    always @(posedge clk or negedge rst_l) begin
        if (!rst_l) begin
            wrq <= '0; wwq <= '0; lsw_v <= '0; ldc_v <= '0; ldr_v <= '0; dp1 <= '0; dp2 <= '0; dp3 <= '0;
            for (integer b = 0; b < NL; b = b + 1) begin dq_h[b] <= '0; dq_t[b] <= '0; dq_n[b] <= '0; end
            wst_ldone <= '1; wdr_ldone <= '1; lane_ovf <= 1'b0;
            for (integer b = 0; b < NL; b = b + 1) begin
                sg_r[b] <= 3'd7; sg_on[b] <= 1'b0; cl_r[b] <= 3'd7; cl_on[b] <= 1'b0; dg_r[b] <= 3'd7; dg_on[b] <= 1'b0;
                cr[b] <= (QB+1)'(LQ); wcr[b] <= (QB+1)'(LQ); lqh[b] <= '0; lqt[b] <= '0; lqn[b] <= '0; wpend[b] <= '0;
            end
        end else begin
            for (integer b = 0; b < NL; b = b + 1) begin : lane
                reg iss, land, dr_iss, wsend, wfree;
                reg [20:0] f;
                iss = 1'b0; land = 1'b0; dr_iss = 1'b0; wsend = 1'b0; wfree = 1'b0;
                wrq[b*16 + 15] <= 1'b0; lsw_v[b] <= 1'b0; ldc_v[b] <= 1'b0; ldr_v[b] <= 1'b0; wwq[b*280 + 279] <= 1'b0;
                // ---------------- stage: source region walk (regions 0..3)
                if (wst_go) begin sg_r[b] <= 3'd0; sg_on[b] <= 1'b0; cl_r[b] <= 3'd4; cl_on[b] <= 1'b0; wst_ldone[b] <= 1'b0; end
                else if (sg_r[b] < 3'd4) begin
                    if (!sg_on[b]) begin
                        f = first_of(21'(lo[sg_r[b]] >> 3), 32'(sl_q) * NL + b);
                        if (rv[sg_r[b]] && f <= 21'(hi[sg_r[b]] >> 3)) begin
                            sg_nx[b] <= f; sg_end[b] <= 21'(hi[sg_r[b]] >> 3); sg_on[b] <= 1'b1;
                        end else sg_r[b] <= sg_r[b] + 3'd1;
                    end else if (cr[b] != 0) begin
                        iss = 1'b1;
                        wrq[b*16 +: 16] <= {1'b1, sg_nx[b][14:0]};
                        if (LQSRAM == 0) lq[b][lqt[b]] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        if (lqt[b] == '0) lq_first[b] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        lqt[b] <= lqt[b] + 1'b1;
                        if (sg_nx[b] + 21'd32 > sg_end[b]) begin sg_on[b] <= 1'b0; sg_r[b] <= sg_r[b] + 3'd1; end
                        else sg_nx[b] <= sg_nx[b] + 21'd32;
                    end
                end
                // responses land in request order
                if (wrr_q[b*257 + 256]) begin
                    land = 1'b1;
                    lsw_v[b] <= 1'b1; lsw_sec[b*LSW +: LSW] <= (MUT_W == 1) ? lq_first[b] : lq_head[b];
                    lsw_d[b*256 +: 256] <= wrr_q[b*257 +: 256];
                    lqh[b] <= lqh[b] + 1'b1;
                end
                lqn[b] <= lqn[b] + iss - land;
                if (lqn[b] == (LFB+1)'(LFD) && iss && !land) lane_ovf <= 1'b1;
                cr[b] <= cr[b] - iss + wrq_cr_q[b];
                // sink dirty-mask clears (regions 4, 5; the local span), one sector a lane an edge
                if (!wst_go && cl_r[b] < 3'd6) begin
                    if (!cl_on[b]) begin
                        f = first_of(21'(lb[cl_r[b]] >> 3), 32'(sl_q) * NL + b);
                        if (rv[cl_r[b]] && f <= 21'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3)) begin
                            cl_nx[b] <= LSW'(f); cl_end[b] <= LSW'((lb[cl_r[b]] + (hi[cl_r[b]] - lo[cl_r[b]])) >> 3);
                            cl_on[b] <= 1'b1;
                        end else cl_r[b] <= cl_r[b] + 3'd1;
                    end else begin
                        ldc_v[b] <= 1'b1; ldc_sec[b*LSW +: LSW] <= cl_nx[b];
                        if (21'(cl_nx[b]) + 21'd32 > 21'(cl_end[b])) begin cl_on[b] <= 1'b0; cl_r[b] <= cl_r[b] + 3'd1; end
                        else cl_nx[b] <= cl_nx[b] + LSW'(32);
                    end
                end
                if (!wst_go && sg_r[b] >= 3'd4 && sg_r[b] != 3'd7 && cl_r[b] >= 3'd6 &&
                    ((lqn[b] + iss - land) == 0 && (cr[b] - iss + wrq_cr_q[b]) == (QB+1)'(LQ))) wst_ldone[b] <= 1'b1;
                // ---------------- drain: sink regions 4 (O, unless STREAM) and 5 (R)
                if (wdr_go) begin dg_r[b] <= 3'd4; dg_on[b] <= 1'b0; wdr_ldone[b] <= 1'b0; end
                else if (dg_r[b] < 3'd6) begin
                    if (!dg_on[b]) begin
                        f = first_of(21'(d_lb[dg_r[b]] >> 3), 32'(sl_q) * NL + b);
                        if (d_rv[dg_r[b]] && !(dg_r[b] == 3'd4 && d_os) &&
                            f <= 21'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3)) begin
                            dg_nx[b] <= LSW'(f); dg_end[b] <= LSW'((d_lb[dg_r[b]] + (d_hi[dg_r[b]] - d_lo[dg_r[b]])) >> 3);
                            dg_on[b] <= 1'b1;
                        end else dg_r[b] <= dg_r[b] + 3'd1;
                    end else if (wcr[b] != 0) begin
                        if (!(MUT_W == 2 && 21'(dg_nx[b]) + 21'd32 > 21'(dg_end[b]))) begin
                            dr_iss = 1'b1;
                            ldr_v[b] <= 1'b1; ldr_sec[b*LSW +: LSW] <= dg_nx[b];
                            dq_s[b][dq_t[b]] <= 21'(dg_nx[b]) - d_dsec[dg_r[b]]; dq_t[b] <= dq_t[b] + 1'b1;
                        end
                        if (21'(dg_nx[b]) + 21'd32 > 21'(dg_end[b])) begin dg_on[b] <= 1'b0; dg_r[b] <= dg_r[b] + 3'd1; end
                        else dg_nx[b] <= dg_nx[b] + LSW'(32);
                    end
                end
                // read return: valid-driven (ldr_rv pin flop), the sector identity from the lane's in-flight FIFO
                begin : wpub
                    reg [7:0] mk; reg v3; reg [20:0] s3;
                    mk = MUT_DIRTY ? 8'hFF : ldr_dm_q[b*8 +: 8];
                    v3 = ldr_rv_q[b]; s3 = dq_s[b][dq_h[b]];
                    if (v3) dq_h[b] <= dq_h[b] + 1'b1;
                    dq_n[b] <= dq_n[b] + dr_iss - v3;
                    if (v3) begin
                        if (mk != 8'd0) begin
                            wsend = 1'b1;
                            wwq[b*280 +: 280] <= {1'b1, s3[14:0], ldr_d_q[b*256 +: 256], mk};
                        end else wfree = 1'b1;
                    end
                end
                wcr[b] <= wcr[b] - dr_iss + wfree + wwq_cr_q[b];
                wpend[b] <= wpend[b] + wsend - wwq_done_q[b];
                if (!wdr_go && dg_r[b] >= 3'd6 && dg_r[b] != 3'd7 && !dr_iss && (dq_n[b] - ldr_rv_q[b]) == 0 &&
                    (MUT_W == 3 || ((wpend[b] + wsend - wwq_done_q[b]) == 0 && (wcr[b] - dr_iss + wfree + wwq_cr_q[b]) == (QB+1)'(LQ)))) wdr_ldone[b] <= 1'b1;
            end
        end
    end
    always @(posedge clk or negedge rst_l)
        if (!rst_l) begin wst_dn <= 1'b1; wdr_dn <= 1'b1; ovf <= 1'b0; end
        else begin wst_dn <= (&wst_ldone) && dn_st_q; wdr_dn <= (&wdr_ldone) && dn_dr_q; ovf <= lane_ovf || dn_ov_q; end
endmodule
