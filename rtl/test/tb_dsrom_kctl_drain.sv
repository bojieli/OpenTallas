`timescale 1ps/1ps
module tb_dsrom_kctl_drain;
localparam NPC=32,WB=32,GA=24,AW=30,HW=23,TAGW=16,LENW=4,BEATW=4,DW=256;
reg clk=0; always #416 clk=~clk;
reg rst_n=0,cmd_v=0;
reg [HW-1:0] cmd_base=17,cmd_base2=0;
reg [9:0] cmd_skip=0;
reg [HW+9:0] cmd_nkeys=0,cmd_nkeys2=0;
reg [NPC-1:0] req_rdy=0,rsp_v=0;
reg [NPC*TAGW-1:0] rsp_tag=0;
reg [NPC*BEATW-1:0] rsp_beat=0;
reg [NPC*DW-1:0] rsp_data=0;
reg o_ready=0;
wire  busy_a,busy_b,busy_off;
wire [NPC-1:0] req_v_a,req_v_b,req_v_off;
wire [NPC*AW-1:0] req_addr_a,req_addr_b,req_addr_off;
wire [NPC*LENW-1:0] req_len_a,req_len_b,req_len_off;
wire [NPC*TAGW-1:0] req_tag_a,req_tag_b,req_tag_off;
wire [NPC-1:0] rsp_rdy_a,rsp_rdy_b,rsp_rdy_off;
wire  o_valid_a,o_valid_b,o_valid_off;
wire [15:0] o_kv_a,o_kv_b,o_kv_off;
wire [16*544-1:0] o_key_a,o_key_b,o_key_off;
wire [47:0] cnt_keys_streamed_a,cnt_keys_streamed_b,cnt_keys_streamed_off;
wire [47:0] cnt_hbm_beats_a,cnt_hbm_beats_b,cnt_hbm_beats_off;
ot_hdc_v41x_idx_kstream_ring #(.NPC(NPC),.WB(WB),.GA(GA),.AW(AW),.HW(HW),.TAGW(TAGW)) u_a (
.clk(clk),
.rst_n(rst_n),
.cmd_v(cmd_v),
.cmd_base(cmd_base),
.cmd_skip(cmd_skip),
.cmd_nkeys(cmd_nkeys),
.cmd_base2(cmd_base2),
.cmd_nkeys2(cmd_nkeys2),
.busy(busy_a),
.req_v(req_v_a),
.req_rdy(req_rdy),
.req_addr(req_addr_a),
.req_len(req_len_a),
.req_tag(req_tag_a),
.rsp_v(rsp_v),
.rsp_rdy(rsp_rdy_a),
.rsp_tag(rsp_tag),
.rsp_beat(rsp_beat),
.rsp_data(rsp_data),
.o_valid(o_valid_a),
.o_ready(o_ready),
.o_kv(o_kv_a),
.o_key(o_key_a),
.cnt_keys_streamed(cnt_keys_streamed_a),
.cnt_hbm_beats(cnt_hbm_beats_a));
ot_hdc_v41x_idx_kstream_ring_drain #(.ENABLE(1),.NPC(NPC),.WB(WB),.GA(GA),.AW(AW),.HW(HW),.TAGW(TAGW)) u_b (
.clk(clk),
.rst_n(rst_n),
.cmd_v(cmd_v),
.cmd_base(cmd_base),
.cmd_skip(cmd_skip),
.cmd_nkeys(cmd_nkeys),
.cmd_base2(cmd_base2),
.cmd_nkeys2(cmd_nkeys2),
.busy(busy_b),
.req_v(req_v_b),
.req_rdy(req_rdy),
.req_addr(req_addr_b),
.req_len(req_len_b),
.req_tag(req_tag_b),
.rsp_v(rsp_v),
.rsp_rdy(rsp_rdy_b),
.rsp_tag(rsp_tag),
.rsp_beat(rsp_beat),
.rsp_data(rsp_data),
.o_valid(o_valid_b),
.o_ready(o_ready),
.o_kv(o_kv_b),
.o_key(o_key_b),
.cnt_keys_streamed(cnt_keys_streamed_b),
.cnt_hbm_beats(cnt_hbm_beats_b));
ot_hdc_v41x_idx_kstream_ring_drain #(.ENABLE(0),.NPC(NPC),.WB(WB),.GA(GA),.AW(AW),.HW(HW),.TAGW(TAGW)) u_off (
.clk(clk),
.rst_n(rst_n),
.cmd_v(cmd_v),
.cmd_base(cmd_base),
.cmd_skip(cmd_skip),
.cmd_nkeys(cmd_nkeys),
.cmd_base2(cmd_base2),
.cmd_nkeys2(cmd_nkeys2),
.busy(busy_off),
.req_v(req_v_off),
.req_rdy(req_rdy),
.req_addr(req_addr_off),
.req_len(req_len_off),
.req_tag(req_tag_off),
.rsp_v(rsp_v),
.rsp_rdy(rsp_rdy_off),
.rsp_tag(rsp_tag),
.rsp_beat(rsp_beat),
.rsp_data(rsp_data),
.o_valid(o_valid_off),
.o_ready(o_ready),
.o_kv(o_kv_off),
.o_key(o_key_off),
.cnt_keys_streamed(cnt_keys_streamed_off),
.cnt_hbm_beats(cnt_hbm_beats_off));
integer rembeats[0:NPC-1],sent[0:NPC-1];
reg [TAGW-1:0] tags[0:NPC-1];
reg [AW-1:0] addr[0:NPC-1];
integer cyc=0, scans=0, count=0, p,j,t,step, first,last,words;
integer sizes[0:13];
initial begin
for(p=0;p<NPC;p=p+1) begin rembeats[p]=0;sent[p]=0;end
sizes[0]=0;sizes[1]=1;sizes[2]=15;sizes[3]=16;sizes[4]=17;sizes[5]=63;sizes[6]=64;sizes[7]=65;
sizes[8]=1023;sizes[9]=1024;sizes[10]=1025;sizes[11]=2048;sizes[12]=4097;sizes[13]=8193;
repeat(3) @(negedge clk);rst_n=1;
for(t=0;t<28;t=t+1) begin
@(negedge clk);cmd_v=1;cmd_nkeys=sizes[t%14];cmd_skip=(t>=14 && sizes[t%14]!=0)?37:0;
cmd_nkeys2=(t>=14)?sizes[(t+3)%14]:0;cmd_base=17+(t%3)*17;cmd_base2=0;
first=cyc;words=0;
begin : scan_loop
for(step=0;step<200000;step=step+1) begin
if(step!=0) @(negedge clk);
if(step==1)cmd_v=0;
o_ready=((cyc%19)!=3 && (cyc%19)!=4 && (cyc%19)!=5);
for(p=0;p<NPC;p=p+1) begin
req_rdy[p]=(rembeats[p]==0 && ((cyc+p)%7!=0));
rsp_v[p]=(rembeats[p]!=0 && ((cyc+3*p)%5!=0));
rsp_tag[p*TAGW+:TAGW]=tags[p];rsp_beat[p*BEATW+:BEATW]=sent[p];
for(j=0;j<8;j=j+1)rsp_data[p*DW+j*32+:32]=(addr[p]+sent[p])*32'h9e3779b1+j;
end
@(posedge clk);
for(p=0;p<NPC;p=p+1) begin
if(rsp_v[p] && rsp_rdy_a[p])begin rembeats[p]=rembeats[p]-1;sent[p]=sent[p]+1;end
if(req_v_a[p] && req_rdy[p])begin rembeats[p]=req_len_a[p*LENW+:LENW];sent[p]=0;tags[p]=req_tag_a[p*TAGW+:TAGW];addr[p]=req_addr_a[p*AW+:AW];end
end
#1;cyc=cyc+1;
if(1 && (busy_a !== busy_b || busy_a !== busy_off)) $fatal(1,"mismatch busy scan=%0d cycle=%0d",t,cyc);
if(1 && (req_v_a !== req_v_b || req_v_a !== req_v_off)) $fatal(1,"mismatch req_v scan=%0d cycle=%0d",t,cyc);
if((|req_v_a) && (req_addr_a !== req_addr_b || req_addr_a !== req_addr_off)) $fatal(1,"mismatch req_addr scan=%0d cycle=%0d",t,cyc);
if((|req_v_a) && (req_len_a !== req_len_b || req_len_a !== req_len_off)) $fatal(1,"mismatch req_len scan=%0d cycle=%0d",t,cyc);
if((|req_v_a) && (req_tag_a !== req_tag_b || req_tag_a !== req_tag_off)) $fatal(1,"mismatch req_tag scan=%0d cycle=%0d",t,cyc);
if(1 && (rsp_rdy_a !== rsp_rdy_b || rsp_rdy_a !== rsp_rdy_off)) $fatal(1,"mismatch rsp_rdy scan=%0d cycle=%0d",t,cyc);
if(1 && (o_valid_a !== o_valid_b || o_valid_a !== o_valid_off)) $fatal(1,"mismatch o_valid scan=%0d cycle=%0d",t,cyc);
if(o_valid_a && (o_kv_a !== o_kv_b || o_kv_a !== o_kv_off)) $fatal(1,"mismatch o_kv scan=%0d cycle=%0d",t,cyc);
if(o_valid_a && (o_key_a !== o_key_b || o_key_a !== o_key_off)) $fatal(1,"mismatch o_key scan=%0d cycle=%0d",t,cyc);
if(1 && (cnt_keys_streamed_a !== cnt_keys_streamed_b || cnt_keys_streamed_a !== cnt_keys_streamed_off)) $fatal(1,"mismatch cnt_keys_streamed scan=%0d cycle=%0d",t,cyc);
if(1 && (cnt_hbm_beats_a !== cnt_hbm_beats_b || cnt_hbm_beats_a !== cnt_hbm_beats_off)) $fatal(1,"mismatch cnt_hbm_beats scan=%0d cycle=%0d",t,cyc);
if(o_valid_a && o_ready)words=words+1;
if(step>2 && !busy_a)begin
$display("SCAN id=%0d first_keys=%0d skip=%0d second_keys=%0d cycles=%0d words=%0d baseline_keys=%0d candidate_keys=%0d",t,cmd_nkeys,cmd_skip,cmd_nkeys2,cyc-first,words,cnt_keys_streamed_a,cnt_keys_streamed_b);
scans=scans+1;disable scan_loop;end
end
if(step==200000)$fatal(1,"scan failed to drain");
end
end
$display("PASS KCTL_DRAIN scans=%0d cycles=%0d",scans,cyc);$finish;
end
endmodule
