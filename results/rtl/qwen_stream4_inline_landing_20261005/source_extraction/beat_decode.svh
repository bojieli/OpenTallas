    // ---- landed beats: decode and per-port slice writes ------------------------------------------
    reg [NPC-1:0]  b_rd, b_bad, b_drop;
    reg [16:0]     b_sec [0:NPC-1];
    reg [1:0]      b_n   [0:NPC-1];           // slice writes of the beat (1 K, 2 V, 0 dropped)
    reg [10:0]     b_tile [0:NPC-1][0:1];
    reg [6:0]      b_loc  [0:NPC-1][0:1];
    reg [511:0]    b_data [0:NPC-1][0:1];
    reg [511:0]    b_msk  [0:NPC-1][0:1];
    reg [NPC-1:0]  b_ktail;                   // the beat's words belong to the open K tile
    integer pi;
    always @(*) begin
        for (pi = 0; pi < NPC; pi = pi + 1) begin
            reg [16:0] s; reg [17:0] a; reg [10:0] c;
            reg [8:0] t; reg [6:0] d; reg h; reg [16:0] w; reg [12:0] pp; reg [2:0] q;
            reg [255:0] dat; reg [127:0] lm;
            dat = l_data[pi*256 +: 256];
            c = lcnt[pi];
            b_rd[pi] = 1'b0; b_bad[pi] = 1'b0; b_drop[pi] = 1'b0; b_n[pi] = 0; b_ktail[pi] = 1'b0;
            b_sec[pi] = 0;
            b_tile[pi][0] = 0; b_tile[pi][1] = 0; b_loc[pi][0] = 0; b_loc[pi][1] = 0;
            b_data[pi][0] = 0; b_data[pi][1] = 0; b_msk[pi][0] = 0; b_msk[pi][1] = 0;
            if (l_v[pi]) begin
                b_rd[pi] = 1'b1;
                //: exactly the next sector of this PC's stream, of this layer's row, inside the window
                if (!active || fill_done || c >= nfill || l_sec[pi*17 +: 17] != p2l(pi, c[9:0]) || l_row[pi*8 +: 8] != lyr)
                    b_bad[pi] = 1'b1;
                s = p2l(pi, c[9:0]);
                b_sec[pi] = s;
                a = {s, 1'b0};
                if (a < KVB) begin
                    h = a[16]; t = a[15:7]; d = a[6:0];       // d even: words d, d+1 share tile and local
                    b_n[pi] = 2'd1;
                    b_tile[pi][0] = (t % 48) * 32 + d / 4;
                    b_loc[pi][0] = (t / 48) * 2 + h;
                    //: the open tile: lanes >= P mod 16 are the token's (or later): never written by the fill
                    lm = (t == T) ? ((128'd1 << (8 * PL)) - 128'd1) : {128{1'b1}};
                    if (t == T) b_ktail[pi] = 1'b1;
                    b_data[pi][0] = {256'd0, dat} << (128 * d[1:0]);
                    b_msk[pi][0]  = {256'd0, lm, lm} << (128 * d[1:0]);
                end else begin
                    w = a - KVB;
                    h = w[16]; pp = w[15:3]; q = w[2:0];      // q even: dim tiles q, q+1
                    if (pp >= P[12:0]) b_drop[pi] = 1'b1;    // V of the token's position or later: not history
                    else begin
                        b_n[pi] = 2'd2;
                        b_tile[pi][0] = q * 128 + (pp % 512) / 4;
                        b_tile[pi][1] = (q + 1) * 128 + (pp % 512) / 4;
                        b_loc[pi][0] = KL + (pp / 512) * 2 + h;
                        b_loc[pi][1] = KL + (pp / 512) * 2 + h;
                        b_data[pi][0] = {384'd0, dat[127:0]} << (128 * pp[1:0]);
                        b_data[pi][1] = {384'd0, dat[255:128]} << (128 * pp[1:0]);
                        b_msk[pi][0]  = {384'd0, {128{1'b1}}} << (128 * pp[1:0]);
                        b_msk[pi][1]  = {384'd0, {128{1'b1}}} << (128 * pp[1:0]);
                    end
                end
            end
        end
    end

