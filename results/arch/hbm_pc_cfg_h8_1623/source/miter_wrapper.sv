module ot_hbm_svc_pc_ctrl_leaf_cfg #(
    parameter integer OREG=1,
    parameter integer KREG=1,
    parameter integer KRREG=1,
    parameter integer RREG=1,
    // WPAY=1 (H-DIE 2026-10-15 22:50, physical default): the 256-bit write payload of the 32-entry same-row queue lives
    // in a real 128x256 SRAM (rows 0..31) instead of 8,192 queue flops + a 32:1 x 256 head mux; the clock root drops
    // from 15,219 to ~7k sinks.  The payload is read continuously at the NEXT head (rp, or rp+1 on a column pop), so
    // the head word is valid one edge after any pop.  A write column issued less than two edges after its own payload
    // write would read the old word: that is checked (sticky fault), never silently stretched.  WPAY=0 = flops.
    parameter integer WPAY=1,
    // QREG=1 (H-HARDEN 2026-10-16, H6 route TT -50.14 / 888 D pins): same edges and decisions, fewer levels from
    // flops -- (a) the same-row queue is written at its FREE slots wp..wp+3 (count+b<32) every edge instead of under
    // `accepted` (K legality/same-row -> i_rdy -> 2,048-flop enable was -41 ps); an accept writes exactly the slots it
    // always wrote, and a free slot is never read before an accept rewrites it (push/head are read only at valid slots;
    // col_data/col_strb are sampled only with col_v); (b) the push entry queue[ep] is a REGISTER (push_q) maintained
    // exactly, so ep -> 32:1 mux -> bank decode -> controller queue (-46.6 ps) starts from flops; (c) the response
    // identity reads both candidate slots from registered addresses and selects late; (d) controller PHYS_WACT 2.
    // QREG=0 is H6 exactly.
    parameter integer QREG=1
)(
    input wire clk,rst_n,
    input wire [4:0]pc_id,
    input wire [7:0]refresh_reload,
    input wire k_v,output wire k_rdy,input wire k_we,
    input wire[29:0]k_addr,input wire[3:0]k_len,input wire[16:0]k_tag,
    input wire[255:0]k_wdata,input wire[31:0]k_wstrb,
    output wire kr_v,input wire kr_rdy,
    output wire[16:0]kr_tag,output wire[3:0]kr_beat,output wire[255:0]kr_data,
    output reg k_wr_done,
    output wire row_v,output wire[2:0]row_op,output wire[4:0]row_bank,output wire[18:0]row_row,
    output wire col_v,col_we,output wire[4:0]col_bank,col_col,
    output wire[255:0]col_data,output wire[31:0]col_strb,
    input wire dram_rvalid,input wire[255:0]dram_rdata,
    output wire pc_fault,owner_fault
);
 wire [1:0] state;
 wire [5:0] count;
 wire  sticky;
 wire [5:0] unposted;
 wire [63:0] push_q;
 wire [63:0] head_q;
 wire [4:0] ep;
 wire [4:0] rp;
 wire [63:0] queue[0:31];
 generate if(QREG==0)begin:g_ref
ot_hbm_svc_pc_ctrl_leaf_cfg_h7ref #(.OREG(OREG),.KREG(KREG),.KRREG(KRREG),.RREG(RREG),.WPAY(WPAY),.QREG(1)) u(.clk(clk),.rst_n(rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload),.k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.k_wr_done(k_wr_done),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.pc_fault(pc_fault),.owner_fault(owner_fault));
 assign state=u.state;
 assign count=u.count;
 assign sticky=u.sticky;
 assign unposted=u.unposted;
 assign push_q=u.push_q;
 assign head_q=u.head_q;
 assign ep=u.ep;
 assign rp=u.rp;
 for(genvar i=0;i<32;i=i+1)begin:vv assign queue[i]=u.queue[i];end
 end else begin:g_cand
 wire [5:0] split;
 assign owner_fault=|split;
ot_hbm_svc_pc_ctrl_leaf_cfg_faults #(.OREG(OREG),.KREG(KREG),.KRREG(KRREG),.RREG(RREG),.WPAY(WPAY),.QREG(1)) u(.clk(clk),.rst_n(rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload),.k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),.k_wr_done(k_wr_done),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.pc_fault(pc_fault),.owner_fault_split(split));
 assign state=u.state;
 assign count=u.count;
 assign sticky=u.sticky;
 assign unposted=u.unposted;
 assign push_q=u.push_q;
 assign head_q=u.head_q;
 assign ep=u.ep;
 assign rp=u.rp;
 for(genvar i=0;i<32;i=i+1)begin:vv assign queue[i]=u.queue[i];end
 end endgenerate
endmodule
