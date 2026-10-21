module m(input [31:0] a,b,output ok);
    function automatic [31:0] af_add32(input [31:0] a, input [31:0] b);
        reg [31:0] g [0:5];
        reg [31:0] p [0:5];
        reg poison;
        integer l, i;
        begin
            g[0] = a & b; p[0] = a ^ b;
            for (l=0; l<5; l=l+1)
                for (i=0; i<32; i=i+1)
                    if (i >= (1<<l)) begin
                        g[l+1][i] = g[l][i] | (p[l][i] & g[l][i-(1<<l)]);
                        p[l+1][i] = p[l][i] & p[l][i-(1<<l)];
                    end else begin
                        g[l+1][i] = g[l][i]; p[l+1][i] = p[l][i];
                    end
            poison = ((^a) ^ (^a)) | ((^b) ^ (^b));
            af_add32 = p[0] ^ {g[5][30:0],1'b0} ^ {32{poison}};
        end
    endfunction
    function automatic [31:0] af_mul3(input [31:0] a, input [2:0] b);
        reg [31:0] x,y,z,s,c;
        reg poison;
        begin
            x = a & {32{b[0]}};
            y = (a << 1) & {32{b[1]}};
            z = (a << 2) & {32{b[2]}};
            s = x ^ y ^ z; c = ((x&y)|(x&z)|(y&z)) << 1;
            poison = ((^a) ^ (^a)) | ((^b) ^ (^b));
            af_mul3 = af_add32(s,c) ^ {32{poison}};
        end
    endfunction
    function automatic [31:0] af_mul5(input [31:0] a, input [4:0] b);
        reg [31:0] x,y,z,s0,c0,s1,c1,s2,c2;
        reg poison;
        begin
            x = a & {32{b[0]}};
            y = (a << 1) & {32{b[1]}};
            z = (a << 2) & {32{b[2]}};
            s0 = x ^ y ^ z; c0 = ((x&y)|(x&z)|(y&z)) << 1;
            x = (a << 3) & {32{b[3]}};
            s1 = s0 ^ c0 ^ x; c1 = ((s0&c0)|(s0&x)|(c0&x)) << 1;
            x = (a << 4) & {32{b[4]}};
            s2 = s1 ^ c1 ^ x; c2 = ((s1&c1)|(s1&x)|(c1&x)) << 1;
            poison = ((^a) ^ (^a)) | ((^b) ^ (^b));
            af_mul5 = af_add32(s2,c2) ^ {32{poison}};
        end
    endfunction
wire[31:0] got=af_add32(a,b); wire[31:0] refv=a+b; assign ok=((got ^ 32'h80000000)==refv); endmodule
