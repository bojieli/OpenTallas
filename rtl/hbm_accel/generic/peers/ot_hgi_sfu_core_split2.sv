`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// ot_hgi_sfu_core_split2 (H-SU 2026-10-16, k7; opt-in successor of ot_hgi_sfu_core_split, which stays unchanged):
// the same SFU core (pin registers, VM bridge, static engine with 16 lanes + 80 operand SRAMs; same latencies) with
//  (1) the lane-direct buses split by die face so every lane's 116 boundary pins sit beside it: lanes 0..7 on the W
//      face (_w = bits of lanes 0..7, i.e. the LOW half of each lane-major bus), lanes 8..15 on the E face (_e = high
//      half). Port mapping: vi_re = {vi_re_e, vi_re_w}, vi_addr = {vi_addr_e, vi_addr_w}, ... (lane j at [j*W +: W]).
//  (2) regional clock roots: clk = bridge + engine (~10.9k flops); clk_pw = W-face pin registers local_rq/local_wq/
//      local_rr/local_w_done (~4.4k); clk_pe = E-face pin registers io/compiler_control/ro_v/ro_x (~2.7k). Same clock
//      from the die (one source, three balanced roots like clk_lane/clk_map), so no cycle changes. k6 had 18,143 sinks
//      on clk (> 15k with no measured tree: textbook REFUSE).
//  (3) rst_n drives only ot_rst_relay (4 regions: bridge, engine, W pins, E pins); release +3 clk edges (the static
//      programme starts long after reset; exactness is per transaction). k6 had 13,745 loads on the rst_n port.
// OT_SFU_CORE_MUT_SKIP_REG (bench negative control) as in ot_hgi_sfu_core_split.
module ot_hgi_sfu_core_split2 #(
 parameter integer LWB=15,
 parameter integer LG_PATH=0,
 // DRAIN_PIPE (SFU-K9 10-18): passed to the VM bridge; 1 = registered drain interface (drain -> local_wq +1 edge,
 // local_w_done expected +1 edge). Default 0 keeps k7/k8 bit-identical.
 parameter integer DRAIN_PIPE=0,
 // HBM-SAFE-K9 (10-19): WPIPE / GCLK passed to the operand store (bank-write landing stage; per-group store roots
 // clk_st[4:0]). Defaults 0 keep k7/k8/k9 bit-identical (clk_st unused).
 parameter integer WPIPE=0, GCLK=0,
 // LH-SU (10-19): WROT passed to the operand store (bank-aligned shared sector rotate). Default 0 = bit-identical.
 parameter integer WROT=0,
 // LH-SU (10-19): lane_map pass-ring one-hot replication passed to the engine. Default 0 = bit-identical.
 parameter integer PASS_OHREP=0,
 // LH-K9R (10-19, safe-design items 1 + 3): RST_TREE=1 replaces the 4-region ot_rst_relay (rr[0] drove 6,245 mapped loads,
 //  rr[1] 1,059) and the direct rst_lg_n / rst_map_n / rst_lane_n fan-out (rst_lg_n__ot_rl1[k] 2,989 each) by registered
 //  two-level distribution trees with KEPT identical copies (rtl/lib/ot_rst_kept_tree.sv), one per reset pin, clocked by
 //  the consumers' regional root; synthesis spreads the loads <= 32 per copy (spec reset_relay_split). Every reset reaches
 //  its consumers 2 edges after the core port (the kit's face landing adds 2: port -> consumers 4 edges; old rst_n path
 //  2 + 3 = 5, old rst_lg/map/lane 2). Default 0 = bit-identical.
 parameter integer RST_TREE=0
)(
 input wire clk,clk_pw,clk_pe,rst_n,
 input wire [4:0] clk_st,
 input wire [3:0] clk_lg,rst_lg_n,
 input wire [15:0] clk_lane,clk_map,rst_lane_n,rst_map_n,
 input wire [470:0] io_word,
 input wire [1741:0] compiler_control,
 output reg [135:0] local_rq,
 input wire [2055:0] local_rr,
 output reg [2247:0] local_wq,
 input wire [7:0] local_w_done,
 output wire [7:0] vi_re_w,vi_re_e,
 output wire [191:0] vi_addr_w,vi_addr_e,
 input wire [255:0] vi_q_w,vi_q_e,
 output reg [7:0] ro_v_w,ro_v_e,
 output wire [7:0] kv_we_w,kv_we_e,
 output reg [255:0] ro_x_w,ro_x_e,
 output wire [255:0] kv_wdata_w,kv_wdata_e,
 output wire [191:0] kv_waddr_w,kv_waddr_e,
 output reg fault
);
 localparam IOW=8+8+128+16+8*LWB+24+96+4+2+2*LWB+32+2+1;
 initial if(LWB!=15 || IOW!=471)$fatal(1,"SFU IO programme ABI requires LWB15");
 wire [3:0] rr;   // 0 bridge, 1 engine, 2 W pins, 3 E pins
 wire [3:0] rst_lg_t;
 wire [15:0] rst_lane_t,rst_map_t;
 generate if(RST_TREE!=0)begin:g_rt
  // sizes from the k9s mapped census (textbook hf_report 32): core 7,3xx loads / 384 copies (~19 each), lg 2,989 / 160
  // (~19), map <= 256 / 8; level A NA = ceil(NB/24). Instance names bracket-free (copy pass addresses every copy bit).
  wire rt_core_n;
  ot_rst_kept_tree #(.NA(16),.NB(384)) u_fl_rst_core(.clk(clk),.rst_n_in(rst_n),.rst_n(rt_core_n));
  assign rr={4{rt_core_n}};
  ot_rst_kept_tree #(.NA(8),.NB(160)) u_fl_rst_lg0(.clk(clk_lg[0]),.rst_n_in(rst_lg_n[0]),.rst_n(rst_lg_t[0]));
`ifdef OT_SFU_CORE_MUT_RSTTREE
  // negative control (bench mutant rsttree): lg path 1's tree output never releases -> its tap never moves
  assign rst_lg_t[1]=1'b0;
