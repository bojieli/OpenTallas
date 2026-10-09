`default_nettype none
// One physical PC, one read lease. Normal traffic wins idle admission; once
// native is admitted its descriptor remains stable and exclusively owns reply.
// The parent selects this PC through actual address mapping and coordinates WB.
module ot_hbm_loader_read_lease #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire normal_v,output wire normal_rdy,input wire [29:0] normal_addr,
 input wire [3:0] normal_len,input wire [16:0] normal_tag,
 output wire normal_rsp_v,input wire normal_rsp_rdy,output wire [16:0] normal_rsp_tag,
 output wire [3:0] normal_rsp_beat,output wire [255:0] normal_rsp_data,
 input wire native_v,output wire native_rdy,input wire [29:0] native_addr,input wire [15:0] native_tag,
 output wire native_rsp_v,input wire native_rsp_rdy,output wire [15:0] native_rsp_tag,
 output wire [3:0] native_rsp_beat,output wire [255:0] native_rsp_data,
 output wire k_v,input wire k_rdy,output wire [29:0] k_addr,output wire [3:0] k_len,output wire [16:0] k_tag,
 input wire kr_v,output wire kr_rdy,input wire [16:0] kr_tag,input wire [3:0] kr_beat,input wire [255:0] kr_data,
 output wire fault
);
 generate if(ENABLE==0)begin:off
 assign k_v=normal_v;assign normal_rdy=k_rdy;assign k_addr=normal_addr;assign k_len=normal_len;assign k_tag=normal_tag;
 assign normal_rsp_v=kr_v;assign kr_rdy=normal_rsp_rdy;assign normal_rsp_tag=kr_tag;assign normal_rsp_beat=kr_beat;assign normal_rsp_data=kr_data;
 assign native_rdy=0;assign native_rsp_v=0;assign native_rsp_tag=0;assign native_rsp_beat=0;assign native_rsp_data=0;assign fault=0;
 end else begin:on
 localparam [1:0] IDLE=0,NORMAL=1,ISSUE=2,NATIVE=3;
 reg[1:0]state;reg sticky;reg[29:0]addr_q;reg[16:0]tag_q;reg[3:0]len_q;reg[15:0]seen;
 wire normal_ok=kr_tag==tag_q&&kr_beat<len_q&&!seen[kr_beat];
 wire native_ok=kr_tag==tag_q&&kr_beat==0;
 wire normal_take=normal_v&&normal_rdy;
 assign native_rdy=state==IDLE&&!normal_v&&!sticky;
 assign k_v=!sticky&&((state==IDLE&&normal_v&&normal_len!=0)||(state==ISSUE));
 assign normal_rdy=state==IDLE&&normal_len!=0&&!sticky&&k_rdy;
 assign k_addr=state==ISSUE?addr_q:normal_addr;
 assign k_len=state==ISSUE?4'd1:normal_len;
 assign k_tag=state==ISSUE?tag_q:normal_tag;
 assign normal_rsp_v=kr_v&&state==NORMAL&&normal_ok&&!sticky;
 assign normal_rsp_tag=kr_tag;assign normal_rsp_beat=kr_beat;assign normal_rsp_data=kr_data;
 assign native_rsp_v=kr_v&&state==NATIVE&&native_ok&&!sticky;
 assign native_rsp_tag=tag_q[15:0];assign native_rsp_beat=kr_beat;assign native_rsp_data=kr_data;
 assign kr_rdy=normal_rsp_v?normal_rsp_rdy:(native_rsp_v?native_rsp_rdy:1'b0);
 assign fault=sticky;
 wire[15:0]next_seen=seen|(16'b1<<kr_beat);
 wire[15:0]expected=(16'b1<<len_q)-1;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
 state<=IDLE;sticky<=0;addr_q<=0;tag_q<=0;len_q<=0;seen<=0;
 end else begin
 if(normal_v&&state==IDLE&&normal_len==0)sticky<=1;
 if(kr_v&&((state==NORMAL&&!normal_ok)||(state==NATIVE&&!native_ok)||(state!=NORMAL&&state!=NATIVE)))sticky<=1;
 if(normal_take)begin state<=NORMAL;tag_q<=normal_tag;len_q<=normal_len;seen<=0;end
 if(native_v&&native_rdy)begin state<=ISSUE;addr_q<=native_addr;tag_q<={1'b1,native_tag};end
 if(state==ISSUE&&k_v&&k_rdy)state<=NATIVE;
 if(normal_rsp_v&&normal_rsp_rdy)begin seen<=next_seen;if(next_seen==expected)state<=IDLE;end
 if(native_rsp_v&&native_rsp_rdy)state<=IDLE;
 end
 end endgenerate
endmodule
`default_nettype wire
