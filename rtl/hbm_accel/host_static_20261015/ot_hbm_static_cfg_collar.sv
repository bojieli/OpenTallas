`timescale 1ns/1ps
`default_nettype none
// Static F20 target collar for heterogeneous programme/operand layouts (H-NETLIST cp2, 2026-10-15).
// ONE parameterised master serves every target whose local ABI is not the plain PCW row port of
// ot_static_program_target: SU (bank16/row7 programme), SFU (two striped programmes + IO start),
// IDX (programme + per-launch operands) and the TOPK/ARGMAX record issuers.
//
// Configuration only (host elastic boundary ends at the ingress); execution is one launch event plus
// compiler-fixed record cycles. No ready/credit/backpressure on any output.
//
// Target identity: tgt[7:0] is a declared identity strap (the F20 target number of this instance).
// Row address map (ingress F20 row, auto-incremented per 256-bit frame):
//   0x000-0x7FF  programme row: linear L = {page[space], addr[10:0]} into the selected space.
//                Writes must be sequential per space (L == installed high-water mark) or restart at L==0
//                (hwm := 1). This is the finite local installation validator: rows [0,hwm) are written.
//   0x800-0xBFF  operand row r=addr[9:0] (< NPR): prm[r*256+:256] := data   (held operand registers)
//   0xC00-0xDFF  record row r=addr[8:0] (< NREC): {payload221, gomask2, valid1, offset32}
//   0xE00        select: data[7:0]=space (< NS), data[8+:PAGE_W]=page of that space
//   0xE01        need:   data[s*32+:AW+1]=rows that must be installed in space s; data[128]=wait for c_done
//   other        fault
// Descriptor (F28/F2c) for tgt arms the target for the next launch; any later write disarms it.
// Launch (F30): if armed -> ready must hold (else fault); start_v pulses, records run; if not armed -> no-op
// (non-participating target). ready = armed & need written & all operand rows written & hwm>=need & !fault.
// Records: record i (row order, offsets strictly increasing) asserts go[gomask]/rec[] offset_i+1 edges
// after the edge start_v rises (offset 0 = the edge after start_v). A late/non-increasing offset faults.
// active = from launch until records exhausted, TAIL edges after the last start/go, c_busy low and
// (if requested) c_done seen.
// Pins: every input lands in a pin flop, every output is a flop Q (owner rule 19:50).
// Fixed latency (XSER=0): launch_v -> start_v = 2 edges; cfg frame -> pw_we = 2 edges; record go = offset+1
// edges after start_v. XSER=1 adds the rational crossing (stream pin + hold + 2 serial edges), a fixed value
// for each launch phase of the common 3:4 epoch (the compiler issues F30 on a known phase).
module ot_hbm_static_cfg_collar #(
    parameter integer PAGE_W=12,   // page bits per programme space (AW = PAGE_W+11)
    parameter integer NS=2,        // programme spaces (1..4)
    parameter integer NPR=1,       // operand rows of 256 b (>=1)
    parameter integer NREC=0,      // record rows (0..512)
    parameter integer NGO=1,       // record go outputs (1..2)
    parameter integer NB=2,        // client busy inputs
    parameter integer NF=1,        // client fault inputs
    parameter integer TAIL=4,
    parameter integer XSER=0,      // 1: core clk is the 3:4 serial domain, broadcast pins on clk_in (stream)
    parameter integer MUT=0,       // bench: 1 skip sequential check, 2 ready ignores need, 3 go one edge early, 4 no event seq check
    parameter integer AW=PAGE_W+11
)(
    input  wire clk, clk_in, rst_n,
    input  wire [7:0] tgt,
    input  wire cfg_v,
    input  wire [7:0] cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire desc_v,
    input  wire launch_v,
    input  wire [NB-1:0] c_busy,
    input  wire c_done,
    input  wire [NF-1:0] c_fault,
    output reg  [NS-1:0] pw_we,
    output reg  [AW-1:0] pw_addr,
    output reg  [255:0] pw_data,
    output reg  [NPR*256-1:0] prm,
    output reg  start_v,
    output reg  [NGO-1:0] go,
    output reg  [220:0] rec,
    output reg  ready, active, fault
);
    initial begin
        if (NS<1 || NS>4 || NPR<1 || NPR>1024 || NREC<0 || NREC>512 || NGO<1 || NGO>2 || PAGE_W<1 || AW>31)
            $fatal(1, "ot_hbm_static_cfg_collar: parameter out of range");
    end
    localparam integer SW = (NS>1) ? $clog2(NS) : 1;
    localparam integer RN = (NREC>0) ? NREC : 1;
    localparam integer RW = (NREC>1) ? $clog2(NREC+1) : 1;
    // ---------------- pin flops
    reg cv, dv, lv, done_q, xfault;
    reg [7:0] ct, tg;
    reg [11:0] ca;
    reg [255:0] cd;
    reg [NB-1:0] busy_q;
    reg [NF-1:0] cf_q;
    always @(posedge clk) tg <= tgt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin done_q <= 0; busy_q <= 0; cf_q <= 0; end
        else begin done_q <= c_done; busy_q <= c_busy; cf_q <= c_fault; end
    generate if (XSER == 0) begin : g_same
        // broadcast pins in the core clock (clk_in is the same root)
        always @(posedge clk) begin ct <= cfg_target; ca <= cfg_addr; cd <= cfg_data; end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin cv <= 0; dv <= 0; lv <= 0; xfault <= 0; end
            else begin cv <= cfg_v; dv <= desc_v; lv <= launch_v; xfault <= 0; end
    end else begin : g_xser
        // Rational 3:4 synchronous crossing (common-epoch family, timed by STA at the tightest edge pair):
        // stream pin flops -> held event register + 2-bit event sequence; the serial core samples sequence and
        // payload on the same edge and consumes each event exactly once. Broadcast events are >=4 stream
        // edges apart (each is a separate ingress AXI write), i.e. >=3 serial edges; a skipped sequence
        // value (event lost) faults.
        reg pv_cv, pv_dv, pv_lv; reg [7:0] p_ct; reg [11:0] p_ca; reg [255:0] p_cd;
        reg [1:0] h_seq; reg h_cv, h_dv, h_lv; reg [7:0] h_ct; reg [11:0] h_ca; reg [255:0] h_cd;
        always @(posedge clk_in) begin p_ct <= cfg_target; p_ca <= cfg_addr; p_cd <= cfg_data; end
        always @(posedge clk_in or negedge rst_n)
            if (!rst_n) begin pv_cv <= 0; pv_dv <= 0; pv_lv <= 0; h_seq <= 0; h_cv <= 0; h_dv <= 0; h_lv <= 0; end
            else begin
                pv_cv <= cfg_v; pv_dv <= desc_v; pv_lv <= launch_v;
                if (pv_cv || pv_dv || pv_lv) begin
                    h_seq <= h_seq + 1'b1; h_cv <= pv_cv; h_dv <= pv_dv; h_lv <= pv_lv;
                    h_ct <= p_ct; h_ca <= p_ca; h_cd <= p_cd;
                end
            end
        reg [1:0] s_seq, s_prev; reg s_cv, s_dv, s_lv; reg [7:0] s_ct; reg [11:0] s_ca; reg [255:0] s_cd;
        always @(posedge clk) begin s_ct <= h_ct; s_ca <= h_ca; s_cd <= h_cd; end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin s_seq <= 0; s_prev <= 0; s_cv <= 0; s_dv <= 0; s_lv <= 0; end
            else begin s_seq <= h_seq; s_prev <= s_seq; s_cv <= h_cv; s_dv <= h_dv; s_lv <= h_lv; end
        wire ev = s_seq != s_prev;
        always @(posedge clk) begin ct <= s_ct; ca <= s_ca; cd <= s_cd; end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin cv <= 0; dv <= 0; lv <= 0; xfault <= 0; end
            else begin
                cv <= ev && s_cv; dv <= ev && s_dv; lv <= ev && s_lv;
                xfault <= ev && (s_seq - s_prev) != 2'd1 && MUT != 4;
            end
    end endgenerate
    // ---------------- state
    reg [SW-1:0] sel;
    reg [PAGE_W-1:0] page [0:NS-1];
    reg [AW:0] hwm [0:NS-1];
    reg [AW:0] need [0:NS-1];
    reg need_set, wait_mask, wait_done;
    reg [NPR-1:0] loaded;
    reg armed, run;
    reg [31:0] cnt;
    reg [RW-1:0] rptr;
    reg [7:0] tail;
    reg [31:0] r_off [0:RN-1];
    reg [RN-1:0] r_val;
    reg [1:0] r_go [0:RN-1];
    reg [220:0] r_pay [0:RN-1];
    wire hit = cv && ct == tg;
    wire dhit = dv && ct == tg;
    wire [AW:0] lin = {1'b0, page[sel], ca[10:0]};
    reg inst_ok;
    integer s;
    always @* begin
        inst_ok = need_set && (&loaded);
        for (s = 0; s < NS; s = s + 1) if (hwm[s] < need[s] && MUT != 2) inst_ok = 0;
    end
    wire recs_done = (NREC == 0) || (rptr >= NREC) || !r_val[rptr];
    wire [31:0] cur_off = r_off[(NREC == 0) ? 0 : rptr];
    wire [31:0] cmp_cnt = (MUT == 3) ? cnt + 1 : cnt;
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pw_we <= 0; start_v <= 0; go <= 0; ready <= 0; active <= 0; fault <= 0;
            sel <= 0; need_set <= 0; wait_mask <= 0; wait_done <= 0; loaded <= 0; armed <= 0; run <= 0;
            cnt <= 0; rptr <= 0; tail <= 0; r_val <= 0;
            for (k = 0; k < NS; k = k + 1) begin hwm[k] <= 0; need[k] <= 0; page[k] <= 0; end
        end else begin
            pw_we <= 0; start_v <= 0; go <= 0;
            if (|cf_q || xfault) fault <= 1;
            // ------------ configuration frames
            if (hit) begin
                armed <= 0;
                if (run) fault <= 1;
                else if (!ca[11]) begin
                    if (lin == hwm[sel] || MUT == 1) begin
                        if (hwm[sel][AW]) fault <= 1;
                        else begin pw_we[sel] <= 1; pw_addr <= lin[AW-1:0]; pw_data <= cd; hwm[sel] <= lin + 1'b1; end
                    end else if (lin == 0) begin
                        pw_we[sel] <= 1; pw_addr <= 0; pw_data <= cd; hwm[sel] <= 1;
                    end else fault <= 1;
                end else if (ca[11:10] == 2'b10) begin
                    if (ca[9:0] >= NPR) fault <= 1;
                    else begin prm[ca[9:0]*256 +: 256] <= cd; loaded[ca[9:0]] <= 1; end
                end else if (ca[11:9] == 3'b110) begin
                    if (ca[8:0] >= NREC) fault <= 1;
                    else begin
                        r_off[ca[8:0]] <= cd[31:0]; r_val[ca[8:0]] <= cd[32];
                        r_go[ca[8:0]] <= cd[34:33]; r_pay[ca[8:0]] <= cd[255:35];
                        if (NGO < 2 && cd[34]) fault <= 1;
                    end
                end else if (ca == 12'hE00) begin
                    if (cd[7:0] >= NS) fault <= 1;
                    else begin sel <= cd[SW-1:0]; page[cd[SW-1:0]] <= cd[8 +: PAGE_W]; end
                end else if (ca == 12'hE01) begin
                    for (k = 0; k < NS; k = k + 1) need[k] <= cd[k*32 +: AW+1];
                    wait_mask <= cd[128]; need_set <= 1;
                end else fault <= 1;
            end
            if (dhit) begin
                if (run || hit) fault <= 1; else armed <= 1;
            end
            // ------------ launch: only an armed target participates
            if (lv && armed) begin
                armed <= 0;
                if (!(inst_ok && !fault && !run)) fault <= 1;
                else begin
                    start_v <= 1; run <= 1; cnt <= 0; rptr <= 0; tail <= TAIL[7:0];
                    wait_done <= wait_mask;
                end
            end
            // ------------ execution: fixed record calendar
            if (run) begin
                cnt <= cnt + 1'b1;
                if (tail != 0 && !start_v) tail <= tail - 1'b1;
                if (done_q) wait_done <= 0;
                if (!recs_done) begin
                    if (cur_off == cmp_cnt) begin
                        go <= r_go[rptr][NGO-1:0]; rec <= r_pay[rptr]; rptr <= rptr + 1'b1; tail <= TAIL[7:0];
                    end else if (cur_off < cnt) fault <= 1;
                end else if (!start_v && tail == 0 && !(|busy_q) && !wait_done && go == 0) run <= 0;
            end
            active <= run || (lv && armed);
            ready <= armed && inst_ok && !fault && !run && !hit;
        end
    end
endmodule
`default_nettype wire