`else
  ot_rst_kept_tree #(.NA(8),.NB(160)) u_fl_rst_lg1(.clk(clk_lg[1]),.rst_n_in(rst_lg_n[1]),.rst_n(rst_lg_t[1]));
`endif
  ot_rst_kept_tree #(.NA(8),.NB(160)) u_fl_rst_lg2(.clk(clk_lg[2]),.rst_n_in(rst_lg_n[2]),.rst_n(rst_lg_t[2]));
  ot_rst_kept_tree #(.NA(8),.NB(160)) u_fl_rst_lg3(.clk(clk_lg[3]),.rst_n_in(rst_lg_n[3]),.rst_n(rst_lg_t[3]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map0(.clk(clk_map[0]),.rst_n_in(rst_map_n[0]),.rst_n(rst_map_t[0]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map1(.clk(clk_map[1]),.rst_n_in(rst_map_n[1]),.rst_n(rst_map_t[1]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map2(.clk(clk_map[2]),.rst_n_in(rst_map_n[2]),.rst_n(rst_map_t[2]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map3(.clk(clk_map[3]),.rst_n_in(rst_map_n[3]),.rst_n(rst_map_t[3]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map4(.clk(clk_map[4]),.rst_n_in(rst_map_n[4]),.rst_n(rst_map_t[4]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map5(.clk(clk_map[5]),.rst_n_in(rst_map_n[5]),.rst_n(rst_map_t[5]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map6(.clk(clk_map[6]),.rst_n_in(rst_map_n[6]),.rst_n(rst_map_t[6]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map7(.clk(clk_map[7]),.rst_n_in(rst_map_n[7]),.rst_n(rst_map_t[7]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map8(.clk(clk_map[8]),.rst_n_in(rst_map_n[8]),.rst_n(rst_map_t[8]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map9(.clk(clk_map[9]),.rst_n_in(rst_map_n[9]),.rst_n(rst_map_t[9]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map10(.clk(clk_map[10]),.rst_n_in(rst_map_n[10]),.rst_n(rst_map_t[10]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map11(.clk(clk_map[11]),.rst_n_in(rst_map_n[11]),.rst_n(rst_map_t[11]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map12(.clk(clk_map[12]),.rst_n_in(rst_map_n[12]),.rst_n(rst_map_t[12]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map13(.clk(clk_map[13]),.rst_n_in(rst_map_n[13]),.rst_n(rst_map_t[13]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map14(.clk(clk_map[14]),.rst_n_in(rst_map_n[14]),.rst_n(rst_map_t[14]));
  ot_rst_kept_tree #(.NA(1),.NB(8)) u_fl_rst_map15(.clk(clk_map[15]),.rst_n_in(rst_map_n[15]),.rst_n(rst_map_t[15]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane0(.clk(clk_lane[0]),.rst_n_in(rst_lane_n[0]),.rst_n(rst_lane_t[0]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane1(.clk(clk_lane[1]),.rst_n_in(rst_lane_n[1]),.rst_n(rst_lane_t[1]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane2(.clk(clk_lane[2]),.rst_n_in(rst_lane_n[2]),.rst_n(rst_lane_t[2]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane3(.clk(clk_lane[3]),.rst_n_in(rst_lane_n[3]),.rst_n(rst_lane_t[3]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane4(.clk(clk_lane[4]),.rst_n_in(rst_lane_n[4]),.rst_n(rst_lane_t[4]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane5(.clk(clk_lane[5]),.rst_n_in(rst_lane_n[5]),.rst_n(rst_lane_t[5]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane6(.clk(clk_lane[6]),.rst_n_in(rst_lane_n[6]),.rst_n(rst_lane_t[6]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane7(.clk(clk_lane[7]),.rst_n_in(rst_lane_n[7]),.rst_n(rst_lane_t[7]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane8(.clk(clk_lane[8]),.rst_n_in(rst_lane_n[8]),.rst_n(rst_lane_t[8]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane9(.clk(clk_lane[9]),.rst_n_in(rst_lane_n[9]),.rst_n(rst_lane_t[9]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane10(.clk(clk_lane[10]),.rst_n_in(rst_lane_n[10]),.rst_n(rst_lane_t[10]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane11(.clk(clk_lane[11]),.rst_n_in(rst_lane_n[11]),.rst_n(rst_lane_t[11]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane12(.clk(clk_lane[12]),.rst_n_in(rst_lane_n[12]),.rst_n(rst_lane_t[12]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane13(.clk(clk_lane[13]),.rst_n_in(rst_lane_n[13]),.rst_n(rst_lane_t[13]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane14(.clk(clk_lane[14]),.rst_n_in(rst_lane_n[14]),.rst_n(rst_lane_t[14]));
  ot_rst_kept_tree #(.NA(1),.NB(1)) u_fl_rst_lane15(.clk(clk_lane[15]),.rst_n_in(rst_lane_n[15]),.rst_n(rst_lane_t[15]));
 end else begin:g_rr
  ot_rst_relay #(.REGIONS(4),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
  assign rst_lg_t=rst_lg_n;
  assign rst_lane_t=rst_lane_n;
  assign rst_map_t=rst_map_n;
 end endgenerate
 reg [470:0] io_r;
 reg [1741:0] ctl_r;
