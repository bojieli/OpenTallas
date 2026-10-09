`default_nettype none
// Native loader byte address is validated by the actual external mapper. The
// supplied sector/PC are its outputs, not a guessed truncation or aperture.
// wr_ack is source-owned retirement of physical write completion, NEVER credit.
module ot_hbm_loader_native_endpoint #(parameter integer ENABLE=0)(
 input wire clk,rst_n,input wire req_v,output wire req_rdy,
 input wire req_we,input wire [31:0] req_addr,input wire [255:0] req_wdata,
 input wire [31:0] req_wstrb,input wire [15:0] req_tag,
 input wire translation_valid,input wire [4:0] translated_pc,input wire [29:0] translated_addr,
 output wire rsp_v,input wire rsp_rdy,output wire rsp_we,
 output wire [15:0] rsp_tag,output wire [255:0] rsp_data,
 output wire wr_v,input wire wr_rdy,output wire [290:0] wr_packet,input wire wr_ack,
 output wire rd_v,input wire rd_rdy,output wire [4:0] rd_pc,
 output wire [29:0] rd_addr,output wire [15:0] rd_tag,
 input wire rd_rsp_v,output wire rd_rsp_rdy,input wire [4:0] rd_rsp_pc,
 input wire [15:0] rd_rsp_tag,input wire [3:0] rd_rsp_beat,input wire [255:0] rd_rsp_data,
 input wire service_fault,output wire busy,output wire fault
);
 generate if (!ENABLE) begin:g_off
 assign req_rdy=0;assign rsp_v=0;assign rsp_we=0;assign rsp_tag=0;assign rsp_data=0;
 assign wr_v=0;assign wr_packet=0;assign rd_v=0;assign rd_pc=0;assign rd_addr=0;assign rd_tag=0;assign rd_rsp_rdy=0;assign busy=0;assign fault=0;
 end else begin:g_on
 localparam [2:0] IDLE=0,WRITE_ISSUE=1,WRITE_WAIT=2,READ_ISSUE=3,READ_WAIT=4,REPLY=5;
 reg [2:0] state;reg sticky,we_q;reg [4:0] pc_q;reg [29:0] addr_q;
 reg [15:0] tag_q;reg [255:0] data_q,reply_q;
 wire valid=translation_valid&&req_addr[4:0]==0&&(!req_we||req_wstrb==32'hffffffff);
 wire rd_match=rd_rsp_pc==pc_q&&rd_rsp_tag==tag_q&&rd_rsp_beat==0;
 assign req_rdy=state==IDLE&&valid&&!sticky&&!service_fault;
 assign wr_v=state==WRITE_ISSUE&&!sticky&&!service_fault;
 assign wr_packet={data_q,addr_q,pc_q};
 assign rd_v=state==READ_ISSUE&&!sticky&&!service_fault;
 assign rd_pc=pc_q;assign rd_addr=addr_q;assign rd_tag=tag_q;
 assign rd_rsp_rdy=state==READ_WAIT&&rd_match&&!sticky&&!service_fault;
 assign rsp_v=state==REPLY&&!sticky&&!service_fault;
 assign rsp_we=we_q;assign rsp_tag=tag_q;assign rsp_data=reply_q;
 assign busy=state!=IDLE;assign fault=sticky||service_fault;
 always @(posedge clk or negedge rst_n) if(!rst_n)begin
 state<=IDLE;sticky<=0;we_q<=0;pc_q<=0;addr_q<=0;tag_q<=0;data_q<=0;reply_q<=0;
 end else begin
 if(req_v&&state==IDLE&&!valid)sticky<=1;
 if(wr_ack&&state!=WRITE_WAIT)sticky<=1;
 if(rd_rsp_v&&(state!=READ_WAIT||!rd_match))sticky<=1;
 if(req_v&&req_rdy)begin
 we_q<=req_we;pc_q<=translated_pc;addr_q<=translated_addr;tag_q<=req_tag;data_q<=req_wdata;
 state<=req_we?WRITE_ISSUE:READ_ISSUE;
 end
 if(wr_v&&wr_rdy)state<=WRITE_WAIT;
 if(state==WRITE_WAIT&&wr_ack&&!service_fault)begin reply_q<=0;state<=REPLY;end
 if(rd_v&&rd_rdy)state<=READ_WAIT;
 if(rd_rsp_v&&rd_rsp_rdy)begin reply_q<=rd_rsp_data;state<=REPLY;end
 if(rsp_v&&rsp_rdy)state<=IDLE;
 end
 end endgenerate
endmodule
`default_nettype wire
