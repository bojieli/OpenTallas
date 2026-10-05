`timescale 1ns/1ps
`default_nettype none
module tb;
 reg clk=0;always #3 clk=~clk;
 reg rst_n=0,go=0,ready=0,reply_v=0;reg [12:0] cookie=0;reg [127:0] data=0;
 wire [3:0] req;wire [119:0] addr;wire [12:0] request_cookie;wire reply_ready,idfault;
 integer accepted=0,cycle=0,pending=0,delay=0,i;reg [12:0] saved_cookie;reg [127:0] saved_data;
 reg [119:0] last_addr;reg held=0;
 ot_hdc_v41x_idx_pool_adapt_related_vm #(.VM_RESPONSE_WAIT(1),.MP(1),.G(4),.AW(30),.NW(21)) dut(
 .clk(clk),.rst_n(rst_n),.go(go),.cfg_ik_base(30'd0),.i_user_base_sec(28'd0),
 .i_nout(21'd0),.i_k(21'd32),.i_wbase(30'd0),.i_xbase(30'd0),.i_xks(30'd1),
 .i_xjs(30'd32),.i_xcs(30'd256),.i_hg(2'd2),.i_round(1'b0),.i_obase(30'd0),
 .i_mmode(1'b1),.i_oen(1'b0),.i_fuse(1'b1),.i_wts(30'd2048),
 .x_re(req),.x_addr(addr),.x_q(data),.x_req_ready(ready),.x_reply_v(reply_v),
 .x_reply_cookie(cookie),.x_request_cookie(request_cookie),.x_reply_ready(reply_ready),
 .x_identity_fault(idfault),.h_req_rdy(128'd0),.h_rsp_v(128'd0),
 .h_rsp_tag(2048'd0),.h_rsp_beat(512'd0),.h_rsp_data(32768'd0));
 // This is an explicit bounded response fixture for the actual query loader,
 // not a substituted VM/provider or a claimed complete token path.
 always @(negedge clk)begin
  cycle=cycle+1;ready=(cycle%3==0)&&!pending;
  if(pending)begin
    if(delay!=0)delay=delay-1;
    else begin reply_v=1;cookie=saved_cookie;data=saved_data;end
  end
 end
 always @(posedge clk)if(rst_n)begin
  if(held && req!=0 && addr!==last_addr)$fatal(1,"held request changed address");
  held=(req!=0)&&!ready;last_addr=addr;
  if(req!=0&&ready)begin
   if(pending)$fatal(1,"duplicate active read");
   if(req!=4'hf)$fatal(1,"wrong mask");
   pending=1;delay=3+(accepted%4);saved_cookie=request_cookie;
   for(integer j=0;j<4;j=j+1)saved_data[j*32+:32]={16'h3f80+16'(addr[j*30+:30]%16),16'd0};
   accepted=accepted+1;
  end
  if(reply_v&&reply_ready)begin pending=0;#1;reply_v=0;end
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;go=1;@(negedge clk);go=0;
  wait(dut.st==3);#1;
  if(accepted!=264||idfault)$fatal(1,"missing query reads or identity fault");
  for(i=0;i<1056;i=i+1)if(dut.qv[i] !== (16'h3f80+(i%16)))$fatal(1,"query slot/order mismatch %0d",i);
  $display("PASS ACTUAL_INDEX_QUERY_WAIT reads=264 BF16slots=1056 stalled_requests=1 delayed_replies=1 MP=1 IH=32");$finish;
 end
 initial begin repeat(10000)@(posedge clk);$fatal(1,"directed event bound");end
endmodule
`default_nettype wire
