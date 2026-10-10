`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// redesign-qwen 2026-10-09: DISTRIBUTED successor of ot_qkvd_kv_wq (same ports, same KV layout, same credit / durable /
// fault contract; see ot_qkvd_kv_wq.sv for the layout and the flow).
//
// Why: qkd_kvwq_a-f7e45bead EARLY_FAIL_SETUP TT -639 (7,273 endpoints): the master is a 172.8 x 1,296 um strip, and ONE
// central head row (1,024 b + its decisions) fed the 8,192 w_data / 768 w_sec / 288 w_tag output flops of all 32 PCs
// spread over the 1,296-um right face (reg->out fault -608 ps with 258 ps of wire; head -> PC flops > one 504-um reach).
//
// Structure (TPU / Tensix style: replicate the head per quarter group, registered hops, local decisions):
//   central   pin capture, the QD-row queue, the head bookkeeping (hv / done / retire / credits / rw_v / faults).
//   feed F1   one registered copy per quarter group g of the head's sector swq^-1(g) (256 b), its sector address, the
//             one-hot PC lane t[2:0] and the tag {slot, q}: loaded from the queue on the head load (the queue read is
//             the base's own head-load mux).  Kept per group so placement puts it on the way to its group.
//   group G   per quarter group (8 PCs on one span of the right face): the sector, its lane, room of its own 8 PCs
//             (registered, as the base's room_q), the push into its PC's output flops, the write-done check of its 8 PCs
//             (tag = {slot, q}, done once, only after the push), and a registered done / bad report.
//   return R1 one registered stage per group back to the central bookkeeping.
// One row in flight, as the base: the next head loads only after all 4 sectors of the current one are durable.
// Cost: +3 core cycles a row from head load to first push / last done to retire (posted writes, not on the token path);
// area: +4 x (256 + 24 + 8 + TAGW) feed flops, the base's 1,024-b hrow is replaced by the 4 group sectors.
// MUT (bench mutants, must FAIL): 1 = sectors 1 and 2 swap PC groups; 2 = sector data from the wrong quarter (q ^ 1);
//   3 = quarter 0 never pushed (the row never becomes durable: the bench times out).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_wq_dist #(
    parameter integer HD   = 128,
    parameter integer NPC  = 32,
    parameter integer QD   = 4,
    parameter integer TAGW = 9,
    parameter integer MUT  = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  kvw_v,
    input  wire [1:0]            kvw_vg,
    input  wire [13:0]           kvw_t,
    input  wire [5:0]            kvw_layer,
    input  wire [HD*8-1:0]       kvw_d,
    output reg                   kvw_cr,
    output reg  [NPC-1:0]        w_v,
    output reg  [24*NPC-1:0]     w_sec,
    output reg  [256*NPC-1:0]    w_data,
    output reg  [TAGW*NPC-1:0]   w_tag,
    input  wire [NPC-1:0]        w_room,
    input  wire [NPC-1:0]        wd_v,
    input  wire [TAGW*NPC-1:0]   wd_tag,
    output reg                   rw_v,
    output reg  [21:0]           rw_id,
    output reg                   fault
);
    localparam integer QA = (QD > 1) ? $clog2(QD) : 1;
    localparam integer NG = 4;                 // quarter groups
    localparam integer GP = NPC / NG;          // PCs a group (8: lane t[2:0])
    // sector carried by quarter group g (swq is an involution: MUT 1 swaps groups 1 and 2)
    function automatic [1:0] swq(input [1:0] q);
        swq = (MUT == 1 && q == 2'd1) ? 2'd2 : (MUT == 1 && q == 2'd2) ? 2'd1 : q;
    endfunction
    function automatic [23:0] sec_of(input [5:0] layer, input [1:0] vg, input [13:0] t);
        sec_of = {7'd0, layer, vg[0], vg[1], t[13:9], t[6:3]};
    endfunction
    // ---- pin capture ----
    reg              iv;
    reg  [1:0]       ivg;
    reg  [13:0]      it;
    reg  [5:0]       il;
    reg  [HD*8-1:0]  id;
    reg  [NPC-1:0]   room_r, wdv_r;
    reg  [TAGW*NPC-1:0] wdt_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin iv <= 1'b0; room_r <= 0; wdv_r <= 0; end
        else begin iv <= kvw_v; room_r <= w_room; wdv_r <= wd_v; end
    always @(posedge clk) begin ivg <= kvw_vg; it <= kvw_t; il <= kvw_layer; id <= kvw_d; wdt_r <= wd_tag; end
    // ---- row queue ----
    reg  [HD*8-1:0]  qd  [0:QD-1];
    reg  [21:0]      qid [0:QD-1];
    reg  [QA:0]      qw, qr;
    wire             q_empty = (qw == qr);
    wire             q_full = (qw[QA-1:0] == qr[QA-1:0]) && (qw[QA] != qr[QA]);
    always @(posedge clk) if (iv) begin qd[qw[QA-1:0]] <= id; qid[qw[QA-1:0]] <= {il, ivg, it}; end
    // ---- central head bookkeeping ----
    reg              hv;
    reg  [21:0]      hid;
    reg  [3:0]       done;               // per sector q: durable (reported through the return stage)
    wire             retire = hv && (done == 4'hF);
    wire             hload = (!hv || retire) && !q_empty;
    wire [HD*8-1:0]  h_row = qd[qr[QA-1:0]];
    wire [21:0]      h_id  = qid[qr[QA-1:0]];
    wire [QA-1:0]    h_slot = qr[QA-1:0];
    // ---- per quarter group: feed (F1), group head (G), return (R1) ----
    reg  [NG-1:0]    r_v, r_bad;         // return stage (one per group)
    genvar g, i;
    generate for (g = 0; g < NG; g = g + 1) begin : g_grp
        localparam [1:0] SQ = swq(g);           // the sector this group carries
        localparam [1:0] DQ = (MUT == 2) ? (SQ ^ 2'd1) : SQ;   // the quarter of the row its bytes come from
        // F1: feed copy
        (* keep *) reg            f_v;
        (* keep *) reg [255:0]    f_d;
        (* keep *) reg [23:0]     f_sec;
        (* keep *) reg [GP-1:0]   f_lane;
        (* keep *) reg [TAGW-1:0] f_tag;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) f_v <= 1'b0;
            else f_v <= hload;
        always @(posedge clk) if (hload) begin
            f_d <= h_row[256*DQ +: 256];
            f_sec <= sec_of(h_id[21:16], h_id[15:14], h_id[13:0]);
            f_lane <= {{(GP-1){1'b0}}, 1'b1} << h_id[2:0];
            f_tag <= TAGW'({h_slot, SQ});
        end
        // G: group head
        reg            gv, gsent, gdone, rq;
        reg [255:0]    gd;
        reg [23:0]     gsec;
        reg [GP-1:0]   glane;
        reg [TAGW-1:0] gtag;
        wire           gpush = gv && !gsent && rq && !(MUT == 3 && SQ == 2'd0);
        // write-done of this group's PCs: any report, and its check against the head sector
        reg            wd_any, wd_bad;
        integer k;
        always @* begin
            wd_any = 1'b0; wd_bad = 1'b0;
            for (k = 0; k < GP; k = k + 1)
                if (wdv_r[GP*g + k]) begin
                    wd_any = 1'b1;
                    if (wdt_r[TAGW*(GP*g + k) +: TAGW] != gtag || !gsent || gdone || !gv) wd_bad = 1'b1;
                end
        end
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin gv <= 1'b0; gsent <= 1'b0; gdone <= 1'b0; rq <= 1'b0; r_v[g] <= 1'b0; r_bad[g] <= 1'b0; end
            else begin
                r_v[g] <= wd_any && !wd_bad;
                r_bad[g] <= wd_bad;
                if (f_v) begin gv <= 1'b1; gsent <= 1'b0; gdone <= 1'b0; rq <= 1'b0; end
                else begin
                    gsent <= gsent | gpush;
                    gdone <= gdone | wd_any;
                    rq <= (|(room_r[GP*g +: GP] & glane)) && !gpush;
                    if (gdone && retire) gv <= 1'b0;
                end
            end
        end
        always @(posedge clk) if (f_v) begin gd <= f_d; gsec <= f_sec; glane <= f_lane; gtag <= f_tag; end
        // the PC output flops of this group
        for (i = 0; i < GP; i = i + 1) begin : g_pc
            always @(posedge clk or negedge rst_n)
                if (!rst_n) w_v[GP*g + i] <= 1'b0;
                else w_v[GP*g + i] <= gpush && glane[i];
            always @(posedge clk) if (gpush && glane[i]) begin
                w_data[256*(GP*g + i) +: 256] <= gd;
                w_sec[24*(GP*g + i) +: 24] <= gsec;
                w_tag[TAGW*(GP*g + i) +: TAGW] <= gtag;
            end
        end
    end endgenerate
    // the return report of group g marks sector swq(g)
    wire [3:0] r_q;
    generate for (g = 0; g < NG; g = g + 1) begin : g_rq
        assign r_q[swq(g)] = r_v[g];
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qw <= 0; qr <= 0; kvw_cr <= 1'b0; rw_v <= 1'b0; fault <= 1'b0; hv <= 1'b0; done <= 4'd0;
        end else begin
            kvw_cr <= 1'b0; rw_v <= 1'b0;
            if (iv) begin
                if (q_full) fault <= 1'b1;
                qw <= qw + 1'b1;
            end
            if (|r_bad) fault <= 1'b1;
            if (|(r_q & done)) fault <= 1'b1;            // a sector reported durable twice
            done <= done | r_q;
            if (retire) begin
                hv <= 1'b0; kvw_cr <= 1'b1; rw_v <= 1'b1; rw_id <= hid;
            end
            if (hload) begin
                hv <= 1'b1; qr <= qr + 1'b1; done <= 4'd0; hid <= h_id;
            end
        end
    end
endmodule
