// New master; CLOSED c2 and old c_pa are untouched.
module dsdv_bksel_c_pa_n32(input wire ck,input wire[412:0]rst_profile,input wire[287:0]fs0_0,input wire[287:0]fs0_1,input wire[288:0]fs0_2,input wire[287:0]fs1_0,input wire[287:0]fs1_1,input wire[288:0]fs1_2,input wire[287:0]fs2_0,input wire[287:0]fs2_1,input wire[288:0]fs2_2,input wire[287:0]fs3_0,input wire[287:0]fs3_1,input wire[288:0]fs3_2,input wire[353:0]fo0,input wire[353:0]fo1,input wire[353:0]fo2,input wire[353:0]fo3,output wire[131:0]t_c_s,t_c_n,output wire[1:0]t_cr_s,t_cr_n,output wire[513:0]vd);
 wire[263:0]tc;wire[3:0]cr;wire vf;
 ot_s81pa_ctl u_c(.ck(ck),.rst_profile(rst_profile),.f_s({fs3_2,fs3_1,fs3_0,fs2_2,fs2_1,fs2_0,fs1_2,fs1_1,fs1_0,fs0_2,fs0_1,fs0_0}),.f_o({fo3,fo2,fo1,fo0}),.t_c(tc),.t_cr(cr),.vd(vd),.vf(vf));
 assign {t_c_n,t_c_s}=tc;assign {t_cr_n,t_cr_s}=cr;
endmodule