`ifdef OT_SFU_SYNC_RST
 // k8 sync-reset standard: boundary pin registers are pure data stages (no reset; the bridge / engine they feed are
 // held in reset by their own regional relays until these registers carry live values)
 always @(posedge clk_pe) begin io_r<=io_word;ctl_r<=compiler_control;end
`else
 always @(posedge clk_pe `OT_SFU_ARST(rr[3]))
  if(!rr[3])begin io_r<=0;ctl_r<=0;end
  else begin io_r<=io_word;ctl_r<=compiler_control;end
`endif
`ifdef OT_SFU_CORE_MUT_SKIP_REG
 wire [470:0] io=io_word;
 wire [1741:0] control=compiler_control;
`else
 wire [470:0] io=io_r;
 wire [1741:0] control=ctl_r;
`endif
 wire [7:0] prefetch_v,prefetch_scalar;
 wire [127:0] prefetch_sector;
 wire [15:0] prefetch_group;
 wire [119:0] prefetch_local_addr;
 wire [23:0] prefetch_word;
 wire [95:0] scalar_addr;
 wire [3:0] scalar_enable;
 wire [1:0] drain_v,drain_round_bf16;
 wire [29:0] drain_addr;
 wire [31:0] drain_vm_sector;
 wire arithmetic_start_unused;
 assign {arithmetic_start_unused,drain_round_bf16,drain_vm_sector,drain_addr,drain_v,scalar_enable,
         scalar_addr,prefetch_word,prefetch_local_addr,prefetch_group,prefetch_sector,prefetch_scalar,prefetch_v}=io;
 wire [7:0] stage_v;
 wire [15:0] stage_group;
 wire [8*LWB-1:0] stage_addr;
 wire [63:0] stage_mask;
 wire [2047:0] stage_data;
 wire [3:0] scalar_load;
 wire [95:0] scalar_load_addr;
 wire [127:0] scalar_data;
 wire [511:0] drain_data;
 wire [1:0] drain_result_v;
 wire bridge_fault,engine_fault;
 wire [135:0] b_rq;
 wire [2247:0] b_wq;
 reg [2055:0] b_rr;
 reg [7:0] b_wd;
 wire [15:0] e_rov;
 wire [511:0] e_rox;
`ifdef OT_SFU_SYNC_RST
 // k8 sync-reset standard: boundary pin registers are pure data stages (no reset; the bridge / engine they feed are
 // held in reset by their own regional relays until these registers carry live values)
 always @(posedge clk_pw) begin local_rq<=b_rq;local_wq<=b_wq;b_rr<=local_rr;b_wd<=local_w_done;end
`else
 always @(posedge clk_pw `OT_SFU_ARST(rr[2]))
  if(!rr[2])begin local_rq<=0;local_wq<=0;b_rr<=0;b_wd<=0;end
  else begin local_rq<=b_rq;local_wq<=b_wq;b_rr<=local_rr;b_wd<=local_w_done;end
