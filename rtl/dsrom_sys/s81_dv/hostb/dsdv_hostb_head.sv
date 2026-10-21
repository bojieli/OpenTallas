`timescale 1ns/1ps
`default_nettype none
// Connect ahead of the actual HD-CTL ri pin. Existing RESULT/DRAFT remain
// untouched. HSF0 type10 is distinct stage-event egress, booked separately.
module dsdv_hostb_head(input wire ck,rst_n,configured,return_slot,
 input wire [7:0] expected_stage,input wire [1:0] expected_rank,local_group,
 input wire [15:0] expected_tid,input wire [9:0] expected_user,
 input wire [20:0] expected_position,expected_token,
 input wire [31:0] epoch_id,input wire [63:0] programme_id,
 input wire [47:0] receiver_edge,input wire [1103:0] ring_i,
 output wire [1103:0] to_ctl,
 output reg htv,output reg [552:0] htd,output reg [3:0] fault);
 wire rn;ot_reset_sync #(.ASYNC_STAGES(2)) u_reset(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 wire [511:0] p=ring_i[532:21];
 wire event_record=ring_i[0] && ring_i[3:1]==6 && p[31:0]==32'h31454248 && p[39:36]==3;
 wire shape=p[35:32]==2 && p[75:66]==131 && p[77:76]==0 && !(|p[511:405]);
 wire identity=configured && p[47:40]==expected_stage && expected_stage<241 && p[49:48]==expected_rank &&
   p[65:50]==expected_tid && p[87:78]==expected_user && p[108:88]==expected_position &&
   p[129:109]==expected_token && p[161:130]==epoch_id && p[273:210]==programme_id;
 assign to_ctl={ring_i[1103:1],ring_i[0]&&!event_record};
 always @(posedge ck)htd<={1'b1,24'd0,p,8'd0,local_group,expected_rank,4'd10};
 always @(posedge ck or negedge rn)begin
   if(!rn)begin htv<=0;fault<=0;end
   else begin
     htv<=0;
     if(return_slot&&!event_record)fault[0]<=1;
     if(event_record)begin
       if(!return_slot || receiver_edge>p[209:162])fault[1]<=1;
       else if(!shape)fault[2]<=1;
       else if(!identity)fault[3]<=1;
       else htv<=fault==0;
     end
   end
 end
endmodule
`default_nettype wire
