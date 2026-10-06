`timescale 1ns/1ps
// Four actual restored NC8 rows reserved before a no-ready W2 launch.
// Provider write ACK and complete payload readback precede visible completion.
// Root POR only: local CP reset never discards accepted result/provider debt.
module ot_hbm_integrated_w2_result_sink #(
 parameter integer ENABLE=0
)(
 input wire clk,por_n,owned,installed,
 input wire reserve_v,output wire reserve_r,
 input wire pair_op,input wire [1:0] rows_a,rows_b,
 input wire [31:0] op_a,op_b,base_a,limit_a,base_b,limit_b,
 input wire [15:0] provider_tag,
 input wire [72:0] frame,
 output wire source_permit,retained,done,quiet,fault,
 input wire result_v,input wire [31:0] result_op,
 input wire [11:0] result_row,input wire [255:0] result_data,
 input wire native_done,retire_v,output wire retire_r,
 output wire req_v,input wire req_r,output wire [336:0] req,
 input wire rsp_v,output wire rsp_r,input wire [272:0] rsp
);
 generate if(!ENABLE)begin:off
 assign reserve_r=0;assign source_permit=0;assign retained=0;
 assign done=0;assign quiet=1;assign fault=0;assign retire_r=0;
 assign req_v=0;assign req=0;assign rsp_r=0;
 end else begin:on
 localparam [2:0] IDLE=0,CAPTURE=1,WRITE=2,WAIT_WRITE=3,READ=4,WAIT_READ=5,DONE=6,FAIL=7;
 // metadata: frame2, original operation IDs1, extents4, shape/tag1.
 // payload4*4 protected words; control1. No result-ready substituted for rv.
 reg [71:0] code[0:24];
 wire [65:0] decoded[0:24];wire [63:0] data[0:24];
 wire [24:0] uncorrectable;
 for(genvar k=0;k<25;k=k+1)begin:protected_rows
  assign decoded[k]=ot_gpu_w6_secded_pkg::decode64(code[k]);
  assign data[k]=decoded[k][63:0];assign uncorrectable[k]=decoded[k][65];
 end
 wire [2:0] state=data[24][2:0];
 wire [3:0] seen=data[24][6:3],verified=data[24][10:7];
 wire [1:0] slot=data[24][12:11];wire native_finished=data[24][13];
 wire [72:0] held_frame={data[1][8:0],data[0]};
 wire [31:0] held_a=data[2][31:0],held_b=data[2][63:32];
 wire [31:0] a_base=data[3][31:0],a_limit=data[4][31:0];
 wire [31:0] b_base=data[5][31:0],b_limit=data[6][31:0];
 wire [1:0] na=data[7][1:0],nb=data[7][3:2];
 wire held_pair=data[7][4];wire [15:0] tag=data[7][20:5];
 wire [3:0] expected=(4'b0011>>(2-na)) |
                         (held_pair?((4'b0011>>(2-nb))<<2):4'b0);
 wire source_context=frame==held_frame&&owned;
 wire shape=rows_a>=1&&rows_a<=2&&(!pair_op||(rows_b>=1&&rows_b<=2&&op_a!=op_b))&&
  base_a[5:0]==0&&limit_a>base_a&&({1'b0,base_a}+33'(rows_a)*33'd32<={1'b0,limit_a})&&
  (!pair_op||(base_b[5:0]==0&&limit_b>base_b&&
    ({1'b0,base_b}+33'(rows_b)*33'd32<={1'b0,limit_b})&&
    (limit_a<=base_b||limit_b<=base_a)));
 wire active=state!=IDLE&&state!=DONE&&state!=FAIL;
 assign fault=(|uncorrectable)||state==FAIL||
              (state!=IDLE&&(!source_context||!installed));
 assign retained=state!=IDLE;
 assign reserve_r=state==IDLE&&owned&&installed&&shape&&!fault;
 assign source_permit=active&&!native_finished&&!fault;
 assign done=state==DONE&&!fault;
 assign quiet=state==IDLE&&!fault;
 assign retire_r=done&&owned;
 wire belongs_a=result_op==held_a;
 wire belongs_b=held_pair&&result_op==held_b;
 wire result_shape=(belongs_a&&result_row<na)||(belongs_b&&result_row<nb);
 wire [1:0] result_slot=(belongs_b?2'd2:2'd0)+result_row[1:0];
 wire [3:0] result_mask=4'b1<<result_slot;
 wire [255:0] payload={data[8+4*integer'(slot)+3],data[8+4*integer'(slot)+2],
                      data[8+4*integer'(slot)+1],data[8+4*integer'(slot)]};
 wire [31:0] address=(slot[1]?b_base:a_base)+{26'b0,slot[0],5'b0};
 assign req_v=(state==WRITE||state==READ)&&!fault;
 assign req={state==WRITE,address,payload,state==WRITE?32'hffffffff:32'b0,tag};
 wire response_match=rsp[272:257]==tag&&rsp[256]==(state==WAIT_WRITE);
 assign rsp_r=(state==WAIT_WRITE||state==WAIT_READ)&&response_match&&!fault;
 reg [63:0] control_next;
 reg [3:0] available;integer next_slot;
 always @*begin
  control_next=data[24];available=seen&~verified;next_slot=0;
  for(integer k=3;k>=0;k=k-1)if(available[k])next_slot=k;
  if(result_v&&active)control_next[6:3]=seen|result_mask;
  if(native_done&&active)control_next[13]=1;
  case(state)
   CAPTURE:if(|available)begin control_next[2:0]=WRITE;control_next[12:11]=2'(next_slot);end
    else if(native_finished&&seen==expected&&verified==expected)control_next[2:0]=DONE;
   WRITE:if(req_v&&req_r)control_next[2:0]=WAIT_WRITE;
   WAIT_WRITE:if(rsp_v&&rsp_r)control_next[2:0]=READ;
   READ:if(req_v&&req_r)control_next[2:0]=WAIT_READ;
   WAIT_READ:if(rsp_v&&rsp_r)begin
    if(rsp[255:0]!=payload)control_next[2:0]=FAIL;
    else begin control_next[10:7]=verified|(4'b1<<slot);control_next[2:0]=CAPTURE;end
   end
   DONE:if(retire_v&&retire_r)control_next=0;
   default:begin end
  endcase
  if(fault||(reserve_v&&state==IDLE&&!reserve_r)||
     (result_v&&(!active||!result_shape|||(seen&result_mask)))||
     (native_done&&active&&((seen|(result_v?result_mask:4'b0))!=expected))||
     (rsp_v&&(state!=WAIT_WRITE&&state!=WAIT_READ||!response_match)))
   control_next[2:0]=FAIL;
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)for(integer k=0;k<25;k=k+1)code[k]<=ot_gpu_w6_secded_pkg::encode64(0);
  else begin
   code[24]<=ot_gpu_w6_secded_pkg::encode64(control_next);
   if(reserve_v&&reserve_r)begin
    code[0]<=ot_gpu_w6_secded_pkg::encode64(frame[63:0]);
    code[1]<=ot_gpu_w6_secded_pkg::encode64({55'b0,frame[72:64]});
    code[2]<=ot_gpu_w6_secded_pkg::encode64({op_b,op_a});
    code[3]<=ot_gpu_w6_secded_pkg::encode64({32'b0,base_a});
    code[4]<=ot_gpu_w6_secded_pkg::encode64({32'b0,limit_a});
    code[5]<=ot_gpu_w6_secded_pkg::encode64({32'b0,base_b});
    code[6]<=ot_gpu_w6_secded_pkg::encode64({32'b0,limit_b});
    code[7]<=ot_gpu_w6_secded_pkg::encode64({43'b0,provider_tag,pair_op,rows_b,rows_a});
    code[24]<=ot_gpu_w6_secded_pkg::encode64(64'(CAPTURE));
   end
   if(result_v&&active&&result_shape&&!(|(seen&result_mask))&&!fault)
    for(integer k=0;k<4;k=k+1)
     code[8+4*integer'(result_slot)+k]<=ot_gpu_w6_secded_pkg::encode64(result_data[k*64+:64]);
  end
 end
 end endgenerate
endmodule
