`timescale 1ns/1ps
// Controlled transport gate: actual fetch + timing-faithful HBM model + replay.
// Not released-checkpoint/numerical evidence. No CPU inference or timer cap.
module tb_ds_hbm_union_fetch;
 reg clk=0,rst_n=0;always #0.5 clk=~clk;
 reg uv=0;wire ur;wire req,ready;wire [23:0] addr;wire [4:0] len;wire [15:0] tag;
 wire [1:0] rv,rr;wire [31:0] rt;wire [9:0] rb;wire [511:0] rd;
 wire [1:0] ov;reg [1:0] accept=1;wire [2047:0] od;
 wire [5:0] col;wire [31:0] line;wire [8:0] expert;wire done,last,fault;
 integer reads=0,c0=0,c1=0;
 ot_ds_hbm_union_fetch #(.ENABLE(1),.AW(24)) dut(
 .clk(clk),.rst_n(rst_n),.cfg_base(22'd0),.cfg_exp_lines(16'd4),
 .cfg_off({16'd1,16'd0}),.cfg_lines({16'd1,16'd1}),
 .u_v(uv),.u_ready(ur),.u_id(9'd2),.u_mask(8'b00100101),.u_last(1'b1),
 .req_v(req),.req_rdy(ready),.req_addr(addr),.req_len(len),.req_tag(tag),
 .rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd),
 .out_valid(ov),.out_ready(accept),.out_data(od),.out_col(col),.out_line(line),.out_expert(expert),
 .expert_done(done),.pass_done(last),.fault(fault));
 ot_hdc_hbm_model #(.NPC(2),.AW(24),.MEM_WORDS(128),.BEATW(5)) hbm(
 .clk(clk),.rst_n(rst_n),.req_v(req),.req_rdy(ready),.req_we(1'b0),
 .req_addr(addr),.req_len(len),.req_tag(tag),.req_wdata(256'b0),
 .rsp_v(rv),.rsp_rdy(rr),.rsp_tag(rt),.rsp_beat(rb),.rsp_data(rd),.pc_room());
 function automatic integer expected_col(input integer n);
  case(n) 0:expected_col=0;1:expected_col=2;2:expected_col=5;default:expected_col=-1;endcase
 endfunction
 always @(posedge clk) if(rst_n) begin
  if(req && ready) begin
   reads<=reads+1;
   if(len!=4 || (addr!=32 && addr!=36)) $fatal(1,"source descriptor sector extent");
  end
  if(done && (c0!=3 || c1!=3)) $fatal(1,"premature expert retirement");
  for(integer s=0;s<2;s=s+1) if(ov[s] && accept[s]) begin
   if(expert!=2 || line[s*16+:16]!=0 || col[s*3+:3]!=expected_col(s==0?c0:c1))
    $fatal(1,"expert/column/line identity or order");
   for(integer q=0;q<4;q=q+1)
    for(integer w=0;w<8;w=w+1)
     if(od[s*1024+q*256+w*32+:32] != 32'hc0000000+32+s*4+q)
      $fatal(1,"actual source payload mismatch");
   if(s==0)c0<=c0+1;else c1<=c1+1;
  end
 end
 initial begin
  #2;
  for(integer a=32;a<40;a=a+1) hbm.mem[a]={8{32'hc0000000+32'(a)}};
  rst_n=1;
  wait(ur);@(negedge clk);uv=1;@(negedge clk);uv=0;
  wait(c0==3);
  if(done || last || c1!=0) $fatal(1,"blocked column authority discarded");
  @(negedge clk);accept=3;
  wait(last);
  if(reads!=2 || fault) $fatal(1,"expert fetched repeatedly or faulted");
  $display("PASS_ACTUAL_UNION_FETCH_REPLAY reads=%0d consumers=%0d scope=controlled_transport_only",reads,c0+c1);
  $finish;
 end
endmodule
