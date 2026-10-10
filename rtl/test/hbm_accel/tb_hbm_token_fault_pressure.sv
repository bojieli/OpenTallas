`timescale 1ps/1fs
module tb_hbm_token_fault_pressure #(parameter MUT=0);
 reg clk=0;always #417 clk=~clk;
 reg rst_n=0,job_v=0,hr_rdy=0,fault=0,mtp_v=0;
 reg [101:0] mtp_tok=0;wire jr,hr_v,busy,emit_v;wire [73:0] hr_d;
 wire [2:0] status,emit;wire stop;
 ot_hbm_token_loop #(.EXTERNAL_FAULT_EN(1)) dut(.clk(clk),.rst_n(rst_n),.post_en(1'b1),
  .external_fault(MUT==1?1'b0:fault),.job_v(job_v),.job_rdy(jr),.job_id(32'hdeadbeef),
  .job_tok(17'd5),.job_pos(20'd40),.job_ngen(20'd30),.job_eos(17'd0),.job_eos_en(1'b0),
  .job_maxpos(21'd1048576),.job_mtp(1'b1),.host_stop(1'b0),
  .hr_v(hr_v),.hr_rdy(hr_rdy),.hr_d(hr_d),.db_rdy(1'b0),.cpl_v(1'b0),.cpl_token(17'd0),.cpl_status(4'd0),
  .mtp_v(mtp_v),.mtp_n(3'd6),.mtp_tok(mtp_tok),.mtp_emit_v(emit_v),.mtp_emit(emit),.mtp_stop(stop),
  .busy(busy),.last_status(status));
 integer records=0;
 always @(posedge clk) if(hr_v && hr_rdy) begin
  if(records<8) begin
   if(hr_d[16:0]!==records+1 || hr_d[37:17]!==records+41 || hr_d[73] || hr_d[72:70]!=0)$fatal(1,"prior committed record corrupt");
  end else if(records==8) begin
   if(!hr_d[73] || hr_d[72:70]!=4 || hr_d[16:0]!=0 || hr_d[69:38]!=32'hdeadbeef)$fatal(1,"fault record lost/fabricated");
  end else $fatal(1,"duplicate record");
  records=records+1;
 end
 initial begin
  repeat(5) @(negedge clk);rst_n=1;
  @(negedge clk);job_v=1;
  @(negedge clk);job_v=0;
  wait(dut.ls==4);@(negedge clk);mtp_tok={17'd6,17'd5,17'd4,17'd3,17'd2,17'd1};mtp_v=1;
  @(negedge clk);mtp_v=0;
  wait(emit_v);wait(dut.ls==4);@(negedge clk);mtp_tok={17'd12,17'd11,17'd10,17'd9,17'd8,17'd7};mtp_v=1;
  @(negedge clk);mtp_v=0;
  wait(dut.hq_full);@(negedge clk);fault=1;
  repeat(5) @(negedge clk);if(!busy)$fatal(1,"abort lost on full FIFO");hr_rdy=1;
  wait(records==9);repeat(5) @(negedge clk);
  if(busy || status!=4 || !stop)$fatal(1,"fault terminal state");
  $display("PASS full-FIFO MTP fault preserves8 tokens and final zero-token abort");$finish;
 end
 initial begin repeat(5000) @(posedge clk);$fatal(1,"watchdog");end
endmodule
