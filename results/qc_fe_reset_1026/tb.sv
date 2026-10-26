`timescale 1ns/1fs
module tb;
logic ck=0,rst_n=0;
always #0.4165 ck=~ck;
logic [1087:0]  st_dn_i='0;
logic [47:0]    sc_dn_i='0;
logic [1094:0]  ch_up_i='0;
logic [9:0]     ag_up_i='0;
logic [115:0]   cmd_q='0;
logic [1087:0]  st_up_c='0;
logic [47:0]    sc_up_c='0;
logic [452:0]   hr_c='0;
logic [1037:0]  chr_c='0;
logic [8:0]     treq_c='0;
logic [513:0]   l9_c='0;
wire [1087:0]  gold_se_q;
wire [1087:0]  new_se_q;
wire [1087:0]  off_se_q;
wire [1087:0]  mut_se_q;
wire [47:0]    gold_scd_q;
wire [47:0]    new_scd_q;
wire [47:0]    off_scd_q;
wire [47:0]    mut_scd_q;
wire [1094:0]  gold_chu_q;
wire [1094:0]  new_chu_q;
wire [1094:0]  off_chu_q;
wire [1094:0]  mut_chu_q;
wire [9:0]     gold_agu_q;
wire [9:0]     new_agu_q;
wire [9:0]     off_agu_q;
wire [9:0]     mut_agu_q;
wire [115:0]   gold_cmd_o;
wire [115:0]   new_cmd_o;
wire [115:0]   off_cmd_o;
wire [115:0]   mut_cmd_o;
wire [1087:0]  gold_st_up_o;
wire [1087:0]  new_st_up_o;
wire [1087:0]  off_st_up_o;
wire [1087:0]  mut_st_up_o;
wire [47:0]    gold_sc_up_o;
wire [47:0]    new_sc_up_o;
wire [47:0]    off_sc_up_o;
wire [47:0]    mut_sc_up_o;
wire [452:0]   gold_hr_o;
wire [452:0]   new_hr_o;
wire [452:0]   off_hr_o;
wire [452:0]   mut_hr_o;
wire [1037:0]  gold_ch_up_o;
wire [1037:0]  new_ch_up_o;
wire [1037:0]  off_ch_up_o;
wire [1037:0]  mut_ch_up_o;
wire [8:0]     gold_treq_o;
wire [8:0]     new_treq_o;
wire [8:0]     off_treq_o;
wire [8:0]     mut_treq_o;
wire [513:0]   gold_l9_o;
wire [513:0]   new_l9_o;
wire [513:0]   off_l9_o;
wire [513:0]   mut_l9_o;
gold_s6_fup u_gold (.ck(ck), .rst_n(rst_n), .st_dn_i(st_dn_i), .sc_dn_i(sc_dn_i), .ch_up_i(ch_up_i), .ag_up_i(ag_up_i), .se_q(gold_se_q), .scd_q(gold_scd_q), .chu_q(gold_chu_q), .agu_q(gold_agu_q), .cmd_q(cmd_q), .cmd_o(gold_cmd_o), .st_up_c(st_up_c), .st_up_o(gold_st_up_o), .sc_up_c(sc_up_c), .sc_up_o(gold_sc_up_o), .hr_c(hr_c), .hr_o(gold_hr_o), .chr_c(chr_c), .ch_up_o(gold_ch_up_o), .treq_c(treq_c), .treq_o(gold_treq_o), .l9_c(l9_c), .l9_o(gold_l9_o));
qfd_dv_s6_fup_reset_local u_new (.ck(ck), .rst_n(rst_n), .st_dn_i(st_dn_i), .sc_dn_i(sc_dn_i), .ch_up_i(ch_up_i), .ag_up_i(ag_up_i), .se_q(new_se_q), .scd_q(new_scd_q), .chu_q(new_chu_q), .agu_q(new_agu_q), .cmd_q(cmd_q), .cmd_o(new_cmd_o), .st_up_c(st_up_c), .st_up_o(new_st_up_o), .sc_up_c(sc_up_c), .sc_up_o(new_sc_up_o), .hr_c(hr_c), .hr_o(new_hr_o), .chr_c(chr_c), .ch_up_o(new_ch_up_o), .treq_c(treq_c), .treq_o(new_treq_o), .l9_c(l9_c), .l9_o(new_l9_o));
qfd_dv_s6_fup_reset_local #(.LOCAL_RESET_COPIES(1'b0)) u_off (.ck(ck), .rst_n(rst_n), .st_dn_i(st_dn_i), .sc_dn_i(sc_dn_i), .ch_up_i(ch_up_i), .ag_up_i(ag_up_i), .se_q(off_se_q), .scd_q(off_scd_q), .chu_q(off_chu_q), .agu_q(off_agu_q), .cmd_q(cmd_q), .cmd_o(off_cmd_o), .st_up_c(st_up_c), .st_up_o(off_st_up_o), .sc_up_c(sc_up_c), .sc_up_o(off_sc_up_o), .hr_c(hr_c), .hr_o(off_hr_o), .chr_c(chr_c), .ch_up_o(off_ch_up_o), .treq_c(treq_c), .treq_o(off_treq_o), .l9_c(l9_c), .l9_o(off_l9_o));
mut_s6_fup_reset_local #(.LOCAL_RESET_COPIES(1'b1)) u_mut (.ck(ck), .rst_n(rst_n), .st_dn_i(st_dn_i), .sc_dn_i(sc_dn_i), .ch_up_i(ch_up_i), .ag_up_i(ag_up_i), .se_q(mut_se_q), .scd_q(mut_scd_q), .chu_q(mut_chu_q), .agu_q(mut_agu_q), .cmd_q(cmd_q), .cmd_o(mut_cmd_o), .st_up_c(st_up_c), .st_up_o(mut_st_up_o), .sc_up_c(sc_up_c), .sc_up_o(mut_sc_up_o), .hr_c(hr_c), .hr_o(mut_hr_o), .chr_c(chr_c), .ch_up_o(mut_ch_up_o), .treq_c(treq_c), .treq_o(mut_treq_o), .l9_c(l9_c), .l9_o(mut_l9_o));
integer cyc=0,checks=0,mutant_diffs=0,mutant_first=-1;
task check_all; begin
 if ({new_se_q,new_scd_q,new_chu_q,new_agu_q,new_cmd_o,new_st_up_o,new_sc_up_o,new_hr_o,new_ch_up_o,new_treq_o,new_l9_o} !== {gold_se_q,gold_scd_q,gold_chu_q,gold_agu_q,gold_cmd_o,gold_st_up_o,gold_sc_up_o,gold_hr_o,gold_ch_up_o,gold_treq_o,gold_l9_o}) $fatal(1,"FUP lockstep mismatch cycle %0d time %0t",cyc,$time);
 if ({off_se_q,off_scd_q,off_chu_q,off_agu_q,off_cmd_o,off_st_up_o,off_sc_up_o,off_hr_o,off_ch_up_o,off_treq_o,off_l9_o} !== {gold_se_q,gold_scd_q,gold_chu_q,gold_agu_q,gold_cmd_o,gold_st_up_o,gold_sc_up_o,gold_hr_o,gold_ch_up_o,gold_treq_o,gold_l9_o}) $fatal(1,"FUP default-off mismatch cycle %0d time %0t",cyc,$time);
 if ({mut_se_q,mut_scd_q,mut_chu_q,mut_agu_q,mut_cmd_o,mut_st_up_o,mut_sc_up_o,mut_hr_o,mut_ch_up_o,mut_treq_o,mut_l9_o} !== {gold_se_q,gold_scd_q,gold_chu_q,gold_agu_q,gold_cmd_o,gold_st_up_o,gold_sc_up_o,gold_hr_o,gold_ch_up_o,gold_treq_o,gold_l9_o}) begin mutant_diffs++; if(mutant_first<0)mutant_first=cyc; end
 checks++;
end endtask
initial begin
for(cyc=0;cyc<20000;cyc++)begin
 @(negedge ck);
 st_dn_i = {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
 sc_dn_i = {$urandom(), $urandom()};
 ch_up_i = {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
 ag_up_i = {$urandom()};
 cmd_q = {$urandom(), $urandom(), $urandom(), $urandom()};
 st_up_c = {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
 sc_up_c = {$urandom(), $urandom()};
 hr_c = {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
 chr_c = {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
 treq_c = {$urandom()};
 l9_c = {$urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom(), $urandom()};
 if(cyc%11==0)begin cmd_q[0]=1'b1;cmd_q[3:1]=3'd7;end
 rst_n=!(cyc<3 || cyc%113<2);
 #0.000001;check_all();
 #0.101;if(cyc%17==0)rst_n=0;
 #0.000001;check_all();
 #0.047;if(cyc%17==0)rst_n=1;
 #0.000001;check_all();
 @(posedge ck);#0.000001;check_all();
 #0.101;if(cyc%31==0)rst_n=0;
 #0.000001;check_all();
 #0.047;if(cyc%31==0)rst_n=1;
 #0.000001;check_all();
end
if(mutant_diffs==0)$fatal(1,"mutant escaped");
$display("FUP_RESET_LOCKSTEP PASS cycles=%0d checks=%0d mutant_diffs=%0d mutant_first=%0d added_data_cycles=0 added_reset_cycles=0",cyc,checks,mutant_diffs,mutant_first);$finish;end
endmodule
