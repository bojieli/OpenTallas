`default_nettype none
// Actual K boundary lease, including production multi-outstanding KVS reads.
// normal_pending_write covers write transport/FIFO/pipeline/landing before PHY
// acceptance; it must be actual ownership state. Accepted writes tracked here.
module ot_hbm_loader_pc_service_lease #(parameter integer ENABLE=0, ENABLE_NATIVE_BURST=0)(
 input wire clk,rst_n,normal_pending_write,
 input wire normal_v,output wire normal_rdy,input wire normal_we,
 input wire [29:0] normal_addr,input wire [3:0] normal_len,input wire [16:0] normal_tag,
 input wire [255:0] normal_wdata,input wire [31:0] normal_wstrb,
 output wire normal_rsp_v,input wire normal_rsp_rdy,output wire [16:0] normal_rsp_tag,
 output wire [3:0] normal_rsp_beat,output wire [255:0] normal_rsp_data,
 input wire native_v,output wire native_rdy,input wire [29:0] native_addr,input wire [15:0] native_tag,input wire [3:0] native_len,
 output wire native_rsp_v,input wire native_rsp_rdy,output wire [15:0] native_rsp_tag,
 output wire [3:0] native_rsp_beat,output wire [255:0] native_rsp_data,
 output wire k_v,input wire k_rdy,output wire k_we,output wire [29:0] k_addr,
 output wire [3:0] k_len,output wire [16:0] k_tag,output wire [255:0] k_wdata,output wire [31:0] k_wstrb,
 input wire kr_v,output wire kr_rdy,input wire [16:0] kr_tag,input wire [3:0] kr_beat,input wire [255:0] kr_data,
 input wire k_wr_done,output wire native_busy,output wire fault
);
 generate if(ENABLE==0)begin:off
 assign k_v=normal_v;assign normal_rdy=k_rdy;assign k_we=normal_we;assign k_addr=normal_addr;
 assign k_len=normal_len;assign k_tag=normal_tag;assign k_wdata=normal_wdata;assign k_wstrb=normal_wstrb;
 assign normal_rsp_v=kr_v;assign kr_rdy=normal_rsp_rdy;assign normal_rsp_tag=kr_tag;assign normal_rsp_beat=kr_beat;assign normal_rsp_data=kr_data;
 assign native_rdy=0;assign native_rsp_v=0;assign native_rsp_tag=0;assign native_rsp_beat=0;assign native_rsp_data=0;assign fault=0;assign native_busy=0;
 end else begin:on
 localparam [1:0] IDLE=0,ISSUE=1,WAIT_REPLY=2,REPLY=3;
 reg[1:0]state;reg sticky;reg[6:0]read_debt;reg[3:0]write_debt;
 reg[3:0]len_q,received_q,beat_q;reg reply_full;
 reg[29:0]addr_q;reg[15:0]tag_q;reg[255:0]reply_q;
 wire is_normal=state==IDLE;
 wire normal_take=normal_v&&normal_rdy;
 wire add_read=normal_take&&!normal_we;
 wire add_write=normal_take&&normal_we;
 wire normal_room=normal_we?write_debt<8:(read_debt+7'(normal_len)<=64&&normal_len!=0);
 wire normal_reply=kr_v&&is_normal&&read_debt!=0&&!sticky;
 wire native_match=kr_tag=={1'b1,tag_q}&&kr_beat==received_q;
 wire length_ok=ENABLE_NATIVE_BURST==0||(native_len>=1&&native_len<=8);
 wire reply_take=native_rsp_v&&native_rsp_rdy;
 wire receive_take=state==WAIT_REPLY&&kr_v&&kr_rdy;
 wire[7:0]new_read={1'b0,read_debt}+(add_read?8'(normal_len):8'd0)-(normal_reply&&normal_rsp_rdy?8'd1:8'd0);
 wire[4:0]new_write={1'b0,write_debt}+(add_write?5'd1:5'd0)-(k_wr_done?5'd1:5'd0);
 assign native_rdy=is_normal&&read_debt==0&&write_debt==0&&!normal_v&&!normal_pending_write&&!sticky&&length_ok;
 assign native_busy=state!=IDLE;
 assign k_v=!sticky&&((is_normal&&normal_v&&normal_room)||(state==ISSUE));
 assign normal_rdy=is_normal&&normal_room&&!sticky&&k_rdy;
 assign k_we=is_normal&&normal_we;
 assign k_addr=is_normal?normal_addr:addr_q;
 assign k_len=is_normal?normal_len:len_q;
 assign k_tag=is_normal?normal_tag:{1'b1,tag_q};
 assign k_wdata=normal_wdata;assign k_wstrb=is_normal?normal_wstrb:32'd0;
 assign normal_rsp_v=normal_reply;
 assign normal_rsp_tag=kr_tag;assign normal_rsp_beat=kr_beat;assign normal_rsp_data=kr_data;
 assign kr_rdy=is_normal&&read_debt!=0&&!sticky?normal_rsp_rdy:(state==WAIT_REPLY&&!sticky&&(!reply_full||native_rsp_rdy)&&(!kr_v||native_match));
 assign native_rsp_v=reply_full&&!sticky;
 assign native_rsp_tag=tag_q;assign native_rsp_beat=beat_q;assign native_rsp_data=reply_q;
 assign fault=sticky;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
 state<=IDLE;sticky<=0;read_debt<=0;write_debt<=0;addr_q<=0;tag_q<=0;reply_q<=0;len_q<=1;received_q<=0;beat_q<=0;reply_full<=0;
 end else begin
 read_debt<=new_read[6:0];write_debt<=new_write[3:0];
 if(new_read>64||new_write>8)sticky<=1;
 if(kr_v&&((is_normal&&read_debt==0)||(state==WAIT_REPLY&&!native_match)||(state!=IDLE&&state!=WAIT_REPLY)))sticky<=1;
 if(native_v&&native_rdy)begin state<=ISSUE;addr_q<=native_addr;tag_q<=native_tag;len_q<=ENABLE_NATIVE_BURST!=0?native_len:4'd1;received_q<=0;end
 if(state==ISSUE&&k_v&&k_rdy)state<=WAIT_REPLY;
 if(reply_take)reply_full<=0;
 if(receive_take)begin reply_q<=kr_data;beat_q<=kr_beat;reply_full<=1;received_q<=received_q+1;
 if(received_q+1==len_q)state<=REPLY;end
 if(reply_take&&state==REPLY)state<=IDLE;
 end
 end endgenerate
endmodule
`default_nettype wire
