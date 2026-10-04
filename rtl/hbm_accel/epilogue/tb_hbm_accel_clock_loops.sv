`timescale 1ns/1ps
// Connected issue+bulk-copy differential bench. Behavioural SRAM is TEST ONLY.
module ot_sram_1r1w_1024x256_m2_r2c2 (
 input clk,r_ce_in,input [9:0] r_addr_in, output reg [255:0] rd_out,
 input w_ce_in,input [9:0] w_addr_in,input [255:0] wd_in,w_mask_in,
 input [1:0] rr_en,input [17:0] rr_addr,input [1:0] cr_en,input [15:0] cr_sel);
 reg [255:0] m[0:1023];
 always @(posedge clk) begin
  if(w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in);
  if(r_ce_in) rd_out <= m[r_addr_in];
 end
endmodule

module ot_sram_1r1w_512x256_m1_r2c2 (
 input clk,r_ce_in,input [8:0] r_addr_in, output reg [255:0] rd_out,
 input w_ce_in,input [8:0] w_addr_in,input [255:0] wd_in,w_mask_in,
 input [1:0] rr_en,input [17:0] rr_addr,input [1:0] cr_en,input [15:0] cr_sel);
 reg [255:0] m[0:511];
 // the read output holds for two cycles only (it is captured on a two-cycle path): X once it is stale
 reg [1:0] age;
 always @(posedge clk) begin
  if(w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in);
  if(r_ce_in) begin rd_out <= m[r_addr_in]; age <= 0; end
  else if(age != 2'd3) begin age <= age + 1'b1; if(age == 2'd1) rd_out <= {256{1'bx}}; end
 end
endmodule

module ha3_connected_case #(parameter ENABLE=0, SRAM=0, RMAC=1)(input clk,rst_n,go,
 input [12:0] rows,input [15:0] chunks,input [7:0] groups,input gs,input [1:0] stress,
 output reg finished);
 reg desc_sent;
 wire dr,req_v,sv,wr,iv,ok,first,last,glast,rev,busy,arrive,idle;
 wire [31:0] addr;wire [9:0] tag;wire [1023:0] data;
 wire [9:0] outstanding;wire [12:0] row;wire [2:0] slot;wire [6:0] xa;
 reg rsp_v;reg [9:0] rsp_tag;reg [1023:0] rsp_data;
 integer cyc,issued,received,consumed,events,first_event,max_streak,streak,k,j,chosen;
 reg [1023:0] pending;reg [31:0] saved_addr[0:1023];integer landing[0:1023];
 reg [2:0] retire_pipe;
 wire rdone=retire_pipe[2];
 wire req_ready = !stress || cyc%7 != 3;
 wire x_ready = !stress || cyc%19 < 16;
 ot_hbm_accel_bulk_copy #(.ENABLE(ENABLE),.SRAM_RING(SRAM),.RING_MACRO(RMAC)) copy (
  .clk(clk),.rst_n(rst_n),.d_valid(go && !desc_sent),.d_ready(dr),.d_base(32'd100),
  .d_lines(24'(rows*chunks*groups)),.req_v(req_v),.req_ready(req_ready),
  .req_addr(addr),.req_tag(tag),.rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
  .s_valid(sv),.s_ready(wr),.s_data(data),.outstanding(outstanding),.idle(idle));
 ot_hbm_accel_issue #(.ENABLE(ENABLE)) issue (
  .clk(clk),.rst_n(rst_n),.start(go),.op_rows(rows),.op_c(chunks),.op_g(groups),.op_gs(gs),
  .w_valid(sv),.x_rdy(x_ready),.w_ready(wr),.rdone(rdone),.busy(busy),.iss_v(iv),
  .iss_row_ok(ok),.iss_slot(slot),.iss_row(row),.iss_first(first),.iss_last(last),
  .iss_glast(glast),.iss_rev_end(rev),.xa(xa),.arrive(arrive),.release_in(arrive),.released());
 reg held_req,held_stream;reg [41:0] saved_req;reg [1023:0] saved_stream;
 always @(negedge clk) begin
  rsp_v=0;chosen=-1;
  if(rst_n && (stress!=2 || cyc>=700) && (!stress || cyc%97<84)) begin
   // Deterministic out-of-order completion with line-dependent service and a refresh window.
   for(j=0;j<1024;j=j+1) begin
    k=(j+cyc*13)%1024;
    if(pending[k] && landing[k]<=cyc && chosen<0) chosen=k;
   end
   if(chosen>=0) begin
    rsp_v=1;rsp_tag=chosen;rsp_data={32{saved_addr[chosen]}};
   end
  end
 end
 always @(posedge clk) begin
  if(!rst_n) begin
   finished<=0;desc_sent<=0;cyc=0;pending=0;rsp_v=0;retire_pipe<=0;
   issued=0;received=0;consumed=0;events=0;first_event=-1;streak=0;max_streak=0;
   held_req=0;held_stream=0;
  end else if(!finished) begin
   cyc=cyc+1;
   if(held_req && (!req_v || {addr,tag}!==saved_req)) $fatal(1,"request hold");
   if(held_stream && (!sv || data!==saved_stream)) $fatal(1,"data hold");
   held_req=req_v && !req_ready;saved_req={addr,tag};
   held_stream=sv && !wr;saved_stream=data;
   retire_pipe<={retire_pipe[1:0],iv && ok && last && glast};
   if(go && dr) desc_sent<=1;
   if(rsp_v) begin
    if(!pending[rsp_tag]) $fatal(1,"unowned response");
    pending[rsp_tag]=0;received=received+1;
   end
   if(req_v && req_ready) begin
    if(pending[tag]) $fatal(1,"credit reused");
    pending[tag]=1;saved_addr[tag]=addr;landing[tag]=cyc+3+(stress?tag%11:0);issued=issued+1;
   end
   if(iv) begin
    if(first_event<0) first_event=cyc;
    events=events+1;streak=streak+1;if(streak>max_streak)max_streak=streak;
    $display("TRACE %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d", ENABLE,events,ok,row,slot,first,last,glast,rev,xa);
   end else streak=0;
   if(sv && wr) begin
    if(data!=={32{32'(100+consumed)}}) $fatal(1,"lost/reordered payload at %0d",consumed);
    consumed=consumed+1;
   end
   if(desc_sent && !busy && idle) begin
    if(consumed!=rows*chunks*groups || received!=issued || pending!=0) $fatal(1,"terminal inventory");
    $display("DONE enable=%0d cycles=%0d first=%0d lines=%0d events=%0d max_streak=%0d",ENABLE,cyc,first_event,consumed,events,max_streak);
    finished<=1;
   end
  end
 end
endmodule

module tb_hbm_accel_clock_loops;
 parameter SRAM=0;
 parameter RMAC=1;   // successor ring: 1 = even/odd groups of 512x256 macros, two-cycle capture (the 1.2 GHz SS configuration)
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,go=0;reg [12:0] rows;reg [15:0] chunks;reg [7:0] groups;reg gs;reg [1:0] stress;
 wire f0,f1;
 ha3_connected_case #(.ENABLE(0),.SRAM(SRAM)) b(clk,rst_n,go,rows,chunks,groups,gs,stress,f0);
 ha3_connected_case #(.ENABLE(1),.SRAM(SRAM),.RMAC(RMAC)) n(clk,rst_n,go,rows,chunks,groups,gs,stress,f1);
 integer temp;
 initial begin
  if(!$value$plusargs("ROWS=%d",temp))temp=17;rows=temp;
  if(!$value$plusargs("C=%d",temp))temp=3;chunks=temp;
  if(!$value$plusargs("G=%d",temp))temp=5;groups=temp;
  if(!$value$plusargs("GS=%d",temp))temp=1;gs=temp;
  if(!$value$plusargs("STRESS=%d",temp))temp=1;stress=temp;
  repeat(4)@(negedge clk);rst_n=1;
  repeat(2)@(negedge clk);go=1;
  @(negedge clk);go=0;
  wait(f0 && f1);$display("PASS connected");$finish;
 end
endmodule
