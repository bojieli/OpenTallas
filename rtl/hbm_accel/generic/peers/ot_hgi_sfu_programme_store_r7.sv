`timescale 1ns/1ps
`default_nettype none
// ot_hgi_sfu_programme_store_r7 (H-SU 2026-10-16; successor of _r6, which is unchanged and stays the fallback route).
// Coordinator rule 10-16: a regional SYNCHRONOUS reset tree is mandatory. r6 still had ~3,300 asynchronous-clear loads
// (ot_rst_relay outputs into the calendars: rst_n[1] 738, rst_n[0] 278 DFFASRHQN loads plus the pin/status regs).
// r7 reset tree, every flop synchronous (no asynchronous clear anywhere in this block):
//   rst_n port -> 2-flop synchronizer (rs1, rs2: plain D flops, the port is sampled as data)
//   -> stage A: 3 region relays (programme calendar / IO calendar / pin+status regs)
//   -> stage B: one relay per programme stripe (8), per IO stripe (3) and one for the pin+status regs (12 relays,
//      each drives one stripe's ~85 control flops or the 72 pin/status flops: <= 256 loads per relay).
// All relays are (* keep *) registers (ot_keep_regs.tcl hook) so synthesis cannot merge them and placement puts each
// copy beside its stripe. Data registers carry no reset (as r6; the stripe launch arguments pc/base/limit/loops_left
// also lose theirs: every legal start loads them before running rises).
// Cycle delta vs r6: datapath and invocation identical (io_word / compiler_control D = 4, status +2); reset RELEASE
// takes 4 edges (r6: 3): the host contract becomes "configuration writes start >= 4 edges after rst_n release"
// (tb_hgi_sfu_split_equiv SFU_PSTORE_R7 drives config at exactly release + 4; mutant SFU_PSTORE_R7_EARLY at +3 must fail).
// Reset ASSERTION is also synchronous: it reaches every flop 4 edges after rst_n falls (rst_n must stay low >= 5 edges;
// the clock runs during reset). OT_SFU_PSTORE_MUT_FLIP as before.
module ot_hgi_sfu_programme_store_r7 #(
 parameter integer PAGE_AW=1, AW=10+PAGE_AW
)(
 input wire clk,rst_n,
 input wire cfg_we,
 input wire [2:0] cfg_stripe,
 input wire [AW-1:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire [AW-1:0] start_base,
 input wire [AW:0] start_limit,
 input wire [15:0] start_loops,
 output reg programme_active,programme_done,
 output reg [31:0] programme_ordinal,
 input wire io_cfg_we,
 input wire [1:0] io_cfg_stripe,
 input wire [AW-1:0] io_cfg_addr,
 input wire [255:0] io_cfg_data,
 input wire io_start_v,
 input wire [AW-1:0] io_start_base,
 input wire [AW:0] io_start_limit,
 input wire [15:0] io_start_loops,
 output reg io_active,io_done,
 output reg [31:0] io_ordinal,
 output reg [470:0] io_word,
 output reg [1741:0] compiler_control,
 output reg fault
);
 // ---- input pin registers
 reg r_cfg_we,r_io_cfg_we,r_io_start_v;
 reg [2:0] r_cfg_stripe;
 reg [1:0] r_io_cfg_stripe;
 reg [AW-1:0] r_cfg_addr,r_io_cfg_addr,r_start_base,r_io_start_base;
 reg [255:0] r_cfg_data,r_io_cfg_data;
 reg [AW:0] r_start_limit,r_io_start_limit;
 reg [15:0] r_start_loops,r_io_start_loops;
 // ---- synchronous regional reset tree (see header)
 reg rs1,rs2;
 always @(posedge clk)begin rs1<=rst_n;rs2<=rs1;end
 (* keep = "true", dont_touch = "true" *) reg [2:0] ra;          // stage A: 0 IO calendar, 1 programme calendar, 2 pin/status
 always @(posedge clk)ra<={3{rs2}};
 (* keep = "true", dont_touch = "true" *) reg [7:0] rb_p;        // stage B: programme stripes 0..7
 (* keep = "true", dont_touch = "true" *) reg [2:0] rb_io;       // stage B: IO stripes 0..2
 (* keep = "true", dont_touch = "true" *) reg rb_pin;            // stage B: pin + status registers
 always @(posedge clk)begin rb_io<={3{ra[0]}};rb_p<={8{ra[1]}};rb_pin<=ra[2];end
 always @(posedge clk)
  if(!rb_pin)begin r_cfg_we<=0;r_io_cfg_we<=0;r_io_start_v<=0;end
  else begin r_cfg_we<=cfg_we;r_io_cfg_we<=io_cfg_we;r_io_start_v<=io_start_v;end
 always @(posedge clk)begin
  r_cfg_stripe<=cfg_stripe;r_cfg_addr<=cfg_addr;r_cfg_data<=cfg_data;
  r_start_base<=start_base;r_start_limit<=start_limit;r_start_loops<=start_loops;
  r_io_cfg_stripe<=io_cfg_stripe;r_io_cfg_addr<=io_cfg_addr;r_io_cfg_data<=io_cfg_data;
  r_io_start_base<=io_start_base;r_io_start_limit<=io_start_limit;r_io_start_loops<=io_start_loops;
 end
 // ---- the two unchanged calendars (exactly as in ot_hgi_sfu_scheduled_engine / ot_hgi_sfu_programmed_engine)
 wire [470:0] io;
 wire [1741:0] control;
 wire io_fault,program_fault,w_io_active,w_io_done,w_p_active,w_p_done;
 wire [31:0] w_io_ord,w_p_ord;
 ot_hgi_sfu_io_calendar_sreset #(.PAGE_AW(PAGE_AW)) u_io(
  .clk(clk),.rst_n(rb_io),.cfg_we(r_io_cfg_we),.cfg_stripe(r_io_cfg_stripe),.cfg_addr(r_io_cfg_addr),.cfg_data(r_io_cfg_data),
  .start_v(r_io_start_v),.start_base(r_io_start_base),.start_limit(r_io_start_limit),.start_loops(r_io_start_loops),
  .compiler_control(io),.control_v(),.ordinal(w_io_ord),.active(w_io_active),.done(w_io_done),.fault(io_fault));
 ot_hgi_sfu_calendar_paged_sreset #(.PAGE_AW(PAGE_AW)) u_programme(
  .clk(clk),.rst_n(rb_p),.cfg_we(r_cfg_we),.cfg_stripe(r_cfg_stripe),.cfg_addr(r_cfg_addr),.cfg_data(r_cfg_data),
  .start_v(io[470]),.start_base(r_start_base),.start_limit(r_start_limit),.start_loops(r_start_loops),
  .compiler_control(control),.control_v(),.ordinal(w_p_ord),
  .active(w_p_active),.done(w_p_done),.fault(program_fault));
 // ---- relay stage (mid-tile) + output pin registers: data registers without reset
 reg [470:0] io_p;
 reg [1741:0] ctl_p;
 always @(posedge clk)begin
  io_p<=io;
`ifdef OT_SFU_PSTORE_MUT_FLIP
  ctl_p<=control^1742'd1;          // bench negative control: one control bit corrupted on the crossing
`else
  ctl_p<=control;
`endif
  io_word<=io_p;compiler_control<=ctl_p;
 end
 always @(posedge clk)
  if(!rb_pin)begin
   io_active<=0;io_done<=0;io_ordinal<=0;programme_active<=0;programme_done<=0;programme_ordinal<=0;fault<=0;
  end else begin
   io_active<=w_io_active;io_done<=w_io_done;io_ordinal<=w_io_ord;
   programme_active<=w_p_active;programme_done<=w_p_done;programme_ordinal<=w_p_ord;
   if(io_fault||program_fault)fault<=1;
  end
endmodule
`default_nettype wire
