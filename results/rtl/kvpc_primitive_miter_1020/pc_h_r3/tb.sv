`timescale 1ps/1fs
module tb;
reg ck=0,hck=0,run_ck=1,run_hck=1; always #417 if(run_ck) ck=~ck; initial begin #0.3;forever #512 if(run_hck) hck=~hck;end
reg rst_n=0,hrst_n=0; integer mut=0,t=0,seed=1,dummy,checks=0,er_v=0,her_v=0,reset_checks=0; reg compare_on=0; wire dut_rst_n=rst_n && !(mut==2 && t>=1000 && t<1008);
reg [4:0] pc__pc=0;
reg [288:0] pc__pi=0;
reg [32:0] pc__ki=0;
reg [0:0] pc__fi=0;
reg [1:0] pc__cfg_stack=0;
reg [3:0] pc__front_hbm_data=0;
reg [3:0] pc__return_hbm_data=0;
reg [0:0] x__est__0_1=0;
reg [260:0] pc__land_er=0;
reg [287:0] pc__hes=0;
reg [32:0] i_grp=0;
reg [94:0] i_grp_h=0;
reg [779:0] i_next=0;
wire [0:0] r_pc__fo,d_pc__fo;
wire [2:0] r_pc__hfx,d_pc__hfx;
wire [260:0] r_pc__er,d_pc__er;
wire [32:0] r_pc__ko,d_pc__ko;
wire [327:0] r_pc__po,d_pc__po;
wire [0:0] r_pc__completion_v,d_pc__completion_v;
wire [0:0] r_pc__completion_we,d_pc__completion_we;
wire [287:0] r_pc__land_es,d_pc__land_es;
wire [260:0] r_pc__her,d_pc__her;
wire [0:0] r_pc__hcompletion_v,d_pc__hcompletion_v;
wire [0:0] r_pc__hcompletion_we,d_pc__hcompletion_we;
wire [294:0] r_o_grp,d_o_grp;
wire [9:0] r_o_grp_h,d_o_grp_h;
wire [298:0] r_o_next,d_o_next;
qkd_kvs_pc_h u_ref (.ck(ck), .rst_n(rst_n), .hck(hck), .hrst_n(hrst_n), .pc__pc(pc__pc), .pc__pi(pc__pi), .pc__ki(pc__ki), .pc__fi(pc__fi), .pc__cfg_stack(pc__cfg_stack), .pc__front_hbm_data(pc__front_hbm_data), .pc__return_hbm_data(pc__return_hbm_data), .x__est__0_1(x__est__0_1), .pc__land_er(pc__land_er), .pc__hes(pc__hes), .pc__fo(r_pc__fo), .pc__hfx(r_pc__hfx), .pc__er(r_pc__er), .pc__ko(r_pc__ko), .pc__po(r_pc__po), .pc__completion_v(r_pc__completion_v), .pc__completion_we(r_pc__completion_we), .pc__land_es(r_pc__land_es), .pc__her(r_pc__her), .pc__hcompletion_v(r_pc__hcompletion_v), .pc__hcompletion_we(r_pc__hcompletion_we), .i_grp(i_grp), .i_grp_h(i_grp_h), .i_next(i_next), .o_grp(r_o_grp), .o_grp_h(r_o_grp_h), .o_next(r_o_next));
qkd_kvs_pc_h_n32 u_dut (.ck(ck), .rst_n(dut_rst_n), .hck(hck), .hrst_n(hrst_n), .pc__pc(pc__pc), .pc__pi(pc__pi), .pc__ki(pc__ki), .pc__fi(pc__fi), .pc__cfg_stack(pc__cfg_stack), .pc__front_hbm_data(pc__front_hbm_data), .pc__return_hbm_data(pc__return_hbm_data), .x__est__0_1(x__est__0_1), .pc__land_er(pc__land_er), .pc__hes(pc__hes), .pc__fo(d_pc__fo), .pc__hfx(d_pc__hfx), .pc__er(d_pc__er), .pc__ko(d_pc__ko), .pc__po(d_pc__po), .pc__completion_v(d_pc__completion_v), .pc__completion_we(d_pc__completion_we), .pc__land_es(d_pc__land_es), .pc__her(d_pc__her), .pc__hcompletion_v(d_pc__hcompletion_v), .pc__hcompletion_we(d_pc__hcompletion_we), .i_grp(i_grp), .i_grp_h(i_grp_h), .i_next(i_next), .o_grp(d_o_grp), .o_grp_h(d_o_grp_h), .o_next(d_o_next));
task compare; begin
checks++; if(r_pc__er[0])er_v++;if(r_pc__her[0])her_v++;if(!rst_n||!hrst_n)reset_checks++;
if(r_pc__fo !== (d_pc__fo ^ 1'(mut==1)))$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__fo ref=%h dut=%h rst=%b/%b",mut,t,r_pc__fo,d_pc__fo,rst_n,hrst_n);
if(r_pc__hfx !== d_pc__hfx)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__hfx ref=%h dut=%h rst=%b/%b",mut,t,r_pc__hfx,d_pc__hfx,rst_n,hrst_n);
if((r_pc__er[0] !== d_pc__er[0]) || (r_pc__er[260:259] !== d_pc__er[260:259]) || (r_pc__er[0] && (r_pc__er[258:1] !== d_pc__er[258:1])))$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__er ref=%h dut=%h rst=%b/%b",mut,t,r_pc__er,d_pc__er,rst_n,hrst_n);
if(r_pc__ko !== d_pc__ko)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__ko ref=%h dut=%h rst=%b/%b",mut,t,r_pc__ko,d_pc__ko,rst_n,hrst_n);
if(r_pc__po !== d_pc__po)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__po ref=%h dut=%h rst=%b/%b",mut,t,r_pc__po,d_pc__po,rst_n,hrst_n);
if(r_pc__completion_v !== d_pc__completion_v)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__completion_v ref=%h dut=%h rst=%b/%b",mut,t,r_pc__completion_v,d_pc__completion_v,rst_n,hrst_n);
if(r_pc__completion_we !== d_pc__completion_we)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__completion_we ref=%h dut=%h rst=%b/%b",mut,t,r_pc__completion_we,d_pc__completion_we,rst_n,hrst_n);
if(r_pc__land_es !== d_pc__land_es)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__land_es ref=%h dut=%h rst=%b/%b",mut,t,r_pc__land_es,d_pc__land_es,rst_n,hrst_n);
if((r_pc__her[0] !== d_pc__her[0]) || (r_pc__her[260:259] !== d_pc__her[260:259]) || (r_pc__her[0] && (r_pc__her[258:1] !== d_pc__her[258:1])))$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__her ref=%h dut=%h rst=%b/%b",mut,t,r_pc__her,d_pc__her,rst_n,hrst_n);
if(r_pc__hcompletion_v !== d_pc__hcompletion_v)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__hcompletion_v ref=%h dut=%h rst=%b/%b",mut,t,r_pc__hcompletion_v,d_pc__hcompletion_v,rst_n,hrst_n);
if(r_pc__hcompletion_we !== d_pc__hcompletion_we)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=pc__hcompletion_we ref=%h dut=%h rst=%b/%b",mut,t,r_pc__hcompletion_we,d_pc__hcompletion_we,rst_n,hrst_n);
if(r_o_grp !== d_o_grp)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=o_grp ref=%h dut=%h rst=%b/%b",mut,t,r_o_grp,d_o_grp,rst_n,hrst_n);
if(r_o_grp_h !== d_o_grp_h)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=o_grp_h ref=%h dut=%h rst=%b/%b",mut,t,r_o_grp_h,d_o_grp_h,rst_n,hrst_n);
if(r_o_next !== d_o_next)$fatal(1,"KVPC_PRIMITIVE FAIL top=qkd_kvs_pc_h mut=%0d t=%0d out=o_next ref=%h dut=%h rst=%b/%b",mut,t,r_o_next,d_o_next,rst_n,hrst_n);
end endtask
always @(negedge ck) begin #0.01;if(compare_on)compare;end
always @(negedge hck) begin #0.02;if(compare_on)compare;end
initial begin
dummy=$value$plusargs("mut=%d",mut);dummy=$value$plusargs("seed=%d",seed);dummy=$urandom(seed);
pc__pc=5'd9;
pc__cfg_stack=2'd2;
repeat(12)@(negedge ck); compare_on=1; rst_n=1;hrst_n=1;
for(t=0;t<20000;t++)begin @(negedge ck);#0.05;
pc__pi=289'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom});
pc__ki=33'({$urandom,$urandom});
pc__fi=1'({$urandom});
pc__front_hbm_data=4'({$urandom});
pc__return_hbm_data=4'({$urandom});
x__est__0_1=1'({$urandom});
pc__land_er=261'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom});
pc__hes=288'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom});
i_grp=33'({$urandom,$urandom});
i_grp_h=95'({$urandom,$urandom,$urandom});
i_next=780'({$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom});
if(t==4000)rst_n=0;if(t==4006)rst_n=1;
if(t==7000)hrst_n=0;if(t==7008)hrst_n=1;
if(t==10000)begin run_hck=0;hrst_n=0;end if(t==10010)hrst_n=1;if(t==10020)run_hck=1;
if(t==13000)begin rst_n=0;hrst_n=0;end if(t==13008)begin rst_n=1;hrst_n=1;end
end
if(er_v==0||her_v==0||reset_checks==0)$fatal(1,"KVPC_PRIMITIVE FAIL coverage er=%0d her=%0d reset=%0d",er_v,her_v,reset_checks);
$display("KVPC_PRIMITIVE PASS top=qkd_kvs_pc_h mut=%0d checks=%0d er=%0d her=%0d resetchecks=%0d",mut,checks,er_v,her_v,reset_checks);$finish;end
integer power_row; reg[63:0] power_word; initial begin #0.001;
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.down.g_sram.u_mem.g_b[0].u_m .arr[power_row]=power_word; u_dut.u75551_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.down.g_sram.u_mem.g_b[1].u_m .arr[power_row]=power_word; u_dut.u75552_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.down.g_sram.u_mem.g_b[2].u_m .arr[power_row]=power_word; u_dut.u75553_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.down.g_sram.u_mem.g_b[3].u_m .arr[power_row]=power_word; u_dut.u75554_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.down.g_sram.u_mem.g_b[4].u_m .arr[power_row]=power_word; u_dut.u75555_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.down.g_sram.u_mem.g_b[5].u_m .arr[power_row]=power_word; u_dut.u75556_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.up.g_sram.u_mem.g_b[0].u_m .arr[power_row]=power_word; u_dut.u75597_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.up.g_sram.u_mem.g_b[1].u_m .arr[power_row]=power_word; u_dut.u75598_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.up.g_sram.u_mem.g_b[2].u_m .arr[power_row]=power_word; u_dut.u75599_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.up.g_sram.u_mem.g_b[3].u_m .arr[power_row]=power_word; u_dut.u75600_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_cdc.u_ecdc.up.g_sram.u_mem.g_b[4].u_m .arr[power_row]=power_word; u_dut.u75601_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_sched.u_tq.u_e .arr[power_row]=power_word; u_dut.u88785_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_ctrl.u_sched.u_tq.u_o .arr[power_row]=power_word; u_dut.u88786_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_front.u_mem.g_b[0].u_m .arr[power_row]=power_word; u_dut.u89137_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_front.u_mem.g_b[1].u_m .arr[power_row]=power_word; u_dut.u89138_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_front.u_mem.g_b[2].u_m .arr[power_row]=power_word; u_dut.u89139_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_front.u_mem.g_b[3].u_m .arr[power_row]=power_word; u_dut.u89140_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_front.u_mem.g_b[4].u_m .arr[power_row]=power_word; u_dut.u89141_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_return.u_mem.g_b[0].u_m .arr[power_row]=power_word; u_dut.u89556_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_return.u_mem.g_b[1].u_m .arr[power_row]=power_word; u_dut.u89557_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_return.u_mem.g_b[2].u_m .arr[power_row]=power_word; u_dut.u89558_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_return.u_mem.g_b[3].u_m .arr[power_row]=power_word; u_dut.u89559_c0.u_cell.arr[power_row]=power_word; end
for(power_row=0;power_row<32;power_row++)begin power_word={$urandom,$urandom}; u_ref.\u_pc.u_pce.u_path.u_return.u_mem.g_b[4].u_m .arr[power_row]=power_word; u_dut.u89560_c0.u_cell.arr[power_row]=power_word; end
end
endmodule
