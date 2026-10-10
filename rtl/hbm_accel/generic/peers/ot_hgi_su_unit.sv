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
    parameter integer PAYLOAD_RESET = 1,
    parameter integer GLU = 0,
    parameter integer SLB = 16,
    parameter integer MUT_DIRTY = 0,
    parameter integer WIDE = 0,           // hgi-unitrate: 1 = ot_hgi_su_ctlw (32-lane wide stage / drain, pipelined span)
    parameter integer LQ = 8,             // WIDE: credits a lane holds (size to the lane-group round trip incl. relays)
    parameter integer LRLAT = 1,          // WIDE bench: the wide lmem model's read latency (the controller is valid-driven)
    parameter integer MUT_RV = 0,         // WIDE bench: lmem read valid 1 early / 2 late (must FAIL)
    parameter integer MUT_W = 0           // WIDE bench mutants (ot_hgi_su_ctlw)
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
    generate if (WIDE) begin : g_wctl
    ot_hgi_su_ctlw #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET), .MUT_W(MUT_W), .LQ(LQ)) u_ctl (.clk(clk),
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
    ot_hgi_su_ctl #(.N(N), .M(M), .LV(LV), .LWB(LWB), .GLU(GLU), .SLB(SLB), .MUT_DIRTY(MUT_DIRTY), .PAYLOAD_RESET(PAYLOAD_RESET)) u_ctl (.clk(clk),
        .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a),
        .rec_b(rec_b), .rec_c(rec_c), .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .vmq(vmq), .vmr(vmr), .s0_v(s0_v),
        .s0_idx(s0_idx), .s0_data(s0_data), .am_stream(am_stream), .am_rdy(am_rdy), .go(go), .ready(ready),
        .idle(idle), .vfault(vfault), .wl(wl), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data), .sw_v(sw_v),
        .sw_sec(sw_sec), .sw_data(sw_data), .dc_v(dc_v), .dc_sec(dc_sec), .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm));
        assign wrq = '0; assign wwq = '0; assign rg_req = 1'b0; assign wg_req = 1'b0;
    end endgenerate
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
    generate if (WIDE) begin : g_wmem
    ot_hgi_su_lmemw #(.N(N), .LWB(LWB), .AW(AW), .RLAT(LRLAT), .MUT_RV(MUT_RV)) u_mem (.clk(clk), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .rd_re(rd_re), .rd_addr(rd_addr), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data),
        .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm),
        .lsw_v(lsw_v), .lsw_sec(lsw_sec), .lsw_d(lsw_d), .ldc_v(ldc_v), .ldc_sec(ldc_sec), .ldr_v(ldr_v), .ldr_sec(ldr_sec),
        .ldr_d(ldr_d), .ldr_dm(ldr_dm), .ldr_rv(ldr_rv), .sr_rv(sr_rv), .bank_err(lm_bank_err));
    end else begin : g_mem
    ot_hgi_su_lmem #(.N(N), .LWB(LWB), .AW(AW)) u_mem (.clk(clk), .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .rd_re(rd_re), .rd_addr(rd_addr), .rd_q(rd_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data), .sl_v(sl_v), .sl_addr(sl_addr), .sl_data(sl_data),
        .sw_v(sw_v), .sw_sec(sw_sec), .sw_data(sw_data), .dc_v(dc_v), .dc_sec(dc_sec), .sr_v(sr_v), .sr_sec(sr_sec),
        .sr_data(sr_data), .sr_dm(sr_dm));
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
    output reg  [32*16-1:0]  wrq,          // VM wide read lane b {v, sector 15}: LQ credits a lane
    input  wire [31:0]       wrq_cr,       // a credit back (the request reached its bank)
    input  wire [32*257-1:0] wrr,          // the sector {v, data 256}, in request order
    output reg  [32*280-1:0] wwq,          // VM wide write lane b {v, sector 15, wdata 256, word mask 8}
    input  wire [31:0]       wwq_cr,       // a credit back (the write reached its bank)
    input  wire [31:0]       wwq_done,     // a write in the macro (the record retires after the last)
    // shared lane groups (ot_hgi_vm_lanearb): a burst (a record's stage / drain) holds its group from grant to release;
    // tie the grants high for a dedicated group
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt,
    output reg  [31:0]       lsw_v,        // local stage write lane b (sector, data)
    output reg  [32*(LWB-3)-1:0] lsw_sec,
    output reg  [32*256-1:0] lsw_d,
    output reg  [31:0]       ldc_v,        // local dirty clear lane b
    output reg  [32*(LWB-3)-1:0] ldc_sec,
    output reg  [31:0]       ldr_v,        // local drain read lane b: {data, dirty mask} one edge later
    output reg  [32*(LWB-3)-1:0] ldr_sec,
    input  wire [32*256-1:0] ldr_d,
    input  wire [32*8-1:0]   ldr_dm,
    input  wire [31:0]       ldr_rv,       // the lane's drain read data is valid (any latency, in request order)
    input  wire              sr_rv         // the STREAM-out sector read data is valid
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
    reg [5:0] wpend [0:31]; reg lane_ovf;
    reg [2:0]  cl_r [0:31]; reg cl_on [0:31]; reg [LSW-1:0] cl_nx [0:31]; reg [LSW-1:0] cl_end [0:31];
    reg [2:0]  dg_r [0:31]; reg dg_on [0:31]; reg [LSW-1:0] dg_nx [0:31]; reg [LSW-1:0] dg_end [0:31];
    reg [QB:0] wcr [0:31]; reg [31:0] dp1, dp2, dp3; reg [20:0] dp1_s [0:31]; reg [20:0] dp2_s [0:31]; reg [20:0] dp3_s [0:31];
    reg [31:0] wst_ldone, wdr_ldone;
    wire wst_done = &wst_ldone, wdr_done = &wdr_ldone;
    function automatic [20:0] first_of(input [20:0] lo_s, input integer b);
        first_of = lo_s + 21'((5'(b) - lo_s[4:0]) & 5'd31);
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wrq <= '0; wwq <= '0; lsw_v <= '0; ldc_v <= '0; ldr_v <= '0; dp1 <= '0; dp2 <= '0; dp3 <= '0;
            for (integer b = 0; b < 32; b = b + 1) begin dq_h[b] <= '0; dq_t[b] <= '0; dq_n[b] <= '0; end
            wst_ldone <= '1; wdr_ldone <= '1; lane_ovf <= 1'b0;
            for (integer b = 0; b < 32; b = b + 1) begin
                sg_r[b] <= 3'd7; sg_on[b] <= 1'b0; cl_r[b] <= 3'd7; cl_on[b] <= 1'b0; dg_r[b] <= 3'd7; dg_on[b] <= 1'b0;
                cr[b] <= (QB+1)'(LQ); wcr[b] <= (QB+1)'(LQ); lqh[b] <= '0; lqt[b] <= '0; lqn[b] <= '0; wpend[b] <= '0;
            end
        end else begin
            for (integer b = 0; b < 32; b = b + 1) begin : lane
                reg iss, land, dr_iss, wsend, wfree;
                reg [20:0] f;
                iss = 1'b0; land = 1'b0; dr_iss = 1'b0; wsend = 1'b0; wfree = 1'b0;
                wrq[b*16 + 15] <= 1'b0; lsw_v[b] <= 1'b0; ldc_v[b] <= 1'b0; ldr_v[b] <= 1'b0; wwq[b*280 + 279] <= 1'b0;
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
                        wrq[b*16 +: 16] <= {1'b1, sg_nx[b][14:0]};
                        lq[b][lqt[b]] <= LSW'(sg_nx[b] + dsec[sg_r[b]]);
                        lqt[b] <= lqt[b] + 1'b1;
                        if (sg_nx[b] + 21'd32 > sg_end[b]) begin sg_on[b] <= 1'b0; sg_r[b] <= sg_r[b] + 3'd1; end
                        else sg_nx[b] <= sg_nx[b] + 21'd32;
                    end
                end
                // responses land in request order
                if (wrr_q[b*257 + 256]) begin
                    land = 1'b1;
                    lsw_v[b] <= 1'b1; lsw_sec[b*LSW +: LSW] <= (MUT_W == 1) ? lq[b][0] : lq[b][lqh[b]];
                    lsw_d[b*256 +: 256] <= wrr_q[b*257 +: 256];
                    lqh[b] <= lqh[b] + 1'b1;
                end
                lqn[b] <= lqn[b] + iss - land;
                if (lqn[b] == (LFB+1)'(LFD) && iss && !land) lane_ovf <= 1'b1;
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
                        f = first_of(21'(d_lb[dg_r[b]] >> 3), b);
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
`default_nettype wire
