`default_nettype none
module ot_hbm_svc_core_native #(
  parameter integer NATIVE=0, NSM = 8, NPC = 32,
  parameter [NSM*5-1:0] SM_PC0 = 0,       // first of SM i's four K pseudo-channels
  parameter [NPC*4-1:0] RSP_ST = 0,       // wire stages, PC p response ingress -> its SM's assembler
  parameter [NSM*4-1:0] REQ_ST = 0,       // wire stages, SM i request port -> its PCs
  parameter [NSM*4-1:0] W_ST = 0,         // wire stages, W lane l -> SM l
  parameter [NSM-1:0] FWD = 0,            // SM i link forwarded (row 1): request with fclk, no ready; line with fclk
  parameter integer KV_PC = 0, IK_PC = 0,
  parameter integer KV_ST = 0, IK_ST = 0, // wire stages KV_PC / IK_PC -> kv / ik ports
  parameter integer E_ST = 0,             // wire stages e port -> PHY request side
  parameter integer XST = 2,              // MARGIN: extra wire stages on every chain (route at <= 770 ps)
  // hbm-system 2026-10-08 (T3 gap 3): WRITE path.  WB = 1 adds the forwarded sector-write link of the hub
  // write-back unit (rtl/hbm_accel/service/ot_hbm_kvwb_hub.sv) and drives k_we / k_wdata / k_wstrb; WB = 0 (default)
  // is the read-only service, bit for bit.
  parameter integer WB = 0,
  parameter integer WB_SOURCE_ACK = 0, // opt-in source-owned per-PC DRAM completions
  parameter integer WQ_ST = 0,            // wire stages, wq port -> the PC request registers (and back)
  // hbm-system 2026-10-08 (coordinator: one fixed KV_PC per stack cannot reach the >= 90 % KV bandwidth rule):
  // KVS = 1 turns e kind 1 into a PER-PC KV STREAM.  Descriptor ed: [1:0] = 1, [16:2] row0 (15 b), [28:17] nsec
  // (sectors per PC; the last read of a PC is 4 sectors, pad sectors are dropped), [60:29] PC mask, [70:61] tag.  Every PC in the mask streams its sectors
  // j = 0 .. nsec-1 of the region (the dskv_wb / stream-PC j order: bank {j[9:7], j[1:0]}, column j[6:2],
  // row row0 + (j >> 10), K address by ot_hbm_kport_map), up to KNO 4-sector reads outstanding per PC, and its
  // beats leave on its OWN lane kvs[p] = {data256, j12, v} (one sector a clock a PC: the PHY rate), so a stack
  // delivers up to 32 sectors a clock.  kvs_done pulses when every PC finished.  KVS = 0: the single-PC kind 1.
  parameter integer KVS = 0,
  parameter integer KNO = 15              // 4-sector reads outstanding per PC (60 of the controller's 64 queued beats)
)(
  input  wire ck, input wire rst,          // rst: active-low die reset (por_hbm)
  input  wire [NSM*42-1:0] q_d, input wire [NSM-1:0] q_v, input wire [NSM-1:0] q_fclk, output wire [NSM-1:0] q_rdy,
  output wire [NSM*1099-1:0] line, output wire fclk,
  input  wire [127:0] e_d, input wire e_fclk,
  output wire [1037:0] kv, output wire [1023:0] ik,
  output wire phy_clk, output wire phy_rst_n,
  output wire [NPC-1:0] k_v, input wire [NPC-1:0] k_rdy, output wire [NPC*30-1:0] k_addr, output wire [NPC*4-1:0] k_len,
  output wire [NPC*17-1:0] k_tag, output wire [NPC-1:0] k_we, output wire [NPC*256-1:0] k_wdata,
  output wire [NPC*32-1:0] k_wstrb,
  input  wire [NPC-1:0] kr_v, output wire [NPC-1:0] kr_rdy, input wire [NPC*17-1:0] kr_tag, input wire [NPC*4-1:0] kr_beat,
  input  wire [NPC*256-1:0] kr_data,
  output wire w_v, input wire w_rdy, output wire [23:0] w_addr, output wire [5:0] w_len, output wire [9:0] w_tag,
  input  wire [7:0] w_room,
  input  wire [7:0] wr_v, output wire [7:0] wr_rdy, input wire [79:0] wr_tag, input wire [39:0] wr_beat,
  input  wire [2047:0] wr_data,
  // WB = 1: sector writes {data256, addr30, pc5, v} forwarded with wq_fclk; returns {ack_gray8, pop_gray8} on ck
  input  wire [291:0] wq_d, input wire wq_fclk, output wire [15:0] wq_g, input wire [NPC-1:0] k_wr_done,
  input wire [1:0] wq_source, output wire [31:0] wq_source_g, output wire wq_source_fault, output wire [NPC-1:0] wq_source_busy, output wire wq_pending,
  // KVS = 1: per-PC KV stream lanes (launched on ck, forwarded with fclk) and the stream-complete pulse
  output wire [NPC*269-1:0] kvs, output wire kvs_done,
 input wire outer_write_pending,
 input wire native_v,output wire native_rdy,input wire[4:0]native_pc,input wire[29:0]native_addr,input wire[15:0]native_tag,
 output wire native_rsp_v,input wire native_rsp_rdy,output wire[4:0]native_rsp_pc,output wire[15:0]native_rsp_tag,
 output wire[3:0]native_rsp_beat,output wire[255:0]native_rsp_data,output wire native_fault
);
 wire [NPC-1:0] n_k_v;
 wire [NPC-1:0] n_k_rdy;
 wire [NPC-1:0] n_k_we;
 wire [NPC*30-1:0] n_k_addr;
 wire [NPC*4-1:0] n_k_len;
 wire [NPC*17-1:0] n_k_tag;
 wire [NPC*256-1:0] n_k_wdata;
 wire [NPC*32-1:0] n_k_wstrb;
 wire [NPC-1:0] n_kr_v;
 wire [NPC-1:0] n_kr_rdy;
 wire [NPC*17-1:0] n_kr_tag;
 wire [NPC*4-1:0] n_kr_beat;
 wire [NPC*256-1:0] n_kr_data;
 wire n_pending;wire[NPC-1:0]n_busy,native_busy;
 assign wq_pending=n_pending;assign wq_source_busy=n_busy;
 ot_hbm_svc_core #(.NSM(NSM),.SM_PC0(SM_PC0),.RSP_ST(RSP_ST),.REQ_ST(REQ_ST),.W_ST(W_ST),.FWD(FWD),.KV_PC(KV_PC),.KV_ST(KV_ST),.E_ST(E_ST),.XST(XST),.WB(WB),.WB_SOURCE_ACK(WB_SOURCE_ACK),.WQ_ST(WQ_ST),.KVS(KVS),.KNO(KNO)) u_core (
 .ck(ck),
 .rst(rst),
 .q_d(q_d),
 .q_v(q_v),
 .q_fclk(q_fclk),
 .q_rdy(q_rdy),
 .line(line),
 .fclk(fclk),
 .e_d(e_d),
 .e_fclk(e_fclk),
 .kv(kv),
 .ik(ik),
 .phy_clk(phy_clk),
 .phy_rst_n(phy_rst_n),
 .k_v(n_k_v),
 .k_rdy(n_k_rdy),
 .k_addr(n_k_addr),
 .k_len(n_k_len),
 .k_tag(n_k_tag),
 .k_we(n_k_we),
 .k_wdata(n_k_wdata),
 .k_wstrb(n_k_wstrb),
 .kr_v(n_kr_v),
 .kr_rdy(n_kr_rdy),
 .kr_tag(n_kr_tag),
 .kr_beat(n_kr_beat),
 .kr_data(n_kr_data),
 .w_v(w_v),
 .w_rdy(w_rdy),
 .w_addr(w_addr),
 .w_len(w_len),
 .w_tag(w_tag),
 .w_room(w_room),
 .wr_v(wr_v),
 .wr_rdy(wr_rdy),
 .wr_tag(wr_tag),
 .wr_beat(wr_beat),
 .wr_data(wr_data),
 .wq_d(wq_d),
 .wq_fclk(wq_fclk),
 .wq_g(wq_g),
 .k_wr_done(k_wr_done),
 .wq_source(wq_source),
 .wq_source_g(wq_source_g),
 .wq_source_fault(wq_source_fault),
 .wq_source_busy(n_busy),
 .wq_pending(n_pending),
 .kvs(kvs),
 .kvs_done(kvs_done));
 ot_hbm_loader_service_boundary #(.ENABLE(NATIVE),.NPC(NPC)) u_native(
 .clk(ck),.rst_n(phy_rst_n),.normal_pending_write({NPC{outer_write_pending||n_pending}}|n_busy),
 .native_v(native_v),.native_rdy(native_rdy),.native_pc(native_pc),.native_addr(native_addr),.native_tag(native_tag),
 .native_rsp_v(native_rsp_v),.native_rsp_rdy(native_rsp_rdy),.native_rsp_pc(native_rsp_pc),.native_rsp_tag(native_rsp_tag),
 .native_rsp_beat(native_rsp_beat),.native_rsp_data(native_rsp_data),.native_busy(native_busy),.fault(native_fault),
 .normal_v(n_k_v),.k_v(k_v),
 .normal_rdy(n_k_rdy),.k_rdy(k_rdy),
 .normal_we(n_k_we),.k_we(k_we),
 .normal_addr(n_k_addr),.k_addr(k_addr),
 .normal_len(n_k_len),.k_len(k_len),
 .normal_tag(n_k_tag),.k_tag(k_tag),
 .normal_wdata(n_k_wdata),.k_wdata(k_wdata),
 .normal_wstrb(n_k_wstrb),.k_wstrb(k_wstrb),
 .normal_rsp_v(n_kr_v),.kr_v(kr_v),
 .normal_rsp_rdy(n_kr_rdy),.kr_rdy(kr_rdy),
 .normal_rsp_tag(n_kr_tag),.kr_tag(kr_tag),
 .normal_rsp_beat(n_kr_beat),.kr_beat(kr_beat),
 .normal_rsp_data(n_kr_data),.kr_data(kr_data),
 .k_wr_done(k_wr_done));
endmodule
`default_nettype wire