`endif
`ifdef OT_SFU_SYNC_RST
 // k8 sync-reset standard: boundary pin registers are pure data stages (no reset; the bridge / engine they feed are
 // held in reset by their own regional relays until these registers carry live values)
 always @(posedge clk_pe) begin {ro_v_e,ro_v_w}<=e_rov;{ro_x_e,ro_x_w}<=e_rox;end
`else
 always @(posedge clk_pe `OT_SFU_ARST(rr[3]))
  if(!rr[3])begin ro_v_w<=0;ro_v_e<=0;ro_x_w<=0;ro_x_e<=0;end
  else begin {ro_v_e,ro_v_w}<=e_rov;{ro_x_e,ro_x_w}<=e_rox;end
`endif
 localparam integer LGB=LG_PATH+1;
 ot_hgi_sfu_vm_static_bridge #(.LWB(LWB),.READ_RETURN(14+2*LGB),.WRITE_RETURN(11+2*LGB),.DRAIN_PIPE(DRAIN_PIPE)) u_vm(
 .clk(clk),.rst_n(rr[0]),.clk_lg(clk_lg),.rst_lg_n(rst_lg_t),.prefetch_v(prefetch_v),.prefetch_sector(prefetch_sector),.prefetch_group(prefetch_group),
 .prefetch_local_addr(prefetch_local_addr),.prefetch_scalar(prefetch_scalar),.prefetch_word(prefetch_word),.scalar_addr(scalar_addr),
 .local_rq(b_rq),.local_rr(b_rr),.local_wq(b_wq),.local_w_done(b_wd),
 .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
 .scalar_load(scalar_load),.scalar_load_addr(scalar_load_addr),.scalar_data(scalar_data),
 .drain_v(drain_v),.drain_round_bf16(drain_round_bf16),.drain_vm_sector(drain_vm_sector),.drain_result_v(drain_result_v),.drain_data(drain_data),.fault(bridge_fault));
 ot_hgi_sfu_static_engine #(.LWB(LWB),.WPIPE(WPIPE),.GCLK(GCLK),.WROT(WROT),.PASS_OHREP(PASS_OHREP)) u_engine(
  .clk(clk),.rst_n(rr[1]),.clk_grp(clk_st),.clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_t),.rst_map_n(rst_map_t),
  .compiler_control(control),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_addr(scalar_load_addr),.scalar_data(scalar_data),
  .stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(stage_mask),.stage_data(stage_data),
  .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_result_v),
  .vi_re({vi_re_e,vi_re_w}),.vi_addr({vi_addr_e,vi_addr_w}),.vi_q({vi_q_e,vi_q_w}),.ro_v(e_rov),.ro_x(e_rox),
  .kv_we({kv_we_e,kv_we_w}),.kv_waddr({kv_waddr_e,kv_waddr_w}),.kv_wdata({kv_wdata_e,kv_wdata_w}),.fault(engine_fault));
 always @(posedge clk_pe `OT_SFU_ARST(rr[3]))
  if(!rr[3])fault<=0;else if(bridge_fault||engine_fault)fault<=1;
endmodule
`default_nettype wire
