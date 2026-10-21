`timescale 1ns/1ps
module s8_guard_cut(input ck,rst,output reg done=0);
integer cycle=0,checks=0,unknown_checks=0;integer mutant=0;
initial if($value$plusargs("mutant=%d",mutant))begin end
reg [115:0] r_cmd_q;
reg [1037:0] r_chd_q;
reg  r_tw_we;
reg [1:0] r_tw_kind;
reg [23:0] r_tw_addr;
reg [1023:0] r_tw_data;
wire [115:0] r_old_ctl_cmd,r_new_ctl_cmd;
wire [1037:0] r_old_ctl_chd,r_new_ctl_chd;
wire  r_old_vtw_we,r_new_vtw_we;
wire [1:0] r_old_vtw_kind,r_new_vtw_kind;
wire [23:0] r_old_vtw_addr,r_new_vtw_addr;
wire [1023:0] r_old_vtw_data,r_new_vtw_data;
wire  r_old_fault,r_new_fault;
qfd_dv_s8_rp1_reference r_old(.ck(ck),.rst_n(rst),.cmd_q(r_cmd_q),.chd_q(r_chd_q),.tw_we(r_tw_we),.tw_kind(r_tw_kind),.tw_addr(r_tw_addr),.tw_data(r_tw_data),.ctl_cmd(r_old_ctl_cmd),.ctl_chd(r_old_ctl_chd),.vtw_we(r_old_vtw_we),.vtw_kind(r_old_vtw_kind),.vtw_addr(r_old_vtw_addr),.vtw_data(r_old_vtw_data),.fault(r_old_fault));
qfd_dv_s8_rp1 r_new(.ck(ck),.rst_n(rst),.cmd_q(r_cmd_q),.chd_q(r_chd_q),.tw_we(r_tw_we),.tw_kind(r_tw_kind),.tw_addr(r_tw_addr),.tw_data(r_tw_data),.ctl_cmd(r_new_ctl_cmd),.ctl_chd(r_new_ctl_chd),.vtw_we(r_new_vtw_we),.vtw_kind(r_new_vtw_kind),.vtw_addr(r_new_vtw_addr),.vtw_data(r_new_vtw_data),.fault(r_new_fault));
reg [115:0] f_cmd_i;
reg [452:0] f_hr_i;
reg [1087:0] f_st_up_i;
reg [47:0] f_sc_up_i;
reg [1037:0] f_ch_dn_i;
reg [8:0] f_treq_i;
wire [115:0] f_old_cmd_q,f_new_cmd_q;
wire [452:0] f_old_hr_q,f_new_hr_q;
wire [1087:0] f_old_sw_q,f_new_sw_q;
wire [47:0] f_old_scu_q,f_new_scu_q;
wire [1037:0] f_old_chd_q,f_new_chd_q;
wire [8:0] f_old_treq_q,f_new_treq_q;
reg [45:0] f_chu_ar_sel;
reg [45:0] f_chu_dd_sel;
reg [1094:0] f_chu_q;
reg [1094:0] f_own_ch;
wire [1094:0] f_old_ch_dn_o,f_new_ch_dn_o;
wire  f_old_pc_bad,f_new_pc_bad;
reg [9:0] f_agu_q;
reg [9:0] f_ag_own;
wire [9:0] f_old_ag_dn_o,f_new_ag_dn_o;
reg [1087:0] f_st_dn_c;
wire [1087:0] f_old_st_dn_o,f_new_st_dn_o;
reg [47:0] f_sc_dn_c;
wire [47:0] f_old_sc_dn_o,f_new_sc_dn_o;
reg [106:0] f_st_c;
wire [106:0] f_old_st,f_new_st;
reg [49:0] f_cc_c;
wire [49:0] f_old_cc_o,f_new_cc_o;
reg [513:0] f_l9_i;
wire [65:0] f_old_l9_r0,f_new_l9_r0;
wire [65:0] f_old_l9_r1,f_new_l9_r1;
wire [65:0] f_old_l9_r2,f_new_l9_r2;
wire [65:0] f_old_l9_r3,f_new_l9_r3;
wire [65:0] f_old_l9_r4,f_new_l9_r4;
wire [65:0] f_old_l9_r5,f_new_l9_r5;
wire [65:0] f_old_l9_r6,f_new_l9_r6;
wire [65:0] f_old_l9_r7,f_new_l9_r7;
wire [8:0] f_old_treq_c,f_new_treq_c;
qfd_dv_s8_fdn_arf1_reference #(.USE_SEL_COPIES(1)) f_old(.ck(ck),.rst_n(rst),.cmd_i(f_cmd_i),.hr_i(f_hr_i),.st_up_i(f_st_up_i),.sc_up_i(f_sc_up_i),.ch_dn_i(f_ch_dn_i),.treq_i(f_treq_i),.cmd_q(f_old_cmd_q),.hr_q(f_old_hr_q),.sw_q(f_old_sw_q),.scu_q(f_old_scu_q),.chd_q(f_old_chd_q),.treq_q(f_old_treq_q),.chu_ar_sel(f_chu_ar_sel),.chu_dd_sel(f_chu_dd_sel),.chu_q(f_chu_q),.own_ch(f_own_ch),.ch_dn_o(f_old_ch_dn_o),.pc_bad(f_old_pc_bad),.agu_q(f_agu_q),.ag_own(f_ag_own),.ag_dn_o(f_old_ag_dn_o),.st_dn_c(f_st_dn_c),.st_dn_o(f_old_st_dn_o),.sc_dn_c(f_sc_dn_c),.sc_dn_o(f_old_sc_dn_o),.st_c(f_st_c),.st(f_old_st),.cc_c(f_cc_c),.cc_o(f_old_cc_o),.l9_i(f_l9_i),.l9_r0(f_old_l9_r0),.l9_r1(f_old_l9_r1),.l9_r2(f_old_l9_r2),.l9_r3(f_old_l9_r3),.l9_r4(f_old_l9_r4),.l9_r5(f_old_l9_r5),.l9_r6(f_old_l9_r6),.l9_r7(f_old_l9_r7),.treq_c(f_old_treq_c));
qfd_dv_s8_fdn_arf1 #(.USE_SEL_COPIES(1)) f_new(.ck(ck),.rst_n(rst),.cmd_i(f_cmd_i),.hr_i(f_hr_i),.st_up_i(f_st_up_i),.sc_up_i(f_sc_up_i),.ch_dn_i(f_ch_dn_i),.treq_i(f_treq_i),.cmd_q(f_new_cmd_q),.hr_q(f_new_hr_q),.sw_q(f_new_sw_q),.scu_q(f_new_scu_q),.chd_q(f_new_chd_q),.treq_q(f_new_treq_q),.chu_ar_sel(f_chu_ar_sel),.chu_dd_sel(f_chu_dd_sel),.chu_q(f_chu_q),.own_ch(f_own_ch),.ch_dn_o(f_new_ch_dn_o),.pc_bad(f_new_pc_bad),.agu_q(f_agu_q),.ag_own(f_ag_own),.ag_dn_o(f_new_ag_dn_o),.st_dn_c(f_st_dn_c),.st_dn_o(f_new_st_dn_o),.sc_dn_c(f_sc_dn_c),.sc_dn_o(f_new_sc_dn_o),.st_c(f_st_c),.st(f_new_st),.cc_c(f_cc_c),.cc_o(f_new_cc_o),.l9_i(f_l9_i),.l9_r0(f_new_l9_r0),.l9_r1(f_new_l9_r1),.l9_r2(f_new_l9_r2),.l9_r3(f_new_l9_r3),.l9_r4(f_new_l9_r4),.l9_r5(f_new_l9_r5),.l9_r6(f_new_l9_r6),.l9_r7(f_new_l9_r7),.treq_c(f_new_treq_c));
always @(negedge ck)begin
cycle=cycle+1;
for(integer b=0;b<116;b=b+1)r_cmd_q[b]=$random;
for(integer b=0;b<1038;b=b+1)r_chd_q[b]=$random;
r_tw_we=$random;
for(integer b=0;b<2;b=b+1)r_tw_kind[b]=$random;
for(integer b=0;b<24;b=b+1)r_tw_addr[b]=$random;
for(integer b=0;b<1024;b=b+1)r_tw_data[b]=$random;
for(integer b=0;b<116;b=b+1)f_cmd_i[b]=$random;
for(integer b=0;b<453;b=b+1)f_hr_i[b]=$random;
for(integer b=0;b<1088;b=b+1)f_st_up_i[b]=$random;
for(integer b=0;b<48;b=b+1)f_sc_up_i[b]=$random;
for(integer b=0;b<1038;b=b+1)f_ch_dn_i[b]=$random;
for(integer b=0;b<9;b=b+1)f_treq_i[b]=$random;
for(integer b=0;b<46;b=b+1)f_chu_ar_sel[b]=$random;
for(integer b=0;b<46;b=b+1)f_chu_dd_sel[b]=$random;
for(integer b=0;b<1095;b=b+1)f_chu_q[b]=$random;
for(integer b=0;b<1095;b=b+1)f_own_ch[b]=$random;
for(integer b=0;b<10;b=b+1)f_agu_q[b]=$random;
for(integer b=0;b<10;b=b+1)f_ag_own[b]=$random;
for(integer b=0;b<1088;b=b+1)f_st_dn_c[b]=$random;
for(integer b=0;b<48;b=b+1)f_sc_dn_c[b]=$random;
for(integer b=0;b<107;b=b+1)f_st_c[b]=$random;
for(integer b=0;b<50;b=b+1)f_cc_c[b]=$random;
for(integer b=0;b<514;b=b+1)f_l9_i[b]=$random;
r_cmd_q=0;f_cmd_i=0;r_chd_q[519:518]=0;
if(cycle%32==10)begin
 r_cmd_q[0]=1;r_cmd_q[3:1]=7;r_cmd_q[7:4]=3;
 f_cmd_i[0]=1;f_cmd_i[3:1]=7;f_cmd_i[7:4]=3;
end
if(cycle%32==12)begin
 r_cmd_q[0]=1;r_cmd_q[115:112]=15;r_cmd_q[5:4]=1;r_cmd_q[15:6]=16;
 f_cmd_i[0]=1;f_cmd_i[115:112]=15;f_cmd_i[5:4]=0;f_cmd_i[22:7]=4;f_cmd_i[54:23]=32'h11223344;
end
if(cycle%32>=14 && cycle%32<=21)begin
 r_chd_q[519:518]=3;r_chd_q[514:512]=3'(cycle%32-14);
 if(cycle%32==17)r_chd_q[519]=1'bx;
 if(cycle%32==18)r_chd_q[518]=1'bz;
 r_chd_q[31:0]=(cycle%2)?32'bz:32'bx;
 f_chu_q[1094]=1;
end
f_chu_ar_sel={46{f_chu_q[1094]}};f_chu_dd_sel={46{f_chu_q[547]}};
if(cycle%32==24)begin f_chu_ar_sel=46'bx;f_chu_dd_sel=46'bz;end
if(cycle%32==25)begin f_chu_q[1094]=1'bx;f_chu_q[547]=1'bz;end
end
always @(posedge ck)begin #1;
if(r_old_ctl_cmd!==r_new_ctl_cmd)$fatal(1,"GUARD_EQ_MISMATCH r.ctl_cmd cycle%0d",cycle);
if(r_old_ctl_chd!==r_new_ctl_chd)$fatal(1,"GUARD_EQ_MISMATCH r.ctl_chd cycle%0d",cycle);
if(r_old_vtw_we!==r_new_vtw_we)$fatal(1,"GUARD_EQ_MISMATCH r.vtw_we cycle%0d",cycle);
if(r_old_vtw_kind!==r_new_vtw_kind)$fatal(1,"GUARD_EQ_MISMATCH r.vtw_kind cycle%0d",cycle);
if(r_old_vtw_addr!==r_new_vtw_addr)$fatal(1,"GUARD_EQ_MISMATCH r.vtw_addr cycle%0d",cycle);
if(r_old_vtw_data!==r_new_vtw_data)$fatal(1,"GUARD_EQ_MISMATCH r.vtw_data cycle%0d",cycle);
if(r_old_fault!==r_new_fault)$fatal(1,"GUARD_EQ_MISMATCH r.fault cycle%0d",cycle);
if(f_old_cmd_q!==f_new_cmd_q)$fatal(1,"GUARD_EQ_MISMATCH f.cmd_q cycle%0d",cycle);
if(f_old_hr_q!==f_new_hr_q)$fatal(1,"GUARD_EQ_MISMATCH f.hr_q cycle%0d",cycle);
if(f_old_sw_q!==f_new_sw_q)$fatal(1,"GUARD_EQ_MISMATCH f.sw_q cycle%0d",cycle);
if(f_old_scu_q!==f_new_scu_q)$fatal(1,"GUARD_EQ_MISMATCH f.scu_q cycle%0d",cycle);
if(f_old_chd_q!==f_new_chd_q)$fatal(1,"GUARD_EQ_MISMATCH f.chd_q cycle%0d",cycle);
if(f_old_treq_q!==f_new_treq_q)$fatal(1,"GUARD_EQ_MISMATCH f.treq_q cycle%0d",cycle);
if(f_old_ch_dn_o!==f_new_ch_dn_o)$fatal(1,"GUARD_EQ_MISMATCH f.ch_dn_o cycle%0d",cycle);
if(f_old_pc_bad!==f_new_pc_bad)$fatal(1,"GUARD_EQ_MISMATCH f.pc_bad cycle%0d",cycle);
if(f_old_ag_dn_o!==f_new_ag_dn_o)$fatal(1,"GUARD_EQ_MISMATCH f.ag_dn_o cycle%0d",cycle);
if(f_old_st_dn_o!==f_new_st_dn_o)$fatal(1,"GUARD_EQ_MISMATCH f.st_dn_o cycle%0d",cycle);
if(f_old_sc_dn_o!==f_new_sc_dn_o)$fatal(1,"GUARD_EQ_MISMATCH f.sc_dn_o cycle%0d",cycle);
if(f_old_st!==f_new_st)$fatal(1,"GUARD_EQ_MISMATCH f.st cycle%0d",cycle);
if(f_old_cc_o!==f_new_cc_o)$fatal(1,"GUARD_EQ_MISMATCH f.cc_o cycle%0d",cycle);
if(f_old_l9_r0!==f_new_l9_r0)$fatal(1,"GUARD_EQ_MISMATCH f.l9_r0 cycle%0d",cycle);
if(f_old_l9_r1!==f_new_l9_r1)$fatal(1,"GUARD_EQ_MISMATCH f.l9_r1 cycle%0d",cycle);
if(f_old_l9_r2!==f_new_l9_r2)$fatal(1,"GUARD_EQ_MISMATCH f.l9_r2 cycle%0d",cycle);
if(f_old_l9_r3!==f_new_l9_r3)$fatal(1,"GUARD_EQ_MISMATCH f.l9_r3 cycle%0d",cycle);
if(f_old_l9_r4!==f_new_l9_r4)$fatal(1,"GUARD_EQ_MISMATCH f.l9_r4 cycle%0d",cycle);
if(f_old_l9_r5!==f_new_l9_r5)$fatal(1,"GUARD_EQ_MISMATCH f.l9_r5 cycle%0d",cycle);
if(f_old_l9_r6!==f_new_l9_r6)$fatal(1,"GUARD_EQ_MISMATCH f.l9_r6 cycle%0d",cycle);
if(f_old_l9_r7!==f_new_l9_r7)$fatal(1,"GUARD_EQ_MISMATCH f.l9_r7 cycle%0d",cycle);
if(f_old_treq_c!==f_new_treq_c)$fatal(1,"GUARD_EQ_MISMATCH f.treq_c cycle%0d",cycle);
if(r_old.sid_q!==r_new.sid_q)$fatal(1,"GUARD_STATE_MISMATCH r.sid_q cycle%0d",cycle);
if(r_old.sid_ok!==r_new.sid_ok)$fatal(1,"GUARD_STATE_MISMATCH r.sid_ok cycle%0d",cycle);
if(r_old.rp_arm!==r_new.rp_arm)$fatal(1,"GUARD_STATE_MISMATCH r.rp_arm cycle%0d",cycle);
if(r_old.rp_base!==r_new.rp_base)$fatal(1,"GUARD_STATE_MISMATCH r.rp_base cycle%0d",cycle);
if(r_old.rp_k!==r_new.rp_k)$fatal(1,"GUARD_STATE_MISMATCH r.rp_k cycle%0d",cycle);
if(f_old.arf_sid!==f_new.arf_sid)$fatal(1,"GUARD_STATE_MISMATCH f.arf_sid cycle%0d",cycle);
if(f_old.arf_sid_ok!==f_new.arf_sid_ok)$fatal(1,"GUARD_STATE_MISMATCH f.arf_sid_ok cycle%0d",cycle);
if(f_old.arf_arm!==f_new.arf_arm)$fatal(1,"GUARD_STATE_MISMATCH f.arf_arm cycle%0d",cycle);
if(f_old.arf_tag!==f_new.arf_tag)$fatal(1,"GUARD_STATE_MISMATCH f.arf_tag cycle%0d",cycle);
if(f_old.arf_wm1!==f_new.arf_wm1)$fatal(1,"GUARD_STATE_MISMATCH f.arf_wm1 cycle%0d",cycle);
if(f_old.arf_cnt!==f_new.arf_cnt)$fatal(1,"GUARD_STATE_MISMATCH f.arf_cnt cycle%0d",cycle);
if(f_old.pq!==f_new.pq)$fatal(1,"GUARD_STATE_MISMATCH f.pq cycle%0d",cycle);
checks=checks+1;if((^r_new_vtw_data)===1'bx)unknown_checks=unknown_checks+1;
if(cycle==255)begin if(checks<250||unknown_checks<4)$fatal(1,"GUARD_COVERAGE");$display("GUARD_EQ_PASS cycles%0d unknown_outputs%0d all_ports_all_state startup_reset_XZ",checks,unknown_checks);done=1;end
end
endmodule
