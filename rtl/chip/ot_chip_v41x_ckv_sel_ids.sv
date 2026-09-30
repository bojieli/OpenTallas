`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Selected-ID stream of an indexed DeepSeek-V4.1 attention layer: the final
// (cross-die merged) index top-K, in the golden's order, with the owner of
// every selected compressed-KV row.
//
// Golden: tools/hdc_golden_v41.py Model.indexer returns
//   sel = sorted(topk_lowest_index(s, min(index_topk, n)))
// and Model.attention appends state["ckv"][src][i] for i in sel after the
// window rows, so selection RANK k (0-based, ascending position) becomes
// attention row window_count + k.
//
// INPUT: the output side of ot_hdc_v41x_sel (the final select over the four
// dies' local selections; every die runs it on the same all-gathered
// candidates, so every die holds the same list).  Port q carries the selected
// positions of quarter q in ascending order, W lanes per beat, every beat full
// except the last (lane mask a prefix), closed by out_last (an empty quarter
// sends one beat with lv = 0 and last).  The concatenation of the ports in
// quarter order is the ascending selection; this module takes the ports in
// that order and REJECTS (fault) a non-prefix mask, a position that is not
// strictly above its predecessor, more than K entries, or a final count
// different from the expected one.  The expected count is known before the
// select runs: n_sel = min(K, published compressed rows) (topk_lowest_index
// always returns exactly min(k, n) positions).
//
// OWNERSHIP (docs/V41X_SELECTED_CKV_DMA.md, ot_chip_v41x_ckv_selected_dma):
// compressed row id g lives in 16-row group g / 16 on
//   die   = (g / 16) % 4          = g[5:4]
//   stack = (g / 64) % 4          = g[7:6]
//   local = (g / 256) * 16 + g%16 (row index in that die/stack's region)
// sector address = region_base_sector[stack] + 9 * local + sector.
// A die fetches only the rows it owns and all-gathers them (tensor group 4:
// every die needs all selected rows, the MQA row is shared by its heads).
//
// OUTPUT: a table of the selection, written in rank order as it streams in
// (entries 0 .. count-1 are final once written), with NRD combinational read
// ports: rd_rank -> {gid, owner die, owner stack, local row}.  Consumers (the
// owned-row fetch and the in-order collector) follow `count` and `done`, so
// fetch starts on the first selected ID, not after the whole list.
//
// OWNED LISTS (OWN mask bit d set): the ranks owned by die d, in rank order,
// compacted as the beats arrive (up to W per cycle), so die d's fetch walks
// only its own rows (one dispatch per cycle) instead of scanning all n_sel
// ranks.  A die instantiates its own table with OWN = 1 << DIE_ID; a bench
// modelling four dies may share one table with OWN = 4'b1111.
//   own_count[d]  ranks listed so far (final when done)
//   own_idx[d] -> own_rank[d] (the rank), own_gid[d] (its id)
//
// Throughput: one sel beat (W entries) per cycle; s_ready is held high on
// the open port.  Latency: an entry is readable two cycles after its beat is
// accepted (input register, then the bank write).
// ---------------------------------------------------------------------------
module ot_chip_v41x_ckv_sel_ids #(
    parameter integer Q = 4,
    parameter integer W = 16,
    parameter integer IW = 20,          // sel index width
    parameter integer POS_W = 21,       // global compressed-row id width (DMA)
    parameter integer K = 512,
    parameter integer NRD = 2,
    parameter [3:0] OWN = 4'b0000,     // dies whose owned-rank lists are kept
    parameter integer KW = $clog2(K + 1)
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // job: clears the table; exp_n = min(K, published rows)
    input  wire                 clr,
    input  wire [KW-1:0]        exp_n,
    // ot_hdc_v41x_sel output side
    input  wire [Q-1:0]         s_valid,
    output wire [Q-1:0]         s_ready,
    input  wire [Q-1:0]         s_last,
    input  wire [Q*W-1:0]       s_lv,
    input  wire [Q*W*IW-1:0]    s_idx,
    // table
    output reg  [KW-1:0]        count,      // entries written (ranks 0 .. count-1 valid)
    output reg                  done,       // every quarter closed and count == exp_n
    output reg  [31:0]          done_cycle_count, // cycles from clr to done (stat)
    input  wire [NRD*KW-1:0]    rd_rank,
    output wire [NRD*POS_W-1:0] rd_gid,
    output wire [NRD*2-1:0]     rd_die,
    output wire [NRD*2-1:0]     rd_stack,
    output wire [NRD*POS_W-1:0] rd_local,
    output wire [4*KW-1:0]      own_count,
    input  wire [4*KW-1:0]      own_idx,
    output wire [4*KW-1:0]      own_rank,
    output wire [4*POS_W-1:0]   own_gid,
    output reg                  fault,
    output reg  [3:0]           fault_code  // {count, order, overflow, mask}
);
    // Storage: W banks (rank mod W) of K/W rows, one write port each: a beat's
    // lanes are rotated onto the banks, so no bank sees more than one write per
    // cycle (SRAM-mappable).  The beat is registered before it is checked and
    // written (acceptance pointer aport runs one beat ahead of r_port).
    localparam integer BD = K / W;
    localparam integer LW = $clog2(W);
    reg [POS_W-1:0] tb [0:W-1][0:BD-1];
    reg [$clog2(Q+1)-1:0] aport, r_port;
    reg [POS_W-1:0] prev;
    reg have_prev;
    reg run;
    reg r_v, r_last;
    reg [W-1:0] r_lv;
    reg [W*IW-1:0] r_idx;
    assign s_ready = run ? (Q'(1) << aport) : '0;
    wire acc = run && aport < Q && s_valid[aport];

    function automatic [POS_W-1:0] tab_rd(input [KW-1:0] rk);
        tab_rd = tb[rk[LW-1:0]][rk >> LW];
    endfunction

    // lane mask must be a prefix; n = its population; ascending, strictly
    integer i;
    reg [$clog2(W+1)-1:0] n;
    reg prefix_ok, order_ok;
    reg [POS_W-1:0] last_id;
    always @(*) begin
        n = 0; prefix_ok = 1'b1; order_ok = 1'b1; last_id = prev;
        for (i = 0; i < W; i = i + 1) begin
            if (r_lv[i]) begin
                if (n != i[$clog2(W+1)-1:0]) prefix_ok = 1'b0;
                n = n + 1'b1;
                if ((have_prev || i != 0) && POS_W'(r_idx[i*IW +: IW]) <= last_id) order_ok = 1'b0;
                last_id = POS_W'(r_idx[i*IW +: IW]);
            end
        end
    end
    wire wr_ok = r_v && prefix_ok && 32'(count) + 32'(n) <= K;
    wire [LW-1:0] c0 = count[LW-1:0];
    wire [KW-1:0] r0 = count >> LW;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 0; done <= 0; fault <= 0; fault_code <= 0; aport <= 0; r_port <= 0;
            prev <= 0; have_prev <= 0; run <= 0; done_cycle_count <= 0; r_v <= 0; r_last <= 0;
        end else if (clr) begin
            count <= 0; done <= 0; aport <= 0; r_port <= 0; prev <= 0; have_prev <= 0; run <= 1;
            done_cycle_count <= 0; r_v <= 0;
        end else begin
            if (run && !done) done_cycle_count <= done_cycle_count + 1;
            r_v <= acc;
            if (acc) begin
                r_lv <= s_lv[aport*W +: W]; r_idx <= s_idx[aport*W*IW +: W*IW]; r_last <= s_last[aport];
                if (s_last[aport]) begin
                    aport <= aport + 1'b1;
                    if (aport == Q - 1) run <= 0;
                end
            end
            if (r_v) begin
                if (!prefix_ok) begin fault <= 1; fault_code[0] <= 1; end
                if (!order_ok) begin fault <= 1; fault_code[2] <= 1; end
                if (32'(count) + 32'(n) > K) begin fault <= 1; fault_code[1] <= 1; end
                else count <= count + KW'(n);
                if (n != 0) begin prev <= last_id; have_prev <= 1; end
                if (r_last) begin
                    r_port <= r_port + 1'b1;
                    if (r_port == Q - 1) begin
                        if (count + KW'(n) != exp_n) begin fault <= 1; fault_code[3] <= 1; end
                        else done <= 1;
                    end
                end
            end
        end
    end
    genvar bk;
    generate for (bk = 0; bk < W; bk = bk + 1) begin : g_bank
        wire [LW-1:0] j = LW'(bk) - c0;                 // lane landing on this bank
        wire [KW-1:0] row = r0 + KW'({1'b0, c0} + {1'b0, j} >= (LW+1)'(W));
        always @(posedge clk)
            if (wr_ok && 32'(j) < 32'(n)) tb[bk][row] <= POS_W'(r_idx[j*IW +: IW]);
    end endgenerate

    // ---- owned-rank lists ----
    genvar od;
    generate for (od = 0; od < 4; od = od + 1) begin : g_own
        if (OWN[od]) begin : g_on
            reg [KW-1:0] lb [0:W-1][0:BD-1];
            reg [KW-1:0] comp [0:W-1];                  // compacted owned ranks of this beat
            reg [$clog2(W+1)-1:0] nown;
            reg [KW-1:0] oc;
            integer a;
            assign own_count[od*KW +: KW] = oc;
            always @(*) begin
                nown = 0;
                for (a = 0; a < W; a = a + 1) comp[a] = 0;
                for (a = 0; a < W; a = a + 1)
                    if (a < n && r_idx[a*IW + 4 +: 2] == 2'(od)) begin
                        comp[nown[LW-1:0]] = count + KW'(a);
                        nown = nown + 1'b1;
                    end
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) oc <= 0;
                else if (clr) oc <= 0;
                else if (wr_ok) oc <= oc + KW'(nown);
            end
            wire [LW-1:0] o0 = oc[LW-1:0];
            wire [KW-1:0] q0 = oc >> LW;
            genvar ob;
            for (ob = 0; ob < W; ob = ob + 1) begin : g_ob
                wire [LW-1:0] j = LW'(ob) - o0;
                wire [KW-1:0] row = q0 + KW'({1'b0, o0} + {1'b0, j} >= (LW+1)'(W));
                always @(posedge clk)
                    if (wr_ok && 32'(j) < 32'(nown)) lb[ob][row] <= comp[j];
            end
            wire [KW-1:0] oi = own_idx[od*KW +: KW];
            wire [KW-1:0] rk = lb[oi[LW-1:0]][oi >> LW];
            assign own_rank[od*KW +: KW] = rk;
            assign own_gid[od*POS_W +: POS_W] = tab_rd(rk);
        end else begin : g_off
            assign own_count[od*KW +: KW] = 0;
            assign own_rank[od*KW +: KW] = 0;
            assign own_gid[od*POS_W +: POS_W] = 0;
        end
    end endgenerate

    genvar r;
    generate for (r = 0; r < NRD; r = r + 1) begin : g_rd
        wire [POS_W-1:0] g = tab_rd(rd_rank[r*KW +: KW]);
        assign rd_gid[r*POS_W +: POS_W] = g;
        assign rd_die[r*2 +: 2] = g[5:4];
        assign rd_stack[r*2 +: 2] = g[7:6];
        assign rd_local[r*POS_W +: POS_W] = ((g >> 8) << 4) | POS_W'(g[3:0]);
    end endgenerate
endmodule
