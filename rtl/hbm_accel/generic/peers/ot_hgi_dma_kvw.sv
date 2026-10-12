`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_dma_kvw (hbm-fq/dma 2026-10-11): the DMA mover's KV WRITE-BACK ENGINE (ot_hgi_dma_mover KVW = 1, needs VR2 = 1).
// Budget: ds_hbm op DMA.KVWB_DS, one 2,048 B row a record at 60 cycles (>= 35.5 B / cycle sustained at target).  The
// sector engine moves one 32 B sector a cycle at best and, on a VM source, keeps one sector in flight a read lane and drains
// one landed sector a cycle into one landing RAM; its write lane takes one request every second cycle (request register
// set from its own valid).  This engine takes every raw VM -> HBM row copy (VM source, HBM linear destination, FP32 / U32
// words on both sides, element strides 1, VM rows of whole sectors, 32 B aligned destination rows) and runs it as a
// 64 B / cycle stream:
//   I  issue: an address generator walks (row, sector) and issues TWO consecutive VM sectors a cycle on the VM DMA wide
//      READ group (lanes s[4:0] and s[4:0] + 1), up to two in flight a lane (64 sectors = one 2 KB row in flight), against
//      the group's per-lane credits (the mover's counters) and the grant; every issued sector takes the next slot of a
//      512-slot two-bank buffer (slot q: bank q[0], row q[8:1]) and pushes {lane, last of move} into the issue-order FIFO.
//   H  hold: a lane's responses (in order a lane) land in its two hold entries (written from the response pins).
//   D  drain (two stages): the issue-order FIFO's head pair is taken when held (D1, registered one-hot entry selects, one a
//      bank), the selected entries go through one AND-OR rung each into the bank write registers (D2): two sectors a cycle
//      in issue order, one a bank.  A move's last sector written = its SOURCE CONSUMED (src pulse: the posted retire).
//   W  write: four write STREAMS, one a stack: a move is dispatched (in order) to its destination stack's stream when that
//      stream is free; a stream walks the move's destination rows over its slot range.  Each bank's read port serves one
//      stream a cycle (rotating priority among the streams whose next slot is in that bank, written, and whose lane FIFO
//      has room): up to two sectors a cycle on two stacks.  Two edges after the read the sector enters its stack lane's
//      4-entry output ring (4 reservations taken at the read) whose registered head = the lane request (full
//      sector, all strobes; the lane's ready only clears the head and advances the pointer);
//      acknowledgements are counted a lane.  Slots are released by the oldest unread slot (buffer room for the issue).
// The engine accepts the next move as soon as the descriptor FIFO (4) has room: a posted move's HBM writes drain while the
// next move's source is read.  done pulses once when every accepted move's every write is acknowledged (the mover's FENCE
// and any non-KVW move wait for idle).
// MUT 5 (bench): the second drain port takes the head's hold entry (the wrong sector is written).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_kvw_core #(
    parameter integer MUT = 0,
    parameter integer OWN_B0 = 1          // 1: bank 0 is this engine's own macro (a hardened element of its own, the textbook
                                          //    split 10-11); 0: bank 0 = the mover's landing RAM on the b0_* ports
) (
    input  wire          clk,
    input  wire          rn,
    // move descriptor (from the mover's command station)
    input  wire          c_v,
    output reg           c_rdy,
    input  wire [14:0]   c_vs,          // VM sector of row 0 (the read group's 15-bit sector)
    input  wire [14:0]   c_vst,         // VM row stride, sectors
    input  wire [31:0]   c_ds,          // HBM destination sector of row 0 {stack 2, stack-local sector 30}
    input  wire [31:0]   c_dst,         // HBM row stride, sectors
    input  wire [17:0]   c_ns,          // sectors a row
    input  wire [19:0]   c_m,           // rows
    // VM DMA wide read group (the mover's pin-flopped grant and its per-lane credit counters)
    input  wire          g_gnt,
    input  wire [32*6-1:0] g_cr,
    output wire [511:0]  kq,            // lane requests {v, sector 15} x 32 (ORed into vr2q by the mover)
    output wire          kq_creq,       // this engine needs the group (reads to issue or in flight)
    // the two hold tiles (ot_hgi_dma_kvw_hold, lanes 0-15 / 16-31; textbook split 10-11): response valids (registered in the
    // tile), the bank-port data of each tile (registered AND-OR of its hold entries), the registered one-hot entry selects
    input  wire [31:0]   h_v,
    input  wire [4*256-1:0] h_d,       // {tile 1 port 1, tile 1 port 0, tile 0 port 1, tile 0 port 0}
    output wire [63:0]   h_sel0,
    output wire [63:0]   h_sel1,
    output reg           h_act,
    // buffer bank 0 = the mover's landing RAM (shared: the sector engine is idle while this engine is busy)
    output reg           b0_we,
    output reg  [7:0]    b0_wa,
    output reg  [255:0]  b0_wd,
    output reg           b0_re,
    output reg  [7:0]    b0_ra,
    input  wire [255:0]  b0_rd,
    // HBM write lanes (one a stack)
    output wire [3:0]    kw_v,
    input  wire [3:0]    kw_rdy,
    output wire [4*37-1:0] kw_addr,
    output wire [4*256-1:0] kw_wdata,
    input  wire [3:0]    r_rsp_v,
    input  wire [3:0]    r_rsp_we,
    output wire [3:0]    kw_wo,         // lanes with this engine's writes in flight (their responses are acknowledgements)
    output reg           src,           // pulse: a move's last source sector is in the buffer
    output reg           done,          // pulse: every accepted move's every write acknowledged
    output reg           idle
);
    // ================================================================ descriptor FIFO (two readers: issue, write)
    reg [14:0] f_vs [0:3], f_vst [0:3]; reg [31:0] f_ds [0:3], f_dst [0:3]; reg [17:0] f_ns [0:3]; reg [19:0] f_m [0:3];
    reg [2:0] f_t, f_i, f_w;
    reg st_v; reg [14:0] st_vs, st_vst; reg [31:0] st_ds, st_dst; reg [17:0] st_ns; reg [19:0] st_m;                                // tail, issue head, write head (mod 8 counters, 4 entries)
    // ================================================================ issue (I)
    reg        i_act; reg [14:0] i_vs, i_vnx, i_vst; reg [17:0] i_left, i_ns; reg [19:0] i_rows;
    wire       i_le1 = i_left == 18'd1, i_eq2 = i_left == 18'd2;      // registered-input compares (parallel to the decision)
    wire [14:0] i_vs1 = i_vs + 15'd1, i_vs2 = i_vs + 15'd2; wire [17:0] i_lm1 = i_left - 18'd1, i_lm2 = i_left - 18'd2;
    reg [1:0]  occ [0:31];                                  // a lane's sectors issued, not drained (<= 2: its hold entries)
    reg [31:0] kqv, kqv_d; reg [14:0] kq_s [0:31];          // valid (reset) / sector (no reset) a lane
    genvar gk;
    for (gk = 0; gk < 32; gk = gk + 1) begin : g_kq
        assign kq[gk*16 +: 16] = {kqv[gk], kq_s[gk] & {15{kqv[gk]}}};
    end
    always @(posedge clk) if (pi_n != 2'd0) begin                // the applied decision's sectors (no reset)
        kq_s[pi_l0] <= pi_vs; if (pi_n == 2'd2) kq_s[pi_l1] <= 15'(pi_vs + 15'd1);
    end                                  // lanes with a request in kq / one edge earlier (not yet in gcr_q)
    // registered boundary (standalone element): the grant and the mover's credit counters are pin-flopped; the requests of
    // the last two edges are not in gcr_q yet, so a lane needs more credits than those
    reg gnt_q; reg [32*6-1:0] gcr_q;
    reg [9:0]  q_iss;                                       // slots issued (mod 1024, 512 slots)
    reg        buf_ok;                                      // registered: >= 8 free slots
    // issue-order FIFO {lane 5, last of move 1}
    reg [5:0]  iof [0:63]; reg [5:0] o_t, o_h; reg [6:0] o_n;
    // hbm-fq/dma 10-11 (class 5): the issue decision is made on registered state with the unapplied (previous) decision
    // counted exactly, registered (pi_*), and applied on the next edge (kq, kqv, the issue-order FIFO, occupancy, slots).
    // The cursor's next values are computed in parallel with the decision and selected by it.
    reg [1:0]  ok_n; reg [4:0] l0, l1; reg i_rend, i_last;
    reg [1:0]  pi_n; reg [4:0] pi_l0, pi_l1; reg [14:0] pi_vs; reg pi_last;   // the registered (unapplied) decision
    function automatic [2:0] ipend(input [4:0] l);           // occupancy / credits the unapplied decision takes on lane l
        ipend = 3'((pi_n != 2'd0 && pi_l0 == l) ? 1 : 0) + 3'((pi_n == 2'd2 && pi_l1 == l) ? 1 : 0);
    endfunction
    always @* begin : idec
        reg ok0, ok1; reg [2:0] p0, p1;
        l0 = i_vs[4:0]; l1 = 5'(i_vs[4:0] + 5'd1);
        p0 = ipend(l0); p1 = ipend(l1);
        ok0 = i_act && gnt_q && buf_ok && 3'(occ[l0]) + p0 < 3'd2 &&
              gcr_q[l0*6 +: 6] > 6'(3'(kqv[l0]) + 3'(kqv_d[l0]) + p0);
        ok1 = ok0 && !i_le1 && 3'(occ[l1]) + p1 < 3'd2 &&
              gcr_q[l1*6 +: 6] > 6'(3'(kqv[l1]) + 3'(kqv_d[l1]) + p1);
        ok_n = ok1 ? 2'd2 : ok0 ? 2'd1 : 2'd0;
        i_rend = ok1 ? i_eq2 : ok0 ? i_le1 : 1'b0;          // this decision ends the row
        i_last = i_rend && i_rows == 20'd1;                 // ... and the move
    end
    reg owed;
    assign kq_creq = owed;                                  // the group is held from the accept until done (no re-grant gap)
    // ================================================================ hold (H) + drain (D1, D2)
    reg [31:0] hr; reg [1:0] hc [0:31];                     // read entry, held count (the entries live in the hold tiles)
    reg [31:0] h_vq;                                        // the tiles' response valids, pin-flopped
    reg        d_v [0:1]; reg [63:0] d_sel [0:1];
    assign h_sel0 = d_sel[0]; assign h_sel1 = d_sel[1]; reg [7:0] d_a [0:1]; reg d_last [0:1];   // D1 registers, per bank
    reg [9:0]  q_drn;                                       // slots drained (in issue order)
    // hbm-fq/dma 10-11 (class 5): the drain decides on a REGISTERED 2-entry window of the issue-order FIFO (w0 / w1, wv
    // valid entries) and on hold counts corrected by the unapplied (registered) previous pop pd_*; the hold counts,
    // read pointers, occupancy and the one-hot bank selects are applied on the next edge.
    reg [1:0]  dn; reg [5:0] e0, e1; reg e0_ok, e1_ok; reg [5:0] x0, x1;   // drain pick (hold entry indices x = 2 lane + entry)
    reg [5:0]  w0, w1; reg [1:0] wv;                        // the window: iof[o_h], iof[o_h + 1]
    reg [1:0]  pd_n; reg [4:0] pd_l0, pd_l1; reg [5:0] pd_x0, pd_x1; reg pd_last0, pd_last1; reg [9:0] pd_q;
    function automatic [1:0] dpend(input [4:0] l);
        dpend = 2'((pd_n != 2'd0 && pd_l0 == l) ? 1 : 0) + 2'((pd_n == 2'd2 && pd_l1 == l) ? 1 : 0);
    endfunction
    always @* begin : dpick
        reg [1:0] h0, h1, q0, q1; reg r0_, r1_;
        e0 = w0; e1 = w1;
        q0 = dpend(e0[5:1]); q1 = dpend(e1[5:1]);
        h0 = hc[e0[5:1]] - q0; h1 = hc[e1[5:1]] - q1;
        r0_ = hr[e0[5:1]] ^ q0[0]; r1_ = hr[e1[5:1]] ^ q1[0];
        e0_ok = wv != 2'd0 && h0 != 2'd0;
        e1_ok = e0_ok && wv == 2'd2 && !e0[0] && ((e1[5:1] != e0[5:1]) ? h1 != 2'd0 : h1 == 2'd2);
        x0 = {e0[5:1], r0_};
        x1 = {e1[5:1], (e1[5:1] == e0[5:1]) ? !r1_ : r1_};
        if (MUT == 5) x1 = x0;
        dn = e1_ok ? 2'd2 : e0_ok ? 2'd1 : 2'd0;
    end
    // D2: the selects go to the hold tiles (registered there), their AND-OR outputs come back registered: the bank write
    // registers take the OR of the two tiles two edges after the select (d_v / d_a / d_last delayed to match)
    reg d_v2 [0:1], d_v3 [0:1]; reg [7:0] d_a2 [0:1], d_a3 [0:1]; reg d_l2 [0:1], d_l3 [0:1];
    reg        b1_we; reg [7:0] b1_wa; reg [255:0] b1_wd; reg b1_re; reg [7:0] b1_ra; wire [255:0] b1_rd;
    reg        bw_last;                                     // a move's last sector is in the bank write registers
    reg [9:0]  w_cnt;                                       // slots written into the buffer
    wire [255:0] b0_rdi;
    if (OWN_B0 != 0) begin : g_b0
        ot_sram_1r1w_256x256_m2_r2c2 u_b0 (.clk(clk), .r_ce_in(b0_re), .r_addr_in(b0_ra), .rd_out(b0_rdi),
            .w_ce_in(b0_we), .w_addr_in(b0_wa), .wd_in(b0_wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end else begin : g_b0x
        assign b0_rdi = b0_rd;
    end
    ot_sram_1r1w_256x256_m2_r2c2 u_b1 (.clk(clk), .r_ce_in(b1_re), .r_addr_in(b1_ra), .rd_out(b1_rd),
        .w_ce_in(b1_we), .w_addr_in(b1_wa), .wd_in(b1_wd), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    // ================================================================ write side (W): four streams, one a stack
    reg [9:0]  f_q [0:3];                                   // a move's first slot (set when the issue side loads it)
    reg [3:0]  w_act; reg [9:0] w_q [0:3]; reg [31:0] w_ds [0:3], w_dnx [0:3], w_dst [0:3]; reg [17:0] w_left [0:3], w_ns [0:3];
    reg [19:0] w_rows [0:3];
    reg [2:0]  res [0:3];                                   // lane FIFO entries + reservations
    reg [1:0]  pr [0:1];                                    // a bank's rotating stream priority
    reg        m1_v [0:1], m2_v [0:1]; reg [1:0] m1_l [0:1], m2_l [0:1]; reg [31:0] m1_s [0:1], m2_s [0:1];   // read pipes a bank
    // the lane's REGISTERED request (textbook audit 10-11: no flop FIFO behind it): a 4-entry output ring a lane, written
    // straight from the buffer read, presented by a registered head pointer; the lane's ready only clears the head's valid
    // and advances the pointer.  4 reservations (taken at the buffer read) cover the read -> present -> release loop.
    reg [3:0] oa_v [0:3]; reg [31:0] oa_s [0:15]; reg [255:0] oa_d [0:15]; reg [1:0] op [0:3], ot [0:3];
    reg [3:0] oh [0:3];                                     // the head pointer one-hot (registered): AND-OR output pick
    reg [3:0]  w_acc, w_ack; reg [6:0] wo [0:3];
    wire [3:0] rl;
    wire [3:0] oh_v, x_v, q_ld; wire [31:0] oh_s [0:3]; wire [255:0] oh_d [0:3];
    reg  [3:0] q_v, k_v; reg [31:0] q_s [0:3], k_s [0:3]; reg [255:0] q_d [0:3], k_d [0:3];
    // a stream's next slot is readable: written (w_cnt - q in 1 .. 512)
    // hbm-fq/dma 10-11 (cal cbf118fb5 2_1_floorplan WNS -361 ps into w_ds[1][31]: slot-distance subtract + compare + the
    // rotating pick + the 32-b destination increment / row-end mux in one cycle): the write-side decision is PIPELINED.
    // R0 registers each stream's readiness for its current slot (r0) and for the next one (r1, as if granted now); R1
    // picks on r1 for a stream granted in the previous cycle, else r0.  The destination keeps a registered +1 (w_dsn,
    // w_dnx1) and a registered row-end flag (w_lst): the grant only selects between registers.
    reg [3:0]  w_rdy, r0, r1, lg, w_lst; reg [31:0] w_dsn [0:3], w_dnx1 [0:3]; reg [1:0] g_s [0:1]; reg [1:0] g_v;
    reg [3:0]  c0, c1;                                      // combinational R0 terms
    always @* begin : wr0
        for (integer t = 0; t < 4; t = t + 1) begin : rd
            reg [9:0] d0, d1; d0 = w_cnt - w_q[t]; d1 = w_cnt - 10'(w_q[t] + 10'd1);
            c0[t] = w_act[t] && d0 != 10'd0 && (!d0[9] || d0 == 10'd512) && res[t] < 3'd4;
            c1[t] = w_act[t] && !(w_lst[t] && w_rows[t] == 20'd1) && d1 != 10'd0 && (!d1[9] || d1 == 10'd512) && res[t] < 3'd3;
        end
    end
    always @* begin : wpick
        for (integer t = 0; t < 4; t = t + 1) w_rdy[t] = lg[t] ? r1[t] : r0[t];
        for (integer b = 0; b < 2; b = b + 1) begin
            g_v[b] = 1'b0; g_s[b] = 2'd0;
            for (integer t = 3; t >= 0; t = t - 1) begin : pk
                reg [1:0] c; c = 2'(pr[b] + 2'(t));
                if (w_rdy[c] && w_q[c][0] == 1'(b)) begin g_v[b] = 1'b1; g_s[b] = c; end
            end
        end
    end
    // the move to dispatch (the oldest the issue side has loaded) and the oldest unread slot
    wire [1:0] f_stk = f_ds[f_w[1:0]][31:30];
    wire       w_disp = f_w != f_i && !w_act[f_stk];
    // the oldest unread slot (buffer room), PIPELINED (route ebb3d0692: f_w -> buf_ok 30 levels / 1,110 ps): R1 registers
    // each stream's / the undispatched move's distance from the issue count, R2 their max; buf_ok takes it with a margin
    // for the 3 edges of issue it lags (<= 2 slots an edge)
    reg  [9:0] ud [0:4]; reg [9:0] used;
    genvar gl;
    for (gl = 0; gl < 4; gl = gl + 1) begin : g_lane
        // ring head (registered pointer, AND-OR pick) -> the lane's OUTPUT REGISTER pair (route 89c140d31: the AND-OR to the
        // kw_wdata pins missed the 0.2 T output budget by 35-75 ps, and kw_rdy -> pop -> res / ring state missed the input
        // budget by 63 ps).  q = presented request (drives the pins straight from flops), k = skid entry.  The ring hands its
        // head over when the skid is empty (registered); kw_rdy only enables the q load and the two valids.
        assign oh_v[gl] = |(oa_v[gl] & oh[gl]);
        assign oh_s[gl] = (oa_s[gl*4] & {32{oh[gl][0]}}) | (oa_s[gl*4+1] & {32{oh[gl][1]}}) |
                         (oa_s[gl*4+2] & {32{oh[gl][2]}}) | (oa_s[gl*4+3] & {32{oh[gl][3]}});
        assign oh_d[gl] = (oa_d[gl*4] & {256{oh[gl][0]}}) | (oa_d[gl*4+1] & {256{oh[gl][1]}}) |
                         (oa_d[gl*4+2] & {256{oh[gl][2]}}) | (oa_d[gl*4+3] & {256{oh[gl][3]}});
        assign x_v[gl] = oh_v[gl] && !k_v[gl];
        assign q_ld[gl] = !q_v[gl] || kw_rdy[gl];
        assign kw_v[gl] = q_v[gl];
        assign kw_addr[gl*37 +: 37] = {q_s[gl], 5'd0};
        assign kw_wdata[gl*256 +: 256] = q_d[gl];
        always @(posedge clk) begin : oq_d                      // datapath: no reset
            if (x_v[gl]) begin k_s[gl] <= oh_s[gl]; k_d[gl] <= oh_d[gl]; end
            if (q_ld[gl] && (k_v[gl] || x_v[gl])) begin q_s[gl] <= k_v[gl] ? k_s[gl] : oh_s[gl]; q_d[gl] <= k_v[gl] ? k_d[gl] : oh_d[gl]; end
        end
        always @(posedge clk or negedge rl[3]) begin : oq_v
            if (!rl[3]) begin q_v[gl] <= 1'b0; k_v[gl] <= 1'b0; end
            else begin
                if (q_ld[gl]) q_v[gl] <= k_v[gl] || x_v[gl];
                k_v[gl] <= (k_v[gl] || x_v[gl]) && !q_ld[gl];
            end
        end
        assign kw_wo[gl] = wo[gl] != 7'd0 || w_acc[gl];
    end
    // ================================================================ registers
    // reset: four relayed regions (textbook audit 10-11: the port reset reached 3,418 loads), one a section; datapath
    // registers carry no reset
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rn), .rst_n(rl));
    always @(posedge clk or negedge rl[0]) begin
        if (!rl[0]) begin
            f_t <= 3'd0; c_rdy <= 1'b0; st_v <= 1'b0; src <= 1'b0; done <= 1'b0; idle <= 1'b1; owed <= 1'b0;
        end else begin
            src <= bw_last; done <= 1'b0;
            // ---- descriptors
            // command station (pin flops): the accepted descriptor enters the FIFO one edge later
            st_v <= c_v && c_rdy;
            if (c_v && c_rdy) begin st_vs <= c_vs; st_vst <= c_vst; st_ds <= c_ds; st_dst <= c_dst; st_ns <= c_ns; st_m <= c_m; owed <= 1'b1; end
            if (st_v) begin
                f_vs[f_t[1:0]] <= st_vs; f_vst[f_t[1:0]] <= st_vst; f_ds[f_t[1:0]] <= st_ds; f_dst[f_t[1:0]] <= st_dst;
                f_ns[f_t[1:0]] <= st_ns; f_m[f_t[1:0]] <= st_m; f_t <= f_t + 3'd1;
            end
            c_rdy <= 3'(f_t + {2'd0, st_v} - f_w) < 3'd2 && !(c_v && c_rdy) && !st_v;   // registered: FIFO + station <= 3
            // ---- completion
            idle <= !owed && !(c_v && c_rdy) && !st_v;
            if (owed && f_t == f_w && !i_act && o_n == 7'd0 && pi_n == 2'd0 && pd_n == 2'd0 && !d_v[0] && !d_v[1] &&
                !d_v2[0] && !d_v2[1] && !d_v3[0] && !d_v3[1] && !b0_we && !b1_we && w_act == 4'd0 && !m1_v[0] && !m1_v[1] && !m2_v[0] && !m2_v[1] &&
                oa_v[0] == 4'd0 && q_v == 4'd0 && k_v == 4'd0 && oa_v[1] == 4'd0 && oa_v[2] == 4'd0 && oa_v[3] == 4'd0 && w_acc == 4'd0 && w_ack == 4'd0 &&
                wo[0] == 7'd0 && wo[1] == 7'd0 && wo[2] == 7'd0 && wo[3] == 7'd0 && !st_v) begin
                // every accepted move drained (a move accepted on this edge stays owed: its own done comes later)
                owed <= c_v && c_rdy; done <= 1'b1; idle <= !(c_v && c_rdy);
            end
        end
    end
    always @(posedge clk or negedge rl[1]) begin
        if (!rl[1]) begin
            f_i <= 3'd0; pi_n <= 2'd0; i_act <= 1'b0; kqv <= 32'd0; kqv_d <= 32'd0; gnt_q <= 1'b0; gcr_q <= '0; q_iss <= 10'd0; buf_ok <= 1'b0;
            o_t <= 6'd0; o_n <= 7'd0;
        end else begin
            // ---- issue
            kqv <= 32'd0; kqv_d <= kqv; gnt_q <= g_gnt; gcr_q <= g_cr;
            if (!i_act && f_i != f_t) begin
                i_act <= 1'b1; i_vs <= f_vs[f_i[1:0]]; i_vnx <= f_vs[f_i[1:0]] + f_vst[f_i[1:0]]; i_vst <= f_vst[f_i[1:0]];
                i_left <= f_ns[f_i[1:0]]; i_ns <= f_ns[f_i[1:0]]; i_rows <= f_m[f_i[1:0]]; f_i <= f_i + 3'd1;
                f_q[f_i[1:0]] <= q_iss + 10'(pi_n);                 // (the unapplied decision's slots come first)
            end
            // decide (cursor now; everything else from the registered decision on the next edge)
            pi_n <= ok_n; pi_l0 <= l0; pi_l1 <= l1; pi_vs <= i_vs; pi_last <= i_last;
            if (ok_n != 2'd0) begin
                if (i_rend) begin
                    i_left <= i_ns; i_rows <= i_rows - 20'd1; i_vs <= i_vnx; i_vnx <= i_vnx + i_vst;
                    if (i_last) i_act <= 1'b0;
                end else begin i_vs <= (ok_n == 2'd2) ? i_vs2 : i_vs1; i_left <= (ok_n == 2'd2) ? i_lm2 : i_lm1; end
            end
            // apply the registered decision
            if (pi_n != 2'd0) begin
                kqv[pi_l0] <= 1'b1;
                iof[o_t] <= {pi_l0, pi_n == 2'd1 && pi_last};
                if (pi_n == 2'd2) begin
                    kqv[pi_l1] <= 1'b1;
                    iof[6'(o_t + 6'd1)] <= {pi_l1, pi_last};
                end
                o_t <= o_t + 6'(pi_n); q_iss <= q_iss + 10'(pi_n);
            end
            for (integer t = 0; t < 4; t = t + 1) ud[t] <= w_act[t] ? 10'(q_iss - w_q[t]) : 10'd0;
            ud[4] <= (f_w != f_i) ? 10'(q_iss - f_q[f_w[1:0]]) : 10'd0;
            begin : umax
                reg [9:0] m01, m23, m; m01 = (ud[0] > ud[1]) ? ud[0] : ud[1]; m23 = (ud[2] > ud[3]) ? ud[2] : ud[3];
                m = (m01 > m23) ? m01 : m23; used <= (m > ud[4]) ? m : ud[4];
            end
            buf_ok <= {1'b0, used} <= 11'd488;              // 512 - 8 (pending) - 16 (3-edge lag, 2 an edge + margin)
            o_n <= o_n + 7'(pi_n) - 7'(dn);
        end
    end
    always @(posedge clk or negedge rl[2]) begin
        if (!rl[2]) begin
            pd_n <= 2'd0; wv <= 2'd0; o_h <= 6'd0; hr <= 32'd0; q_drn <= 10'd0; h_vq <= 32'd0; h_act <= 1'b0;
            d_v2[0] <= 1'b0; d_v2[1] <= 1'b0; d_v3[0] <= 1'b0; d_v3[1] <= 1'b0;
            for (integer b = 0; b < 32; b = b + 1) begin occ[b] <= 2'd0; hc[b] <= 2'd0; end
            d_v[0] <= 1'b0; d_v[1] <= 1'b0; b0_we <= 1'b0; b1_we <= 1'b0; bw_last <= 1'b0; w_cnt <= 10'd0;
        end else begin
            // ---- hold counts / lane occupancy
            h_vq <= h_v; h_act <= !idle;
            for (integer b = 0; b < 32; b = b + 1) begin : lanes
                reg [1:0] dd; reg ii;
                dd = dpend(5'(b));                                 // the registered (unapplied) pop
                ii = (pi_n != 2'd0 && pi_l0 == 5'(b)) || (pi_n == 2'd2 && pi_l1 == 5'(b));
                // the group's responses are this engine's only while it is busy (the sector engine reads only while it is idle)
                hc[b] <= hc[b] + 2'(h_vq[b]) - dd;
                if (dd[0]) hr[b] <= !hr[b];                         // two pops flip twice
                occ[b] <= occ[b] + 2'(ii) - dd;
            end
            // ---- drain: decide (window, pointer, slot cursor), register the decision
            o_h <= o_h + 6'(dn); q_drn <= q_drn + 10'(dn);
            pd_n <= dn; pd_l0 <= e0[5:1]; pd_l1 <= e1[5:1]; pd_x0 <= x0; pd_x1 <= x1; pd_q <= q_drn;
            pd_last0 <= dn == 2'd1 && e0[0]; pd_last1 <= dn == 2'd2 && e1[0];
            begin : win                                          // the next window: candidates o_h + 0..3, by dn
                reg [5:0] c0, c1, c2, c3; reg [6:0] av;
                c0 = iof[o_h]; c1 = iof[6'(o_h + 6'd1)]; c2 = iof[6'(o_h + 6'd2)]; c3 = iof[6'(o_h + 6'd3)];
                w0 <= (dn == 2'd0) ? c0 : (dn == 2'd1) ? c1 : c2;
                w1 <= (dn == 2'd0) ? c1 : (dn == 2'd1) ? c2 : c3;
                av = o_n - 7'(dn);                               // present (written, not popped) entries
                wv <= (av >= 7'd2) ? 2'd2 : 2'(av);
            end
            // ---- drain D1 (from the registered decision): the pair, a bank each (slot q -> bank q[0])
            for (integer b = 0; b < 2; b = b + 1) begin : d1
                reg first; first = pd_q[0] == 1'(b);              // this bank takes the head (else head + 1)
                d_v[b] <= first ? (pd_n != 2'd0) : (pd_n == 2'd2);
                d_sel[b] <= first ? (64'd1 << pd_x0) : (64'd1 << pd_x1);
                d_v2[b] <= d_v[b]; d_a2[b] <= d_a[b]; d_l2[b] <= d_last[b]; d_v3[b] <= d_v2[b]; d_a3[b] <= d_a2[b]; d_l3[b] <= d_l2[b];
                d_a[b] <= first ? pd_q[8:1] : 8'(10'(pd_q + 10'd1) >> 1);
                d_last[b] <= first ? pd_last0 : pd_last1;
            end
            // ---- drain D2: the bank write registers
            b0_we <= d_v3[0]; b0_wa <= d_a3[0]; b0_wd <= h_d[0*256 +: 256] | h_d[2*256 +: 256];
            b1_we <= d_v3[1]; b1_wa <= d_a3[1]; b1_wd <= h_d[1*256 +: 256] | h_d[3*256 +: 256];
            bw_last <= (d_v3[0] && d_l3[0]) || (d_v3[1] && d_l3[1]);
            // the macro writes on this edge: the slots are readable, a move's last sector is in the buffer
            w_cnt <= w_cnt + 10'(b0_we) + 10'(b1_we);
        end
    end
    always @(posedge clk or negedge rl[3]) begin
        if (!rl[3]) begin
            f_w <= 3'd0; b0_re <= 1'b0; b1_re <= 1'b0; w_act <= 4'd0; m1_v[0] <= 1'b0; m1_v[1] <= 1'b0; m2_v[0] <= 1'b0; m2_v[1] <= 1'b0; w_acc <= 4'd0; w_ack <= 4'd0;
            pr[0] <= 2'd0; pr[1] <= 2'd0; r0 <= 4'd0; r1 <= 4'd0; lg <= 4'd0; w_lst <= 4'd0;
            for (integer l = 0; l < 4; l = l + 1) begin res[l] <= 3'd0; op[l] <= 2'd0; ot[l] <= 2'd0; oh[l] <= 4'd1; wo[l] <= 7'd0; oa_v[l] <= 4'd0; end
        end else begin
            // ---- write side: dispatch a move to its stack's stream; each bank serves one stream a cycle
            if (w_disp) begin
                w_act[f_stk] <= 1'b1; w_q[f_stk] <= f_q[f_w[1:0]]; w_ds[f_stk] <= f_ds[f_w[1:0]]; w_dsn[f_stk] <= f_ds[f_w[1:0]] + 32'd1;
                w_dnx[f_stk] <= f_ds[f_w[1:0]] + f_dst[f_w[1:0]]; w_dnx1[f_stk] <= f_ds[f_w[1:0]] + f_dst[f_w[1:0]] + 32'd1; w_dst[f_stk] <= f_dst[f_w[1:0]];
                w_lst[f_stk] <= f_ns[f_w[1:0]] == 18'd1; w_left[f_stk] <= f_ns[f_w[1:0]]; w_ns[f_stk] <= f_ns[f_w[1:0]]; w_rows[f_stk] <= f_m[f_w[1:0]]; f_w <= f_w + 3'd1;
            end
            b0_re <= g_v[0]; b0_ra <= w_q[g_s[0]][8:1]; b1_re <= g_v[1]; b1_ra <= w_q[g_s[1]][8:1];
            r0 <= c0; r1 <= c1;
            for (integer b = 0; b < 2; b = b + 1) begin : wg
                m1_v[b] <= g_v[b]; m1_l[b] <= g_s[b]; m1_s[b] <= w_ds[g_s[b]];
                if (g_v[b]) pr[b] <= g_s[b] + 2'd1;
                m2_v[b] <= m1_v[b]; m2_l[b] <= m1_l[b]; m2_s[b] <= m1_s[b];
            end
            for (integer t = 0; t < 4; t = t + 1) begin : wst
                reg gr; gr = (g_v[0] && g_s[0] == 2'(t)) || (g_v[1] && g_s[1] == 2'(t));
                lg[t] <= gr;
                if (gr) begin
                    w_q[t] <= w_q[t] + 10'd1;
                    if (w_lst[t]) begin
                        w_left[t] <= w_ns[t]; w_rows[t] <= w_rows[t] - 20'd1; w_lst[t] <= w_ns[t] == 18'd1;
                        w_ds[t] <= w_dnx[t]; w_dsn[t] <= w_dnx1[t]; w_dnx[t] <= w_dnx[t] + w_dst[t]; w_dnx1[t] <= w_dnx1[t] + w_dst[t];
                        if (w_rows[t] == 20'd1) w_act[t] <= 1'b0;
                    end else begin
                        w_ds[t] <= w_dsn[t]; w_dsn[t] <= w_dsn[t] + 32'd1; w_left[t] <= w_left[t] - 18'd1; w_lst[t] <= w_left[t] == 18'd2;
                    end
                end
            end
            // ---- lane FIFOs: push the read sector, pop on the lane's acceptance; acknowledgements
            for (integer l = 0; l < 4; l = l + 1) begin : lf
                reg push, pop, pb; reg [3:0] ov;
                pb = m2_v[1] && m2_l[1] == 2'(l);              // a stream (= stack) reads one bank a cycle
                push = (m2_v[0] && m2_l[0] == 2'(l)) || pb; pop = x_v[l];
                if (push) begin oa_d[l*4 + ot[l]] <= pb ? b1_rd : b0_rdi; oa_s[l*4 + ot[l]] <= pb ? m2_s[1] : m2_s[0]; ot[l] <= ot[l] + 2'd1; end
                ov = oa_v[l];
                if (pop) begin ov[op[l]] = 1'b0; op[l] <= op[l] + 2'd1; oh[l] <= {oh[l][2:0], oh[l][3]}; end
                if (push) ov[ot[l]] = 1'b1;
                oa_v[l] <= ov;
                res[l] <= res[l] + 3'(((g_v[0] && g_s[0] == 2'(l)) || (g_v[1] && g_s[1] == 2'(l))) ? 1 : 0) - 3'(pop);
                w_acc[l] <= q_v[l] && kw_rdy[l]; w_ack[l] <= r_rsp_v[l] && r_rsp_we[l] && kw_wo[l];
                wo[l] <= wo[l] + 7'(w_acc[l]) - 7'(w_ack[l]);
            end
        end
    end
endmodule
`default_nettype wire
`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_dma_kvw_hold (hbm-fq/dma 2026-10-11, textbook split of the KV engine: route ebb3d0692 had 25,124 flops on one
// clock root and 11,534 input -> register endpoints behind the 8,257-b read-group pins): one HARDENED HOLD TILE of NL read
// lanes.  Response pin flops (valid gated by the core's registered busy, data unconditional), two hold entries a lane
// (written alternately), the two bank ports' registered AND-OR of the entries picked by the core's registered one-hot
// selects (zero when no entry of this tile is picked), and the response valids registered back to the core.  Local
// clock tree; every port registered; no reset on data.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_kvw_hold #(
    parameter integer NL = 16
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NL*257-1:0] rsp,          // {v, data 256} a lane (the read group's lanes)
    input  wire              act,          // the core's registered busy
    input  wire [2*NL-1:0]   sel0,         // port 0 / 1 one-hot entry selects (entry 2 l + e), registered in the core
    input  wire [2*NL-1:0]   sel1,
    output reg  [NL-1:0]     hv,           // a response landed (registered)
    output reg  [255:0]      d0,
    output reg  [255:0]      d1
);
    reg [NL-1:0] pv, hw; reg [255:0] pd [0:NL-1]; reg [255:0] hd [0:2*NL-1];
    reg act_q; reg [2*NL-1:0] s0_q, s1_q;
    wire [0:0] rr; ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));   // relayed reset (control only)
    always @(posedge clk) begin s0_q <= sel0; s1_q <= sel1; end                                    // selects: no reset
    always @(posedge clk or negedge rr[0])
        if (!rr[0]) begin pv <= '0; hw <= '0; hv <= '0; act_q <= 1'b0; end
        else begin
            act_q <= act; hv <= pv;
            for (integer l = 0; l < NL; l = l + 1) begin
                pv[l] <= rsp[l*257 + 256] && act_q;
                if (pv[l]) hw[l] <= !hw[l];
            end
        end
    always @(posedge clk) begin : dp
        reg [255:0] o0, o1;
        for (integer l = 0; l < NL; l = l + 1) begin
            pd[l] <= rsp[l*257 +: 256];
            if (pv[l]) hd[2*l + hw[l]] <= pd[l];
        end
        o0 = 256'd0; o1 = 256'd0;
        for (integer k = 0; k < 2*NL; k = k + 1) begin
            o0 = o0 | (hd[k] & {256{s0_q[k]}}); o1 = o1 | (hd[k] & {256{s1_q[k]}});
        end
        d0 <= o0; d1 <= o1;
    end
endmodule
`default_nettype wire
`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_dma_kvw (hbm-fq/dma 2026-10-11): the KV write-back engine = composition of three hardened elements with
// registered seams: two hold tiles (read lanes 0-15 / 16-31, ot_hgi_dma_kvw_hold) and the core (ot_hgi_dma_kvw_core:
// decisions, the 2-bank buffer, the write streams, the lane rings).  Ports as before (the mover's view).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_kvw #(
    parameter integer MUT = 0,
    parameter integer OWN_B0 = 1
) (
    input  wire          clk,
    input  wire          rn,
    input  wire          c_v,
    output wire          c_rdy,
    input  wire [14:0]   c_vs,
    input  wire [14:0]   c_vst,
    input  wire [31:0]   c_ds,
    input  wire [31:0]   c_dst,
    input  wire [17:0]   c_ns,
    input  wire [19:0]   c_m,
    input  wire          g_gnt,
    input  wire [32*6-1:0] g_cr,
    output wire [511:0]  kq,
    output wire          kq_creq,
    input  wire [8256:0] vr2r,
    output wire          b0_we,
    output wire [7:0]    b0_wa,
    output wire [255:0]  b0_wd,
    output wire          b0_re,
    output wire [7:0]    b0_ra,
    input  wire [255:0]  b0_rd,
    output wire [3:0]    kw_v,
    input  wire [3:0]    kw_rdy,
    output wire [4*37-1:0] kw_addr,
    output wire [4*256-1:0] kw_wdata,
    input  wire [3:0]    r_rsp_v,
    input  wire [3:0]    r_rsp_we,
    output wire [3:0]    kw_wo,
    output wire          src,
    output wire          done,
    output wire          idle
);
    wire [31:0] h_v; wire [4*256-1:0] h_d; wire [63:0] s0, s1; wire act;
    ot_hgi_dma_kvw_hold #(.NL(16)) u_h0 (.clk(clk), .rst_n(rn), .rsp(vr2r[16*257-1:0]), .act(act), .sel0(s0[31:0]), .sel1(s1[31:0]),
        .hv(h_v[15:0]), .d0(h_d[0*256 +: 256]), .d1(h_d[1*256 +: 256]));
    ot_hgi_dma_kvw_hold #(.NL(16)) u_h1 (.clk(clk), .rst_n(rn), .rsp(vr2r[32*257-1:16*257]), .act(act), .sel0(s0[63:32]), .sel1(s1[63:32]),
        .hv(h_v[31:16]), .d0(h_d[2*256 +: 256]), .d1(h_d[3*256 +: 256]));
    ot_hgi_dma_kvw_core #(.MUT(MUT), .OWN_B0(OWN_B0)) u_core (.clk(clk), .rn(rn), .c_v(c_v), .c_rdy(c_rdy), .c_vs(c_vs), .c_vst(c_vst),
        .c_ds(c_ds), .c_dst(c_dst), .c_ns(c_ns), .c_m(c_m), .g_gnt(g_gnt), .g_cr(g_cr), .kq(kq), .kq_creq(kq_creq),
        .h_v(h_v), .h_d(h_d), .h_sel0(s0), .h_sel1(s1), .h_act(act),
        .b0_we(b0_we), .b0_wa(b0_wa), .b0_wd(b0_wd), .b0_re(b0_re), .b0_ra(b0_ra), .b0_rd(b0_rd),
        .kw_v(kw_v), .kw_rdy(kw_rdy), .kw_addr(kw_addr), .kw_wdata(kw_wdata), .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we),
        .kw_wo(kw_wo), .src(src), .done(done), .idle(idle));
endmodule
`default_nettype wire
