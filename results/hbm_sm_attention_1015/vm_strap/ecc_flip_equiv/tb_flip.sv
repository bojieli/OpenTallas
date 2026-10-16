module tb_flip;
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1) for (b = a + 1; b < 7; b = b + 1) for (c = b + 1; c < 7; c = c + 1) begin
                if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c); n = n + 1; end
            colv = v; end
    endfunction
    reg [32*7-1:0] COLS; reg [7*32-1:0] ROWM;
    function automatic [6:0] chk(input [31:0] d);
        integer j; reg [6:0] c; begin for (j = 0; j < 7; j = j + 1) c[j] = ^(d & ROWM[j*32 +: 32]); chk = c; end
    endfunction
    integer n, i, k, e1, e2, bad, nc, nu; reg [31:0] d, dd; reg [6:0] ck, s; reg [31:0] cor_o, cor_n, flip; reg hit_o, hit_n, ue_o, ue_n;
    initial begin
        for (i = 0; i < 32; i = i + 1) COLS[i*7 +: 7] = colv(i);
        for (k = 0; k < 7; k = k + 1) for (i = 0; i < 32; i = i + 1) ROWM[k*32 + i] = COLS[i*7 + k];
        bad = 0; nc = 0; nu = 0;
        for (n = 0; n < 2000000; n = n + 1) begin
            d = $urandom; ck = chk(d); dd = d;
            e1 = $urandom % 40; e2 = $urandom % 40;
            case (n % 4) 0: ; 1: if (e1 < 32) dd[e1] = ~dd[e1]; else ck[e1-32] = ~ck[e1-32];
                2, 3: begin if (e1 < 32) dd[e1] = ~dd[e1]; else ck[e1-32] = ~ck[e1-32]; if (e2 < 32) dd[e2] = ~dd[e2]; else ck[e2-32] = ~ck[e2-32]; end endcase
            if (n % 97 == 0) ck = $urandom;
            s = chk(dd) ^ ck;
            cor_o = dd; hit_o = 0; ue_o = 0;
            if (s != 0) begin for (i = 0; i < 32; i = i + 1) if (s == COLS[i*7 +: 7]) begin cor_o[i] = ~cor_o[i]; hit_o = 1; end
                if (s == 1 || s == 2 || s == 4 || s == 8 || s == 16 || s == 32 || s == 64) hit_o = 1; if (!hit_o) ue_o = 1; end
            for (i = 0; i < 32; i = i + 1) flip[i] = (s == COLS[i*7 +: 7]);
            cor_n = dd ^ flip; hit_n = 0; ue_n = 0;
            if (s != 0) begin hit_n = |flip; if (s == 1 || s == 2 || s == 4 || s == 8 || s == 16 || s == 32 || s == 64) hit_n = 1; if (!hit_n) ue_n = 1; end
            if (cor_o !== cor_n || hit_o !== hit_n || ue_o !== ue_n) bad = bad + 1;
            if (hit_o) nc = nc + 1; if (ue_o) nu = nu + 1;
        end
        $display("ECC_FLIP_EQUIV vectors=%0d corrected=%0d uncorrectable=%0d mismatches=%0d %s", n, nc, nu, bad, bad ? "FAIL" : "PASS");
        $finish;
    end
endmodule
