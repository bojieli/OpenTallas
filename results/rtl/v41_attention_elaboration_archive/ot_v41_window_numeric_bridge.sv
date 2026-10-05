`timescale 1ns/1ps
// Integration harness boundary only: WINDOW source is owned separately.
// Full H16/D512/TD32/T640 numerical engine is unmodified.
// Q and P are external golden operands here, not a live projection or softmax.
module ot_v41_window_numeric_bridge (
 input wire clk,rst_n,
 input wire staged_v, input wire [7:0] window_rows,
 output reg stream_go,output wire descriptor_ready,
 input wire source_kv_v, output wire source_kv_ready,
 input wire [3:0] source_kv_m,input wire [16959:0] source_kv_w,
 input wire q_v,input wire [8191:0] q_w,output wire q_ready,
 input wire p_v,input wire [511:0] p_w,output wire p_ready,
 output wire sc_v,output wire [15:0] sc_row,output wire [3:0] sc_m,
 output wire [2047:0] sc_y,output wire [63:0] sc_f,input wire sc_cr,
 output wire pv_v,output wire [7:0] pv_c,output wire [32767:0] pv_y,
 output wire [1023:0] pv_f,input wire pv_cr,
 output wire qk_iss,pv_iss
);
 wire engine_ready;
 reg pending;
 reg [15:0] rows;
 wire job_go=pending&&engine_ready;
 assign descriptor_ready=!pending&&engine_ready;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin pending<=0;rows<=0;stream_go<=0;end
  else begin
   if(staged_v&&!descriptor_ready)$fatal(1,"staged descriptor while previous numeric job active");
   if(staged_v&&(window_rows==0||window_rows>128))$fatal(1,"invalid WINDOW row count");
   stream_go<=job_go;
   if(staged_v&&descriptor_ready)begin pending<=1;rows<={8'd0,window_rows};end
   if(job_go)pending<=0;
  end
 // stream_go appears after job acceptance: engine KV ready is valid then.
 ot_hdc_v41x_attn #(.H(16),.D(512),.TD(32),.NL(4),.TROWS(640)) engine(
 .clk(clk),.rst_n(rst_n),.job_v(pending),.job_t(rows),.job_ready(engine_ready),
 .q_v(q_v),.q_w(q_w),.q_ready(q_ready),
 .kv_v(source_kv_v),.kv_ready(source_kv_ready),.kv_m(source_kv_m),.kv_w(source_kv_w),
 .p_v(p_v),.p_w(p_w),.p_ready(p_ready),
 .sc_v(sc_v),.sc_row(sc_row),.sc_m(sc_m),.sc_y(sc_y),.sc_f(sc_f),.sc_cr(sc_cr),
 .pv_v(pv_v),.pv_c(pv_c),.pv_y(pv_y),.pv_f(pv_f),.pv_cr(pv_cr),
 .qk_iss(qk_iss),.pv_iss(pv_iss));
endmodule
