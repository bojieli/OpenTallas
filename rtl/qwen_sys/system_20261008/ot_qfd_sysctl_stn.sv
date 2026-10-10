`timescale 1ns/1ps
// Generated packet boundary variant; original core remains byte-identical.
module ot_qfd_sysctl_stn #(
    parameter integer BOUNDARY_STATIONS = 0,
    parameter integer PROMPT_VALID_ONLY = 1, // mutant switch; gate unwritten prompt reads
    parameter integer PROMPT_SRAM = 0, // opt-in until exact/physical gates pass
    parameter integer D       = 4,
    parameter integer NW      = 18,
    parameter integer AW      = 24,
    parameter integer NSLOT   = 1,
    parameter integer PLB     = 13,
    parameter integer CTX     = 8192,
    parameter integer KVW     = 1024,
    parameter integer NL      = 6,          // link ends the reset sequencer waits for
    parameter integer T_LINK  = 200000,
    parameter integer T_HBM   = 200000,
    parameter integer WDOG    = 1 << 22
) (
    input  wire               clk,
    input  wire               por_n,
    // host AXI4-Lite slave (13-bit byte address: [12] = 0 host interface, 1 system CSRs)
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
    // AXI4 DMA master to host memory
    output wire               m_arvalid,
    input  wire               m_arready,
    output wire [63:0]        m_araddr,
    output wire [7:0]         m_arlen,
    output wire [2:0]         m_arsize,
    input  wire               m_rvalid,
    output wire               m_rready,
    input  wire [63:0]        m_rdata,
    input  wire [1:0]         m_rresp,
    input  wire               m_rlast,
    output wire               m_awvalid,
    input  wire               m_awready,
    output wire [63:0]        m_awaddr,
    output wire [7:0]         m_awlen,
    output wire [2:0]         m_awsize,
    output wire               m_wvalid,
    input  wire               m_wready,
    output wire [63:0]        m_wdata,
    output wire [7:0]         m_wstrb,
    output wire               m_wlast,
    input  wire               m_bvalid,
    output wire               m_bready,
    input  wire [1:0]         m_bresp,
    output wire               irq,
    // reset / boot
    input  wire [NL-1:0]      link_up,
    input  wire [D-1:0]       boot_done,
    input  wire [D-1:0]       boot_ok,
    output wire               host_rst_n,
    output wire               link_rst_n,
    output wire               hbm_rst_n,
    output wire               boot_go,
    output wire               die_rst_n,
    output wire               sys_ready,
    // package control channel
    output wire               c_start,
    output wire [NW-1:0]      c_token,
    output wire [NW-1:0]      c_pos,
    output wire [AW-1:0]      c_kv_base,
    output wire [1:0]         c_gen,
    input  wire [D-1:0]       c_done,
    input  wire [D*2-1:0]     c_done_gen,
    input  wire [D*NW-1:0]    c_next_token,
    input  wire [D*32-1:0]    c_next_val,
    input  wire [D-1:0]       c_drained,
    input  wire [D-1:0]       c_fault,
    input  wire [D*4-1:0]     c_fault_vec,  // per die: {link, KV / memory, sequencer, stage stepper}
    input  wire               crom_fault,
    output wire [31:0]        fault_src
);

wire [D-1:0] q_boot_done;
wire [D-1:0] q_boot_ok;
wire [D-1:0] q_c_done;
wire [D*2-1:0] q_c_done_gen;
wire [D-1:0] q_c_drained;
wire [D-1:0] q_c_fault;
wire [D*4-1:0] q_c_fault_vec;
wire [D*NW-1:0] q_c_next_token;
wire [D*32-1:0] q_c_next_val;
wire  q_crom_fault;
wire [NL-1:0] q_link_up;
wire [63:0] q_m_araddr;
wire [7:0] q_m_arlen;
wire  q_m_arready;
wire [2:0] q_m_arsize;
wire  q_m_arvalid;
wire [63:0] q_m_awaddr;
wire [7:0] q_m_awlen;
wire  q_m_awready;
wire [2:0] q_m_awsize;
wire  q_m_awvalid;
wire  q_m_bready;
wire [1:0] q_m_bresp;
wire  q_m_bvalid;
wire [63:0] q_m_rdata;
wire  q_m_rlast;
wire  q_m_rready;
wire [1:0] q_m_rresp;
wire  q_m_rvalid;
wire [63:0] q_m_wdata;
wire  q_m_wlast;
wire  q_m_wready;
wire [7:0] q_m_wstrb;
wire  q_m_wvalid;
wire [12:0] q_s_araddr;
wire  q_s_arready;
wire  q_s_arvalid;
wire [12:0] q_s_awaddr;
wire  q_s_awready;
wire  q_s_awvalid;
wire  q_s_bready;
wire [1:0] q_s_bresp;
wire  q_s_bvalid;
wire [31:0] q_s_rdata;
wire  q_s_rready;
wire [1:0] q_s_rresp;
wire  q_s_rvalid;
wire [31:0] q_s_wdata;
wire  q_s_wready;
wire [3:0] q_s_wstrb;
wire  q_s_wvalid;
generate if(BOUNDARY_STATIONS==0)begin:g_bypass
assign q_s_awvalid = s_awvalid;
assign s_awready = q_s_awready;
assign q_s_awaddr = s_awaddr;
assign q_s_wvalid = s_wvalid;
assign s_wready = q_s_wready;
assign q_s_wdata = s_wdata;
assign q_s_wstrb = s_wstrb;
assign s_bvalid = q_s_bvalid;
assign q_s_bready = s_bready;
assign s_bresp = q_s_bresp;
assign q_s_arvalid = s_arvalid;
assign s_arready = q_s_arready;
assign q_s_araddr = s_araddr;
assign s_rvalid = q_s_rvalid;
assign q_s_rready = s_rready;
assign s_rdata = q_s_rdata;
assign s_rresp = q_s_rresp;
assign m_arvalid = q_m_arvalid;
assign q_m_arready = m_arready;
assign m_araddr = q_m_araddr;
assign m_arlen = q_m_arlen;
assign m_arsize = q_m_arsize;
assign q_m_rvalid = m_rvalid;
assign m_rready = q_m_rready;
assign q_m_rdata = m_rdata;
assign q_m_rresp = m_rresp;
assign q_m_rlast = m_rlast;
assign m_awvalid = q_m_awvalid;
assign q_m_awready = m_awready;
assign m_awaddr = q_m_awaddr;
assign m_awlen = q_m_awlen;
assign m_awsize = q_m_awsize;
assign m_wvalid = q_m_wvalid;
assign q_m_wready = m_wready;
assign m_wdata = q_m_wdata;
assign m_wstrb = q_m_wstrb;
assign m_wlast = q_m_wlast;
assign q_m_bvalid = m_bvalid;
assign m_bready = q_m_bready;
assign q_m_bresp = m_bresp;
assign q_link_up = link_up;
assign q_boot_done = boot_done;
assign q_boot_ok = boot_ok;
assign q_c_done = c_done;
assign q_c_done_gen = c_done_gen;
assign q_c_next_token = c_next_token;
assign q_c_next_val = c_next_val;
assign q_c_drained = c_drained;
assign q_c_fault = c_fault;
assign q_c_fault_vec = c_fault_vec;
assign q_crom_fault = crom_fault;
end else begin:g_stations
ot_qfd_packet_stn #(.W(((12)-(0)+1))) u_s_aw (.clk(clk),.rst_n(por_n),.i_valid(s_awvalid),.i_ready(s_awready),.i_data({s_awaddr}),.o_valid(q_s_awvalid),.o_ready(q_s_awready),.o_data({q_s_awaddr}));
ot_qfd_packet_stn #(.W(((31)-(0)+1)+((3)-(0)+1))) u_s_w (.clk(clk),.rst_n(por_n),.i_valid(s_wvalid),.i_ready(s_wready),.i_data({s_wdata,s_wstrb}),.o_valid(q_s_wvalid),.o_ready(q_s_wready),.o_data({q_s_wdata,q_s_wstrb}));
ot_qfd_packet_stn #(.W(((1)-(0)+1))) u_s_b (.clk(clk),.rst_n(por_n),.i_valid(q_s_bvalid),.i_ready(q_s_bready),.i_data({q_s_bresp}),.o_valid(s_bvalid),.o_ready(s_bready),.o_data({s_bresp}));
ot_qfd_packet_stn #(.W(((12)-(0)+1))) u_s_ar (.clk(clk),.rst_n(por_n),.i_valid(s_arvalid),.i_ready(s_arready),.i_data({s_araddr}),.o_valid(q_s_arvalid),.o_ready(q_s_arready),.o_data({q_s_araddr}));
ot_qfd_packet_stn #(.W(((31)-(0)+1)+((1)-(0)+1))) u_s_r (.clk(clk),.rst_n(por_n),.i_valid(q_s_rvalid),.i_ready(q_s_rready),.i_data({q_s_rdata,q_s_rresp}),.o_valid(s_rvalid),.o_ready(s_rready),.o_data({s_rdata,s_rresp}));
ot_qfd_packet_stn #(.W(((63)-(0)+1)+((7)-(0)+1)+((2)-(0)+1))) u_m_ar (.clk(clk),.rst_n(host_rst_n),.i_valid(q_m_arvalid),.i_ready(q_m_arready),.i_data({q_m_araddr,q_m_arlen,q_m_arsize}),.o_valid(m_arvalid),.o_ready(m_arready),.o_data({m_araddr,m_arlen,m_arsize}));
ot_qfd_packet_stn #(.W(((63)-(0)+1)+((1)-(0)+1)+1)) u_m_r (.clk(clk),.rst_n(host_rst_n),.i_valid(m_rvalid),.i_ready(m_rready),.i_data({m_rdata,m_rresp,m_rlast}),.o_valid(q_m_rvalid),.o_ready(q_m_rready),.o_data({q_m_rdata,q_m_rresp,q_m_rlast}));
ot_qfd_packet_stn #(.W(((63)-(0)+1)+((7)-(0)+1)+((2)-(0)+1))) u_m_aw (.clk(clk),.rst_n(host_rst_n),.i_valid(q_m_awvalid),.i_ready(q_m_awready),.i_data({q_m_awaddr,q_m_awlen,q_m_awsize}),.o_valid(m_awvalid),.o_ready(m_awready),.o_data({m_awaddr,m_awlen,m_awsize}));
ot_qfd_packet_stn #(.W(((63)-(0)+1)+((7)-(0)+1)+1)) u_m_w (.clk(clk),.rst_n(host_rst_n),.i_valid(q_m_wvalid),.i_ready(q_m_wready),.i_data({q_m_wdata,q_m_wstrb,q_m_wlast}),.o_valid(m_wvalid),.o_ready(m_wready),.o_data({m_wdata,m_wstrb,m_wlast}));
ot_qfd_packet_stn #(.W(((1)-(0)+1))) u_m_b (.clk(clk),.rst_n(host_rst_n),.i_valid(m_bvalid),.i_ready(m_bready),.i_data({m_bresp}),.o_valid(q_m_bvalid),.o_ready(q_m_bready),.o_data({q_m_bresp}));
reg [D-1:0] r_c_done;
always @(posedge clk or negedge die_rst_n) if(!die_rst_n)r_c_done<=0;else r_c_done<=c_done;
assign q_c_done=r_c_done;
reg [D*2-1:0] r_c_done_gen;
always @(posedge clk or negedge die_rst_n) if(!die_rst_n)r_c_done_gen<=0;else r_c_done_gen<=c_done_gen;
assign q_c_done_gen=r_c_done_gen;
reg [D*NW-1:0] r_c_next_token;
always @(posedge clk or negedge die_rst_n) if(!die_rst_n)r_c_next_token<=0;else r_c_next_token<=c_next_token;
assign q_c_next_token=r_c_next_token;
reg [D*32-1:0] r_c_next_val;
always @(posedge clk or negedge die_rst_n) if(!die_rst_n)r_c_next_val<=0;else r_c_next_val<=c_next_val;
assign q_c_next_val=r_c_next_val;
reg [D-1:0] r_c_drained;
always @(posedge clk or negedge die_rst_n) if(!die_rst_n)r_c_drained<=0;else r_c_drained<=c_drained;
assign q_c_drained=r_c_drained;
reg [D-1:0] r_c_fault;
always @(posedge clk or negedge die_rst_n) if(!die_rst_n)r_c_fault<=0;else r_c_fault<=c_fault;
assign q_c_fault=r_c_fault;
reg [D*4-1:0] r_c_fault_vec;
always @(posedge clk or negedge die_rst_n) if(!die_rst_n)r_c_fault_vec<=0;else r_c_fault_vec<=c_fault_vec;
assign q_c_fault_vec=r_c_fault_vec;
reg  r_crom_fault;
always @(posedge clk or negedge die_rst_n) if(!die_rst_n)r_crom_fault<=0;else r_crom_fault<=crom_fault;
assign q_crom_fault=r_crom_fault;
reg [NL-1:0] r_link_up;
always @(posedge clk or negedge por_n) if(!por_n)r_link_up<=0;else r_link_up<=link_up;
assign q_link_up=r_link_up;
reg [D-1:0] r_boot_done;
always @(posedge clk or negedge por_n) if(!por_n)r_boot_done<=0;else r_boot_done<=boot_done;
assign q_boot_done=r_boot_done;
reg [D-1:0] r_boot_ok;
always @(posedge clk or negedge por_n) if(!por_n)r_boot_ok<=0;else r_boot_ok<=boot_ok;
assign q_boot_ok=r_boot_ok;
end endgenerate
ot_qfd_sysctl #(.PROMPT_VALID_ONLY(PROMPT_VALID_ONLY),.PROMPT_SRAM(PROMPT_SRAM),.D(D),.NW(NW),.AW(AW),.NSLOT(NSLOT),.PLB(PLB),.CTX(CTX),.KVW(KVW),.NL(NL),.T_LINK(T_LINK),.T_HBM(T_HBM),.WDOG(WDOG)) u_core (
.clk(clk),.por_n(por_n),.s_awvalid(q_s_awvalid),.s_awready(q_s_awready),.s_awaddr(q_s_awaddr),.s_wvalid(q_s_wvalid),.s_wready(q_s_wready),.s_wdata(q_s_wdata),.s_wstrb(q_s_wstrb),.s_bvalid(q_s_bvalid),.s_bready(q_s_bready),.s_bresp(q_s_bresp),.s_arvalid(q_s_arvalid),.s_arready(q_s_arready),.s_araddr(q_s_araddr),.s_rvalid(q_s_rvalid),.s_rready(q_s_rready),.s_rdata(q_s_rdata),.s_rresp(q_s_rresp),.m_arvalid(q_m_arvalid),.m_arready(q_m_arready),.m_araddr(q_m_araddr),.m_arlen(q_m_arlen),.m_arsize(q_m_arsize),.m_rvalid(q_m_rvalid),.m_rready(q_m_rready),.m_rdata(q_m_rdata),.m_rresp(q_m_rresp),.m_rlast(q_m_rlast),.m_awvalid(q_m_awvalid),.m_awready(q_m_awready),.m_awaddr(q_m_awaddr),.m_awlen(q_m_awlen),.m_awsize(q_m_awsize),.m_wvalid(q_m_wvalid),.m_wready(q_m_wready),.m_wdata(q_m_wdata),.m_wstrb(q_m_wstrb),.m_wlast(q_m_wlast),.m_bvalid(q_m_bvalid),.m_bready(q_m_bready),.m_bresp(q_m_bresp),.irq(irq),.link_up(q_link_up),.boot_done(q_boot_done),.boot_ok(q_boot_ok),.host_rst_n(host_rst_n),.link_rst_n(link_rst_n),.hbm_rst_n(hbm_rst_n),.boot_go(boot_go),.die_rst_n(die_rst_n),.sys_ready(sys_ready),.c_start(c_start),.c_token(c_token),.c_pos(c_pos),.c_kv_base(c_kv_base),.c_gen(c_gen),.c_done(q_c_done),.c_done_gen(q_c_done_gen),.c_next_token(q_c_next_token),.c_next_val(q_c_next_val),.c_drained(q_c_drained),.c_fault(q_c_fault),.c_fault_vec(q_c_fault_vec),.crom_fault(q_crom_fault),.fault_src(fault_src));
endmodule
// Finite one-entry packet queue. Ready depends only on the registered occupancy.
// No bypass or ready propagation; one edge latency, two-edge minimum accept interval.
module ot_qfd_packet_stn #(parameter integer W=1)(
 input wire clk,rst_n,input wire i_valid,output wire i_ready,input wire [W-1:0] i_data,
 output wire o_valid,input wire o_ready,output wire [W-1:0] o_data);
 reg full;reg [W-1:0] data;
 assign i_ready=!full;assign o_valid=full;assign o_data=data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)full<=0;
  else if(full)begin if(o_ready)full<=0;end
  else if(i_valid)begin full<=1;data<=i_data;end
 end
endmodule
