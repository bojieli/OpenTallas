`timescale 1ns/1ps
`default_nettype none
// HGI-1 IDX.MERGE (proposed G20, hgi-takeover 2026-10-09; review_queue/hgi-die-gaps.md round 5 T1): the exact k-way
// merge behind COLL.TOPK_MERGE.  The program gathers every rank's local selection into VM (two exact COLL.ALL_GATHERs:
// values, ids; G runs of n), each run already sorted by the merge key (a local IDX.TOPK does that), and this engine emits
// the first k elements of the merged order -- exactly the golden lexsort (hgi_sim ds_native.topk_merge).
//
//   A  VM FP32  G rows of n values (row stride A.stride)        key 0 (param[12] = 0): larger value first, -0 = +0,
//   B  VM U32   G rows of n ids    (row stride B.stride)          NaN after every number, equal values -> lower id
//   O  VM U32   k merged ids                                    key 1 (param[12] = 1): lower id first (values ride along)
//   R  VM FP32  k merged values (optional)
//   param [11:0] k (1 .. 2,048), [12] key; G = A.m (1 .. 128).
// A run whose next element is better than the one it just gave is unsorted input: fault (fail-closed, never a silent
// wrong order).  Fewer than k elements in all runs: O / R hold all of them.
// Microarchitecture: one head {value, id} per run; a registered tournament tree (7 levels) whose path is re-evaluated
// level by level after a head changes; one VM request outstanding (head refills: one value read + one id read through a
// one-sector cache each; results through two sector packers, masked 8-word writes).
module ot_hgi_idx_merge #(
    parameter integer GMAX = 128,
    parameter integer MUT = 0          // bench mutant: 1 ties resolve to the HIGHER id
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [11:0]   k,
    input  wire          key_id,
    input  wire [7:0]    g,            // runs
    input  wire [19:0]   n,            // run length
    input  wire [17:0]   a_base, b_base, o_base, r_base,
    input  wire [17:0]   a_str, b_str,
    input  wire          has_r,
    output reg           done,
    output reg           fault,
    output reg  [337:0]  vmq,
    input  wire [273:0]  vmr
);
    localparam integer LG = $clog2(GMAX);
    // ---------------------------------------------------------------- key order
    function automatic [31:0] okey(input [31:0] v);
        okey = (v[30:0] == 31'd0) ? 32'h8000_0000 : (v[31] ? ~v : (v | 32'h8000_0000));
    endfunction
    function automatic is_nan(input [31:0] v); is_nan = (v[30:23] == 8'hFF) && (v[22:0] != 23'd0); endfunction
    function automatic better(input av, input [31:0] a, input [31:0] ai, input bv, input [31:0] b, input [31:0] bi, input kid);
        reg lo;
        begin
            lo = (MUT == 1) ? (ai > bi) : (ai < bi);
            if (!bv) better = av;
            else if (!av) better = 1'b0;
            else if (kid) better = lo;
            else if (is_nan(a) != is_nan(b)) better = is_nan(b);
            else if (is_nan(a)) better = lo;
            else if (okey(a) != okey(b)) better = okey(a) > okey(b);
            else better = lo;
        end
    endfunction
    // ---------------------------------------------------------------- heads and tree
    reg [31:0] hv [0:GMAX-1]; reg [31:0] hi [0:GMAX-1]; reg [GMAX-1:0] hok; reg [19:0] hpos [0:GMAX-1];
    reg [LG-1:0] node [1:GMAX-1];            // node j winner (leaf index); children 2j, 2j+1; leaves GMAX .. 2 GMAX - 1
    function automatic [LG-1:0] child_win(input integer c);   // winner of child c (node or leaf)
        child_win = (c >= GMAX) ? LG'(c - GMAX) : node[c];
    endfunction
    // ---------------------------------------------------------------- VM cache, packers
    reg vm_pend, vm_rd; reg [14:0] c_sec, rd_sec; reg c_ok; reg [255:0] c_dat;
    reg [17:0] pk_a [0:1]; reg [255:0] pk_d [0:1]; reg [7:0] pk_m [0:1]; reg [14:0] pk_s [0:1]; reg [1:0] pk_full;
    // ---------------------------------------------------------------- control
    localparam S_IDLE = 4'd0, S_LOADV = 4'd1, S_LOADI = 4'd2, S_BUILD = 4'd3, S_POP = 4'd4, S_REFV = 4'd5, S_REFI = 4'd6,
               S_PATH = 4'd7, S_FLUSH = 4'd8;
    reg [3:0] st;
    reg [7:0] r;                             // run being loaded / refilled
    reg [LG:0] bj;                           // build: node index (descending)
    reg [LG-1:0] lj;                         // path: current node
    reg [11:0] nout;
    reg [31:0] pv, pi; reg [31:0] nv;        // popped element; the refilled value
    wire [17:0] wa_v = a_base + r * a_str + hpos[r];
    wire [17:0] wa_i = b_base + r * b_str + hpos[r];
    wire [LG-1:0] top = node[1];
    reg [LG-1:0] wl, wr; integer i;
    wire pk_ok = !pk_full[0] && !(has_r && pk_full[1]);
    reg wp_v; reg wp;
    always @* begin wp_v = |pk_full; wp = pk_full[0] ? 1'b0 : 1'b1; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; vmq <= 338'd0; vm_pend <= 1'b0; c_ok <= 1'b0; pk_full <= 2'd0;
            hok <= '0; pk_m[0] <= 8'd0; pk_m[1] <= 8'd0;
        end else begin
            done <= 1'b0; fault <= 1'b0; vmq[337] <= 1'b0;
            if (vmr[273]) begin
                vm_pend <= 1'b0;
                if (vm_rd) begin c_ok <= 1'b1; c_sec <= rd_sec; c_dat <= vmr[255:0]; end
            end
            case (st)
                S_IDLE: if (go) begin
                    if (k == 12'd0 || k > 12'd2048 || g == 8'd0 || g > GMAX || n == 20'd0) fault <= 1'b1;
                    else begin
                        st <= S_LOADV; r <= 8'd0; hok <= '0; nout <= 12'd0; c_ok <= 1'b0;
                        for (i = 0; i < GMAX; i = i + 1) hpos[i] <= 20'd0;
                        pk_a[0] <= o_base; pk_a[1] <= r_base; pk_m[0] <= 8'd0; pk_m[1] <= 8'd0;
                    end
                end
                // ---- initial heads: value then id of run r
                S_LOADV, S_REFV: if (!vm_pend && !wp_v) begin
                    if (c_ok && c_sec == wa_v[17:3]) begin
                        nv <= c_dat[wa_v[2:0] * 32 +: 32]; st <= (st == S_LOADV) ? S_LOADI : S_REFI;
                    end else begin
                        vm_pend <= 1'b1; vm_rd <= 1'b1; rd_sec <= wa_v[17:3];
                        vmq <= {1'b1, 1'b0, {12'd0, wa_v[17:3], 5'd0}, 256'd0, 32'd0, 16'h0920};
                    end
                end
                S_LOADI, S_REFI: if (!vm_pend && !wp_v) begin
                    if (c_ok && c_sec == wa_i[17:3]) begin
                        hv[r] <= nv; hi[r] <= c_dat[wa_i[2:0] * 32 +: 32]; hok[r] <= 1'b1;
                        hpos[r] <= hpos[r] + 20'd1;
                        // sortedness: the refilled head may not be better than the element this run just gave
                        if (st == S_REFI && better(1'b1, nv, c_dat[wa_i[2:0] * 32 +: 32], 1'b1, pv, pi, key_id)) begin
                            st <= S_IDLE; fault <= 1'b1;
                        end else if (st == S_LOADI) begin
                            if (r + 8'd1 == g) begin st <= S_BUILD; bj <= (LG+1)'(GMAX - 1); end
                            else begin r <= r + 8'd1; st <= S_LOADV; end
                        end else begin st <= S_PATH; lj <= LG'((GMAX + r) >> 1); end
                    end else begin
                        vm_pend <= 1'b1; vm_rd <= 1'b1; rd_sec <= wa_i[17:3];
                        vmq <= {1'b1, 1'b0, {12'd0, wa_i[17:3], 5'd0}, 256'd0, 32'd0, 16'h0921};
                    end
                end
                // ---- build the tree bottom-up, one node a cycle
                S_BUILD: begin
                    wl = child_win(2 * bj); wr = child_win(2 * bj + 1);
                    node[bj] <= better(hok[wr], hv[wr], hi[wr], hok[wl], hv[wl], hi[wl], key_id) ? wr : wl;
                    if (bj == 1) st <= S_POP; else bj <= bj - 1;
                end
                // ---- re-evaluate the changed leaf's path, one level a cycle
                S_PATH: begin
                    wl = child_win(2 * lj); wr = child_win(2 * lj + 1);
                    node[lj] <= better(hok[wr], hv[wr], hi[wr], hok[wl], hv[wl], hi[wl], key_id) ? wr : wl;
                    if (lj == 1) st <= S_POP; else lj <= lj >> 1;
                end
                // ---- emit the winner, refill its run
                S_POP: if (pk_ok) begin
                    if (!hok[top] || nout == k) st <= S_FLUSH;
                    else begin
                        pk_d[0][pk_a[0][2:0] * 32 +: 32] <= hi[top]; pk_m[0][pk_a[0][2:0]] <= 1'b1; pk_s[0] <= pk_a[0][17:3];
                        pk_a[0] <= pk_a[0] + 18'd1; if (pk_a[0][2:0] == 3'd7) pk_full[0] <= 1'b1;
                        if (has_r) begin
                            pk_d[1][pk_a[1][2:0] * 32 +: 32] <= hv[top]; pk_m[1][pk_a[1][2:0]] <= 1'b1; pk_s[1] <= pk_a[1][17:3];
                            pk_a[1] <= pk_a[1] + 18'd1; if (pk_a[1][2:0] == 3'd7) pk_full[1] <= 1'b1;
                        end
                        nout <= nout + 12'd1; pv <= hv[top]; pi <= hi[top]; r <= {{(8-LG){1'b0}}, top};
                        if (hpos[top] == n) begin hok[top] <= 1'b0; st <= S_PATH; lj <= LG'((GMAX + top) >> 1); end
                        else st <= S_REFV;
                    end
                end
                S_FLUSH: begin
                    if (pk_m[0] != 8'd0) pk_full[0] <= 1'b1;
                    if (has_r && pk_m[1] != 8'd0) pk_full[1] <= 1'b1;
                    if (!wp_v && !vm_pend && pk_m[0] == 8'd0 && (!has_r || pk_m[1] == 8'd0)) begin st <= S_IDLE; done <= 1'b1; end
                end
                default: st <= S_IDLE;
            endcase
            // ---- packer writes (one outstanding; reads wait while a packer is full)
            if (wp_v && !vm_pend && !vmq[337]) begin
                vm_pend <= 1'b1; vm_rd <= 1'b0;
                vmq <= {1'b1, 1'b1, {12'd0, pk_s[wp], 5'd0}, pk_d[wp],
                        {{4{pk_m[wp][7]}}, {4{pk_m[wp][6]}}, {4{pk_m[wp][5]}}, {4{pk_m[wp][4]}},
                         {4{pk_m[wp][3]}}, {4{pk_m[wp][2]}}, {4{pk_m[wp][1]}}, {4{pk_m[wp][0]}}}, 16'h0922};
                pk_full[wp] <= 1'b0; pk_m[wp] <= 8'd0;
            end
        end
    end
endmodule
`default_nettype wire
