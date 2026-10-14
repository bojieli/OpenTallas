`timescale 1ns/1ps
// Registered physical pin seam around original production logic.
module qkd_host_csr_pins #(

    parameter integer NCNT = 16,
    parameter integer MUT_DIAG = 0
) (
    input  wire               clk,
    input  wire               rst_n,
    // host AXI4-Lite (13-bit address)
    input  wire               s_awvalid,
    output wire               s_awready,
    input  wire [12:0]        s_awaddr,
    input  wire               s_wvalid,
    output wire               s_wready,
    input  wire [31:0]        s_wdata,
    input  wire [3:0]         s_wstrb,
    output wire               s_bvalid,
    input  wire               s_bready,
    output wire [1:0]         s_bresp,
    input  wire               s_arvalid,
    output wire               s_arready,
    input  wire [12:0]        s_araddr,
    output wire               s_rvalid,
    input  wire               s_rready,
    output wire [31:0]        s_rdata,
    output wire [1:0]         s_rresp,
    // to / from ot_host_if (12-bit BAR)
    output wire               h_awvalid,
    input  wire               h_awready,
    output wire [11:0]        h_awaddr,
    output wire               h_wvalid,
    input  wire               h_wready,
    output wire [31:0]        h_wdata,
    output wire [3:0]         h_wstrb,
    input  wire               h_bvalid,
    output wire               h_bready,
    output wire               h_arvalid,
    input  wire               h_arready,
    output wire [11:0]        h_araddr,
    input  wire               h_rvalid,
    output wire               h_rready,
    input  wire [31:0]        h_rdata,
    input  wire               h_irq,
    // system state
    input  wire               sys_ready,
    input  wire               boot_fault,
    input  wire [3:0]         boot_state,
    input  wire [3:0]         boot_err,
    output wire                soft_rst,
    input  wire [31:0]        fault_src,
    input wire [31:0] die_fault_vec,
    input wire [79:0] die_kst,
    input  wire [NCNT*32-1:0] cnt,
    output wire               irq
);
wire  clk_i;
wire  rst_n_i;
wire  s_awvalid_i;
wire  s_awready_i;
wire [12:0] s_awaddr_i;
wire  s_wvalid_i;
wire  s_wready_i;
wire [31:0] s_wdata_i;
wire [3:0] s_wstrb_i;
wire  s_bvalid_i;
wire  s_bready_i;
wire [1:0] s_bresp_i;
wire  s_arvalid_i;
wire  s_arready_i;
wire [12:0] s_araddr_i;
wire  s_rvalid_i;
wire  s_rready_i;
wire [31:0] s_rdata_i;
wire [1:0] s_rresp_i;
wire  h_awvalid_i;
wire  h_awready_i;
wire [11:0] h_awaddr_i;
wire  h_wvalid_i;
wire  h_wready_i;
wire [31:0] h_wdata_i;
wire [3:0] h_wstrb_i;
wire  h_bvalid_i;
wire  h_bready_i;
wire  h_arvalid_i;
wire  h_arready_i;
wire [11:0] h_araddr_i;
wire  h_rvalid_i;
wire  h_rready_i;
wire [31:0] h_rdata_i;
wire  h_irq_i;
wire  sys_ready_i;
wire  boot_fault_i;
wire [3:0] boot_state_i;
wire [3:0] boot_err_i;
wire  soft_rst_i;
wire [31:0] fault_src_i;
wire [31:0] die_fault_vec_i;
wire [79:0] die_kst_i;
wire [NCNT*32-1:0] cnt_i;
wire  irq_i;
qkd_host_pin_channel #(.W((12-0+1)),.IN_PIN(1),.OUT_PIN(0)) st_s_awvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_awvalid),.in_d({s_awaddr}),
 .in_r(s_awready),.out_v(s_awvalid_i),.out_d({s_awaddr_i}),.out_r(s_awready_i));
qkd_host_pin_channel #(.W((31-0+1)+(3-0+1)),.IN_PIN(1),.OUT_PIN(0)) st_s_wvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_wvalid),.in_d({s_wdata,s_wstrb}),
 .in_r(s_wready),.out_v(s_wvalid_i),.out_d({s_wdata_i,s_wstrb_i}),.out_r(s_wready_i));
qkd_host_pin_channel #(.W((1-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_s_bvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_bvalid_i),.in_d({s_bresp_i}),
 .in_r(s_bready_i),.out_v(s_bvalid),.out_d({s_bresp}),.out_r(s_bready));
qkd_host_pin_channel #(.W((12-0+1)),.IN_PIN(1),.OUT_PIN(0)) st_s_arvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_arvalid),.in_d({s_araddr}),
 .in_r(s_arready),.out_v(s_arvalid_i),.out_d({s_araddr_i}),.out_r(s_arready_i));
qkd_host_pin_channel #(.W((31-0+1)+(1-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_s_rvalid(
 .ck(clk),.rst_n(rst_n),.in_v(s_rvalid_i),.in_d({s_rdata_i,s_rresp_i}),
 .in_r(s_rready_i),.out_v(s_rvalid),.out_d({s_rdata,s_rresp}),.out_r(s_rready));
qkd_host_pin_channel #(.W((11-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_h_awvalid(
 .ck(clk),.rst_n(rst_n),.in_v(h_awvalid_i),.in_d({h_awaddr_i}),
 .in_r(h_awready_i),.out_v(h_awvalid),.out_d({h_awaddr}),.out_r(h_awready));
qkd_host_pin_channel #(.W((31-0+1)+(3-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_h_wvalid(
 .ck(clk),.rst_n(rst_n),.in_v(h_wvalid_i),.in_d({h_wdata_i,h_wstrb_i}),
 .in_r(h_wready_i),.out_v(h_wvalid),.out_d({h_wdata,h_wstrb}),.out_r(h_wready));
qkd_host_pin_channel #(.W(1),.IN_PIN(1),.OUT_PIN(0)) st_h_bvalid(
 .ck(clk),.rst_n(rst_n),.in_v(h_bvalid),.in_d(1'b0),
 .in_r(h_bready),.out_v(h_bvalid_i),.out_d(),.out_r(h_bready_i));
qkd_host_pin_channel #(.W((11-0+1)),.IN_PIN(0),.OUT_PIN(1)) st_h_arvalid(
 .ck(clk),.rst_n(rst_n),.in_v(h_arvalid_i),.in_d({h_araddr_i}),
 .in_r(h_arready_i),.out_v(h_arvalid),.out_d({h_araddr}),.out_r(h_arready));
qkd_host_pin_channel #(.W((31-0+1)),.IN_PIN(1),.OUT_PIN(0)) st_h_rvalid(
 .ck(clk),.rst_n(rst_n),.in_v(h_rvalid),.in_d({h_rdata}),
 .in_r(h_rready),.out_v(h_rvalid_i),.out_d({h_rdata_i}),.out_r(h_rready_i));
assign clk_i=clk;
assign rst_n_i=rst_n;
reg  pin_h_irq;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_h_irq<=0;else pin_h_irq<=h_irq;
assign h_irq_i=pin_h_irq;
reg  pin_sys_ready;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_sys_ready<=0;else pin_sys_ready<=sys_ready;
assign sys_ready_i=pin_sys_ready;
reg  pin_boot_fault;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_boot_fault<=0;else pin_boot_fault<=boot_fault;
assign boot_fault_i=pin_boot_fault;
reg [3:0] pin_boot_state;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_boot_state<=0;else pin_boot_state<=boot_state;
assign boot_state_i=pin_boot_state;
reg [3:0] pin_boot_err;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_boot_err<=0;else pin_boot_err<=boot_err;
assign boot_err_i=pin_boot_err;
reg  pin_soft_rst;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_soft_rst<=0;else pin_soft_rst<=soft_rst_i;
assign soft_rst=pin_soft_rst;
reg [31:0] pin_fault_src;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_fault_src<=0;else pin_fault_src<=fault_src;
assign fault_src_i=pin_fault_src;
reg [31:0] pin_die_fault_vec;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_die_fault_vec<=0;else pin_die_fault_vec<=die_fault_vec;
assign die_fault_vec_i=pin_die_fault_vec;
reg [79:0] pin_die_kst;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_die_kst<=0;else pin_die_kst<=die_kst;
assign die_kst_i=pin_die_kst;
reg [NCNT*32-1:0] pin_cnt;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_cnt<=0;else pin_cnt<=cnt;
assign cnt_i=pin_cnt;
reg  pin_irq;
always @(posedge clk or negedge rst_n)if(!rst_n)pin_irq<=0;else pin_irq<=irq_i;
assign irq=pin_irq;
qkd_host_sys_csr #(.NCNT(NCNT),.MUT_DIAG(MUT_DIAG)) u_core(
.clk(clk_i),
.rst_n(rst_n_i),
.s_awvalid(s_awvalid_i),
.s_awready(s_awready_i),
.s_awaddr(s_awaddr_i),
.s_wvalid(s_wvalid_i),
.s_wready(s_wready_i),
.s_wdata(s_wdata_i),
.s_wstrb(s_wstrb_i),
.s_bvalid(s_bvalid_i),
.s_bready(s_bready_i),
.s_bresp(s_bresp_i),
.s_arvalid(s_arvalid_i),
.s_arready(s_arready_i),
.s_araddr(s_araddr_i),
.s_rvalid(s_rvalid_i),
.s_rready(s_rready_i),
.s_rdata(s_rdata_i),
.s_rresp(s_rresp_i),
.h_awvalid(h_awvalid_i),
.h_awready(h_awready_i),
.h_awaddr(h_awaddr_i),
.h_wvalid(h_wvalid_i),
.h_wready(h_wready_i),
.h_wdata(h_wdata_i),
.h_wstrb(h_wstrb_i),
.h_bvalid(h_bvalid_i),
.h_bready(h_bready_i),
.h_arvalid(h_arvalid_i),
.h_arready(h_arready_i),
.h_araddr(h_araddr_i),
.h_rvalid(h_rvalid_i),
.h_rready(h_rready_i),
.h_rdata(h_rdata_i),
.h_irq(h_irq_i),
.sys_ready(sys_ready_i),
.boot_fault(boot_fault_i),
.boot_state(boot_state_i),
.boot_err(boot_err_i),
.soft_rst(soft_rst_i),
.fault_src(fault_src_i),
.die_fault_vec(die_fault_vec_i),
.die_kst(die_kst_i),
.cnt(cnt_i),
.irq(irq_i));

endmodule
