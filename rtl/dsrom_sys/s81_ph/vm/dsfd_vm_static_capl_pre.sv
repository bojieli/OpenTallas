`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------
// dsfd_vm_static_capl_pre (claude S81 VM F2, 2026-10-15, leaf PIPE=2): dsfd_vm_static_capl_pipe with the element
// VALIDATION and ENTRY TARGET decode moved into the leaf's existing pin-register stage (dsfd_vm_static_cap_leaf PIPE=2).
// MEASURED CAUSE (native5 CTS, 14514126e): worst TT reg->reg -127.8 ps runs pin_gid -> 2 fanout buffers -> XNOR
// alignment compare -> AND5 eok -> targeted/first/accepted -> DAT next-state (13 levels, gid->eok alone ~300 ps).
// STRUCTURE: the pin stage registers per element ok (v & !addr18 & addr[7:1] == {gid, k/2}), the one-hot entry target
// (addr[8+EB-1:8]) and the range / alignment fault terms; this module consumes them registered.  Same edges, same
// age as PIPE=1 (+1 serial vs legacy), II1; data pins are no longer reset-gated (only the 16+16E+2 decoded control
// bits are), every data use is gated by a registered ok/target bit.  Cycle-exact to PIPE=1 on every valid word,
// header and sticky fault (tb_dsfd_vm_static_cap_leaf_pre_equiv).
// Mutant OT_VM_CAPL_MUT_WORD: element row1 of every root writes the row0 word slot (words 2j+1 lost): must FAIL.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_vm_static_capl_pre #(parameter integer E = 8) (
    input  wire          ck, rn,              // serial clock, synchronised lane reset (control state only)
    input  wire [3:0]    gid,                 // lane index G (static strap)
    input  wire [831:0]  f_c,                 // 8 roots x {row1 {data32, addr19}, v1, row0 {data32, addr19}, v0} (registered, data use only)
    input  wire [15:0]   p_ok,                // registered per element: valid, in range, aligned
    input  wire [16*E-1:0] p_tgt,             // registered per element one-hot entry target (zero unless p_ok)
    input  wire          p_rng, p_al,         // registered range / alignment fault terms of the same elements
    input  wire          flush,               // phase-drained event (one cycle)
    output reg           o_v,
    output reg  [13:0]   o_row,
    output reg  [15:0]   o_m,
    output reg  [511:0]  o_d,
    output reg  [4:0]    flt
);
    localparam integer EB = $clog2(E);
    // ------------------------------------------------------------------ decode (data fields only; control registered)
    reg [15:0] eok; reg [9:0] ek [0:15]; reg [3:0] ew [0:15]; reg [31:0] ed [0:15];
    wire f_rng = p_rng, f_al = p_al;
    always @* begin : p_dec integer k; reg [50:0] el;
        for (k = 0; k < 16; k = k + 1) begin
            el = (k % 2 == 0) ? f_c[104*(k/2) + 1 +: 51] : f_c[104*(k/2) + 53 +: 51];
            ek[k] = el[17:8]; ed[k] = el[50:19];
`ifdef OT_VM_CAPL_MUT_WORD
            ew[k] = {el[3:1], 1'b0};
`else
            ew[k] = el[3:0];
`endif
            eok[k] = p_ok[k];
        end
    end
    // ------------------------------------------------------------------ entry state
    reg [E-1:0] V; reg [9:0] KEY [0:E-1]; reg [15:0] MSK [0:E-1]; reg [511:0] DAT [0:E-1];
    reg [EB:0] fl_c; reg fl_on;              // flush slot counter (entry fl_c - 1 is written this cycle)
    // The entry registers are the merge stage. Select the prior completed row
    // from these registers for the output stage, and virtually free that entry
    // before accepting the current inputs. This permits immediate entry reuse
    // without an extra data array, ready signal or throughput bubble.
    reg [E-1:0] effV, full;
    reg [15:0] effM [0:E-1];
    reg sel, two;
    integer fe;
    reg flush_q;
    reg [3:0] gid_q, flags_q;
    // Carry the selected entry as one-hot control through clear and snapshot.
    // An integer priority encoder followed by dynamic array decoders lengthens
    // the feedback path from a completed entry into the next merge.
    reg [E-1:0] selected, first_full, flush_hit;
    always @* begin : p_pick
        integer e;
        reg any_full;
        for (e = 0; e < E; e = e + 1)
            full[e] = V[e] && MSK[e] == 16'hffff;
        any_full = |full;
        sel = 1'b0; two = 1'b0; fe = 0;
        for (e = 0; e < E; e = e + 1) begin
            first_full[e] = full[e] && !(|(full & ((1 << e)-1)));
            flush_hit[e] = fl_on && fl_c == e+1 && V[e] && |MSK[e];
            selected[e] = first_full[e] || (!any_full && flush_hit[e]);
            sel = sel | selected[e];
            fe = fe | (selected[e] ? e : 0);
            two = two | (full[e] && |(full & ((1 << e)-1))) |
                        (any_full && flush_hit[e] && !first_full[e]);
            effV[e] = V[e] && !selected[e];
            effM[e] = selected[e] ? 16'd0 : MSK[e];
        end
    end
    // next-state (combinational) per entry
    reg [E-1:0] nV; reg [9:0] nK [0:E-1]; reg [15:0] nM [0:E-1]; reg [511:0] nD [0:E-1];
    reg f_alias, f_dup;
    // Alignment proves ew[k][3:1] == k/2 for every eok[k]. A word
    // therefore has exactly two possible producers, the two inputs of its root.
    // Select the entry key once, then use two fixed data candidates per word.
    // This avoids a blocking 16-input merge chain on every 512-bit entry.
    always @* begin : p_merge
        integer e, k, w, j;
        reg hit, a, b, same_first;
        reg [9:0] kk;
        reg [15:0] targeted, first, accepted;
        f_alias = 1'b0; f_dup = 1'b0;
        for (e = 0; e < E; e = e + 1) begin
            for (k = 0; k < 16; k = k + 1)
                targeted[k] = p_tgt[E*k + e];
            // Parallel prefix priority: each candidate tests a CONSTANT prefix
            // mask. The key is an OR reduction of one-hot candidates, avoiding
            // sixteen cascaded 10-bit priority muxes on the data path.
            for (k = 0; k < 16; k = k + 1)
                first[k] = targeted[k] && !(|(targeted & ((16'h1 << k) - 16'd1)));
            kk = 10'd0;
            for (k = 0; k < 16; k = k + 1)
                kk = kk | (ek[k] & {10{first[k]}});
            accepted = 16'd0;
            for (k = 0; k < 16; k = k + 1) begin
                if (targeted[k]) begin
                    // Compare candidate keys in parallel with first-choice
                    // control. This avoids muxing a ten-bit key and THEN
                    // comparing it on every data acceptance path.
                    same_first = 1'b0;
                    for (j = 0; j < 16; j = j + 1)
                        same_first = same_first | (first[j] && ek[k] == ek[j]);
                    if (effV[e] ? ek[k] != KEY[e] : !same_first) f_alias = 1'b1;
                    else accepted[k] = 1'b1;
                end
            end
            hit = |accepted;
            // An empty entry always accepts its first targeted valid input;
            // a live entry retains its key. Neither control needs to wait for
            // the accepted-data key comparisons to return.
            nV[e] = effV[e] || (|targeted);
            nK[e] = (!effV[e] && (|targeted)) ? kk : KEY[e];
            // Existing-word duplicates compare directly with the registered
            // key. Alignment fixes ew[k][3:1] to k/2, so only bit0 selects
            // between this root's two mask bits. New pairs duplicate iff the
            // two accepted elements select the same low word bit.
            for (k = 0; k < 16; k = k + 1)
                if (targeted[k] && ek[k] == KEY[e] &&
                    effM[e][2*(k/2)+ew[k][0]]) f_dup = 1'b1;
            for (k = 0; k < 8; k = k + 1)
                if (accepted[2*k] && accepted[2*k+1] &&
                    ew[2*k][0] == ew[2*k+1][0]) f_dup = 1'b1;
            for (w = 0; w < 16; w = w + 1) begin
                a = accepted[2*(w/2)] && ew[2*(w/2)][0] == w[0];
                b = accepted[2*(w/2)+1] && ew[2*(w/2)+1][0] == w[0];
                nM[e][w] = effM[e][w] || a || b;
                // Match the original ascending-k blocking merge: last wins.
                nD[e][32*w +: 32] = b ? ed[2*(w/2)+1] :
                                      a ? ed[2*(w/2)] : DAT[e][32*w +: 32];
            end
        end
    end
    // Merge into the entry flops, then snapshot the prior selected entry to
    // the output. Every valid row and sticky fault moves by exactly one serial
    // edge relative to PIPE=0. The flush itinerary also moves by one edge.
    always @(posedge ck) begin : p_out
        integer e;
        // Mutable data has no reset. Its mask/valid state is reset; arbitrary
        // data changes while invalid cannot create a row or a masked write.
        for (e = 0; e < E; e = e + 1) begin
            DAT[e] <= nD[e]; KEY[e] <= nK[e];
        end
        gid_q <= gid;
        if (!rn) begin
            V <= '0; o_v <= 1'b0; flt <= 0;
            fl_on <= 1'b0; fl_c <= 0; flush_q <= 1'b0; flags_q <= 0;
            for (e = 0; e < E; e = e + 1) MSK[e] <= 0;
        end else begin
            for (e = 0; e < E; e = e + 1) begin
                V[e] <= nV[e]; MSK[e] <= nM[e];
            end
            o_v <= sel;
            if (sel) begin o_row <= {KEY[fe], gid_q}; o_m <= MSK[fe]; o_d <= DAT[fe]; end
            flush_q <= flush;
            if (flush_q) begin fl_on <= 1'b1; fl_c <= 1; end
            else if (fl_on) begin if (fl_c == E) fl_on <= 1'b0; else fl_c <= fl_c + 1'b1; end
            flags_q <= {f_dup, f_alias, f_al, f_rng};
            flt <= flt | {two, flags_q};
        end
    end
endmodule
`default_nettype wire
