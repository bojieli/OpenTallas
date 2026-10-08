// Full NC8: thirteen2048-bit groups/fragment, last640 payload bits, padding0.
module ot_hbm_sm_x_read #(parameter integer ENABLE=0)(
 input wire clk,rst_n,input wire installed_valid,input wire[36:0] installed_base,input wire[37:0] installed_limit,
 input wire[15:0] installed_record,input wire[7:0] installed_extent,input wire[6:0] installed_ring,
 input wire x_req_valid,output wire x_req_ready,input wire[15:0] x_req_record,
 input wire[6:0] x_req_base,input wire[7:0] x_req_extent,
 output wire x_valid,input wire x_ready,output wire[15:0] x_record,
 output wire[6:0] x_ordinal,output wire[3:0] x_group,output wire[2047:0] x_data,output wire x_error,
 input wire[15:0] issuer_tag,
 output wire service_req_valid,input wire service_req_ready,output wire[36:0] service_req_addr,
 output wire[15:0] service_req_tag,input wire service_rsp_valid,output wire service_rsp_ready,
 input wire service_rsp_we,input wire[15:0] service_rsp_tag,input wire[255:0] service_rsp_data,
 input wire service_fault,output wire fault
);
 localparam[2:0] IDLE=1,SEND=2,WAIT=4;
 (* keep=1 *)reg[78:0] q;reg[78:0] next_q;(* keep=1 *)reg parity;
 (* keep=1 *)reg[2:0] state;reg sticky;
 wire[36:0] base=q[78:42];wire[7:0] extent=q[25:18];wire[6:0] ordinal=q[10:4];wire[3:0] group_id=q[3:0];
 wire legal=installed_valid&&installed_base[4:0]==0&&x_req_record==installed_record&&
  x_req_extent==installed_extent&&x_req_base==installed_ring&&x_req_extent>0&&x_req_extent<=128&&
  ({1'b0,installed_base}+38'(x_req_extent)*38'd3328)<=installed_limit&&installed_limit<=38'h2000000000;
 wire av,ar,ov,af;wire[2047:0] assembled;
 wire blocked=sticky||af||parity!=(^q)||!(state==IDLE||state==SEND||state==WAIT)||
 (x_req_valid&&state==IDLE&&!legal)||(ov&&group_id==12&&assembled[2047:640]!=0);
 assign fault=(ENABLE!=0)&&blocked;
 assign x_req_ready=(ENABLE!=0)&&state==IDLE&&legal&&!blocked;
 assign av=(ENABLE!=0)&&state==SEND&&!blocked;
 assign x_valid=(ENABLE!=0)&&state==WAIT&&ov&&!blocked;
 assign x_record=q[41:26];assign x_ordinal=ordinal;assign x_group=group_id;assign x_data=assembled;assign x_error=0;
 wire[36:0] group_base=base+37'(ordinal)*37'd3328+37'(group_id)*37'd256;
 ot_hbm_sm_sector_read #(.ENABLE(ENABLE),.N(8)) sectors(
 .clk(clk),.rst_n(rst_n),.in_valid(av),.in_ready(ar),.in_base(group_base),.in_tag(issuer_tag),
 .out_valid(ov),.out_ready(x_valid&&x_ready),.out_data(assembled),.fault(af),.*);
 always @*begin
  next_q=q;
  if(x_req_valid&&x_req_ready)next_q={installed_base,x_req_record,x_req_extent,x_req_base,7'b0,4'b0};
  if(x_valid&&x_ready)begin
   if(group_id==12)begin next_q[3:0]=0;next_q[10:4]=ordinal+1'b1;end
   else next_q[3:0]=group_id+1'b1;
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin q<=0;parity<=0;state<=IDLE;sticky<=0;end
  else if(ENABLE!=0)begin
   if(blocked)sticky<=1;
   else begin
    q<=next_q;parity<=^next_q;
    if(x_req_valid&&x_req_ready)state<=SEND;
    if(av&&ar)state<=WAIT;
    if(x_valid&&x_ready)state<=group_id==12&&{1'b0,ordinal}+8'd1==extent?IDLE:SEND;
   end
  end
 end
endmodule
