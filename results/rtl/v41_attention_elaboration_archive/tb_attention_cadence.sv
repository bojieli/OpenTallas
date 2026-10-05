`timescale 1ns/1ps
module tb_attention_cadence;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,job_v=0,q_v=0,kv_v=0,p_v=0;
integer T=640, GAP=1;
wire job_ready,q_ready,kv_ready,p_ready,sc_v,pv_v,qk_iss,pv_iss;
wire [15:0] sc_row; wire [3:0] sc_m;
wire [2047:0] sc_y;wire [63:0] sc_f;
wire [7:0] pv_c;wire [32767:0] pv_y;wire [1023:0] pv_f;
ot_hdc_v41x_attn #(.H(16),.D(512),.TD(32),.NL(4),.TROWS(640)) dut(
.clk(clk),.rst_n(rst_n),.job_v(job_v),.job_t(16'(T)),.job_ready(job_ready),
.q_v(q_v),.q_ready(q_ready),.q_w(8192'd0),.kv_v(kv_v),.kv_ready(kv_ready),.kv_m(4'hf),.kv_w(16960'd0),
.sc_v(sc_v),.sc_row(sc_row),.sc_m(sc_m),.sc_y(sc_y),.sc_f(sc_f),.sc_cr(sc_v),
.p_v(p_v),.p_ready(p_ready),.p_w(512'd0),.pv_v(pv_v),.pv_c(pv_c),.pv_y(pv_y),.pv_f(pv_f),.pv_cr(pv_v),
.qk_iss(qk_iss),.pv_iss(pv_iss));
integer cycle=0,qs=0,kvs=0,ps=0,scores=0,qkis=0,pvis=0;
integer kfirst=-1,klast=-1,qfirst=-1,qlast=-1,pfirst=-1,plast=-1,slast=-1;
integer wait_prob=0,wait_fill=0,wait_kv=0;
always @(posedge clk) if(rst_n) begin
cycle=cycle+1;
if(q_v&&q_ready) qs=qs+1;
if(kv_v&&kv_ready) begin kvs=kvs+1;if(kfirst<0)kfirst=cycle;klast=cycle;end
if(p_v&&p_ready) ps=ps+1;
if(sc_v)begin scores=scores+4;slast=cycle;end
if(qk_iss)begin qkis=qkis+1;if(qfirst<0)qfirst=cycle;qlast=cycle;end
if(pv_iss)begin pvis=pvis+1;if(pfirst<0)pfirst=cycle;plast=cycle;end
if(dut.act&&!dut.phase_pv&&dut.q_cnt==16&&!dut.qk_rows_ok)wait_kv=wait_kv+1;
if(dut.act&&dut.phase_pv&&!dut.iss_loaded)wait_prob=wait_prob+1;
if(dut.act&&dut.phase_pv&&dut.filled_upto<=dut.iss_blk)wait_fill=wait_fill+1;
if(pvis==((T+31)/32)*8) begin
$display("CONTROL_ONLY T=%0d gap=%0d kv_beats=%0d kv_first=%0d kv_last=%0d qk_beats=%0d qk_first=%0d qk_last=%0d last_score=%0d p_words=%0d pv_beats=%0d pv_first=%0d pv_last=%0d wait_kv=%0d wait_prob=%0d wait_fill=%0d",T,GAP,kvs,kfirst,klast,qkis,qfirst,qlast,slast,ps,pvis,pfirst,plast,wait_kv,wait_prob,wait_fill);
$finish;end
if(cycle>10000)$fatal(1,"timeout");
end
always @(negedge clk)if(rst_n)begin
q_v=qs<16;kv_v=kvs<T/4&&(cycle%GAP==0);p_v=scores>=T&&ps<T/2;
end
initial begin
if($value$plusargs("rows=%d",T));if($value$plusargs("gap=%d",GAP));
repeat(3)@(negedge clk);rst_n=1;job_v=1;@(negedge clk);job_v=0;
end
endmodule
