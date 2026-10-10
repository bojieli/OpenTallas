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
    parameter integer GLU = 0,            // 1: the SFU die body (SFU.GLU records; ot_hgi_su_record GLU mode)
    parameter integer SLB = 16,           // log2 words of the stream-0 landing region (top of the local memory)
    parameter integer MUT_DIRTY = 0       // mutant: drain whole sectors (overwrites words the op did not write)
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
    input  wire [7:0]    sr_dm
);
    localparam integer AW = 24, NR = N / 8, LW = 1 << LWB;
    // ---- the record adapter (decode) and the op it issues
    wire op_v; reg op_rdy_r; wire [669:0] op_w; reg su_idle_r, su_fault_r;
    wire [1:0] strm;
    ot_hgi_su_record #(.LEGACY(0), .GLU(GLU), .STREAM_OK(!GLU)) u_rec (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
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
    reg [39:0] macc; reg [4:0] mbit; reg [1:0] mph;        // (nr - 1) so + (ni - 1) si by shift-add
    reg [23:0] span_hi;
    // ---- VM traffic
    reg [273:0] vr; always @(posedge clk) vr <= vmr;
    reg [2:0] outst; reg [26:0] q_sec [0:3]; reg [1:0] q_h, q_t;  // outstanding requests (sectors), in order
    reg [26:0] cur_sec, end_sec;
    reg [3:0] st;
    localparam [3:0] S_IDLE = 0, S_SPAN = 1, S_MUL = 2, S_NEXTR = 3, S_STAGE = 4, S_STW = 5, S_RUN = 6, S_RUNW = 7,
                     S_DRAIN = 8, S_DRW = 9, S_DONE = 10, S_FAULT = 11, S_SOUT = 12;
    reg [2:0] dk;                                         // drain region (4 O, 5 R)
    reg [26:0] dsec, dend, rsec_d, rsec_d2, rsec_d3; reg so_w;
    reg [3:0] rp;                                         // read pipe: a sector read is in flight
    // Local-memory return pin registers; advance data, mask, valid and sector identity together.
    reg [255:0] sr_data_q; reg [7:0] sr_dm_q;
    always @(posedge clk) begin sr_data_q <= sr_data; sr_dm_q <= sr_dm; end
    reg [255:0] rd_hold; reg [7:0] rd_dm_hold;
    // ---- STREAM 0 landing (top SW words of the local memory) and the op's stream flags
    localparam integer SW = 1 << SLB;
    localparam [LWB:0] SBASE = LW - SW;
    reg [20:0] scount; reg a_s, o_s; reg s_clr;
    reg s0v_q; reg [19:0] s0i_q; reg [31:0] s0d_q;
    always @(posedge clk) begin s0v_q <= s0_v; s0i_q <= s0_idx; s0d_q <= s0_data; end
    reg [20:0] etot; reg [20:0] ebeat; reg [LWB:0] o_lb; reg amr_q;
    always @(posedge clk) amr_q <= am_rdy;
    // ---- control
    // Registered engine status at the controller boundary. The vec holds ready/idle until go;
    // capture its sticky fault with the same edge, so retirement still observes the fault.
    reg ready_q, idle_q, vfault_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin ready_q <= 1'b0; idle_q <= 1'b0; vfault_q <= 1'b0; end
        else begin ready_q <= ready; idle_q <= idle; vfault_q <= vfault; end
    end
    reg vf_seen; reg [1:0] idle_ph;
    wire [LWB:0] lbk = {alloc[LWB:3], 3'b000} + {{LWB{1'b0}}, 1'b0} + (lo[rk] & 24'd7);
    integer k2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; op_rdy_r <= 1'b1; su_idle_r <= 1'b1; su_fault_r <= 1'b0; go <= 1'b0; vmq <= 338'd0;
            sl_v <= 1'b0; sw_v <= 1'b0; dc_v <= 1'b0; sr_v <= 1'b0; rp <= 4'd0;
            outst <= 3'd0; q_h <= 2'd0; q_t <= 2'd0; vf_seen <= 1'b0; scount <= 21'd0; s_clr <= 1'b0; am_stream <= 523'd0;
        end else begin
            vmq[337] <= 1'b0; su_fault_r <= 1'b0; am_stream[0] <= 1'b0; am_stream[1] <= 1'b0;
            sl_v <= s0v_q && s0i_q < SW; sl_addr <= SBASE + s0i_q; sl_data <= s0d_q;
            sw_v <= 1'b0; dc_v <= 1'b0; sr_v <= 1'b0;
            if (s0v_q && s0i_q >= SW) begin su_fault_r <= 1'b1; st <= S_FAULT; end
            if (s_clr) scount <= {20'd0, s0v_q}; else if (s0v_q) scount <= scount + 21'd1;
            if (vfault_q && st == S_RUNW) vf_seen <= 1'b1;
            case (st)
                S_IDLE: begin
                    s_clr <= 1'b0;
                    if (op_v && op_rdy_r) begin
                        w <= op_w; wl <= op_w; op_rdy_r <= 1'b0; su_idle_r <= 1'b0; rk <= 3'd0; alloc <= 0; vf_seen <= 1'b0;
                        a_s <= strm[0]; o_s <= strm[1]; st <= S_SPAN;
                    end
                end
                S_SPAN: begin                                       // region rk: used? span start
                    rv[rk] <= used_k && !(rk == 3'd0 && a_s);
                    if (rk == 3'd0 && a_s) begin                    // A = STREAM: rows of ni, element o ni + i = idx
                        wl[40 +: 24] <= SBASE; wl[64 +: 24] <= {8'd0, ni}; wl[88 +: 24] <= 24'd1; st <= S_NEXTR;
                    end else if (rk == 3'd4 && o_s && a_s && red == 2'd0) begin
                        // O = STREAM over A = STREAM, element-wise: O aliases the stream landing region (element i is
                        // written L cycles after A[i] is read, and reads advance monotonically), so no O storage
                        wl[382 +: 24] <= SBASE; wl[406 +: 24] <= {8'd0, ni}; wl[430 +: 24] <= 24'd1;
                        lb[4] <= SBASE; rv[4] <= 1'b0; st <= S_NEXTR;
                    end else if (rk == 3'd4 && o_s) begin           // O = STREAM: a contiguous local region, no drain
                        wl[406 +: 24] <= {8'd0, ni}; wl[430 +: 24] <= 24'd1; w[406 +: 24] <= {8'd0, ni}; w[430 +: 24] <= 24'd1;
                        w[382 +: 24] <= 24'd0; wl[382 +: 24] <= 24'd0; lo[4] <= 24'd0; macc <= 40'd0; mbit <= 5'd0;
                        mph <= 2'd0; rv[4] <= 1'b1; st <= S_MUL;
                    end
                    else if (!used_k) st <= S_NEXTR;
                    else begin
                        lo[rk] <= base_k; macc <= 40'd0; mbit <= 5'd0; mph <= 2'd0; st <= S_MUL;
                    end
                    if (rk == 3'd0 && (aind != 2'd0 || w[32 +: 8] != 8'd0)) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                end
                S_MUL: begin                                        // macc = (nr - 1) so + (ni - 1) si, a bit an edge
                    if (mph == 2'd0) begin
                        if ((nr_k - 16'd1) >> mbit & 16'd1) macc <= macc + ({16'd0, so_k} << mbit);
                        if (mbit == 5'd15) begin mbit <= 5'd0; mph <= 2'd1; end else mbit <= mbit + 5'd1;
                    end else if (mph == 2'd1) begin
                        if ((ni_k - 16'd1) >> mbit & 16'd1) macc <= macc + ({16'd0, si_k} << mbit);
                        if (mbit == 5'd15) mph <= 2'd2; else mbit <= mbit + 5'd1;
                    end else begin
                        // c_pair reads A[e ^ 1]: widen A to whole pairs
                        if (rk == 3'd0 && cpair) begin lo[0] <= base_k & ~24'd1; hi[0] <= (base_k + macc[23:0]) | 24'd1; end
                        else hi[rk] <= base_k + macc[23:0];
                        st <= S_NEXTR;
                    end
                end
                S_NEXTR: begin                                      // place region rk, relocate its base
                    if (rv[rk]) begin
                        lb[rk] <= lbk;
                        alloc <= lbk + (hi[rk] - lo[rk]) + 1 + 8;
                        if (lbk + (hi[rk] - lo[rk]) + 1 > SBASE) begin su_fault_r <= 1'b1; st <= S_FAULT; end
                        case (rk)
                            3'd0: wl[40 +: 24]  <= w[40 +: 24]  - lo[0] + lbk;
                            3'd1: wl[138 +: 24] <= w[138 +: 24] - lo[1] + lbk;
                            3'd2: wl[211 +: 24] <= w[211 +: 24] - lo[2] + lbk;
                            3'd3: wl[284 +: 24] <= w[284 +: 24] - lo[3] + lbk;
                            3'd4: wl[382 +: 24] <= w[382 +: 24] - lo[4] + lbk;
                            default: wl[484 +: 24] <= w[484 +: 24] - lo[5] + lbk;
                        endcase
                    end
                    if (st != S_FAULT) begin
                        if (rk == 3'd5) begin rk <= 3'd0; st <= S_STAGE; end
                        else begin rk <= rk + 3'd1; st <= S_SPAN; end
                    end
                end
                S_STAGE: begin                                      // sources: copy the span; sinks: clear dirty masks
                    if (rk == 3'd6) st <= S_RUN;
                    else if (!rv[rk]) rk <= rk + 3'd1;
                    else begin cur_sec <= lo[rk] >> 3; end_sec <= hi[rk] >> 3; st <= S_STW; q_h <= 0; q_t <= 0; outst <= 0; end
                end
                S_STW: begin
                    if (rk >= 3'd4) begin                           // sink region: clear its dirty masks a sector an edge
                        dc_v <= 1'b1; dc_sec <= ((cur_sec << 3) - lo[rk] + lb[rk]) >> 3;
                        if (cur_sec == end_sec) begin rk <= rk + 3'd1; st <= S_STAGE; end else cur_sec <= cur_sec + 27'd1;
                    end else begin
                        // issue reads (up to 4 outstanding) and land responses in order
                        if (outst < 3'd4 && cur_sec <= end_sec && !(vr[273] && outst == 3'd4)) begin
                            vmq <= {1'b1, 1'b0, cur_sec, 5'd0, 256'd0, 32'd0, 16'h5355};
                            q_sec[q_t] <= cur_sec; q_t <= q_t + 2'd1; cur_sec <= cur_sec + 27'd1;
                        end
                        if (vr[273] && !vr[256]) begin
                            sw_v <= 1'b1; sw_sec <= (({q_sec[q_h], 3'b000} - lo[rk] + lb[rk]) & ~24'd7) >> 3;
                            sw_data <= vr[255:0]; q_h <= q_h + 2'd1;
                        end
                        outst <= outst + ((outst < 3'd4 && cur_sec <= end_sec) ? 3'd1 : 3'd0) - ((vr[273] && !vr[256]) ? 3'd1 : 3'd0);
                        if (cur_sec > end_sec && outst == ((vr[273] && !vr[256]) ? 3'd1 : 3'd0)) begin
                            rk <= rk + 3'd1; st <= S_STAGE;
                        end
                    end
                end
                S_RUN: if (ready_q && (!a_s || scount >= {5'd0, no} * {5'd0, ni})) begin
                    go <= 1'b1; st <= S_RUNW; idle_ph <= 2'd0;
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
                    if (dk == 3'd6) begin
                        if (o_s) begin etot <= {5'd0, no} * {5'd0, ni}; ebeat <= 21'd0; o_lb <= lb[4]; rp <= 4'd0; so_w <= 1'b0;
                                       st <= S_SOUT; end
                        else st <= S_DONE;
                    end
                    else if (!rv[dk] || (dk == 3'd4 && o_s)) dk <= dk + 3'd1;
                    else begin dsec <= lo[dk] >> 3; dend <= hi[dk] >> 3; st <= S_DRW; outst <= 0; rp <= 4'd0; end
                end
                S_DRW: begin                                        // dirty sectors back to VM, word-masked
                    // A sector return crosses the local-memory pin register before dirty-masked publication.
                    begin : dw
                        reg [7:0] mk; reg issue;
                        mk = MUT_DIRTY ? 8'hFF : sr_dm_q;
                        // sr_v leaves a controller flop, memory captures a sector, then the return pin captures it.
                        issue = dsec <= dend && outst + {2'd0, rp[0]} + {2'd0, rp[2]} + {2'd0, rp[3]} < 3'd4;
                        if (issue) begin sr_v <= 1'b1; sr_sec <= ({dsec, 3'b000} - lo[dk] + lb[dk]) >> 3; dsec <= dsec + 27'd1; end
                        rp[0] <= issue; rp[2] <= rp[0]; rp[3] <= rp[2]; rsec_d2 <= rsec_d; rsec_d3 <= rsec_d2;
                        if (rp[3] && mk != 8'd0)
                            vmq <= {1'b1, 1'b1, rsec_d3, 5'd0, sr_data_q,
                                    {{4{mk[7]}}, {4{mk[6]}}, {4{mk[5]}}, {4{mk[4]}}, {4{mk[3]}}, {4{mk[2]}}, {4{mk[1]}}, {4{mk[0]}}},
                                    16'h5357};
                        if (issue) rsec_d <= dsec;
`ifdef SU_DBG
                        if (rp[3]) $display("DBG drain sec %0d mk %h data %h", rsec_d3, mk, sr_data_q[31:0]);
                        if (issue) $display("DBG issue dsec %0d sr_sec %0d dend %0d", dsec, ({dsec, 3'b000} - lo[dk] + lb[dk]) >> 3, dend);
`endif
                        outst <= outst + ((rp[3] && mk != 8'd0) ? 3'd1 : 3'd0) - ((vr[273] && vr[256]) ? 3'd1 : 3'd0);
                        if (dsec > dend && !rp[0] && !rp[2] && !rp[3] && !issue && outst == ((vr[273] && vr[256]) ? 3'd1 : 3'd0)) begin
                            dk <= dk + 3'd1; st <= S_DRAIN; end
                    end
                end
                S_SOUT: if (amr_q && !rp[1] && !rp[3] && !so_w) begin         // 8 elements a beat, in element order
                    sr_v <= 1'b1; sr_sec <= (o_lb + ebeat) >> 3; so_w <= 1'b1;
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

// ---------------------------------------------------------------------------------------------------------------------
// The unit's local operand memory (behavioural; on the die the r25 SU envelope's operand macros): LW words + a dirty
// mask a sector.  The stream unit's ports read in one edge; its element / reducer writes set dirty bits; the controller
// lands STREAM words and staged sectors, clears sink dirty masks and reads drain / STREAM-out sectors (one edge).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_lmem #(
    parameter integer N = 16, LWB = 17, AW = 24, NR = N / 8
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
    input  wire              sw_v,
    input  wire [LWB-4:0]    sw_sec,
    input  wire [255:0]      sw_data,
    input  wire              dc_v,
    input  wire [LWB-4:0]    dc_sec,
    input  wire              sr_v,
    input  wire [LWB-4:0]    sr_sec,
    output reg  [255:0]      sr_data,
    output reg  [7:0]        sr_dm
);
    localparam integer LW = 1 << LWB;
    reg [31:0] lm [0:LW-1];
    reg [7:0]  dm [0:LW/8-1];
    integer l, s2, q;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) begin
            if (vi_re[l]) vi_q[32*l +: 32] <= lm[vi_addr[l*AW +: AW] & (LW - 1)];
            for (s2 = 0; s2 < 4; s2 = s2 + 1)
                if (rd_re[4*l + s2]) rd_q[(4*l + s2)*32 +: 32] <= lm[rd_addr[(4*l + s2)*AW +: AW] & (LW - 1)];
        end
        if (sr_v) begin for (q = 0; q < 8; q = q + 1) sr_data[32*q +: 32] <= lm[{sr_sec, 3'b000} + q]; sr_dm <= dm[sr_sec]; end
        if (sl_v) lm[sl_addr] <= sl_data;
        if (sw_v) for (q = 0; q < 8; q = q + 1) lm[{sw_sec, 3'b000} + q] <= sw_data[32*q +: 32];
        if (dc_v) dm[dc_sec] <= 8'd0;
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
// The stream-unit die body: the controller (ot_hgi_su_ctl: record adapter + stage / drain / STREAM) + the unchanged
// stream unit ot_hdc_v41x_vec + its local memory.  Ports as before the split (2026-10-10).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_su_unit #(
    parameter integer N = 16, M = 8, LV = 6,
    parameter integer LWB = 17,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer MUT_DIRTY = 0
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
    wire sl_v, sw_v, dc_v, sr_v; wire [LWB-1:0] sl_addr; wire [31:0] sl_data; wire [LWB-4:0] sw_sec, dc_sec, sr_sec;
    wire [255:0] sw_data, sr_data; wire [7:0] sr_dm;
    ot_hgi_su_ctl #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sw_v(sw_v),
        .sw_sec(sw_sec), .sw_data(sw_data), .dc_v(dc_v), .dc_sec(dc_sec), .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm));
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
    ot_hgi_su_lmem #(.N(N), .LWB(LWB), .AW(AW)) u_mem (.clk(clk), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .rd_re(rd_re), .rd_addr(rd_addr), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data),
        .sw_v(sw_v), .sw_sec(sw_sec), .sw_data(sw_data), .dc_v(dc_v), .dc_sec(dc_sec), .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm));
endmodule
`default_nettype wire
