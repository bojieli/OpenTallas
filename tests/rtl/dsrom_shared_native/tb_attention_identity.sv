`timescale 1ns/1ps
module tb;
 reg clk=0;always #3 clk=~clk;
 reg rst_n=0,go=0,x_req_ready=0,x_reply_v=0;
 reg [31:0] x_reply_cookie=0;reg [127:0] x_q=0;
 wire [31:0] x_request_cookie;wire x_reply_ready,ready,idle,fault;
 wire [3:0] x_re;wire [119:0] x_addr;integer captures=0;
 ot_hdc_v41x_att_adapt_native_vm #(.VM_RESPONSE_WAIT(1),.OUTPUT_CREDIT(1),.AW(30),.NW(21),.MP(1),.G(4),.D(512),.TROWS(640),.PACKED_KV(1),.NHMAX(16)) dut(
 .clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.idle(idle),.fault(fault),
 .i_nout(21'd1),.i_tiles(21'd1),.i_k(21'd512),.i_wbase(30'd0),.i_ts(30'd1),.i_ks(30'd1),.i_js(30'd0),
 .i_xbase(30'd17),.i_xks(30'd1),.i_xjs(30'd512),.i_xcs(30'd4096),.i_hg(2'd1),.i_ogs(30'd1),
 .i_round(1'b1),.i_obase(30'd0),.i_ots(30'd1),.i_ojs(30'd1),.i_mmode(1'b1),.i_oen(1'b1),.i_m(3'd1),
 .kv_q('0),.packed_kv_v(1'b0),.packed_kv_m('0),.packed_kv_w('0),.packed_kv_fault(1'b0),
 .x_req_ready(x_req_ready),.x_reply_v(x_reply_v),.x_reply_cookie(x_reply_cookie),.x_q(x_q),
 .x_request_cookie(x_request_cookie),.x_reply_ready(x_reply_ready),.x_re(x_re),.x_addr(x_addr),
 .write_accept(1'b0),.write_visible(1'b0),.write_pending(1'b0),.att_from('0));
 always @(posedge clk)if(rst_n && x_reply_v && x_reply_ready)captures<=captures+1;
 initial begin
  repeat(4)@(negedge clk);rst_n=1;go=1;@(negedge clk);go=0;
  wait(|x_re);@(negedge clk);
  if(x_request_cookie!=0 || x_addr[0+:30]!=17)$fatal(1,"actual first read shape");
  repeat(5)begin @(negedge clk);if(x_re!=15 || x_request_cookie!=0 || x_addr[0+:30]!=17)$fatal(1,"held request changed");end
  x_req_ready=1;@(negedge clk);x_req_ready=0;
  x_reply_cookie=0;x_q={4{32'h3f800000}};x_reply_v=1;@(negedge clk);x_reply_v=0;
  wait(|x_re);@(negedge clk);
  if(x_request_cookie!=4)$fatal(1,"next actual query group");
  x_req_ready=1;@(negedge clk);x_req_ready=0;
  x_reply_cookie=32'd5;x_reply_v=1;
  repeat(4)@(negedge clk);x_reply_v=0;
  if(captures!=1 || x_reply_ready || !dut.read_pending || !dut.identity_fault || !fault || ready)$fatal(1,"wrong reply accepted/owner debt lost");
  for(integer l=0;l<4;l=l+1)if(dut.xbuf[l]!==16'h3f80)$fatal(1,"actual RNE capture changed");
  $display("PASS ATTENTION_NATIVE_IDENTITY D512_T640=1 held_request=1 matching_capture_RNE=1 wrong_cookie_no_accept=1 read_debt_held=1");$finish;
 end
 initial begin repeat(300)@(negedge clk);$fatal(1,"directed event bound");end
endmodule
