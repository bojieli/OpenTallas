    // ---- token (stream-unit) writes: per lane decode ------------------------------------
    // one slice write per lane, merged per tile below
    reg [SW-1:0]   l_v_tok;
    reg [10:0]     l_tile [0:SW-1];
    reg [6:0]      l_loc  [0:SW-1];
    reg [8:0]      l_bit  [0:SW-1];   // bit offset of the lane's code in the slice word
    reg [7:0]      l_code [0:SW-1];
    reg [SW-1:0]   l_bad;
    integer li;
    always @(*) begin
        for (li = 0; li < SW; li = li + 1) begin
            reg [AW-1:0] e; reg [AW-5:0] a; reg [8:0] fc; reg [16:0] w;
            reg [8:0] t; reg [6:0] d; reg h; reg [12:0] pp; reg [2:0] q;
            e = kv_waddr[li*AW +: AW];
            a = e[AW-1:4];
            fc = f32_e4m3(kv_wdata[li*32 +: 32]);
            l_v_tok[li] = kv_we[li];
            l_code[li] = fc[7:0];
            l_bad[li] = 1'b0;
            l_tile[li] = 0; l_loc[li] = 0; l_bit[li] = 0;
            if (kv_we[li]) begin
                if (fc[8]) l_bad[li] = 1'b1;
                if (a < KVB) begin
                    h = a[16]; t = a[15:7]; d = a[6:0];
                    if (a[19:17] != 0 || t != T || e[3:0] != PL) l_bad[li] = 1'b1;
                    l_tile[li] = (t % 48) * 32 + d / 4;
                    l_loc[li]  = (t / 48) * 2 + h;
                    l_bit[li]  = {d[1:0], e[3:0], 3'd0};
                end else begin
                    w = a - KVB;
                    h = w[16]; pp = w[15:3]; q = w[2:0];
                    if (a >= KVB + 131072 || pp != P[12:0]) l_bad[li] = 1'b1;
                    l_tile[li] = q * 128 + (pp % 512) / 4;
                    l_loc[li]  = KL + (pp / 512) * 2 + h;
                    l_bit[li]  = {pp[1:0], e[3:0], 3'd0};
                end
            end
        end
    end

