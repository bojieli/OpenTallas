`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_capl (claude S81 VM owner r9, 2026-10-14): ONE STATIC capture lane of the S81 layer-die VM (serial
// 0.9 GHz).  Successor of the dynamic dsfd_vm_cl (associative row entries, LRU eviction, partial-row timeout: VOID
// under the owner rule 2026-10-14T18:59).  A lane = 8 field roots (8G .. 8G+7) = 16 element inputs a cycle from the
// capture slab (dsfd_sp_capture t_vm: per root {row1 {data32, addr19}, v1, row0 {data32, addr19}, v0}).
// ALIGNMENT CONTRACT (compiler, unchanged from the legacy lane): element k of the lane (root i = 8G + k/2) carries
// addr[7:1] == i, so every element of lane G lands in VM row R = addr[17:4] with R[3:0] = G, word addr[3:0]; the row
// KEY is addr[17:8].  addr[18] set (>= 2^18 words) or a wrong addr[7:1] is a fault (element dropped, fail closed).
// STATIC ASSEMBLY: E direct-mapped row entries, entry = key mod E (no tags searched, no allocation, no victim).
//   * an element merges into entry key mod E (entry empty: it takes the key);
//   * the cycle an entry's 16 words are present it is written (one masked VM row write {row, mask ffff, data}) and
//     cleared: the write cycle is a fixed function of the producers' compiled timeline (the last element's arrival);
//   * PHASE FLUSH: at the capture's phase-drained event (status st[2] rising after st[0], the capture slab's own
//     quota completion) every entry e with a partial row is written at drained + 1 + e (fixed slot, partial mask);
//     the field's last rows of a phase that does not fill a row are the only partial rows.
// FAULTS (sticky, never a delay): [0] range, [1] alignment, [2] alias (an element whose entry holds another key:
//   two live rows of one lane E keys apart = root skew beyond the compiled bound), [3] duplicate word, [4] two rows due
//   on one cycle (full rows of two entries, or a full row inside the flush window).
// Pipeline: S1 (this module's input register = the parent's pin register output) decode + merge into the entry state
// (registered); a completed row leaves from flops one cycle later (o_v / o_row / o_m / o_d).  Latency: element at the
// lane input edge P (its row's last) -> o_* registered at P + 2.
// Mutant OT_VM_CAPL_MUT_WORD: element row1 of every root writes the row0 word slot (words 2j+1 lost): must FAIL.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_static_capl #(parameter integer E = 8) (
    input  wire          ck, rn,              // serial clock, synchronised lane reset (control state only)
    input  wire [3:0]    gid,                 // lane index G (static strap)
    input  wire [831:0]  f_c,                 // 8 roots x {row1 {data32, addr19}, v1, row0 {data32, addr19}, v0} (registered)
    input  wire          flush,               // phase-drained event (one cycle)
    output reg           o_v,
    output reg  [13:0]   o_row,
    output reg  [15:0]   o_m,
    output reg  [511:0]  o_d,
    output reg  [4:0]    flt
);
    localparam integer EB = $clog2(E);
    // ------------------------------------------------------------------ decode
    reg [15:0] ev, eok; reg [9:0] ek [0:15]; reg [3:0] ew [0:15]; reg [31:0] ed [0:15];
    reg f_rng, f_al;
    always @* begin : p_dec integer k; reg [50:0] el; reg v;
        f_rng = 1'b0; f_al = 1'b0;
        for (k = 0; k < 16; k = k + 1) begin
            // root j = k/2: [104 j +: 104] = {row1 51, v1, row0 51, v0}; element k even = row0, odd = row1
            v  = (k % 2 == 0) ? f_c[104*(k/2)] : f_c[104*(k/2) + 52];
            el = (k % 2 == 0) ? f_c[104*(k/2) + 1 +: 51] : f_c[104*(k/2) + 53 +: 51];
            ev[k] = v;
            ek[k] = el[17:8]; ed[k] = el[50:19];
`ifdef OT_VM_CAPL_MUT_WORD
            ew[k] = {el[3:1], 1'b0};
`else
            ew[k] = el[3:0];
`endif
            eok[k] = 1'b0;
            if (v) begin
                if (el[18]) f_rng = 1'b1;
                else if (el[7:1] != {gid, 3'(k / 2)}) f_al = 1'b1;
                else eok[k] = 1'b1;
            end
        end
    end
    // ------------------------------------------------------------------ entry state
    reg [E-1:0] V; reg [9:0] KEY [0:E-1]; reg [15:0] MSK [0:E-1]; reg [511:0] DAT [0:E-1];
    reg [EB:0] fl_c; reg fl_on;              // flush slot counter (entry fl_c - 1 is written this cycle)
    // next-state (combinational) per entry
    reg [E-1:0] nV, full; reg [9:0] nK [0:E-1]; reg [15:0] nM [0:E-1]; reg [511:0] nD [0:E-1];
    reg f_alias, f_dup;
    // Alignment proves ew[k][3:1] == k/2 for every eok[k]. A word
    // therefore has exactly two possible producers, the two inputs of its root.
    // Select the entry key once, then use two fixed data candidates per word.
    // This avoids a blocking 16-input merge chain on every 512-bit entry.
    always @* begin : p_merge
        integer e, k, w;
        reg hit, a, b;
        reg [9:0] kk;
        reg [15:0] targeted, first, accepted;
        f_alias = 1'b0; f_dup = 1'b0;
        for (e = 0; e < E; e = e + 1) begin
            for (k = 0; k < 16; k = k + 1)
                targeted[k] = eok[k] && ek[k][EB-1:0] == e[EB-1:0];
            // Parallel prefix priority: each candidate tests a CONSTANT prefix
            // mask. The key is an OR reduction of one-hot candidates, avoiding
            // sixteen cascaded 10-bit priority muxes on the data path.
            for (k = 0; k < 16; k = k + 1)
                first[k] = targeted[k] && !(|(targeted & ((16'h1 << k) - 16'd1)));
            kk = 10'd0;
            for (k = 0; k < 16; k = k + 1)
                kk = kk | (ek[k] & {10{first[k]}});
            if (V[e]) kk = KEY[e];
            accepted = 16'd0;
            for (k = 0; k < 16; k = k + 1) begin
                if (eok[k] && ek[k][EB-1:0] == e[EB-1:0]) begin
                    if (ek[k] != kk) f_alias = 1'b1;
                    else accepted[k] = rn;
                end
            end
            hit = |accepted;
            nV[e] = V[e] || hit;
            nK[e] = hit ? kk : KEY[e];
            for (w = 0; w < 16; w = w + 1) begin
                a = accepted[2*(w/2)] && ew[2*(w/2)] == w[3:0];
                b = accepted[2*(w/2)+1] && ew[2*(w/2)+1] == w[3:0];
                if ((MSK[e][w] && (a || b)) || (a && b)) f_dup = 1'b1;
                nM[e][w] = MSK[e][w] || a || b;
                // Match the original ascending-k blocking merge: last wins.
                nD[e][32*w +: 32] = b ? ed[2*(w/2)+1] :
                                      a ? ed[2*(w/2)] : DAT[e][32*w +: 32];
            end
            full[e] = nV[e] && nM[e] == 16'hffff;
        end
    end
    // ------------------------------------------------------------------ write selection (registered output)
    always @(posedge ck) begin : p_out integer e; reg [EB:0] nf; reg sel; reg two; integer fe;
        // DAT/KEY are control-valid state: rn must gate the small per-word
        // acceptance signals, not become a separate enable on all 4176 bits.
        // accepted==0 while reset holds makes nD/nK equal their old values, so
        // even the otherwise invalid data bits retain the historical behavior.
        for (e = 0; e < E; e = e + 1) begin
            DAT[e] <= nD[e]; KEY[e] <= nK[e];
        end
        if (!rn) begin
            V <= {E{1'b0}}; o_v <= 1'b0; flt <= 5'd0; fl_on <= 1'b0; fl_c <= '0;
            for (e = 0; e < E; e = e + 1) MSK[e] <= 16'd0;
        end else begin
            sel = 1'b0; two = 1'b0; fe = -1;
            for (e = 0; e < E; e = e + 1) if (full[e]) begin if (sel) two = 1'b1; else begin sel = 1'b1; fe = e; end end
            // flush slot: entry fl_c - 1 at drained + fl_c
            if (fl_on && !sel && nV[fl_c - 1] && nM[fl_c - 1] != 16'd0) begin sel = 1'b1; fe = fl_c - 1; end
            else if (fl_on && sel && nV[fl_c - 1] && nM[fl_c - 1] != 16'd0 && fe != fl_c - 1) two = 1'b1;
            for (e = 0; e < E; e = e + 1) begin
                V[e] <= nV[e] && !(sel && fe == e);
                MSK[e] <= (sel && fe == e) ? 16'd0 : nM[e];
            end
            o_v <= sel;
            if (sel) begin o_row <= {nK[fe], gid}; o_m <= nM[fe]; o_d <= nD[fe]; end
            if (flush) begin fl_on <= 1'b1; fl_c <= 1; end
            else if (fl_on) begin if (fl_c == E) fl_on <= 1'b0; else fl_c <= fl_c + 1'b1; end
            flt <= flt | {two, f_dup, f_alias, f_al, f_rng};
        end
    end
endmodule
`default_nettype wire
