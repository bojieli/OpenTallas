`timescale 1ns/1ps
`default_nettype none
// FUSED.QDQ_* wide engine (tput-gate-1010, 2026-10-10; AGENTS.md throughput qualification).  The packet transport
// (ot_hgi_quant_vm_transport) moves one 8-word sector every 2 cycles with <= 4 outstanding: 14.6x its price on the DS
// kv_row_qdq record.  This engine runs the SAME arithmetic (ot_hgi_quant_decode, one 32-FP32 beat a cycle, II 1) on a VM
// lane group (the lgE chain slot the FUSED record uses in hb_quant; lane b <-> bank b, ot_hgi_vm_unit RP / W2 layout):
//   read  : a beat = 32 FP32 = 4 consecutive sectors = 4 consecutive banks -> 4 lanes in ONE cycle (rq {v, sector 15});
//           LQ credits a lane (rq_cr returns one); responses in request order per lane (rr {v, data 256});
//   lanes : a response lands in its lane's LD-deep FIFO (no slot muxing: lane b only ever holds sectors == b mod 32);
//           an NB-deep issued-beat FIFO {first lane, sectors} drives assembly: the head beat pops its 1..4 lane heads
//           the cycle all are present (a 4 x 32:1 sector select, registered) and launches into the decode in beat
//           order (rows, then beats inside a row; a row's last beat carries n mod 32 elements, other lanes 0 -- the
//           transport's beat rule).  A lane issues only while its FIFO has room for everything in flight to it;
//   write : the decode's y (32 x 16 b) -> words {y_i, 16'h0} (the transport's word) -> 4 sectors on 4 lanes in one cycle
//           (w2q {v, sector 15, data 256, mask 8}); an OD-deep result FIFO with a launch reservation (the decode has no
//           back-pressure); retire when every written sector reported done (w2q_done).
// Fast-path shapes only (the caller routes everything else to the packet transport, which keeps every other rule and
// its faults): header legal for QDQ (the transport's fields_ok), A / O VM FP32-word descriptors with inner stride 1, no
// broadcast, bases and n multiples of 8 words, row strides multiples of 8 (m > 1), ends inside VM, and A / O either
// disjoint or the identical region (in place: a beat is read before it is written).  Exactness: the same decode on the
// same beats as the transport -> word-identical O.
// MUT (bench): 1 = assembly takes sector j from lane j ^ 1 of the beat (lane-to-sector map; must FAIL).
module ot_hgi_quant_wide #(
    parameter integer NB = 16,         // issued-beat FIFO (>= read round trip + 4)
    parameter integer LD = 4,          // per-lane response FIFO depth (a lane serves 1 beat in 8)
    parameter integer OD = 32,         // result FIFO beats (>= decode latency + write stall slack)
    parameter integer LQ = 16,         // lane credits (= the VM unit's LQ for this client)
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    // command {O 256, C 256, B 256, A 256, SUT 128, header 128, valid} (ot_hgi_quant_record cmd layout)
    input  wire          go,
    input  wire [1408:0] cmd,
    output wire          idle,
    output reg           done,
    output reg           fault,
    // lane group (read)
    output reg  [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    // lane group (write)
    output reg  [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    localparam integer SW = $clog2(NB), OW = $clog2(OD), CW = $clog2(LQ + 1);
    // reset: the port drives only a local relay (design standard 2026-10-10); region 0 control, 1 pin flops, 2 decode
    wire [2:0] rr_n;
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    // ---------------------------------------------------------------- record registers
    reg busy, bad;
    reg [127:0] hdr;
    reg [19:0] n, m;
    reg [31:0] abase, obase, rs, ws;
    reg [3:0] nsec_last;                       // sectors in a row's last beat (1..4)
    reg [15:0] beats_row;                      // beats per row
    // read walk
    reg [19:0] r_row; reg [15:0] r_beat; reg [31:0] r_rowbase; reg rd_done;
    // write walk (in launch order)
    reg [39:0] sec_done, sec_iss;
    // registered boundary: every input lands in a pin flop (+1 edge on go / responses / credits)
    reg p_go; reg [1408:0] p_cmd; reg [32*257-1:0] p_wrr; reg [31:0] p_rcr, p_wcr, p_wdone;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin p_go <= 0; p_wrr <= '0; p_rcr <= 0; p_wcr <= 0; p_wdone <= 0; end
        else begin p_go <= go && !busy; p_wrr <= wrr; p_rcr <= wrq_cr; p_wcr <= wwq_cr; p_wdone <= wwq_done; end
    always @(posedge clk) if (go && !busy) p_cmd <= cmd;
    assign idle = !busy && !p_go;
    assign rg_req = busy; assign wg_req = busy;
    reg rg_ok, wg_ok;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin rg_ok <= 0; wg_ok <= 0; end
        else begin rg_ok <= busy && rg_gnt; wg_ok <= busy && wg_gnt; end
    // ---------------------------------------------------------------- lane credits
    reg [CW-1:0] rcr [0:31], wcr [0:31];
    // ---------------------------------------------------------------- per-lane response FIFOs + issued-beat FIFO
    localparam integer LW = $clog2(LD);
    reg [255:0] lf [0:31][0:LD-1];
    reg [LW-1:0] lf_h [0:31], lf_t [0:31];
    reg [LW:0] lf_n [0:31];                     // responses held
    reg [LW:0] lf_r [0:31];                     // issued, not yet popped (held + in flight)
    reg [4:0] bq_l [0:NB-1]; reg [2:0] bq_n [0:NB-1];
    reg [SW-1:0] r_tail, r_head;
    reg [SW:0] r_used;
    // ---------------------------------------------------------------- decode + result FIFO
    reg launch; reg [1023:0] lx; reg [2:0] l_nsec;
    wire vo, qfault, dfault; wire [511:0] y;
    ot_hgi_quant_decode u_dec (.clk(clk), .rst_n(rr_n[2]), .v(launch), .generic_enable(1'b1), .legacy_fp4(1'b0),
        .header(hdr), .x(lx), .vo(vo), .y(y), .fault(qfault), .decode_fault(dfault));
    // meta of launched beats (output sector base, sectors), in order
    reg [14:0] mq_sec [0:OD-1]; reg [2:0] mq_n [0:OD-1]; reg [OW-1:0] mq_h, mq_t;
    reg [511:0] od_y [0:OD-1]; reg [OW-1:0] od_h, od_t; reg [OW:0] od_n;
    reg [OW:0] resv;                            // launched, not yet written
    // write walk position (output sector base of the next launched beat)
    reg [19:0] w_row; reg [15:0] w_beat; reg [31:0] w_rowbase;
    // ---------------------------------------------------------------- combinational: read issue
    wire [31:0] r_addr = r_rowbase + {r_beat, 5'd0};
    wire [14:0] r_sec0 = r_addr[17:3];
    wire r_lastbeat = (r_beat + 16'd1 == beats_row);
    wire [2:0] r_nsec = r_lastbeat ? nsec_last[2:0] : 3'd4;
    reg r_cr_ok;
    always @* begin
        r_cr_ok = 1'b1;
        for (integer j = 0; j < 4; j = j + 1)
            if (j < r_nsec && (rcr[(r_sec0 + j) & 31] == 0 || lf_r[(r_sec0 + j) & 31] == LD)) r_cr_ok = 1'b0;
    end
    wire r_issue = busy && !bad && rg_ok && !rd_done && r_used < NB && r_cr_ok;
    // assembly: the head beat's lanes all hold a response, and a result reservation is free
    wire [4:0] h_l = bq_l[r_head]; wire [2:0] h_n = bq_n[r_head];
    reg h_ok; reg [1023:0] h_x;
    always @* begin
        h_ok = r_used != 0; h_x = '0;
        for (integer j = 0; j < 4; j = j + 1) begin : asm
            reg [4:0] l; l = 5'(h_l + ((MUT == 1) ? (j ^ 1) : j));
            if (j < h_n) begin
                if (lf_n[5'(h_l + j)] == 0) h_ok = 1'b0;
                h_x[j*256 +: 256] = lf[l][lf_h[l]];
            end
        end
    end
    wire l_fire = busy && h_ok && resv < OD;
    // write: the head result's sectors all have write credit
    wire [14:0] w_sec0 = mq_sec[od_h]; wire [2:0] w_n = mq_n[od_h];
    reg w_cr_ok;
    always @* begin
        w_cr_ok = 1'b1;
        for (integer j = 0; j < 4; j = j + 1)
            if (j < w_n && wcr[(w_sec0 + j) & 31] == 0) w_cr_ok = 1'b0;
    end
    wire w_fire = busy && !bad && wg_ok && od_n != 0 && w_cr_ok;
    // ---------------------------------------------------------------- sequential
    integer b, j;
    reg [4:0] lane;
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            busy <= 0; bad <= 0; done <= 0; fault <= 0; hdr <= 0; n <= 0; m <= 0; abase <= 0; obase <= 0; rs <= 0; ws <= 0;
            nsec_last <= 0; beats_row <= 0; r_row <= 0; r_beat <= 0; r_rowbase <= 0; rd_done <= 0;
            sec_done <= 0; sec_iss <= 0; r_tail <= 0; r_head <= 0; r_used <= 0;
            launch <= 0; l_nsec <= 0; mq_h <= 0; mq_t <= 0; od_h <= 0; od_t <= 0; od_n <= 0; resv <= 0;
            w_row <= 0; w_beat <= 0; w_rowbase <= 0; wrq <= 0; wwq <= 0;
            for (b = 0; b < 32; b = b + 1) begin rcr[b] <= LQ[CW-1:0]; wcr[b] <= LQ[CW-1:0]; lf_h[b] <= 0; lf_t[b] <= 0; lf_n[b] <= 0; lf_r[b] <= 0; end
        end else begin
            done <= 0; launch <= 0; wrq <= '0; wwq <= '0;
            if (p_go) begin
                busy <= 1; bad <= 0; fault <= 0; hdr <= p_cmd[128:1];
                n <= p_cmd[129 + 256 + 48 +: 20]; m <= p_cmd[129 + 256 + 68 +: 20];
                abase <= p_cmd[129 + 256 + 8 +: 32]; obase <= p_cmd[1153 + 8 +: 32];
                rs <= p_cmd[129 + 256 + 88 +: 32]; ws <= p_cmd[1153 + 88 +: 32];
                r_rowbase <= p_cmd[129 + 256 + 8 +: 32]; w_rowbase <= p_cmd[1153 + 8 +: 32];
                beats_row <= 16'((p_cmd[129 + 256 + 48 +: 20] + 20'd31) >> 5);
                nsec_last <= (p_cmd[129 + 256 + 48 +: 5] == 5'd0) ? 4'd4 : 4'(p_cmd[129 + 256 + 51 +: 2]);
                r_row <= 0; r_beat <= 0; rd_done <= 0; w_row <= 0; w_beat <= 0;
            end
            // ---- credits back
            for (b = 0; b < 32; b = b + 1) begin
                rcr[b] <= rcr[b] + CW'(p_rcr[b]) - CW'(r_issue && ((b - r_sec0[4:0]) & 31) < r_nsec);
                wcr[b] <= wcr[b] + CW'(p_wcr[b]) - CW'(w_fire && ((b - w_sec0[4:0]) & 31) < w_n);
            end
            // ---- read issue: one beat (<= 4 sectors) a cycle
            if (r_issue) begin
                for (j = 0; j < 4; j = j + 1) if (j < r_nsec) begin
                    lane = 5'(r_sec0 + j);
                    wrq[lane*16 +: 16] <= {1'b1, 15'(r_sec0 + j)};
                end
                r_tail <= r_tail + 1'b1;
                if (r_lastbeat) begin
                    r_beat <= 0; r_row <= r_row + 1; r_rowbase <= r_rowbase + rs;
                    if (r_row + 1 == m) rd_done <= 1;
                end else r_beat <= r_beat + 1;
            end
            // ---- responses land in their lane FIFO; issue / pop bookkeeping per lane
            for (b = 0; b < 32; b = b + 1) begin : lanes
                reg push, pop, iss;
                push = p_wrr[b*257 + 256];
                pop = l_fire && ((b - h_l) & 31) < h_n;
                iss = r_issue && ((b - r_sec0[4:0]) & 31) < r_nsec;
                if (push) lf_t[b] <= lf_t[b] + 1'b1;
                if (pop) lf_h[b] <= lf_h[b] + 1'b1;
                lf_n[b] <= lf_n[b] + (LW+1)'(push) - (LW+1)'(pop);
                lf_r[b] <= lf_r[b] + (LW+1)'(iss) - (LW+1)'(pop);
            end
            // ---- launch the head beat
            if (l_fire) begin
                launch <= 1; r_head <= r_head + 1'b1; mq_t <= mq_t + 1'b1;
                if (w_beat + 16'd1 == beats_row) begin w_beat <= 0; w_row <= w_row + 1; w_rowbase <= w_rowbase + ws; end
                else w_beat <= w_beat + 1;
            end
            r_used <= r_used + (SW+1)'(r_issue) - (SW+1)'(l_fire);
            // ---- decode results
            if (vo) begin
                od_t <= od_t + 1'b1;
                if (qfault) begin bad <= 1; fault <= 1; end
            end
            if (dfault) begin bad <= 1; fault <= 1; end
            od_n <= od_n + (OW+1)'(vo) - (OW+1)'(w_fire);
            resv <= resv + (OW+1)'(l_fire) - (OW+1)'(w_fire);
            // ---- write the head result
            if (w_fire) begin
                for (j = 0; j < 4; j = j + 1) if (j < w_n) begin : wr
                    reg [255:0] d;
                    for (integer k = 0; k < 8; k = k + 1) d[k*32 +: 32] = {od_y[od_h][(j*8 + k)*16 +: 16], 16'd0};
                    lane = 5'(w_sec0 + j);
                    wwq[lane*280 +: 280] <= {1'b1, 15'(w_sec0 + j), d, 8'hff};
                end
                od_h <= od_h + 1'b1; mq_h <= mq_h + 1'b1; sec_iss <= sec_iss + 40'(w_n);
            end
            // ---- retire
            begin : cnt
                reg [5:0] c; c = 0;
                for (b = 0; b < 32; b = b + 1) c = c + 6'(p_wdone[b]);
                sec_done <= sec_done + 40'(c);
                if (busy && !bad && rd_done && w_row == m && resv == 0 && od_n == 0 && sec_done + 40'(c) == sec_iss) begin busy <= 0; done <= 1; end
            end
            // fail closed: on a fault stop launching new reads; retire when the in-flight work drained
            if (busy && bad && r_used == 0 && od_n == resv && !launch && sec_done == sec_iss) begin busy <= 0; done <= 1; end
            // a new record starts from empty queues (last: overrides the idle-cycle bookkeeping above)
            if (p_go) begin
                sec_done <= 0; sec_iss <= 0;
                r_tail <= 0; r_head <= 0; r_used <= 0; mq_h <= 0; mq_t <= 0; od_h <= 0; od_t <= 0; od_n <= 0; resv <= 0;
            end
        end
    end
    // storage (no reset): issued-beat FIFO, lane response FIFOs, launch beat, write meta, results
    always @(posedge clk) begin
        if (r_issue) begin bq_l[r_tail] <= r_sec0[4:0]; bq_n[r_tail] <= r_nsec; end
        for (integer q = 0; q < 32; q = q + 1)
            if (p_wrr[q*257 + 256]) lf[q][lf_t[q]] <= p_wrr[q*257 +: 256];
        if (l_fire) begin
            lx <= h_x;
            mq_sec[mq_t] <= w_rowbase[17:3] + 15'({w_beat, 2'd0});
            mq_n[mq_t] <= h_n;
        end
        if (vo) od_y[od_t] <= y;
    end
    initial begin
        if (NB < 8 || (NB & (NB - 1)) != 0) $fatal(1, "ot_hgi_quant_wide: NB must be a power of two >= 8");
        if (LD < 2 || (LD & (LD - 1)) != 0) $fatal(1, "ot_hgi_quant_wide: LD must be a power of two >= 2");
        if (OD < 32 || (OD & (OD - 1)) != 0) $fatal(1, "ot_hgi_quant_wide: OD must be a power of two >= 32 (decode latency 23)");
        if ((LQ & (LQ - 1)) != 0) $fatal(1, "ot_hgi_quant_wide: LQ must be a power of two");
    end
endmodule
`default_nettype wire
