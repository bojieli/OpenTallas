// Finite static programme: entry={deadline32,launch32,job217}. No traffic until
// sequential preload and a source-calendar-bound configuration commit succeed.
module ot_hnx_fused_job217_provider #(parameter integer DELIVERED_RESET=0) (
 input wire clk,rst_n,
 input wire load_v,input wire [7:0] load_addr,input wire [280:0] load_entry,
 input wire cfg_commit,cfg_calendar_bound,input wire [8:0] cfg_count,
 input wire [7:0] cfg_wsc,input wire [5:0] cfg_pk5,input wire cfg_pb5,
 input wire start,
 output reg job_v,output reg [216:0] job,
 output reg [7:0] wsc,output reg [5:0] pk5,output reg pb5,
 input wire root_done,root_fault,root_busy,
 output reg done,fault,output wire busy,output reg armed
);
 wire local_rst_n;
 generate if(DELIVERED_RESET!=0)begin:g_delivered
 (* keep="true",dont_touch="true" *) reg [2:0] reset_pipe;
 always @(posedge clk)reset_pipe<={reset_pipe[1:0],rst_n};
 assign local_rst_n=reset_pipe[2];
 end else begin:g_legacy
 assign local_rst_n=rst_n;
 end endgenerate
 localparam IDLE=0,FETCH0=1,FETCH1=2,WAIT_EDGE=3,RUN=4;
 reg [2:0] state;reg [8:0] loaded,count;reg load_error;
 reg [7:0] ptr;reg [31:0] cycle,launch,deadline;
 reg [216:0] queued_job;reg seen_done,seen_fault;
 reg rd_done,rd_fault,rd_busy;
 wire [255:0] qlo,qhi;wire read_en=(state==FETCH0);
 wire write_en=load_v&&(state==IDLE);
 ot_sram_1r1w_256x256_m2_r2c2 lo(.clk(clk),.r_ce_in(read_en),.r_addr_in(ptr),.rd_out(qlo),
 .w_ce_in(write_en),.w_addr_in(load_addr),.wd_in(load_entry[255:0]),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(16'b0),.cr_en(2'b0),.cr_sel(16'b0));
 ot_sram_1r1w_256x256_m2_r2c2 hi(.clk(clk),.r_ce_in(read_en),.r_addr_in(ptr),.rd_out(qhi),
 .w_ce_in(write_en),.w_addr_in(load_addr),.wd_in({231'b0,load_entry[280:256]}),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(16'b0),.cr_en(2'b0),.cr_sel(16'b0));
 assign busy=(state!=IDLE);
 always @(posedge clk or negedge local_rst_n)begin
 if(!local_rst_n)begin state<=IDLE;loaded<=0;count<=0;load_error<=0;ptr<=0;cycle<=0;launch<=0;deadline<=0;queued_job<=0;seen_done<=0;seen_fault<=0;rd_done<=0;rd_fault<=0;rd_busy<=0;job_v<=0;job<=0;wsc<=0;pk5<=0;pb5<=0;done<=0;fault<=0;armed<=0;end
 else begin
 job_v<=0;done<=0;rd_done<=root_done;rd_fault<=root_fault;rd_busy<=root_busy;
 if(state!=IDLE)cycle<=cycle+1;
 if(load_v)begin
  armed<=0;
  if(state!=IDLE)begin fault<=1;state<=IDLE;end
  else if(load_addr==0)begin loaded<=1;load_error<=0;end
  else if({1'b0,load_addr}==loaded&&loaded<256)loaded<=loaded+1;
  else load_error<=1;
 end
 if(cfg_commit)begin
  armed<=0;
  if(state!=IDLE||load_v||start||!cfg_calendar_bound||load_error||cfg_count==0||cfg_count>256||loaded!=cfg_count||cfg_pk5>32)begin fault<=1;state<=IDLE;end
  else begin armed<=1;fault<=0;count<=cfg_count;wsc<=cfg_wsc;pk5<=cfg_pk5;pb5<=cfg_pb5;end
 end
 if(!load_v&&!cfg_commit)case(state)
 IDLE:if(start)begin if(!armed||cfg_commit||load_v)fault<=1;else begin state<=FETCH0;cycle<=1;ptr<=0;end end
 FETCH0:state<=FETCH1;
 FETCH1:begin queued_job<=qlo[216:0];
 // launch occupies entry[248:217], deadline entry[280:249].
 launch<=qlo[248:217];deadline<={qhi[24:0],qlo[255:249]};state<=WAIT_EDGE;end
 WAIT_EDGE:begin
 if(cycle>launch||deadline<=launch)begin fault<=1;state<=IDLE;armed<=0;end
 else if(cycle==launch)begin
  if(rd_busy)begin fault<=1;state<=IDLE;armed<=0;end
  else begin job<=queued_job;job_v<=1;state<=RUN;seen_done<=0;seen_fault<=0;end
 end end
 RUN:begin
 if(rd_done)seen_done<=1;if(rd_fault)seen_fault<=1;
 if(cycle==deadline)begin
  if(seen_fault||rd_fault||!(seen_done||rd_done))begin fault<=1;state<=IDLE;armed<=0;end
  else if({1'b0,ptr}+1==count)begin done<=1;state<=IDLE;armed<=0;end
  else begin ptr<=ptr+1;state<=FETCH0;end
 end end
 default:begin state<=IDLE;fault<=1;armed<=0;end
 endcase
 end end
endmodule
