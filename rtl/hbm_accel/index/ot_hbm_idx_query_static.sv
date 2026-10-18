`default_nettype none
// Static counterpart of query_owned_native. Same exact quant and retained
// arithmetic; all input/output issue decisions are compiler slots. The compiler
// must leave >=14 edges after the last head block before its emit slot.
module ot_hbm_idx_query_static_core(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire rst_n,frame_start,
 input wire block_v,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire emit_v,input wire [4:0] emit_head,
 output reg ql_v,output reg [7:0] ql_head,
 output wire [511:0] ql_codes,output wire [31:0] ql_sc,output reg [15:0] ql_w,
 output wire fault
);
 // ONE CLOCK ROOT (H-NETLIST/IDXP-OPQ 2026-10-16, successor of hidx_q_pr whose 7 CTS roots each were a different die
 // entry: every crossing paid the 100 ps cross-entry hold reserve, CTS hold repair -56.6 ps / TNS -29,474 ps). Every
 // flop and SRAM here is on clk; clk_quant, clk_quant_delay and clk_bank[3:0] stay die-master ports (ports frozen) and
 // load nothing in this tile. Storage: the 4 x 8-head flop banks (17,408 flops) are 5 SRAM macros 32x128 (codes
 // part 0..3: row = head, 128 code bits; scales: row = head, byte = part), whose registered read is the edge at which
 // the old core register captured codes[emit_head] (same latency, same values under ql_v). Weights/seen stay flops.
 // The quant element line is the register-file form (ot_hdc_delay_rf, cycle-exact).
 reg bad,bfault;reg[6:0]tag[0:12];
 reg[15:0]weights[0:31];reg[3:0]seen[0:31];
 wire qv,qfault;wire[255:0]q;wire signed[9:0]qe;wire[511:0]qy;
 assign fault=bad||bfault;
 ot_hbm_idx_actquant_owned_native #(.XRF(1)) quant(.clk(clk),.clk_delay(clk),.rst_n(rst_n),.v(block_v),.fp4(1'b1),.x(block_data),
 .vo(qv),.q(q),.e(qe),.y(qy),.fault(qfault));
 wire[4:0]qh=tag[12][6:2];wire[1:0]qp=tag[12][1:0];
 wire qok=!(qfault||qe < -127||qe>125||seen[qh][qp]);
 // codes: part p in macro p, word = head
 reg[127:0]qcode;
 always @*for(integer l=0;l<32;l=l+1)qcode[4*l+:4]=q[8*l+:4];
 wire[7:0]qscale=8'(qe+127);
 for(genvar p=0;p<4;p=p+1)begin:gcode
  ot_sram_1r1w_32x128_m1 mem(.clk(clk),.r_ce_in(emit_v),.r_addr_in(emit_head),.rd_out(ql_codes[p*128+:128]),
   .w_ce_in(qv&&qok&&qp==2'(p)),.w_addr_in(qh),.wd_in(qcode),.w_mask_in({128{1'b1}}));
 end
 wire[127:0]sc_rd;
 ot_sram_1r1w_32x128_m1 scmem(.clk(clk),.r_ce_in(emit_v),.r_addr_in(emit_head),.rd_out(sc_rd),
  .w_ce_in(qv&&qok),.w_addr_in(qh),.wd_in({16{qscale}}),
  .w_mask_in({96'd0,(qp==2'd3)?8'hff:8'h00,(qp==2'd2)?8'hff:8'h00,(qp==2'd1)?8'hff:8'h00,(qp==2'd0)?8'hff:8'h00}));
 assign ql_sc=sc_rd[31:0];
 // retained head weights / seen (the old banks' control), one root
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin bfault<=0;for(integer h=0;h<32;h=h+1)seen[h]<=0;end
  else begin
   if(frame_start)for(integer h=0;h<32;h=h+1)seen[h]<=0;
   if(block_v&&block_number!=0&&weights[block_head]!=head_weight)bfault<=1;
   if(qv)begin
    if(!qok)bfault<=1;
    else seen[qh][qp]<=1;
   end
  end
 end
 always @(posedge clk)if(block_v&&block_number==0)weights[block_head]<=head_weight;
 always @(posedge clk)begin
  tag[0]<={block_head,block_number};
  for(integer t=1;t<13;t=t+1)tag[t]<=tag[t-1];
  ql_head<={3'b0,emit_head};ql_w<=weights[emit_head];
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin bad<=0;ql_v<=0;end
  else begin
   ql_v<=emit_v;
   if(emit_v && !(&seen[emit_head]))begin bad<=1;ql_v<=0;end
   if(frame_start && (block_v||emit_v||qv))bad<=1;
  end
 end
endmodule
`default_nettype wire
`default_nettype none
// ---------------------------------------------------------------------------
// PIN-REGISTERED TILE (OWNER RULE 19:50 PT 10-15, H-NETLIST/idxreg 2026-10-16): the die
// master ot_hbm_idx_query_static is this shell. Every data input and every output passes ONE kept
// flop at the pin (clocks pass through; rst_n enters the ot_rst_relay release synchroniser); the arithmetic/control is
// ot_hbm_idx_query_static_core. Latency: +1 edge on every input, +1 edge on every output; the IDX
// calendar compiler (tools/hbm_idx_static_calendar.py, PIN table) schedules them.
// Pin flops have no reset (as physical/common_flow/ot_pin_regs.tcl); the core is reset.
// One data clock (clk) for every pin flop, as the flow's single-clock pin wrapper.
module ot_hbm_idx_query_static(
 input wire clk,clk_quant,clk_quant_delay,input wire [3:0] clk_bank,
 input wire rst_n,frame_start,
 input wire block_v,input wire [4:0] block_head,input wire [1:0] block_number,
 input wire [1023:0] block_data,input wire [15:0] head_weight,
 input wire emit_v,input wire [4:0] emit_head,
 output reg ql_v,output reg [7:0] ql_head,
 output reg [511:0] ql_codes,output reg [31:0] ql_sc,output reg [15:0] ql_w,
 output reg fault
);
 // rst_n: async assert, synchronous release on clk; the core's resets (async and synchronous uses on every
 // same-PLL phase-0 root) come from this one kept register, so no input port feeds another root's data pins.
 // (successor) the release synchroniser is ot_rst_relay: 2 sync + 1 relay flop, release +3 edges; its one output
 // resets only control flops (~170: valids, seen, faults), the data path is reset-free.
 wire rst_core_n;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_core_n));
 (* keep *) reg fs_r,bv_r,ev_r;(* keep *) reg[4:0]bh_r,eh_r;(* keep *) reg[1:0]bn_r;(* keep *) reg[1023:0]bd_r;(* keep *) reg[15:0]hw_r;
 wire c_v,c_fault;wire[7:0]c_head;wire[511:0]c_codes;wire[31:0]c_sc;wire[15:0]c_w;
 always @(posedge clk)begin
  fs_r<=frame_start;bv_r<=block_v;bh_r<=block_head;bn_r<=block_number;bd_r<=block_data;hw_r<=head_weight;ev_r<=emit_v;eh_r<=emit_head;
  ql_v<=c_v;ql_head<=c_head;ql_codes<=c_codes;ql_sc<=c_sc;ql_w<=c_w;fault<=c_fault;
 end
 ot_hbm_idx_query_static_core core(.clk(clk),.clk_quant(clk_quant),.clk_quant_delay(clk_quant_delay),.clk_bank(clk_bank),.rst_n(rst_core_n),
  .frame_start(fs_r),.block_v(bv_r),.block_head(bh_r),.block_number(bn_r),.block_data(bd_r),.head_weight(hw_r),
  .emit_v(ev_r),.emit_head(eh_r),.ql_v(c_v),.ql_head(c_head),.ql_codes(c_codes),.ql_sc(c_sc),.ql_w(c_w),.fault(c_fault));
endmodule
`default_nettype wire
