`timescale 1ns/1ps
`default_nettype none
// FUSED.QDQ_* wide engine, lane-quad physical structure (el1011-hbm-fq, 2026-10-11).  Same ports, same arithmetic, same
// beat order and same VM lane-group protocol as ot_hgi_quant_wide (read that header for the record / beat / fast-path
// rules); only the cycle structure differs, so O is word-identical.  ot_hgi_quant_wide made every decision in one
// cycle across all 32 lanes (r_issue -> 32-bit address add -> dynamic credit lookup -> 512 wrq flops + 64 counters;
// l_fire -> a 4 x 128:1 select of 256-bit sectors -> lx; w_fire -> od_y 32:1 x 512 b -> 32 x 280 wwq flops), which
// cannot close once the 32 lanes span a pin face (~800 um).  Here:
//   * issue / pop / write decisions are central and drive only a 32-bit HIT vector (one flop per lane) plus local
//     state; per-lane counters (read credits, issued-not-popped, responses held, write credits) take the hit vector
//     one edge later, and every decision subtracts the still-unapplied hit bit (exact accounting, no lost capacity);
//   * read issue walks the sector address incrementally (no 32-bit add in the issue cone);
//   * read gather: per lane quad (lanes 4q..4q+3) a free-running register holds the 4 beat slots (zero where no lane
//     of the quad pops) next to the lane FIFOs; the centre ORs the 8 quads into lx (+2 edges vs one-cycle assembly);
//   * write: a free-running central register takes od_y[od_h] (no enable fanout), 8 per-quad relay registers carry it
//     to the lane face, and each lane's wwq output flop selects its slot (4:1) (+2 edges);
//   * wrq leaves through per-lane output flops fed by the registered hit vector (+1 edge); credits / done return
//     through a relay register (+1 edge).
// Added latency per record ~5 cycles; throughput stays one 32-element beat a cycle.
// MUT (bench): 1 = assembly takes sector j from lane j ^ 1 of the beat (lane-to-sector map; must FAIL).
module ot_hgi_quant_wide_q #(
    parameter integer NB = 32,         // issued-beat FIFO (>= read round trip + 4)
    parameter integer LD = 4,          // per-lane response FIFO depth (a lane serves 1 beat in 8)
    parameter integer OD = 32,         // result FIFO beats (>= decode latency + gather + write slack)
    parameter integer LQ = 16,         // lane credits (= the VM unit's LQ for this client)
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [1408:0] cmd,
    output wire          idle,
    output reg           done,
    output reg           fault,
    output reg  [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output reg  [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    localparam integer SW = $clog2(NB), OW = $clog2(OD), CW = $clog2(LQ + 1), LW = $clog2(LD);
    wire [2:0] rr_n;                           // 0 control, 1 pin flops / lane state, 2 decode
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    // ---------------------------------------------------------------- record registers
    reg busy, bad;
    reg [127:0] hdr;
    reg [19:0] m;
    reg [31:0] rs, ws;
    reg [3:0] nsec_last;
    reg [15:0] beats_row;
    reg b1;                                    // beats_row == 1
    // read walk (incremental sector address)
    reg [19:0] r_row; reg [15:0] r_left; reg r_last; reg [14:0] r_sec; reg [31:0] r_nrowbase; reg rd_done;
    // write walk (in launch order)
    reg [19:0] w_row; reg [15:0] w_beat; reg [31:0] w_rowbase;
    reg [39:0] sec_done, sec_iss;
    // ---------------------------------------------------------------- registered boundary
    reg p_go; reg [1408:0] p_cmd; reg [32*257-1:0] p_wrr; reg [31:0] p_rcr, p_wcr, p_wdone;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin p_go <= 0; p_wrr <= '0; p_rcr <= 0; p_wcr <= 0; p_wdone <= 0; end
        else begin p_go <= go && !busy; p_wrr <= wrr; p_rcr <= wrq_cr; p_wcr <= wwq_cr; p_wdone <= wwq_done; end
    always @(posedge clk) if (go && !busy) p_cmd <= cmd;
    // credit / done relay (pin face -> centre)
    reg [31:0] q_rcr, q_wcr, q_wdone;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin q_rcr <= 0; q_wcr <= 0; q_wdone <= 0; end
        else begin q_rcr <= p_rcr; q_wcr <= p_wcr; q_wdone <= p_wdone; end
    assign idle = !busy && !p_go;
    assign rg_req = busy; assign wg_req = busy;
    reg rg_ok, wg_ok;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin rg_ok <= 0; wg_ok <= 0; end
        else begin rg_ok <= busy && rg_gnt; wg_ok <= busy && wg_gnt; end
    // ---------------------------------------------------------------- per-lane state
    reg [CW-1:0] rcr [0:31], wcr [0:31];
    reg [255:0] lf [0:31][0:LD-1];
    reg [LW-1:0] lf_h [0:31], lf_t [0:31];
    reg [LW:0] lf_n [0:31];                     // responses held, not yet popped (decided)
    reg [LW:0] lf_r [0:31];                     // issued, not yet popped (decided)
    reg [31:0] hit_r, hit_p, hit_w;             // last cycle's issue / pop / write lanes (applied to counters now)
    reg [14:0] iss_sec; reg [2:0] iss_n;        // last cycle's issued beat (wrq output flops)
    reg [1:0] pop_hl;                           // last pop's head lane [1:0] (gather slot map)
    // issued-beat FIFO
    reg [4:0] bq_l [0:NB-1]; reg [2:0] bq_n [0:NB-1];
    reg [SW-1:0] r_tail, r_head;
    reg [SW:0] r_used;
    // ---------------------------------------------------------------- decode + result FIFO
    reg launch; reg [1023:0] lx;
    wire vo, qfault, dfault; wire [511:0] y;
    ot_hgi_quant_decode u_dec (.clk(clk), .rst_n(rr_n[2]), .v(launch), .generic_enable(1'b1), .legacy_fp4(1'b0),
        .header(hdr), .x(lx), .vo(vo), .y(y), .fault(qfault), .decode_fault(dfault));
    reg [14:0] mq_sec [0:OD-1]; reg [2:0] mq_n [0:OD-1]; reg [OW-1:0] mq_h, mq_t;
    reg [511:0] od_y [0:OD-1]; reg [OW-1:0] od_h, od_t; reg [OW:0] od_n;
    reg [OW:0] resv;
    // ---------------------------------------------------------------- read issue decision
    wire [2:0] r_nsec = r_last ? nsec_last[2:0] : 3'd4;
    reg [31:0] r_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1)
        r_ok_l[b] = (rcr[b] > CW'(hit_r[b])) && ((lf_r[b] + (LW+1)'(hit_r[b])) < (LW+1)'(LD));
    reg r_cr_ok;
    always @* begin
        r_cr_ok = 1'b1;
        for (integer j = 0; j < 4; j = j + 1)
            if (j < r_nsec && !r_ok_l[5'(r_sec[4:0] + j)]) r_cr_ok = 1'b0;
    end
    wire r_issue = busy && !bad && rg_ok && !rd_done && r_used < NB && r_cr_ok;
    // ---------------------------------------------------------------- pop decision (head beat's lanes all hold a response)
    wire [4:0] h_l = bq_l[r_head]; wire [2:0] h_n = bq_n[r_head];
    reg h_ok;
    always @* begin
        h_ok = r_used != 0;
        for (integer j = 0; j < 4; j = j + 1)
            if (j < h_n && !(lf_n[5'(h_l + j)] > (LW+1)'(hit_p[5'(h_l + j)]))) h_ok = 1'b0;
    end
    wire l_fire = busy && h_ok && resv < OD;
    // ---------------------------------------------------------------- write decision
    wire [14:0] w_sec0 = mq_sec[od_h]; wire [2:0] w_n = mq_n[od_h];
    reg w_cr_ok;
    always @* begin
        w_cr_ok = 1'b1;
        for (integer j = 0; j < 4; j = j + 1)
            if (j < w_n && !(wcr[5'(w_sec0 + j)] > CW'(hit_w[5'(w_sec0 + j)]))) w_cr_ok = 1'b0;
    end
    wire w_fire = busy && !bad && wg_ok && od_n != 0 && w_cr_ok;
    // lane masks of this cycle's decisions
    function automatic [31:0] lanes(input [4:0] l0, input [2:0] nn);
        lanes = 0;
        for (integer j = 0; j < 4; j = j + 1) if (j < nn) lanes[5'(l0 + j)] = 1'b1;
    endfunction
    // ---------------------------------------------------------------- central control
    integer b;
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            busy <= 0; bad <= 0; done <= 0; fault <= 0; hdr <= 0; m <= 0; rs <= 0; ws <= 0; nsec_last <= 0; beats_row <= 0;
            b1 <= 0; r_row <= 0; r_left <= 0; r_last <= 0; r_sec <= 0; r_nrowbase <= 0; rd_done <= 0;
            sec_done <= 0; sec_iss <= 0; r_tail <= 0; r_head <= 0; r_used <= 0;
            mq_h <= 0; mq_t <= 0; od_h <= 0; od_t <= 0; od_n <= 0; resv <= 0;
            w_row <= 0; w_beat <= 0; w_rowbase <= 0;
            hit_r <= 0; hit_p <= 0; hit_w <= 0; iss_sec <= 0; iss_n <= 0; pop_hl <= 0;
        end else begin
            done <= 0;
            hit_r <= r_issue ? lanes(r_sec[4:0], r_nsec) : 32'd0;
            hit_p <= l_fire ? lanes(h_l, h_n) : 32'd0;
            hit_w <= w_fire ? lanes(w_sec0[4:0], w_n) : 32'd0;
            iss_sec <= r_sec; iss_n <= r_nsec; pop_hl <= h_l[1:0];
            if (p_go) begin
                busy <= 1; bad <= 0; fault <= 0; hdr <= p_cmd[128:1];
                m <= p_cmd[129 + 256 + 68 +: 20];
                rs <= p_cmd[129 + 256 + 88 +: 32]; ws <= p_cmd[1153 + 88 +: 32];
                r_sec <= p_cmd[129 + 256 + 8 + 3 +: 15];
                r_nrowbase <= p_cmd[129 + 256 + 8 +: 32] + p_cmd[129 + 256 + 88 +: 32];
                w_rowbase <= p_cmd[1153 + 8 +: 32];
                beats_row <= 16'((p_cmd[129 + 256 + 48 +: 20] + 20'd31) >> 5);
                r_left <= 16'((p_cmd[129 + 256 + 48 +: 20] + 20'd31) >> 5);
                b1 <= p_cmd[129 + 256 + 48 +: 20] <= 20'd32;
                r_last <= p_cmd[129 + 256 + 48 +: 20] <= 20'd32;
                nsec_last <= (p_cmd[129 + 256 + 48 +: 5] == 5'd0) ? 4'd4 : 4'(p_cmd[129 + 256 + 51 +: 2]);
                r_row <= 0; rd_done <= 0; w_row <= 0; w_beat <= 0;
            end
            // ---- read issue: one beat (<= 4 sectors) a cycle
            if (r_issue) begin
                r_tail <= r_tail + 1'b1;
                if (r_last) begin
                    r_row <= r_row + 1; r_sec <= r_nrowbase[17:3]; r_nrowbase <= r_nrowbase + rs;
                    r_left <= beats_row; r_last <= b1;
                    if (r_row + 1 == m) rd_done <= 1;
                end else begin
                    r_sec <= r_sec + 15'd4; r_left <= r_left - 1'b1; r_last <= (r_left == 16'd2);
                end
            end
            // ---- launch decision: meta in order, write walk
            if (l_fire) begin
                r_head <= r_head + 1'b1; mq_t <= mq_t + 1'b1;
                if (w_beat + 16'd1 == beats_row) begin w_beat <= 0; w_row <= w_row + 1; w_rowbase <= w_rowbase + ws; end
                else w_beat <= w_beat + 1;
            end
            r_used <= r_used + (SW+1)'(r_issue) - (SW+1)'(l_fire);
            if (vo) begin
                od_t <= od_t + 1'b1;
                if (qfault) begin bad <= 1; fault <= 1; end
            end
            if (dfault) begin bad <= 1; fault <= 1; end
            od_n <= od_n + (OW+1)'(vo) - (OW+1)'(w_fire);
            resv <= resv + (OW+1)'(l_fire) - (OW+1)'(w_fire);
            if (w_fire) begin od_h <= od_h + 1'b1; mq_h <= mq_h + 1'b1; sec_iss <= sec_iss + 40'(w_n); end
            begin : cnt
                reg [5:0] c; c = 0;
                for (b = 0; b < 32; b = b + 1) c = c + 6'(q_wdone[b]);
                sec_done <= sec_done + 40'(c);
                if (busy && !bad && rd_done && w_row == m && resv == 0 && od_n == 0 && sec_done + 40'(c) == sec_iss) begin busy <= 0; done <= 1; end
            end
            if (busy && bad && r_used == 0 && od_n == resv && sec_done == sec_iss) begin busy <= 0; done <= 1; end
            if (p_go) begin
                sec_done <= 0; sec_iss <= 0;
                r_tail <= 0; r_head <= 0; r_used <= 0; mq_h <= 0; mq_t <= 0; od_h <= 0; od_t <= 0; od_n <= 0; resv <= 0;
            end
        end
    end
    // ---------------------------------------------------------------- per-lane counters (take last cycle's hit vectors)
    always @(posedge clk or negedge rr_n[1]) begin
        if (!rr_n[1]) begin
            for (b = 0; b < 32; b = b + 1) begin rcr[b] <= LQ[CW-1:0]; wcr[b] <= LQ[CW-1:0]; lf_h[b] <= 0; lf_t[b] <= 0; lf_n[b] <= 0; lf_r[b] <= 0; end
        end else begin
            for (b = 0; b < 32; b = b + 1) begin
                rcr[b] <= rcr[b] + CW'(q_rcr[b]) - CW'(hit_r[b]);
                wcr[b] <= wcr[b] + CW'(q_wcr[b]) - CW'(hit_w[b]);
                if (p_wrr[b*257 + 256]) lf_t[b] <= lf_t[b] + 1'b1;
                if (hit_p[b]) lf_h[b] <= lf_h[b] + 1'b1;
                lf_n[b] <= lf_n[b] + (LW+1)'(p_wrr[b*257 + 256]) - (LW+1)'(hit_p[b]);
                lf_r[b] <= lf_r[b] + (LW+1)'(hit_r[b]) - (LW+1)'(hit_p[b]);
            end
        end
    end
    // ---------------------------------------------------------------- read requests: per-lane output flops
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) wrq <= '0;
        else for (b = 0; b < 32; b = b + 1)
            wrq[b*16 +: 16] <= hit_r[b] ? {1'b1, iss_sec + 15'(5'(b - iss_sec[4:0]))} : 16'd0;
    // ---------------------------------------------------------------- read gather: quad registers -> central OR
    reg [1023:0] gq [0:7];
    reg g_v;
    always @(posedge clk) begin
        for (integer q = 0; q < 8; q = q + 1) begin
            reg [1023:0] a; a = '0;
            for (integer i = 0; i < 4; i = i + 1) begin
                reg [1:0] s; s = 2'(i - pop_hl) ^ ((MUT == 1) ? 2'd1 : 2'd0);
                if (hit_p[q*4 + i]) a[s*256 +: 256] = lf[q*4 + i][lf_h[q*4 + i]];
            end
            gq[q] <= a;
        end
        begin : orq
            reg [1023:0] o; o = '0;
            for (integer q = 0; q < 8; q = q + 1) o = o | gq[q];
            lx <= o;
        end
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin g_v <= 0; launch <= 0; end
        else begin g_v <= |hit_p; launch <= g_v; end
    // ---------------------------------------------------------------- write: central register -> quad relays -> lane flops
    reg [511:0] wc_y; reg [14:0] wc_sec; reg [2:0] wc_n; reg wc_v;
    reg [511:0] wq_y [0:7]; reg [14:0] wq_sec [0:7]; reg [2:0] wq_n [0:7]; reg [7:0] wq_v;
    always @(posedge clk) begin
        wc_y <= od_y[od_h]; wc_sec <= w_sec0; wc_n <= w_n;
        for (integer q = 0; q < 8; q = q + 1) begin wq_y[q] <= wc_y; wq_sec[q] <= wc_sec; wq_n[q] <= wc_n; end
    end
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin wc_v <= 0; wq_v <= 0; wwq <= '0; end
        else begin
            wc_v <= w_fire; wq_v <= {8{wc_v}};
            for (integer q = 0; q < 8; q = q + 1)
                for (integer i = 0; i < 4; i = i + 1) begin : wl
                    reg [4:0] j; reg [255:0] d;
                    j = 5'(q*4 + i - wq_sec[q][4:0]);
                    for (integer k = 0; k < 8; k = k + 1) d[k*32 +: 32] = {wq_y[q][(j[1:0]*8 + k)*16 +: 16], 16'd0};
                    wwq[(q*4 + i)*280 +: 280] <= (wq_v[q] && j < 5'(wq_n[q])) ? {1'b1, wq_sec[q] + 15'(j), d, 8'hff} : 280'd0;
                end
        end
    // ---------------------------------------------------------------- storage (no reset)
    always @(posedge clk) begin
        if (r_issue) begin bq_l[r_tail] <= r_sec[4:0]; bq_n[r_tail] <= r_nsec; end
        for (integer q = 0; q < 32; q = q + 1)
            if (p_wrr[q*257 + 256]) lf[q][lf_t[q]] <= p_wrr[q*257 +: 256];
        if (l_fire) begin
            mq_sec[mq_t] <= w_rowbase[17:3] + 15'({w_beat, 2'd0});
            mq_n[mq_t] <= h_n;
        end
        if (vo) od_y[od_t] <= y;
    end
    initial begin
        if (NB < 8 || (NB & (NB - 1)) != 0) $fatal(1, "ot_hgi_quant_wide_q: NB must be a power of two >= 8");
        if (LD < 2 || (LD & (LD - 1)) != 0) $fatal(1, "ot_hgi_quant_wide_q: LD must be a power of two >= 2");
        if (OD < 32 || (OD & (OD - 1)) != 0) $fatal(1, "ot_hgi_quant_wide_q: OD must be a power of two >= 32");
        if ((LQ & (LQ - 1)) != 0) $fatal(1, "ot_hgi_quant_wide_q: LQ must be a power of two");
    end
endmodule
`default_nettype wire
