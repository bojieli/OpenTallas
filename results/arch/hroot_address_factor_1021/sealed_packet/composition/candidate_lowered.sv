module candidate_lowered(input[255:0] st_d,input[31:0] st_row,s_gs,input[2:0] s_stk,st_ph,input[4:0] st_sec,output[319:0] addresses); localparam AW=32;
    wire [31:0] s_ring = st_d[143:112];
    wire [31:0] s_local = (s_ring != 0) ? (st_row & ((s_ring) + ( 32'hffffffff))) : ((s_gs << 4) | (st_row & 32'd15));
    wire [31:0] s_rbase = ((st_d[47:16]) + ( ((s_ring != 0) ? 32'd0 : ((st_d[79:48]) * ( s_stk)))));
    wire [15:0] s_rb = st_d[183:168];
    wire [4:0]  s_pitch = st_d[84:80];
    wire [31:0] s_raddr = ((s_rbase) + ( ((s_local) * ( s_pitch))));          // pitch <= 31: shifts and adds
    // IKEY: super-block sb = gs / 64 (17 x 128 sectors), group q = gs mod 64
    wire [31:0] k_sb = s_gs >> 6;
    wire [5:0]  k_q = s_gs[5:0];
    wire [31:0] k_blk = ((((s_rbase) + ( (k_sb << 11)))) + ( (k_sb << 7)));
    wire [31:0] k_code = ((((((k_blk) + ( (((32'd1) + ( {28'd0, k_q[5:2]})) << 7)))) + ( ({30'd0, k_q[1:0]} << 5)))) + ( ((st_row & 32'd15) << 1)));
    wire [31:0] k_scal = ((k_blk) + ( ({26'd0, k_q} << 1)));

wire[31:0] u_raddr=s_raddr,u_kcode=k_code,u_kscal=k_scal;
wire[31:0] final0 = (AW == 32) ? ((st_d[47:16]) + ( st_row)) : (st_d[47:16] + st_row);
wire[31:0] final1 = (AW == 32) ? ((u_raddr) + ( {27'd0, st_sec})) : (u_raddr + st_sec);
wire[31:0] final2 = (AW == 32) ? ((u_kcode) + ( {29'd0, st_ph})) : (u_kcode + st_ph);
wire[31:0] final3 = (AW == 32) ? ((u_kscal) + ( (st_ph == 3'd4 ? 32'd1 : 32'd0))) : (u_kscal + (st_ph == 3'd4 ? 1 : 0));
assign addresses={s_local,s_rbase,s_raddr,k_blk,k_code,k_scal,final0,final1,final2,final3};
endmodule
