// Pure port split around the exact CLOSED quarter. No edge, math, or storage.
module dsdv_bksel_q_pa(input wire ck,rst,input wire[256:0]lane_lo,input wire[257:0]lane_hi,input wire[66:0]ctl,
 output wire[287:0]t_s0,t_s1,output wire[288:0]t_s2,output wire[353:0]t_o);
 wire[864:0]ts;
 dsdv_bksel_q u_q(.ck(ck),.rst(rst),.lane({lane_hi,lane_lo}),.f_c(ctl[66:1]),.f_cr(ctl[0]),.t_s(ts),.t_o(t_o));
 assign {t_s2,t_s1,t_s0}=ts;
endmodule

module dsdv_bksel_c_pa(input wire ck,rst,input wire[287:0]fs0_0,input wire[287:0]fs0_1,input wire[288:0]fs0_2,input wire[287:0]fs1_0,input wire[287:0]fs1_1,input wire[288:0]fs1_2,input wire[287:0]fs2_0,input wire[287:0]fs2_1,input wire[288:0]fs2_2,input wire[287:0]fs3_0,input wire[287:0]fs3_1,input wire[288:0]fs3_2,input wire[353:0]fo0,input wire[353:0]fo1,input wire[353:0]fo2,input wire[353:0]fo3,output wire[131:0]t_c_s,t_c_n,output wire[1:0]t_cr_s,t_cr_n,output wire[513:0]vd);
 wire[263:0]tc;wire[3:0]cr;wire vf;
 dsfd_selt_c #(.SEARCH_PIPE(1),.DM(4),.PACE(2),.MRG_PIPE(1),.RQPIPE(1),.SLAT(4),.XDX(15))u_c(.ck(ck),.rst(rst),.f_s({fs3_2,fs3_1,fs3_0,fs2_2,fs2_1,fs2_0,fs1_2,fs1_1,fs1_0,fs0_2,fs0_1,fs0_0}),.f_o({fo3,fo2,fo1,fo0}),.t_c(tc),.t_cr(cr),.vd(vd),.vf(vf));
 assign {t_c_n,t_c_s}=tc;assign {t_cr_n,t_cr_s}=cr;
endmodule
