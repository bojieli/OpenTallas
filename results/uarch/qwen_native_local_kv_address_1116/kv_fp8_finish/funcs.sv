    function automatic [31:0] fp8r_fin(input [31:0] p);
        reg [3:0] m4; reg [8:0] e9; reg [3:0] n; reg [31:0] y;
        begin
            y = 32'd0;
            if (p[30:29] == 2'd1) begin
                m4 = {1'b1, p[10:8]} + {3'd0, p[11]};
                e9 = {1'b0, p[7:0]};
                if (m4 == 4'd0) begin e9 = e9 + 9'd1; m4 = 4'd8; end
                if (e9 > 9'd135 || (e9 == 9'd135 && m4 > 4'd14)) y = {p[31], 8'd135, 3'b110, 20'd0};
                else y = {p[31], e9[7:0], m4[2:0], 20'd0};
            end else if (p[30:29] == 2'd2) begin
                n = {1'b0, p[2:0]} + {3'd0, p[3]};
                if (n == 4'd0) y = 32'd0;
                else if (n[3]) y = {p[31], 8'd121, 23'd0};
                else if (n[2]) y = {p[31], 8'd120, n[1:0], 21'd0};
                else if (n[1]) y = {p[31], 8'd119, n[0], 22'd0};
                else y = {p[31], 8'd118, 23'd0};
            end
            fp8r_fin = y;
        end
    endfunction
    function automatic [31:0] fp8r(input [31:0] v);
        reg [7:0] ex; reg [22:0] mt; reg [24:0] sig; reg [4:0] sh; reg [24:0] n, rem, half;
        reg [3:0] m4; reg up; integer e; reg [31:0] y;
        begin
            ex = v[30:23]; mt = v[22:0]; e = ex - 127;
            if (ex == 0) y = 32'd0;
            else if (e >= -6) begin
                up = v[19] && ((|v[18:0]) || v[20]);
                m4 = {1'b1, v[22:20]} + up;
                if (m4 == 0) begin e = e + 1; m4 = 4'd8; end
                if (e > 8 || (e == 8 && m4 > 4'd14)) y = {v[31], 8'd135, 3'b110, 20'd0};
                else y = {v[31], e[7:0] + 8'd127, m4[2:0], 20'd0};
            end else begin
                sig = {2'b01, mt};
                if (14 - e >= 26) y = 32'd0;
                else begin
                    sh = 14 - e;
                    n = sig >> sh; rem = sig & ((25'd1 << sh) - 1); half = 25'd1 << (sh - 1);
                    if (rem > half || (rem == half && n[0])) n = n + 1;
                    if (n == 0) y = 32'd0;
                    else if (n[3]) y = {v[31], 8'd121, 23'd0};
                    else if (n[2]) y = {v[31], 8'd120, n[1:0], 21'd0};
                    else if (n[1]) y = {v[31], 8'd119, n[0], 22'd0};
                    else y = {v[31], 8'd118, 23'd0};
                end
            end
            fp8r = y;
        end
    endfunction
    function automatic [31:0] fp8r_pre(input [31:0] v);
        reg [7:0] ex; reg [22:0] mt; reg [2:0] n0; reg r; reg [31:0] p;
        begin
            ex = v[30:23]; mt = v[22:0]; p = 32'd0; p[31] = v[31];
            if (ex == 8'd0) p[30:29] = 2'd0;
            else if (ex >= 8'd121) begin
                p[30:29] = 2'd1; p[7:0] = ex; p[10:8] = v[22:20];
                p[11] = v[19] && ((|v[18:0]) || v[20]);
            end else if (ex >= 8'd116) begin
                p[30:29] = 2'd2;
                case (ex)
                    8'd120: begin n0 = {1'b1, mt[22:21]}; r = mt[20] && ((|mt[19:0]) || mt[21]); end   // sh 21
                    8'd119: begin n0 = {2'b01, mt[22]};   r = mt[21] && ((|mt[20:0]) || mt[22]); end   // sh 22
                    8'd118: begin n0 = 3'd1;              r = mt[22] && ((|mt[21:0]) || 1'b1); end     // sh 23
                    8'd117: begin n0 = 3'd0;              r = (|mt); end                                // sh 24
                    default: begin n0 = 3'd0;             r = 1'b0; end                                 // sh 25
                endcase
                p[2:0] = n0; p[3] = r;
            end
            fp8r_pre = p;
        end
    endfunction
