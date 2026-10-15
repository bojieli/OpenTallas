`timescale 1ns/1ps
module tb_tt_tree_partition;
parameter integer MUT=0;
localparam integer XW=24,G=3072;
reg clk=0;always #0.4166665 clk=~clk;
reg  rst_n=0;
wire [XW-1:0] ref_me_acc_o,dut_me_acc_o;
wire  ref_me_idle_o,dut_me_idle_o;
wire [15:0] ref_me_prog_o,dut_me_prog_o;
reg  up_fault=0;
reg [15:0] land_cnt=0;
wire  ref_scale_re,dut_scale_re;
wire [(G >> 7)-1:0] ref_scale_gre,dut_scale_gre;
wire [(G >> 7)*24-1:0] ref_scale_addr,dut_scale_addr;
wire [$clog2(G):0] ref_t_sel_e,dut_t_sel_e;
wire [$clog2(G):0] ref_t_tv_e,dut_t_tv_e;
reg [16-1:0] tr_fault=0;
wire  ref_p_v_e2,dut_p_v_e2;
wire [113-1:0] ref_p_f_e2,dut_p_f_e2;
reg [((G >> 7) / 4)*51-1:0] p_am=0;
reg [((G >> 7) / 4)-1:0] p_fault=0;
reg  fab_fault=0;
wire  ref_ov,dut_ov;
wire  ref_mx_we,dut_mx_we;
wire [24-1:0] ref_mx_addr,dut_mx_addr;
wire [16-1:0] ref_mx_mask,dut_mx_mask;
wire [16*32-1:0] ref_mx_data,dut_mx_data;
reg [379:0] cmd[0]=0;
wire [94:0] ref_ret,dut_ret;
qfd_tt_ctlm_tree_static u_ref(.clk(clk),.rst_n(rst_n),.me_acc_o(ref_me_acc_o),.me_idle_o(ref_me_idle_o),.me_prog_o(ref_me_prog_o),.up_fault(up_fault),.land_cnt(land_cnt),.scale_re(ref_scale_re),.scale_gre(ref_scale_gre),.scale_addr(ref_scale_addr),.t_sel_e(ref_t_sel_e),.t_tv_e(ref_t_tv_e),.tr_fault(tr_fault),.p_v_e2(ref_p_v_e2),.p_f_e2(ref_p_f_e2),.p_am(p_am),.p_fault(p_fault),.fab_fault(fab_fault),.ov(ref_ov),.mx_we(ref_mx_we),.mx_addr(ref_mx_addr),.mx_mask(ref_mx_mask),.mx_data(ref_mx_data),.cmd(cmd),.ret(ref_ret));
qfd_tt_tree_partition #(.MUT(MUT)) u_dut(.ck_core(clk),.ck_scale(clk),.rst_n(rst_n),.me_acc_o(dut_me_acc_o),.me_idle_o(dut_me_idle_o),.me_prog_o(dut_me_prog_o),.up_fault(up_fault),.land_cnt(land_cnt),.scale_re(dut_scale_re),.scale_gre(dut_scale_gre),.scale_addr(dut_scale_addr),.t_sel_e(dut_t_sel_e),.t_tv_e(dut_t_tv_e),.tr_fault(tr_fault),.p_v_e2(dut_p_v_e2),.p_f_e2(dut_p_f_e2),.p_am(p_am),.p_fault(p_fault),.fab_fault(fab_fault),.ov(dut_ov),.mx_we(dut_mx_we),.mx_addr(dut_mx_addr),.mx_mask(dut_mx_mask),.mx_data(dut_mx_data),.cmd(cmd),.ret(dut_ret));
integer cyc,checks=0,errors=0,scale_seen=0,go_seen=0; reg [31:0] rng=32'h4a9bf831;
task step_rng;begin rng=(rng<<13)^rng;rng=(rng>>17)^rng;rng=(rng<<5)^rng;end endtask
initial begin
repeat(8) @(negedge clk);rst_n=1;
for(cyc=0;cyc<30000;cyc=cyc+1)begin
@(negedge clk);step_rng();
cmd[0]=0;
if(cyc%1200==0)begin
cmd={24'd96,1'b1,1'b1,1'b1,1'b0,24'd32,24'd8,24'd0,1'b1,24'd8192,4'(7+(cyc/1200)%5),3'd0,24'd1,24'd1,24'd1,24'd0,24'd1,24'd1,24'd8,24'd128,1'b0,18'd4,18'd2,18'd4096,1'b0};
end
if(cyc%1200==16)begin cmd[0]=1;go_seen=go_seen+1;end
p_am={6{1'b1,rng,18'(cyc)}};
if(ref_ov)land_cnt=land_cnt+1;
if(cyc>800)begin
checks=checks+1;
if(ref_scale_re)scale_seen=scale_seen+1;
if(ref_me_acc_o !== dut_me_acc_o)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d me_acc_o",cyc);end
if(ref_me_idle_o !== dut_me_idle_o)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d me_idle_o",cyc);end
if(ref_me_prog_o !== dut_me_prog_o)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d me_prog_o",cyc);end
if(ref_scale_re !== dut_scale_re)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d scale_re",cyc);end
if(ref_scale_gre !== dut_scale_gre)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d scale_gre",cyc);end
if(ref_scale_addr !== dut_scale_addr)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d scale_addr",cyc);end
if(ref_t_sel_e !== dut_t_sel_e)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d t_sel_e",cyc);end
if(ref_t_tv_e !== dut_t_tv_e)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d t_tv_e",cyc);end
if(ref_p_v_e2 !== dut_p_v_e2)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d p_v_e2",cyc);end
if(ref_p_f_e2 !== dut_p_f_e2)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d p_f_e2",cyc);end
if(ref_ov !== dut_ov)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d ov",cyc);end
if(ref_mx_we !== dut_mx_we)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d mx_we",cyc);end
if(ref_mx_addr !== dut_mx_addr)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d mx_addr",cyc);end
if(ref_mx_mask !== dut_mx_mask)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d mx_mask",cyc);end
if(ref_mx_data !== dut_mx_data)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d mx_data",cyc);end
if(ref_ret !== dut_ret)begin errors=errors+1;if(errors<8)$display("MISMATCH %0d ret",cyc);end
end
end
if(scale_seen==0||go_seen<10)$fatal(1,"TT_SPLIT_UNSENSITIZED scale=%0d go=%0d",scale_seen,go_seen);
if(errors)$fatal(1,"TT_SPLIT_FAIL MUT=%0d errors=%0d checks=%0d scale=%0d",MUT,errors,checks,scale_seen);
$display("TT_SPLIT_PASS MUT=%0d checks=%0d scale=%0d",MUT,checks,scale_seen);$finish;
end
endmodule
