    // ---- arbitration: token writes first, then beats in rotating order -------------------
    reg [$clog2(NPC)-1:0] rr;
    reg [NE-1:0]   e_v;
    reg [10:0]     e_tile [0:NE-1];
    reg [6:0]      e_loc  [0:NE-1];
    reg [511:0]    e_data [0:NE-1];
    reg [511:0]    e_msk  [0:NE-1];
    reg            tok_conflict;
    integer ai, aj, ak, pp_i;
    integer tent [0:NT-1];           // the entry that claimed a tile this cycle (-1: none)
    reg [3:0]      seen_q [0:NT-1];  // lane quarters of the valid beat requests of the claimed word so far
    reg [1:0]      hdone [0:NPC-1];  // halves of the presented beat written in earlier cycles
    reg [1:0]      h_got [0:NPC-1];  // halves written by this cycle
    always @(*) begin
        reg ok; integer n;
        for (ai = 0; ai < NE; ai = ai + 1) begin e_v[ai] = 1'b0; e_tile[ai] = 0; e_loc[ai] = 0; e_data[ai] = 0; e_msk[ai] = 0; end
        for (ai = 0; ai < NT; ai = ai + 1) tent[ai] = -1;
        tok_conflict = 1'b0;
        n = 0;
        // token lanes merged per tile (same tile => same local word, else a protocol fault)
        for (ai = 0; ai < SW; ai = ai + 1)
            if (l_v_tok[ai]) begin
                ok = 1'b0;
                for (aj = 0; aj < SW; aj = aj + 1)
                    if (aj < n && e_v[aj] && e_tile[aj] == l_tile[ai]) begin
                        ok = 1'b1;
                        if (e_loc[aj] != l_loc[ai]) tok_conflict = 1'b1;
                        e_data[aj] = e_data[aj] | ({504'd0, l_code[ai]} << l_bit[ai]);
                        e_msk[aj]  = e_msk[aj]  | ({504'd0, 8'hff} << l_bit[ai]);
                    end
                if (!ok) begin
                    tent[l_tile[ai]] = n;
                    e_v[n] = 1'b1; e_tile[n] = l_tile[ai]; e_loc[n] = l_loc[ai];
                    e_data[n] = {504'd0, l_code[ai]} << l_bit[ai];
                    e_msk[n]  = {504'd0, 8'hff} << l_bit[ai];
                    n = n + 1;
                end
            end
        // beats: each beat HALF (slice write) is arbitrated at its own tile by the per-tile landing merge
        // (rtl/hdc/kv/ot_qwen_kv_land_merge.sv, the hardened element; same rule): the first valid request in
        // rotating port order claims the tile's write (unless a token write holds it); a later request joins
        // that write iff it is for the same slice word and its lane quarters overlap no EARLIER valid request
        // of that word.  A V beat's two halves are granted independently; the beat pops when both are written.
        l_pop = 0;
        for (ai = 0; ai < NPC; ai = ai + 1) h_got[ai] = hdone[ai];
        for (ai = 0; ai < NT; ai = ai + 1) seen_q[ai] = 4'd0;
        for (pp_i = 0; pp_i < NPC; pp_i = pp_i + 1) begin
            integer p; reg [1:0] need; reg [3:0] qv; integer tl;
            p = (rr + pp_i) % NPC;
            if (l_v[p]) begin
                if (b_bad[p] || b_drop[p]) l_pop[p] = 1'b1;          // no slice write (a bad beat faults)
                else begin
                    need = (b_n[p] == 2'd2) ? 2'b11 : 2'b01;
                    for (ak = 0; ak < 2; ak = ak + 1)
                        if (need[ak] && !hdone[p][ak]) begin
                            tl = b_tile[p][ak];
                            qv = {|b_msk[p][ak][511:384], |b_msk[p][ak][383:256], |b_msk[p][ak][255:128], |b_msk[p][ak][127:0]};
                            aj = tent[tl];
                            if (aj < 0) begin
                                tent[tl] = SW + 2 * p + ak; seen_q[tl] = qv; h_got[p][ak] = 1'b1;
                                e_v[SW + 2 * p + ak] = 1'b1;
                                e_tile[SW + 2 * p + ak] = b_tile[p][ak]; e_loc[SW + 2 * p + ak] = b_loc[p][ak];
                                e_data[SW + 2 * p + ak] = b_data[p][ak]; e_msk[SW + 2 * p + ak] = b_msk[p][ak];
                            end else if (aj >= SW && e_loc[aj] == b_loc[p][ak]) begin
                                if ((seen_q[tl] & qv) == 4'd0) begin
                                    e_data[aj] = e_data[aj] | b_data[p][ak];
                                    e_msk[aj]  = e_msk[aj]  | b_msk[p][ak];
                                    h_got[p][ak] = 1'b1;
                                end
                                seen_q[tl] = seen_q[tl] | qv;
                            end
                        end
                    if ((h_got[p] & need) == need) l_pop[p] = 1'b1;
                end
            end
        end
    end
    // halves of the presented beat already written (a V beat whose other half waits)
    integer hi;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) for (hi = 0; hi < NPC; hi = hi + 1) hdone[hi] <= 2'b00;
        else for (hi = 0; hi < NPC; hi = hi + 1)
            if (l_v[hi]) hdone[hi] <= l_pop[hi] ? 2'b00 : h_got[hi];

