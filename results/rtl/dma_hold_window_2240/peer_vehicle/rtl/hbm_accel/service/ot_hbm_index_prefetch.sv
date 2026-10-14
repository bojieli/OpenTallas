`timescale 1ps/1fs
`default_nettype none
// One prepaid descriptor and one acceptance receipt. Encoded buses remain
// stable until the complementary epoch handshake completes in both domains.
// Descriptor={frame73,row15,blocks9,kind2}; only decoded kind2 reaches core.
module ot_hbm_index_prefetch_source (
 input wire clk, rst_n, input wire req_v, input wire [98:0] req_d,
 output wire req_r, output wire receipt_v, input wire receipt_r,
 output wire [72:0] receipt_frame, output reg fault,
 output wire [106:0] rq_w, output reg [1:0] rq_epoch,
 input wire [80:0] rc_w, input wire [1:0] rc_epoch,
 input wire rc_fault, output reg [1:0] rc_release
);
 localparam IDLE=0,ENCODE=1,SEND=2,WAIT=3,DECODE=4,RECEIPT=5;
 reg[2:0]state,state_bar;
 reg[98:0]pending,pending_bar;
 reg armed,armed_bar;
 reg[1:0]seen_receipt;
 (* async_reg="true" *) reg[1:0]rs1,rs2;
 (* async_reg="true" *) reg fs1,fs2;
 task automatic next_state(input[2:0]s);begin state<=s;state_bar<=~s;end endtask
 ot_secded_enc #(.K(99),.R(8)) enc(.clk(clk),.d(pending),.q(rq_w));
 wire healthy=state==~state_bar && pending==~pending_bar &&
  (^rq_epoch)==1'b1 && (^rc_release)==1'b1 && (^seen_receipt)==1'b1 && armed!=armed_bar;
 wire decode_v=state==WAIT && rs2[0]!=seen_receipt[0] && (^rs2)==1'b1 && !fault&&healthy;
 wire ov,ce,ue;wire[72:0]frame;
 ot_secded_dec #(.K(73),.R(8)) dec(.clk(clk),.rst_n(rst_n),.v(decode_v),.w(rc_w),
  .ov(ov),.d(frame),.ce(ce),.ue(ue),.n_ce(),.n_ue());
 assign req_r=state==IDLE&&!fault&&healthy&&armed&&!fs2;
 assign receipt_v=state==RECEIPT&&!fault&&healthy&&!fs2;
 assign receipt_frame=pending[98:26];
 always@(posedge clk or negedge rst_n)
  if(!rst_n)begin rs1<=2'b10;rs2<=2'b10;fs1<=0;fs2<=0;end
  else begin rs1<=rc_epoch;rs2<=rs1;fs1<=rc_fault;fs2<=fs1;end
 always@(posedge clk or negedge rst_n)
  if(!rst_n)begin
   next_state(IDLE);pending<=0;pending_bar<=~99'd0;
   rq_epoch<=2'b10;rc_release<=2'b10;seen_receipt<=2'b10;fault<=0;armed<=1;armed_bar<=0;
  end else begin
   if(!healthy||fs2)fault<=1;
   if(!req_v)begin armed<=1;armed_bar<=0;end
   if(!fault&&!fs2&&healthy)case(state)
    IDLE:if(req_v&&req_r)begin pending<=req_d;pending_bar<=~req_d;armed<=0;armed_bar<=1;next_state(ENCODE);end
    ENCODE:next_state(SEND); // encoder captures the newly retained descriptor
    SEND:begin rq_epoch<={rq_epoch[0],~rq_epoch[0]};next_state(WAIT);end
    WAIT:if(decode_v)begin seen_receipt<=rs2;next_state(DECODE);end
    DECODE:if(ov)begin
     if(ue || frame!=pending[98:26])fault<=1;
     else next_state(RECEIPT);
    end
    RECEIPT:if(receipt_r)begin rc_release<=seen_receipt;next_state(IDLE);end
    default:fault<=1;
   endcase
  end
endmodule

module ot_hbm_index_prefetch_sink (
 input wire clk,rst_n,input wire[106:0]rq_w,input wire[1:0]rq_epoch,
 output wire ip_v,output wire[98:0]ip_d,input wire ip_take,
 output reg fault,output wire[80:0]rc_w,output reg[1:0]rc_epoch,
 input wire[1:0]rc_release
);
 localparam IDLE=0,DECODE=1,ADMIT=2,ENCODE=3,RELEASE=4;
 reg[2:0]state,state_bar;
 reg[98:0]pending,pending_bar;
 reg[72:0]last_frame,last_frame_bar;
 reg last_valid,last_valid_bar;
 reg[1:0]seen_request;
 (* async_reg="true" *) reg[1:0]qs1,qs2,as1,as2;
 task automatic next_state(input[2:0]s);begin state<=s;state_bar<=~s;end endtask
 wire healthy=state==~state_bar && pending==~pending_bar && last_frame==~last_frame_bar &&
  last_valid!=last_valid_bar && (^rc_epoch)==1'b1 && (^seen_request)==1'b1;
 wire decode_v=state==IDLE && qs2[0]!=seen_request[0] && (^qs2)==1'b1&&!fault&&healthy;
 wire ov,ce,ue;wire[98:0]decoded;
 ot_secded_dec #(.K(99),.R(8)) dec(.clk(clk),.rst_n(rst_n),.v(decode_v),.w(rq_w),
  .ov(ov),.d(decoded),.ce(ce),.ue(ue),.n_ce(),.n_ue());
 ot_secded_enc #(.K(73),.R(8)) enc(.clk(clk),.d(pending[98:26]),.q(rc_w));
 assign ip_v=state==ADMIT&&!fault&&healthy;
 assign ip_d=pending;
 always@(posedge clk or negedge rst_n)
  if(!rst_n)begin qs1<=2'b10;qs2<=2'b10;as1<=2'b10;as2<=2'b10;end
  else begin qs1<=rq_epoch;qs2<=qs1;as1<=rc_release;as2<=as1;end
 always@(posedge clk or negedge rst_n)
  if(!rst_n)begin
   next_state(IDLE);pending<=0;pending_bar<=~99'd0;
   last_frame<=0;last_frame_bar<=~73'd0;last_valid<=0;last_valid_bar<=1;
   seen_request<=2'b10;rc_epoch<=2'b10;fault<=0;
  end else begin
   if(!healthy)fault<=1;
   if(!fault&&healthy)case(state)
    IDLE:if(decode_v)begin seen_request<=qs2;next_state(DECODE);end
    DECODE:if(ov)begin
     if(ue || decoded[1:0]!=2'd2 || decoded[10:2]==0 || decoded[10:2]>9'd342 ||
        (last_valid && decoded[98:26]==last_frame))fault<=1;
     else begin pending<=decoded;pending_bar<=~decoded;next_state(ADMIT);end
    end
    ADMIT:if(ip_take)begin
     last_frame<=pending[98:26];last_frame_bar<=~pending[98:26];
     last_valid<=1;last_valid_bar<=0;next_state(ENCODE);
    end
    ENCODE:begin rc_epoch<={rc_epoch[0],~rc_epoch[0]};next_state(RELEASE);end
    RELEASE:if(as2==rc_epoch&&(^as2)==1'b1)next_state(IDLE);
    default:fault<=1;
   endcase
  end
endmodule
`default_nettype wire
