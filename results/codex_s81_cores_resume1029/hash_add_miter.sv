module hash_add_miter(input wire [63:0] a64,b64, input wire [27:0] a28,b28,
 output wire equal64,equal28,mut_equal64,mut_equal28);
    function automatic [63:0] gold64(input [63:0] a, input [63:0] b);
        reg [8:0] z0, o0;
        reg [8:0] z1, o1;
        reg [8:0] z2, o2;
        reg [8:0] z3, o3;
        reg [8:0] z4, o4;
        reg [8:0] z5, o5;
        reg [8:0] z6, o6;
        reg [8:0] z7, o7;
        reg [8:0] c;
        begin
            c[0] = 1'b0;
            z0 = {1'b0, a[7:0]} + {1'b0, b[7:0]};
            o0 = {1'b0, a[7:0]} + {1'b0, b[7:0]} + 9'd1;
            c[1] = c[0] ? o0[8] : z0[8];
            gold64[7:0] = c[0] ? o0[7:0] : z0[7:0];
            z1 = {1'b0, a[15:8]} + {1'b0, b[15:8]};
            o1 = {1'b0, a[15:8]} + {1'b0, b[15:8]} + 9'd1;
            c[2] = c[1] ? o1[8] : z1[8];
            gold64[15:8] = c[1] ? o1[7:0] : z1[7:0];
            z2 = {1'b0, a[23:16]} + {1'b0, b[23:16]};
            o2 = {1'b0, a[23:16]} + {1'b0, b[23:16]} + 9'd1;
            c[3] = c[2] ? o2[8] : z2[8];
            gold64[23:16] = c[2] ? o2[7:0] : z2[7:0];
            z3 = {1'b0, a[31:24]} + {1'b0, b[31:24]};
            o3 = {1'b0, a[31:24]} + {1'b0, b[31:24]} + 9'd1;
            c[4] = c[3] ? o3[8] : z3[8];
            gold64[31:24] = c[3] ? o3[7:0] : z3[7:0];
            z4 = {1'b0, a[39:32]} + {1'b0, b[39:32]};
            o4 = {1'b0, a[39:32]} + {1'b0, b[39:32]} + 9'd1;
            c[5] = c[4] ? o4[8] : z4[8];
            gold64[39:32] = c[4] ? o4[7:0] : z4[7:0];
            z5 = {1'b0, a[47:40]} + {1'b0, b[47:40]};
            o5 = {1'b0, a[47:40]} + {1'b0, b[47:40]} + 9'd1;
            c[6] = c[5] ? o5[8] : z5[8];
            gold64[47:40] = c[5] ? o5[7:0] : z5[7:0];
            z6 = {1'b0, a[55:48]} + {1'b0, b[55:48]};
            o6 = {1'b0, a[55:48]} + {1'b0, b[55:48]} + 9'd1;
            c[7] = c[6] ? o6[8] : z6[8];
            gold64[55:48] = c[6] ? o6[7:0] : z6[7:0];
            z7 = {1'b0, a[63:56]} + {1'b0, b[63:56]};
            o7 = {1'b0, a[63:56]} + {1'b0, b[63:56]} + 9'd1;
            c[8] = c[7] ? o7[8] : z7[8];
            gold64[63:56] = c[7] ? o7[7:0] : z7[7:0];
        end
    endfunction
    function automatic [63:0] fast64(input [63:0] a, input [63:0] b);
        reg [63:0] p [0:6];
        reg [63:0] g [0:6];
        integer k;
        begin
            p[0] = a ^ b;
            g[0] = a & b;
            for (k = 0; k < 6; k = k + 1) begin
                g[k+1] = g[k] | (p[k] & (g[k] << (32'd1 << k)));
                p[k+1] = p[k] & (p[k] << (32'd1 << k));
            end
            fast64 = p[0] ^ {g[6][62:0], 1'b0};
        end
    endfunction
    function automatic [63:0] mut64(input [63:0] a, input [63:0] b);
        reg [63:0] p [0:6];
        reg [63:0] g [0:6];
        integer k;
        begin
            p[0] = a ^ b;
            g[0] = a & b;
            for (k = 0; k < 6; k = k + 1) begin
                g[k+1] = g[k] | (p[k] & (g[k] << (32'd1 << k)));
                p[k+1] = p[k] & (p[k] << (32'd1 << k));
            end
            mut64 = p[0] ^ {g[6][62:0], 1'b0};
            mut64[17] = p[0][17] ^ g[6][15]; // wrong carry bit control
        end
    endfunction
    assign equal64 = gold64(a64,b64) == fast64(a64,b64);
    assign mut_equal64 = gold64(a64,b64) == mut64(a64,b64);
    function automatic [27:0] gold28(input [27:0] a, input [27:0] b);
        reg [8:0] z0, o0;
        reg [8:0] z1, o1;
        reg [8:0] z2, o2;
        reg [4:0] z3, o3;
        reg [4:0] c;
        begin
            c[0] = 1'b0;
            z0 = {1'b0, a[7:0]} + {1'b0, b[7:0]};
            o0 = {1'b0, a[7:0]} + {1'b0, b[7:0]} + 9'd1;
            c[1] = c[0] ? o0[8] : z0[8];
            gold28[7:0] = c[0] ? o0[7:0] : z0[7:0];
            z1 = {1'b0, a[15:8]} + {1'b0, b[15:8]};
            o1 = {1'b0, a[15:8]} + {1'b0, b[15:8]} + 9'd1;
            c[2] = c[1] ? o1[8] : z1[8];
            gold28[15:8] = c[1] ? o1[7:0] : z1[7:0];
            z2 = {1'b0, a[23:16]} + {1'b0, b[23:16]};
            o2 = {1'b0, a[23:16]} + {1'b0, b[23:16]} + 9'd1;
            c[3] = c[2] ? o2[8] : z2[8];
            gold28[23:16] = c[2] ? o2[7:0] : z2[7:0];
            z3 = {1'b0, a[27:24]} + {1'b0, b[27:24]};
            o3 = {1'b0, a[27:24]} + {1'b0, b[27:24]} + 5'd1;
            c[4] = c[3] ? o3[4] : z3[4];
            gold28[27:24] = c[3] ? o3[3:0] : z3[3:0];
        end
    endfunction
    function automatic [27:0] fast28(input [27:0] a, input [27:0] b);
        reg [27:0] p [0:5];
        reg [27:0] g [0:5];
        integer k;
        begin
            p[0] = a ^ b;
            g[0] = a & b;
            for (k = 0; k < 5; k = k + 1) begin
                g[k+1] = g[k] | (p[k] & (g[k] << (32'd1 << k)));
                p[k+1] = p[k] & (p[k] << (32'd1 << k));
            end
            fast28 = p[0] ^ {g[5][26:0], 1'b0};
        end
    endfunction
    function automatic [27:0] mut28(input [27:0] a, input [27:0] b);
        reg [27:0] p [0:5];
        reg [27:0] g [0:5];
        integer k;
        begin
            p[0] = a ^ b;
            g[0] = a & b;
            for (k = 0; k < 5; k = k + 1) begin
                g[k+1] = g[k] | (p[k] & (g[k] << (32'd1 << k)));
                p[k+1] = p[k] & (p[k] << (32'd1 << k));
            end
            mut28 = p[0] ^ {g[5][26:0], 1'b0};
            mut28[17] = p[0][17] ^ g[5][15]; // wrong carry bit control
        end
    endfunction
    assign equal28 = gold28(a28,b28) == fast28(a28,b28);
    assign mut_equal28 = gold28(a28,b28) == mut28(a28,b28);
endmodule
