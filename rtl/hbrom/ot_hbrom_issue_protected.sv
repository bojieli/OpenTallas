`timescale 1ns/1ps
// Default off. Fixed full NC1 state inventory; fail-stop DMR, no arithmetic copy.
module ot_hbrom_issue_protected #(
 parameter integer PROTECT=0, ENABLE=1, IL=8, RMAX=4096, XDEPTH=128
)(input wire clk,rst_n,start,input wire [$clog2(RMAX):0] op_rows,
 input wire [15:0] op_c,input wire [7:0] op_g,input wire op_gs,w_valid,x_rdy,
 output wire w_ready,input wire rdone,output wire busy,iss_v,iss_row_ok,
 output wire [$clog2(IL)-1:0] iss_slot,output wire [$clog2(RMAX):0] iss_row,
 output wire iss_first,iss_last,iss_glast,iss_rev_end,
 output wire [$clog2(XDEPTH)-1:0] xa,output wire arrive,
 input wire release_in,output wire released,output wire fault);
 generate if(!PROTECT) begin:g_original
  ot_hbm_accel_issue #(.ENABLE(ENABLE),.IL(IL),.RMAX(RMAX),.XDEPTH(XDEPTH)) u_original(.*);
  assign fault=0;
 end else begin:g_protected
  if(IL!=8 || RMAX!=4096 || XDEPTH!=128 || ENABLE!=1) begin:g_bad
   initial $fatal(1,"protected issuer requires priced NC1 shape");
  end
  wire [681:0] a_state,b_state;
  wire [34:0] a_cmd,b_cmd;
  wire a_ready,a_busy,a_v,a_ok,a_first,a_last,a_glast,a_rev,a_arrive,a_released;
  wire b_ready,b_busy,b_v,b_ok,b_first,b_last,b_glast,b_rev,b_arrive,b_released;
  wire [2:0] a_slot,b_slot;wire [12:0] a_row,b_row;wire [6:0] a_xa,b_xa;
  (* keep *) reg poison_a,poison_b;
  wire mismatch=(a_state!=b_state)||(a_cmd!=b_cmd);
  assign fault=poison_a|poison_b|(poison_a!=poison_b)|mismatch;
  always @(posedge clk or negedge rst_n) if(!rst_n) poison_a<=0; else poison_a<=poison_a|mismatch|poison_b;
  always @(posedge clk or negedge rst_n) if(!rst_n) poison_b<=0; else poison_b<=poison_b|mismatch|poison_a;
  assign a_cmd={a_ready,a_busy,a_v,a_ok,a_slot,a_row,a_first,a_last,a_glast,a_rev,a_xa,a_arrive,a_released};
  assign b_cmd={b_ready,b_busy,b_v,b_ok,b_slot,b_row,b_first,b_last,b_glast,b_rev,b_xa,b_arrive,b_released};
  (* keep_hierarchy *) ot_hbrom_issue_replica #(.ENABLE(1),.IL(8),.RMAX(4096),.XDEPTH(128)) u_a(
   .clk(clk),.rst_n(rst_n),.start(start),.op_rows(op_rows),.op_c(op_c),.op_g(op_g),.op_gs(op_gs),
   .w_valid(w_valid),.x_rdy(x_rdy),.w_ready(a_ready),.rdone(rdone),.busy(a_busy),.iss_v(a_v),.iss_row_ok(a_ok),
   .iss_slot(a_slot),.iss_row(a_row),.iss_first(a_first),.iss_last(a_last),.iss_glast(a_glast),.iss_rev_end(a_rev),
   .xa(a_xa),.arrive(a_arrive),.release_in(release_in),.released(a_released),.control_state(a_state));
  (* keep_hierarchy *) ot_hbrom_issue_replica #(.ENABLE(1),.IL(8),.RMAX(4096),.XDEPTH(128)) u_b(
   .clk(clk),.rst_n(rst_n),.start(start),.op_rows(op_rows),.op_c(op_c),.op_g(op_g),.op_gs(op_gs),
   .w_valid(w_valid),.x_rdy(x_rdy),.w_ready(b_ready),.rdone(rdone),.busy(b_busy),.iss_v(b_v),.iss_row_ok(b_ok),
   .iss_slot(b_slot),.iss_row(b_row),.iss_first(b_first),.iss_last(b_last),.iss_glast(b_glast),.iss_rev_end(b_rev),
   .xa(b_xa),.arrive(b_arrive),.release_in(release_in),.released(b_released),.control_state(b_state));
  assign w_ready=a_ready&&!fault;assign busy=a_busy||fault;assign iss_v=a_v&&!fault;
  assign iss_row_ok=a_ok&&!fault;assign iss_slot=a_slot;assign iss_row=a_row;
  assign iss_first=a_first&&!fault;assign iss_last=a_last&&!fault;assign iss_glast=a_glast&&!fault;
  assign iss_rev_end=a_rev&&!fault;assign xa=a_xa;
  // Arrival is meaningful only with !fault; top must never commit a poisoned arrival.
  assign arrive=a_arrive;assign released=a_released&&!fault;
 end endgenerate
endmodule
