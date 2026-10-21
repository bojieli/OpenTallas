module candidate(input[255:0] st_d,input[31:0] st_row,s_gs,input[2:0] s_stk,st_ph,input[4:0] st_sec,output[319:0] addresses); localparam AW=32;
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
    wire [31:0] s_ring = st_d[143:112];
    wire [31:0] s_local = (s_ring != 0) ? (st_row & af_add32(s_ring, 32'hffffffff)) : ((s_gs << 4) | (st_row & 32'd15));
    wire [31:0] s_rbase = af_add32(st_d[47:16], ((s_ring != 0) ? 32'd0 : af_mul3(st_d[79:48], s_stk)));
    wire [15:0] s_rb = st_d[183:168];
    wire [4:0]  s_pitch = st_d[84:80];
    wire [31:0] s_raddr = af_add32(s_rbase, af_mul5(s_local, s_pitch));          // pitch <= 31: shifts and adds
    // IKEY: super-block sb = gs / 64 (17 x 128 sectors), group q = gs mod 64
    wire [31:0] k_sb = s_gs >> 6;
    wire [5:0]  k_q = s_gs[5:0];
    wire [31:0] k_blk = af_add32(af_add32(s_rbase, (k_sb << 11)), (k_sb << 7));
    wire [31:0] k_code = af_add32(af_add32(af_add32(k_blk, (af_add32(32'd1, {28'd0, k_q[5:2]}) << 7)), ({30'd0, k_q[1:0]} << 5)), ((st_row & 32'd15) << 1));
    wire [31:0] k_scal = af_add32(k_blk, ({26'd0, k_q} << 1));

wire[31:0] u_raddr=s_raddr,u_kcode=k_code,u_kscal=k_scal;
wire[31:0] final0 = (AW == 32) ? af_add32(st_d[47:16], st_row) : (st_d[47:16] + st_row);
wire[31:0] final1 = (AW == 32) ? af_add32(u_raddr, {27'd0, st_sec}) : (u_raddr + st_sec);
wire[31:0] final2 = (AW == 32) ? af_add32(u_kcode, {29'd0, st_ph}) : (u_kcode + st_ph);
wire[31:0] final3 = (AW == 32) ? af_add32(u_kscal, (st_ph == 3'd4 ? 32'd1 : 32'd0)) : (u_kscal + (st_ph == 3'd4 ? 1 : 0));
assign addresses={s_local,s_rbase,s_raddr,k_blk,k_code,k_scal,final0,final1,final2,final3};
endmodule
